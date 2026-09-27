#Requires AutoHotkey v2.0
#Include %A_ScriptDir%\..\lib\text.ahk

failures := 0

Check(name, actual, expected) {
    global failures
    if (actual == expected) {
        FileAppend("ok   " name "`n", "*", "UTF-8")
        return
    }
    failures++
    FileAppend("FAIL " name "`n  expected: " expected "`n  actual:   " actual "`n", "*", "UTF-8")
}

SerializeMap(map) {
    out := ""
    for key, value in map
        out .= key "=" value "|"
    return out
}

SerializeEntries(entries) {
    out := ""
    for entry in entries
        out .= entry.trigger "|" entry.options "|" entry.preview "`n"
    return out
}

jira := "https://example.atlassian.net/"

cases := [
    ["snake from camel", ToSnakeCase("fooBarBaz"), "foo_bar_baz"],
    ["snake from mixed separators", ToSnakeCase("Foo Bar-baz"), "foo_bar_baz"],
    ["snake from acronym", ToSnakeCase("HTTPServerError"), "http_server_error"],
    ["camel from snake", ToCamelCase("foo_bar baz"), "fooBarBaz"],
    ["camel from empty", ToCamelCase(""), ""],
    ["pascal from kebab", ToPascalCase("foo-bar"), "FooBar"],
    ["kebab from pascal", ToKebabCase("FooBar baz"), "foo-bar-baz"],

    ["url encode reserved and unicode", UrlEncode("a b&c=d/é"), "a%20b%26c%3Dd%2F%C3%A9"],
    ["url encode leaves unreserved", UrlEncode("AZaz09-_.~"), "AZaz09-_.~"],
    ["url decode unicode", UrlDecode("a%20b%C3%A9"), "a bé"],
    ["url decode leaves malformed escape", UrlDecode("100%"), "100%"],

    ["strip tracking keeps real params and fragment",
        StripTracking("https://x.com/p?utm_source=a&id=3&fbclid=z#frag"), "https://x.com/p?id=3#frag"],
    ["strip tracking drops spotify si",
        StripTracking("https://open.spotify.com/track/abc?si=123"), "https://open.spotify.com/track/abc"],
    ["strip tracking drops empty query", StripTracking("https://x.com/p?utm_source=a"), "https://x.com/p"],
    ["strip tracking leaves clean url", StripTracking("https://x.com/p"), "https://x.com/p"],
    ["strip tracking ignores non urls", StripTracking("why?utm_source=a"), "why?utm_source=a"],

    ["pretty json nests and collapses empties", PrettyJson('{"a":1,"b":[1,2],"c":{}}'),
        '{`n  "a": 1,`n  "b": [`n    1,`n    2`n  ],`n  "c": {}`n}'],
    ["pretty json leaves string contents alone", PrettyJson('{"s":"x, {y} \"z\""}'),
        '{`n  "s": "x, {y} \"z\""`n}'],
    ["pretty json ignores non json", PrettyJson("not json"), "not json"],

    ["resolve url opens as is", ResolveTarget("https://a.com/x", ""), "https://a.com/x"],
    ["resolve jira key", ResolveTarget("  ABC-123 ", jira), "https://example.atlassian.net/browse/ABC-123"],
    ["resolve jira key in branch name", ResolveTarget("feature/ABC-123-fix", jira),
        "https://example.atlassian.net/browse/ABC-123"],
    ["resolve jira key without base searches", ResolveTarget("ABC-123", ""),
        "https://www.google.com/search?q=ABC-123"],
    ["resolve text searches", ResolveTarget("how to x", jira), "https://www.google.com/search?q=how%20to%20x"],
    ["resolve empty", ResolveTarget("  ", jira), ""],

    ["markdown link", MarkdownLink("Some [Page] - Google Chrome", "https://x.com/a_(b)?utm_source=z"),
        "[Some \[Page\]](https://x.com/a_%28b%29)"],
    ["markdown link with profile suffix", MarkdownLink("Docs - Google Chrome – Work", "https://d.io"),
        "[Docs](https://d.io)"],

    ["common prefix", CommonPrefixLength("chuch", "church"), 3],
    ["common prefix is case sensitive", CommonPrefixLength("Teh", "the"), 0],
    ["common prefix empty", CommonPrefixLength("", "x"), 0],

    ["parse aliases", SerializeMap(ParseAliases("alias ll='ls -la'`nalias g=git`r`nalias q='echo '\''hi'\'''`n")),
        "g=git|ll=ls -la|q=echo 'hi'|"],

    ["parse hotstrings", SerializeEntries(ParseHotstrings(
        ":*:,,cl::console.log(){Left}`n"
        "::,,nv::--no-verify   `; comment`n"
        ":*X:,,song::Foo()`n"
        "::btw::by the way`n"
        "`; :*:,,x::commented`n")),
        ",,cl|*|console.log(){Left}`n,,nv||--no-verify`n,,song|*X|Foo()`n"],
]

snippets := [
    {trigger: ",,cl", options: "", preview: "console.log()"},
    {trigger: ",,dockerrun", options: "", preview: "docker run -d image_name"},
    {trigger: ",,log", options: "", preview: "logger = logging.getLogger(__name__)"},
]
cases.Push(
    ["filter empty query keeps all", SerializeEntries(FilterSnippets(snippets, "")), SerializeEntries(snippets)],
    ["filter ranks trigger matches first", SerializeEntries(FilterSnippets(snippets, "log")),
        ",,log||logger = logging.getLogger(__name__)`n,,cl||console.log()`n"],
    ["filter requires every term", SerializeEntries(FilterSnippets(snippets, "dock RUN")),
        ",,dockerrun||docker run -d image_name`n"],
)

for testCase in cases
    Check(testCase*)

ExitApp(failures ? 1 : 0)
