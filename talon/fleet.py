import json
import subprocess
import threading

from talon import Module, actions, app, imgui, settings, ui

from .fleet_commands import COMMANDS, TIERS

mod = Module()
mod.setting(
    'fleet_coach',
    type=bool,
    default=True,
    desc='Auto-show the fleet voice cheat sheet while the dashboard has focus',
)

DASHBOARD_TITLE = 'tmux fleet:dash'
FLEET_LS = (
    '"${DOTFILES_DIR:-$HOME/projects/dotfiles}/scripts/fleet.sh" ls --json'
)
NEEDS_YOU = ('waiting', 'idle')
coach_override: list[bool] = []


@imgui.open()
def cheat_sheet(gui: imgui.GUI) -> None:
    gui.text('Fleet by voice')
    gui.line()
    for tier in TIERS:
        gui.text(tier)
        for _, spoken, effect in (c for c in COMMANDS if c[0] == tier):
            gui.text(f'   {spoken}  ->  {effect}')
        gui.spacer()
    gui.text('"fleet help" hides this. "fleet coach off" stops auto-show.')


def coach_on() -> bool:
    return (
        coach_override[-1]
        if coach_override
        else settings.get('user.fleet_coach')
    )


def on_window_change(_window: object) -> None:
    if not coach_on():
        return
    on_dashboard = ui.active_window().title.startswith(DASHBOARD_TITLE)
    if on_dashboard and not cheat_sheet.showing:
        cheat_sheet.show()
    elif not on_dashboard and cheat_sheet.showing:
        cheat_sheet.hide()


def report_status() -> None:
    try:
        result = subprocess.run(  # noqa: S603
            ['wsl.exe', '--', 'bash', '-lc', FLEET_LS],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        rows = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        app.notify(title='Fleet', body=f'status failed: {error}')
        return
    waiting = [r['name'] for r in rows if r.get('state') in NEEDS_YOU]
    if not waiting:
        app.notify(
            title='Fleet',
            body=f'Nobody needs you. {len(rows)} agents running.',
        )
        return
    app.notify(
        title='Fleet',
        body=f'{len(waiting)} need you: {", ".join(waiting)}',
    )


@mod.action_class
class Actions:
    def fleet_help_toggle() -> None:
        """Show or hide the fleet voice cheat sheet."""
        if cheat_sheet.showing:
            cheat_sheet.hide()
        else:
            cheat_sheet.show()

    def fleet_coach(on: int) -> None:  # noqa: N805
        """Auto-show the cheat sheet: 1 on, 0 off, until Talon restarts."""
        coach_override[:] = [bool(on)]
        if not on:
            cheat_sheet.hide()
        app.notify(title='Fleet', body=f'voice coach {"on" if on else "off"}')

    def fleet_status() -> None:
        """Pop up which agents need you (runs fleet ls in WSL)."""
        threading.Thread(target=report_status, daemon=True).start()

    def fleet_send(text: str) -> None:  # noqa: N805
        """Type a message into the selected agent from the dashboard."""
        actions.key('s')
        actions.sleep('300ms')
        actions.insert(text)
        actions.key('ctrl-s')


ui.register('win_focus', on_window_change)
ui.register('win_title', on_window_change)
