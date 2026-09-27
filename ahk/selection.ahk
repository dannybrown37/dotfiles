; @doc selection: Alt+T - transform selected text (case, JSON, URL) from a keyboard menu; Alt+G - open selection (or clipboard) as URL / Jira key / Google search
; Ctrl+Insert / Shift+Insert rather than Ctrl+C / Ctrl+V: in a terminal Ctrl+C
; with nothing selected is SIGINT, and Insert-based copy/paste works in
; Windows Terminal, VS Code, Chrome and Teams alike.
CopySelection() {
    saved := ClipboardAll()
    A_Clipboard := ""
    Send("^{Insert}")
    text := ClipWait(0.5) ? A_Clipboard : ""
    A_Clipboard := saved
    return text
}

PasteText(text) {
    saved := ClipboardAll()
    A_Clipboard := text
    if !ClipWait(0.5)
        return
    Send("+{Insert}")
    ; Restoring immediately races the target app's read of the clipboard.
    Sleep(150)
    A_Clipboard := saved
}

Flash(message) {
    ToolTip(message)
    SetTimer(() => ToolTip(), -1500)
}

Transforms := [
    ["&UPPER CASE", StrUpper],
    ["&lower case", StrLower],
    ["&Title Case", StrTitle],
    ["&snake_case", ToSnakeCase],
    ["&camelCase", ToCamelCase],
    ["&PascalCase", ToPascalCase],
    ["&kebab-case", ToKebabCase],
    ["&JSON pretty print", PrettyJson],
    ["URL &encode", UrlEncode],
    ["URL &decode", UrlDecode],
    ["&Remove link tracking", StripTracking],
]

; Each item has an underlined letter, so the menu is driven entirely from the
; keyboard: Alt+T, then e.g. S for snake_case. Esc cancels.
!t:: {
    text := CopySelection()
    if (text = "") {
        Flash("Select some text first")
        return
    }
    transformMenu := Menu()
    for item in Transforms
        transformMenu.Add(item[1], ((transform, *) => PasteText(transform(text))).Bind(item[2]))
    if CaretGetPos(&caretX, &caretY)
        transformMenu.Show(caretX, caretY + 20)
    else
        transformMenu.Show()
}

; Set the Jira base once from PowerShell, then restart AHK:
;   setx JIRA_BASE_URL https://yourcompany.atlassian.net
!g:: {
    text := CopySelection()
    target := ResolveTarget(text != "" ? text : A_Clipboard, EnvGet("JIRA_BASE_URL"))
    if (target = "")
        Flash("Nothing selected or copied")
    else
        Run(target)
}
