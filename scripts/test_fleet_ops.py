"""Tests for fleet.ops: spawning agents into tmux and reading their state.

The end-to-end tests drive a real tmux server on a private socket with a
fake agent binary, so nothing touches the user's own tmux sessions.
"""

import os
import shutil
import subprocess
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from fleet.agents import AgentState
from fleet.ops import (
    SpawnRequest,
    agent_views,
    dashboard_rows,
    ensure_dashboard,
    kill_agent,
    resolve_state,
    spawn_agent,
)
from fleet.procs import AgentProcess
from fleet.store import LiveState, Store
from fleet.tmux import PaneInfo, Tmux

HOOK = Path(__file__).parent / 'fleet-hook.sh'
GIT_ENV = {
    'GIT_CONFIG_GLOBAL': '/dev/null',
    'GIT_AUTHOR_NAME': 't',
    'GIT_AUTHOR_EMAIL': 't@t',
    'GIT_COMMITTER_NAME': 't',
    'GIT_COMMITTER_EMAIL': 't@t',
}

# Records its argv/cwd, reports "idle" through the real hook, then echoes
# each line it is sent so tests can see what reached it.
FAKE_AGENT = """#!/usr/bin/env bash
out="${FAKE_AGENT_OUT}"
printf '%s\\n' "$@" > "${out}.args"
pwd > "${out}.cwd"
echo '{}' | "${FLEET_HOOK}" claude Stop
while IFS= read -r line; do
    printf '%s\\n' "${line}" >> "${out}.input"
    [[ "${line}" == quit ]] && exit 0
done
"""


def live(state: AgentState) -> LiveState:
    return LiveState(state=state, event='e', message='', updated_at=1.0)


def pane(*, dead: bool = False) -> PaneInfo:
    return PaneInfo(
        window_id='@1',
        window_name='x',
        pane_id='%1',
        dead=dead,
        session='fleet',
    )


@pytest.mark.parametrize(
    ('live_state', 'pane_info', 'age', 'expected'),
    [
        (live(AgentState.WORKING), None, 1, AgentState.GONE),
        (live(AgentState.WORKING), pane(dead=True), 1, AgentState.EXITED),
        (None, pane(dead=True), 1, AgentState.EXITED),
        (None, pane(), 1, AgentState.UNKNOWN),
        (live(AgentState.WAITING), pane(), 1, AgentState.WAITING),
        (live(AgentState.IDLE), pane(), 999, AgentState.IDLE),
        # No hook yet long after launch: a trust/login dialog is waiting.
        (None, pane(), 60, AgentState.WAITING),
    ],
)
def test_resolve_state(
    live_state: LiveState | None,
    pane_info: PaneInfo | None,
    age: float,
    expected: AgentState,
) -> None:
    assert resolve_state(live_state, pane_info, age) == expected


needs_tmux = pytest.mark.skipif(
    shutil.which('tmux') is None,
    reason='tmux not installed',
)


def wait_for(predicate: Callable[[], bool], timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    msg = 'condition not met before timeout'
    raise AssertionError(msg)


@pytest.fixture
def tmux() -> Iterator[Tmux]:
    server = Tmux(socket=f'fleet-test-{uuid.uuid4().hex[:8]}')
    yield server
    subprocess.run(  # noqa: S603
        [*server.base, 'kill-server'],
        check=False,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key, value in GIT_ENV.items():
        monkeypatch.setenv(key, value)
    path = tmp_path / 'proj'
    path.mkdir()
    for cmd in (
        ['git', 'init', '-q', '-b', 'main'],
        ['git', 'commit', '-q', '--allow-empty', '-m', 'init'],
    ):
        subprocess.run(  # noqa: S603
            cmd,
            cwd=path,
            check=True,
            env={**os.environ, **GIT_ENV},
        )
    return path


@pytest.fixture
def fake_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    binary = tmp_path / 'fake-agent'
    binary.write_text(FAKE_AGENT)
    binary.chmod(0o755)
    out = tmp_path / 'agent-out'
    monkeypatch.setenv('FAKE_AGENT_OUT', str(out))
    return out


def make_request(
    repo: Path,
    tmp_path: Path,
    name: str = 'fix-x',
) -> SpawnRequest:
    return SpawnRequest(
        kind='claude',
        name=name,
        repo_dir=repo,
        base='',
        prompt='fix the thing',
        extra_args=[],
        binary=str(tmp_path / 'fake-agent'),
        hook_path=str(HOOK),
        session='fleet',
    )


@needs_tmux
def test_spawn_agent_end_to_end(
    tmux: Tmux,
    repo: Path,
    fake_agent: Path,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / 'state')
    record = spawn_agent(store, tmux, make_request(repo, tmp_path))

    assert record.base == 'main'
    assert record.worktree == str(repo.parent / 'proj-worktrees' / 'fix-x')
    assert store.load('fix-x') == record

    args_file = fake_agent.with_suffix('.args')
    wait_for(args_file.exists)
    args = args_file.read_text().splitlines()
    assert args[-2:] == ['--', 'fix the thing']
    assert (
        fake_agent.with_suffix('.cwd').read_text().strip() == record.worktree
    )

    wait_for(lambda: store.read_state('fix-x') is not None)
    views = agent_views(store, tmux)
    assert [(v.record.name, v.state) for v in views] == [
        ('fix-x', AgentState.IDLE),
    ]

    tmux.send_text(record.window_id, 'hello agent')
    input_file = fake_agent.with_suffix('.input')
    wait_for(
        lambda: (
            input_file.exists() and 'hello agent' in input_file.read_text()
        ),
    )

    tmux.send_text(record.window_id, 'quit')
    wait_for(lambda: agent_views(store, tmux)[0].state == AgentState.EXITED)


def discovered(
    pid: int,
    *,
    socket: str = '',
    pane: str = '',
    fleet_agent: str = '',
    background: bool = False,
    cwd: str = '/home/u/projects/api',
) -> AgentProcess:
    return AgentProcess(
        pid=pid,
        kind='claude',
        cwd=cwd,
        start_time=500,
        tmux_socket=socket,
        tmux_pane=pane,
        fleet_agent=fleet_agent,
        background=background,
    )


@needs_tmux
def test_dashboard_rows_include_sessions_fleet_did_not_start(
    tmux: Tmux,
    tmp_path: Path,
) -> None:
    window_id = tmux.new_window(
        'mine',
        'editor',
        tmp_path,
        {},
        ['sleep', '30'],
    )
    pane_id = tmux.panes()[window_id].pane_id
    store = Store(tmp_path / 'state')
    store.write_session(
        11,
        500,
        AgentState.WAITING,
        'Notification',
        'allow?',
        1.0,
    )
    procs = [
        discovered(11, socket=tmux.socket_name, pane=pane_id),
        discovered(12, cwd='/home/u/projects/web'),
        discovered(13, background=True),
        discovered(14, fleet_agent='fix-x'),
    ]
    rows = {row.key: row for row in dashboard_rows(store, tmux, procs)}
    assert set(rows) == {'pid:11', 'pid:12', 'pid:13'}
    in_tmux = rows['pid:11']
    assert (in_tmux.state, in_tmux.message) == (AgentState.WAITING, 'allow?')
    assert in_tmux.target == pane_id
    assert in_tmux.where == 'tmux mine:editor'
    assert in_tmux.name == 'api'
    assert in_tmux.record is None
    assert (rows['pid:12'].state, rows['pid:12'].target) == (
        AgentState.UNKNOWN,
        '',
    )
    assert rows['pid:12'].where == 'terminal'
    assert rows['pid:13'].where == 'background'


@needs_tmux
def test_dashboard_rows_ignore_pane_ids_from_another_tmux_server(
    tmux: Tmux,
    tmp_path: Path,
) -> None:
    window_id = tmux.new_window(
        'mine',
        'editor',
        tmp_path,
        {},
        ['sleep', '30'],
    )
    pane_id = tmux.panes()[window_id].pane_id
    procs = [discovered(11, socket='some-other-server', pane=pane_id)]
    [row] = dashboard_rows(Store(tmp_path / 'state'), tmux, procs)
    assert row.target == ''


@needs_tmux
def test_dashboard_rows_prune_state_of_dead_sessions(
    tmux: Tmux,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / 'state')
    store.write_session(99, 1, AgentState.IDLE, 'Stop', '', 1.0)
    dashboard_rows(store, tmux, [])
    assert not store.session_path(99).exists()


@needs_tmux
def test_dashboard_rows_list_fleet_agents_with_window_target(
    tmux: Tmux,
    repo: Path,
    fake_agent: Path,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / 'state')
    record = spawn_agent(store, tmux, make_request(repo, tmp_path))
    [row] = dashboard_rows(store, tmux, [])
    assert (row.key, row.target, row.where) == (
        'agent:fix-x',
        record.window_id,
        'fleet',
    )
    assert row.record == record
    assert row.diff_base == 'main'


@needs_tmux
def test_ensure_dashboard_is_idempotent(tmux: Tmux, tmp_path: Path) -> None:
    command = ['bash', '-c', 'sleep 30']
    first = ensure_dashboard(tmux, 'fleet', command, tmp_path)
    second = ensure_dashboard(tmux, 'fleet', command, tmp_path)
    assert first == second
    dash_windows = [
        p for p in tmux.panes().values() if p.window_name == 'dash'
    ]
    assert len(dash_windows) == 1


@needs_tmux
def test_ensure_dashboard_respawns_after_quit(
    tmux: Tmux,
    tmp_path: Path,
) -> None:
    """Pressing q in the dashboard must not leave Alt+W on a dead pane."""
    marker = tmp_path / 'second-run'
    command = ['bash', '-c', f'test -f {marker} || exit 0; sleep 30']
    window_id = ensure_dashboard(tmux, 'fleet', command, tmp_path)
    wait_for(lambda: tmux.panes()[window_id].dead)
    marker.write_text('')
    assert ensure_dashboard(tmux, 'fleet', command, tmp_path) == window_id
    wait_for(lambda: not tmux.panes()[window_id].dead)


@needs_tmux
def test_ensure_dashboard_joins_session_agents_already_use(
    tmux: Tmux,
    repo: Path,
    fake_agent: Path,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    record = spawn_agent(
        Store(tmp_path / 'state'),
        tmux,
        make_request(repo, tmp_path),
    )
    dash = ensure_dashboard(
        tmux,
        'fleet',
        ['bash', '-c', 'sleep 30'],
        tmp_path,
    )
    panes = tmux.panes()
    assert panes[dash].session == panes[record.window_id].session == 'fleet'


@needs_tmux
def test_spawn_second_agent_joins_existing_session(
    tmux: Tmux,
    repo: Path,
    fake_agent: Path,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / 'state')
    first = spawn_agent(store, tmux, make_request(repo, tmp_path, 'one'))
    second = spawn_agent(store, tmux, make_request(repo, tmp_path, 'two'))
    assert first.window_id != second.window_id
    panes = tmux.panes()
    assert panes[first.window_id].session == 'fleet'
    assert panes[second.window_id].window_name == 'two'


@needs_tmux
def test_agent_that_dies_at_once_keeps_its_window(
    tmux: Tmux,
    repo: Path,
    tmp_path: Path,
) -> None:
    """A missing or crashing agent CLI must show as exited, not vanish."""
    store = Store(tmp_path / 'state')
    request = make_request(repo, tmp_path)
    crashing = SpawnRequest(**{**request.__dict__, 'binary': 'false'})
    record = spawn_agent(store, tmux, crashing)
    wait_for(lambda: agent_views(store, tmux)[0].state == AgentState.EXITED)
    assert record.window_id in tmux.panes()


@needs_tmux
def test_reused_name_ignores_late_state_from_killed_agent(
    tmux: Tmux,
    repo: Path,
    tmp_path: Path,
) -> None:
    """A killed Claude fires SessionEnd after `fleet rm` deleted its state."""
    store = Store(tmp_path / 'state')
    store.write_state('fix-x', AgentState.EXITED, 'SessionEnd', '', 1.0)
    silent_agent = tmp_path / 'silent-agent'
    silent_agent.write_text('#!/bin/sh\nexec sleep 30\n')
    silent_agent.chmod(0o755)
    request = make_request(repo, tmp_path)
    spawn_agent(
        store,
        tmux,
        SpawnRequest(**{**request.__dict__, 'binary': str(silent_agent)}),
    )
    assert agent_views(store, tmux)[0].state == AgentState.UNKNOWN


@needs_tmux
def test_spawn_refuses_duplicate_name(
    tmux: Tmux,
    repo: Path,
    fake_agent: Path,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / 'state')
    spawn_agent(store, tmux, make_request(repo, tmp_path))
    with pytest.raises(ValueError, match='already exists'):
        spawn_agent(store, tmux, make_request(repo, tmp_path))


@needs_tmux
def test_kill_agent_keeps_worktree_unless_asked(
    tmux: Tmux,
    repo: Path,
    fake_agent: Path,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / 'state')
    record = spawn_agent(store, tmux, make_request(repo, tmp_path))
    kill_agent(store, tmux, record, remove_checkout=False, force=False)
    assert record.window_id not in tmux.panes()
    assert Path(record.worktree).is_dir()
    assert store.list_records() == []


@needs_tmux
def test_kill_agent_refuses_dirty_worktree_without_force(
    tmux: Tmux,
    repo: Path,
    fake_agent: Path,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / 'state')
    record = spawn_agent(store, tmux, make_request(repo, tmp_path))
    (Path(record.worktree) / 'wip.txt').write_text('unsaved work')
    with pytest.raises(ValueError, match='uncommitted'):
        kill_agent(store, tmux, record, remove_checkout=True, force=False)
    assert Path(record.worktree, 'wip.txt').exists()
    assert store.list_records() == [record]
