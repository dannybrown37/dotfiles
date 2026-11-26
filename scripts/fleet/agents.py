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


def step_brief(launcher: str) -> str:
    """One brief line asking the agent to report steps.

    Mirrors savvy-progress's worker brief: agents skip a tool that is merely
    available, but follow the same request written into the brief. Names the
    launcher by path: `fleet` is a shell alias, which an agent's own shell
    may not have.
    """
    step = f'{shlex.quote(launcher)} step'
    return (
        f'Progress reporting: right after reading this, run `{step} 0 '
        '<total> "<first step>"` with your plan in 3-8 steps, then '
        f'`{step} <done> <total> "<next step>"` as each step finishes. '
        'It only draws a progress bar in the fleet panel.'
    )


def with_step_brief(prompt: str, launcher: str) -> str:
    """An empty prompt stays empty: a brief would start the agent working."""
    brief = step_brief(launcher)
    if not prompt or prompt.endswith(brief):
        return prompt
    return f'{prompt}\n\n{brief}'


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


HOOK_TIMEOUT_S = 5

type HookEntry = dict[str, list[dict[str, str | int]]]
type HookSettings = dict[str, dict[str, list[HookEntry]]]


def claude_hook_entry(hook_path: str, event: str) -> HookEntry:
    """One settings.json hook entry that runs fleet-hook.sh for `event`.

    The -x guard keeps a moved or deleted dotfiles checkout from turning
    every Claude event into a "No such file" hook error.
    """
    hook = shlex.quote(hook_path)
    command = f'[ -x {hook} ] && exec {hook} claude {event} || true'
    return {
        'hooks': [
            {'type': 'command', 'command': command, 'timeout': HOOK_TIMEOUT_S},
        ],
    }


def claude_hook_settings(hook_path: str) -> HookSettings:
    return {
        'hooks': {
            event: [claude_hook_entry(hook_path, event)]
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
