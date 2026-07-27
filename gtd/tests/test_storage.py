import json
from datetime import datetime
from pathlib import Path

import pytest

from gtd import storage
from gtd.storage import (
    current_week_start,
    get_weekly_review_done,
    load_areas,
    load_review_state,
    reset_review_state,
    save_areas,
    save_review_state,
    set_weekly_review_done,
)


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect all storage paths to a temp directory."""
    monkeypatch.setattr(storage, 'OUTPUT_PATH', tmp_path)
    monkeypatch.setattr(
        storage, 'WEEKLY_REVIEW_PATH', tmp_path / 'weekly_review.json'
    )
    monkeypatch.setattr(storage, 'AREAS_PATH', tmp_path / 'areas.json')


class TestWeeklyReviewDone:
    def test_returns_none_when_file_missing(self) -> None:
        assert get_weekly_review_done() is None

    def test_set_writes_today(self) -> None:
        set_weekly_review_done()
        result = get_weekly_review_done()
        assert result == datetime.now().date().isoformat()

    def test_set_updates_existing_value(self) -> None:
        storage.WEEKLY_REVIEW_PATH.write_text(
            json.dumps({'done_date': '2020-01-01'}) + '\n'
        )
        set_weekly_review_done()
        assert get_weekly_review_done() == datetime.now().date().isoformat()


# ── load_areas / save_areas ──────────────────────────────────────────────────


class TestLoadAndSaveAreas:
    def test_returns_empty_list_when_file_missing(self) -> None:
        assert load_areas() == []

    def test_returns_areas_from_file(self, tmp_path: Path) -> None:
        data = [{'name': 'Health', 'notes': ''}]
        storage.AREAS_PATH.write_text(json.dumps(data) + '\n')
        assert load_areas() == data

    def test_save_writes_json_to_areas_path(self, tmp_path: Path) -> None:
        areas = [{'name': 'Work', 'notes': 'Day job'}]
        save_areas(areas)
        assert storage.AREAS_PATH.exists()
        assert json.loads(storage.AREAS_PATH.read_text()) == areas

    def test_roundtrip_preserves_name_and_notes(self) -> None:
        areas = [
            {'name': 'Health', 'notes': 'exercise and sleep'},
            {'name': 'Family', 'notes': ''},
        ]
        save_areas(areas)
        loaded = load_areas()
        assert loaded[0]['name'] == 'Health'
        assert loaded[0]['notes'] == 'exercise and sleep'
        assert loaded[1]['name'] == 'Family'


# ── load_review_state / save_review_state / reset_review_state ───────────────


class TestReviewState:
    def test_returns_all_false_when_file_missing(self) -> None:
        assert load_review_state(3) == [False, False, False]

    def test_returns_all_false_when_week_start_differs(self) -> None:
        state = {'week_start': '2020-01-06', 'steps_done': [True, True, True]}
        storage.WEEKLY_REVIEW_PATH.write_text(
            json.dumps({'review_state': state}) + '\n'
        )
        assert load_review_state(3) == [False, False, False]

    def test_returns_saved_state_when_week_matches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            storage, 'current_week_start', lambda: '2026-07-06'
        )
        state = {'week_start': '2026-07-06', 'steps_done': [True, False, True]}
        storage.WEEKLY_REVIEW_PATH.write_text(
            json.dumps({'review_state': state}) + '\n'
        )
        assert load_review_state(3) == [True, False, True]

    def test_roundtrip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            storage, 'current_week_start', lambda: '2026-07-06'
        )
        save_review_state([True, True, False])
        assert load_review_state(3) == [True, True, False]

    def test_returns_all_false_when_step_count_differs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            storage, 'current_week_start', lambda: '2026-07-06'
        )
        save_review_state([True, True])
        assert load_review_state(4) == [False, False, False, False]

    def test_reset_removes_review_state_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            storage, 'current_week_start', lambda: '2026-07-06'
        )
        save_review_state([True, False])
        reset_review_state()
        data = json.loads(storage.WEEKLY_REVIEW_PATH.read_text())
        assert 'review_state' not in data

    def test_reset_is_noop_when_file_missing(self) -> None:
        reset_review_state()  # should not raise

    def test_save_preserves_review_done_date(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review state and the done-date marker share one file — neither wins.

        Both live in weekly_review.json. If save_review_state stopped
        merging, finishing a review step would wipe the record of the
        review already completed this week.
        """
        monkeypatch.setattr(
            storage, 'current_week_start', lambda: '2026-07-06'
        )
        set_weekly_review_done()
        save_review_state([True, False])

        assert get_weekly_review_done() == datetime.now().date().isoformat()
        assert load_review_state(2) == [True, False]

    def test_set_review_done_preserves_review_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The same merge contract in the other direction."""
        monkeypatch.setattr(
            storage, 'current_week_start', lambda: '2026-07-06'
        )
        save_review_state([True, True])
        set_weekly_review_done()

        assert load_review_state(2) == [True, True]

    def test_reset_clears_the_done_date_marker(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            storage, 'current_week_start', lambda: '2026-07-06'
        )
        set_weekly_review_done()
        save_review_state([True, False])
        reset_review_state()

        data = json.loads(storage.WEEKLY_REVIEW_PATH.read_text())
        assert 'review_state' not in data
        assert 'done_date' not in data


# ── current_week_start: drives the Monday reset ──────────────────────────────


class TestCurrentWeekStart:
    @pytest.mark.parametrize(
        ('today', 'expected_monday'),
        [
            ('2026-07-27', '2026-07-27'),  # Monday
            ('2026-07-28', '2026-07-27'),  # Tuesday
            ('2026-07-31', '2026-07-27'),  # Friday
            ('2026-08-01', '2026-07-27'),  # Saturday
            ('2026-08-02', '2026-07-27'),  # Sunday
            ('2026-08-03', '2026-08-03'),  # next Monday
        ],
    )
    def test_resolves_to_the_containing_monday(
        self,
        monkeypatch: pytest.MonkeyPatch,
        today: str,
        expected_monday: str,
    ) -> None:
        """Sunday must still belong to the week that began Monday.

        Getting this off by a day would reset a half-finished weekly
        review on Sunday instead of Monday.
        """
        fixed = datetime.fromisoformat(today)

        class _FixedDatetime(datetime):
            @classmethod
            def now(cls, tz: object = None) -> datetime:  # noqa: ARG003
                return fixed

        monkeypatch.setattr(storage, 'datetime', _FixedDatetime)

        assert current_week_start() == expected_monday
