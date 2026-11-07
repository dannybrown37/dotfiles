from talon import Context, actions, scope

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
