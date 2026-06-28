# Project Manager

A CLI implementation of the [12-Week Year](https://12weekyear.com/) planning method.

## What it does

- Create goals with a 12-week time horizon
- Define tactics (recurring actions) with cadences like daily, weekly, 2x/week
- Score tactics weekly on a 1–10 scale to track execution
- Manage to-dos with optional due dates
- View progress bars, score history, and overall execution percentage
- Archive completed goals and start new cycles carrying over tactics/todos

## Requirements

- Python 3.12+
- [fzf](https://github.com/junegunn/fzf) (for interactive menus)

## Installation

```bash
cd project_manager
uv sync
uv pip install -e .
```

This installs the `pm` command.

## Usage

### Interactive mode

```bash
pm
```

Opens the fzf-powered menu. Navigate goals, score tactics, manage to-dos.

### Quick status (no fzf needed)

```bash
pm status
```

Prints a snapshot of all goals to stdout — useful for scripts, tmux status bars, or a quick glance.

### Workflow

1. **Create a goal** — give it a name and description, it auto-sets a 12-week window
2. **Add tactics** — the recurring actions that drive the goal (e.g. "Write 500 words daily")
3. **Score weekly** — at the end of each week, rate each tactic 1–10
4. **Track to-dos** — one-off tasks with optional due dates
5. **Review** — watch your execution % and adjust tactics that aren't working
6. **Cycle** — when the 12 weeks end, start a new cycle (optionally carrying over tactics)

### Key concepts from the 12-Week Year

- **85% execution = success** — the green threshold. You don't need perfection.
- **Weekly scoring** — the core accountability mechanism. Score honestly.
- **Tactics ≠ to-dos** — tactics are recurring habits; to-dos are one-off tasks.

## Data storage

Goals are stored as JSON files in `~/.local/share/project_manager/`. They're human-readable and easy to back up.

## Project structure

```
src/project_manager/
├── models.py    # Pydantic models (Goal, Tactic, Todo)
├── storage.py   # File I/O and path management
├── ui.py        # fzf helpers, prompts, formatting
├── views.py     # Display builders (headers, progress bars)
├── actions.py   # Goal actions (scoring, editing, cycling)
└── cli.py       # Menu routing and entry point
```
