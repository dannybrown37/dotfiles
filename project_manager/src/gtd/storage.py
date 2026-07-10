import json
from datetime import datetime
from pathlib import Path
import re

from gtd.models import Goal


__all__ = [
    'ARCHIVE_PATH',
    'CONFIG_PATH',
    'OUTPUT_PATH',
    'ensure_dirs',
    'get_archived_goal_names',
    'get_stored_goal_names',
    'get_weekly_habit_date',
    'load_config',
    'load_goal',
    'save_config',
    'save_goal',
    'set_weekly_habit_date',
]

OUTPUT_PATH = Path.home() / '.local' / 'share' / 'gtd'
ARCHIVE_PATH = OUTPUT_PATH / 'archive'
CONFIG_PATH = OUTPUT_PATH / 'config.json'
HABITS_PATH = OUTPUT_PATH / 'weekly_habits.json'


def ensure_dirs() -> None:
    """Create storage directories if they don't exist."""
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str) -> str:
    """Sanitize a goal name for use as a filename."""
    safe = re.sub(r'[/<>:"\\|?*\x00-\x1f]', '-', name)
    safe = re.sub(r'-{2,}', '-', safe)
    return safe.strip('-. ') or 'unnamed'


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    with CONFIG_PATH.open('w') as f:
        json.dump(config, f, indent=2)


def get_weekly_habit_date(key: str) -> str | None:
    """Return the ISO date this habit was last marked done, or None."""
    if not HABITS_PATH.exists():
        return None
    return json.loads(HABITS_PATH.read_text()).get(key)


def set_weekly_habit_date(key: str) -> None:
    """Mark a habit done today."""
    data: dict = {}
    if HABITS_PATH.exists():
        data = json.loads(HABITS_PATH.read_text())
    data[key] = datetime.now().date().isoformat()
    HABITS_PATH.write_text(json.dumps(data, indent=2) + '\n')


def save_goal(goal: Goal) -> None:
    path = OUTPUT_PATH / f'{_safe_filename(goal.name)}.json'
    with path.open('w') as f:
        json.dump(goal.model_dump(), f, indent=2)


def load_goal(name: str) -> Goal:
    path = OUTPUT_PATH / f'{_safe_filename(name)}.json'
    with path.open() as f:
        data = json.load(f)
    return Goal.model_validate(data)


def get_stored_goal_names() -> list[str]:
    return [
        f.stem
        for f in sorted(OUTPUT_PATH.glob('*.json'))
        if f.name not in ('config.json', 'weekly_habits.json')
    ]


def get_archived_goal_names() -> list[str]:
    return [f.stem for f in sorted(ARCHIVE_PATH.glob('*.json'))]
