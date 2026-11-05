"""Minimal /proc readers shared by the hook and fleet.procs.

Imports nothing beyond os, for the same reason as fleet.events.
"""

CLAUDE_VERSIONS_DIR = '/claude/versions'


def agent_kind(argv: list[str]) -> str | None:
    if not argv:
        return None
    program = argv[0]
    directory, _, name = program.rpartition('/')
    if name == 'claude' or directory.endswith(CLAUDE_VERSIONS_DIR):
        return 'claude'
    if name == 'copilot':
        return 'copilot'
    if name == 'node' and any('@github/copilot' in arg for arg in argv[1:2]):
        return 'copilot'
    return None


def read_proc(
    proc_root: str,
    pid: int,
) -> tuple[int, str, int, list[str]] | None:
    """(ppid, state, start_time, argv), or None if the process is gone."""
    base = f'{proc_root}/{pid}'
    try:
        with open(f'{base}/cmdline', 'rb') as cmdline_file:  # noqa: PTH123
            raw_argv = cmdline_file.read()
        with open(f'{base}/stat') as stat_file:  # noqa: PTH123
            stat = stat_file.read()
    except OSError:
        return None
    # comm (field 2) can contain spaces and ')', so split after the last ')'.
    fields = stat.rpartition(')')[2].split()
    if len(fields) < 20:  # noqa: PLR2004
        return None
    argv = [
        arg.decode(errors='replace') for arg in raw_argv.split(b'\0') if arg
    ]
    # A retitled process folds args into argv[0]: "claude bg-pty-host".
    if argv and ' ' in argv[0] and not argv[0].startswith('/'):
        argv = argv[0].split() + argv[1:]
    return int(fields[1]), fields[0], int(fields[19]), argv


def find_agent_ancestor(
    pid: int,
    proc_root: str = '/proc',
    max_depth: int = 12,
) -> tuple[int, int] | None:
    """From a hook process, climb to the agent CLI: (pid, start_time)."""
    current = pid
    for _ in range(max_depth):
        info = read_proc(proc_root, current)
        if info is None:
            return None
        ppid, _, start_time, argv = info
        if agent_kind(argv):
            return current, start_time
        if ppid <= 1:
            return None
        current = ppid
    return None


def environ_value(proc_root: str, pid: int, key: str) -> str:
    try:
        with open(f'{proc_root}/{pid}/environ', 'rb') as environ_file:  # noqa: PTH123
            raw = environ_file.read()
    except OSError:
        return ''
    prefix = key.encode() + b'='
    for entry in raw.split(b'\0'):
        if entry.startswith(prefix):
            return entry[len(prefix) :].decode(errors='replace')
    return ''
