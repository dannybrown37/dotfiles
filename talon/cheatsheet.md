# Talon Cheat Sheet

Commands work in command mode. The dot at the top of the screen shows the mode.

## Modes

| Say / do | Effect |
| --- | --- |
| pop | Toggle dictation ↔ command |
| `start typing` / `stop typing` | Dictation / command |
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
