import pytest
from datetime import datetime, timedelta

from gtd.gtd_tui import (
    _current_sprint_label,
    _current_week_label,
    _is_sprint_cadence,
    _parse_cadence_per_week,
    _render_entry_detail,
    _render_entry_summary,
    _render_tactic_detail,
    _tactic_is_due,
    _tactic_sort_key,
    _tactic_status_line,
)
from gtd.models import Goal, Tactic, Update
from gtd.notion.models import ProjectEntry
from gtd.notion.schema import STATUS_ICONS


def _today() -> str:
    return datetime.now().date().isoformat()


def _days_ago(n: int) -> str:
    return (datetime.now().date() - timedelta(days=n)).isoformat()


def _tactic(
    cadence: str = 'weekly', updates: list[Update] | None = None
) -> Tactic:
    return Tactic(
        description='Do the thing',
        reminder_cadence=cadence,
        updates=updates or [],
    )


def _update(days_ago: int = 0, note: str = 'did it') -> Update:
    return Update(date=_days_ago(days_ago), note=note)


def _goal(name: str = 'My Goal') -> Goal:
    today = datetime.now().date()
    return Goal(
        name=name,
        description='',
        start_date=(today - timedelta(weeks=2)).isoformat(),
        end_date=(today + timedelta(weeks=10)).isoformat(),
    )


def _entry(**kwargs) -> ProjectEntry:
    defaults = {
        'page_id': 'abc123',
        'header': 'Buy milk',
        'status': 'Current Project',
        'context': 'Home',
        'next_step': 'Go to store',
        'due_date': None,
        'follow_up_date': None,
        'created_date': '2026-07-01T00:00:00',
    }
    return ProjectEntry(**{**defaults, **kwargs})


class TestRenderEntryDetail:
    def test_shows_header(self):
        result = _render_entry_detail(_entry(header='Buy milk'))
        assert 'Buy milk' in result

    def test_shows_status(self):
        result = _render_entry_detail(_entry(status='Current Project'))
        assert 'Current Project' in result

    def test_shows_context(self):
        result = _render_entry_detail(_entry(context='Work'))
        assert 'Work' in result

    def test_shows_next_step(self):
        result = _render_entry_detail(_entry(next_step='Write tests'))
        assert 'Write tests' in result

    def test_shows_due_date_when_present(self):
        result = _render_entry_detail(_entry(due_date='2026-07-20'))
        assert '2026-07-20' in result

    def test_no_due_line_when_absent(self):
        result = _render_entry_detail(_entry(due_date=None))
        assert 'Due' not in result

    def test_shows_follow_up_when_present(self):
        result = _render_entry_detail(_entry(follow_up_date='2026-07-25'))
        assert '2026-07-25' in result

    def test_loading_state_when_notes_none(self):
        result = _render_entry_detail(_entry(), notes=None)
        assert 'Loading' in result

    def test_shows_notes_content(self):
        result = _render_entry_detail(_entry(), notes='Important context here')
        assert 'Important context here' in result

    def test_no_notes_message_when_empty(self):
        result = _render_entry_detail(_entry(), notes='')
        assert 'No notes' in result

    def test_status_icon_in_output(self):
        result = _render_entry_detail(_entry(status='Current Project'))
        assert STATUS_ICONS['Current Project'] in result

    def test_triage_icon(self):
        result = _render_entry_detail(_entry(status='Triage'))
        assert STATUS_ICONS['Triage'] in result

    def test_empty_next_step_shows_none(self):
        result = _render_entry_detail(_entry(next_step=''))
        assert '(none)' in result

    def test_multiline_notes_shown(self):
        result = _render_entry_detail(_entry(), notes='Line 1\nLine 2\nLine 3')
        assert 'Line 1' in result
        assert 'Line 3' in result


class TestRenderEntrySummary:
    def test_shows_header(self):
        result = _render_entry_summary(_entry(header='Buy milk'))
        assert 'Buy milk' in result

    def test_shows_context(self):
        result = _render_entry_summary(_entry(context='Work'))
        assert 'Work' in result

    def test_shows_status_icon(self):
        result = _render_entry_summary(_entry(status='Current Project'))
        assert STATUS_ICONS['Current Project'] in result

    def test_shows_due_date_when_present(self):
        result = _render_entry_summary(_entry(due_date='2026-07-20'))
        assert 'Jul 20' in result or '2026-07-20' in result

    def test_shows_next_step(self):
        result = _render_entry_summary(_entry(next_step='Write tests'))
        assert 'Write tests' in result


# ── Cadence parsing ──────────────────────────────────────────────────────────


class TestParseCadencePerWeek:
    @pytest.mark.parametrize(
        ('cadence', 'expected'),
        [
            ('daily', 7),
            ('every day', 7),
            ('DAILY', 7),
            ('Every Day', 7),
            ('2x/week', 2),
            ('3x/week', 3),
            ('1x/week', 1),
            ('weekly', 1),
            ('', 1),
            ('monthly', 1),
        ],
    )
    def test_parses(self, cadence: str, expected: int) -> None:
        assert _parse_cadence_per_week(cadence) == expected


class TestIsSprintCadence:
    @pytest.mark.parametrize(
        ('cadence', 'expected'),
        [
            ('sprint', True),
            ('Sprint', True),
            ('SPRINT', True),
            ('daily', False),
            ('weekly', False),
            ('2x/week', False),
            ('', False),
        ],
    )
    def test_identifies(self, cadence: str, expected: bool) -> None:
        assert _is_sprint_cadence(cadence) == expected


# ── _tactic_is_due ───────────────────────────────────────────────────────────


class TestTacticIsDue:
    def test_daily_due_with_no_updates(self) -> None:
        assert _tactic_is_due(_tactic('daily')) is True

    def test_daily_not_due_after_logging_today(self) -> None:
        t = _tactic('daily', [_update(0)])
        assert _tactic_is_due(t) is False

    def test_daily_due_if_only_logged_yesterday(self) -> None:
        t = _tactic('daily', [_update(1)])
        assert _tactic_is_due(t) is True

    def test_weekly_due_with_no_updates(self) -> None:
        assert _tactic_is_due(_tactic('weekly')) is True

    def test_weekly_not_due_after_logging_this_week(self) -> None:
        today = datetime.now().date()
        days_since_monday = today.weekday()
        t = _tactic('weekly', [_update(days_since_monday)])
        assert _tactic_is_due(t) is False

    def test_two_per_week_due_with_one_update(self) -> None:
        today = datetime.now().date()
        days_since_monday = today.weekday()
        t = _tactic('2x/week', [_update(days_since_monday)])
        assert _tactic_is_due(t) is True

    def test_two_per_week_not_due_with_two_updates_this_week(self) -> None:
        today = datetime.now().date()
        days_since_monday = today.weekday()
        t = _tactic(
            '2x/week', [_update(0), _update(min(1, days_since_monday))]
        )
        assert _tactic_is_due(t) is False

    def test_sprint_due_with_no_updates(self) -> None:
        assert _tactic_is_due(_tactic('sprint')) is True

    def test_sprint_not_due_after_logging_within_14_days(self) -> None:
        t = _tactic('sprint', [_update(7)])
        assert _tactic_is_due(t) is False

    def test_sprint_due_if_only_update_older_than_14_days(self) -> None:
        t = _tactic('sprint', [_update(15)])
        assert _tactic_is_due(t) is True


# ── _tactic_sort_key ─────────────────────────────────────────────────────────


class TestTacticSortKey:
    def test_daily_no_updates_is_overdue(self) -> None:
        assert _tactic_sort_key(_tactic('daily')) == 0

    def test_daily_logged_today_is_done(self) -> None:
        assert _tactic_sort_key(_tactic('daily', [_update(0)])) == 2

    def test_weekly_no_updates_is_overdue(self) -> None:
        assert _tactic_sort_key(_tactic('weekly')) == 0

    def test_weekly_logged_this_week_is_done(self) -> None:
        today = datetime.now().date()
        t = _tactic('weekly', [_update(today.weekday())])
        assert _tactic_sort_key(t) == 2

    def test_two_per_week_zero_updates_is_overdue(self) -> None:
        assert _tactic_sort_key(_tactic('2x/week')) == 0

    def test_two_per_week_one_update_is_partial(self) -> None:
        today = datetime.now().date()
        t = _tactic('2x/week', [_update(today.weekday())])
        assert _tactic_sort_key(t) == 1

    def test_two_per_week_two_updates_is_done(self) -> None:
        today = datetime.now().date()
        days_since_monday = today.weekday()
        t = _tactic(
            '2x/week', [_update(0), _update(min(1, days_since_monday))]
        )
        assert _tactic_sort_key(t) == 2

    def test_sprint_no_updates_is_overdue(self) -> None:
        assert _tactic_sort_key(_tactic('sprint')) == 0

    def test_sprint_recent_update_is_done(self) -> None:
        assert _tactic_sort_key(_tactic('sprint', [_update(7)])) == 2


# ── _tactic_status_line ──────────────────────────────────────────────────────


class TestTacticStatusLine:
    def test_daily_due(self) -> None:
        result = _tactic_status_line(_tactic('daily'))
        assert '⚠' in result
        assert 'Due today' in result

    def test_daily_done(self) -> None:
        result = _tactic_status_line(_tactic('daily', [_update(0)]))
        assert '✓' in result
        assert 'Done today' in result

    def test_weekly_due(self) -> None:
        result = _tactic_status_line(_tactic('weekly'))
        assert '⚠' in result
        assert '0/1' in result

    def test_weekly_done(self) -> None:
        today = datetime.now().date()
        t = _tactic('weekly', [_update(today.weekday())])
        result = _tactic_status_line(t)
        assert '✓' in result
        assert '1/1' in result

    def test_two_per_week_partial(self) -> None:
        today = datetime.now().date()
        t = _tactic('2x/week', [_update(today.weekday())])
        result = _tactic_status_line(t)
        assert '◑' in result
        assert '1/2' in result

    def test_sprint_due(self) -> None:
        result = _tactic_status_line(_tactic('sprint'))
        assert '⚠' in result
        assert 'sprint' in result.lower()

    def test_sprint_done(self) -> None:
        result = _tactic_status_line(_tactic('sprint', [_update(3)]))
        assert '✓' in result
        assert 'sprint' in result.lower()


# ── _render_tactic_detail ────────────────────────────────────────────────────


class TestRenderTacticDetail:
    def test_shows_goal_name(self) -> None:
        t = _tactic()
        result = _render_tactic_detail('My Goal', t, None)
        assert 'My Goal' in result

    def test_shows_tactic_description(self) -> None:
        t = _tactic()
        result = _render_tactic_detail('Goal', t, None)
        assert 'Do the thing' in result

    def test_shows_cadence(self) -> None:
        t = _tactic('3x/week')
        result = _render_tactic_detail('Goal', t, None)
        assert '3x/week' in result

    def test_no_updates_shows_prompt(self) -> None:
        result = _render_tactic_detail('Goal', _tactic(), None)
        assert 'No updates yet' in result

    def test_recent_updates_shown(self) -> None:
        t = _tactic(
            'weekly', [_update(0, 'great session'), _update(7, 'last week')]
        )
        result = _render_tactic_detail('Goal', t, None)
        assert 'great session' in result
        assert 'Recent updates' in result

    def test_only_last_5_updates_shown(self) -> None:
        updates = [_update(i, f'note {i}') for i in range(7)]
        t = _tactic('weekly', updates)
        result = _render_tactic_detail('Goal', t, None)
        assert 'note 5' not in result
        assert 'note 6' not in result

    def test_with_goal_shows_week_and_progress(self) -> None:
        t = _tactic()
        g = _goal('My Goal')
        result = _render_tactic_detail('My Goal', t, g)
        assert 'Week' in result
        assert '/12' in result

    def test_with_goal_shows_week_date_range(self) -> None:
        t = _tactic()
        g = _goal('My Goal')
        result = _render_tactic_detail('My Goal', t, g)
        # Should contain a month abbreviation for the week range
        months = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
        ]
        assert any(m in result for m in months)

    def test_with_goal_shows_goal_date_range(self) -> None:
        t = _tactic()
        g = _goal('My Goal')
        result = _render_tactic_detail('My Goal', t, g)
        # Goal spans 12 weeks, so the year should appear
        assert str(datetime.now().year) in result


# ── Date label helpers ───────────────────────────────────────────────────────


class TestCurrentWeekLabel:
    def test_returns_string_with_month(self) -> None:
        label = _current_week_label()
        months = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
        ]
        assert any(m in label for m in months)

    def test_contains_day_numbers(self) -> None:
        label = _current_week_label()
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())
        assert str(monday.day) in label

    def test_contains_hyphen_separator(self) -> None:
        assert '-' in _current_week_label()


class TestCurrentSprintLabel:
    def test_returns_string_with_month(self) -> None:
        label = _current_sprint_label()
        months = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
        ]
        assert any(m in label for m in months)

    def test_contains_hyphen_separator(self) -> None:
        assert '-' in _current_sprint_label()


class TestStatusLineIncludesDates:
    def test_weekly_due_includes_week_range(self) -> None:
        result = _tactic_status_line(_tactic('weekly'))
        months = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
        ]
        assert any(m in result for m in months)

    def test_daily_due_includes_date(self) -> None:
        result = _tactic_status_line(_tactic('daily'))
        today = datetime.now().date()
        assert str(today.day) in result

    def test_sprint_due_includes_date_range(self) -> None:
        result = _tactic_status_line(_tactic('sprint'))
        months = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
        ]
        assert any(m in result for m in months)
