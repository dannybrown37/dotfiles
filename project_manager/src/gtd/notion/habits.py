"""Habits database client functions."""

import os
from datetime import datetime, timedelta

import httpx

from .client import NOTION_API_URL, _handle_response, get_token
from .init import _auth_headers
from .habits_models import Habit, HabitCompletion


def _get_habits_db_id() -> str:
    """Get Habits database ID from environment."""
    db_id = os.getenv('NOTION_HABITS_DB_ID')
    msg = 'NOTION_HABITS_DB_ID not set in environment'
    if not db_id:
        raise ValueError(msg)
    return db_id


def _get_completions_db_id() -> str:
    """Get Habit Completions database ID from environment."""
    db_id = os.getenv('NOTION_HABIT_COMPLETIONS_DB_ID')
    msg = 'NOTION_HABIT_COMPLETIONS_DB_ID not set'
    if not db_id:
        raise ValueError(msg)
    return db_id


def get_habits(*, active_only: bool = True) -> list[Habit]:
    """Fetch all habits, optionally filtering for active only."""
    token = get_token()
    db_id = _get_habits_db_id()

    payload = {}
    if active_only:
        payload = {
            'filter': {
                'property': 'Active',
                'checkbox': {'equals': True},
            }
        }

    response = httpx.post(
        f'{NOTION_API_URL}/databases/{db_id}/query',
        headers=_auth_headers(token),
        json=payload,
    )
    _handle_response(response)

    results = response.json().get('results', [])
    return [Habit.from_page(page) for page in results]


def create_habit(
    name: str,
    target_frequency: str = 'Daily',
    description: str = '',
    color: str = 'Blue',
    notes: str = '',
) -> Habit:
    """Create a new habit."""
    token = get_token()
    db_id = _get_habits_db_id()

    payload = {
        'parent': {'database_id': db_id},
        'properties': {
            'Name': {'title': [{'text': {'content': name}}]},
            'Target Frequency': {'select': {'name': target_frequency}},
            'Color': {'select': {'name': color}},
            'Active': {'checkbox': True},
            'Created Date': {
                'date': {'start': datetime.now().date().isoformat()}
            },
        },
    }

    if description:
        payload['properties']['Description'] = {
            'rich_text': [{'text': {'content': description}}]
        }

    if notes:
        payload['properties']['Notes'] = {
            'rich_text': [{'text': {'content': notes}}]
        }

    response = httpx.post(
        f'{NOTION_API_URL}/pages',
        headers=_auth_headers(token),
        json=payload,
    )
    _handle_response(response)

    return Habit.from_page(response.json())


def update_habit(habit_id: str, **fields: str | bool) -> Habit:
    """Update habit fields.

    Accepts: name, description, color, target_frequency, active, notes.
    """
    token = get_token()

    properties = {}

    if 'name' in fields:
        properties['Name'] = {'title': [{'text': {'content': fields['name']}}]}

    if 'description' in fields:
        properties['Description'] = {
            'rich_text': [{'text': {'content': fields['description']}}]
        }

    if 'color' in fields:
        properties['Color'] = {'select': {'name': fields['color']}}

    if 'target_frequency' in fields:
        properties['Target Frequency'] = {
            'select': {'name': fields['target_frequency']}
        }

    if 'active' in fields:
        properties['Active'] = {'checkbox': fields['active']}

    if 'notes' in fields:
        properties['Notes'] = {
            'rich_text': [{'text': {'content': fields['notes']}}]
        }

    response = httpx.patch(
        f'{NOTION_API_URL}/pages/{habit_id}',
        headers=_auth_headers(token),
        json={'properties': properties},
    )
    _handle_response(response)

    return Habit.from_page(response.json())


def delete_habit(habit_id: str) -> None:
    """Delete a habit (archive the page)."""
    token = get_token()

    response = httpx.patch(
        f'{NOTION_API_URL}/pages/{habit_id}',
        headers=_auth_headers(token),
        json={'archived': True},
    )
    _handle_response(response)


def get_completions_for_habit(
    habit_id: str, from_date: str = '', to_date: str = ''
) -> list[HabitCompletion]:
    """Get completion records for a habit within optional date range.

    Dates are ISO format strings (YYYY-MM-DD).
    """
    token = get_token()
    db_id = _get_completions_db_id()

    filters = [
        {
            'property': 'Habit',
            'relation': {'contains': habit_id},
        }
    ]

    if from_date and to_date:
        filters.append(
            {
                'property': 'Date',
                'date': {
                    'on_or_after': from_date,
                    'on_or_before': to_date,
                },
            }
        )
    elif from_date:
        filters.append(
            {
                'property': 'Date',
                'date': {'on_or_after': from_date},
            }
        )
    elif to_date:
        filters.append(
            {
                'property': 'Date',
                'date': {'on_or_before': to_date},
            }
        )

    payload = (
        {
            'filter': {'and': filters if len(filters) > 1 else filters[0]}
            if filters
            else {}
        }
        if filters
        else {}
    )

    response = httpx.post(
        f'{NOTION_API_URL}/databases/{db_id}/query',
        headers=_auth_headers(token),
        json=payload,
    )
    _handle_response(response)

    results = response.json().get('results', [])
    return [HabitCompletion.from_page(page) for page in results]


def get_completions_for_date(date_str: str) -> list[HabitCompletion]:
    """Get all completions for a specific date."""
    token = get_token()
    db_id = _get_completions_db_id()

    payload = {
        'filter': {
            'property': 'Date',
            'date': {'equals': date_str},
        }
    }

    response = httpx.post(
        f'{NOTION_API_URL}/databases/{db_id}/query',
        headers=_auth_headers(token),
        json=payload,
    )
    _handle_response(response)

    results = response.json().get('results', [])
    return [HabitCompletion.from_page(page) for page in results]


def mark_complete(
    habit_id: str, date: str, status: str = 'Complete', notes: str = ''
) -> HabitCompletion:
    """Mark a habit complete/incomplete/skipped for a date.

    Returns existing record if one exists for that date, or creates new.
    """
    token = get_token()
    db_id = _get_completions_db_id()

    # Check if record already exists for this date
    existing = get_completions_for_habit(habit_id, date, date)
    if existing:
        page_id = existing[0].page_id
        properties = {
            'Status': {'select': {'name': status}},
        }
        if notes:
            properties['Notes'] = {'rich_text': [{'text': {'content': notes}}]}

        response = httpx.patch(
            f'{NOTION_API_URL}/pages/{page_id}',
            headers=_auth_headers(token),
            json={'properties': properties},
        )
        _handle_response(response)
        return HabitCompletion.from_page(response.json())

    # Create new record
    payload = {
        'parent': {'database_id': db_id},
        'properties': {
            'Title': {'title': [{'text': {'content': f'{date}'}}]},
            'Habit': {'relation': [{'id': habit_id}]},
            'Date': {'date': {'start': date}},
            'Status': {'select': {'name': status}},
        },
    }

    if notes:
        payload['properties']['Notes'] = {
            'rich_text': [{'text': {'content': notes}}]
        }

    response = httpx.post(
        f'{NOTION_API_URL}/pages',
        headers=_auth_headers(token),
        json=payload,
    )
    _handle_response(response)

    return HabitCompletion.from_page(response.json())


def get_calendar_data(habit_id: str, months_back: int = 12) -> dict[str, str]:
    """Get habit completion calendar data for the past N months.

    Returns dict mapping ISO date strings to status ("Complete",
    "Incomplete", "Skipped").
    """
    start_date = (datetime.now() - timedelta(days=30 * months_back)).date()
    to_date = datetime.now().date()

    completions = get_completions_for_habit(
        habit_id,
        from_date=start_date.isoformat(),
        to_date=to_date.isoformat(),
    )

    return {c.date: c.status for c in completions}
