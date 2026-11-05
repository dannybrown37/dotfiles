"""Find running Claude Code and Copilot sessions by reading /proc."""

import os
from dataclasses import dataclass
from pathlib import Path

from fleet.proclite import agent_kind, environ_value, read_proc

PROC = Path('/proc')
NON_INTERACTIVE_FLAGS = frozenset(
    {'-p', '--print', '--prompt', '--version', '-v'},
)
PLUMBING_SUBCOMMANDS = frozenset(
    {'daemon', 'bg-pty-host', 'bg-spare', 'mcp', 'update'},
)
DEAD_STATES = frozenset({'T', 't', 'Z', 'X'})


@dataclass(frozen=True)
class AgentProcess:
    pid: int
    kind: str
    cwd: str
    start_time: int
    tmux_socket: str
    tmux_pane: str
    fleet_agent: str
    background: bool


@dataclass(frozen=True)
class ProcInfo:
    pid: int
    ppid: int
    state: str
    start_time: int
    argv: list[str]


def boot_time(proc_root: Path = PROC) -> float:
    try:
        stat = (proc_root / 'stat').read_text()
    except OSError:
        return 0.0
    for line in stat.splitlines():
        if line.startswith('btime '):
            return float(line.split()[1])
    return 0.0


def process_started_at(start_time: int, proc_root: Path = PROC) -> float:
    """/proc start times are clock ticks since boot."""
    return boot_time(proc_root) + start_time / os.sysconf('SC_CLK_TCK')


def is_interactive(argv: list[str]) -> bool:
    if len(argv) > 1 and argv[1] in PLUMBING_SUBCOMMANDS:
        return False
    return not NON_INTERACTIVE_FLAGS.intersection(argv[1:])


def tmux_socket_name(tmux_env: str) -> str:
    """`TMUX=/tmp/tmux-1000/default,123,0` -> `default`."""
    socket_path = tmux_env.split(',', 1)[0]
    return socket_path.rsplit('/', 1)[-1] if socket_path else ''


def scan_processes(proc_root: Path) -> dict[int, ProcInfo]:
    infos = {}
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        info = read_proc(str(proc_root), int(entry.name))
        if info is not None:
            ppid, state, start_time, argv = info
            infos[int(entry.name)] = ProcInfo(
                int(entry.name),
                ppid,
                state,
                start_time,
                argv,
            )
    return infos


def scan_agent_processes(proc_root: Path = PROC) -> list[AgentProcess]:
    infos = scan_processes(proc_root)
    agents = []
    for info in sorted(infos.values(), key=lambda i: i.pid):
        kind = agent_kind(info.argv)
        if (
            kind is None
            or info.state in DEAD_STATES
            or not is_interactive(info.argv)
        ):
            continue
        parent = infos.get(info.ppid)
        background = bool(parent and parent.argv[1:2] == ['bg-pty-host'])
        if parent and agent_kind(parent.argv) and not background:
            continue
        try:
            cwd = str((proc_root / str(info.pid) / 'cwd').readlink())
        except OSError:
            continue
        root = str(proc_root)
        agents.append(
            AgentProcess(
                pid=info.pid,
                kind=kind,
                cwd=cwd,
                start_time=info.start_time,
                tmux_socket=tmux_socket_name(
                    environ_value(root, info.pid, 'TMUX'),
                ),
                tmux_pane=environ_value(root, info.pid, 'TMUX_PANE'),
                fleet_agent=environ_value(root, info.pid, 'FLEET_AGENT'),
                background=background,
            ),
        )
    return agents
