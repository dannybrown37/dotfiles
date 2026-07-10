"""Unified GTD + Goals TUI."""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import (
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    Static,
    TabbedContent,
    TabPane,
    Tabs,
)

from gtd.models import Goal, Tactic, Update
from gtd.notion.models import ProjectEntry
from gtd.notion.schema import STATUSES, STATUS_ICONS
from gtd.tui import (
    ConfirmModal,
    GoalsContent,
    InputModal,
    SelectModal,
    TwoFieldModal,
    VimListView,
)


# ── Entry renderers ──────────────────────────────────────────────────────────


def _render_entry_detail(entry: ProjectEntry, notes: str | None = None) -> str:
    icon = STATUS_ICONS.get(entry.status, '·')
    lines = [
        f'{icon} [bold cyan]{entry.header.strip()}[/bold cyan]',
        '',
    ]

    def row(label: str, value: str, color: str = '') -> str:
        padded = f'{label}:'.ljust(12)
        if not value:
            return f'  [dim]{padded} (none)[/dim]'
        val = f'[{color}]{value}[/{color}]' if color else value
        return f'  [dim]{padded}[/dim] {val}'

    lines.append(row('Status', entry.status))
    lines.append(row('Context', entry.context))
    lines.append(row('Next step', entry.next_step))
    if entry.due_date:
        lines.append(row('Due', entry.due_date, 'yellow'))
    if entry.follow_up_date:
        lines.append(row('Follow-up', entry.follow_up_date, 'dim'))

    lines.append('')
    if notes is None:
        lines.append('[dim]Loading notes...[/dim]')
    elif notes.strip():
        lines.append('[dim]── Notes ──[/dim]')
        for line in notes.split('\n'):
            lines.append(f'  {line}' if line.strip() else '')
    else:
        lines.append('[dim]No notes.[/dim]')

    return '\n'.join(lines)


def _render_entry_summary(entry: ProjectEntry) -> str:
    icon = STATUS_ICONS.get(entry.status, '·')
    ctx = f'  [dim][{entry.context}][/dim]' if entry.context else ''
    due = ''
    if entry.due_date:
        try:
            d = datetime.fromisoformat(entry.due_date)
            due = f'  [yellow]{d:%b %-d}[/yellow]'
        except ValueError:
            due = f'  [yellow]{entry.due_date}[/yellow]'
    next_step = (
        f'\n  [dim]→ {entry.next_step}[/dim]' if entry.next_step else ''
    )
    return f'{icon} {entry.header.strip()}{ctx}{due}{next_step}'


# ── Tactic cadence helpers ───────────────────────────────────────────────────


def _parse_cadence_per_week(cadence: str) -> int:
    """Parse reminder_cadence string into times-per-week count."""
    c = cadence.lower().strip()
    if c in ('daily', 'every day'):
        return 7
    m = re.match(r'(\d+)x', c)
    if m:
        return int(m.group(1))
    return 1


_DAILY_CADENCE = 7  # sentinel: cadence that means "every day"
_SPRINT_DAYS = 14  # sprint = one update per 2-week window


def _is_sprint_cadence(cadence: str) -> bool:
    return cadence.lower().strip() == 'sprint'


def _week_start_iso() -> str:
    today = datetime.now().date()
    return (today - timedelta(days=today.weekday())).isoformat()


def _sprint_start_iso() -> str:
    return (
        datetime.now().date() - timedelta(days=_SPRINT_DAYS - 1)
    ).isoformat()


def _count_updates_this_week(tactic: Tactic) -> int:
    ws = _week_start_iso()
    return sum(1 for u in tactic.updates if u.date >= ws)


def _updated_in_sprint(tactic: Tactic) -> bool:
    return any(u.date >= _sprint_start_iso() for u in tactic.updates)


def _updated_today(tactic: Tactic) -> bool:
    today = datetime.now().date().isoformat()
    return any(u.date == today for u in tactic.updates)


def _tactic_is_due(tactic: Tactic) -> bool:
    if _is_sprint_cadence(tactic.reminder_cadence):
        return not _updated_in_sprint(tactic)
    per_week = _parse_cadence_per_week(tactic.reminder_cadence)
    if per_week >= _DAILY_CADENCE:
        return not _updated_today(tactic)
    return _count_updates_this_week(tactic) < per_week


def _tactic_sort_key(tactic: Tactic) -> int:
    """0 = overdue, 1 = partial, 2 = done — for sorting due items first."""
    if _is_sprint_cadence(tactic.reminder_cadence):
        return 0 if not _updated_in_sprint(tactic) else 2
    per_week = _parse_cadence_per_week(tactic.reminder_cadence)
    if per_week >= _DAILY_CADENCE:
        return 0 if not _updated_today(tactic) else 2
    n = _count_updates_this_week(tactic)
    if n == 0:
        return 0
    return 1 if n < per_week else 2


def _tactic_status_line(tactic: Tactic) -> str:
    """One-line due/done status for the detail pane."""
    if _is_sprint_cadence(tactic.reminder_cadence):
        if _updated_in_sprint(tactic):
            return '[green]✓ Logged this sprint[/green]'
        return '[bold red]⚠ Due this sprint[/bold red]'
    per_week = _parse_cadence_per_week(tactic.reminder_cadence)
    if per_week >= _DAILY_CADENCE:
        return (
            '[green]✓ Done today[/green]'
            if _updated_today(tactic)
            else '[bold red]⚠ Due today[/bold red]'
        )
    n = _count_updates_this_week(tactic)
    if n >= per_week:
        return f'[green]✓ Done this week ({n}/{per_week})[/green]'
    if n > 0:
        return f'[yellow]◑ In progress this week ({n}/{per_week})[/yellow]'
    return f'[bold red]⚠ Due this week (0/{per_week})[/bold red]'


def _render_tactic_detail(
    goal_name: str, tactic: Tactic, goal: Goal | None
) -> str:
    lines: list[str] = [f'[bold cyan]{goal_name}[/bold cyan]']
    if goal:
        week = goal.current_week()
        bar = goal.progress_bar()
        lines.append(f'[dim]Week {week}/12  {bar}[/dim]')
    lines += ['', f'[bold]{tactic.description}[/bold]']
    lines.append(f'Cadence: [dim]{tactic.reminder_cadence}[/dim]')
    lines.append('')
    lines.append(_tactic_status_line(tactic))

    recent = sorted(tactic.updates, key=lambda u: u.date, reverse=True)[:5]
    if recent:
        lines += ['', '[dim]── Recent updates ──[/dim]']
        today_iso = datetime.now().date().isoformat()
        for u in recent:
            try:
                d = datetime.fromisoformat(u.date)
                date_str = 'Today' if u.date == today_iso else f'{d:%b %-d}'
            except ValueError:
                date_str = u.date
            lines.append(f'  [dim]{date_str}[/dim]  {u.note}')
    else:
        lines += ['', '[dim]No updates yet. Press N to log one.[/dim]']

    return '\n'.join(lines)


# ── Weekly habit helpers ─────────────────────────────────────────────────────

WEEKLY_HABITS: list[tuple[str, str]] = [
    ('weekly_review', 'Weekly Review'),
    ('goal_scoring', 'Score Goals'),
]

_GTD_REVIEW_CHECKLIST = """\
  □ Process all inboxes to zero
  □ Review Projects list & next actions
  □ Review Waiting For list
  □ Review Someday/Maybe list
  □ Review calendar (past & upcoming)
  □ Check 12-Week Goals progress"""

_GOAL_SCORING_HINT = """\
  Navigate to the Goals tab (right) and press S on each goal.
  Score 1-10 for how well you executed each tactic this week."""


def _habit_done_this_week(key: str) -> bool:
    from gtd.storage import get_weekly_habit_date  # noqa: PLC0415

    last = get_weekly_habit_date(key)
    if not last:
        return False
    return last >= _week_start_iso()


def _render_habit_detail(key: str, label: str) -> str:
    from gtd.storage import get_weekly_habit_date  # noqa: PLC0415
    from gtd.storage import get_stored_goal_names, load_goal  # noqa: PLC0415

    last = get_weekly_habit_date(key)
    if last:
        try:
            d = datetime.fromisoformat(last)
            days_ago = (datetime.now().date() - d.date()).days
            last_str = (
                'today' if days_ago == 0 else f'{d:%b %-d} ({days_ago}d ago)'
            )
        except ValueError:
            last_str = last
    else:
        last_str = 'never'

    done = _habit_done_this_week(key)
    if done:
        status = '[green]✓ Done this week[/green]'
    else:
        status = '[bold red]⚠ Not done this week[/bold red]'

    lines = [
        f'[bold red]● {label}[/bold red]'
        if not done
        else f'[dim]✓ {label}[/dim]',
        '',
        f'{status}   [dim]last: {last_str}[/dim]',
        '',
    ]

    if key == 'weekly_review':
        lines += [
            '[dim]── GTD Weekly Review checklist ──[/dim]',
            _GTD_REVIEW_CHECKLIST,
        ]
    elif key == 'goal_scoring':
        goals = [
            load_goal(n)
            for n in get_stored_goal_names()
            if not load_goal(n).is_complete
        ]
        if goals:
            lines.append('[dim]── Goals to score ──[/dim]')
            for g in goals:
                week = g.current_week()
                scored = str(week) in (
                    g.tactics[0].weekly_scores if g.tactics else {}
                )
                mark = '[green]✓[/green]' if scored else '[red]·[/red]'
                lines.append(f'  {mark} {g.name}  [dim]Week {week}[/dim]')
            lines += ['', _GOAL_SCORING_HINT]

    if not done:
        lines += ['', '[dim]Press X to mark done for this week.[/dim]']

    return '\n'.join(lines)


# ── List item widgets ────────────────────────────────────────────────────────


class EntryListItem(ListItem):
    def __init__(self, entry: ProjectEntry) -> None:
        super().__init__()
        self.page_id = entry.page_id
        icon = STATUS_ICONS.get(entry.status, '·')
        ctx = f' [{entry.context}]' if entry.context else ''
        self._text = f'{icon} {entry.header.strip()}{ctx}'

    def compose(self) -> ComposeResult:
        yield Label(self._text)


class WeeklyHabitItem(ListItem):
    def __init__(self, key: str, label: str) -> None:
        super().__init__()
        self.habit_key = key
        self.habit_label = label

    def compose(self) -> ComposeResult:
        yield Label(
            f'[bold red]●[/bold red] {self.habit_label}'
            f'  [dim]not done this week[/dim]',
            markup=True,
        )


class TacticListItem(ListItem):
    def __init__(self, goal_name: str, tactic: Tactic) -> None:
        super().__init__()
        self.goal_name = goal_name
        self.tactic = tactic

    @property
    def tactic_description(self) -> str:
        return self.tactic.description

    @property
    def cadence(self) -> str:
        return self.tactic.reminder_cadence

    def _build_label(self) -> str:
        desc = self.tactic.description
        cad = self.tactic.reminder_cadence
        done = not _tactic_is_due(self.tactic)
        per_week = _parse_cadence_per_week(cad)
        n = _count_updates_this_week(self.tactic)
        is_partial = (
            not _is_sprint_cadence(cad)
            and per_week < _DAILY_CADENCE
            and 0 < n < per_week
        )
        if done:
            return f'[dim]✓ {desc}  {cad}[/dim]'
        if is_partial:
            return (
                f'[yellow]◑[/yellow] {desc}  [dim]{cad} · {n}/{per_week}[/dim]'
            )
        return f'[bold red]●[/bold red] {desc}  [dim]{cad}[/dim]'

    def compose(self) -> ComposeResult:
        yield Label(self._build_label(), markup=True)

    def refresh_display(self, tactic: Tactic) -> None:
        """Update visual after tactic data changes."""
        self.tactic = tactic
        self.query_one(Label).update(self._build_label())


class SeparatorListItem(ListItem):
    def __init__(self, label: str) -> None:
        super().__init__(disabled=True)
        self._label = label

    def compose(self) -> ComposeResult:
        yield Label(f'[dim]── {self._label} ──[/dim]', markup=True)


class DetailPane(ScrollableContainer):
    """Scrollable detail pane — not focusable via Tab."""

    can_focus = False


# ── Shared action helpers ────────────────────────────────────────────────────


async def _prompt_and_get_props(
    app: App,
    entry: ProjectEntry,
    choice: str,
) -> dict | None:
    """Prompt for a field value; return kwargs for build_property_update."""
    from gtd.notion.client import get_select_options  # noqa: PLC0415
    from gtd.notion.entries import _parse_date_input  # noqa: PLC0415

    loop = asyncio.get_running_loop()
    props: dict | None = None

    if choice == 'Name':
        value = await app.push_screen_wait(
            InputModal('Update Name', initial=entry.header.strip())
        )
        props = {'name': value} if value else None
    elif choice == 'Status':
        value = await app.push_screen_wait(SelectModal('Status', STATUSES))
        props = {'status': value} if value else None
    elif choice == 'Context':
        contexts = await loop.run_in_executor(
            None, get_select_options, 'Context'
        )
        value = await app.push_screen_wait(SelectModal('Context', contexts))
        props = {'context': value} if value else None
    elif choice == 'Next actionable step':
        value = await app.push_screen_wait(
            InputModal('Next Actionable Step', initial=entry.next_step)
        )
        props = {'next_step': value} if value is not None else None
    elif choice in ('Follow-up date', 'Due date'):
        value = await app.push_screen_wait(
            InputModal(choice, 'e.g. Monday, Jul 15, blank to clear')
        )
        if value is not None:
            date = _parse_date_input(value) if value else ''
            key = (
                'follow_up_date' if choice == 'Follow-up date' else 'due_date'
            )
            props = {key: date}

    return props


async def _shared_update_entry(
    app: App,
    entry: ProjectEntry,
    refresh_cb: Callable[[], None],
) -> None:
    """Update entry fields — shared across tab widgets."""
    from gtd.notion.client import build_property_update, update_page  # noqa: PLC0415

    fields = [
        'Name',
        'Status',
        'Context',
        'Next actionable step',
        'Follow-up date',
        'Due date',
    ]
    choice = await app.push_screen_wait(
        SelectModal('Update which field?', fields)
    )
    if not choice:
        return

    props = await _prompt_and_get_props(app, entry, choice)
    if props is None:
        return

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, update_page, entry.page_id, build_property_update(**props)
    )
    refresh_cb()
    app.notify(f'✓ "{entry.header.strip()}" updated')


async def _shared_edit_notes(
    app: App,
    entry: ProjectEntry,
    notes_cache: dict[str, str],
    refresh_cb: Callable[[], None],
) -> None:
    """Open nvim to edit notes — shared across tab widgets."""
    from gtd.notion.client import get_page_body, replace_page_body  # noqa: PLC0415

    loop = asyncio.get_running_loop()
    body = await loop.run_in_executor(None, get_page_body, entry.page_id)
    fd, tmp_path = tempfile.mkstemp(suffix='.md')
    with open(fd, 'w') as f:  # noqa: PTH123
        f.write(body)
    editor = os.environ.get('EDITOR', 'nvim')
    with app.suspend():
        subprocess.run([editor, tmp_path], check=False)  # noqa: S603

    new_body = Path(tmp_path).read_text()
    Path(tmp_path).unlink(missing_ok=True)
    if new_body != body:
        await loop.run_in_executor(
            None, replace_page_body, entry.page_id, new_body
        )
        notes_cache[entry.page_id] = new_body
        app.notify('Notes saved')
        refresh_cb()


async def _shared_log_and_reschedule(
    app: App,
    entry: ProjectEntry,
    notes_cache: dict[str, str],
) -> str | None:
    """Open editor, save notes, prompt/infer next follow-up.

    Returns the new follow-up date string, or None if cancelled.
    """
    from gtd.notion.client import (  # noqa: PLC0415
        get_page_body,
        replace_page_body,
    )

    loop = asyncio.get_running_loop()
    try:
        body = await loop.run_in_executor(None, get_page_body, entry.page_id)
    except Exception as e:
        app.notify(f'Error: {e}', severity='error')
        return None

    fd, tmp_path = tempfile.mkstemp(suffix='.md')
    with open(fd, 'w') as f:  # noqa: PTH123
        f.write(body)
    editor = os.environ.get('EDITOR', 'nvim')
    with app.suspend():
        subprocess.run([editor, tmp_path], check=False)  # noqa: S603

    new_body = Path(tmp_path).read_text()
    Path(tmp_path).unlink(missing_ok=True)
    if new_body != body:
        await loop.run_in_executor(
            None, replace_page_body, entry.page_id, new_body
        )
        notes_cache[entry.page_id] = new_body
        app.notify('Notes saved')

    from gtd.notion.log import _infer_reschedule_days  # noqa: PLC0415

    inferred = _infer_reschedule_days(entry.header)
    if inferred:
        next_date = (datetime.now() + timedelta(days=inferred)).strftime(
            '%Y-%m-%d'
        )
    else:
        date_str = await app.push_screen_wait(
            InputModal('Reschedule to', 'e.g. tomorrow, Monday, Jul 15')
        )
        if not date_str:
            return None
        from gtd.notion.entries import _parse_date_input  # noqa: PLC0415

        next_date = _parse_date_input(date_str)
        if not next_date:
            app.notify('Could not parse date', severity='warning')
            return None

    from gtd.notion.client import build_property_update, update_page  # noqa: PLC0415

    await loop.run_in_executor(
        None,
        update_page,
        entry.page_id,
        build_property_update(follow_up_date=next_date),
    )
    return next_date


# ── Base entry content ───────────────────────────────────────────────────────


class BaseEntryContent(Vertical):
    """Shared two-pane infrastructure for all entry tab widgets."""

    TITLE: ClassVar[str] = ''
    EMPTY_MSG: ClassVar[str] = 'Nothing here.'

    DEFAULT_CSS = """
    BaseEntryContent { layout: horizontal; height: 1fr; }
    BaseEntryContent #entry-list-pane {
        width: 44;
        border-right: solid $panel;
    }
    BaseEntryContent #entry-list-header {
        background: $panel;
        padding: 0 1;
        height: 1;
        text-style: bold;
    }
    BaseEntryContent #entry-list { height: 1fr; }
    BaseEntryContent #entry-detail-pane { width: 1fr; padding: 1 2; }
    BaseEntryContent LoadingIndicator { height: 3; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[ProjectEntry] = []
        self._notes: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id='entry-list-pane'):
            yield Static(self.TITLE, id='entry-list-header')
            yield LoadingIndicator(id='entry-loading')
            yield VimListView(id='entry-list')
        with DetailPane(id='entry-detail-pane'):
            yield Static('', id='entry-detail', markup=True)

    def on_mount(self) -> None:
        self._load_entries()

    def _build_filter(self) -> dict:
        raise NotImplementedError

    @work(thread=True)
    def _load_entries(self) -> None:
        from gtd.notion.client import query_database  # noqa: PLC0415

        try:
            pages = query_database(filter_obj=self._build_filter())
            entries = [ProjectEntry.from_page(p) for p in pages]
            self.app.call_from_thread(self._set_entries, entries)
        except Exception as e:
            msg = f'Notion error: {e}'
            self.app.call_from_thread(
                lambda: self.app.notify(msg, severity='error')
            )
            self.app.call_from_thread(self._set_entries, [])

    def _set_entries(self, entries: list[ProjectEntry]) -> None:
        self._entries = entries
        with contextlib.suppress(Exception):
            self.query_one('#entry-loading', LoadingIndicator).display = False
        lv = self.query_one('#entry-list', VimListView)
        lv.clear()
        for entry in entries:
            lv.append(EntryListItem(entry))
        header = self.query_one('#entry-list-header', Static)
        detail = self.query_one('#entry-detail', Static)
        if not entries:
            header.update(f'{self.TITLE} — empty')
            detail.update(f'[dim]{self.EMPTY_MSG}[/dim]')
        else:
            header.update(f'{self.TITLE}  [dim]({len(entries)})[/dim]')
            lv.index = 0
            self._update_detail()

    @on(ListView.Highlighted, '#entry-list')
    def on_list_highlighted(self) -> None:
        self._update_detail()

    def _current_entry(self) -> ProjectEntry | None:
        idx = self.query_one('#entry-list', VimListView).index
        if idx is None or idx >= len(self._entries):
            return None
        return self._entries[idx]

    def _update_detail(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        notes = self._notes.get(entry.page_id)
        self.query_one('#entry-detail', Static).update(
            _render_entry_detail(entry, notes)
        )
        if entry.page_id not in self._notes:
            self._load_notes(entry.page_id)

    @work(thread=True, exclusive=True)
    def _load_notes(self, page_id: str) -> None:
        from gtd.notion.client import get_page_body  # noqa: PLC0415

        try:
            body = get_page_body(page_id)
        except Exception:
            body = ''
        self._notes[page_id] = body
        self.app.call_from_thread(self._maybe_refresh_detail, page_id)

    def _maybe_refresh_detail(self, page_id: str) -> None:
        entry = self._current_entry()
        if entry and entry.page_id == page_id:
            self._update_detail()

    def _remove_entry(self, page_id: str) -> None:
        self._entries = [e for e in self._entries if e.page_id != page_id]
        self._set_entries(self._entries)

    def action_refresh(self) -> None:
        self._entries = []
        self._notes = {}
        with contextlib.suppress(Exception):
            self.query_one('#entry-loading', LoadingIndicator).display = True
        self.query_one('#entry-list', VimListView).clear()
        self.query_one('#entry-detail', Static).update('')
        self._load_entries()

    @work
    async def action_update_entry(self) -> None:
        entry = self._current_entry()
        if entry:
            await _shared_update_entry(self.app, entry, self._load_entries)

    @work
    async def action_edit_notes(self) -> None:
        entry = self._current_entry()
        if entry:
            await _shared_edit_notes(
                self.app, entry, self._notes, self._update_detail
            )

    @work
    async def action_mark_done(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        from gtd.notion.log import _is_recurring  # noqa: PLC0415

        if _is_recurring(entry):
            choice = await self.app.push_screen_wait(
                SelectModal(
                    f'⚠ "{entry.header.strip()}" is recurring',
                    ['Reschedule', 'Permanently complete'],
                )
            )
            if choice == 'Reschedule':
                next_date = await _shared_log_and_reschedule(
                    self.app, entry, self._notes
                )
                if next_date:
                    self._remove_entry(entry.page_id)
                    self.app.notify(
                        f'✓ "{entry.header.strip()}" → {next_date}'
                    )
                return
            if choice != 'Permanently complete':
                return
            confirmed = await self.app.push_screen_wait(
                ConfirmModal(
                    f'⚠ Permanently complete "{entry.header.strip()}"?'
                )
            )
        else:
            confirmed = await self.app.push_screen_wait(
                ConfirmModal(f'Mark done: "{entry.header.strip()}"?')
            )
        if not confirmed:
            return
        self._done_worker(entry.page_id)
        self._remove_entry(entry.page_id)
        self.app.notify(f'✓ "{entry.header.strip()}" → done')

    @work(thread=True)
    def _done_worker(self, page_id: str) -> None:
        from gtd.notion.client import archive_page  # noqa: PLC0415

        archive_page(page_id)

    @work
    async def action_log_and_reschedule(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        next_date = await _shared_log_and_reschedule(
            self.app, entry, self._notes
        )
        if next_date:
            self._update_detail()
            self.app.notify(f'✓ "{entry.header.strip()}" → {next_date}')

    @work
    async def action_drop_entry(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmModal(f'Drop: "{entry.header.strip()}"?')
        )
        if not confirmed:
            return
        self._drop_worker(entry.page_id)
        self._remove_entry(entry.page_id)
        self.app.notify(f'✓ Dropped "{entry.header.strip()}"')

    @work(thread=True)
    def _drop_worker(self, page_id: str) -> None:
        from gtd.notion.client import archive_page  # noqa: PLC0415

        archive_page(page_id)

    async def action_activate(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        self._activate_worker(entry.page_id)
        self._remove_entry(entry.page_id)
        self.app.notify(f'✓ "{entry.header.strip()}" → Current Project')

    @work(thread=True)
    def _activate_worker(self, page_id: str) -> None:
        from gtd.notion.client import build_property_update, update_page  # noqa: PLC0415

        update_page(page_id, build_property_update(status='Current Project'))

    async def action_move_someday(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        self._someday_worker(entry.page_id)
        self._remove_entry(entry.page_id)
        self.app.notify(f'✓ "{entry.header.strip()}" → Someday/Maybe')

    @work(thread=True)
    def _someday_worker(self, page_id: str) -> None:
        from gtd.notion.client import build_property_update, update_page  # noqa: PLC0415

        update_page(page_id, build_property_update(status='Someday/Maybe'))

    @work
    async def action_capture(self) -> None:
        header = await self.app.push_screen_wait(
            InputModal('Capture to Inbox', 'What needs capturing?')
        )
        if not header:
            return
        self._capture_worker(header)
        self.app.notify(f'✓ Captured: "{header}" → Triage')

    @work(thread=True)
    def _capture_worker(self, header: str) -> None:
        from gtd.notion.capture import _create_page  # noqa: PLC0415

        _create_page(header)


# ── Today content ────────────────────────────────────────────────────────────


class TodayContent(BaseEntryContent):
    """Today's actionable items — the GTD daily driver."""

    TITLE: ClassVar[str] = 'Today'
    EMPTY_MSG: ClassVar[str] = 'All clear. Nice work.'

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('W', 'complete_habit', 'Score Week'),
        Binding('L', 'log', 'Log'),
        Binding('S', 'snooze', 'Snooze'),
        Binding('W', 'waiting_for', 'Waiting For'),
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'mark_done', 'Done'),
        Binding('N', 'log_tactic', 'Log update'),
        Binding('U', 'unlog_tactic', 'Unlog last'),
    ]

    _GTD_ACTIONS: ClassVar[set[str]] = {
        'log',
        'snooze',
        'waiting_for',
        'update_entry',
        'edit_notes',
        'mark_done',
    }
    _TACTIC_ACTIONS: ClassVar[set[str]] = {'log_tactic', 'unlog_tactic'}
    _HABIT_ACTIONS: ClassVar[set[str]] = {'complete_habit'}

    def __init__(self) -> None:
        super().__init__()
        self._tactic_items: list[TacticListItem] = []
        self._habit_items: list[WeeklyHabitItem] = []
        self._goals: dict[str, Goal] = {}

    def _build_filter(self) -> dict:
        return {}

    @work(thread=True)
    def _load_entries(self) -> None:
        from gtd.notion.entries import _get_today_entries  # noqa: PLC0415

        try:
            entries = _get_today_entries()
            self.app.call_from_thread(self._set_entries, entries)
        except Exception as e:
            msg = f'Notion error: {e}'
            self.app.call_from_thread(
                lambda: self.app.notify(msg, severity='error')
            )
            self.app.call_from_thread(self._set_entries, [])

    def _populate_list(
        self,
        lv: VimListView,
        entries: list[ProjectEntry],
        goals_with_tactics: list[tuple[Goal, list[TacticListItem]]],
    ) -> None:
        lv.clear()
        for item in self._habit_items:
            lv.append(item)
        if self._habit_items and entries:
            lv.append(SeparatorListItem('GTD'))
        for entry in entries:
            lv.append(EntryListItem(entry))
        if not goals_with_tactics:
            return
        total_due = sum(
            1 for i in self._tactic_items if _tactic_is_due(i.tactic)
        )
        header_sep = '12-Week Goals'
        if total_due:
            header_sep += f' ({total_due} due)'
        lv.append(SeparatorListItem(header_sep))
        for goal, items in goals_with_tactics:
            due = sum(1 for i in items if _tactic_is_due(i.tactic))
            goal_label = f'  {goal.name}'
            if due:
                goal_label += f'  [red]{due} due[/red]'
            lv.append(SeparatorListItem(goal_label))
            for item in items:
                lv.append(item)

    def _set_entries(self, entries: list[ProjectEntry]) -> None:
        self._entries = entries
        with contextlib.suppress(Exception):
            self.query_one('#entry-loading', LoadingIndicator).display = False

        from gtd.storage import get_stored_goal_names, load_goal  # noqa: PLC0415

        self._habit_items = [
            WeeklyHabitItem(key, label)
            for key, label in WEEKLY_HABITS
            if not _habit_done_this_week(key)
        ]

        self._goals = {}
        goals_with_tactics: list[tuple[Goal, list[TacticListItem]]] = []
        for name in get_stored_goal_names():
            goal = load_goal(name)
            if goal.is_complete or not goal.tactics:
                continue
            self._goals[goal.name] = goal
            items = [TacticListItem(goal.name, t) for t in goal.tactics]
            items.sort(key=lambda i: _tactic_sort_key(i.tactic))
            goals_with_tactics.append((goal, items))

        self._tactic_items = [
            i for _, items in goals_with_tactics for i in items
        ]

        lv = self.query_one('#entry-list', VimListView)
        self._populate_list(lv, entries, goals_with_tactics)

        header = self.query_one('#entry-list-header', Static)
        detail = self.query_one('#entry-detail', Static)
        has_content = entries or self._tactic_items or self._habit_items
        if not has_content:
            header.update('Today — nothing actionable 🎉')
            detail.update('[dim]All clear. Nice work.[/dim]')
        else:
            header.update(f'Today  [dim]({len(entries)})[/dim]')
            lv.index = 0
            self._update_detail()

    @on(ListView.Highlighted, '#entry-list')
    def on_list_highlighted(self) -> None:
        self._update_detail()
        self.app.refresh_bindings()

    def _current_entry(self) -> ProjectEntry | None:
        idx = self.query_one('#entry-list', VimListView).index
        if idx is None or idx >= len(self._entries):
            return None
        return self._entries[idx]

    def _current_habit_item(self) -> WeeklyHabitItem | None:
        item = self.query_one('#entry-list', VimListView).highlighted_child
        return item if isinstance(item, WeeklyHabitItem) else None

    def _current_tactic_item(self) -> TacticListItem | None:
        item = self.query_one('#entry-list', VimListView).highlighted_child
        return item if isinstance(item, TacticListItem) else None

    def _update_detail(self) -> None:
        habit_item = self._current_habit_item()
        if habit_item is not None:
            detail = _render_habit_detail(
                habit_item.habit_key, habit_item.habit_label
            )
            self.query_one('#entry-detail', Static).update(detail)
            return
        tactic_item = self._current_tactic_item()
        if tactic_item is not None:
            goal = self._goals.get(tactic_item.goal_name)
            self.query_one('#entry-detail', Static).update(
                _render_tactic_detail(
                    tactic_item.goal_name, tactic_item.tactic, goal
                )
            )
            return
        entry = self._current_entry()
        if not entry:
            return
        notes = self._notes.get(entry.page_id)
        self.query_one('#entry-detail', Static).update(
            _render_entry_detail(entry, notes)
        )
        if entry.page_id not in self._notes:
            self._load_notes(entry.page_id)

    def check_action(
        self,
        action: str,
        parameters: tuple[object, ...],  # noqa: ARG002
    ) -> bool | None:
        habit_focused = self._current_habit_item() is not None
        tactic_focused = self._current_tactic_item() is not None
        if action in self._HABIT_ACTIONS:
            return habit_focused
        if action in self._TACTIC_ACTIONS:
            return tactic_focused
        if action in self._GTD_ACTIONS:
            return not (tactic_focused or habit_focused)
        return None

    @work
    async def action_complete_habit(self) -> None:
        item = self._current_habit_item()
        if not item:
            return

        if item.habit_key == 'goal_scoring':
            confirmed = await self._run_goal_scoring_flow()
        elif item.habit_key == 'weekly_review':
            confirmed = await self._run_weekly_review_flow()
        else:
            confirmed = await self.app.push_screen_wait(
                ConfirmModal(f'Mark "{item.habit_label}" done for this week?')
            )

        if confirmed:
            self._dismiss_habit_item(item)

    async def _run_goal_scoring_flow(self) -> bool:
        from gtd.storage import get_stored_goal_names, load_goal, save_goal  # noqa: PLC0415
        from gtd.tui import ScorecardScreen  # noqa: PLC0415

        scored_any = False
        for name in get_stored_goal_names():
            goal = load_goal(name)
            if goal.is_complete or not goal.tactics:
                continue
            week = goal.current_week()
            scores = await self.app.push_screen_wait(
                ScorecardScreen(goal, week)
            )
            if scores is None:
                continue
            wk_key = str(week)
            for i, tactic in enumerate(goal.tactics):
                if str(i) in scores:
                    tactic.weekly_scores[wk_key] = scores[str(i)]
            save_goal(goal)
            scored_any = True
            self.app.notify(f'✓ Scored {goal.name} week {week}')
        return scored_any

    async def _run_weekly_review_flow(self) -> bool:
        loop = asyncio.get_running_loop()

        # Step 1: Inbox
        inbox_entries: list[ProjectEntry] = []
        try:
            from gtd.notion.client import query_database  # noqa: PLC0415

            inbox_filter = {
                'or': [
                    {'property': 'Status', 'select': {'equals': 'Triage'}},
                    {'property': 'Status', 'select': {'equals': 'Inbox'}},
                ]
            }
            inbox_entries = await loop.run_in_executor(
                None, query_database, inbox_filter
            )
            inbox_count = len(inbox_entries)
        except Exception:
            inbox_count = -1

        if inbox_count == 0:
            self.app.notify('Inbox: empty ✓')
        else:
            label = f'{inbox_count} item(s)' if inbox_count > 0 else '? items'
            choice = await self.app.push_screen_wait(
                SelectModal(
                    f'Process inbox  [{label}]',
                    ['Triage inbox now', 'Already done ✓'],
                )
            )
            if choice is None:
                return False
            if choice == 'Triage inbox now':
                inbox_content = self.app.query_one(InboxContent)
                inbox_content.seed_entries(inbox_entries)
                await inbox_content.triage_entries(inbox_entries)

        # Remaining checklist steps
        steps = [
            'Review Projects & next actions',
            'Review Waiting For list',
            'Review Someday/Maybe list',
            'Review calendar (past & upcoming week)',
            'Review 12-Week Goals progress',
        ]
        for step in steps:
            choice = await self.app.push_screen_wait(
                SelectModal(step, ['Done ✓', 'Skip'])
            )
            if choice is None:
                return False

        return True

    def _dismiss_habit_item(self, item: WeeklyHabitItem) -> None:
        from gtd.storage import set_weekly_habit_date  # noqa: PLC0415

        set_weekly_habit_date(item.habit_key)
        lv = self.query_one('#entry-list', VimListView)
        idx = lv.index
        item.remove()
        self._habit_items = [
            h for h in self._habit_items if h.habit_key != item.habit_key
        ]
        lv.index = max(0, (idx or 1) - 1)
        self._update_detail()
        self.app.refresh_bindings()
        self.app.notify(f'✓ {item.habit_label} done for this week')

    def action_refresh_today(self) -> None:
        self.action_refresh()

    @work
    async def action_log(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        next_date = await _shared_log_and_reschedule(
            self.app, entry, self._notes
        )
        if next_date:
            self._remove_entry(entry.page_id)
            self.app.notify(f'✓ "{entry.header.strip()}" → {next_date}')

    async def action_snooze(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        self._snooze_worker(entry.page_id, tomorrow)
        self._remove_entry(entry.page_id)
        self.app.notify(f'✓ Snoozed until {tomorrow}')

    @work(thread=True)
    def _snooze_worker(self, page_id: str, date: str) -> None:
        from gtd.notion.client import build_property_update, update_page  # noqa: PLC0415

        props = build_property_update(follow_up_date=date)
        update_page(page_id, props)

    @work
    async def action_waiting_for(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        result = await self.app.push_screen_wait(
            TwoFieldModal(
                'Waiting For',
                'Who/what are you waiting on?',
                entry.next_step or '',
                'Follow-up date (optional)',
                'e.g. Friday, in 3 days',
            )
        )
        if not result:
            return
        waiting_on, followup_str = result
        from gtd.notion.entries import _parse_date_input  # noqa: PLC0415

        follow_date = _parse_date_input(followup_str) if followup_str else None
        self._waiting_for_worker(entry.page_id, waiting_on, follow_date)
        self._remove_entry(entry.page_id)
        self.app.notify(f'✓ "{entry.header.strip()}" → Waiting For')

    @work(thread=True)
    def _waiting_for_worker(
        self, page_id: str, waiting_on: str, follow_date: str | None
    ) -> None:
        from gtd.notion.client import build_property_update, update_page  # noqa: PLC0415

        kwargs: dict = {'status': 'Waiting For'}
        if waiting_on:
            kwargs['next_step'] = waiting_on
        if follow_date:
            kwargs['follow_up_date'] = follow_date
        update_page(page_id, build_property_update(**kwargs))

    @work
    async def action_log_tactic(self) -> None:
        tactic_item = self._current_tactic_item()
        if not tactic_item:
            return
        note = await self.app.push_screen_wait(
            InputModal('Log update', tactic_item.tactic_description)
        )
        if not note:
            return
        from gtd.storage import get_stored_goal_names, load_goal, save_goal  # noqa: PLC0415

        for name in get_stored_goal_names():
            if name != tactic_item.goal_name:
                continue
            goal = load_goal(name)
            for t in goal.tactics:
                if t.description == tactic_item.tactic_description:
                    t.updates.append(
                        Update(
                            date=datetime.now().date().isoformat(),
                            note=note,
                        )
                    )
                    save_goal(goal)
                    self._goals[goal.name] = goal
                    tactic_item.refresh_display(t)
                    self._update_detail()
                    self.app.notify(f'✓ Logged update on "{t.description}"')
                    return

    @work
    async def action_unlog_tactic(self) -> None:
        tactic_item = self._current_tactic_item()
        if not tactic_item:
            return
        from gtd.storage import get_stored_goal_names, load_goal, save_goal  # noqa: PLC0415

        for name in get_stored_goal_names():
            if name != tactic_item.goal_name:
                continue
            goal = load_goal(name)
            for t in goal.tactics:
                if t.description != tactic_item.tactic_description:
                    continue
                if not t.updates:
                    self.app.notify('No updates to remove', severity='warning')
                    return
                last = t.updates[-1]
                confirmed = await self.app.push_screen_wait(
                    ConfirmModal(
                        f'Remove update from {last.date}?\n"{last.note}"'
                    )
                )
                if not confirmed:
                    return
                t.updates.pop()
                save_goal(goal)
                self._goals[goal.name] = goal
                tactic_item.refresh_display(t)
                self._update_detail()
                self.app.notify(f'✓ Removed last update on "{t.description}"')
                return


# ── Inbox content ────────────────────────────────────────────────────────────


class InboxContent(BaseEntryContent):
    """Triage inbox — items waiting to be processed."""

    TITLE: ClassVar[str] = 'Inbox'
    EMPTY_MSG: ClassVar[str] = 'Inbox zero! 🎉'

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('T', 'triage_entry', 'Triage'),
        Binding('A', 'triage_all', 'Triage all'),
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'drop_entry', 'Drop'),
    ]

    def _build_filter(self) -> dict:
        return {
            'or': [
                {
                    'property': 'Status',
                    'select': {'equals': 'Triage'},
                },
                {
                    'property': 'Status',
                    'select': {'is_empty': True},
                },
                {
                    'property': 'Context',
                    'select': {'is_empty': True},
                },
                {
                    'property': 'Next Actionable Step',
                    'rich_text': {'is_empty': True},
                },
            ],
        }

    def seed_entries(self, entries: list[ProjectEntry]) -> None:
        """Pre-populate entries (e.g. from weekly review flow)."""
        self._entries = entries

    @work
    async def action_triage_entry(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        triaged = await self._triage_one(entry)
        if triaged:
            self._remove_entry(entry.page_id)

    @work
    async def action_triage_all(self) -> None:
        await self.triage_entries(self._entries)

    async def triage_entries(self, entries: list[ProjectEntry]) -> None:
        processed = 0
        for entry in list(entries):
            triaged = await self._triage_one(entry)
            if triaged is None:
                break
            if triaged:
                processed += 1
                self._remove_entry(entry.page_id)
        if processed:
            s = 's' if processed != 1 else ''
            self.app.notify(f'✓ Triaged {processed} item{s}')

    async def _triage_one(self, entry: ProjectEntry) -> bool | None:
        """Triage a single entry via TUI modals.

        Returns True if saved, False if skipped/deleted, None if cancelled.
        """
        from dateutil import parser as dateparser  # noqa: PLC0415
        from gtd.notion.client import (  # noqa: PLC0415
            archive_page,
            build_property_update,
            get_select_options,
            update_page,
        )
        from gtd.notion.triage import TRIAGE_STATUSES  # noqa: PLC0415

        title = entry.header.strip()

        status = await self.app.push_screen_wait(
            SelectModal(f'Triage: {title}', TRIAGE_STATUSES)
        )
        if status is None:
            return None

        if status == 'Delete':
            confirmed = await self.app.push_screen_wait(
                ConfirmModal(f'Delete "{title}"?')
            )
            if confirmed:
                await asyncio.get_running_loop().run_in_executor(
                    None, archive_page, entry.page_id
                )
                self.app.notify(f'✓ Deleted "{title}"')
                return True
            return False

        contexts = await asyncio.get_running_loop().run_in_executor(
            None, get_select_options, 'Context'
        )
        context = await self.app.push_screen_wait(
            SelectModal(f'Context: {title}', contexts)
        )
        if context is None:
            return None

        prompt = (
            'Who/what are you waiting on?'
            if status == 'Waiting For'
            else 'Next actionable step'
        )
        next_step = await self.app.push_screen_wait(InputModal(prompt, title))
        if next_step is None:
            return None

        due_str = await self.app.push_screen_wait(
            InputModal('Due date (blank to skip)', 'e.g. Jul 15, 2026-08-01')
        )
        due_iso: str | None = None
        if due_str:
            parsed = dateparser.parse(due_str, fuzzy=True)
            due_iso = parsed.strftime('%Y-%m-%d') if parsed else None

        follow_up_prompt = (
            'Follow-up date (required)'
            if status == 'Waiting For'
            else 'Follow-up date (blank to skip)'
        )
        follow_str = await self.app.push_screen_wait(
            InputModal(follow_up_prompt, 'e.g. Friday, in 3 days')
        )
        follow_iso: str | None = None
        if follow_str:
            parsed = dateparser.parse(follow_str, fuzzy=True)
            follow_iso = parsed.strftime('%Y-%m-%d') if parsed else None

        props = build_property_update(
            status=status,
            context=context,
            next_step=next_step or None,
            due_date=due_iso,
            follow_up_date=follow_iso,
        )
        await asyncio.get_running_loop().run_in_executor(
            None, update_page, entry.page_id, props
        )
        self.app.notify(f'✓ "{title}" → {status} [{context}]')
        return True

    @work
    async def action_update_entry(self) -> None:  # noqa: PLR0911
        from gtd.notion.client import (  # noqa: PLC0415
            build_property_update,
            get_select_options,
            update_page,
        )

        entry = self._current_entry()
        if not entry:
            return

        fields = [
            'Name',
            'Status',
            'Context',
            'Next actionable step',
            'Follow-up date',
            'Due date',
        ]
        choice = await self.app.push_screen_wait(
            SelectModal('Update which field?', fields)
        )
        if not choice:
            return

        if choice != 'Status':
            props = await _prompt_and_get_props(self.app, entry, choice)
            if props is None:
                return
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                update_page,
                entry.page_id,
                build_property_update(**props),
            )
            self._load_entries()
            self.app.notify(f'✓ "{entry.header.strip()}" updated')
            return

        # Setting Status requires Context + Next Actionable Step
        status = await self.app.push_screen_wait(
            SelectModal('Status', STATUSES)
        )
        if not status:
            return

        loop = asyncio.get_running_loop()
        context = entry.context
        if not context:
            contexts = await loop.run_in_executor(
                None, get_select_options, 'Context'
            )
            context = await self.app.push_screen_wait(
                SelectModal('Context (required to move out)', contexts)
            )
            if not context:
                self.app.notify(
                    'Context required to move out of Inbox',
                    severity='warning',
                )
                return

        next_step = entry.next_step
        if not next_step:
            next_step = await self.app.push_screen_wait(
                InputModal('Next Actionable Step (required to move out)')
            )
            if not next_step:
                self.app.notify(
                    'Next step required to move out of Inbox',
                    severity='warning',
                )
                return

        await loop.run_in_executor(
            None,
            update_page,
            entry.page_id,
            build_property_update(
                status=status, context=context, next_step=next_step
            ),
        )
        self._load_entries()
        self.app.notify(f'✓ "{entry.header.strip()}" → {status}')


# ── Projects content ─────────────────────────────────────────────────────────


class ProjectsContent(BaseEntryContent):
    """All active projects — Current Project and Waiting For."""

    TITLE: ClassVar[str] = 'Projects'
    EMPTY_MSG: ClassVar[str] = 'No active projects.'

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'mark_done', 'Done'),
        Binding('S', 'move_someday', 'Someday'),
    ]

    def _build_filter(self) -> dict:
        return {
            'or': [
                {
                    'property': 'Status',
                    'select': {'equals': 'Current Project'},
                },
                {
                    'property': 'Status',
                    'select': {'equals': 'Waiting For'},
                },
            ],
        }


# ── Recurring content ────────────────────────────────────────────────────────


class RecurringContent(BaseEntryContent):
    """All recurring tasks — habits and repeating actions."""

    TITLE: ClassVar[str] = 'Recurring'
    EMPTY_MSG: ClassVar[str] = 'No recurring tasks.'

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('L', 'log_and_reschedule', 'Log'),
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'drop_entry', 'Drop'),
    ]

    def _build_filter(self) -> dict:
        return {'property': 'Status', 'select': {'equals': 'Recurring'}}


# ── Waiting For content ──────────────────────────────────────────────────────


class WaitingForContent(BaseEntryContent):
    """Items delegated and waiting on someone else."""

    TITLE: ClassVar[str] = 'Waiting For'
    EMPTY_MSG: ClassVar[str] = 'Nothing in waiting.'

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'mark_done', 'Done'),
        Binding('A', 'activate', 'Activate'),
    ]

    def _build_filter(self) -> dict:
        return {
            'property': 'Status',
            'select': {'equals': 'Waiting For'},
        }


# ── Someday content ──────────────────────────────────────────────────────────


class SomedayContent(BaseEntryContent):
    """Someday/Maybe — ideas parked for later review."""

    TITLE: ClassVar[str] = 'Someday'
    EMPTY_MSG: ClassVar[str] = 'No someday items.'

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('A', 'activate', 'Activate'),
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'drop_entry', 'Drop'),
    ]

    def _build_filter(self) -> dict:
        return {
            'property': 'Status',
            'select': {'equals': 'Someday/Maybe'},
        }


# ── Snoozed content ──────────────────────────────────────────────────────────


class SnoozedContent(BaseEntryContent):
    """Items snoozed with a future follow-up date."""

    TITLE: ClassVar[str] = 'Snoozed'
    EMPTY_MSG: ClassVar[str] = 'Nothing snoozed.'

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'mark_done', 'Done'),
    ]

    def _build_filter(self) -> dict:
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            'and': [
                {
                    'property': 'Status',
                    'select': {'equals': 'Current Project'},
                },
                {
                    'property': 'Follow-Up Date',
                    'date': {'after': today},
                },
            ],
        }


class GTDApp(App[None]):
    """Unified GTD + Goals TUI."""

    TITLE = 'GTD'
    COMMANDS: ClassVar[set] = set()
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('ctrl+p', 'command_palette', show=False),
        Binding('h', 'tab_left', '←tab', priority=True),
        Binding('l', 'tab_right', 'tab→', priority=True),
        Binding('j', 'focus_list', show=False),
        Binding('down', 'focus_list', show=False),
        Binding('C', 'capture', 'Capture'),
        Binding('R', 'refresh', 'Refresh'),
        Binding('q', 'quit', 'Quit', priority=True),
        Binding('escape', 'quit', show=False),
    ]

    DEFAULT_CSS = """
    GTDApp { background: $surface; }
    TabPane { padding: 0; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id='tabs'):
            with TabPane('Today', id='tab-today'):
                yield TodayContent()
            with TabPane('Inbox', id='tab-inbox'):
                yield InboxContent()
            with TabPane('Projects', id='tab-projects'):
                yield ProjectsContent()
            with TabPane('Recurring', id='tab-recurring'):
                yield RecurringContent()
            with TabPane('Waiting For', id='tab-waiting'):
                yield WaitingForContent()
            with TabPane('Snoozed', id='tab-snoozed'):
                yield SnoozedContent()
            with TabPane('Someday', id='tab-someday'):
                yield SomedayContent()
            with TabPane('Goals', id='tab-goals'):
                yield GoalsContent()
        yield Footer()

    @on(VimListView.FocusTabBar)
    def on_focus_tab_bar(self) -> None:
        self.query_one(Tabs).focus()

    @on(TabbedContent.TabActivated)
    def on_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        with contextlib.suppress(Exception):
            pane = self.query_one(f'#{event.tab.id}', TabPane)
            pane.query_one(VimListView).focus()

    def action_focus_list(self) -> None:
        """Drop focus from tab bar back to active tab's list."""
        tc = self.query_one('#tabs', TabbedContent)
        with contextlib.suppress(Exception):
            pane = tc.query_one(f'#{tc.active}', TabPane)
            pane.query_one(VimListView).focus()

    def action_capture(self) -> None:
        """Capture a new item — available from anywhere in the app."""
        tc = self.query_one('#tabs', TabbedContent)
        with contextlib.suppress(Exception):
            pane = tc.query_one(f'#{tc.active}', TabPane)
            pane.query_one(BaseEntryContent).action_capture()

    def action_refresh(self) -> None:
        """Reload the active tab's list."""
        tc = self.query_one('#tabs', TabbedContent)
        with contextlib.suppress(Exception):
            pane = tc.query_one(f'#{tc.active}', TabPane)
            with contextlib.suppress(Exception):
                pane.query_one(BaseEntryContent).action_refresh()
                return
            pane.query_one(GoalsContent).action_refresh_goals()

    def action_tab_right(self) -> None:
        tc = self.query_one('#tabs', TabbedContent)
        tab_ids = [p.id for p in tc.query(TabPane)]
        if not tab_ids:
            return
        try:
            idx = tab_ids.index(tc.active)
            tc.active = tab_ids[(idx + 1) % len(tab_ids)]
        except (ValueError, KeyError):
            pass

    def action_tab_left(self) -> None:
        tc = self.query_one('#tabs', TabbedContent)
        tab_ids = [p.id for p in tc.query(TabPane)]
        if not tab_ids:
            return
        try:
            idx = tab_ids.index(tc.active)
            tc.active = tab_ids[(idx - 1) % len(tab_ids)]
        except (ValueError, KeyError):
            pass


def run_gtd_tui() -> None:
    """Launch the unified GTD TUI."""
    GTDApp().run()
