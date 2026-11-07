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

## Keys

| Say | Effect |
| --- | --- |
| `control drum` | Ctrl+D (tmux prefix) |
| `control drum` then a letter word | Any tmux binding, e.g. `fox` = fleet dashboard |
| `help alphabet` | Show letter words |

## Chief

| Say | Effect |
| --- | --- |
| `chief waiting` | Anything waiting on me? |
| `chief status` | One line per agent |
| `chief say <words>` | Type a message into the chief |
