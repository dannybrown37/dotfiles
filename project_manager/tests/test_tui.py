from datetime import datetime, timedelta

import pytest

from gtd.models import Goal, Tactic, Update
from gtd.tui import (
    _parse_updates_from_text,
    _render_goal_detail,
    _render_score_history,
    _serialize_updates,
)


def _make_goal(**kwargs) -> Goal:
    now = datetime.now()
    defaults = {
        'name': 'Test Goal',
        'description': 'A test description',
        'start_date': now.isoformat(),
        'end_date': (now + timedelta(weeks=12)).isoformat(),
    }
    return Goal(**{**defaults, **kwargs})


def _make_goal_week(week: int, **kwargs) -> Goal:
    start = datetime.now() - timedelta(weeks=week - 1)
    return _make_goal(
        start_date=start.isoformat(),
        end_date=(start + timedelta(weeks=12)).isoformat(),
        **kwargs,
    )


class TestRenderGoalDetail:
    def test_shows_goal_name(self):
        goal = _make_goal(name='My Big Goal')
        result = _render_goal_detail(goal)
        assert 'My Big Goal' in result

    def test_shows_description(self):
        goal = _make_goal(description='Do something great')
        result = _render_goal_detail(goal)
        assert 'Do something great' in result

    def test_shows_week_info(self):
        goal = _make_goal_week(3)
        result = _render_goal_detail(goal)
        assert 'Week 3' in result

    def test_no_tactics_shows_prompt(self):
        goal = _make_goal()
        result = _render_goal_detail(goal)
        assert 'No tactics' in result

    def test_tactic_description_shown(self):
        goal = _make_goal(
            tactics=[
                Tactic(description='Write daily', reminder_cadence='daily')
            ]
        )
        result = _render_goal_detail(goal)
        assert 'Write daily' in result
        assert 'daily' in result

    def test_scored_tactic_shows_score(self):
        goal = _make_goal(
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    weekly_scores={'1': 8},
                )
            ]
        )
        result = _render_goal_detail(goal)
        assert '8/10' in result

    def test_unscored_tactic_shows_dash(self):
        goal = _make_goal(
            tactics=[Tactic(description='Run', reminder_cadence='daily')]
        )
        result = _render_goal_detail(goal)
        assert '—' in result

    def test_tactic_with_update_shows_latest(self):
        goal = _make_goal(
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    updates=[
                        Update(date='2026-07-01T09:00:00', note='Did 5k')
                    ],
                )
            ]
        )
        result = _render_goal_detail(goal)
        assert 'Did 5k' in result

    def test_overall_execution_shown_when_scored(self):
        goal = _make_goal(
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    weekly_scores={'1': 9},
                )
            ]
        )
        result = _render_goal_detail(goal)
        assert '90%' in result


class TestRenderScoreHistory:
    def test_shows_goal_name(self):
        goal = _make_goal(name='Fitness Goal')
        result = _render_score_history(goal)
        assert 'Fitness Goal' in result

    def test_shows_unscored_weeks(self):
        goal = _make_goal_week(3)
        result = _render_score_history(goal)
        assert 'not scored' in result

    def test_shows_scored_weeks(self):
        goal = _make_goal_week(
            2,
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    weekly_scores={'1': 8},
                )
            ],
        )
        result = _render_score_history(goal)
        assert '80%' in result

    def test_marks_current_week(self):
        goal = _make_goal_week(2)
        result = _render_score_history(goal)
        assert 'current' in result

    def test_shows_overall_when_scored(self):
        goal = _make_goal_week(
            2,
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    weekly_scores={'1': 9, '2': 7},
                )
            ],
        )
        result = _render_score_history(goal)
        assert 'Overall' in result

    @pytest.mark.parametrize(
        ('score', 'expected_indicator'),
        [
            (9, '🟢'),
            (7, '🟡'),
            (5, '🔴'),
        ],
    )
    def test_score_indicators(self, score: int, expected_indicator: str):
        goal = _make_goal(
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    weekly_scores={'1': score},
                )
            ]
        )
        result = _render_score_history(goal)
        assert expected_indicator in result


# --- _serialize_updates / _parse_updates_from_text round-trip ---


class TestSerializeUpdates:
    def test_empty_updates_produces_only_header_lines(self):
        result = _serialize_updates([])
        lines = [
            ln for ln in result.splitlines() if ln and not ln.startswith('#')
        ]
        assert lines == []

    def test_single_update_serialized(self):
        updates = [Update(date='2026-07-01', note='Did the thing')]
        result = _serialize_updates(updates)
        assert '2026-07-01: Did the thing' in result

    def test_multiple_updates_all_present(self):
        updates = [
            Update(date='2026-07-01', note='First'),
            Update(date='2026-07-02', note='Second'),
        ]
        result = _serialize_updates(updates)
        assert '2026-07-01: First' in result
        assert '2026-07-02: Second' in result

    def test_datetime_truncated_to_date(self):
        updates = [Update(date='2026-07-11T09:30:00', note='Morning run')]
        result = _serialize_updates(updates)
        assert '2026-07-11: Morning run' in result
        assert 'T09:30' not in result


class TestParseUpdatesFromText:
    def test_basic_round_trip(self):
        updates = [
            Update(date='2026-07-01', note='Did it'),
            Update(date='2026-07-03', note='Did it again'),
        ]
        text = _serialize_updates(updates)
        parsed = _parse_updates_from_text(text)
        assert len(parsed) == 2
        assert parsed[0].note == 'Did it'
        assert parsed[1].date == '2026-07-03'

    def test_comments_and_blank_lines_ignored(self):
        text = '# This is a comment\n\n2026-07-05: Real entry\n\n'
        parsed = _parse_updates_from_text(text)
        assert len(parsed) == 1
        assert parsed[0].note == 'Real entry'

    def test_deleted_line_removes_entry(self):
        updates = [
            Update(date='2026-07-01', note='Keep me'),
            Update(date='2026-07-02', note='Delete me'),
        ]
        text = _serialize_updates(updates)
        trimmed = '\n'.join(
            ln for ln in text.splitlines() if 'Delete me' not in ln
        )
        parsed = _parse_updates_from_text(trimmed)
        assert len(parsed) == 1
        assert parsed[0].note == 'Keep me'

    def test_edited_note_preserved(self):
        parsed = _parse_updates_from_text('2026-07-10: Edited note')
        assert parsed[0].note == 'Edited note'

    def test_malformed_lines_skipped(self):
        text = 'not-a-date: something\n2026-07-10: good line\njunk'
        parsed = _parse_updates_from_text(text)
        assert len(parsed) == 1
        assert parsed[0].date == '2026-07-10'

    def test_note_with_colon_preserved(self):
        text = '2026-07-10: Step 1: do the thing'
        parsed = _parse_updates_from_text(text)
        assert parsed[0].note == 'Step 1: do the thing'

    @pytest.mark.parametrize(
        ('date_input', 'expected_date'),
        [
            ('2026-07-11', '2026-07-11'),
            ('2026-07-01', '2026-07-01'),
        ],
    )
    def test_valid_iso_dates_accepted(
        self, date_input: str, expected_date: str
    ):
        parsed = _parse_updates_from_text(f'{date_input}: Some note')
        assert len(parsed) == 1
        assert parsed[0].date == expected_date
