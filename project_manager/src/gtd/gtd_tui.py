"""Unified GTD + Goals TUI."""

from __future__ import annotations

import asyncio
import contextlib
import os
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


# ── Today content ────────────────────────────────────────────────────────────


class EntryListItem(ListItem):
    def __init__(self, entry: ProjectEntry) -> None:
        super().__init__()
        self.page_id = entry.page_id
        icon = STATUS_ICONS.get(entry.status, '·')
        ctx = f' [{entry.context}]' if entry.context else ''
        self._text = f'{icon} {entry.header.strip()}{ctx}'

    def compose(self) -> ComposeResult:
        yield Label(self._text)


class TacticListItem(ListItem):
    def __init__(
        self, goal_name: str, tactic_description: str, cadence: str
    ) -> None:
        super().__init__()
        self.goal_name = goal_name
        self.tactic_description = tactic_description
        self.cadence = cadence

    def compose(self) -> ComposeResult:
        yield Label(
            f'◆ {self.tactic_description}  [dim]{self.cadence}[/dim]',
            markup=True,
        )


class SeparatorListItem(ListItem):
    def __init__(self, label: str) -> None:
        super().__init__(disabled=True)
        self._label = label

    def compose(self) -> ComposeResult:
        yield Label(f'[dim]── {self._label} ──[/dim]', markup=True)


class DetailPane(ScrollableContainer):
    """Scrollable detail pane — not focusable via Tab."""

    can_focus = False


# ── Today content ────────────────────────────────────────────────────────────


class TodayContent(Vertical):
    """Today's actionable items — the GTD daily driver."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('L', 'log', 'Log'),
        Binding('S', 'snooze', 'Snooze'),
        Binding('W', 'waiting_for', 'Waiting For'),
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'mark_done', 'Done'),
        Binding('N', 'log_tactic', 'Log update'),
    ]

    _GTD_ACTIONS: ClassVar[set[str]] = {
        'log',
        'snooze',
        'waiting_for',
        'update_entry',
        'edit_notes',
        'mark_done',
    }
    _TACTIC_ACTIONS: ClassVar[set[str]] = {'log_tactic'}

    DEFAULT_CSS = """
    TodayContent { layout: horizontal; height: 1fr; }
    TodayContent #today-list-pane {
        width: 44;
        border-right: solid $panel;
    }
    TodayContent #today-list-header {
        background: $panel;
        padding: 0 1;
        height: 1;
        text-style: bold;
    }
    TodayContent #today-list { height: 1fr; }
    TodayContent #today-detail-pane { width: 1fr; padding: 1 2; }
    TodayContent LoadingIndicator { height: 3; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[ProjectEntry] = []
        self._tactic_items: list[TacticListItem] = []
        self._notes: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id='today-list-pane'):
            yield Static('Today', id='today-list-header')
            yield LoadingIndicator(id='today-loading')
            yield VimListView(id='today-list')
        with DetailPane(id='today-detail-pane'):
            yield Static('', id='today-detail', markup=True)

    def on_mount(self) -> None:
        self._load_entries()

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

    def _set_entries(self, entries: list[ProjectEntry]) -> None:
        self._entries = entries
        with contextlib.suppress(Exception):
            self.query_one('#today-loading', LoadingIndicator).display = False

        from gtd.storage import get_stored_goal_names, load_goal  # noqa: PLC0415

        self._tactic_items = []
        for name in get_stored_goal_names():
            goal = load_goal(name)
            if goal.is_complete or not goal.tactics:
                continue
            for tactic in goal.tactics:
                self._tactic_items.append(
                    TacticListItem(
                        goal.name, tactic.description, tactic.reminder_cadence
                    )
                )

        lv = self.query_one('#today-list', VimListView)
        lv.clear()
        for entry in entries:
            lv.append(EntryListItem(entry))
        if self._tactic_items:
            lv.append(SeparatorListItem('12-Week Goals'))
            for item in self._tactic_items:
                lv.append(item)

        header = self.query_one('#today-list-header', Static)
        detail = self.query_one('#today-detail', Static)

        if not entries and not self._tactic_items:
            header.update('Today — nothing actionable 🎉')
            detail.update('[dim]All clear. Nice work.[/dim]')
        else:
            header.update(f'Today  [dim]({len(entries)})[/dim]')
            lv.index = 0
            self._update_detail()

    @on(ListView.Highlighted, '#today-list')
    def on_list_highlighted(self) -> None:
        self._update_detail()
        self.app.refresh_bindings()

    def _current_entry(self) -> ProjectEntry | None:
        idx = self.query_one('#today-list', VimListView).index
        if idx is None or idx >= len(self._entries):
            return None
        return self._entries[idx]

    def _current_tactic_item(self) -> TacticListItem | None:
        lv = self.query_one('#today-list', VimListView)
        if lv.index is None:
            return None
        item = lv.highlighted_child
        if isinstance(item, TacticListItem):
            return item
        return None

    def _update_detail(self) -> None:
        tactic = self._current_tactic_item()
        if tactic is not None:
            self.query_one('#today-detail', Static).update(
                f'[bold cyan]{tactic.goal_name}[/bold cyan]\n\n'
                f'[bold]{tactic.tactic_description}[/bold]\n\n'
                f'Cadence: [dim]{tactic.cadence}[/dim]'
            )
            return
        entry = self._current_entry()
        if not entry:
            return
        notes = self._notes.get(entry.page_id)
        self.query_one('#today-detail', Static).update(
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

    # ── Actions ──────────────────────────────────────────────────────────────

    @work
    async def action_log(self) -> None:
        entry = self._current_entry()
        if not entry:
            return

        loop = asyncio.get_running_loop()

        # Fetch current body
        from gtd.notion.client import get_page_body, replace_page_body  # noqa: PLC0415

        self.query_one('#today-detail', Static).update(
            '[dim]Fetching notes...[/dim]'
        )
        try:
            body = await loop.run_in_executor(
                None, get_page_body, entry.page_id
            )
        except Exception as e:
            self.app.notify(f'Error: {e}', severity='error')
            self._update_detail()
            return

        # Open editor
        fd, tmp_path = tempfile.mkstemp(suffix='.md')
        with open(fd, 'w') as f:  # noqa: PTH123
            f.write(body)
        editor = os.environ.get('EDITOR', 'nvim')
        with self.app.suspend():
            subprocess.run([editor, tmp_path], check=False)  # noqa: S603

        new_body = Path(tmp_path).read_text()
        Path(tmp_path).unlink(missing_ok=True)

        if new_body != body:
            await loop.run_in_executor(
                None, replace_page_body, entry.page_id, new_body
            )
            self._notes[entry.page_id] = new_body
            self.app.notify('Notes saved')

        # Reschedule
        from gtd.notion.log import _infer_reschedule_days  # noqa: PLC0415

        inferred = _infer_reschedule_days(entry.header)

        if inferred:
            next_date = (datetime.now() + timedelta(days=inferred)).strftime(
                '%Y-%m-%d'
            )
        else:
            date_str = await self.app.push_screen_wait(
                InputModal('Reschedule to', 'e.g. tomorrow, Monday, Jul 15')
            )
            if not date_str:
                self._update_detail()
                return
            from gtd.notion.entries import _parse_date_input  # noqa: PLC0415

            next_date = _parse_date_input(date_str)
            if not next_date:
                self.app.notify('Could not parse date', severity='warning')
                self._update_detail()
                return

        from gtd.notion.client import build_property_update, update_page  # noqa: PLC0415

        props = build_property_update(follow_up_date=next_date)
        await loop.run_in_executor(None, update_page, entry.page_id, props)

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
    async def action_update_entry(self) -> None:  # noqa: C901, PLR0912
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

        loop = asyncio.get_running_loop()
        from gtd.notion.client import build_property_update, update_page  # noqa: PLC0415

        if choice == 'Name':
            value = await self.app.push_screen_wait(
                InputModal('Update Name', initial=entry.header.strip())
            )
            if value:
                await loop.run_in_executor(
                    None,
                    update_page,
                    entry.page_id,
                    build_property_update(name=value),
                )

        elif choice == 'Status':
            value = await self.app.push_screen_wait(
                SelectModal('Status', STATUSES)
            )
            if value:
                await loop.run_in_executor(
                    None,
                    update_page,
                    entry.page_id,
                    build_property_update(status=value),
                )

        elif choice == 'Context':
            from gtd.notion.client import get_select_options  # noqa: PLC0415

            contexts = await loop.run_in_executor(
                None, get_select_options, 'Context'
            )
            value = await self.app.push_screen_wait(
                SelectModal('Context', contexts)
            )
            if value:
                await loop.run_in_executor(
                    None,
                    update_page,
                    entry.page_id,
                    build_property_update(context=value),
                )

        elif choice == 'Next actionable step':
            value = await self.app.push_screen_wait(
                InputModal('Next Actionable Step', initial=entry.next_step)
            )
            if value is not None:
                await loop.run_in_executor(
                    None,
                    update_page,
                    entry.page_id,
                    build_property_update(next_step=value),
                )

        elif choice == 'Follow-up date':
            from gtd.notion.entries import _parse_date_input  # noqa: PLC0415

            value = await self.app.push_screen_wait(
                InputModal(
                    'Follow-up date', 'e.g. Monday, Jul 15, blank to clear'
                )
            )
            if value is not None:
                date = _parse_date_input(value) if value else ''
                await loop.run_in_executor(
                    None,
                    update_page,
                    entry.page_id,
                    build_property_update(follow_up_date=date),
                )

        elif choice == 'Due date':
            from gtd.notion.entries import _parse_date_input  # noqa: PLC0415

            value = await self.app.push_screen_wait(
                InputModal('Due date', 'e.g. Jul 20, blank to clear')
            )
            if value is not None:
                date = _parse_date_input(value) if value else ''
                await loop.run_in_executor(
                    None,
                    update_page,
                    entry.page_id,
                    build_property_update(due_date=date),
                )

        # Refresh entry in list
        self._load_entries()
        self.app.notify(f'✓ "{entry.header.strip()}" updated')

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

        question = (
            f'⚠ "{entry.header.strip()}" is recurring! Really delete?'
            if _is_recurring(entry)
            else f'Mark done: "{entry.header.strip()}"?'
        )
        confirmed = await self.app.push_screen_wait(ConfirmModal(question))
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

    def action_refresh_today(self) -> None:
        self._entries = []
        self._notes = {}
        with contextlib.suppress(Exception):
            self.query_one('#today-loading', LoadingIndicator).display = True
        self.query_one('#today-list', VimListView).clear()
        self.query_one('#today-detail', Static).update('')
        self._load_entries()

    def check_action(
        self,
        action: str,
        parameters: tuple[object, ...],  # noqa: ARG002
    ) -> bool | None:
        tactic_focused = self._current_tactic_item() is not None
        if action in self._GTD_ACTIONS and tactic_focused:
            return False
        return not (action in self._TACTIC_ACTIONS and not tactic_focused)

    @work
    async def action_log_tactic(self) -> None:
        tactic = self._current_tactic_item()
        if not tactic:
            return
        note = await self.app.push_screen_wait(
            InputModal('Log update', f'{tactic.tactic_description}')
        )
        if not note:
            return
        from gtd.storage import get_stored_goal_names, load_goal, save_goal  # noqa: PLC0415
        from gtd.models import Update  # noqa: PLC0415
        from datetime import datetime  # noqa: PLC0415

        for name in get_stored_goal_names():
            if name != tactic.goal_name:
                continue
            goal = load_goal(name)
            for t in goal.tactics:
                if t.description == tactic.tactic_description:
                    t.updates.append(
                        Update(
                            date=datetime.now().date().isoformat(),
                            note=note,
                        )
                    )
                    save_goal(goal)
                    self.app.notify(f'✓ Logged update on "{t.description}"')
                    return


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


# ── Inbox content ────────────────────────────────────────────────────────────


class InboxContent(Vertical):
    """Triage inbox — items waiting to be processed."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('T', 'triage_all', 'Triage all'),
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'drop_entry', 'Drop'),
    ]

    DEFAULT_CSS = """
    InboxContent { layout: horizontal; height: 1fr; }
    InboxContent #inbox-list-pane {
        width: 44;
        border-right: solid $panel;
    }
    InboxContent #inbox-list-header {
        background: $panel;
        padding: 0 1;
        height: 1;
        text-style: bold;
    }
    InboxContent #inbox-list { height: 1fr; }
    InboxContent #inbox-detail-pane { width: 1fr; padding: 1 2; }
    InboxContent LoadingIndicator { height: 3; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[ProjectEntry] = []
        self._notes: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id='inbox-list-pane'):
            yield Static('Inbox', id='inbox-list-header')
            yield LoadingIndicator(id='inbox-loading')
            yield VimListView(id='inbox-list')
        with DetailPane(id='inbox-detail-pane'):
            yield Static('', id='inbox-detail', markup=True)

    def on_mount(self) -> None:
        self._load_entries()

    @work(thread=True)
    def _load_entries(self) -> None:
        from gtd.notion.triage import _get_triage_entries  # noqa: PLC0415

        try:
            entries = _get_triage_entries()
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
            self.query_one('#inbox-loading', LoadingIndicator).display = False
        lv = self.query_one('#inbox-list', VimListView)
        lv.clear()
        for entry in entries:
            lv.append(EntryListItem(entry))
        header = self.query_one('#inbox-list-header', Static)
        detail = self.query_one('#inbox-detail', Static)
        if not entries:
            header.update('Inbox — empty 🎉')
            detail.update('[dim]Inbox zero![/dim]')
        else:
            header.update(f'Inbox  [dim]({len(entries)})[/dim]')
            lv.index = 0
            self._update_detail()

    @on(ListView.Highlighted, '#inbox-list')
    def on_list_highlighted(self) -> None:
        self._update_detail()

    def _current_entry(self) -> ProjectEntry | None:
        idx = self.query_one('#inbox-list', VimListView).index
        if idx is None or idx >= len(self._entries):
            return None
        return self._entries[idx]

    def _update_detail(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        notes = self._notes.get(entry.page_id)
        self.query_one('#inbox-detail', Static).update(
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
            self.query_one('#inbox-loading', LoadingIndicator).display = True
        self.query_one('#inbox-list', VimListView).clear()
        self.query_one('#inbox-detail', Static).update('')
        self._load_entries()

    @work
    async def action_triage_all(self) -> None:
        from gtd.notion.triage import process_triage  # noqa: PLC0415

        with self.app.suspend():
            process_triage()
        self.action_refresh()

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
                    'Context required to move out of Inbox', severity='warning'
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

    @work
    async def action_edit_notes(self) -> None:
        entry = self._current_entry()
        if entry:
            await _shared_edit_notes(
                self.app, entry, self._notes, self._update_detail
            )

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


# ── Projects content ─────────────────────────────────────────────────────────


class ProjectsContent(Vertical):
    """All active projects — Current Project and Waiting For."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'mark_done', 'Done'),
        Binding('S', 'move_someday', 'Someday'),
    ]

    DEFAULT_CSS = """
    ProjectsContent { layout: horizontal; height: 1fr; }
    ProjectsContent #projects-list-pane {
        width: 44;
        border-right: solid $panel;
    }
    ProjectsContent #projects-list-header {
        background: $panel;
        padding: 0 1;
        height: 1;
        text-style: bold;
    }
    ProjectsContent #projects-list { height: 1fr; }
    ProjectsContent #projects-detail-pane { width: 1fr; padding: 1 2; }
    ProjectsContent LoadingIndicator { height: 3; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[ProjectEntry] = []
        self._notes: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id='projects-list-pane'):
            yield Static('Projects', id='projects-list-header')
            yield LoadingIndicator(id='projects-loading')
            yield VimListView(id='projects-list')
        with DetailPane(id='projects-detail-pane'):
            yield Static('', id='projects-detail', markup=True)

    def on_mount(self) -> None:
        self._load_entries()

    @work(thread=True)
    def _load_entries(self) -> None:
        from gtd.notion.client import query_database  # noqa: PLC0415

        try:
            pages = query_database(
                filter_obj={
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
            )
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
            self.query_one(
                '#projects-loading', LoadingIndicator
            ).display = False
        lv = self.query_one('#projects-list', VimListView)
        lv.clear()
        for entry in entries:
            lv.append(EntryListItem(entry))
        header = self.query_one('#projects-list-header', Static)
        detail = self.query_one('#projects-detail', Static)
        if not entries:
            header.update('Projects — empty')
            detail.update('[dim]No active projects.[/dim]')
        else:
            header.update(f'Projects  [dim]({len(entries)})[/dim]')
            lv.index = 0
            self._update_detail()

    @on(ListView.Highlighted, '#projects-list')
    def on_list_highlighted(self) -> None:
        self._update_detail()

    def _current_entry(self) -> ProjectEntry | None:
        idx = self.query_one('#projects-list', VimListView).index
        if idx is None or idx >= len(self._entries):
            return None
        return self._entries[idx]

    def _update_detail(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        notes = self._notes.get(entry.page_id)
        self.query_one('#projects-detail', Static).update(
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
            self.query_one(
                '#projects-loading', LoadingIndicator
            ).display = True
        self.query_one('#projects-list', VimListView).clear()
        self.query_one('#projects-detail', Static).update('')
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

        question = (
            f'⚠ "{entry.header.strip()}" is recurring! Really delete?'
            if _is_recurring(entry)
            else f'Mark done: "{entry.header.strip()}"?'
        )
        confirmed = await self.app.push_screen_wait(ConfirmModal(question))
        if not confirmed:
            return
        self._done_worker(entry.page_id)
        self._remove_entry(entry.page_id)
        self.app.notify(f'✓ "{entry.header.strip()}" → done')

    @work(thread=True)
    def _done_worker(self, page_id: str) -> None:
        from gtd.notion.client import archive_page  # noqa: PLC0415

        archive_page(page_id)

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


# ── Someday content ──────────────────────────────────────────────────────────


class SomedayContent(Vertical):
    """Someday/Maybe — ideas parked for later review."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('A', 'activate', 'Activate'),
        Binding('U', 'update_entry', 'Update'),
        Binding('E', 'edit_notes', 'Edit notes'),
        Binding('D', 'drop_entry', 'Drop'),
    ]

    DEFAULT_CSS = """
    SomedayContent { layout: horizontal; height: 1fr; }
    SomedayContent #someday-list-pane {
        width: 44;
        border-right: solid $panel;
    }
    SomedayContent #someday-list-header {
        background: $panel;
        padding: 0 1;
        height: 1;
        text-style: bold;
    }
    SomedayContent #someday-list { height: 1fr; }
    SomedayContent #someday-detail-pane { width: 1fr; padding: 1 2; }
    SomedayContent LoadingIndicator { height: 3; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[ProjectEntry] = []
        self._notes: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id='someday-list-pane'):
            yield Static('Someday/Maybe', id='someday-list-header')
            yield LoadingIndicator(id='someday-loading')
            yield VimListView(id='someday-list')
        with DetailPane(id='someday-detail-pane'):
            yield Static('', id='someday-detail', markup=True)

    def on_mount(self) -> None:
        self._load_entries()

    @work(thread=True)
    def _load_entries(self) -> None:
        from gtd.notion.client import query_database  # noqa: PLC0415

        try:
            pages = query_database(
                filter_obj={
                    'property': 'Status',
                    'select': {'equals': 'Someday/Maybe'},
                }
            )
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
            self.query_one(
                '#someday-loading', LoadingIndicator
            ).display = False
        lv = self.query_one('#someday-list', VimListView)
        lv.clear()
        for entry in entries:
            lv.append(EntryListItem(entry))
        header = self.query_one('#someday-list-header', Static)
        detail = self.query_one('#someday-detail', Static)
        if not entries:
            header.update('Someday — empty')
            detail.update('[dim]No someday items.[/dim]')
        else:
            header.update(f'Someday  [dim]({len(entries)})[/dim]')
            lv.index = 0
            self._update_detail()

    @on(ListView.Highlighted, '#someday-list')
    def on_list_highlighted(self) -> None:
        self._update_detail()

    def _current_entry(self) -> ProjectEntry | None:
        idx = self.query_one('#someday-list', VimListView).index
        if idx is None or idx >= len(self._entries):
            return None
        return self._entries[idx]

    def _update_detail(self) -> None:
        entry = self._current_entry()
        if not entry:
            return
        notes = self._notes.get(entry.page_id)
        self.query_one('#someday-detail', Static).update(
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
            self.query_one('#someday-loading', LoadingIndicator).display = True
        self.query_one('#someday-list', VimListView).clear()
        self.query_one('#someday-detail', Static).update('')
        self._load_entries()

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
        Binding('M', 'gtd_menu', 'FZF menu'),
        Binding('q', 'quit', 'Quit', priority=True),
        Binding('escape', 'quit', show=False),
    ]

    DEFAULT_CSS = """
    GTDApp { background: $surface; }
    TabPane { padding: 0; }
    """

    _TAB_LIST_IDS: ClassVar[dict[str, str]] = {
        'tab-today': '#today-list',
        'tab-inbox': '#inbox-list',
        'tab-projects': '#projects-list',
        'tab-someday': '#someday-list',
        'tab-goals': '#goals-list',
    }

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id='tabs'):
            with TabPane('Today', id='tab-today'):
                yield TodayContent()
            with TabPane('Inbox', id='tab-inbox'):
                yield InboxContent()
            with TabPane('Projects', id='tab-projects'):
                yield ProjectsContent()
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
        list_id = self._TAB_LIST_IDS.get(event.tab.id or '')
        if list_id:
            with contextlib.suppress(Exception):
                self.query_one(list_id, VimListView).focus()

    def action_focus_list(self) -> None:
        """Drop focus from tab bar back to active tab's list."""
        tc = self.query_one('#tabs', TabbedContent)
        list_id = self._TAB_LIST_IDS.get(tc.active or '')
        if list_id:
            with contextlib.suppress(Exception):
                self.query_one(list_id, VimListView).focus()

    def action_capture(self) -> None:
        """Capture a new item — available from anywhere in the app."""
        tc = self.query_one('#tabs', TabbedContent)
        active = tc.active or ''
        with contextlib.suppress(Exception):
            if active == 'tab-today':
                self.query_one(TodayContent).action_capture()
            elif active == 'tab-inbox':
                self.query_one(InboxContent).action_capture()
            elif active == 'tab-projects':
                self.query_one(ProjectsContent).action_capture()
            elif active == 'tab-someday':
                self.query_one(SomedayContent).action_capture()

    def action_refresh(self) -> None:
        """Reload the active tab's list."""
        tc = self.query_one('#tabs', TabbedContent)
        active = tc.active or ''
        with contextlib.suppress(Exception):
            if active == 'tab-today':
                self.query_one(TodayContent).action_refresh_today()
            elif active == 'tab-inbox':
                self.query_one(InboxContent).action_refresh()
            elif active == 'tab-projects':
                self.query_one(ProjectsContent).action_refresh()
            elif active == 'tab-someday':
                self.query_one(SomedayContent).action_refresh()
            elif active == 'tab-goals':
                self.query_one(GoalsContent).action_refresh()

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

    @work
    async def action_gtd_menu(self) -> None:
        """Suspend the TUI and open the full fzf GTD menu."""
        with self.suspend():
            subprocess.run(['gtd'], check=False)  # noqa: S607


def run_gtd_tui() -> None:
    """Launch the unified GTD TUI."""
    GTDApp().run()
