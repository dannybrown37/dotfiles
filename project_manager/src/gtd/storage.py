import json
from pathlib import Path
import re

from gtd.models import Goal


OUTPUT_PATH = Path.home() / '.local' / 'share' / 'gtd'
ARCHIVE_PATH = OUTPUT_PATH / 'archive'
CONFIG_PATH = OUTPUT_PATH / 'config.json'


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


def save_goal(goal: Goal) -> None:
    path = OUTPUT_PATH / f'{_safe_filename(goal.name)}.json'
    with path.open('w') as f:
        json.dump(goal.model_dump(), f, indent=2)


def load_goal(name: str) -> Goal:
    path = OUTPUT_PATH / f'{name}.json'
    with path.open() as f:
        data = json.load(f)
    return Goal.model_validate(data)


def get_stored_goal_names() -> list[str]:
    return [
        f.stem
        for f in sorted(OUTPUT_PATH.glob('*.json'))
        if f.name != 'config.json'
    ]


def get_archived_goal_names() -> list[str]:
    return [f.stem for f in sorted(ARCHIVE_PATH.glob('*.json'))]
