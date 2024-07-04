#SingleInstance Force
#NoEnv ; Recommended for performance and compatibility with future AutoHotkey releases.
#Warn ; Enable warnings to assist with detecting common errors.
#Persistent


; Ctrl+Shift+D to toggle Microsoft Teams ("Deams")
^+d::
{
    IfWinExist, Microsoft Teams
    {
        WinGet, MinMax, MinMax, Microsoft Teams
        if (MinMax = -1)  ; If the window is minimized
        {
            WinRestore, Microsoft Teams  ; Restore the window
        }
        else
        {
            WinMinimize, Microsoft Teams  ; Minimize the window
        }
    }
    else
    {
        MsgBox, Microsoft Teams is not running.
    }
    return
}
