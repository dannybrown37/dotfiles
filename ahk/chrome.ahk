; @doc chrome: Alt+C in Chrome - copy the current tab as a markdown link, tracking params stripped
#HotIf WinActive("ahk_exe chrome.exe")
!c:: {
    title := WinGetTitle("A")
    saved := ClipboardAll()
    A_Clipboard := ""
    Send("^l")
    Sleep(50)
    Send("^c")
    url := ClipWait(0.5) ? A_Clipboard : ""
    ; Esc reverts the address bar edit; F6 hands focus back to the page.
    Send("{Esc}{F6}")
    if (url = "") {
        A_Clipboard := saved
        Flash("Couldn't read the address bar")
        return
    }
    A_Clipboard := MarkdownLink(title, url)
    Flash("Copied " A_Clipboard)
}
#HotIf
