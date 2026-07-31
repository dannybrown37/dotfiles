; @doc app_toggle: Ctrl+Shift+X/C/D - Toggle focus for VS Code / Chrome / Teams
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
