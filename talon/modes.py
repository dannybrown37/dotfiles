from talon import Context, Module, actions, scope

mod = Module()
ctx = Context()
ctx.matches = r"""
mode: command
mode: dictation
"""


@ctx.action_class('user')
class UserActions:
    def noise_trigger_pop():  # noqa: ANN201 - must match community prototype
        # Zoom mouse and drag/scroll stop own pop first, as in community.
        if actions.tracking.control_zoom_enabled():
            return
        if actions.user.mouse_drag_end() or actions.user.mouse_scroll_stop():
            return
        if 'dictation' in scope.get('mode'):
            actions.user.command_mode()
        else:
            actions.user.dictation_mode()


@mod.action_class
class Actions:
    def start_typing(text: str) -> None:  # noqa: N805 - Talon actions take no self
        """Switch to dictation, then type any words said after the command."""
        actions.user.dictation_mode()
        if text:
            actions.user.dictation_insert(text)

    def stop_typing(text: str) -> None:  # noqa: N805 - Talon actions take no self
        """Switch to command mode, then run any words said after it."""
        actions.user.command_mode()
        if text:
            actions.mimic(text)
