; @doc quick_google: Ctrl+Shift+G - Search Google for selected text
#SingleInstance Force
#NoEnv ; Recommended for performance and compatibility with future AutoHotkey releases.
#Warn ; Enable warnings to assist with detecting common errors.
#Persistent
^+g::
{
  Send, ^c
  Sleep 50
  Run, https://www.google.com/search?q=%clipboard%
  Return
}
