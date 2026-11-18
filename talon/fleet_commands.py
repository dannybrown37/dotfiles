"""Every fleet voice command, by learning tier.

One list feeds the coach overlay (fleet.py) and is checked against
fleet*.talon and talon.md by scripts/test_talon_fleet.py, so the three
never drift. Plain data: no talon import.
"""

START = '1 · Start here: learn these first'
DAILY = '2 · Daily driving'
POWER = '3 · Power moves'
TIERS = (START, DAILY, POWER)

COMMANDS = (
    (START, 'fleet open', 'show / hide the fleet dashboard (Alt+W)'),
    (START, 'fleet help', 'show / hide this cheat sheet'),
    (START, 'agent next', 'move down one agent'),
    (START, 'agent last', 'move up one agent'),
    (START, 'agent jump', "go into the selected agent's pane"),
    (START, 'fleet back', 'from any tmux window, back to the dashboard'),
    (DAILY, 'agent top', 'first row: the agent that needs you most'),
    (DAILY, 'agent go', 'tell the selected agent "go" (autopilot gate 1)'),
    (DAILY, 'agent send <words>', 'type a message into the selected agent'),
    (DAILY, 'agent diff', "show the selected agent's diff"),
    (DAILY, 'agent draft', 'commit, push, open a draft PR (autopilot gate 2)'),
    (DAILY, 'agent browser', "open the selected agent's or review's PR"),
    (DAILY, 'fleet status', 'pop-up: who needs you, without looking'),
    (POWER, 'agent new', 'new agent form'),
    (POWER, 'agent stop', 'stop the agent, keep worktree and branch'),
    (POWER, 'agent lazy git', "lazygit in the agent's worktree"),
    (POWER, 'show agents', 'Agents tab'),
    (POWER, 'show reviews', 'Reviews tab'),
    (POWER, 'show mine', 'My PRs tab'),
    (POWER, 'review this', 'pre-review the selected PR'),
    (POWER, 'review deep', 'agent review in a worktree'),
    (POWER, 'fleet palette', 'Ctrl+P: search every action'),
    (POWER, 'fleet coach on', 'auto-show this sheet on the dashboard'),
    (POWER, 'fleet coach off', 'stop auto-showing; "fleet help" still works'),
)
