from talon import Module

mod = Module()
mod.list('slash_builtin', desc='Built-in Claude Code and Copilot commands')
mod.list('slash_skill', desc='Installed skills, written by just talon')
mod.list('cli_command', desc='Shell commands to type in tmux')


@mod.capture(rule='{user.slash_builtin} | {user.slash_skill}')
def slash_command(m) -> str:  # noqa: ANN001 - Talon capture match type
    """A slash command name, without the slash."""
    return str(m)
