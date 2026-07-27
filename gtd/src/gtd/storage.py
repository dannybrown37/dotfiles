import json
from datetime import datetime, timedelta
from pathlib import Path


__all__ = [
    'OUTPUT_PATH',
    'current_week_start',
    'get_weekly_review_done',
    'load_areas',
    'save_areas',
    'set_weekly_review_done',
]

OUTPUT_PATH = Path.home() / '.local' / 'share' / 'gtd'
WEEKLY_REVIEW_PATH = OUTPUT_PATH / 'weekly_review.json'
AREAS_PATH = OUTPUT_PATH / 'areas.json'


def get_weekly_review_done() -> str | None:
    """Return the ISO date the weekly review was last completed, or None."""
    if not WEEKLY_REVIEW_PATH.exists():
        return None
    return json.loads(WEEKLY_REVIEW_PATH.read_text()).get('done_date')


def set_weekly_review_done() -> None:
    """Mark the weekly review done today."""
    data: dict = {}
    if WEEKLY_REVIEW_PATH.exists():
        data = json.loads(WEEKLY_REVIEW_PATH.read_text())
    data['done_date'] = datetime.now().date().isoformat()
    WEEKLY_REVIEW_PATH.write_text(json.dumps(data, indent=2) + '\n')


def current_week_start() -> str:
    today = datetime.now().date()
    return (today - timedelta(days=today.weekday())).isoformat()


def load_review_state(num_steps: int) -> list[bool]:
    """Return saved step completion list for this week, or all-False."""
    if not WEEKLY_REVIEW_PATH.exists():
        return [False] * num_steps
    data = json.loads(WEEKLY_REVIEW_PATH.read_text())
    state = data.get('review_state', {})
    if state.get('week_start') != current_week_start():
        return [False] * num_steps
    saved = state.get('steps_done', [])
    if len(saved) != num_steps:
        return [False] * num_steps
    return list(saved)


def save_review_state(steps_done: list[bool]) -> None:
    """Persist step completion for this week."""
    data: dict = {}
    if WEEKLY_REVIEW_PATH.exists():
        data = json.loads(WEEKLY_REVIEW_PATH.read_text())
    data['review_state'] = {
        'week_start': current_week_start(),
        'steps_done': steps_done,
    }
    WEEKLY_REVIEW_PATH.write_text(json.dumps(data, indent=2) + '\n')


def reset_review_state() -> None:
    """Clear the saved weekly review state and completion marker."""
    if not WEEKLY_REVIEW_PATH.exists():
        return
    data = json.loads(WEEKLY_REVIEW_PATH.read_text())
    data.pop('review_state', None)
    data.pop('done_date', None)
    WEEKLY_REVIEW_PATH.write_text(json.dumps(data, indent=2) + '\n')


def load_areas() -> list[dict]:
    """Return list of area dicts: {name: str, notes: str}."""
    if not AREAS_PATH.exists():
        return []
    return json.loads(AREAS_PATH.read_text())


def save_areas(areas: list[dict]) -> None:
    AREAS_PATH.write_text(json.dumps(areas, indent=2) + '\n')
