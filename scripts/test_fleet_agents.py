"""Tests for fleet.agents: launch commands and hook-event state mapping."""

import json
import subprocess
from pathlib import Path

import pytest

from fleet.agents import (
    AgentState,
    claude_hook_settings,
    launch_command,
    state_for_event,
    validate_agent_name,
)


@pytest.mark.parametrize(
    ('kind', 'event', 'payload', 'expected'),
    [
        ('claude', 'UserPromptSubmit', {}, AgentState.WORKING),
        ('claude', 'PostToolUse', {}, AgentState.WORKING),
        ('claude', 'Stop', {}, AgentState.IDLE),
        ('claude', 'SessionStart', {}, AgentState.IDLE),
        ('claude', 'SessionEnd', {}, AgentState.EXITED),
        (
            'claude',
            'Notification',
            {'notification_type': 'permission_prompt'},
            AgentState.WAITING,
        ),
        (
            'claude',
            'Notification',
            {'notification_type': 'idle_prompt'},
            AgentState.IDLE,
        ),
        ('claude', 'Notification', {}, AgentState.WAITING),
        ('claude', 'PreCompact', {}, None),
        ('copilot', 'userPromptSubmitted', {}, AgentState.WORKING),
        ('copilot', 'postToolUse', {}, AgentState.WORKING),
        ('copilot', 'agentStop', {}, AgentState.IDLE),
        ('copilot', 'sessionStart', {}, AgentState.IDLE),
        ('copilot', 'sessionEnd', {}, AgentState.EXITED),
        ('copilot', 'permissionRequest', {}, AgentState.WAITING),
        ('copilot', 'notification', {}, AgentState.WAITING),
        (
            'copilot',
            'notification',
            {'notification_type': 'idle_prompt'},
            AgentState.IDLE,
        ),
        ('copilot', 'errorOccurred', {}, AgentState.ERROR),
        ('copilot', 'Stop', {}, None),
        ('unknown', 'Stop', {}, None),
    ],
)
def test_state_for_event(
    kind: str,
    event: str,
    payload: dict[str, object],
    expected: AgentState | None,
) -> None:
    assert state_for_event(kind, event, payload) == expected


@pytest.mark.parametrize(
    'name',
    ['fix-flaky', 'review_42', 'a', 'Abc-1'],
)
def test_validate_agent_name_accepts(name: str) -> None:
    assert validate_agent_name(name) == name


@pytest.mark.parametrize(
    'name',
    ['', '-lead', 'has space', 'a:b', 'a.b', 'a/b', 'x' * 61, '$(rm)'],
)
def test_validate_agent_name_rejects(name: str) -> None:
    with pytest.raises(ValueError, match='agent name'):
        validate_agent_name(name)


def test_claude_launch_command_passes_hooks_name_and_prompt_last() -> None:
    cmd = launch_command(
        'claude',
        name='fix-x',
        prompt='--not-a-flag fix it',
        hook_path='/d/fleet-hook.sh',
        extra_args=['--permission-mode', 'acceptEdits'],
        binary='claude',
    )
    assert cmd[0] == 'claude'
    assert cmd[cmd.index('-n') + 1] == 'fix-x'
    assert cmd[-2:] == ['--', '--not-a-flag fix it']
    assert '--permission-mode' in cmd
    settings = json.loads(cmd[cmd.index('--settings') + 1])
    assert 'Stop' in settings['hooks']


def test_claude_launch_skips_settings_when_hooks_are_global() -> None:
    """Global hooks already report state; per-launch ones would double it."""
    cmd = launch_command(
        'claude',
        name='x',
        prompt='go',
        hook_path='/h',
        extra_args=[],
        binary='claude',
        with_hooks=False,
    )
    assert cmd == ['claude', '-n', 'x', '--', 'go']


def test_claude_launch_command_without_prompt_has_no_separator() -> None:
    cmd = launch_command(
        'claude',
        name='x',
        prompt='',
        hook_path='/h',
        extra_args=[],
        binary='claude',
    )
    assert '--' not in cmd


def test_copilot_launch_command_uses_interactive_prompt_flag() -> None:
    cmd = launch_command(
        'copilot',
        name='fix-x',
        prompt='fix it',
        hook_path='/h',
        extra_args=[],
        binary='/opt/copilot',
    )
    assert cmd == ['/opt/copilot', '-n', 'fix-x', '-i', 'fix it']


def test_copilot_launch_command_without_prompt() -> None:
    cmd = launch_command(
        'copilot',
        name='x',
        prompt='',
        hook_path='/h',
        extra_args=['--model', 'auto'],
        binary='copilot',
    )
    assert cmd == ['copilot', '-n', 'x', '--model', 'auto']


def test_launch_command_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match='agent kind'):
        launch_command(
            'gemini',
            name='x',
            prompt='',
            hook_path='/h',
            extra_args=[],
            binary='gemini',
        )


@pytest.mark.parametrize('exists', [True, False])
def test_claude_hook_command_handles_spaces_and_a_missing_hook(
    tmp_path: Path,
    exists: bool,  # noqa: FBT001
) -> None:
    hook_dir = tmp_path / 'my dir'
    hook_dir.mkdir()
    hook = hook_dir / 'fleet-hook.sh'
    log = tmp_path / 'argv.log'
    if exists:
        hook.write_text(f'#!/bin/sh\necho "$@" > "{log}"\n')
        hook.chmod(0o755)
    [entry] = claude_hook_settings(str(hook))['hooks']['Stop']
    result = subprocess.run(  # noqa: S603
        ['bash', '-c', str(entry['hooks'][0]['command'])],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode, result.stdout, result.stderr) == (0, '', '')
    ran_with = log.read_text() if log.exists() else None
    assert ran_with == ('claude Stop\n' if exists else None)
