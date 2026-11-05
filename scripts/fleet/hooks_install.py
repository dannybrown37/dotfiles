"""Install fleet's global hooks for Claude Code and Copilot CLI.

Global hooks are how the dashboard sees sessions fleet did not start.
Claude needs fleet-hook.sh merged into its settings.json. Copilot
reads each file in ~/.copilot/hooks/, so it only needs a symlink to
config/copilot/hooks/fleet.json (install/symlinks.sh makes the same one).
"""

import json
import shlex
from pathlib import Path

from fleet.events import CLAUDE_EVENT_STATES
from fleet.store import write_json_atomically

CLAUDE_SETTINGS = Path.home() / '.claude' / 'settings.json'
COPILOT_HOOK_LINK = Path.home() / '.copilot' / 'hooks' / 'fleet.json'
COPILOT_HOOK_FILE = (
    Path(__file__).resolve().parents[2]
    / 'config'
    / 'copilot'
    / 'hooks'
    / 'fleet.json'
)
MARKER = 'fleet-hook.sh'
BACKUP_SUFFIX = '.pre-fleet.bak'


def load_settings(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except ValueError as error:
        msg = f'{path} is not valid JSON; fix it before installing hooks'
        raise ValueError(msg) from error
    if not isinstance(data, dict):
        msg = f'{path} is not a JSON object'
        raise ValueError(msg)  # noqa: TRY004
    return data


def is_fleet_entry(entry: object) -> bool:
    hooks = entry.get('hooks', []) if isinstance(entry, dict) else []
    return any(MARKER in str(hook.get('command', '')) for hook in hooks)


def claude_hooks_installed(path: Path = CLAUDE_SETTINGS) -> bool:
    try:
        hooks = load_settings(path).get('hooks') or {}
    except ValueError:
        return False
    return isinstance(hooks, dict) and all(
        any(is_fleet_entry(e) for e in hooks.get(event, []))
        for event in CLAUDE_EVENT_STATES
    )


def write_settings(path: Path, data: dict[str, object]) -> None:
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if path.exists() and not backup.exists():
        backup.write_text(path.read_text())
    write_json_atomically(path, data, indent=2)


def install_claude_hooks(path: Path, hook_path: str) -> bool:
    data = load_settings(path)
    hooks = data.setdefault('hooks', {})
    if not isinstance(hooks, dict):
        msg = f'{path}: "hooks" is not an object'
        raise ValueError(msg)  # noqa: TRY004
    changed = False
    for event in CLAUDE_EVENT_STATES:
        entries = hooks.setdefault(event, [])
        if any(is_fleet_entry(e) for e in entries):
            continue
        command = f'{shlex.quote(hook_path)} claude {event}'
        entries.append({'hooks': [{'type': 'command', 'command': command}]})
        changed = True
    if changed:
        write_settings(path, data)
    return changed


def uninstall_claude_hooks(path: Path) -> bool:
    data = load_settings(path)
    hooks = data.get('hooks')
    if not isinstance(hooks, dict):
        return False
    changed = False
    for event in list(hooks):
        kept = [e for e in hooks[event] if not is_fleet_entry(e)]
        if len(kept) != len(hooks[event]):
            changed = True
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
    if not hooks:
        del data['hooks']
    if changed:
        write_settings(path, data)
    return changed


def copilot_hooks_installed(link: Path = COPILOT_HOOK_LINK) -> bool:
    return link.exists()


def install_copilot_hooks(link: Path, source: Path) -> bool:
    if link.is_symlink() and link.resolve() == source.resolve():
        return False
    if link.exists() and not link.is_symlink():
        msg = f'{link} exists and is not a symlink; move it aside first'
        raise ValueError(msg)
    link.parent.mkdir(parents=True, exist_ok=True)
    link.unlink(missing_ok=True)
    link.symlink_to(source)
    return True


def uninstall_copilot_hooks(link: Path) -> bool:
    if not link.is_symlink():
        return False
    link.unlink()
    return True
