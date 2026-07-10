---
name: project-manager
description: "Invoke when working on the project_manager package — the GTD + 12-Week Year TUI app backed by Notion and local JSON."
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Project Manager

A personal productivity CLI at `project_manager/` combining David Allen's **Getting Things Done** (GTD) with **12-Week Year** (12WY) goal tracking. Entry point: `gtd` (runs the TUI by default). Legacy fzf menu: `gtd fzf`.

## Architecture

```
src/gtd/
├── gtd.py          # CLI entry point (click group); gtd / gtd fzf / gtd tui / gtd triage / etc.
├── gtd_tui.py      # Unified Textual TUI — GTDApp (main), all tab content widgets
├── tui.py          # Shared Textual widgets: modals, GoalsApp, GoalsContent, VimListView
├── models.py       # Pydantic: Goal, Tactic, Todo, Update
├── storage.py      # Local JSON I/O for goals (~/.local/share/gtd/)
├── cli.py          # 12WY fzf-based CLI (legacy pm command)
├── ui.py           # fzf helpers (fzf_on_a_list), CancelAction
├── views.py        # Goal display builders (progress bars, headers)
├── actions.py      # Goal mutations (scoring, editing, tactic/todo management)
└── notion/
    ├── client.py   # Notion REST API client (httpx)
    ├── commands.py # GTD command implementations (update, defer, snooze, done)
    ├── entries.py  # ProjectEntry fetching and filtering
    ├── triage.py   # Triage flow logic; TRIAGE_STATUSES, _process_single_entry
    ├── capture.py  # Inbox capture
    ├── log.py      # Log & reschedule
    ├── today.py    # Today filter logic
    ├── models.py   # ProjectEntry dataclass
    ├── schema.py   # Notion DB schema: STATUSES, STATUS_ICONS, property names
    ├── config.py   # ~/.config/gtd/ config management
    └── init.py     # DB creation/upgrade
```

## TUI Layout (GTDApp)

Five tabs: **Today | Inbox | Projects | Someday | Goals**

Each tab is a `Vertical` widget with:
- Left pane (44 wide): `VimListView` + header `Static`
- Right pane (1fr): `DetailPane` (scrollable, non-focusable) showing rendered entry detail

**Today tab extras**: below the GTD items, a `── 12-Week Goals ──` separator followed by `TacticListItem`s from all active goals. GTD actions (Log, Snooze, etc.) are hidden when a tactic is focused; **N → Log update** appears instead. `check_action` + `refresh_bindings()` drives this.

**Inbox tab**: **T** triages selected entry, **A** triages all — both use TUI modals (no fzf, no app suspension). `_triage_one()` chains: SelectModal(status) → SelectModal(context) → InputModal(next step) → InputModal(due date) → InputModal(follow-up).

## Data Stores

| Data | Store | Location |
|------|-------|----------|
| GTD projects/inbox | Notion database | configured via `NOTION_PROJECTS_DB_ID` |
| 12WY goals/tactics/todos | Local JSON | `~/.local/share/gtd/` |

## Key Models

**ProjectEntry** (Notion-backed): `page_id`, `header`, `status`, `context`, `next_step`, `due_date`, `follow_up_date`

**Goal** (local JSON, Pydantic): `name`, `description`, `start_date`, `end_date`, `tactics: list[Tactic]`, `todos: list[Todo]`

**Tactic**: `description`, `reminder_cadence` (e.g. "daily", "2x/week"), `updates: list[Update]`, `weekly_scores: dict[str, int]`

## Textual Conventions

- `VimListView(ListView)` — adds j/k/G/g bindings; k at index 0 posts `FocusTabBar`
- `DetailPane(ScrollableContainer)` — `can_focus = False` so Tab skips it
- Modals: `InputModal`, `SelectModal`, `ConfirmModal`, `TwoFieldModal` — all `ModalScreen`, dismiss with result
- `ENABLE_COMMAND_PALETTE = False` on both App classes (ctrl+p intercepted by VSCode)
- Use `@work` for async actions, `@work(thread=True)` for blocking Notion calls
- Always call `self.app.refresh_bindings()` after selection changes that affect `check_action`

## Tooling

- **uv** for dependency management (`uv run`, `uv sync`)
- **ruff** for lint/format — `uv run ruff check src/` must pass before shipping
- **pytest** for tests — `uv run pytest`
- Python 3.12+, Textual ≥ 0.71, Pydantic ≥ 2, httpx, click, python-dateutil
