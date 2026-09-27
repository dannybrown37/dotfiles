; @doc picker: Alt+, - fuzzy-search every ,, snippet and bash alias, Enter inserts it into the window you were in
SnippetEntries() {
    entries := []
    for entry in ParseHotstrings(FileRead(A_ScriptDir "\hotstrings.ahk", "UTF-8")) {
        entry.insert := FireHotstring.Bind(entry.trigger)
        entries.Push(entry)
    }
    for aliasName, aliasValue in Aliases
        entries.Push({trigger: ",," aliasName, options: "", preview: aliasValue, insert: SendText.Bind(aliasValue)})
    return entries
}

; Typing the trigger back at SendLevel 1 lets the script's own hotstrings see
; it, so dynamic ones like ,,song run their code instead of pasting a preview.
FireHotstring(trigger) {
    Hotstring("Reset")
    SendLevel(1)
    SendEvent("{Raw}" trigger)
    SendLevel(0)
}

PickerWindow := 0
PickerMove := 0

; The search box keeps focus while these move the list selection, so typing
; and navigating never need a Tab between them.
#HotIf PickerWindow && WinActive("ahk_id " PickerWindow)
Down::
^n::
^j::PickerMove(1)
Up::
^p::
^k::PickerMove(-1)
#HotIf

!,:: {
    targetWindow := WinExist("A")
    allEntries := SnippetEntries()
    shown := allEntries

    picker := Gui("+AlwaysOnTop +ToolWindow -Caption +Border", "Snippet picker")
    picker.SetFont("s11", "Consolas")
    search := picker.Add("Edit", "w900")
    list := picker.Add("ListView", "w900 r18 -Multi", ["Trigger", "Inserts"])
    picker.Add("Button", "Default Hidden", "OK").OnEvent("Click", Choose)
    list.OnEvent("DoubleClick", Choose)
    search.OnEvent("Change", Refresh)
    picker.OnEvent("Escape", (*) => picker.Destroy())
    picker.OnEvent("Close", (*) => picker.Destroy())

    Refresh()
    global PickerWindow := picker.Hwnd
    global PickerMove := MoveSelection
    picker.Show()

    Refresh(*) {
        shown := FilterSnippets(allEntries, search.Value)
        list.Opt("-Redraw")
        list.Delete()
        for entry in shown
            list.Add(, entry.trigger, entry.preview)
        list.ModifyCol(1, "AutoHdr")
        list.Modify(1, "Select Focus Vis")
        list.Opt("+Redraw")
    }

    MoveSelection(step) {
        row := Max(1, Min(list.GetCount(), list.GetNext(0, "F") + step))
        list.Modify(row, "Select Focus Vis")
    }

    Choose(*) {
        row := list.GetNext(0, "F")
        if !row
            return
        chosen := shown[row]
        picker.Destroy()
        if !targetWindow
            return
        WinActivate(targetWindow)
        if WinWaitActive(targetWindow, , 1)
            chosen.insert.Call()
    }
}
