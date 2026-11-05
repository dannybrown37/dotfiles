; @doc fleet: Alt+W - show/hide the always-warm fleet cockpit (agents, review radar, Ctrl+P palette)
; Same show/hide trick as quick_run.ahk: the window is created once and then
; only hidden and shown. `fleet cockpit` attaches to the `fleet` tmux session,
; so closing the window loses nothing.
FleetTitle := "Fleet ahk_exe WindowsTerminal.exe"

!w:: {
    DetectHiddenWindows(true)
    windowHandleId := WinExist(FleetTitle)

    if !windowHandleId {
        shell := ComObject("WScript.Shell")
        shell.Run('wt.exe -w fleet --title "Fleet" wsl.exe -- bash -lic "~/projects/dotfiles/scripts/fleet.sh cockpit"', 0, false)
        return
    }

    if WinActive(FleetTitle) {
        WinHide(windowHandleId)
    } else {
        WinShow(windowHandleId)
        WinActivate(windowHandleId)
    }
}
