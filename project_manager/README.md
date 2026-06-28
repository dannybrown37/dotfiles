# Project Manager

A CLI for personal productivity combining [GTD (Getting Things Done)](https://gettingthingsdone.com/) with the [12-Week Year](https://12weekyear.com/) planning method.

## What it does

### GTD (`gtd` command) — Notion-backed

- Capture items to an inbox and triage them into projects
- Track projects with contexts, next actions, and follow-up dates
- Log completions and auto-reschedule recurring items
- Defer, snooze, and review Someday/Maybe lists
- Filter by context for focused work sessions

### 12-Week Year (`pm` command) — local JSON

- Create goals with a 12-week time horizon
- Define tactics (recurring actions) with cadences like daily, weekly, 2x/week
- Score tactics weekly on a 1–10 scale to track execution
- Manage to-dos with optional due dates
- View progress bars, score history, and overall execution percentage

## Requirements

- Python 3.12+
- [fzf](https://github.com/junegunn/fzf) (for interactive menus)
- A [Notion integration token](https://developers.notion.com/) (for `gtd`)

## Installation

```bash
cd project_manager
uv sync
uv pip install -e .
```

This installs both the `pm` and `gtd` commands.

## Usage

### GTD interactive mode

```bash
gtd
```

Opens the fzf-powered GTD menu:

<!-- BEGIN MENU -->
| Category | Action |
| --- | --- |
| Do | Today |
| Do | Log & Reschedule |
| Do | Snooze until tomorrow |
| Do | Capture new item |
| Do | Triage inbox |
| Manage | Update project |
| Manage | Defer project until date |
| Manage | Mark done |
| Review | Weekly Review |
| Review | Review Someday/Maybe |
| View | View all projects |
| View | 12-Week Goals |
| View | Filter by context |
<!-- END MENU -->

### GTD subcommands

```bash
gtd triage        # Process inbox items
gtd review        # Guided weekly review ritual
gtd goals         # Show 12-week goal entries
gtd filter work   # Filter projects by context
gtd today         # Show today's actionable items
gtd capture       # Quick-capture to inbox
gtd done          # Mark a project as done
gtd update        # Update project fields
gtd defer         # Defer a project
```

### 12-Week Year

```bash
pm                # Interactive menu
pm status         # Quick snapshot (no fzf needed)
```

## Updating this README

Menu options are extracted from source. After changing menu items in `gtd.py`:

```bash
python scripts/update_readme.py
```

## Data storage

- **GTD**: Notion database (configured via `NOTION_TOKEN` and `NOTION_DATABASE_ID` env vars)
- **12-Week Year**: JSON files in `~/.local/share/project_manager/`

## Project structure

```
src/project_manager/
├── cli.py           # 12-Week Year menu routing and entry point
├── gtd.py           # GTD interactive menu and CLI commands
├── models.py        # Pydantic models (Goal, Tactic, Todo)
├── storage.py       # File I/O and path management
├── ui.py            # fzf helpers, prompts, formatting
├── views.py         # Display builders (headers, progress bars)
├── actions.py       # Goal actions (scoring, editing, cycling)
└── notion/
    ├── client.py    # Notion API client
    ├── models.py    # ProjectEntry dataclass
    ├── commands.py  # GTD command implementations
    ├── capture.py   # Inbox capture
    ├── triage.py    # Triage processing
    └── display.py   # Entry formatting
scripts/
└── update_readme.py # Auto-update README menu section
```
