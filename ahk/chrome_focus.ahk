#SingleInstance Force
#NoEnv ; Recommended for performance and compatibility with future AutoHotkey releases.
#Warn ; Enable warnings to assist with detecting common errors.
#Persistent


; Ctrl+Shift+C to focus on open Chrome window
^+c::
{
    if WinExist("Google Chrome")
    {
        WinActivate
    }
    else
    {
        MsgBox, Chrome is not running.
    }
    return
}
