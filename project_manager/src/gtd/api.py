"""Thin FastAPI wrapper around GTD Notion operations for iOS Shortcuts."""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from gtd.notion.capture import _create_page
from gtd.notion.client import archive_page, build_property_update, update_page
from gtd.notion.entries import _get_today_entries, _parse_date_input
from gtd.notion.models import ProjectEntry
from gtd.notion.client import query_database
from gtd.notion.schema import STATUSES

app = FastAPI(title='GTD API', docs_url='/docs')
_bearer = HTTPBearer()


def _require_auth(
    creds: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
) -> None:
    expected = os.environ.get('GTD_API_KEY')
    if not expected:
        raise HTTPException(500, 'GTD_API_KEY not set on server')
    if creds.credentials != expected:
        raise HTTPException(401, 'Invalid API key')


Auth = Annotated[None, Depends(_require_auth)]


def _entry_dict(e: ProjectEntry) -> dict:
    return asdict(e)


# ── Capture ──────────────────────────────────────────────────────────────────


class CaptureRequest(BaseModel):
    header: str


@app.post('/capture', status_code=201)
def capture(_: Auth, body: CaptureRequest) -> dict:
    """Add an item to the GTD inbox (Triage status)."""
    page = _create_page(body.header.strip())
    return {'page_id': page['id'], 'header': body.header.strip()}


# ── Today ────────────────────────────────────────────────────────────────────


@app.get('/today')
def today(_: Auth) -> list[dict]:
    """Return today's actionable entries."""
    return [_entry_dict(e) for e in _get_today_entries()]


# ── Inbox ────────────────────────────────────────────────────────────────────


@app.get('/inbox')
def inbox(_: Auth) -> list[dict]:
    """Return all entries with Triage status."""
    pages = query_database(
        filter_obj={'property': 'Status', 'select': {'equals': 'Triage'}}
    )
    return [_entry_dict(ProjectEntry.from_page(p)) for p in pages]


# ── Done ─────────────────────────────────────────────────────────────────────


@app.post('/done/{page_id}')
def done(_: Auth, page_id: str) -> dict:
    """Archive (complete) an entry."""
    archive_page(page_id)
    return {'page_id': page_id, 'status': 'archived'}


# ── Snooze ───────────────────────────────────────────────────────────────────


class SnoozeRequest(BaseModel):
    days: int = 1
    until: str | None = None  # YYYY-MM-DD or natural language


@app.post('/snooze/{page_id}')
def snooze(_: Auth, page_id: str, body: SnoozeRequest) -> dict:
    """Set a follow-up date, pushing the entry out of today's view."""
    if body.until:
        date = _parse_date_input(body.until)
        if not date:
            raise HTTPException(400, f'Could not parse date: {body.until!r}')
    else:
        date = (datetime.now() + timedelta(days=body.days)).strftime(
            '%Y-%m-%d'
        )
    update_page(page_id, build_property_update(follow_up_date=date))
    return {'page_id': page_id, 'follow_up_date': date}


# ── Update status / fields ───────────────────────────────────────────────────


class UpdateRequest(BaseModel):
    status: str | None = None
    context: str | None = None
    next_step: str | None = None
    due_date: str | None = None
    follow_up_date: str | None = None


@app.patch('/entry/{page_id}')
def update_entry(_: Auth, page_id: str, body: UpdateRequest) -> dict:
    """Update one or more fields on an entry."""
    if body.status and body.status not in STATUSES:
        raise HTTPException(400, f'Invalid status. Must be one of: {STATUSES}')
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(400, 'No fields provided')
    update_page(page_id, build_property_update(**kwargs))
    return {'page_id': page_id, 'updated': kwargs}


# ── Meta ─────────────────────────────────────────────────────────────────────


@app.get('/statuses')
def statuses(_: Auth) -> list[str]:
    """List valid GTD statuses."""
    return STATUSES
