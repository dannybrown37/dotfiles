"""Thin Flask wrapper around GTD Notion operations for iOS Shortcuts."""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timedelta, date
from functools import wraps
from typing import Any, TYPE_CHECKING
from urllib.parse import unquote_plus

if TYPE_CHECKING:
    from collections.abc import Callable

from flask import Flask, jsonify, request

from gtd.notion.capture import _create_page
from gtd.notion.client import (
    archive_page,
    build_property_update,
    get_list_categories,
    query_database,
    update_page,
)
from gtd.notion.entries import _get_today_entries, _parse_date_input
from gtd.notion.models import ProjectEntry
from gtd.notion.schema import STATUSES

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


@app.get('/list-categories')
@require_auth
def list_categories() -> Any:
    return jsonify(list_categories=get_list_categories())


@app.post('/done/<page_id>')
@require_auth
def done(page_id: str) -> Any:
    archive_page(page_id)
    return jsonify(page_id=page_id, status='archived')


@app.patch('/entry/<page_id>')
@require_auth
def update_entry(page_id: str) -> Any:
    body = request.get_json(force=True, silent=True) or {}
    status = body.get('status')
    if status and status not in STATUSES:
        return jsonify(
            error=f'Invalid status. Must be one of: {STATUSES}'
        ), 400
    fields = (
        'status',
        'context',
        'list_category',
        'next_step',
        'due_date',
        'follow_up_date',
    )
    kwargs = {k: body[k] for k in fields if body.get(k) is not None}
    if not kwargs:
        return jsonify(error='No fields provided'), 400
    update_page(page_id, build_property_update(**kwargs))
    return jsonify(page_id=page_id, updated=kwargs)


@app.get('/inbox')
@require_auth
def inbox() -> Any:
    pages = query_database(
        filter_obj={'property': 'Status', 'select': {'equals': 'Triage'}},
    )
    return jsonify([_entry_dict(ProjectEntry.from_page(p)) for p in pages])


@app.get('/next-steps')
@require_auth
def next_steps() -> Any:
    pages = query_database(
        filter_obj={
            'property': 'Status',
            'select': {'equals': 'Current Project'},
        },
    )
    entries = [ProjectEntry.from_page(p) for p in pages]
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


@app.post('/snooze/<page_id>')
@require_auth
def snooze(page_id: str) -> Any:
    body = request.get_json(force=True, silent=True) or {}
    until = body.get('until')
    days = body.get('days', 1)
    if until:
        date = _parse_date_input(until)
        if not date:
            return jsonify(error=f'Could not parse date: {until!r}'), 400
    else:
        date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    update_page(page_id, build_property_update(follow_up_date=date))
    return jsonify(page_id=page_id, follow_up_date=date)


@app.get('/statuses')
@require_auth
def statuses() -> Any:
    return jsonify(STATUSES)


@app.get('/today')
@require_auth
def today() -> Any:
    return jsonify([_entry_dict(e) for e in _get_today_entries()])


# endregion
