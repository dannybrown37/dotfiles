"""Thin wrapper over the tmux CLI. Windows are addressed by id (`@12`)."""

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER = ('sleep', 'infinity')
PANE_FORMAT = '\t'.join(
    (
        '#{window_id}',
        '#{window_name}',
        '#{pane_id}',
        '#{pane_dead}',
        '#{session_name}',
    ),
)


@dataclass(frozen=True)
class PaneInfo:
    window_id: str
    window_name: str
    pane_id: str
    dead: bool
    session: str


class Tmux:
    def __init__(self, socket: str | None = None) -> None:
        self.base = ['tmux', *(['-L', socket] if socket else [])]
        self.socket_name = socket or 'default'

    def run(
        self,
        *args: str,
        stdin: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [*self.base, *args],
            input=stdin,
            capture_output=True,
            text=True,
            check=check,
        )

    def has_session(self, session: str) -> bool:
        return (
            self.run(
                'has-session',
                '-t',
                f'={session}',
                check=False,
            ).returncode
            == 0
        )

    def new_window(
        self,
        session: str,
        name: str,
        cwd: Path,
        env: Mapping[str, str],
        command: Sequence[str],
    ) -> str:
        """Start `command` directly (no shell) in a detached window.

        remain-on-exit keeps the window after the agent quits, so its last
        output stays readable and the dead pane tells us it exited. It has
        to be set before the real command starts: an agent that dies at
        once would otherwise take its window, and its error, with it.
        """
        common = ['-d', '-n', name, '-c', str(cwd), '-P', '-F', '#{window_id}']
        if self.has_session(session):
            created = self.run(
                'new-window',
                '-t',
                f'={session}:',
                *common,
                *PLACEHOLDER,
            )
        else:
            created = self.run(
                'new-session',
                '-s',
                session,
                *common,
                *PLACEHOLDER,
            )
        window_id = created.stdout.strip()
        self.run('set-option', '-w', '-t', window_id, 'remain-on-exit', 'on')
        self.respawn(window_id, cwd, env, command)
        return window_id

    def respawn(
        self,
        window_id: str,
        cwd: Path,
        env: Mapping[str, str],
        command: Sequence[str],
    ) -> None:
        env_args = [
            arg
            for key, value in env.items()
            for arg in ('-e', f'{key}={value}')
        ]
        self.run(
            'respawn-pane',
            '-k',
            '-t',
            window_id,
            '-c',
            str(cwd),
            *env_args,
            *command,
        )

    def all_panes(self) -> list[PaneInfo]:
        result = self.run('list-panes', '-a', '-F', PANE_FORMAT, check=False)
        if result.returncode != 0:
            return []
        panes = []
        for line in result.stdout.splitlines():
            window_id, window_name, pane_id, dead, session = line.split('\t')
            is_dead = dead == '1'
            panes.append(
                PaneInfo(window_id, window_name, pane_id, is_dead, session),
            )
        return panes

    def panes(self) -> dict[str, PaneInfo]:
        """First pane of every window on the server, keyed by window id."""
        panes: dict[str, PaneInfo] = {}
        for pane in self.all_panes():
            panes.setdefault(pane.window_id, pane)
        return panes

    def capture(
        self,
        window_id: str,
        lines: int = 200,
        *,
        color: bool = True,
    ) -> str:
        """Colour is for showing the pane; reading its text needs it off."""
        result = self.run(
            'capture-pane',
            '-p',
            *(['-e'] if color else []),
            '-J',
            '-t',
            window_id,
            '-S',
            f'-{lines}',
            check=False,
        )
        return result.stdout if result.returncode == 0 else ''

    def send_text(self, window_id: str, text: str) -> None:
        """Paste as one bracketed paste, then press Enter.

        `send-keys -l` with a multi-line message would submit at the first
        newline; bracketed paste makes the agent TUI take it as one prompt.
        """
        buffer_name = f'fleet-{os.getpid()}'
        self.run('load-buffer', '-b', buffer_name, '-', stdin=text)
        self.run(
            'paste-buffer',
            '-p',
            '-d',
            '-b',
            buffer_name,
            '-t',
            window_id,
        )
        self.run('send-keys', '-t', window_id, 'Enter')

    def kill_window(self, window_id: str) -> None:
        self.run('kill-window', '-t', window_id, check=False)

    def jump_command(self, target: str) -> list[str]:
        """Inside tmux, switch the client; outside, attach.

        `target` is a window id (`@3`) or pane id (`%25`); both select the
        right pane.
        """
        if os.environ.get('TMUX') and len(self.base) == 1:
            return [*self.base, 'switch-client', '-t', target]
        return [
            *self.base,
            'select-window',
            '-t',
            target,
            ';',
            'select-pane',
            '-t',
            target,
            ';',
            'attach-session',
            '-t',
            target,
        ]
