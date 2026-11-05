"""Tests for scripts/fleet-hook.sh, the entry both agent CLIs call."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from fleet import hook
from fleet.agents import AgentState
from fleet.store import Store

HOOK = Path(__file__).parent / 'fleet-hook.sh'


def run_hook(
    args: list[str],
    stdin: str,
    env_overrides: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith('FLEET_')}
    return subprocess.run(  # noqa: S603
        [str(HOOK), *args],
        input=stdin,
        env={**env, **env_overrides},
        capture_output=True,
        text=True,
        check=False,
    )


def read_state(state_dir: Path, name: str) -> dict[str, object]:
    path = state_dir / 'agents' / f'{name}.state.json'
    return json.loads(path.read_text())


def test_hook_writes_state_for_fleet_agent(tmp_path: Path) -> None:
    result = run_hook(
        ['claude', 'Stop'],
        '{"session_id": "s"}',
        {'FLEET_AGENT': 'fix-x', 'FLEET_STATE_DIR': str(tmp_path)},
    )
    assert result.returncode == 0
    assert read_state(tmp_path, 'fix-x')['state'] == 'idle'


def test_hook_records_launch_id(tmp_path: Path) -> None:
    run_hook(
        ['claude', 'Stop'],
        '{}',
        {
            'FLEET_AGENT': 'fix-x',
            'FLEET_LAUNCH_ID': 'abc123',
            'FLEET_STATE_DIR': str(tmp_path),
        },
    )
    assert read_state(tmp_path, 'fix-x')['launch_id'] == 'abc123'


def test_hook_keeps_notification_message(tmp_path: Path) -> None:
    run_hook(
        ['claude', 'Notification'],
        json.dumps({'message': 'Claude needs permission to use Bash'}),
        {'FLEET_AGENT': 'fix-x', 'FLEET_STATE_DIR': str(tmp_path)},
    )
    state = read_state(tmp_path, 'fix-x')
    assert state['state'] == 'waiting'
    assert state['message'] == 'Claude needs permission to use Bash'


def test_hook_without_fleet_agent_writes_no_agent_state(
    tmp_path: Path,
) -> None:
    result = run_hook(
        ['copilot', 'agentStop'],
        '{}',
        {'FLEET_STATE_DIR': str(tmp_path)},
    )
    assert result.returncode == 0
    assert not (tmp_path / 'agents').exists()


@pytest.mark.parametrize(
    'stdin',
    ['not json', '', '[1, 2]'],
)
def test_hook_survives_bad_stdin(tmp_path: Path, stdin: str) -> None:
    result = run_hook(
        ['copilot', 'agentStop'],
        stdin,
        {'FLEET_AGENT': 'a', 'FLEET_STATE_DIR': str(tmp_path)},
    )
    assert result.returncode == 0
    assert read_state(tmp_path, 'a')['state'] == 'idle'


def test_hook_is_silent_on_stdout(tmp_path: Path) -> None:
    """Claude feeds UserPromptSubmit stdout to the model as context."""
    result = run_hook(
        ['claude', 'UserPromptSubmit'],
        '{"prompt": "hi"}',
        {'FLEET_AGENT': 'a', 'FLEET_STATE_DIR': str(tmp_path)},
    )
    assert result.stdout == ''
    assert result.stderr == ''


def test_hook_exits_zero_when_state_dir_unwritable(tmp_path: Path) -> None:
    blocker = tmp_path / 'file'
    blocker.write_text('')
    result = run_hook(
        ['claude', 'Stop'],
        '{}',
        {'FLEET_AGENT': 'a', 'FLEET_STATE_DIR': str(blocker / 'sub')},
    )
    assert result.returncode == 0


def test_hook_ignores_unmapped_event(tmp_path: Path) -> None:
    run_hook(
        ['claude', 'PreCompact'],
        '{}',
        {'FLEET_AGENT': 'a', 'FLEET_STATE_DIR': str(tmp_path)},
    )
    assert not (tmp_path / 'agents').exists()


AGENT_PID = 4242
AGENT_START = 99


@pytest.fixture
def agent_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        'fleet.hook.find_agent_ancestor',
        lambda _pid: (AGENT_PID, AGENT_START),
    )


@pytest.mark.usefixtures('agent_parent')
def test_handle_writes_session_state_for_any_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv('FLEET_AGENT', raising=False)
    monkeypatch.setenv('FLEET_STATE_DIR', str(tmp_path))
    hook.handle('claude', 'Notification', '{"message": "allow Bash?"}')
    live = Store(tmp_path).read_session(AGENT_PID, AGENT_START)
    assert live is not None
    assert (live.state, live.message) == (AgentState.WAITING, 'allow Bash?')
    assert not (tmp_path / 'agents').exists()


@pytest.mark.usefixtures('agent_parent')
@pytest.mark.parametrize(
    'message',
    ['say "hi"\nthen \\ leave', 'naïve café ✓', '\t\x07ctrl'],
)
def test_handle_writes_valid_json_for_awkward_messages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message: str,
) -> None:
    monkeypatch.setenv('FLEET_AGENT', 'fix-x')
    monkeypatch.setenv('FLEET_STATE_DIR', str(tmp_path))
    hook.handle('copilot', 'notification', json.dumps({'message': message}))
    assert read_state(tmp_path, 'fix-x')['message'] == message
    live = Store(tmp_path).read_session(AGENT_PID, AGENT_START)
    assert live is not None
    assert live.message == message


@pytest.mark.usefixtures('agent_parent')
def test_handle_bad_fleet_name_still_records_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('FLEET_AGENT', '../escape')
    monkeypatch.setenv('FLEET_STATE_DIR', str(tmp_path))
    with pytest.raises(ValueError, match='agent name'):
        hook.handle('claude', 'Stop', '{}')
    assert Store(tmp_path).read_session(AGENT_PID, AGENT_START) is not None


def test_handle_without_agent_ancestor_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv('FLEET_AGENT', raising=False)
    monkeypatch.setenv('FLEET_STATE_DIR', str(tmp_path))
    monkeypatch.setattr('fleet.hook.find_agent_ancestor', lambda _pid: None)
    hook.handle('claude', 'Stop', '{}')
    assert list(tmp_path.iterdir()) == []


def test_hook_rejects_agent_name_with_path_traversal(tmp_path: Path) -> None:
    run_hook(
        ['claude', 'Stop'],
        '{}',
        {'FLEET_AGENT': '../escape', 'FLEET_STATE_DIR': str(tmp_path)},
    )
    assert not (tmp_path / 'escape.state.json').exists()
    assert not (tmp_path / 'agents').exists()
