import json
from datetime import datetime
from pathlib import Path

import pytest

from gtd import storage
from gtd.models import Goal, Tactic
from gtd.storage import (
    get_stored_goal_names,
    get_weekly_habit_date,
    load_goal,
    save_goal,
    set_weekly_habit_date,
)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect all storage paths to a temp directory."""
    monkeypatch.setattr(storage, 'OUTPUT_PATH', tmp_path)
    monkeypatch.setattr(storage, 'ARCHIVE_PATH', tmp_path / 'archive')
    monkeypatch.setattr(storage, 'CONFIG_PATH', tmp_path / 'config.json')
    monkeypatch.setattr(
        storage, 'HABITS_PATH', tmp_path / 'weekly_habits.json'
    )
    (tmp_path / 'archive').mkdir()


def _goal(name: str = 'Test Goal') -> Goal:
    return Goal(
        name=name,
        description='desc',
        start_date='2026-01-01',
        end_date='2026-03-24',
        tactics=[Tactic(description='Run daily', reminder_cadence='daily')],
    )


# ── get_stored_goal_names ────────────────────────────────────────────────────


class TestGetStoredGoalNames:
    def test_returns_empty_when_no_files(self, tmp_path: Path) -> None:
        assert get_stored_goal_names() == []

    def test_returns_goal_filenames(self, tmp_path: Path) -> None:
        (tmp_path / 'fitness.json').write_text('{}')
        (tmp_path / 'writing.json').write_text('{}')
        names = get_stored_goal_names()
        assert 'fitness' in names
        assert 'writing' in names

    def test_excludes_config_json(self, tmp_path: Path) -> None:
        (tmp_path / 'config.json').write_text('{}')
        (tmp_path / 'mygoal.json').write_text('{}')
        assert 'config' not in get_stored_goal_names()
        assert 'mygoal' in get_stored_goal_names()

    def test_excludes_weekly_habits_json(self, tmp_path: Path) -> None:
        (tmp_path / 'weekly_habits.json').write_text('{}')
        (tmp_path / 'mygoal.json').write_text('{}')
        assert 'weekly_habits' not in get_stored_goal_names()
        assert 'mygoal' in get_stored_goal_names()

    def test_sorted_alphabetically(self, tmp_path: Path) -> None:
        (tmp_path / 'zebra.json').write_text('{}')
        (tmp_path / 'apple.json').write_text('{}')
        (tmp_path / 'mango.json').write_text('{}')
        assert get_stored_goal_names() == ['apple', 'mango', 'zebra']


# ── save_goal / load_goal ────────────────────────────────────────────────────


class TestSaveAndLoadGoal:
    def test_roundtrip(self) -> None:
        g = _goal('Fitness')
        save_goal(g)
        loaded = load_goal('Fitness')
        assert loaded.name == 'Fitness'
        assert loaded.tactics[0].description == 'Run daily'

    def test_safe_filename_strips_slashes(self, tmp_path: Path) -> None:
        g = _goal('A/B Goal')
        save_goal(g)
        files = list(tmp_path.glob('*.json'))
        assert all('/' not in f.name for f in files)

    def test_overwrites_on_save(self) -> None:
        g = _goal('Fitness')
        save_goal(g)
        g.description = 'updated desc'
        save_goal(g)
        loaded = load_goal('Fitness')
        assert loaded.description == 'updated desc'


# ── get/set_weekly_habit_date ────────────────────────────────────────────────


class TestWeeklyHabitDate:
    def test_returns_none_when_file_missing(self) -> None:
        assert get_weekly_habit_date('weekly_review') is None

    def test_returns_none_for_unknown_key(self, tmp_path: Path) -> None:
        (tmp_path / 'weekly_habits.json').write_text(
            '{"goal_scoring": "2026-01-01"}'
        )
        assert get_weekly_habit_date('weekly_review') is None

    def test_set_writes_today(self) -> None:
        set_weekly_habit_date('weekly_review')
        result = get_weekly_habit_date('weekly_review')
        assert result == datetime.now().date().isoformat()

    def test_set_preserves_other_keys(self) -> None:
        set_weekly_habit_date('goal_scoring')
        set_weekly_habit_date('weekly_review')
        assert (
            get_weekly_habit_date('goal_scoring')
            == datetime.now().date().isoformat()
        )
        assert (
            get_weekly_habit_date('weekly_review')
            == datetime.now().date().isoformat()
        )

    def test_set_updates_existing_key(self) -> None:
        storage.HABITS_PATH.write_text(
            json.dumps({'weekly_review': '2020-01-01'}) + '\n'
        )
        set_weekly_habit_date('weekly_review')
        assert (
            get_weekly_habit_date('weekly_review')
            == datetime.now().date().isoformat()
        )
