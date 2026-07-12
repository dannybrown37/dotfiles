---
name: project-manager
description: "Invoke when working on the project_manager package — the GTD + 12-Week Year TUI app backed by Notion and local JSON."
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Project Manager

A personal productivity CLI at `project_manager/` combining David Allen's **Getting Things Done** (GTD) with **12-Week Year** (12WY) goal tracking. Entry point: `gtd` (runs the TUI by default). Legacy fzf menu: `gtd fzf`.

**Install**: `uv tool install -e .` — must be re-run after every code change for the installed `gtd` binary to pick up changes.

## Architecture

```
src/gtd/
├── gtd.py          # CLI entry point (click group); gtd / gtd fzf / gtd tui / gtd triage / etc.
├── gtd_tui.py      # Unified Textual TUI — GTDApp (main), all tab content widgets
├── tui.py          # Shared Textual widgets: modals, GoalsApp, GoalsContent, VimListView, ScorecardScreen
├── models.py       # Pydantic: Goal, Tactic, Todo, Update
├── storage.py      # Local JSON I/O for goals + weekly habits (~/.local/share/gtd/)
├── cli.py          # 12WY fzf-based CLI (legacy pm command)
├── ui.py           # fzf helpers (fzf_on_a_list), CancelAction
├── views.py        # Goal display builders (progress bars, headers)
├── actions.py      # Goal mutations (scoring, editing, tactic/todo management)
└── notion/
    ├── client.py   # Notion REST API client (httpx)
    ├── commands.py # GTD command implementations (update, defer, snooze, done)
    ├── entries.py  # ProjectEntry fetching and filtering; _get_today_entries, _today_filter
    ├── triage.py   # Triage flow logic; TRIAGE_STATUSES
    ├── capture.py  # Inbox capture
    ├── log.py      # Log & reschedule; _is_recurring, _infer_reschedule_days
    ├── today.py    # Today filter logic
    ├── models.py   # ProjectEntry dataclass
    ├── schema.py   # Notion DB schema: STATUSES (includes Recurring), STATUS_ICONS
    ├── config.py   # ~/.config/gtd/ config management
    └── init.py     # DB creation/upgrade; reads NOTION_PROJECTS_DB_ID + NOTION_NOTES_TOKEN env vars
```

## TUI Layout (GTDApp)

Eight tabs: **Today | Inbox | Projects | Recurring | Waiting For | Snoozed | Someday | Goals**

All entry tabs extend `BaseEntryContent(Vertical)` with stable IDs (`#entry-list`, `#entry-detail`, etc.) and shared infrastructure. Override `_build_filter()` to define what Notion entries appear. `TodayContent` overrides `_load_entries()` entirely (uses `_get_today_entries()`).

### Today tab

The Today tab has three sections in the left list:

1. **Weekly habit reminders** (top, always) — shown when not done this week:
   - `● Weekly Review` — `W` opens a guided 6-step flow via `WeeklyReviewScreen` modal. Steps: (1) Triage Inbox, (2) Review Projects, (3) Review Waiting For, (4) Review Someday/Maybe [uses `SomedayBrowseScreen`], (5) Review Areas of Focus, (6) Plan next week's priorities + Review Calendar [manual steps]. State persisted per-week in `weekly_habits.json` under `review_state`; resumes at first incomplete step.
   - `● Score Goals` — `W` opens `ScorecardScreen` for each active goal sequentially
   - Both use `check_action` to show `W` only when habit item is focused
   - Completion stored in `~/.local/share/gtd/weekly_habits.json`; resets each Monday

2. **GTD entries** — standard entries from Notion, separated with `── GTD ──` when habits are present

3. **12-Week Goals section** — tactics grouped by goal with per-goal sub-separators:
   - `── 12-Week Goals (N due) ──` header
   - `── Goal Name  N due ──` per-goal sub-header
   - `TacticListItem`s sorted within each goal: due → partial → done
   - Visual: `● tactic  cadence` (red=due), `◑ tactic  cadence · n/total` (yellow=partial), `✓ tactic  cadence` (dim=done)

**`check_action` in TodayContent** — three mutually exclusive modes:
- `_HABIT_ACTIONS = {'complete_habit'}` — only active when habit focused
- `_TACTIC_ACTIONS = {'log_tactic'}` — only active when tactic focused  
- `_GTD_ACTIONS = {log, snooze, waiting_for, update_entry, edit_notes, mark_done}` — only active when GTD entry focused
- Returns explicit `True`/`False` (not `None`) for all three sets

### Inbox tab

**T** triages selected entry, **A** triages all — both use TUI modals (no fzf). `_triage_one()` chains: `SelectModal(status)` → `SelectModal(context)` → `InputModal(next step)` → `InputModal(due date)` → `InputModal(follow-up)`. Core logic is in `triage_entries(entries)` (public, no `@work`); `action_triage_all` wraps it with `@work`.

### Other tabs

- **Recurring** — Status == 'Recurring'; `L` log+reschedule (stays in list), `D` drop
- **Waiting For** — Status == 'Waiting For'
- **Snoozed** — Current Project + follow_up > today
- **Projects / Someday** — standard status filters
- **Goals** — `GoalsContent` widget (from `tui.py`); `E` opens edit sub-menu

## SelectModal UX

Two-mode design: opens in **browse mode** (ListView focused, j/k navigate). **Tab** switches to **filter mode** (Input focused, type to filter). Any printable non-j/k key in browse mode jumps to filter and appends char. Default is browse mode.

## SomedayBrowseScreen

`ModalScreen` used during Weekly Review step 4 (Review Someday/Maybe). Shows a scrollable list of Someday items — scroll with j/k, optionally **a** to activate or **d** to drop any item. No forced per-item decision; user browses at will and dismisses when done.

## GoalsContent (tui.py)

`E` → sub-menu: Name & description / Start & end dates / Edit a tactic / Remove a tactic. All async actions decorated with `@work` (required when called from GTDApp context). `ScorecardScreen` is importable from `tui.py`.

## Tactic Cadence System

Cadences parsed in `_parse_cadence_per_week()` in `gtd_tui.py`:
- `daily` / `every day` → 7x/week (checks `_updated_today`)
- `Nx/week` → N times (checks `_count_updates_this_week`)
- `sprint` → 1x per 14-day rolling window (checks `_updated_in_sprint`)
- anything else → 1x/week

Key helpers: `_tactic_is_due`, `_tactic_sort_key`, `_render_tactic_detail`, `_tactic_status_line`, `_DAILY_CADENCE = 7`, `_SPRINT_DAYS = 14`.

## Data Stores

| Data | Store | Location |
|------|-------|----------|
| GTD projects/inbox | Notion database | `NOTION_PROJECTS_DB_ID` env var |
| 12WY goals/tactics/todos | Local JSON | `~/.local/share/gtd/<goal-name>.json` |
| Weekly habit completion | Local JSON | `~/.local/share/gtd/weekly_habits.json` |
| Areas of Focus | Local JSON | `~/.local/share/gtd/areas.json` |
| GTD config | Local JSON | `~/.config/gtd/config.json` |

`get_stored_goal_names()` excludes `config.json`, `weekly_habits.json`, and `areas.json` from glob results.

## Areas of Focus

`load_areas()` / `save_areas(areas)` in `storage.py` manage `areas.json` — a list of `{name: str, notes: str}` dicts. `load_areas()` returns `[]` when the file is missing.

**CLI commands** (`gtd areas`):
- `gtd areas` — list all areas (name + notes if present); prints "No areas defined" when empty
- `gtd areas add "Health"` — add new area; `--notes "..."` sets optional description; duplicate names rejected (case-insensitive)
- `gtd areas remove "Health"` — remove area by name (case-insensitive)
- `gtd areas notes "Health" "some notes"` — update notes field for existing area

## Key Models

**ProjectEntry** (Notion-backed): `page_id`, `header`, `status`, `context`, `next_step`, `due_date`, `follow_up_date`

**Goal** (local JSON, Pydantic): `name`, `description`, `start_date`, `end_date`, `tactics: list[Tactic]`, `todos: list[Todo]`

**Tactic**: `description`, `reminder_cadence` (e.g. `"daily"`, `"2x/week"`, `"sprint"`, `"weekly"`), `updates: list[Update]`, `weekly_scores: dict[str, int]`

**STATUSES** (schema.py): includes `'Recurring'` — items surface on Today when follow_up_date ≤ today; `action_mark_done` on recurring items offers Reschedule vs Permanently complete. Run `gtd init --upgrade` to add new statuses to an existing Notion DB.

## Shared Action Helpers (gtd_tui.py module-level)

- `_shared_log_and_reschedule(app, entry, notes_cache)` — opens editor, saves notes, infers or prompts reschedule date, updates Notion. Returns new date string or None.
- `_shared_edit_notes(app, entry, notes_cache, refresh_cb)` — opens editor, saves notes only.
- `_prompt_and_get_props(app, entry, field)` — prompts for a single field update, returns props dict.

## Textual Conventions

- `VimListView(ListView)` — adds j/k/G/g bindings; k at index 0 posts `FocusTabBar`
- `DetailPane(ScrollableContainer)` — `can_focus = False` so Tab skips it
- `SeparatorListItem(ListItem)` — `disabled=True`, used as visual dividers; supports markup in label
- `WeeklyHabitItem(ListItem)` — habit reminder item with `habit_key` and `habit_label` attrs
- `TacticListItem(ListItem)` — holds full `Tactic` object; `refresh_display(tactic)` updates label in-place
- Modals: `InputModal`, `SelectModal`, `ConfirmModal`, `TwoFieldModal`, `ScorecardScreen`, `SomedayBrowseScreen` — all `ModalScreen`
- `ENABLE_COMMAND_PALETTE = False` on both App classes
- Use `@work` for ALL async actions that call `push_screen_wait` — required in both standalone and embedded contexts. `@work(thread=True)` for blocking Notion calls.
- **Never `await` a `@work`-decorated method** — it returns a `Worker` object. Extract core logic into a plain `async def` and have both `@work` action and other callers use that.
- Always call `self.app.refresh_bindings()` after selection changes that affect `check_action`
- `check_action` must return explicit `True`/`False` (not `None`) for actions you control — `None` means "defer to parent" which can cause unexpected behaviour with duplicate key bindings
- **`SplitFooter`** — subclass of `Footer`; separates contextual bindings (left) from global app bindings (right) with a ` ─── ` separator. Global section always sourced from `self.app.BINDINGS` directly (not overridable by child widgets).
- **Left pane width**: `40%` via CSS — dynamic, scales with terminal width.

## Tooling

- **uv** for dependency management (`uv run`, `uv sync`)
- **ruff** for lint/format — `uv run ruff check src/` must pass before shipping
- **pytest** for tests — `uv run pytest`
- Python 3.12+, Textual ≥ 0.71, Pydantic ≥ 2, httpx, click, python-dateutil
- After any code change: `uv tool install -e .` to update the installed `gtd` binary
