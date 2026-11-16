import os

from talon import Context, Module, actions, ui

# Purview DLP on the work PC likely blocks Rango's clipboard requests
# ("Clipboard is empty"), so there Rango's voice commands are off. Hints are
# clicked by typing their letters (Rango keyboard clicking +
# rango_keyboard.talon).
ctx = Context()
ctx.matches = 'tag: browser'
if os.environ.get('USERDOMAIN', '').upper() == 'WHELEN':
    ctx.tags = ['user.rango_disabled']


mod = Module()

MAX_TABS = 50


@mod.action_class
class Actions:
    def chrome_go_tab_marker(marker: str) -> None:  # noqa: N805 - Talon actions take no self
        """Cycle Chrome tabs until the title starts with Rango's tab marker."""
        prefix = f'{marker.upper()} | '
        start = ui.active_window().title
        for _ in range(MAX_TABS):
            if ui.active_window().title.upper().startswith(prefix):
                return
            actions.key('ctrl-tab')
            actions.sleep('60ms')
            if ui.active_window().title == start:
                break
        actions.app.notify(f'No tab marked {marker.upper()}')
