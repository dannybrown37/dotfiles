#Requires AutoHotkey v2.0
; Pure text helpers -- no windows, clipboard or keystrokes -- so that
; ahk/tests/test_text.ahk can cover them without driving a desktop.

SplitWords(text) {
    text := RegExReplace(text, "([a-z0-9])([A-Z])", "$1 $2")
    text := RegExReplace(text, "([A-Z]+)([A-Z][a-z])", "$1 $2")
    text := Trim(RegExReplace(text, "[\s_\-.]+", " "))
    return text = "" ? [] : StrSplit(text, " ")
}

JoinWords(words, separator, capitalizeFrom) {
    out := ""
    for index, word in words {
        word := StrLower(word)
        if (index >= capitalizeFrom)
            word := StrUpper(SubStr(word, 1, 1)) SubStr(word, 2)
        out .= (index > 1 ? separator : "") word
    }
    return out
}

ToSnakeCase(text) => JoinWords(SplitWords(text), "_", 0x7FFFFFFF)
ToKebabCase(text) => JoinWords(SplitWords(text), "-", 0x7FFFFFFF)
ToCamelCase(text) => JoinWords(SplitWords(text), "", 2)
ToPascalCase(text) => JoinWords(SplitWords(text), "", 1)

UrlEncode(text) {
    bytes := Buffer(StrPut(text, "UTF-8"))
    StrPut(text, bytes, "UTF-8")
    out := ""
    Loop bytes.Size - 1 {
        byte := NumGet(bytes, A_Index - 1, "UChar")
        out .= IsUnreservedUrlByte(byte) ? Chr(byte) : Format("%{:02X}", byte)
    }
    return out
}

IsUnreservedUrlByte(byte) {
    return (byte >= 0x30 && byte <= 0x39) || (byte >= 0x41 && byte <= 0x5A) || (byte >= 0x61 && byte <= 0x7A)
        || byte = 0x2D || byte = 0x5F || byte = 0x2E || byte = 0x7E
}

UrlDecode(text) {
    out := ""
    position := 1
    while (found := RegExMatch(text, "(%[0-9A-Fa-f]{2})+", &escapes, position)) {
        out .= SubStr(text, position, found - position) PercentRunToString(escapes[0])
        position := found + escapes.Len[0]
    }
    return out SubStr(text, position)
}

PercentRunToString(escapes) {
    count := StrLen(escapes) // 3
    bytes := Buffer(count)
    Loop count
        NumPut("UChar", Integer("0x" SubStr(escapes, A_Index * 3 - 1, 2)), bytes, A_Index - 1)
    return StrGet(bytes, count, "UTF-8")
}

StripTracking(url) {
    if !RegExMatch(url, "^(https?://[^?#]*)(?:\?([^#]*))?(#.*)?$", &parts)
        return url
    kept := []
    for param in StrSplit(parts[2], "&") {
        if (param != "" && !RegExMatch(param, "i)^(utm_\w+|fbclid|gclid|dclid|gbraid|wbraid|msclkid|mc_cid|mc_eid|igshid|si|ref_src|_hsenc|_hsmi|yclid|twclid)(=|$)"))
            kept.Push(param)
    }
    query := ""
    for index, param in kept
        query .= (index = 1 ? "?" : "&") param
    return parts[1] query parts[3]
}

PrettyJson(text, indent := "  ") {
    text := Trim(text, " `t`r`n")
    if !RegExMatch(text, "^[\[{]")
        return text
    out := ""
    depth := 0
    inString := false
    escaped := false
    Loop Parse text {
        char := A_LoopField
        if inString {
            out .= char
            if escaped
                escaped := false
            else if (char = "\")
                escaped := true
            else if (char = '"')
                inString := false
            continue
        }
        switch char {
            case '"':
                inString := true
                out .= char
            case "{", "[":
                depth++
                out .= char "`n" RepeatText(indent, depth)
            case "}", "]":
                depth := Max(depth - 1, 0)
                out .= "`n" RepeatText(indent, depth) char
            case ",":
                out .= char "`n" RepeatText(indent, depth)
            case ":":
                out .= ": "
            case " ", "`t", "`r", "`n":
            default:
                out .= char
        }
    }
    return RegExReplace(out, "([\[{])\s+([\]}])", "$1$2")
}

RepeatText(text, count) {
    out := ""
    Loop count
        out .= text
    return out
}

ResolveTarget(text, jiraBaseUrl) {
    text := Trim(text, " `t`r`n")
    if (text = "")
        return ""
    if RegExMatch(text, "i)^https?://\S+$")
        return text
    ; Only a single token is checked for a Jira key, so a sentence that merely
    ; mentions "UTF-8" is searched rather than opened as ticket UTF-8.
    if (jiraBaseUrl != "" && !RegExMatch(text, "\s")
        && RegExMatch(text, "(?<![A-Z0-9])([A-Z][A-Z0-9]+-\d+)(?!\d)", &key))
        return RTrim(jiraBaseUrl, "/") "/browse/" key[1]
    return "https://www.google.com/search?q=" UrlEncode(text)
}

MarkdownLink(title, url) {
    title := RegExReplace(title, "\s+-\s+Google Chrome.*$")
    title := RegExReplace(title, "([\[\]])", "\$1")
    url := StrReplace(StrReplace(StripTracking(url), "(", "%28"), ")", "%29")
    return "[" title "](" url ")"
}

CommonPrefixLength(a, b) {
    length := 0
    Loop Min(StrLen(a), StrLen(b)) {
        if !(SubStr(a, A_Index, 1) == SubStr(b, A_Index, 1))
            break
        length++
    }
    return length
}

ParseAliases(text) {
    parsed := Map()
    for line in StrSplit(text, "`n", "`r") {
        if !RegExMatch(line, "^alias\s+([^=]+)=(.*)$", &match)
            continue
        value := match[2]
        if RegExMatch(value, "^'(.*)'$", &quoted)
            value := StrReplace(quoted[1], "'\''", "'")
        parsed[match[1]] := value
    }
    return parsed
}

ParseHotstrings(text) {
    entries := []
    for line in StrSplit(text, "`n", "`r") {
        if RegExMatch(line, "^:([^:]*):(,,[^:]+)::(.*)$", &match)
            entries.Push({trigger: match[2], options: match[1], preview: Trim(RegExReplace(match[3], "\s+;.*$"))})
    }
    return entries
}

FilterSnippets(entries, query) {
    terms := StrSplit(Trim(query), " ")
    if (Trim(query) = "")
        return entries
    triggerMatches := []
    otherMatches := []
    for entry in entries {
        haystack := entry.trigger " " entry.preview
        matchesAll := true
        for term in terms {
            if (term != "" && !InStr(haystack, term)) {
                matchesAll := false
                break
            }
        }
        if matchesAll
            (InStr(entry.trigger, terms[1]) ? triggerMatches : otherMatches).Push(entry)
    }
    triggerMatches.Push(otherMatches*)
    return triggerMatches
}
