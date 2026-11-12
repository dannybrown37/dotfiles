# Talon rejects overrides whose signature differs from community's prototype,
# and its action classes take no self.
# ruff: noqa: ANN201, N805
import time

from talon import Context, actions, ui

# Windows can leave a stale process behind under the same app name (e.g. a dead
# "Windows Terminal Host" whose only window is a drag bar), and Talon may pick
# it. Its windows reject focus with "Invalid window handle". So try the visible
# windows of every app with this name, real top-level windows first.
ctx = Context()
ctx.matches = 'os: windows'

TOP_LEVEL_CLASSES = ('CASCADIA_HOSTING_WINDOW_CLASS',)


class AppFocusError(RuntimeError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Can't focus app: {name}")


def candidate_windows(app: ui.App) -> list[ui.Window]:
    windows = [
        w
        for w in ui.windows()
        if not w.hidden and (w.app.pid == app.pid or w.app.name == app.name)
    ]
    windows.sort(key=lambda w: (w.cls not in TOP_LEVEL_CLASSES, not w.title))
    return windows


@ctx.action_class('user')
class UserActions:
    def switcher_focus_app(app: ui.App):
        for window in candidate_windows(app):
            try:
                window.focus()
            except OSError:
                continue
            t1 = time.perf_counter()
            while time.perf_counter() - t1 < 1:
                if (
                    ui.active_window() == window
                    or ui.active_app() == window.app
                ):
                    return
                actions.sleep(0.1)
        raise AppFocusError(app.name)
