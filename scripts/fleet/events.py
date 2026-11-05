"""Hook event -> agent state tables, and agent-name rules.

Imports nothing: the hook loads this on every event of every agent session,
so its cost lands on every tool call.
"""

WORKING = 'working'
WAITING = 'waiting'
IDLE = 'idle'
ERROR = 'error'
EXITED = 'exited'

CLAUDE_EVENT_STATES = {
    'SessionStart': IDLE,
    'UserPromptSubmit': WORKING,
    'PostToolUse': WORKING,
    'Notification': WAITING,
    'Stop': IDLE,
    'SessionEnd': EXITED,
}

COPILOT_EVENT_STATES = {
    'sessionStart': IDLE,
    'userPromptSubmitted': WORKING,
    'postToolUse': WORKING,
    'permissionRequest': WAITING,
    'notification': WAITING,
    'agentStop': IDLE,
    'errorOccurred': ERROR,
    'sessionEnd': EXITED,
}

EVENT_STATES = {'claude': CLAUDE_EVENT_STATES, 'copilot': COPILOT_EVENT_STATES}

# Both CLIs send this when the agent has sat at its prompt for a while
# after finishing. That is "your turn", not "blocked on a permission".
IDLE_NOTIFICATION_TYPE = 'idle_prompt'

MAX_AGENT_NAME = 60


def is_valid_agent_name(name: str) -> bool:
    """Names become tmux window names, branch names and file names."""
    return (
        0 < len(name) <= MAX_AGENT_NAME
        and name[0].isascii()
        and name[0].isalnum()
        and all(c.isascii() and (c.isalnum() or c in '-_') for c in name)
    )


def state_name_for_event(
    kind: str,
    event: str,
    notification_type: str,
) -> str | None:
    state = EVENT_STATES.get(kind, {}).get(event)
    if state == WAITING and notification_type == IDLE_NOTIFICATION_TYPE:
        return IDLE
    return state
