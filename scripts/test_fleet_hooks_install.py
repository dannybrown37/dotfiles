"""Tests for fleet.hooks_install: global Claude hooks for session discovery."""

import json
from pathlib import Path

import pytest

from fleet.events import CLAUDE_EVENT_STATES, COPILOT_EVENT_STATES
from fleet.hooks_install import (
    claude_hooks_installed,
    install_claude_hooks,
    uninstall_claude_hooks,
)

HOOK = '/d/scripts/fleet-hook.sh'
ATUIN = {
    'matcher': 'Bash',
    'hooks': [{'type': 'command', 'command': 'atuin hook claude-code'}],
}


@pytest.fixture
def settings(tmp_path: Path) -> Path:
    path = tmp_path / 'settings.json'
    path.write_text(
        json.dumps(
            {
                'model': 'opus',
                'hooks': {'PostToolUse': [ATUIN]},
                'permissions': {'allow': ['Bash(ls)']},
            },
            indent=2,
        ),
    )
    return path


def fleet_commands(data: dict[str, object]) -> list[str]:
    hooks = data.get('hooks') or {}
    return [
        hook['command']
        for entries in hooks.values()  # type: ignore[attr-defined]
        for entry in entries
        for hook in entry['hooks']
        if 'fleet-hook.sh' in hook['command']
    ]


def test_install_adds_every_event_and_keeps_other_settings(
    settings: Path,
) -> None:
    assert install_claude_hooks(settings, HOOK) is True
    data = json.loads(settings.read_text())
    assert data['model'] == 'opus'
    assert data['permissions'] == {'allow': ['Bash(ls)']}
    assert ATUIN in data['hooks']['PostToolUse']
    assert sorted(fleet_commands(data)) == sorted(
        f'{HOOK} claude {event}' for event in CLAUDE_EVENT_STATES
    )


def test_install_is_idempotent(settings: Path) -> None:
    install_claude_hooks(settings, HOOK)
    first = settings.read_text()
    assert install_claude_hooks(settings, HOOK) is False
    assert settings.read_text() == first


def test_install_backs_up_once(settings: Path) -> None:
    original = settings.read_text()
    install_claude_hooks(settings, HOOK)
    uninstall_claude_hooks(settings)
    install_claude_hooks(settings, HOOK)
    backup = settings.with_name('settings.json.pre-fleet.bak')
    assert backup.read_text() == original


def test_install_creates_missing_settings(tmp_path: Path) -> None:
    settings = tmp_path / 'sub' / 'settings.json'
    install_claude_hooks(settings, HOOK)
    assert claude_hooks_installed(settings)


def test_install_refuses_invalid_json_settings(tmp_path: Path) -> None:
    settings = tmp_path / 'settings.json'
    settings.write_text('{ broken')
    with pytest.raises(ValueError, match='not valid JSON'):
        install_claude_hooks(settings, HOOK)
    assert settings.read_text() == '{ broken'


def test_uninstall_restores_original_hooks(settings: Path) -> None:
    original = json.loads(settings.read_text())
    install_claude_hooks(settings, HOOK)
    assert uninstall_claude_hooks(settings) is True
    assert json.loads(settings.read_text()) == original
    assert uninstall_claude_hooks(settings) is False


def test_copilot_hook_file_covers_exactly_the_mapped_events() -> None:
    path = (
        Path(__file__).parent.parent
        / 'config'
        / 'copilot'
        / 'hooks'
        / 'fleet.json'
    )
    hooks = json.loads(path.read_text())['hooks']
    assert set(hooks) == set(COPILOT_EVENT_STATES)
    for event, [entry] in hooks.items():
        assert entry['bash'].endswith(f'fleet-hook.sh}}" copilot {event}')


def test_installed_status(settings: Path, tmp_path: Path) -> None:
    assert not claude_hooks_installed(settings)
    assert not claude_hooks_installed(tmp_path / 'missing.json')
    install_claude_hooks(settings, HOOK)
    assert claude_hooks_installed(settings)
