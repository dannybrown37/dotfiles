from datetime import datetime, timedelta

import pytest

from gtd.models import Goal, Tactic, Todo, Update
from gtd.tui import _render_goal_detail, _render_score_history


def _make_goal(**kwargs) -> Goal:
    now = datetime.now()
    defaults = {
        'name': 'Test Goal',
        'description': 'A test description',
        'start_date': now.isoformat(),
        'end_date': (now + timedelta(weeks=12)).isoformat(),
    }
    return Goal(**{**defaults, **kwargs})


def _make_goal_week(week: int, **kwargs) -> Goal:
    start = datetime.now() - timedelta(weeks=week - 1)
    return _make_goal(
        start_date=start.isoformat(),
        end_date=(start + timedelta(weeks=12)).isoformat(),
        **kwargs,
    )


class TestRenderGoalDetail:
    def test_shows_goal_name(self):
        goal = _make_goal(name='My Big Goal')
        result = _render_goal_detail(goal)
        assert 'My Big Goal' in result

    def test_shows_description(self):
        goal = _make_goal(description='Do something great')
        result = _render_goal_detail(goal)
        assert 'Do something great' in result

    def test_shows_week_info(self):
        goal = _make_goal_week(3)
        result = _render_goal_detail(goal)
        assert 'Week 3' in result

    def test_no_tactics_shows_prompt(self):
        goal = _make_goal()
        result = _render_goal_detail(goal)
        assert 'No tactics' in result

    def test_tactic_description_shown(self):
        goal = _make_goal(
            tactics=[
                Tactic(description='Write daily', reminder_cadence='daily')
            ]
        )
        result = _render_goal_detail(goal)
        assert 'Write daily' in result
        assert 'daily' in result

    def test_scored_tactic_shows_score(self):
        goal = _make_goal(
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    weekly_scores={'1': 8},
                )
            ]
        )
        result = _render_goal_detail(goal)
        assert '8/10' in result

    def test_unscored_tactic_shows_dash(self):
        goal = _make_goal(
            tactics=[Tactic(description='Run', reminder_cadence='daily')]
        )
        result = _render_goal_detail(goal)
        assert '—' in result

    def test_tactic_with_update_shows_latest(self):
        goal = _make_goal(
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    updates=[
                        Update(date='2026-07-01T09:00:00', note='Did 5k')
                    ],
                )
            ]
        )
        result = _render_goal_detail(goal)
        assert 'Did 5k' in result

    def test_open_todo_shown(self):
        goal = _make_goal(todos=[Todo(description='Buy milk')])
        result = _render_goal_detail(goal)
        assert 'Buy milk' in result
        assert '☐' in result

    def test_completed_todos_show_count(self):
        goal = _make_goal(
            todos=[
                Todo(description='Done thing', completed=True),
                Todo(description='Done thing 2', completed=True),
            ]
        )
        result = _render_goal_detail(goal)
        assert '2' in result

    def test_overall_execution_shown_when_scored(self):
        goal = _make_goal(
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    weekly_scores={'1': 9},
                )
            ]
        )
        result = _render_goal_detail(goal)
        assert '90%' in result

    def test_due_date_shown(self):
        goal = _make_goal(
            todos=[Todo(description='Ship it', due_date='2026-07-20T00:00:00')]
        )
        result = _render_goal_detail(goal)
        assert 'Jul' in result

    def test_no_todos_shows_prompt(self):
        goal = _make_goal()
        result = _render_goal_detail(goal)
        assert 'No to-dos' in result


class TestRenderScoreHistory:
    def test_shows_goal_name(self):
        goal = _make_goal(name='Fitness Goal')
        result = _render_score_history(goal)
        assert 'Fitness Goal' in result

    def test_shows_unscored_weeks(self):
        goal = _make_goal_week(3)
        result = _render_score_history(goal)
        assert 'not scored' in result

    def test_shows_scored_weeks(self):
        goal = _make_goal_week(
            2,
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    weekly_scores={'1': 8},
                )
            ],
        )
        result = _render_score_history(goal)
        assert '80%' in result

    def test_marks_current_week(self):
        goal = _make_goal_week(2)
        result = _render_score_history(goal)
        assert 'current' in result

    def test_shows_overall_when_scored(self):
        goal = _make_goal_week(
            2,
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    weekly_scores={'1': 9, '2': 7},
                )
            ],
        )
        result = _render_score_history(goal)
        assert 'Overall' in result

    @pytest.mark.parametrize(
        ('score', 'expected_indicator'),
        [
            (9, '🟢'),
            (7, '🟡'),
            (5, '🔴'),
        ],
    )
    def test_score_indicators(self, score: int, expected_indicator: str):
        goal = _make_goal(
            tactics=[
                Tactic(
                    description='Run',
                    reminder_cadence='daily',
                    weekly_scores={'1': score},
                )
            ]
        )
        result = _render_score_history(goal)
        assert expected_indicator in result
