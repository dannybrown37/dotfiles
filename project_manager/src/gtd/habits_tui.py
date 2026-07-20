"""Habits TUI widget and content pane."""

from __future__ import annotations

from calendar import monthcalendar
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Container, ScrollableContainer, Vertical
from textual.widgets import Label, ListItem, ListView, Static
from textual import on, work

from gtd.notion.habits import (
    create_habit,
    delete_habit,
    get_calendar_data,
    get_habits,
    update_habit,
)
from gtd.tui import InputModal, SelectModal, VimListView

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from gtd.notion.habits_models import Habit


class HabitListItem(ListItem):
    """ListItem representing a single habit."""

    def __init__(self, habit: Habit) -> None:
        super().__init__(Label(habit.name))
        self.habit: Habit = habit


class HabitCalendar(Static):
    """Renders a calendar grid for habit completion."""

    DEFAULT_CSS = """
    HabitCalendar {
        height: auto;
        margin: 1 0;
    }
    """

    def __init__(
        self,
        habit: Habit,
        calendar_data: dict[str, str],
        months_back: int = 3,
    ) -> None:
        super().__init__()
        self.habit = habit
        self.calendar_data = calendar_data
        self.months_back = months_back
        self.selected_date: str | None = None

    def render(self) -> str:
        """Render the calendar grid."""
        lines: list[str] = []

        # Get current month
        today = datetime.now().date()
        current_date = today.replace(day=1)

        # Render current month header
        month_name = current_date.strftime('%B %Y')
        lines.append(f'[bold cyan]{month_name}[/bold cyan]')
        lines.append('')

        # Day headers that match cell width (2 chars per day: 14 total)
        lines.append('S M T W T F S ')

        # Get calendar grid
        cal = monthcalendar(current_date.year, current_date.month)

        # Render each week
        for week in cal:
            week_str = ''
            for day in week:
                if day == 0:
                    week_str += '   '
                else:
                    day_date = current_date.replace(day=day)
                    day_iso = day_date.isoformat()
                    status = self.calendar_data.get(day_iso, '')

                    if status == 'Complete':
                        cell = '[green]●[/green]'
                    elif status == 'Incomplete':
                        cell = '[yellow]○[/yellow]'
                    elif status == 'Skipped':
                        cell = '[dim]-[/dim]'
                    else:
                        cell = '◯'

                    week_str += cell + ' '

            lines.append(week_str)

        lines.append('')
        msg = (
            '[green]●[/green] = Complete  [yellow]○[/yellow] = Incomplete  '
            '[dim]-[/dim] = Skipped  ◯ = No entry'
        )
        lines.append(msg)
        lines.append('[dim]Press c/i/s to log[/dim]')

        return '\n'.join(lines)


class HabitsContent(Container):
    """Habits tracking tab with calendar view (left = list, right = detail)."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding('plus', 'add_habit', 'Add habit', show=True),
        Binding('e', 'edit_habit', 'Edit', show=True),
        Binding('d', 'delete_habit', 'Delete', show=True),
        Binding('c', 'log_today', 'Log Today', show=True),
        Binding('i', 'log_incomplete', 'Incomplete', show=True),
        Binding('s', 'log_skip', 'Skip', show=True),
    ]

    DEFAULT_CSS = """
    HabitsContent {
        height: 1fr;
        layout: horizontal;
    }

    HabitsContent > #habit-list-pane {
        width: 35%;
        height: 1fr;
        border: solid $accent;
    }

    HabitsContent > #habit-list-pane > #habit-pane-title {
        dock: top;
        height: 1;
        text-style: bold;
        background: $boost;
        border-bottom: solid $accent;
        padding: 0 1;
    }

    HabitsContent > #habit-detail-pane {
        width: 65%;
        height: 1fr;
        layout: vertical;
    }

    HabitsContent > #habit-detail-pane > #habit-title {
        dock: top;
        height: auto;
        text-style: bold;
        background: $boost;
        border-bottom: double $accent;
        padding: 0 1;
    }

    HabitsContent > #habit-detail-pane > ScrollableContainer {
        height: 1fr;
        border: none;
        padding: 1;
    }

    HabitsContent > #habit-detail-pane > #habit-stats {
        dock: bottom;
        height: 1;
        border-top: solid $accent;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.habits: list[Habit] = []
        self.calendar_data: dict[str, str] = {}
        self._calendar_cache: dict[str, dict[str, str]] = {}
        self._current_habit_id: str | None = None
        self._load_timer_handle: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the Habits content pane."""
        with Vertical(id='habit-list-pane'):
            yield Label('Habits', id='habit-pane-title')
            yield VimListView(id='habit-list')
        with Vertical(id='habit-detail-pane'):
            yield Label('', id='habit-title')
            with ScrollableContainer(id='habit-calendar-scroll'):
                yield Static(
                    'Select a habit to view calendar', id='habit-calendar'
                )
            yield Label('', id='habit-stats')

    async def on_mount(self) -> None:
        """Load habits on mount."""
        self._load_habits()

    @work(thread=True)
    def _load_habits(self) -> None:
        """Fetch habits from Notion (blocking I/O in thread)."""
        try:
            self.habits = get_habits(active_only=True)
        except Exception as e:
            self.app.notify(f'Failed to load habits: {e}', severity='error')
            return

        self.app.call_from_thread(self._on_habits_loaded)

    def _on_habits_loaded(self) -> None:
        """Update UI after habits loaded (called from main thread)."""
        self._update_list()
        if self.habits:
            # Auto-load first habit's calendar (delay for widget mount)
            first_habit = self.habits[0]
            self.set_timer(
                0.1,
                lambda h=first_habit: self._load_and_render(h),
            )

    def _update_list(self) -> None:
        """Update habit list view."""
        list_view = self.query_one('#habit-list', VimListView)
        list_view.clear()

        if not self.habits:
            placeholder = ListItem(
                Label('[dim]No active habits — press [+] to create[/dim]')
            )
            placeholder.disabled = True
            list_view.append(placeholder)
            return

        for habit in self.habits:
            list_view.append(HabitListItem(habit))

    @on(ListView.Selected)
    def on_habit_selected(self, event: ListView.Selected) -> None:
        """Update detail view when habit is selected (with debounce)."""
        if not isinstance(event.item, HabitListItem):
            return

        habit = event.item.habit
        self._current_habit_id = habit.page_id

        # Update title immediately
        title = self.query_one('#habit-title', Label)
        title.update(f'[bold]{habit.name}[/bold]  [{habit.target_frequency}]')

        # Cancel existing timer
        if self._load_timer_handle:
            self.remove_timer(self._load_timer_handle)

        # Schedule calendar load with debounce
        self._load_timer_handle = self.set_timer(
            0.25, lambda: self._load_and_render(habit)
        )

    def _load_and_render(self, habit: Habit) -> None:
        """Load calendar and render (after debounce)."""
        self._load_timer_handle = None

        # Check cache first
        if habit.page_id in self._calendar_cache:
            self.calendar_data = self._calendar_cache[habit.page_id]
            self._render_calendar_view(habit)
            self._update_stats()
        else:
            # Load in background
            self._load_calendar_async(habit.page_id)

    @work(thread=True)
    def _load_calendar_async(self, habit_id: str) -> None:
        """Load calendar data in background thread."""
        try:
            data = get_calendar_data(habit_id, months_back=3)
            self._calendar_cache[habit_id] = data
            # Only update UI if still viewing this habit
            if self._current_habit_id == habit_id:
                self.app.call_from_thread(self._refresh_calendar_display)
        except Exception as e:
            self.app.call_from_thread(
                lambda err=str(e): self.app.notify(
                    f'Failed to load calendar: {err}', severity='error'
                )
            )

    def _refresh_calendar_display(self) -> None:
        """Refresh calendar display with currently cached data."""
        if self._current_habit_id is None:
            return

        habit = next(
            (h for h in self.habits if h.page_id == self._current_habit_id),
            None,
        )
        if habit is None:
            return

        self.calendar_data = self._calendar_cache.get(
            self._current_habit_id, {}
        )
        self._render_calendar_view(habit)
        self._update_stats()

    def _render_calendar_view(self, habit: Habit) -> None:
        """Render the calendar with current cached data."""
        calendar = HabitCalendar(habit, self.calendar_data, months_back=3)
        self.query_one('#habit-calendar', Static).update(calendar.render())

    def _update_stats(self) -> None:
        """Update stats display."""
        today = datetime.now().date().isoformat()
        total = len(self.calendar_data)
        complete = sum(
            1 for s in self.calendar_data.values() if s == 'Complete'
        )
        pct = (complete / total * 100) if total > 0 else 0
        today_status = self.calendar_data.get(today, '')
        entry = today_status or 'No entry'
        self.query_one('#habit-stats', Label).update(
            f'Total: {complete}/{total} ({pct:.0f}%)  |  Today: {entry}'
        )

    @work
    async def action_add_habit(self) -> None:
        """Add a new habit."""
        name = await self.app.push_screen_wait(
            InputModal(
                title='New Habit',
                placeholder='Habit name:',
            )
        )
        if not name or not name.strip():
            return

        frequency = await self.app.push_screen_wait(
            SelectModal(
                'Target Frequency',
                [
                    'Daily',
                    '2x/week',
                    '3x/week',
                    '5x/week',
                    'Weekly',
                    'Monthly',
                ],
            )
        )
        if not frequency:
            return

        self._create_habit_async(name, frequency)

    @work(thread=True)
    def _create_habit_async(self, name: str, frequency: str) -> None:
        """Create habit in Notion (thread-safe)."""
        try:
            new_habit = create_habit(
                name=name,
                target_frequency=frequency,
            )
            self.habits.append(new_habit)
            self.app.call_from_thread(
                lambda: (
                    self._update_list(),
                    self.app.notify(f'✓ Created habit: {name}'),
                )
            )
        except Exception as e:
            self.app.notify(f'Failed to create habit: {e}', severity='error')

    @work
    async def action_edit_habit(self) -> None:
        """Edit current habit."""
        list_view = self.query_one('#habit-list', VimListView)
        if (
            list_view.index is None
            or list_view.index < 0
            or list_view.index >= len(self.habits)
        ):
            return

        habit = self.habits[list_view.index]

        new_name = await self.app.push_screen_wait(
            InputModal(
                title='Edit Habit',
                placeholder='Habit name:',
                initial=habit.name,
            )
        )
        if not new_name or new_name == habit.name:
            return

        self._update_habit_async(habit, new_name)

    @work
    async def action_delete_habit(self) -> None:
        """Delete current habit with confirmation."""
        list_view = self.query_one('#habit-list', VimListView)
        if (
            list_view.index is None
            or list_view.index < 0
            or list_view.index >= len(self.habits)
        ):
            return

        habit = self.habits[list_view.index]

        from gtd.tui import ConfirmModal  # noqa: PLC0415

        confirmed = await self.app.push_screen_wait(
            ConfirmModal(f"Delete habit '[bold]{habit.name}[/bold]'?")
        )

        if not confirmed:
            return

        self._delete_habit_async(habit)

    @work(thread=True)
    def _update_habit_async(self, habit: Habit, new_name: str) -> None:
        """Update habit in Notion (thread-safe)."""
        try:
            updated = update_habit(habit.page_id, name=new_name)
            idx = self.habits.index(habit)
            self.habits[idx] = updated
            self.app.call_from_thread(
                lambda: (
                    self._update_list(),
                    self._refresh_detail(),
                    self.app.notify(f'✓ Updated habit: {new_name}'),
                )
            )
        except Exception as e:
            self.app.notify(f'Failed to update habit: {e}', severity='error')

    @work(thread=True)
    def _delete_habit_async(self, habit: Habit) -> None:
        """Delete habit from Notion (thread-safe)."""
        try:
            delete_habit(habit.page_id)
            self.habits.remove(habit)
            self.app.call_from_thread(
                lambda: (
                    self._update_list(),
                    self.app.notify(f'✓ Deleted habit: {habit.name}'),
                )
            )
        except Exception as e:
            self.app.notify(f'Failed to delete habit: {e}', severity='error')

    def action_log_today(self) -> None:
        """Mark today as complete."""
        list_view = self.query_one('#habit-list', VimListView)
        if (
            list_view.index is None
            or list_view.index < 0
            or list_view.index >= len(self.habits)
        ):
            return

        habit = self.habits[list_view.index]
        today = datetime.now().date().isoformat()
        self._log_completion_async(habit, today, 'Complete')

    def action_log_incomplete(self) -> None:
        """Mark today as incomplete."""
        list_view = self.query_one('#habit-list', VimListView)
        if (
            list_view.index is None
            or list_view.index < 0
            or list_view.index >= len(self.habits)
        ):
            return

        habit = self.habits[list_view.index]
        today = datetime.now().date().isoformat()
        self._log_completion_async(habit, today, 'Incomplete')

    def action_log_skip(self) -> None:
        """Mark today as skipped."""
        list_view = self.query_one('#habit-list', VimListView)
        if (
            list_view.index is None
            or list_view.index < 0
            or list_view.index >= len(self.habits)
        ):
            return

        habit = self.habits[list_view.index]
        today = datetime.now().date().isoformat()
        self._log_completion_async(habit, today, 'Skipped')

    @work(thread=True)
    def _log_completion_async(
        self, habit: Habit, date: str, status: str
    ) -> None:
        """Log a habit completion (thread-safe)."""
        try:
            from gtd.notion.habits import mark_complete  # noqa: PLC0415

            mark_complete(habit.page_id, date, status)
            # Update cache optimistically
            if habit.page_id in self._calendar_cache:
                self._calendar_cache[habit.page_id][date] = status
            self.calendar_data[date] = status
            self.app.call_from_thread(
                lambda: (
                    self._update_stats(),
                    self._render_calendar_view(habit),
                    self.app.notify(f'✓ {status}: {habit.name}'),
                )
            )
        except Exception as e:
            self.app.notify(f'Failed to log habit: {e}', severity='error')
