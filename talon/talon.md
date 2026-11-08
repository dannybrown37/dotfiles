# Talon Cheat Sheet

Commands work in command mode. The dot at the top of the screen shows the mode.

## Modes

| Say / do | Effect |
| --- | --- |
| pop | Toggle dictation ↔ command |
| `start typing` / `stop typing` | Dictation / command (missed? say it twice) |
| `start typing <words>` | Dictation, then type the words |
| `stop typing <command>` | Command mode, then run the command |
| `<words> stop typing [<command>]` | Mid-sentence: type the words, then switch |
| `mixed mode` | Commands and dictation both on (`command mode` to leave) |
| `command history` | Show what Talon heard (say again to hide) |
| `wake up` | Wake from sleep |
| `chief sleep` | Sleep |

## tmux windows

| Say | Effect |
| --- | --- |
| `mux left` / `mux right` | Previous / next window |
| `mux window <number>` | Jump to window N (status bar numbers, from 0) |
| `mux new window` | New window |
| `mux rename window` | Rename window |
| `mux kill window` | Close window (asks y/n) |
| `mux sessions` | Pick a session |

## tmux panes

| Say | Effect |
| --- | --- |
| `pane left` / `right` / `up` / `down` | Move to the pane on that side |
| `pane next` | Next pane |
| `pane zoom` | Zoom pane in/out |
| `pane split right` / `pane split down` | New pane |
| `pane close` | Close pane (asks y/n) |

Avoid `split …`, `focus …`, `tab …` and `mux close window` in tmux: they go to
Windows Terminal or press keys this tmux.conf unbinds.

## Claude Code and Copilot

Works in Windows Terminal, in command or dictation mode.

| Say | Effect |
| --- | --- |
| `slash <name>` | Type `/name`, e.g. `slash code review`, `slash compact` |
| then `enter` | Run the top menu match |
| then `space` | Start typing arguments |

Skill names are spoken with dashes as spaces. Short forms are said out:
`ci` = "see eye", `cli` = "see el eye", `ui` = "you eye", `tui` = "tooey",
`mcp` = "em see pee". Built-ins live in `slash_builtin.talon-list`. Skills come
from `~/.claude` and `~/.copilot`; re-run `just talon` after adding one.

## Shell (in tmux)

| Say | Effect |
| --- | --- |
| `run <tool>` | Type the command, e.g. `run just`, `run git start`, `run you vee run tests` |
| `katie <words>` / `katie up` | `cd` |
| `lisa` | `ls` |
| `core <utility>` | Type a unix tool, e.g. `core grep` |
| `clear screen` / `run last` | `clear` / up + enter |

Tools live in `cli_command.talon-list`.

Free text after a command: `run git start` then `kebab voice fixes` =
`git start voice-fixes`. `say <words>` types words as-is, `smash` joins them.
End with `over` so the next words are a new command.

## Git (any terminal)

| Say | Effect |
| --- | --- |
| `git status` | Runs at once |
| `git <subcommand>` | Type it, e.g. `git diff`, `git log`, `git cherry pick` |
| `git commit message <words>` | `git commit --message "<words>"` |
| `git add patch` | `git add --patch`, runs at once |

## Repeat and chain

| Say | Effect |
| --- | --- |
| `<command> twice` / `third` / `<n> times` | Repeat the last command |
| `<cmd> then <cmd>` | Force a break between two commands in one breath |
| `<words> over` | End free text, next words are a command |

## Fix misheard words

| Say | Effect |
| --- | --- |
| `copy to vocab [as <phrase>]` | Add the selected word to Talon's vocabulary |
| `draft this` / `draft submit` | Edit long text in a pop-up, then paste it |

## Editing

| Say | Effect |
| --- | --- |
| `clear line` | Delete the whole line (also in tmux: shell and Claude Code prompt) |
| `tail`, then `control urge` | Delete the whole line in a terminal outside tmux |
| `clear way left` / `clear way right` | Delete to line start / end (not in a terminal) |
| `clear all` | Delete everything |

## Switch apps

| Say | Effect |
| --- | --- |
| `focus chrome` / `focus term` | Go to Chrome / Windows Terminal |
| `focus last` | Back to the previous window (say again to return) |
| `focus` | Pick from a menu of open apps |
| `running list` | Show the names `focus` accepts |

## Chrome

| Say | Effect |
| --- | --- |
| `tab new` / `tab close` / `tab next` / `tab last` | Tabs |
| `go tab <number>` / `go tab final` | Jump to a tab |
| `tab reopen` | Reopen a closed tab |
| `tab search <words>` | Chrome's tab search |
| `go address` | Focus the URL bar |
| `go back` / `go forward` | History back / forward |
| `refresh it` / `refresh it hard` | Reload |
| `bookmark it` | Bookmark the page |
| `show history` / `show downloads` | Open those pages |
| `dev tools` | Toggle DevTools |
| `find it <words>` | Find on page |
| `mouse grid`, then numbers | Click anywhere |

## Rango (click in Chrome)

Needs the [Rango extension](https://chrome.google.com/webstore/detail/rango/lnemjdnjjofijemhdogofbpcedhgcpmb).
Each link and button gets a letter hint. Pause before and after a hint.

| Say | Effect |
| --- | --- |
| `<hint>`, e.g. `air` / `gust harp` | Click hint `a` / `gh` |
| `press air` | Type `a` (when it is also a hint) |
| `blank <hint>` / `stash <hint>` | Open link in new tab / background tab |
| `hover <hint>` / `show <hint>` | Hover / show title and URL |
| `insert <text> to <hint>` | Type into a field |
| `paste to <hint>` | Paste into a field |
| `upper` / `downer` (`all`) | Scroll up / down (to the end) |
| `tiny up` / `tiny down` | Small scroll |
| `crown <hint>` | Scroll that element to the top |
| `click text <words>` | Click by visible text |
| `go tab <hint>` / `tab back` | Tab by marker / previous tab |
| `hints toggle` / `hints refresh` | Hide-show / redraw hints |
| `rango settings` | Open Rango settings |

Full list: [Rango README](https://github.com/david-tejada/rango#readme).

## Keys

| Say | Effect |
| --- | --- |
| `control drum` | Ctrl+D (tmux prefix) |
| `control drum` then a letter word | Any tmux binding, e.g. `ship fine` (F) = fleet dashboard |
| `help alphabet` | Show letter words on screen |

### Alphabet

| a | b | c | d | e | f | g | h | i |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| air | bat | cap | drum | each | fine | gust | harp | sit |

| j | k | l | m | n | o | p | q | r |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| jury | crunch | look | made | near | odd | pit | quench | red |

| s | t | u | v | w | x | y | z |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sun | trap | urge | vest | whale | plex | yank | zip |

- Chain letters in one breath: `air bat cap` types `abc`.
- Capitals: `ship <letters>`, e.g. `ship fine` = `F`.
- Numbers: `numb <number>`, e.g. `numb forty two` = `42`. Digit keys: `zero` … `nine`.

### Keys and modifiers

| Say | Key |
| --- | --- |
| `control` / `shift` / `alt` / `super` + key | Combo, e.g. `control shift tab`, `alt fine` |
| `up` / `down` / `left` / `right` | Arrows |
| `enter` / `escape` / `tab` / `space` | Same |
| `wipe` or `delete` | Backspace |
| `forward delete` | Delete |
| `home` / `end` / `page up` / `page down` | Same |
| `f one` … `f twelve` | Function keys |
| `press <key>` | Any key, also works in dictation |

### Symbols (command mode)

| Say | Sym | Say | Sym | Say | Sym |
| --- | --- | --- | --- | --- | --- |
| `dot` / `point` | `.` | `comma` | `,` | `semi` | `;` |
| `colon` | `:` | `question` | `?` | `bang` | `!` |
| `quote` | `'` | `dub quote` | `"` | `grave` | `` ` `` |
| `dash` / `minus` | `-` | `underscore` | `_` | `equals` | `=` |
| `plus` | `+` | `star` | `*` | `slash` | `/` |
| `backslash` | `\` | `pipe` | `\|` | `amper` | `&` |
| `hash` | `#` | `dollar` | `$` | `percent` | `%` |
| `caret` | `^` | `tilde` | `~` | `at sign` | `@` |
| `paren` / `R paren` | `(` `)` | `brack` / `R brack` | `[` `]` | `brace` / `R brace` | `{` `}` |
| `angle` / `rangle` | `<` `>` | | | | |

In dictation, use the full name: `comma`, `period`, `question mark`, `forward slash`.

### Formatters (command mode)

Say the formatter, then the words: `snake hello world` = `hello_world`.

| Say | Result | Say | Result |
| --- | --- | --- | --- |
| `snake` | `hello_world` | `kebab` | `hello-world` |
| `camel` | `helloWorld` | `hammer` | `HelloWorld` |
| `constant` | `HELLO_WORLD` | `all cap` | `HELLO WORLD` |
| `smash` | `helloworld` | `dotted` | `hello.world` |
| `conga` | `hello/world` | `dunder` | `hello__world` |
| `string` | `'hello world'` | `dub string` | `"hello world"` |
| `say` | `hello world` | `sentence` / `title` | `Hello world` / `Hello World` |
| `word <w>` | one word | `<formatter> that` | Reformat the selection |

## Chief

| Say | Effect |
| --- | --- |
| `chief waiting` | Anything waiting on me? |
| `chief status` | One line per agent |
| `chief say <words>` | Type a message into the chief |
