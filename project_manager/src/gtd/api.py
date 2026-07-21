"""Thin Flask wrapper around GTD Notion operations for iOS Shortcuts."""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import date
from functools import wraps
from typing import Any, TYPE_CHECKING
from urllib.parse import unquote_plus
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from collections.abc import Callable

from flask import Flask, jsonify, request

from gtd.notion.capture import _create_page
from gtd.notion.client import (
    query_database,
)
from gtd.notion.models import ProjectEntry

app = Flask(__name__)


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
    return {k: v for k, v in asdict(e).items() if k not in excluded}


# region Endpoints

# Endpoint definitions should be alphabetical


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
    today_str = date.today().isoformat()
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
    today_str = date.today(tz=ZoneInfo('America/New_York')).isoformat()
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


# endregion
