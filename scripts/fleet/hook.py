"""Hook entry for every agent session: records state for the agent that ran it.

Every session gets a pid-keyed record, which is how the dashboard sees
agents fleet did not start. Fleet's own agents also get a name-keyed one.

This runs on every tool call of every session, so it imports only os and
sys (json only for events that carry a message) and writes its tiny JSON by
hand. The file layout is read back by fleet.store.
"""

import os
import sys
import time

from fleet.events import WAITING, is_valid_agent_name, state_name_for_event
from fleet.proclite import find_agent_ancestor

MAX_MESSAGE_CHARS = 300


def json_string(value: str) -> str:
    escaped = ''.join(
        c if c >= ' ' and c not in '"\\' else f'\\u{ord(c):04x}' for c in value
    )
    return f'"{escaped}"'


def state_dir() -> str:
    if os.environ.get('FLEET_STATE_DIR'):
        return os.environ['FLEET_STATE_DIR']
    if os.environ.get('XDG_STATE_HOME'):
        return f'{os.environ["XDG_STATE_HOME"]}/fleet'
    return f'{os.path.expanduser("~")}/.local/state/fleet'  # noqa: PTH111


def write_atomically(directory: str, filename: str, content: str) -> None:
    os.makedirs(directory, exist_ok=True)  # noqa: PTH103
    tmp_path = f'{directory}/.tmp-{os.getpid()}-{filename}'
    with open(tmp_path, 'w', encoding='utf-8') as tmp_file:  # noqa: PTH123
        tmp_file.write(content)
    os.replace(tmp_path, f'{directory}/{filename}')  # noqa: PTH105


def read_notification(raw_payload: str) -> tuple[str, str]:
    """(message, notification_type), parsed only when the event has them."""
    import json

    try:
        payload = json.loads(raw_payload)
    except ValueError:
        return '', ''
    if not isinstance(payload, dict):
        return '', ''
    message = str(payload.get('message') or '')[:MAX_MESSAGE_CHARS]
    return message, str(payload.get('notification_type') or '')


def handle(kind: str, event: str, raw_payload: str) -> None:
    state = state_name_for_event(kind, event, '')
    if state is None:
        return
    message = ''
    if state == WAITING:
        message, notification_type = read_notification(raw_payload)
        state = state_name_for_event(kind, event, notification_type) or state
    root = state_dir()
    fields = (
        f'"state": {json_string(state)}, "event": {json_string(event)}, '
        f'"message": {json_string(message)}, "updated_at": {time.time()}'
    )
    agent = find_agent_ancestor(os.getppid())
    if agent is not None:
        pid, start_time = agent
        write_atomically(
            f'{root}/sessions',
            f'{pid}.json',
            f'{{{fields}, "start_time": {start_time}}}',
        )
    name = os.environ.get('FLEET_AGENT', '')
    if name:
        if not is_valid_agent_name(name):
            msg = f'invalid agent name {name!r}'
            raise ValueError(msg)
        launch_id = json_string(os.environ.get('FLEET_LAUNCH_ID', ''))
        write_atomically(
            f'{root}/agents',
            f'{name}.state.json',
            f'{{{fields}, "launch_id": {launch_id}}}',
        )


def main() -> None:
    if len(sys.argv) != 3:  # noqa: PLR2004
        return
    handle(sys.argv[1], sys.argv[2], sys.stdin.read())


if __name__ == '__main__':
    main()
