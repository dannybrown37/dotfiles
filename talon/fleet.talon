mode: command
-
# Work from any app: Alt+W is a global AutoHotkey hotkey (ahk/fleet.ahk).
fleet open: key(alt-w)
fleet help: user.fleet_help_toggle()
fleet status: user.fleet_status()
fleet coach on: user.fleet_coach(1)
fleet coach off: user.fleet_coach(0)
