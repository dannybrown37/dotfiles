#Requires AutoHotkey v2.0
#SingleInstance Force
#Warn All, StdOut
SetTitleMatchMode(2)

; One process for everything; `ahk` starts this file. autocorrect.ahk stays
; last because the community list sets #Hotstring options that would leak
; onto any hotstring defined after it.
#Include %A_ScriptDir%\lib\text.ahk
#Include %A_ScriptDir%\app_toggle.ahk
#Include %A_ScriptDir%\quick_run.ahk
#Include %A_ScriptDir%\selection.ahk
#Include %A_ScriptDir%\chrome.ahk
#Include %A_ScriptDir%\hotstrings.ahk
#Include %A_ScriptDir%\picker.ahk
#Include *i %A_ScriptDir%\secrets.ahk
#Include %A_ScriptDir%\autocorrect.ahk

; Reload on save. Polling a dozen mtimes every 2s costs well under 1ms. A
; save with a syntax error shows the error once and leaves the running copy
; alone; the next save tries again.
ScriptFilesSignature() {
    signature := ""
    Loop Files, A_ScriptDir "\*.ahk", "R"
        signature .= A_LoopFilePath A_LoopFileTimeModified "|"
    return signature
}

LoadedScriptFilesSignature := ScriptFilesSignature()
SetTimer(ReloadIfScriptsChanged, 2000)

ReloadIfScriptsChanged() {
    global LoadedScriptFilesSignature
    currentSignature := ScriptFilesSignature()
    if (currentSignature = LoadedScriptFilesSignature)
        return
    LoadedScriptFilesSignature := currentSignature
    Reload()
}
