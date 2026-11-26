"""On-disk agent records and live state.

The fleet CLI writes `<name>.json` once at launch. Hooks write
`<name>.state.json` on every event. The agent itself writes
`<name>.steps.json` through `fleet step`. One file per writer, so no two
writers race on the same file.
"""

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from fleet.agents import AgentState

STATE_SUFFIX = '.state.json'
STEPS_SUFFIX = '.steps.json'
MAX_STEP_NOTE = 80


def default_state_dir(env: Mapping[str, str] = os.environ) -> Path:
    if env.get('FLEET_STATE_DIR'):
        return Path(env['FLEET_STATE_DIR'])
    if env.get('XDG_STATE_HOME'):
        return Path(env['XDG_STATE_HOME']) / 'fleet'
    return Path(env.get('HOME', '~')).expanduser() / '.local/state/fleet'


@dataclass
class AgentRecord:
    name: str
    kind: str
    repo: str
    worktree: str
    branch: str
    base: str
    prompt: str
    created_at: float
    window_id: str
    launch_id: str = ''
    autopilot: bool = False


@dataclass(frozen=True)
class LiveState:
    state: AgentState
    event: str
    message: str
    updated_at: float
    launch_id: str = ''


@dataclass(frozen=True)
class Steps:
    """Progress an agent reports on its own task."""

    done: int
    total: int
    note: str


def make_steps(done: int, total: int, note: str) -> Steps | None:
    if total < 1:
        return None
    return Steps(
        done=min(total, max(0, done)),
        total=total,
        note=note.strip()[:MAX_STEP_NOTE],
    )


def parse_steps(data: dict[str, object]) -> Steps | None:
    done, total = data.get('done'), data.get('total')
    if type(done) is not int or type(total) is not int:
        return None
    return make_steps(done, total, str(data.get('note') or ''))


def write_json_atomically(
    path: Path,
    data: object,
    indent: int | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix='.tmp-')
    with os.fdopen(fd, 'w') as tmp_file:
        json.dump(data, tmp_file, indent=indent)
        if indent is not None:
            tmp_file.write('\n')
    Path(tmp_name).replace(path)


def read_json(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def parse_live_state(data: dict[str, object]) -> LiveState | None:
    try:
        return LiveState(
            state=AgentState(str(data['state'])),
            event=str(data.get('event', '')),
            message=str(data.get('message', '')),
            updated_at=float(data.get('updated_at', 0)),  # type: ignore[arg-type]
            launch_id=str(data.get('launch_id', '')),
        )
    except (KeyError, ValueError):
        return None


class Store:
    def __init__(self, root: Path) -> None:
        self.agents_dir = root / 'agents'
        self.sessions_dir = root / 'sessions'

    def record_path(self, name: str) -> Path:
        return self.agents_dir / f'{name}.json'

    def state_path(self, name: str) -> Path:
        return self.agents_dir / f'{name}{STATE_SUFFIX}'

    def save(self, record: AgentRecord) -> None:
        write_json_atomically(self.record_path(record.name), asdict(record))

    def load(self, name: str) -> AgentRecord:
        data = read_json(self.record_path(name))
        if data is None:
            raise KeyError(name)
        return AgentRecord(**data)  # type: ignore[arg-type]

    def list_records(self) -> list[AgentRecord]:
        if not self.agents_dir.is_dir():
            return []
        records = []
        for path in self.agents_dir.glob('*.json'):
            if path.name.endswith((STATE_SUFFIX, STEPS_SUFFIX)):
                continue
            data = read_json(path)
            if data is None:
                continue
            try:
                records.append(AgentRecord(**data))  # type: ignore[arg-type]
            except TypeError:
                continue
        return sorted(records, key=lambda record: record.created_at)

    def delete(self, name: str) -> None:
        self.record_path(name).unlink(missing_ok=True)
        self.state_path(name).unlink(missing_ok=True)
        self.steps_path(name).unlink(missing_ok=True)

    def steps_path(self, name: str) -> Path:
        return self.agents_dir / f'{name}{STEPS_SUFFIX}'

    def write_steps(self, name: str, steps: Steps, launch_id: str) -> None:
        write_json_atomically(
            self.steps_path(name),
            {**asdict(steps), 'launch_id': launch_id},
        )

    def read_steps(self, name: str, launch_id: str = '') -> Steps | None:
        """With `launch_id`, steps from an earlier launch are ignored."""
        data = read_json(self.steps_path(name))
        if data is None or (launch_id and data.get('launch_id') != launch_id):
            return None
        return parse_steps(data)

    def write_state(  # noqa: PLR0917  mirrors the hook's on-disk fields
        self,
        name: str,
        state: AgentState,
        event: str,
        message: str,
        now: float,
        launch_id: str = '',
    ) -> None:
        write_json_atomically(
            self.state_path(name),
            {
                'state': state.value,
                'event': event,
                'message': message,
                'updated_at': now,
                'launch_id': launch_id,
            },
        )

    def read_state(self, name: str, launch_id: str = '') -> LiveState | None:
        """With `launch_id`, state written by an earlier launch is ignored."""
        data = read_json(self.state_path(name))
        live = parse_live_state(data) if data else None
        if live is None or (launch_id and live.launch_id != launch_id):
            return None
        return live

    def session_path(self, pid: int) -> Path:
        return self.sessions_dir / f'{pid}.json'

    def write_session(  # noqa: PLR0917  mirrors the hook's on-disk fields
        self,
        pid: int,
        start_time: int,
        state: AgentState,
        event: str,
        message: str,
        now: float,
    ) -> None:
        """State for any agent session, keyed by the agent's pid."""
        write_json_atomically(
            self.session_path(pid),
            {
                'state': state.value,
                'event': event,
                'message': message,
                'updated_at': now,
                'start_time': start_time,
            },
        )

    def read_session(self, pid: int, start_time: int) -> LiveState | None:
        """A different start time means the pid was reused: stale state."""
        data = read_json(self.session_path(pid))
        if data is None or data.get('start_time') != start_time:
            return None
        return parse_live_state(data)

    def prune_sessions(self, alive: set[tuple[int, int]]) -> None:
        if not self.sessions_dir.is_dir():
            return
        for path in self.sessions_dir.glob('*.json'):
            data = read_json(path) or {}
            key = (
                int(path.stem) if path.stem.isdigit() else -1,
                data.get('start_time'),
            )
            if key not in alive:
                path.unlink(missing_ok=True)
