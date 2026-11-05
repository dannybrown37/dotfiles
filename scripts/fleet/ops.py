"""Fleet operations shared by the CLI and the TUI."""

import dataclasses
import os
import subprocess
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from fleet.agents import (
    AGENT_KINDS,
    AgentState,
    launch_command,
    validate_agent_name,
)
from fleet.hooks_install import (
    claude_hooks_installed,
    copilot_hooks_installed,
)
from fleet.procs import AgentProcess, process_started_at
from fleet.store import AgentRecord, LiveState, Store, default_state_dir
from fleet.tmux import PaneInfo, Tmux
from fleet.trust import answer_trust_dialog, source_is_trusted
from fleet.worktree import (
    create_worktree,
    delete_branch,
    git,
    is_dirty,
    remove_worktree,
    repo_root,
    unpushed_commits,
)

DEFAULT_SESSION = 'fleet'
STARTUP_GRACE_SECONDS = 20
DASHBOARD_WINDOW = 'dash'
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
HOOK_PATH = SCRIPTS_DIR / 'fleet-hook.sh'
LAUNCHER_PATH = SCRIPTS_DIR / 'fleet.sh'


@dataclass(frozen=True)
class SpawnRequest:
    kind: str
    name: str
    repo_dir: Path
    base: str
    prompt: str
    extra_args: Sequence[str]
    binary: str
    hook_path: str
    session: str
    auto_trust: bool = False
    # A pane id to split instead of opening a window in `session`.
    split_from: str = ''


@dataclass(frozen=True)
class AgentView:
    record: AgentRecord
    state: AgentState
    live: LiveState | None
    pane: PaneInfo | None


@dataclass(frozen=True)
class DashboardRow:
    """One agent session, whether fleet started it or found it running."""

    key: str
    kind: str
    name: str
    state: AgentState
    message: str
    cwd: Path
    diff_base: str
    target: str
    started_at: float
    where: str
    record: AgentRecord | None
    shell: str = ''
    shell_target: str = ''


IDLE_SHELLS = frozenset({'bash', 'zsh', 'fish', 'sh', 'dash'})


def sibling_panes(target: str, panes: Sequence[PaneInfo]) -> list[PaneInfo]:
    """Live non-agent panes sharing a window with `target` (`%N` or `@N`)."""
    own = next(
        (p for p in panes if target in (p.pane_id, p.window_id)),
        None,
    )
    if own is None:
        return []
    own_pane = target if target.startswith('%') else own.pane_id
    return [
        pane
        for pane in panes
        if pane.window_id == own.window_id
        and pane.pane_id != own_pane
        and not pane.dead
        and pane.command not in AGENT_KINDS
    ]


def shell_status(siblings: Sequence[PaneInfo]) -> str:
    """e.g. `$ idle` for a bare prompt, `▶ npm` while a script runs."""
    return ', '.join(
        '$ idle' if pane.command in IDLE_SHELLS else f'▶ {pane.command}'
        for pane in siblings
    )


def with_shell(row: DashboardRow, panes: Sequence[PaneInfo]) -> DashboardRow:
    siblings = sibling_panes(row.target, panes) if row.target else []
    if not siblings:
        return row
    return dataclasses.replace(
        row,
        shell=shell_status(siblings),
        shell_target=siblings[0].pane_id,
    )


def fleet_session() -> str:
    return os.environ.get('FLEET_SESSION', DEFAULT_SESSION)


def agent_binary(kind: str) -> str:
    return os.environ.get(f'FLEET_{kind.upper()}_BIN', kind)


def default_agent_kind() -> str:
    kind = os.environ.get('FLEET_DEFAULT_AGENT', 'claude')
    return kind if kind in AGENT_KINDS else 'claude'


def review_agent_kind(requested: str | None) -> str:
    kind = requested or os.environ.get('FLEET_REVIEW_AGENT', 'copilot')
    return kind if kind in AGENT_KINDS else 'copilot'


def resolve_state(
    live: LiveState | None,
    pane: PaneInfo | None,
    age_seconds: float,
) -> AgentState:
    if pane is None:
        return AgentState.GONE
    if pane.dead:
        return AgentState.EXITED
    if live:
        return live.state
    # Trust and login dialogs come before any hook fires.
    if age_seconds > STARTUP_GRACE_SECONDS:
        return AgentState.WAITING
    return AgentState.UNKNOWN


def current_ref(path: Path) -> str:
    """Branch name when on one, so diffs stay relative to e.g. `main`."""
    ref = git(path, 'rev-parse', '--abbrev-ref', 'HEAD').strip()
    return git(path, 'rev-parse', 'HEAD').strip() if ref == 'HEAD' else ref


def spawn_agent(
    store: Store,
    tmux: Tmux,
    request: SpawnRequest,
) -> AgentRecord:
    name = validate_agent_name(request.name)
    if store.record_path(name).exists():
        msg = (
            f'agent {name!r} already exists; remove it with `fleet rm {name}`'
        )
        raise ValueError(msg)
    root = repo_root(request.repo_dir)
    base = request.base or current_ref(request.repo_dir)
    worktree = create_worktree(root, name, base)
    command = launch_command(
        request.kind,
        name=name,
        prompt=request.prompt,
        hook_path=request.hook_path,
        extra_args=request.extra_args,
        binary=request.binary,
        with_hooks=not claude_hooks_installed(),
    )
    launch_id = uuid.uuid4().hex
    env = {
        'FLEET_AGENT': name,
        'FLEET_LAUNCH_ID': launch_id,
        'FLEET_HOOK': request.hook_path,
        'FLEET_STATE_DIR': str(store.agents_dir.parent),
    }
    if request.split_from:
        window_id = tmux.split_pane(request.split_from, worktree, env, command)
    else:
        window_id = tmux.new_window(
            request.session,
            name,
            worktree,
            env,
            command,
        )
    record = AgentRecord(
        name=name,
        kind=request.kind,
        repo=str(root),
        worktree=str(worktree),
        branch=name,
        base=base,
        prompt=request.prompt,
        created_at=time.time(),
        window_id=window_id,
        launch_id=launch_id,
    )
    store.save(record)
    if request.auto_trust and source_is_trusted(root):
        answer_trust_dialog(tmux, store, record, str(worktree))
    return record


def agent_views(store: Store, tmux: Tmux) -> list[AgentView]:
    # Records hold a window id, or a pane id for agents split into a pane.
    panes: dict[str, PaneInfo] = {
        pane.pane_id: pane for pane in tmux.all_panes()
    }
    panes.update(tmux.panes())
    now = time.time()
    views = []
    for record in store.list_records():
        live = store.read_state(record.name, record.launch_id)
        pane = panes.get(record.window_id)
        state = resolve_state(live, pane, now - record.created_at)
        views.append(AgentView(record, state, live, pane))
    return views


def agent_row(view: AgentView) -> DashboardRow:
    record = view.record
    return DashboardRow(
        key=f'agent:{record.name}',
        kind=record.kind,
        name=record.name,
        state=view.state,
        message=(view.live.message if view.live else '') or record.prompt,
        cwd=Path(record.worktree),
        diff_base=record.base,
        target=record.window_id if view.pane else '',
        started_at=record.created_at,
        where='fleet',
        record=record,
    )


def session_row(
    process: AgentProcess,
    live: LiveState | None,
    pane: PaneInfo | None,
    *,
    hooks_on: bool = False,
) -> DashboardRow:
    # Copilot fires its first hook (sessionStart) only once the first prompt
    # is sent, so with hooks on, no state means it sits at a fresh prompt.
    state, message = (
        (live.state, live.message)
        if live
        else (AgentState.IDLE, 'new session, no prompt yet')
        if hooks_on
        else (AgentState.UNKNOWN, '')
    )
    if process.background:
        where = 'background'
    elif pane:
        where = f'tmux {pane.session}:{pane.window_name}'
    else:
        where = 'terminal'
    return DashboardRow(
        key=f'pid:{process.pid}',
        kind=process.kind,
        name=Path(process.cwd).name,
        state=state,
        message=message,
        cwd=Path(process.cwd),
        diff_base='HEAD',
        target=pane.pane_id if pane else '',
        started_at=process_started_at(process.start_time),
        where=where,
        record=None,
    )


def dashboard_rows(
    store: Store,
    tmux: Tmux,
    processes: Sequence[AgentProcess],
    hooks_on: Mapping[str, bool] | None = None,
) -> list[DashboardRow]:
    if hooks_on is None:
        hooks_on = {
            'claude': claude_hooks_installed(),
            'copilot': copilot_hooks_installed(),
        }
    rows = [agent_row(view) for view in agent_views(store, tmux)]
    all_panes = tmux.all_panes()
    panes_by_id = {pane.pane_id: pane for pane in all_panes}
    for process in processes:
        if process.fleet_agent:
            continue
        same_server = process.tmux_socket == tmux.socket_name
        pane = panes_by_id.get(process.tmux_pane) if same_server else None
        live = store.read_session(process.pid, process.start_time)
        rows.append(
            session_row(
                process,
                live,
                pane,
                hooks_on=hooks_on.get(process.kind, False),
            ),
        )
    store.prune_sessions({(p.pid, p.start_time) for p in processes})
    return [with_shell(row, all_panes) for row in rows]


def kill_agent(
    store: Store,
    tmux: Tmux,
    record: AgentRecord,
    *,
    remove_checkout: bool,
    force: bool,
    remove_branch: bool = False,
) -> None:
    worktree = Path(record.worktree)
    repo = Path(record.repo)
    remove_checkout = remove_checkout or remove_branch
    if (
        remove_checkout
        and worktree.is_dir()
        and not force
        and is_dirty(worktree)
    ):
        msg = (
            f'{worktree} has uncommitted changes; commit them or pass '
            '--force to discard them'
        )
        raise ValueError(msg)
    if remove_branch and not force and unpushed_commits(repo, record.branch):
        msg = (
            f'branch {record.branch} has unpushed commits; push them or '
            'pass --force to discard them'
        )
        raise ValueError(msg)
    tmux.kill_window(record.window_id)
    if remove_checkout and worktree.is_dir():
        remove_worktree(repo, worktree, force=force)
    if remove_branch:
        delete_branch(repo, record.branch)
    store.delete(record.name)


def ensure_dashboard(
    tmux: Tmux,
    session: str,
    command: Sequence[str],
    cwd: Path,
) -> str:
    """The `dash` window lives in the agents' session, so jumps are cheap."""
    for pane in tmux.panes().values():
        if pane.session == session and pane.window_name == DASHBOARD_WINDOW:
            if pane.dead:
                tmux.respawn(pane.window_id, cwd, {}, command)
            return pane.window_id
    return tmux.new_window(session, DASHBOARD_WINDOW, cwd, {}, command)


def default_store() -> Store:
    return Store(default_state_dir())


def default_tmux() -> Tmux:
    return Tmux(os.environ.get('FLEET_TMUX_SOCKET') or None)


def run_interactive(command: Sequence[str], cwd: Path | None = None) -> int:
    return subprocess.run(command, cwd=cwd, check=False).returncode  # noqa: S603
