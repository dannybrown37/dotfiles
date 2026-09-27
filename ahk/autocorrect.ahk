; @doc autocorrect: Fixes ~7,000 common typos as you type, everywhere except VS Code and terminals (community list, fetched by `ahk`)
; The kunkel321/AutoCorrect2 list calls f() for each fix. This is a trimmed
; copy of its f() without the logging, beeps and input buffering: erase only
; the part of the typo that differs from the fix, then type the rest.
f(replace := "", *) {
    trigger := SubStr(A_ThisHotkey, InStr(A_ThisHotkey, ":", , , 2) + 1)
    keep := CommonPrefixLength(trigger, replace)
    SendInput("{BS " (StrLen(trigger) + StrLen(A_EndChar) - keep) "}")
    SendText(SubStr(replace, keep + 1) A_EndChar)
}

; Code and shell commands are full of "typos" that are really identifiers.
#HotIf !WinActive("ahk_exe Code.exe") && !WinActive("ahk_exe WindowsTerminal.exe")
#Include *i %A_ScriptDir%\vendor\AutoCorrectHotstrings.ahk
#HotIf
