"""Tests for fleet.hooks_install: global Claude hooks for session discovery."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from fleet.agents import HOOK_TIMEOUT_S
from fleet.events import CLAUDE_EVENT_STATES, COPILOT_EVENT_STATES
from fleet.hooks_install import (
    claude_hooks_installed,
    copilot_hooks_installed,
    install_claude_hooks,
    install_copilot_hooks,
    uninstall_claude_hooks,
    uninstall_copilot_hooks,
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


def fleet_entries(
    data: dict[str, object],
    event: str,
) -> list[dict[str, object]]:
    return [
        hook
        for entry in data['hooks'][event]  # type: ignore[index]
        for hook in entry['hooks']
        if 'fleet-hook.sh' in hook['command']
    ]


def fake_hook(tmp_path: Path) -> tuple[Path, Path]:
    """An executable that records its argv, standing in for fleet-hook.sh."""
    log = tmp_path / 'argv.log'
    hook = tmp_path / 'fleet-hook.sh'
    hook.write_text(f'#!/bin/sh\necho "$@" >> {log}\n')
    hook.chmod(0o755)
    return hook, log


def run_shell(
    command: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ['bash', '-c', command],  # noqa: S607
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=False,
    )


def test_install_adds_every_event_and_keeps_other_settings(
    settings: Path,
) -> None:
    assert install_claude_hooks(settings, HOOK) is True
    data = json.loads(settings.read_text())
    assert data['model'] == 'opus'
    assert data['permissions'] == {'allow': ['Bash(ls)']}
    assert ATUIN in data['hooks']['PostToolUse']
    for event in CLAUDE_EVENT_STATES:
        [hook] = fleet_entries(data, event)
        assert hook['timeout'] == HOOK_TIMEOUT_S


def test_installed_command_runs_the_hook(tmp_path: Path) -> None:
    hook, log = fake_hook(tmp_path)
    settings = tmp_path / 'settings.json'
    install_claude_hooks(settings, str(hook))
    data = json.loads(settings.read_text())
    for event in CLAUDE_EVENT_STATES:
        [entry] = fleet_entries(data, event)
        assert run_shell(str(entry['command'])).returncode == 0
    assert sorted(log.read_text().splitlines()) == sorted(
        f'claude {event}' for event in CLAUDE_EVENT_STATES
    )


def test_installed_command_is_silent_when_hook_is_gone(tmp_path: Path) -> None:
    settings = tmp_path / 'settings.json'
    install_claude_hooks(settings, str(tmp_path / 'moved' / 'fleet-hook.sh'))
    data = json.loads(settings.read_text())
    for event in CLAUDE_EVENT_STATES:
        [entry] = fleet_entries(data, event)
        result = run_shell(str(entry['command']))
        assert (result.returncode, result.stdout, result.stderr) == (0, '', '')


@pytest.mark.parametrize(
    'old_command',
    [
        pytest.param(f'{HOOK} claude Stop', id='unguarded'),
        pytest.param('/old/place/fleet-hook.sh claude Stop', id='stale-path'),
    ],
)
def test_install_replaces_outdated_fleet_entries(
    settings: Path,
    old_command: str,
) -> None:
    install_claude_hooks(settings, HOOK)
    data = json.loads(settings.read_text())
    data['hooks']['Stop'] = [
        {'hooks': [{'type': 'command', 'command': old_command}]},
    ]
    settings.write_text(json.dumps(data))

    assert install_claude_hooks(settings, HOOK) is True
    [hook] = fleet_entries(json.loads(settings.read_text()), 'Stop')
    assert hook['command'] != old_command
    assert HOOK in str(hook['command'])


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


def copilot_hook_commands() -> dict[str, str]:
    path = Path(__file__).parent.parent / 'config/copilot/hooks/fleet.json'
    hooks = json.loads(path.read_text())['hooks']
    return {event: entry['bash'] for event, [entry] in hooks.items()}


def test_copilot_hook_commands_run_the_hook(tmp_path: Path) -> None:
    hook, log = fake_hook(tmp_path)
    for command in copilot_hook_commands().values():
        assert run_shell(command, {'FLEET_HOOK': str(hook)}).returncode == 0
    assert sorted(log.read_text().splitlines()) == sorted(
        f'copilot {event}' for event in COPILOT_EVENT_STATES
    )


def test_copilot_hook_commands_are_silent_when_hook_is_gone(
    tmp_path: Path,
) -> None:
    missing = {'FLEET_HOOK': str(tmp_path / 'gone.sh')}
    for command in copilot_hook_commands().values():
        result = run_shell(command, missing)
        assert (result.returncode, result.stdout, result.stderr) == (0, '', '')


def test_copilot_install_links_hook_file_and_is_idempotent(
    tmp_path: Path,
) -> None:
    source = tmp_path / 'fleet.json'
    source.write_text('{}')
    link = tmp_path / '.copilot' / 'hooks' / 'fleet.json'
    assert not copilot_hooks_installed(link)
    assert install_copilot_hooks(link, source) is True
    assert link.resolve() == source
    assert copilot_hooks_installed(link)
    assert install_copilot_hooks(link, source) is False


def test_copilot_install_refuses_to_overwrite_a_real_file(
    tmp_path: Path,
) -> None:
    source = tmp_path / 'fleet.json'
    source.write_text('{}')
    link = tmp_path / 'hooks' / 'fleet.json'
    link.parent.mkdir()
    link.write_text('mine')
    with pytest.raises(ValueError, match='not a symlink'):
        install_copilot_hooks(link, source)
    assert link.read_text() == 'mine'


@pytest.mark.parametrize('installed', [True, False])
def test_copilot_uninstall_only_removes_the_link(
    tmp_path: Path,
    installed: bool,  # noqa: FBT001
) -> None:
    source = tmp_path / 'fleet.json'
    source.write_text('{}')
    link = tmp_path / 'hooks' / 'fleet.json'
    if installed:
        install_copilot_hooks(link, source)
    assert uninstall_copilot_hooks(link) is installed
    assert not link.is_symlink()
    assert source.exists()


def test_installed_status(settings: Path, tmp_path: Path) -> None:
    assert not claude_hooks_installed(settings)
    assert not claude_hooks_installed(tmp_path / 'missing.json')
    install_claude_hooks(settings, HOOK)
    assert claude_hooks_installed(settings)
