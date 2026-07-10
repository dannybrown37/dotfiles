"""Textual TUI for 12-Week Year goals."""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import ClassVar

from dateutil import parser as dateparser
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from gtd.models import Goal, Tactic, Todo, Update, TOTAL_WEEKS
from gtd.storage import (
    ARCHIVE_PATH,
    OUTPUT_PATH,
    _safe_filename,
    ensure_dirs,
    get_stored_goal_names,
    load_goal,
    save_goal,
)
from gtd.ui import score_indicator, score_pct


# ── Rich renderers ───────────────────────────────────────────────────────────


_SCORE_GREEN = 8
_SCORE_YELLOW = 6


def _tactic_score_color(score: int) -> str:
    if score >= _SCORE_GREEN:
        return 'green'
    if score >= _SCORE_YELLOW:
        return 'yellow'
    return 'red'


def _render_tactics_section(goal: Goal, week: int) -> list[str]:
    lines = ['\n[bold]Tactics[/bold]']
    if not goal.tactics:
        lines.append(
            '  [dim]No tactics yet — press [bold]a[/bold] to add one[/dim]'
        )
        return lines
    wk_key = str(week)
    for i, t in enumerate(goal.tactics, 1):
        if wk_key in t.weekly_scores:
            score_val = t.weekly_scores[wk_key]
            mark = f'{score_val}/10'
            color = _tactic_score_color(score_val)
        else:
            mark = '—'
            color = 'dim'
        lines.append(
            f'  {i}. [{color}]{mark:>4}[/{color}]  '
            f'{t.description}  [dim]({t.reminder_cadence})[/dim]'
        )
        if t.updates:
            latest = t.updates[-1]
            date = datetime.fromisoformat(latest.date).strftime('%b %-d')
            lines.append(f'       [dim]↳ {date}: {latest.note}[/dim]')
    return lines


def _render_todos_section(goal: Goal) -> list[str]:
    lines = ['\n[bold]To-dos[/bold]']
    if not goal.todos:
        lines.append(
            '  [dim]No to-dos yet — press [bold]t[/bold] to add one[/dim]'
        )
        return lines
    open_todos = [t for t in goal.todos if not t.completed]
    done_count = sum(1 for t in goal.todos if t.completed)
    for t in open_todos:
        due = ''
        if t.due_date:
            d = datetime.fromisoformat(t.due_date)
            due = f'  [yellow](due {d:%b %-d})[/yellow]'
        lines.append(f'  ☐  {t.description}{due}')
    if done_count:
        lines.append(f'  [dim]+ {done_count} completed[/dim]')
    if not open_todos:
        lines.append('  [green]All to-dos complete ✓[/green]')
    return lines


def _render_goal_detail(goal: Goal) -> str:
    week = goal.current_week()
    weeks_left = goal.weeks_remaining()
    lines: list[str] = []

    lines.append(f'[bold cyan]{goal.name}[/bold cyan]')
    lines.append(f'[dim]{goal.date_range_display()}[/dim]')
    lines.append(goal.progress_bar())
    lines.append(
        f'[dim]Week {week}/{TOTAL_WEEKS}  •  '
        f'{weeks_left} week{"s" if weeks_left != 1 else ""} left[/dim]'
    )
    if goal.description:
        lines.append(f'\n{goal.description}')

    ex, tot = goal.overall_score()
    if tot > 0:
        pct = score_pct(ex, tot)
        ind = score_indicator(ex / tot)
        lines.append(
            f'\n{ind} Overall execution: [bold]{pct}[/bold] ({ex}/{tot})'
        )
        ex_w, tot_w = goal.week_score(week)
        if tot_w > 0:
            lines.append(
                f'  Week {week}: {score_pct(ex_w, tot_w)} ({ex_w}/{tot_w})'
            )

    lines.extend(_render_tactics_section(goal, week))
    lines.extend(_render_todos_section(goal))
    return '\n'.join(lines)


def _render_score_history(goal: Goal) -> str:
    week = goal.current_week()
    lines = [f'[bold]Score History: {goal.name}[/bold]\n']
    for w in range(1, min(week, TOTAL_WEEKS) + 1):
        ex, tot = goal.week_score(w)
        if tot == 0:
            bar = '[dim](not scored)[/dim]'
        else:
            pct_val = ex / tot
            filled = round(pct_val * 20)
            bar_str = '█' * filled + '░' * (20 - filled)
            ind = score_indicator(pct_val)
            pct_str = score_pct(ex, tot)
            bar = f'{ind} [{bar_str}] [bold]{pct_str:>4}[/bold] ({ex}/{tot})'
        current = ' [green]◀ current[/green]' if w == week else ''
        lines.append(f'  Week {w:>2}: {bar}{current}')

    ex_tot, tot_tot = goal.overall_score()
    if tot_tot > 0:
        lines.append(
            f'\n  [bold]Overall: {score_pct(ex_tot, tot_tot)}[/bold]'
            f' ({ex_tot}/{tot_tot})'
        )
    return '\n'.join(lines)


# ── Modals ───────────────────────────────────────────────────────────────────

_MODAL_CSS = """
.modal-box {
    background: $surface;
    border: solid $accent;
    padding: 1 2;
    height: auto;
}
.modal-title {
    text-style: bold;
    margin-bottom: 1;
}
.field-label {
    margin-top: 1;
    color: $text-muted;
}
.modal-buttons {
    margin-top: 1;
    align-horizontal: right;
}
.modal-buttons Button {
    margin-left: 1;
}
"""


class InputModal(ModalScreen[str | None]):
    """Single text input modal."""

    DEFAULT_CSS = (
        _MODAL_CSS
        + """
    InputModal { align: center middle; }
    InputModal .modal-box { width: 60; }
    """
    )

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('escape', 'cancel', 'Cancel', show=False)
    ]

    def __init__(
        self, title: str, placeholder: str = '', initial: str = ''
    ) -> None:
        super().__init__()
        self._title = title
        self._placeholder = placeholder
        self._initial = initial

    def compose(self) -> ComposeResult:
        with Vertical(classes='modal-box'):
            yield Label(self._title, classes='modal-title')
            yield Input(
                value=self._initial,
                placeholder=self._placeholder,
                id='the-input',
            )
            with Horizontal(classes='modal-buttons'):
                yield Button('OK', variant='primary', id='ok')
                yield Button('Cancel', id='cancel')

    def on_mount(self) -> None:
        self.query_one('#the-input', Input).focus()

    @on(Button.Pressed, '#ok')
    def confirm(self) -> None:
        self.dismiss(self.query_one('#the-input', Input).value.strip() or None)

    @on(Button.Pressed, '#cancel')
    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Input.Submitted)
    def submitted(self) -> None:
        self.confirm()


class TwoFieldModal(ModalScreen[tuple[str, str] | None]):
    """Two-field input modal."""

    DEFAULT_CSS = (
        _MODAL_CSS
        + """
    TwoFieldModal { align: center middle; }
    TwoFieldModal .modal-box { width: 70; }
    """
    )

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('escape', 'cancel', 'Cancel', show=False)
    ]

    def __init__(
        self,
        title: str,
        label1: str,
        placeholder1: str = '',
        label2: str = '',
        placeholder2: str = '',
        initial1: str = '',
        initial2: str = '',
    ) -> None:
        super().__init__()
        self._title = title
        self._label1 = label1
        self._placeholder1 = placeholder1
        self._label2 = label2
        self._placeholder2 = placeholder2
        self._initial1 = initial1
        self._initial2 = initial2

    def compose(self) -> ComposeResult:
        with Vertical(classes='modal-box'):
            yield Label(self._title, classes='modal-title')
            yield Label(self._label1, classes='field-label')
            yield Input(
                value=self._initial1,
                placeholder=self._placeholder1,
                id='input1',
            )
            yield Label(self._label2, classes='field-label')
            yield Input(
                value=self._initial2,
                placeholder=self._placeholder2,
                id='input2',
            )
            with Horizontal(classes='modal-buttons'):
                yield Button('OK', variant='primary', id='ok')
                yield Button('Cancel', id='cancel')

    def on_mount(self) -> None:
        self.query_one('#input1', Input).focus()

    @on(Button.Pressed, '#ok')
    def confirm(self) -> None:
        v1 = self.query_one('#input1', Input).value.strip()
        v2 = self.query_one('#input2', Input).value.strip()
        self.dismiss((v1, v2) if v1 else None)

    @on(Button.Pressed, '#cancel')
    def action_cancel(self) -> None:
        self.dismiss(None)


class SelectModal(ModalScreen[str | None]):
    """List selection modal."""

    DEFAULT_CSS = (
        _MODAL_CSS
        + """
    SelectModal { align: center middle; }
    SelectModal .modal-box { width: 70; max-height: 30; }
    SelectModal ListView {
        height: auto;
        max-height: 20;
        border: solid $panel;
        margin-bottom: 1;
    }
    """
    )

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('escape', 'cancel', 'Cancel', show=False),
        Binding('j', 'cursor_down', show=False),
        Binding('k', 'cursor_up', show=False),
    ]

    def __init__(self, title: str, items: list[str]) -> None:
        super().__init__()
        self._title = title
        self._items = items

    def compose(self) -> ComposeResult:
        with Vertical(classes='modal-box'):
            yield Label(self._title, classes='modal-title')
            yield ListView(*[ListItem(Label(item)) for item in self._items])
            with Horizontal(classes='modal-buttons'):
                yield Button('Select', variant='primary', id='ok')
                yield Button('Cancel', id='cancel')

    def on_mount(self) -> None:
        self.query_one(ListView).focus()

    def action_cursor_down(self) -> None:
        self.query_one(ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one(ListView).action_cursor_up()

    @on(ListView.Selected)
    def item_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is not None and idx < len(self._items):
            self.dismiss(self._items[idx])

    @on(Button.Pressed, '#ok')
    def confirm(self) -> None:
        idx = self.query_one(ListView).index
        self.dismiss(
            self._items[idx]
            if idx is not None and idx < len(self._items)
            else None
        )

    @on(Button.Pressed, '#cancel')
    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmModal(ModalScreen[bool]):
    """Yes/no confirmation modal."""

    DEFAULT_CSS = (
        _MODAL_CSS
        + """
    ConfirmModal { align: center middle; }
    ConfirmModal .modal-box { width: 60; border: solid $warning; }
    """
    )

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('escape', 'cancel', 'Cancel', show=False)
    ]

    def __init__(self, question: str) -> None:
        super().__init__()
        self._question = question

    def compose(self) -> ComposeResult:
        with Vertical(classes='modal-box'):
            yield Label(self._question, classes='modal-title')
            with Horizontal(classes='modal-buttons'):
                yield Button('Yes', variant='warning', id='yes')
                yield Button('No', variant='primary', id='no')

    def on_mount(self) -> None:
        self.query_one('#no', Button).focus()

    @on(Button.Pressed, '#yes')
    def yes(self) -> None:
        self.dismiss(result=True)

    @on(Button.Pressed, '#no')
    def action_cancel(self) -> None:
        self.dismiss(result=False)


class ScorecardScreen(ModalScreen[dict[str, int] | None]):
    """Scorecard for rating each tactic 1-10."""

    DEFAULT_CSS = (
        _MODAL_CSS
        + """
    ScorecardScreen { align: center middle; }
    ScorecardScreen .modal-box { width: 80; max-height: 40; }
    .score-row { layout: horizontal; height: 3; margin-bottom: 0; }
    .tactic-label { width: 1fr; content-align: left middle; }
    .current-score {
        width: 16;
        content-align: right middle;
        color: $text-muted;
    }
    .score-input { width: 8; }
    """
    )

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('escape', 'cancel', 'Cancel', show=False)
    ]

    def __init__(self, goal: Goal, week: int) -> None:
        super().__init__()
        self._goal = goal
        self._week = week

    def compose(self) -> ComposeResult:
        wk_key = str(self._week)
        with ScrollableContainer(classes='modal-box'):
            yield Label(
                f'Week {self._week} Scorecard — {self._goal.name}',
                classes='modal-title',
            )
            for i, tactic in enumerate(self._goal.tactics):
                current = tactic.weekly_scores.get(wk_key)
                current_str = (
                    f'current: {current}/10'
                    if current is not None
                    else 'not scored'
                )
                with Horizontal(classes='score-row'):
                    yield Label(
                        f'{i + 1}. {tactic.description}',
                        classes='tactic-label',
                    )
                    yield Label(f'[{current_str}]', classes='current-score')
                    yield Input(
                        placeholder='1-10',
                        id=f'score-{i}',
                        classes='score-input',
                        value=str(current) if current is not None else '',
                    )
            with Horizontal(classes='modal-buttons'):
                yield Button('Save', variant='primary', id='ok')
                yield Button('Cancel', id='cancel')

    def on_mount(self) -> None:
        if self._goal.tactics:
            self.query_one('#score-0', Input).focus()

    @on(Button.Pressed, '#ok')
    def confirm(self) -> None:
        scores: dict[str, int] = {}
        for i in range(len(self._goal.tactics)):
            val = self.query_one(f'#score-{i}', Input).value.strip()
            if val and val.isdigit():
                scores[str(i)] = max(1, min(10, int(val)))
        self.dismiss(scores or None)

    @on(Button.Pressed, '#cancel')
    def action_cancel(self) -> None:
        self.dismiss(None)


# ── Widgets ──────────────────────────────────────────────────────────────────


class DetailPane(ScrollableContainer):
    """Scrollable detail pane — not focusable via Tab."""

    can_focus = False


class VimListView(ListView):
    """ListView with j/k/G/g vim-style navigation.

    Pressing k at the top posts FocusTabBar so the parent can send focus
    to the tab bar; j is handled normally by ListView.
    """

    class FocusTabBar(Message):
        """Posted when k is pressed at the top of the list."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('j', 'cursor_down', show=False),
        Binding('k', 'cursor_up_or_tabs', show=False),
        Binding('G', 'scroll_end', show=False),
        Binding('g', 'scroll_home', show=False),
    ]

    def action_cursor_up_or_tabs(self) -> None:
        if self.index == 0 or self.index is None:
            self.post_message(self.FocusTabBar())
        else:
            self.action_cursor_up()


class GoalListItem(ListItem):
    def __init__(self, goal: Goal) -> None:
        super().__init__()
        self.goal_name = goal.name
        ex, tot = goal.overall_score()
        pct = f'  {score_pct(ex, tot)}' if tot > 0 else ''
        tag = ' ✓' if goal.is_complete else ''
        self._text = f'{goal.name}{tag}{pct}'

    def compose(self) -> ComposeResult:
        yield Label(self._text)


# ── Goals widget (embeddable) ────────────────────────────────────────────────


class GoalsContent(Widget):
    """Goals pane — can be embedded in a tab or used standalone."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('n', 'new_goal', 'New'),
        Binding('s', 'score_week', 'Score week'),
        Binding('a', 'add_tactic', 'Add tactic'),
        Binding('u', 'log_update', 'Log update'),
        Binding('t', 'add_todo', 'Add to-do'),
        Binding('c', 'complete_todo', 'Complete to-do'),
        Binding('e', 'edit_goal', 'Edit'),
        Binding('h', 'score_history', 'History'),
        Binding('D', 'delete_goal', 'Delete', show=False),
        Binding('r', 'refresh_goals', 'Refresh', show=False),
    ]

    DEFAULT_CSS = """
    GoalsContent {
        layout: horizontal;
        height: 1fr;
    }
    GoalsContent #goals-list-pane {
        width: 34;
        border-right: solid $panel;
    }
    GoalsContent #goals-list-header {
        background: $panel;
        padding: 0 1;
        height: 1;
        text-style: bold;
    }
    GoalsContent #goals-list { height: 1fr; }
    GoalsContent #goals-detail-pane {
        width: 1fr;
        padding: 1 2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        ensure_dirs()
        self._goals: list[Goal] = []
        self._selected_idx: int = 0

    def compose(self) -> ComposeResult:
        with Vertical(id='goals-list-pane'):
            yield Static('Goals', id='goals-list-header')
            yield VimListView(id='goals-list')
        with DetailPane(id='goals-detail-pane'):
            yield Static('', id='goals-detail-content', markup=True)

    def on_mount(self) -> None:
        self._refresh_goals()

    def _refresh_goals(self) -> None:
        names = get_stored_goal_names()
        self._goals = [load_goal(n) for n in names]
        lv = self.query_one('#goals-list', VimListView)
        lv.clear()
        for goal in self._goals:
            lv.append(GoalListItem(goal))
        if self._goals:
            target = min(self._selected_idx, len(self._goals) - 1)
            lv.index = target
            self._update_detail()
        else:
            self.query_one('#goals-detail-content', Static).update(
                '[dim]No goals yet — press [bold]n[/bold] to create one.[/dim]'
            )

    def _update_detail(self) -> None:
        idx = self.query_one('#goals-list', VimListView).index
        if idx is None or idx >= len(self._goals):
            return
        self._selected_idx = idx
        self.query_one('#goals-detail-content', Static).update(
            _render_goal_detail(self._goals[idx])
        )

    def _current_goal(self) -> Goal | None:
        idx = self.query_one('#goals-list', VimListView).index
        if idx is None or idx >= len(self._goals):
            return None
        return self._goals[idx]

    @on(ListView.Highlighted, '#goals-list')
    def on_list_highlighted(self) -> None:
        self._update_detail()

    # ── Actions ──────────────────────────────────────────────────────────────

    async def action_new_goal(self) -> None:
        result = await self.app.push_screen_wait(
            TwoFieldModal(
                'New Goal',
                'Name',
                'e.g. Launch my SaaS',
                'Description',
                'e.g. Ship MVP and get first paying customer',
            )
        )
        if not result:
            return
        name, description = result
        goal = Goal.new(name, description or '')
        save_goal(goal)
        self._selected_idx = len(self._goals)
        self._refresh_goals()

    async def action_score_week(self) -> None:
        goal = self._current_goal()
        if not goal:
            return
        if not goal.tactics:
            self.notify(
                'No tactics to score — add one with [a] first.',
                severity='warning',
            )
            return

        week = goal.current_week()
        available = [f'Week {w}' for w in range(1, min(week, TOTAL_WEEKS) + 1)]
        if len(available) > 1:
            choice = await self.app.push_screen_wait(
                SelectModal('Score which week?', available)
            )
            if not choice:
                return
            score_week = int(choice.split()[-1])
        else:
            score_week = week

        scores = await self.app.push_screen_wait(
            ScorecardScreen(goal, score_week)
        )
        if not scores:
            return

        wk_key = str(score_week)
        for i, tactic in enumerate(goal.tactics):
            if str(i) in scores:
                tactic.weekly_scores[wk_key] = scores[str(i)]
        save_goal(goal)
        self._refresh_goals()

        sc, mx = goal.week_score(score_week)
        self.notify(
            f'Week {score_week} saved: {score_pct(sc, mx)} ({sc}/{mx})'
        )

    async def action_add_tactic(self) -> None:
        goal = self._current_goal()
        if not goal:
            return
        result = await self.app.push_screen_wait(
            TwoFieldModal(
                'Add Tactic',
                'Description',
                'e.g. Write 500 words',
                'Cadence',
                'e.g. daily, weekly, 2x/week',
                initial2='weekly',
            )
        )
        if not result:
            return
        description, cadence = result
        goal.tactics.append(
            Tactic(
                description=description, reminder_cadence=cadence or 'weekly'
            )
        )
        save_goal(goal)
        self._refresh_goals()
        self.notify(f'Tactic added: {description}')

    async def action_log_update(self) -> None:
        goal = self._current_goal()
        if not goal:
            return
        if not goal.tactics:
            self.notify('No tactics yet.', severity='warning')
            return
        choice = await self.app.push_screen_wait(
            SelectModal(
                'Log update on tactic', [t.description for t in goal.tactics]
            )
        )
        if not choice:
            return
        idx = next(
            i for i, t in enumerate(goal.tactics) if t.description == choice
        )
        note = await self.app.push_screen_wait(
            InputModal('Log Update', 'What did you do?')
        )
        if not note:
            return
        goal.tactics[idx].updates.append(
            Update(date=datetime.now().isoformat(), note=note)
        )
        save_goal(goal)
        self._refresh_goals()
        self.notify('Update logged')

    async def action_add_todo(self) -> None:
        goal = self._current_goal()
        if not goal:
            return
        result = await self.app.push_screen_wait(
            TwoFieldModal(
                'Add To-do',
                'Description',
                'e.g. Set up billing',
                'Due date (optional)',
                'e.g. Jul 20, tomorrow',
            )
        )
        if not result:
            return
        description, due_str = result
        due_iso = None
        if due_str:
            with contextlib.suppress(ValueError, OverflowError):
                parsed = dateparser.parse(due_str, fuzzy=True)
                if parsed:
                    due_iso = parsed.isoformat()
        goal.todos.append(Todo(description=description, due_date=due_iso))
        save_goal(goal)
        self._refresh_goals()
        self.notify(f'To-do added: {description}')

    async def action_complete_todo(self) -> None:
        goal = self._current_goal()
        if not goal:
            return
        open_todos = [
            (i, t) for i, t in enumerate(goal.todos) if not t.completed
        ]
        if not open_todos:
            self.notify('No open to-dos.', severity='warning')
            return
        choice = await self.app.push_screen_wait(
            SelectModal(
                'Complete to-do', [t.description for _, t in open_todos]
            )
        )
        if not choice:
            return
        real_idx = next(i for i, t in open_todos if t.description == choice)
        goal.todos[real_idx].completed = True
        save_goal(goal)
        self._refresh_goals()
        self.notify(f'✓ {choice}')

    async def action_edit_goal(self) -> None:
        goal = self._current_goal()
        if not goal:
            return
        result = await self.app.push_screen_wait(
            TwoFieldModal(
                'Edit Goal',
                'Name',
                '',
                'Description',
                '',
                initial1=goal.name,
                initial2=goal.description,
            )
        )
        if not result:
            return
        name, description = result
        old_path = OUTPUT_PATH / f'{_safe_filename(goal.name)}.json'
        goal.name = name
        goal.description = description
        save_goal(goal)
        new_path = OUTPUT_PATH / f'{_safe_filename(goal.name)}.json'
        if old_path != new_path and old_path.exists():
            old_path.unlink()
        self._refresh_goals()

    def action_score_history(self) -> None:
        goal = self._current_goal()
        if not goal:
            return
        self.query_one('#goals-detail-content', Static).update(
            _render_score_history(goal)
        )

    async def action_delete_goal(self) -> None:
        goal = self._current_goal()
        if not goal:
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmModal(f'Archive "{goal.name}"?')
        )
        if not confirmed:
            return
        src = OUTPUT_PATH / f'{_safe_filename(goal.name)}.json'
        if src.exists():
            src.rename(ARCHIVE_PATH / f'{goal.name}.json')
        self._selected_idx = max(0, self._selected_idx - 1)
        self._refresh_goals()
        self.notify(f'"{goal.name}" archived')

    def action_refresh_goals(self) -> None:
        self._refresh_goals()


# ── Standalone goals app ─────────────────────────────────────────────────────


class GoalsApp(App[None]):
    """Standalone 12-Week Year goals TUI."""

    TITLE = '12-Week Year'
    SUB_TITLE = 'Goals'

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('q', 'quit', 'Quit', priority=True)
    ]

    DEFAULT_CSS = 'GoalsApp { background: $surface; }'

    def compose(self) -> ComposeResult:
        yield Header()
        yield GoalsContent()
        yield Footer()


def run_tui() -> None:
    """Launch the standalone goals TUI."""
    GoalsApp().run()
