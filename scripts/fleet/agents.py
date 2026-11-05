"""Agent kinds: how to launch each CLI and how its hooks map to state."""

import json
import shlex
from collections.abc import Mapping, Sequence
from enum import StrEnum

from fleet.events import (
    CLAUDE_EVENT_STATES,
    is_valid_agent_name,
    state_name_for_event,
)


class AgentState(StrEnum):
    WORKING = 'working'
    WAITING = 'waiting'
    IDLE = 'idle'
    ERROR = 'error'
    EXITED = 'exited'
    GONE = 'gone'
    UNKNOWN = 'unknown'


AGENT_KINDS = ('claude', 'copilot')


def state_for_event(
    kind: str,
    event: str,
    payload: Mapping[str, object],
) -> AgentState | None:
    notification_type = str(payload.get('notification_type') or '')
    state = state_name_for_event(kind, event, notification_type)
    return AgentState(state) if state else None


def validate_agent_name(name: str) -> str:
    if not is_valid_agent_name(name):
        msg = (
            f'invalid agent name {name!r}: use letters, digits, - and _ '
            '(max 60, must start with a letter or digit)'
        )
        raise ValueError(msg)
    return name


type HookSettings = dict[str, dict[str, list[dict[str, list[dict[str, str]]]]]]


def claude_hook_settings(hook_path: str) -> HookSettings:
    quoted_hook = shlex.quote(hook_path)
    return {
        'hooks': {
            event: [
                {
                    'hooks': [
                        {
                            'type': 'command',
                            'command': f'{quoted_hook} claude {event}',
                        },
                    ],
                },
            ]
            for event in CLAUDE_EVENT_STATES
        },
    }


def launch_command(
    kind: str,
    *,
    name: str,
    prompt: str,
    hook_path: str,
    extra_args: Sequence[str],
    binary: str,
    with_hooks: bool = True,
) -> list[str]:
    if kind == 'claude':
        # Without global hooks, pass them per launch so fleet agents still
        # report state. Copilot has no such flag; its hooks are user files.
        settings_args = (
            ['--settings', json.dumps(claude_hook_settings(hook_path))]
            if with_hooks
            else []
        )
        cmd = [binary, *settings_args, '-n', name, *extra_args]
        return [*cmd, '--', prompt] if prompt else cmd
    if kind == 'copilot':
        cmd = [binary, '-n', name, *extra_args]
        return [*cmd, '-i', prompt] if prompt else cmd
    msg = f'unknown agent kind {kind!r}: expected one of {AGENT_KINDS}'
    raise ValueError(msg)
