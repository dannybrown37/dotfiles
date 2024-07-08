#SingleInstance Force
#NoEnv
#Warn
#Persistent

; Ctrl+Shift+D to toggle Microsoft Teams ("Deams")
^+d::
{
    if WinExist("ahk_class TeamsWebView")
    {
        WinGet, id, ID, ahk_class TeamsWebView
        if id
        {
            WinGet, MinMax, MinMax, ahk_id %id%
            if (MinMax = -1)  ; If the window is minimized
            {
                WinRestore, ahk_id %id%  ; Restore the window
            }
            else
            {
                WinMinimize, ahk_id %id%  ; Minimize the window
            }
            return
        }
    }
    MsgBox, Microsoft Teams is not running.
    return
}

