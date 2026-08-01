; @doc app_toggle: Ctrl+Shift+X/C/D - Toggle focus for VS Code / Chrome / Teams; Alt+A - jump to tmux in VSCode's terminal; Alt+S - same, but to the spotify_player tmux window
#SingleInstance Force
#NoEnv
#Warn
#Persistent
SetTitleMatchMode, 2

ToggleApp(criteria, runTarget := "") {
    windowHandleId := WinExist(criteria)
    if (windowHandleId) {
        if (WinActive(criteria))
            WinMinimize, ahk_id %windowHandleId%
        else {
            WinActivate, ahk_id %windowHandleId%
            WinShow, ahk_id %windowHandleId%
        }
    } else if (runTarget != "") {
        Run, % runTarget
    } else {
        MsgBox, Window not found: %criteria%
    }
}

^+z::ToggleApp("ahk_exe Code.exe", "Code.exe")
^+x::ToggleApp("ahk_exe Code.exe", "Code.exe")
^+c::ToggleApp("ahk_exe chrome.exe", "chrome.exe")
^+d::ToggleApp("ahk_class TeamsWebView")

; Brings VSCode's integrated terminal (where tmux lives) to the foreground
; with real keyboard focus. whkd/PowerShell SendKeys couldn't do this --
; Windows blocks synthetic input to a window that isn't already foreground,
; so a background PowerShell process sending Ctrl+` was a no-op. WinActivate
; here (same mechanism as the ToggleApp hotkeys above) reliably brings VSCode
; to the foreground first.
FocusTerminal(releaseKey) {
    RunWait, komorebic.exe focus-workspace 0,, Hide
    WinActivate, ahk_exe Code.exe
    WinWaitActive, ahk_exe Code.exe,, 2

    ; Alt is still physically held here, so a bare Send would deliver
    ; Ctrl+Alt+` and VSCode's terminal-focus binding would never fire.
    KeyWait, % releaseKey
    KeyWait, Alt
    Sleep, 150
    ; Ctrl+Shift+Alt+F9 is bound to workbench.action.terminal.focus in
    ; .vscode/keybindings.json. Ctrl+` is a *toggle*, and the panel may
    ; already be visible, so it would hide it instead.
    ; SendEvent, not SendInput: Electron drops SendInput's zero-delay
    ; keystrokes. terminal.focus is idempotent, so the retry is harmless.
    SetKeyDelay, 30, 30
    SendEvent, ^+!{F9}
    Sleep, 120
    SendEvent, ^+!{F9}
}

; Jump straight to tmux -- whatever window the session is already on.
!a::FocusTerminal("a")

; Same as !a, but selects the pinned spotify_player tmux window first.
!s::
    RunWait, wsl.exe bash -l -i -c "source ~/.bashrc; spotify_player_jump",, Hide
    FocusTerminal("s")
return
