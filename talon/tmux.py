# Talon rejects overrides whose signature differs from community's prototype,
# and its action classes take no self.
# ruff: noqa: ANN201, N805
from talon import Context, actions

# Windows Terminal turns on community's Windows shell actions, but tmux runs
# bash in WSL. This context is more specific, so its bash versions win.
ctx = Context()
ctx.matches = r"""
app: windows_terminal
title: /^tmux/
"""


@ctx.action_class('user')
class UserActions:
    def terminal_list_directories(path: str | None = None):
        actions.insert(f'ls {path or ""}')
        actions.key('enter')

    def terminal_list_all_directories():
        actions.insert('ls -a')
        actions.key('enter')

    def terminal_change_directory(path: str):
        actions.insert(f'cd {path}')
        if path:
            actions.key('enter')

    def terminal_change_directory_root():
        actions.insert('cd /')
        actions.key('enter')

    def terminal_clear_screen():
        actions.insert('clear')
        actions.key('enter')

    def terminal_run_last():
        actions.key('up enter')

    def terminal_rerun_search(command: str):
        actions.key('ctrl-r')
        actions.insert(command)

    def terminal_kill_all():
        actions.key('ctrl-c')

    def terminal_escape_string(string: str) -> str:
        return string.replace(' ', r'\ ')

    # readline's cut_line ends in ctrl-k, which tmux takes for pane-up
    def cut_line():
        actions.key('ctrl-e ctrl-u')
