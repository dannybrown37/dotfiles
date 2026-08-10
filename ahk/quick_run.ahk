; @doc quick_run: Alt+P - show/hide an always-warm WSL terminal on the `quickrun` tmux session
#SingleInstance Force
#NoEnv
#Warn
#Persistent
SetTitleMatchMode, 2

; The window is created once and then only ever shown or hidden, never
; relaunched. That is the whole point: spawning wt.exe per press cost about a
; second, while `bash -lic exit` is only ~136ms -- the window was the expense,
; not the shell. Because the session lives in tmux, closing the window loses
; nothing; the next Alt+P reattaches to the same shell, scrollback and all.
;
; komorebi is told to ignore this title in wsl/komorebi.json, so showing and
; hiding it does not disturb the tiling layout.
global QuickRunTitle := "WSL Quick Run ahk_exe WindowsTerminal.exe"

!p::
    ; WinExist/WinShow cannot see a window we previously hid without this.
    DetectHiddenWindows, On
    windowHandleId := WinExist(QuickRunTitle)

    if (!windowHandleId) {
        DetectHiddenWindows, Off
        shell := ComObjCreate("WScript.Shell")
        shell.Run("wt.exe -w quickrun --title ""WSL Quick Run"" wsl.exe -- bash -c ""tmux new-session -A -s quickrun""", 0, false)
        return
    }

    ; Visible *and* focused means this press is a dismissal. Visible but
    ; unfocused means it is buried behind something, so raise it instead --
    ; hiding there would feel like the hotkey did nothing.
    if (WinActive(QuickRunTitle)) {
        WinHide, ahk_id %windowHandleId%
    } else {
        WinShow, ahk_id %windowHandleId%
        WinActivate, ahk_id %windowHandleId%
    }
    DetectHiddenWindows, Off
return
