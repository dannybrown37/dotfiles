from datetime import datetime, timedelta


from gtd.models import Goal, Tactic, Update
from gtd.ui import score_pct


# --- Goal model tests ---


class TestGoalCurrentWeek:
    def test_week_1_on_start_date(self):
        now = datetime.now()
        goal = Goal(
            name='test',
            description='',
            start_date=now.isoformat(),
            end_date=(now + timedelta(weeks=12)).isoformat(),
        )
        assert goal.current_week() == 1

    def test_week_2_after_7_days(self):
        start = datetime.now() - timedelta(days=7)
        goal = Goal(
            name='test',
            description='',
            start_date=start.isoformat(),
            end_date=(start + timedelta(weeks=12)).isoformat(),
        )
        assert goal.current_week() == 2

    def test_week_capped_at_12(self):
        start = datetime.now() - timedelta(weeks=20)
        goal = Goal(
            name='test',
            description='',
            start_date=start.isoformat(),
            end_date=(start + timedelta(weeks=12)).isoformat(),
        )
        assert goal.current_week() == 12
        assert goal.is_complete is True

    def test_never_below_1(self):
        future = datetime.now() + timedelta(days=5)
        goal = Goal(
            name='test',
            description='',
            start_date=future.isoformat(),
            end_date=(future + timedelta(weeks=12)).isoformat(),
        )
        assert goal.current_week() == 1


class TestGoalWeeksRemaining:
    def test_week_1_has_11_remaining(self):
        now = datetime.now()
        goal = Goal(
            name='test',
            description='',
            start_date=now.isoformat(),
            end_date=(now + timedelta(weeks=12)).isoformat(),
        )
        assert goal.weeks_remaining() == 11

    def test_week_12_has_0_remaining(self):
        start = datetime.now() - timedelta(weeks=11)
        goal = Goal(
            name='test',
            description='',
            start_date=start.isoformat(),
            end_date=(start + timedelta(weeks=12)).isoformat(),
        )
        assert goal.weeks_remaining() == 0


class TestGoalProgressBar:
    def test_week_1_no_fill(self):
        now = datetime.now()
        goal = Goal(
            name='test',
            description='',
            start_date=now.isoformat(),
            end_date=(now + timedelta(weeks=12)).isoformat(),
        )
        bar = goal.progress_bar()
        assert '░' * 12 in bar
        assert 'Week 1/12' in bar

    def test_week_4_three_filled(self):
        start = datetime.now() - timedelta(weeks=3)
        goal = Goal(
            name='test',
            description='',
            start_date=start.isoformat(),
            end_date=(start + timedelta(weeks=12)).isoformat(),
        )
        bar = goal.progress_bar()
        assert '███' in bar
        assert 'Week 4/12' in bar


# --- Scoring tests ---


class TestWeekScore:
    def test_no_scores_returns_zeros(self):
        goal = Goal(
            name='test',
            description='',
            start_date=datetime.now().isoformat(),
            end_date=(datetime.now() + timedelta(weeks=12)).isoformat(),
        )
        assert goal.week_score(1) == (0, 0)

    def test_single_tactic_scored(self):
        goal = Goal(
            name='test',
            description='',
            start_date=datetime.now().isoformat(),
            end_date=(datetime.now() + timedelta(weeks=12)).isoformat(),
            tactics=[
                Tactic(
                    description='Do thing',
                    reminder_cadence='daily',
                    weekly_scores={'1': 8},
                ),
            ],
        )
        assert goal.week_score(1) == (8, 10)

    def test_multiple_tactics(self):
        goal = Goal(
            name='test',
            description='',
            start_date=datetime.now().isoformat(),
            end_date=(datetime.now() + timedelta(weeks=12)).isoformat(),
            tactics=[
                Tactic(
                    description='A',
                    reminder_cadence='daily',
                    weekly_scores={'1': 7},
                ),
                Tactic(
                    description='B',
                    reminder_cadence='weekly',
                    weekly_scores={'1': 9},
                ),
            ],
        )
        assert goal.week_score(1) == (16, 20)

    def test_unscored_week_not_counted(self):
        goal = Goal(
            name='test',
            description='',
            start_date=datetime.now().isoformat(),
            end_date=(datetime.now() + timedelta(weeks=12)).isoformat(),
            tactics=[
                Tactic(
                    description='A',
                    reminder_cadence='daily',
                    weekly_scores={'1': 7},
                ),
            ],
        )
        assert goal.week_score(2) == (0, 0)


class TestOverallScore:
    def test_across_multiple_weeks(self):
        start = datetime.now() - timedelta(weeks=2)
        goal = Goal(
            name='test',
            description='',
            start_date=start.isoformat(),
            end_date=(start + timedelta(weeks=12)).isoformat(),
            tactics=[
                Tactic(
                    description='A',
                    reminder_cadence='daily',
                    weekly_scores={'1': 8, '2': 6, '3': 9},
                ),
            ],
        )
        total, max_possible = goal.overall_score()
        assert total == 23
        assert max_possible == 30


# --- score_pct tests ---


class TestScorePct:
    def test_zero_total_returns_dash(self):
        assert score_pct(0, 0) == '—'

    def test_percentage_calculation(self):
        assert score_pct(85, 100) == '85%'

    def test_rounds_down(self):
        assert score_pct(84, 100) == '84%'

    def test_perfect_score(self):
        assert score_pct(10, 10) == '100%'


# --- Model serialization tests ---


class TestSerialization:
    def test_goal_roundtrip(self):
        goal = Goal(
            name='Test Goal',
            description='A test',
            start_date='2026-06-06T00:00:00',
            end_date='2026-08-29T00:00:00',
            tactics=[
                Tactic(
                    description='Do daily standup',
                    reminder_cadence='daily',
                    updates=[
                        Update(
                            date='2026-06-10T09:00:00',
                            note='Did it',
                        ),
                    ],
                    weekly_scores={'1': 8, '2': 7},
                ),
            ],
        )
        data = goal.model_dump()
        restored = Goal.model_validate(data)
        assert restored.name == goal.name
        assert len(restored.tactics) == 1
        assert restored.tactics[0].weekly_scores == {'1': 8, '2': 7}
        assert len(restored.tactics[0].updates) == 1
        assert restored.tactics[0].updates[0].note == 'Did it'

    def test_goal_new_sets_12_week_window(self):
        goal = Goal.new('Test', 'desc')
        start = datetime.fromisoformat(goal.start_date)
        end = datetime.fromisoformat(goal.end_date)
        delta = end - start
        assert 83 <= delta.days <= 84  # 12 weeks


# --- Date display tests ---


class TestDateRangeDisplay:
    def test_format(self):
        goal = Goal(
            name='test',
            description='',
            start_date='2026-06-06T00:00:00',
            end_date='2026-08-29T00:00:00',
        )
        display = goal.date_range_display()
        assert 'Jun' in display
        assert 'Aug' in display
        assert '|' in display
