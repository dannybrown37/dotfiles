import subprocess

from talon import Module

mod = Module()


@mod.action_class
class Actions:
    def chief_send(text: str) -> None:  # noqa: N805 - Talon actions take no self
        """Type a message into the tutti chief window (runs tutti in WSL)."""
        command = 'tutti send chief "$1"'
        subprocess.Popen(  # noqa: S603
            ['wsl.exe', '--', 'bash', '-lc', command, '_', text],  # noqa: S607
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
