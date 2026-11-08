app: windows_terminal
title: /^tmux/
-
tag(): user.tmux
tag(): user.unix_utilities
# Windows' clear line selects with shift-end, which bash and Claude Code ignore.
# tmux.py swaps readline's ctrl-k (tmux pane-up) for ctrl-u.
tag(): user.readline

run {user.cli_command}: insert(cli_command)

# Direct tmux keys: community's split_* actions lose to Windows Terminal's
# own pane actions, which only pop up "not possible"
pane left: key(ctrl-left)
pane right: key(ctrl-right)
pane up: key(ctrl-up)
pane down: key(ctrl-down)
pane next: user.tmux_keybind("o")
pane zoom: user.tmux_keybind("m")
pane split right: user.tmux_keybind("|")
pane split down: user.tmux_keybind("-")
pane close: user.tmux_execute_command_with_confirmation("kill-pane", "kill-pane #P?")

mux left: user.tmux_keybind("p")
mux right: user.tmux_keybind("n")
# community's "mux close window" sends &, which .tmux.conf unbinds
mux kill window: user.tmux_execute_command_with_confirmation("kill-window", "kill-window #W?")
