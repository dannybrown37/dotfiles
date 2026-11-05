"""Tests for fleet.procs: finding agent sessions fleet did not start."""

from pathlib import Path

import pytest

from fleet.proclite import agent_kind, find_agent_ancestor
from fleet.procs import AgentProcess, scan_agent_processes


def fake_process(
    proc: Path,
    pid: int,
    argv: list[str],
    *,
    ppid: int = 1,
    cwd: str = '/home/u/projects/api',
    env: dict[str, str] | None = None,
    state: str = 'S',
    start_time: int = 1000,
) -> None:
    path = proc / str(pid)
    path.mkdir(parents=True)
    (path / 'cmdline').write_bytes(
        b'\0'.join(a.encode() for a in argv) + b'\0',
    )
    (path / 'environ').write_bytes(
        b'\0'.join(f'{k}={v}'.encode() for k, v in (env or {}).items())
        + b'\0',
    )
    # Field 2 (comm) may hold spaces and parens, so parsing must split on ')'.
    fields = [state, str(ppid)] + ['0'] * 17 + [str(start_time)]
    (path / 'stat').write_text(f'{pid} (weird ) name) {" ".join(fields)}\n')
    (path / 'cwd').symlink_to(cwd)


TMUX_ENV = {'TMUX': '/run/tmux-1000/default,123,0', 'TMUX_PANE': '%25'}
VERSIONED = '/home/u/.local/share/claude/versions/2.1.300'


@pytest.mark.parametrize(
    ('argv', 'expected'),
    [
        (['claude'], 'claude'),
        (['/home/u/.local/bin/claude', '--continue'], 'claude'),
        ([VERSIONED, '--session-id', 'x'], 'claude'),
        (['copilot', '-n', 'x'], 'copilot'),
        (
            ['node', '/usr/lib/node_modules/@github/copilot/index.js'],
            'copilot',
        ),
        (['bash', '-c', 'claude'], None),
        (['vim', 'claude.md'], None),
        ([], None),
    ],
)
def test_agent_kind(argv: list[str], expected: str | None) -> None:
    assert agent_kind(argv) == expected


def test_scan_finds_interactive_sessions_with_their_pane(
    tmp_path: Path,
) -> None:
    fake_process(tmp_path, 10, ['claude'], env=TMUX_ENV)
    fake_process(tmp_path, 11, ['copilot'], cwd='/home/u/projects/web')
    procs = scan_agent_processes(tmp_path)
    assert procs == [
        AgentProcess(
            pid=10,
            kind='claude',
            cwd='/home/u/projects/api',
            start_time=1000,
            tmux_socket='default',
            tmux_pane='%25',
            fleet_agent='',
            background=False,
        ),
        AgentProcess(
            pid=11,
            kind='copilot',
            cwd='/home/u/projects/web',
            start_time=1000,
            tmux_socket='',
            tmux_pane='',
            fleet_agent='',
            background=False,
        ),
    ]


@pytest.mark.parametrize(
    'argv',
    [
        ['claude', '-p', 'summarize'],
        ['claude', '--print'],
        ['copilot', '-p', 'x', '-s'],
        ['/home/u/.local/bin/claude', 'daemon', 'run'],
        ['claude', 'bg-spare', '--bg-spare', 'x.sock'],
        ['claude', 'bg-pty-host', '--bg-pty-host', 'x.sock'],
        ['claude', '--version'],
    ],
)
def test_scan_skips_non_interactive_and_plumbing(
    tmp_path: Path,
    argv: list[str],
) -> None:
    fake_process(tmp_path, 10, argv)
    assert scan_agent_processes(tmp_path) == []


def test_scan_skips_stopped_and_zombie_processes(tmp_path: Path) -> None:
    fake_process(tmp_path, 10, ['claude'], state='T')
    fake_process(tmp_path, 11, ['claude'], state='Z')
    assert scan_agent_processes(tmp_path) == []


def test_scan_skips_agent_children_of_agents(tmp_path: Path) -> None:
    fake_process(tmp_path, 10, ['copilot'])
    fake_process(tmp_path, 11, ['copilot'], ppid=10)
    assert [p.pid for p in scan_agent_processes(tmp_path)] == [10]


def test_scan_marks_claude_background_sessions(tmp_path: Path) -> None:
    fake_process(
        tmp_path,
        10,
        ['claude', 'bg-pty-host', '--bg-pty-host', 's', '--', VERSIONED],
    )
    fake_process(tmp_path, 11, [VERSIONED, '--session-id', 'abc'], ppid=10)
    procs = scan_agent_processes(tmp_path)
    assert [(p.pid, p.background) for p in procs] == [(11, True)]


def test_scan_handles_retitled_argv0(tmp_path: Path) -> None:
    """Claude rewrites its title, folding the subcommand into argv[0]."""
    fake_process(
        tmp_path,
        10,
        ['claude bg-pty-host', '--bg-pty-host', 's', '--', VERSIONED],
    )
    fake_process(tmp_path, 11, [VERSIONED, '--session-id', 'abc'], ppid=10)
    procs = scan_agent_processes(tmp_path)
    assert [(p.pid, p.background) for p in procs] == [(11, True)]


def test_scan_reports_fleet_agent_name(tmp_path: Path) -> None:
    fake_process(tmp_path, 10, ['claude'], env={'FLEET_AGENT': 'fix-x'})
    assert scan_agent_processes(tmp_path)[0].fleet_agent == 'fix-x'


def test_scan_survives_processes_vanishing_mid_scan(tmp_path: Path) -> None:
    fake_process(tmp_path, 10, ['claude'])
    (tmp_path / '11').mkdir()
    (tmp_path / 'self').mkdir()
    assert [p.pid for p in scan_agent_processes(tmp_path)] == [10]


def test_find_agent_ancestor_walks_up_from_hook(tmp_path: Path) -> None:
    fake_process(tmp_path, 10, ['claude'], start_time=555)
    fake_process(
        tmp_path,
        20,
        ['/bin/sh', '-c', 'fleet-hook.sh claude Stop'],
        ppid=10,
    )
    fake_process(tmp_path, 30, ['bash', 'fleet-hook.sh'], ppid=20)
    assert find_agent_ancestor(30, str(tmp_path)) == (10, 555)


def test_find_agent_ancestor_none_outside_an_agent(tmp_path: Path) -> None:
    fake_process(tmp_path, 20, ['bash'])
    fake_process(tmp_path, 30, ['python3'], ppid=20)
    assert find_agent_ancestor(30, str(tmp_path)) is None
