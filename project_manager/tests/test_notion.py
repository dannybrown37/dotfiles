"""Tests for Notion integration modules."""

from datetime import datetime, timedelta
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from gtd.notion.client import (
    NotionAPIError,
    _extract_block_text,
    _handle_response,
    build_property_update,
)
from gtd.notion.entries import _parse_date_input
from gtd.notion.log import (
    _infer_cadence,
    _infer_reschedule_days,
    _is_recurring,
)
from gtd.notion.models import ProjectEntry
from gtd.notion.entries import _get_today_entries


# --- _handle_response: maps HTTP codes to actionable errors ---


class TestHandleResponse:
    def _resp(self, code: int, **kwargs) -> MagicMock:
        resp = MagicMock()
        resp.status_code = code
        resp.is_success = 200 <= code < 300
        resp.text = kwargs.get('text', '')
        resp.headers = kwargs.get('headers', {})
        return resp

    def test_2xx_passes_silently(self):
        _handle_response(self._resp(200))
        _handle_response(self._resp(204))

    @pytest.mark.parametrize(
        ('code', 'expected_substr'),
        [
            (HTTPStatus.UNAUTHORIZED, 'gtd init'),
            (HTTPStatus.FORBIDDEN, 'permission'),
            (HTTPStatus.NOT_FOUND, 'NOTION_PROJECTS_DB_ID'),
            (HTTPStatus.CONFLICT, 'try again'),
            (HTTPStatus.TOO_MANY_REQUESTS, 'rate limit'),
        ],
    )
    def test_known_errors_give_actionable_advice(
        self, code: int, expected_substr: str
    ):
        resp = self._resp(code, headers={'Retry-After': '30'})
        with pytest.raises(NotionAPIError) as exc_info:
            _handle_response(resp)
        assert expected_substr.lower() in str(exc_info.value).lower()
        assert exc_info.value.status_code == code

    def test_5xx_treated_as_server_error(self):
        for code in (500, 502, 503):
            with pytest.raises(NotionAPIError, match='server error'):
                _handle_response(self._resp(code))

    def test_unknown_4xx_includes_response_body(self):
        resp = self._resp(422, text='{"message": "validation failed"}')
        with pytest.raises(NotionAPIError) as exc_info:
            _handle_response(resp)
        assert 'validation failed' in str(exc_info.value)


# --- _extract_block_text: the parser that drives get_page_body ---


class TestExtractBlockText:
    def test_paragraph_joins_rich_text_segments(self):
        block = {
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [
                    {'plain_text': 'Hello'},
                    {'plain_text': 'world'},
                ],
            },
        }
        assert _extract_block_text(block) == 'Hello world'

    def test_bulleted_list_gets_prefix(self):
        block = {
            'type': 'bulleted_list_item',
            'bulleted_list_item': {
                'rich_text': [{'plain_text': 'Item one'}],
            },
        }
        assert _extract_block_text(block) == '• Item one'

    def test_unsupported_block_type_returns_none(self):
        block = {'type': 'image', 'image': {}}
        assert _extract_block_text(block) is None

    def test_whitespace_only_returns_none(self):
        block = {
            'type': 'paragraph',
            'paragraph': {'rich_text': [{'plain_text': '   '}]},
        }
        assert _extract_block_text(block) is None


# --- _get_today_entries: client-side filtering after Notion query ---


def _make_page(
    *,
    header: str = 'Test',
    context: str = 'Work',
    next_step: str = 'Do it',
) -> dict:
    return {
        'id': 'page-1',
        'created_time': '2026-06-01T00:00:00Z',
        'properties': {
            'Header': {'title': [{'plain_text': header}]},
            'Status': {'select': {'name': 'Current Project'}},
            'Context': {
                'select': {'name': context} if context else None,
            },
            'Next Actionable Step': {
                'rich_text': [{'plain_text': next_step}] if next_step else [],
            },
            'Details': {'rich_text': []},
            'Due Date': {'date': None},
            'Follow-Up Date': {'date': None},
        },
    }


class TestGetTodayEntries:
    @patch('gtd.notion.entries.query_database')
    def test_excludes_incomplete_entries(self, mock_db):
        """Items missing context or next_step are filtered out client-side."""
        mock_db.return_value = [
            _make_page(header='Complete', context='Work', next_step='Go'),
            _make_page(header='No context', context='', next_step='Go'),
            _make_page(header='No step', context='Work', next_step=''),
        ]
        results = _get_today_entries()
        assert len(results) == 1
        assert results[0].header == 'Complete'


# --- _parse_date_input: relative dates and error handling ---


class TestParseDateInput:
    def test_relative_days_bypass_dateutil(self):
        result = _parse_date_input('tomorrow')
        expected = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        assert result == expected

    def test_garbage_returns_none_gracefully(self, capsys):
        assert _parse_date_input('asdfghjkl') is None
        assert 'Could not parse' in capsys.readouterr().out


# --- Cadence inference: drives auto-rescheduling logic ---


class TestCadenceInference:
    @pytest.mark.parametrize(
        ('header', 'expected_days'),
        [
            ('Daily: Meditate', 1),
            ('daily: journal', 1),
            ('Weekly: Review goals', 7),
            ('2x/week: Exercise', 3),
            ('3x/week: Practice guitar', 2),
        ],
    )
    def test_recurring_headers_infer_days(
        self, header: str, expected_days: int
    ):
        assert _infer_reschedule_days(header) == expected_days

    @pytest.mark.parametrize(
        'header',
        ['Buy groceries', 'Call dentist', '', 'Dailyish: nope'],
    )
    def test_non_recurring_returns_none(self, header: str):
        assert _infer_reschedule_days(header) is None

    def test_infer_cadence_defaults_to_weekly(self):
        assert _infer_cadence('No prefix') == 'weekly'

    def test_is_recurring_delegates_to_infer(self):
        entry = ProjectEntry(
            page_id='x',
            header='Daily: Meditate',
            status='Current Project',
            context='Home',
            details='',
            next_step='Sit',
            due_date=None,
            follow_up_date=None,
            created_date='2026-06-01',
        )
        assert _is_recurring(entry) is True
        entry.header = 'Call Bob'
        assert _is_recurring(entry) is False


# --- build_property_update: empty-string-clears semantics ---


class TestBuildPropertyUpdate:
    def test_empty_string_clears_date_field(self):
        """Empty string means 'clear this field', distinct from None."""
        props = build_property_update(due_date='', follow_up_date='')
        assert props['Due Date'] == {'date': None}
        assert props['Follow-Up Date'] == {'date': None}

    def test_none_omits_field_entirely(self):
        props = build_property_update(status='Waiting For')
        assert 'Status' in props
        assert 'Due Date' not in props
        assert 'Follow-Up Date' not in props
        assert 'Header' not in props
