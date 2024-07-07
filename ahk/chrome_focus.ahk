#SingleInstance Force
#NoEnv ; Recommended for performance and compatibility with future AutoHotkey releases.
#Warn ; Enable warnings to assist with detecting common errors.
#Persistent

; Initialize a global variable to keep track of the current window
global currentWindowIndex := 1

; Ctrl+Shift+C to cycle through open Chrome windows
^+c::
{
    ; Get a list of all Chrome windows
    WinGet, id, list, ahk_class Chrome_WidgetWin_1

    ; If no Chrome windows are found, show a message
    if (id = 0)
    {
        MsgBox, Chrome is not running.
        return
    }

    ; If the current window index exceeds the number of windows, reset it
    if (currentWindowIndex > id)
    {
        currentWindowIndex := 1
    }

    ; Get the window ID for the current index
    currentWindowID := id%currentWindowIndex%

    ; Activate the current window
    WinActivate, ahk_id %currentWindowID%

    ; Increment the current window index for the next activation
    currentWindowIndex++

    return
}
