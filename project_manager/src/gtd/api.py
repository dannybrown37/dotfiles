"""Thin Flask wrapper around GTD Notion operations for iOS Shortcuts."""

from __future__ import annotations

from http import HTTPStatus
import os
from dataclasses import asdict
from datetime import datetime
from functools import wraps
from typing import Any, TYPE_CHECKING
from urllib.parse import unquote_plus
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from collections.abc import Callable

import httpx
from flask import Flask, jsonify, request
from dateutil import parser as dateparser

from gtd.notion.capture import _create_page
from gtd.notion.client import (
    build_property_update,
    get_contexts,
    query_database,
    update_page,
)
from gtd.notion.models import ProjectEntry
from gtd.notion.schema import DEFAULT_LIST_CATEGORIES
from gtd.notion.triage import TRIAGE_STATUSES
from gtd.storage import load_list_categories

NOTION_API_URL = 'https://api.notion.com/v1'
NOTION_API_VERSION = '2022-06-28'

app = Flask(__name__)


# region Utils


def require_auth(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        expected = os.environ.get('GTD_API_KEY')
        if not expected:
            return jsonify(error='GTD_API_KEY not set on server'), 500
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer ') or auth[7:] != expected:
            return jsonify(error='Invalid API key'), 401
        return fn(*args, **kwargs)

    return wrapper


def _entry_dict(e: ProjectEntry, excluded: list[str] | None = None) -> dict:
    excluded = excluded or []
    return {k: v for k, v in asdict(e).items() if k not in excluded}


def _get_timezone_iso_date() -> str:
    return datetime.now(ZoneInfo('America/New_York')).date().isoformat()


def _get_page_by_id(page_id: str) -> dict | None:
    """Retrieve a Notion page by ID and return as ProjectEntry dict."""
    url = f'{NOTION_API_URL}/pages/{page_id}'
    token = os.environ.get('NOTION_NOTES_TOKEN', '')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Notion-Version': NOTION_API_VERSION,
    }
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        if response.status_code == HTTPStatus.OK:
            return response.json()
    except Exception:
        print(f'Failed to retrieve page {page_id}, response: {response.text}')
    return None


# endregion Utils

# region Triage Helpers


def _validate_triage_status(status: str) -> tuple[dict, int] | None:
    """Validate status value. Returns error tuple if invalid, None if valid."""
    if status not in TRIAGE_STATUSES:
        msg = (
            f'Invalid status "{status}". Must be one of: '
            f'{", ".join(TRIAGE_STATUSES)}'
        )
        return jsonify(error=msg), 400
    return None


def _validate_and_set_context_or_list(
    status: str, context: str, list_category: str
) -> tuple[dict, int] | tuple[dict, None]:
    """Validate and set context or list_category.

    Returns (error_response, 400) if invalid, or (kwargs_dict, None) if valid.
    """
    kwargs: dict = {}

    if status == 'List':
        if not list_category:
            msg = 'list_category is required for List status'
            return jsonify(error=msg), 400
        available = load_list_categories(DEFAULT_LIST_CATEGORIES)
        if list_category not in available:
            msg = (
                f'Invalid list_category "{list_category}". '
                f'Valid categories: {", ".join(sorted(available))}'
            )
            return jsonify(error=msg), 400
        kwargs['list_category'] = list_category
    else:
        if not context:
            msg = f'context is required for {status} status'
            return jsonify(error=msg), 400
        available = get_contexts()
        if context not in available:
            msg = (
                f'Invalid context "{context}". '
                f'Valid contexts: {", ".join(sorted(available))}'
            )
            return jsonify(error=msg), 400
        kwargs['context'] = context

    return kwargs, None


def _parse_triage_dates(
    due_date: str | None, follow_up_date: str | None
) -> tuple[dict, int] | tuple[dict, None]:
    """Parse and validate date strings.

    Returns (error_response, 400) if parsing fails, or (kwargs_dict, None).
    """
    kwargs: dict = {}

    if due_date:
        try:
            parsed = dateparser.parse(due_date, fuzzy=True)
        except (ValueError, TypeError) as e:
            msg = f'Could not parse due_date "{due_date}": {e}'
            return jsonify(error=msg), 400
        if parsed is None:
            msg = f'Could not parse due_date "{due_date}"'
            return jsonify(error=msg), 400
        kwargs['due_date'] = parsed.strftime('%Y-%m-%d')

    if follow_up_date:
        try:
            parsed = dateparser.parse(follow_up_date, fuzzy=True)
        except (ValueError, TypeError) as e:
            msg = f'Could not parse follow_up_date "{follow_up_date}": {e}'
            return jsonify(error=msg), 400
        if parsed is None:
            msg = f'Could not parse follow_up_date "{follow_up_date}"'
            return jsonify(error=msg), 400
        kwargs['follow_up_date'] = parsed.strftime('%Y-%m-%d')

    return kwargs, None


def _apply_triage_updates(
    page_id: str, kwargs: dict[str, str]
) -> tuple[dict, int]:
    """Apply triage updates to Notion and return updated entry.

    Returns (jsonified_entry, 200) or (jsonified_error, 500).
    """
    try:
        props = build_property_update(**kwargs)
        update_page(page_id, props)
    except (ValueError, RuntimeError, OSError) as err:
        return jsonify(error=f'Update failed: {err}'), 500

    # Return updated entry
    updated_page = _get_page_by_id(page_id)
    if updated_page:
        updated_entry = ProjectEntry.from_page(updated_page)
        return jsonify(_entry_dict(updated_entry)), 200

    return jsonify(error='Could not retrieve updated entry'), 500


# endregion Triage Helpers

# Endpoint definitions should be alphabetical


@app.get('/inbox')
@require_auth
def inbox() -> Any:
    """Get all Triage entries (inbox) — includes items with no status."""
    pages = query_database(
        filter_obj={
            'or': [
                {
                    'property': 'Status',
                    'select': {'equals': 'Triage'},
                },
                {
                    'not': {
                        'property': 'Status',
                        'select': {'is_not_empty': True},
                    }
                },
            ],
        },
    )
    entries = [ProjectEntry.from_page(p) for p in pages]
    entries.sort(key=lambda e: (e.due_date or '9999-99-99', e.header))
    return jsonify([_entry_dict(e) for e in entries])


@app.post('/capture')
@require_auth
def capture() -> Any:
    body = request.get_json(force=True)
    header = (body.get('header') or '').strip()
    if not header:
        return jsonify(error='header is required'), 400
    page = _create_page(header)
    return jsonify(page_id=page['id'], header=header), 201


@app.get('/contexts')
@require_auth
def contexts() -> Any:
    today_str = _get_timezone_iso_date()
    pages = query_database(
        filter_obj={
            'property': 'Status',
            'select': {'equals': 'Current Project'},
        },
    )
    entries = [ProjectEntry.from_page(p) for p in pages]
    active_contexts = {
        e.context
        for e in entries
        if e.context
        and (not e.follow_up_date or e.follow_up_date <= today_str)
    }
    return jsonify(contexts=sorted(active_contexts))


@app.get('/next-steps')
@require_auth
def next_steps() -> Any:
    today_str = _get_timezone_iso_date()
    pages = query_database(
        filter_obj={
            'or': [
                {
                    'property': 'Status',
                    'select': {'equals': 'Current Project'},
                },
                {'property': 'Status', 'select': {'equals': 'Recurring'}},
            ],
        },
    )
    entries = [ProjectEntry.from_page(p) for p in pages]
    entries = [
        e
        for e in entries
        if not e.follow_up_date or e.follow_up_date <= today_str
    ]
    context = request.args.get('context')
    if context:
        context = unquote_plus(context)
        entries = [e for e in entries if e.context == context]
    exclude_these = [
        'created_date',
        'list_category',
        'status',
        'success_condition',
        'updated_date',
    ]
    for entry in entries:
        entry.next_step = entry.next_step.split('\n')[0].replace('1. ', '')
    entries.sort(key=lambda e: (e.context or '\xff', e.header.lower()))
    entries.sort(
        key=lambda e: (
            e.follow_up_date or '9999-99-99',
            e.due_date or '9999-99-99',
        ),
    )
    return jsonify([_entry_dict(e, exclude_these) for e in entries])


@app.get('/triage-schema')
@require_auth
def triage_schema() -> Any:
    """Get schema for triage workflow: statuses and contexts per status."""
    available_contexts = get_contexts()
    list_categories = load_list_categories(DEFAULT_LIST_CATEGORIES)

    schema = {
        'statuses': TRIAGE_STATUSES,
        'contexts_by_status': {
            'Current Project': sorted(available_contexts),
            'Recurring': sorted(available_contexts),
            'Waiting For': sorted(available_contexts),
            'Someday/Maybe': sorted(available_contexts),
            'List': sorted(list_categories),
        },
        'list_categories': sorted(list_categories),
    }
    return jsonify(schema)


@app.post('/triage/<page_id>')
@require_auth
def triage(page_id: str) -> Any:  # noqa: PLR0911
    """Atomically triage an entry with full data.

    Request body:
    {
        "status": "Current Project" | "Waiting For" | "Someday/Maybe" |
                  "List" | "Recurring" | "Delete",
        "context": "Work" | "Home" | ...,
        "list_category": "Books to Read" | ...,
        "next_step": "...",
        "success_condition": "...",
        "due_date": "2026-08-01" or null,
        "follow_up_date": "2026-08-05" or null
    }

    Returns: updated ProjectEntry or error
    """
    from gtd.notion.client import archive_page

    body = request.get_json(force=True) or {}
    status = body.get('status', '').strip()
    context = body.get('context', '').strip()
    list_category = body.get('list_category', '').strip()
    next_step = body.get('next_step', '').strip()
    success_condition = body.get('success_condition', '').strip()
    due_date_str = (
        body.get('due_date', '').strip() if body.get('due_date') else None
    )
    follow_up_str = (
        body.get('follow_up_date', '').strip()
        if body.get('follow_up_date')
        else None
    )

    # Get the entry to verify it exists
    page_data = _get_page_by_id(page_id)
    if not page_data:
        return jsonify(error=f'Entry {page_id} not found'), 404

    # Handle Delete
    if status == 'Delete':
        try:
            archive_page(page_id)
            result = jsonify(deleted=True), 200
        except (ValueError, RuntimeError, OSError) as err:
            result = jsonify(error=f'Delete failed: {err}'), 500
        return result

    # Validate status
    error = _validate_triage_status(status)
    if error:
        return error

    # Validate and set context/list_category
    context_result = _validate_and_set_context_or_list(
        status, context, list_category
    )
    if isinstance(context_result[0], dict) and context_result[1] is not None:
        return context_result

    kwargs: dict[str, str] = context_result[0]  # type: ignore[assignment]
    if not status:
        return jsonify(error='status is required'), 400
    kwargs['status'] = status

    # Set optional fields
    if next_step:
        kwargs['next_step'] = next_step
    if success_condition:
        kwargs['success_condition'] = success_condition

    # Parse dates
    dates_result = _parse_triage_dates(due_date_str, follow_up_str)
    if dates_result[1] is not None:  # Error case
        return dates_result
    kwargs.update(dates_result[0])

    # Apply updates and return result
    return _apply_triage_updates(page_id, kwargs)


# endregion
