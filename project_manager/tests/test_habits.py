"""Tests for Habits dataclasses and client functions."""

from unittest.mock import MagicMock, patch

import pytest

from gtd.notion.habits import (
    create_habit,
    delete_habit,
    get_calendar_data,
    mark_complete,
    update_habit,
)
from gtd.notion.habits_models import Habit, HabitCompletion


class TestHabitParsing:
    """Test Habit.from_page parsing."""

    def test_parse_habit_all_fields(self):
        """Parse a complete habit page."""
        page = {
            'id': '12345678-1234-1234-1234-123456789abc',
            'properties': {
                'Name': {'title': [{'plain_text': 'Morning Meditation'}]},
                'Description': {
                    'rich_text': [{'plain_text': '10 minute meditation'}]
                },
                'Color': {'select': {'name': 'Blue'}},
                'Target Frequency': {'select': {'name': 'Daily'}},
                'Active': {'checkbox': True},
                'Created Date': {'date': {'start': '2026-07-20'}},
                'Notes': {'rich_text': [{'plain_text': 'For mental clarity'}]},
            },
        }

        habit = Habit.from_page(page)

        assert habit.page_id == '12345678123412341234123456789abc'
        assert habit.name == 'Morning Meditation'
        assert habit.description == '10 minute meditation'
        assert habit.color == 'Blue'
        assert habit.target_frequency == 'Daily'
        assert habit.active is True
        assert habit.created_date == '2026-07-20'
        assert habit.notes == 'For mental clarity'

    def test_parse_habit_minimal_fields(self):
        """Parse a minimal habit page."""
        page = {
            'id': '87654321-4321-4321-4321-cba987654321',
            'properties': {
                'Name': {'title': [{'plain_text': 'Exercise'}]},
                'Description': {'rich_text': []},
                'Color': {'select': {}},
                'Target Frequency': {'select': {}},
                'Active': {'checkbox': False},
                'Created Date': {'date': {}},
                'Notes': {'rich_text': []},
            },
        }

        habit = Habit.from_page(page)

        assert habit.name == 'Exercise'
        assert habit.description == ''
        assert habit.color == 'Blue'  # default
        assert habit.target_frequency == 'Daily'  # default
        assert habit.active is False
        assert habit.created_date == ''
        assert habit.notes == ''


class TestHabitCompletionParsing:
    """Test HabitCompletion.from_page parsing."""

    def test_parse_completion_all_fields(self):
        """Parse a complete habit completion page."""
        page = {
            'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'created_time': '2026-07-20T08:30:00.000Z',
            'properties': {
                'Habit': {
                    'relation': [
                        {'id': 'hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh'}
                    ]
                },
                'Date': {'date': {'start': '2026-07-20'}},
                'Status': {'select': {'name': 'Complete'}},
                'Notes': {'rich_text': [{'plain_text': 'Great session'}]},
            },
        }

        completion = HabitCompletion.from_page(page)

        assert completion.page_id == 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        assert completion.habit_id == 'hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh'
        assert completion.date == '2026-07-20'
        assert completion.status == 'Complete'
        assert completion.notes == 'Great session'
        assert completion.logged_at == '2026-07-20T08:30:00.000Z'

    def test_parse_completion_no_notes(self):
        """Parse habit completion with no notes."""
        page = {
            'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
            'created_time': '2026-07-19T10:00:00.000Z',
            'properties': {
                'Habit': {
                    'relation': [
                        {'id': 'hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh'}
                    ]
                },
                'Date': {'date': {'start': '2026-07-19'}},
                'Status': {'select': {'name': 'Skipped'}},
                'Notes': {'rich_text': []},
            },
        }

        completion = HabitCompletion.from_page(page)

        assert completion.status == 'Skipped'
        assert completion.notes == ''


@pytest.mark.parametrize(
    ('frequency', 'expected'),
    [
        ('Daily', 'Daily'),
        ('5x/week', '5x/week'),
        ('Weekly', 'Weekly'),
        ('Monthly', 'Monthly'),
    ],
)
def test_habit_frequencies(frequency, expected):
    """Test various habit frequencies."""
    page = {
        'id': 'cccccccc-cccc-cccc-cccc-cccccccccccc',
        'properties': {
            'Name': {'title': [{'plain_text': 'Test Habit'}]},
            'Target Frequency': {'select': {'name': frequency}},
            'Description': {'rich_text': []},
            'Color': {'select': {}},
            'Active': {'checkbox': True},
            'Created Date': {'date': {}},
            'Notes': {'rich_text': []},
        },
    }

    habit = Habit.from_page(page)
    assert habit.target_frequency == expected


@pytest.mark.parametrize(
    ('color', 'expected'),
    [
        ('Blue', 'Blue'),
        ('Green', 'Green'),
        ('Purple', 'Purple'),
        ('Red', 'Red'),
        ('Orange', 'Orange'),
        ('Yellow', 'Yellow'),
    ],
)
def test_habit_colors(color, expected):
    """Test various habit colors."""
    page = {
        'id': 'dddddddd-dddd-dddd-dddd-dddddddddddd',
        'properties': {
            'Name': {'title': [{'plain_text': 'Test Habit'}]},
            'Color': {'select': {'name': color}},
            'Target Frequency': {'select': {}},
            'Description': {'rich_text': []},
            'Active': {'checkbox': True},
            'Created Date': {'date': {}},
            'Notes': {'rich_text': []},
        },
    }

    habit = Habit.from_page(page)
    assert habit.color == expected


class TestHabitCompletion:
    """Test mark_complete and get_calendar_data."""

    @patch.dict('os.environ', {'NOTION_HABIT_COMPLETIONS_DB_ID': 'test-db-id'})
    @patch('gtd.notion.habits.get_completions_for_habit')
    @patch('gtd.notion.habits.get_token')
    @patch('httpx.post')
    def test_mark_complete_creates_new_record(
        self, mock_post, mock_token, mock_get_completions
    ):
        """Test marking a habit complete creates a new record."""
        mock_token.return_value = 'test-token'
        mock_get_completions.return_value = []  # No existing record

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'new-page-id',
            'properties': {
                'Habit': {'relation': [{'id': 'habit-id'}]},
                'Date': {'date': {'start': '2026-07-20'}},
                'Status': {'select': {'name': 'Complete'}},
                'Notes': {'rich_text': []},
            },
            'created_time': '2026-07-20T10:00:00.000Z',
        }
        mock_post.return_value = mock_response

        completion = mark_complete('habit-id', '2026-07-20', 'Complete')

        assert completion.status == 'Complete'
        assert completion.date == '2026-07-20'
        mock_post.assert_called_once()

    @patch.dict('os.environ', {'NOTION_HABIT_COMPLETIONS_DB_ID': 'test-db-id'})
    @patch('gtd.notion.habits.get_completions_for_habit')
    @patch('gtd.notion.habits.get_token')
    @patch('httpx.patch')
    def test_mark_complete_updates_existing_record(
        self, mock_patch, mock_token, mock_get_completions
    ):
        """Test marking a habit complete updates existing record."""
        mock_token.return_value = 'test-token'

        existing = HabitCompletion(
            page_id='page-id',
            habit_id='habit-id',
            date='2026-07-20',
            status='Incomplete',
        )
        mock_get_completions.return_value = [existing]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'page-id',
            'properties': {
                'Habit': {'relation': [{'id': 'habit-id'}]},
                'Date': {'date': {'start': '2026-07-20'}},
                'Status': {'select': {'name': 'Complete'}},
                'Notes': {'rich_text': []},
            },
            'created_time': '2026-07-20T10:00:00.000Z',
        }
        mock_patch.return_value = mock_response

        completion = mark_complete('habit-id', '2026-07-20', 'Complete')

        assert completion.status == 'Complete'
        mock_patch.assert_called_once()


class TestCalendarData:
    """Test calendar data retrieval and formatting."""

    @patch('gtd.notion.habits.get_completions_for_habit')
    def test_get_calendar_data_returns_dict(self, mock_get_completions):
        """Test calendar data is returned as dict."""
        completions = [
            HabitCompletion(
                page_id='p1',
                habit_id='h1',
                date='2026-07-20',
                status='Complete',
            ),
            HabitCompletion(
                page_id='p2',
                habit_id='h1',
                date='2026-07-19',
                status='Incomplete',
            ),
            HabitCompletion(
                page_id='p3',
                habit_id='h1',
                date='2026-07-18',
                status='Skipped',
            ),
        ]
        mock_get_completions.return_value = completions

        data = get_calendar_data('h1', months_back=1)

        assert isinstance(data, dict)
        assert data['2026-07-20'] == 'Complete'
        assert data['2026-07-19'] == 'Incomplete'
        assert data['2026-07-18'] == 'Skipped'

    @patch('gtd.notion.habits.get_completions_for_habit')
    def test_get_calendar_data_empty(self, mock_get_completions):
        """Test calendar data with no completions."""
        mock_get_completions.return_value = []

        data = get_calendar_data('h1', months_back=1)

        assert isinstance(data, dict)
        assert len(data) == 0


class TestHabitCreation:
    """Test habit creation and updates."""

    @patch.dict('os.environ', {'NOTION_HABITS_DB_ID': 'test-habits-db'})
    @patch('gtd.notion.habits.get_token')
    @patch('httpx.post')
    def test_create_habit_success(self, mock_post, mock_token):
        """Test successful habit creation."""
        mock_token.return_value = 'test-token'

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'habit-id-123',
            'properties': {
                'Name': {'title': [{'plain_text': 'New Habit'}]},
                'Description': {'rich_text': [{'plain_text': 'Description'}]},
                'Color': {'select': {'name': 'Green'}},
                'Target Frequency': {'select': {'name': 'Daily'}},
                'Active': {'checkbox': True},
                'Created Date': {'date': {'start': '2026-07-20'}},
                'Notes': {'rich_text': []},
            },
        }
        mock_post.return_value = mock_response

        habit = create_habit(
            name='New Habit',
            target_frequency='Daily',
            description='Description',
            color='Green',
        )

        assert habit.name == 'New Habit'
        assert habit.target_frequency == 'Daily'
        assert habit.color == 'Green'
        assert habit.active is True
        mock_post.assert_called_once()

    @patch.dict('os.environ', {'NOTION_HABITS_DB_ID': 'test-habits-db'})
    @patch('gtd.notion.habits.get_token')
    @patch('httpx.patch')
    def test_update_habit_success(self, mock_patch, mock_token):
        """Test successful habit update."""
        mock_token.return_value = 'test-token'

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'habit-id',
            'properties': {
                'Name': {'title': [{'plain_text': 'Updated Name'}]},
                'Description': {'rich_text': []},
                'Color': {'select': {'name': 'Red'}},
                'Target Frequency': {'select': {'name': '5x/week'}},
                'Active': {'checkbox': False},
                'Created Date': {'date': {'start': '2026-07-20'}},
                'Notes': {'rich_text': []},
            },
        }
        mock_patch.return_value = mock_response

        updated = update_habit(
            'habit-id',
            name='Updated Name',
            color='Red',
            target_frequency='5x/week',
            active=False,
        )

        assert updated.name == 'Updated Name'
        assert updated.color == 'Red'
        assert updated.target_frequency == '5x/week'
        assert updated.active is False
        mock_patch.assert_called_once()


class TestHabitDeletion:
    """Test habit deletion."""

    @patch.dict('os.environ', {'NOTION_HABITS_DB_ID': 'test-habits-db'})
    @patch('gtd.notion.habits.get_token')
    @patch('httpx.patch')
    def test_delete_habit_success(self, mock_patch, mock_token):
        """Test successful habit deletion."""
        mock_token.return_value = 'test-token'

        mock_response = MagicMock()
        mock_patch.return_value = mock_response

        delete_habit('habit-id')

        mock_patch.assert_called_once()
        call_args = mock_patch.call_args
        assert 'habit-id' in call_args[0][0]
        assert call_args[1]['json']['archived'] is True
