# Habits System Design

## Overview

GitHub-style habit tracking backed by Notion. Track daily habit completions with a visual calendar heatmap. Syncs across all devices and mobile via API.

## Notion Schema

### 1. Habits Database (`NOTION_HABITS_DB_ID`)

**Purpose:** Store habit definitions

**Fields:**

- `Name` (Title) — e.g., "Morning Meditation", "Exercise"
- `Description` (Rich Text, optional) — What the habit is about
- `Color` (Select) — For visual distinction: Blue, Green, Purple, Red, Orange, Yellow
- `Target Frequency` (Select) — Daily, Weekly (X days/week), Monthly
- `Active` (Checkbox) — Whether habit is currently tracked
- `Created Date` (Date) — When habit was created
- `Notes` (Rich Text, optional) — User notes/context

**Example rows:**

```
| Name | Description | Color | Target Frequency | Active | Created Date |
|------|-------------|-------|------------------|--------|--------------|
| Morning Meditation | 10 min | Blue | Daily | ✓ | 2026-07-20 |
| Exercise | 30+ min cardio/strength | Green | 5x/week | ✓ | 2026-07-20 |
| Read | Any reading | Purple | Daily | ✓ | 2026-06-15 |
| Code Review | Team PRs | Orange | 3x/week | ✓ | 2026-05-01 |
```

### 2. Habit Completions Database (`NOTION_HABIT_COMPLETIONS_DB_ID`)

**Purpose:** Track daily completion status

**Fields:**

- `Habit` (Relation → Habits DB) — Links to parent habit
- `Date` (Date) — Day of completion
- `Status` (Select) — Complete, Incomplete, Skipped
- `Notes` (Rich Text, optional) — Why skipped, extra notes
- `Logged At` (Created Time) — When entry was created

**Index:** Unique constraint on (Habit, Date) — one record per habit per day

**Example rows:**

```
| Habit | Date | Status | Notes | Logged At |
|-------|------|--------|-------|-----------|
| Morning Meditation | 2026-07-20 | Complete | | 2026-07-20 09:15 |
| Morning Meditation | 2026-07-19 | Complete | | 2026-07-19 08:45 |
| Morning Meditation | 2026-07-18 | Incomplete | Overslept | 2026-07-18 10:00 |
| Exercise | 2026-07-20 | Complete | 45 min run | 2026-07-20 18:30 |
| Exercise | 2026-07-19 | Skipped | Sick | 2026-07-19 19:00 |
```

## Data Models

### `Habit` (Pydantic)

```python
class Habit(BaseModel):
    page_id: str
    name: str
    description: str = ""
    color: str = "Blue"  # Blue, Green, Purple, Red, Orange, Yellow
    target_frequency: str  # Daily, Weekly, Monthly, or specific (e.g., "5x/week")
    active: bool = True
    created_date: str  # ISO date
    notes: str = ""
```

### `HabitCompletion` (Pydantic)

```python
class HabitCompletion(BaseModel):
    page_id: str
    habit_id: str  # Habit page_id
    date: str  # ISO date (YYYY-MM-DD)
    status: str  # "Complete", "Incomplete", "Skipped"
    notes: str = ""
    logged_at: str  # ISO datetime
```

## Client Functions

**In `gtd/notion/habits.py`:**

- `get_habits()` → list[Habit]
- `create_habit(name, frequency, description)` → Habit
- `update_habit(habit_id, **fields)` → None
- `delete_habit(habit_id)` → None
- `get_completions_for_habit(habit_id, from_date, to_date)` → list[HabitCompletion]
- `get_completions_for_date(date)` → list[HabitCompletion] (all habits on that day)
- `mark_complete(habit_id, date, status, notes)` → HabitCompletion
- `get_calendar_data(habit_id, months_back=12)` → {date: status, ...}

## TUI Implementation

### `HabitsContent(Vertical)` Tab

**Layout:**

```
┌─ Habits ──────────────────────────────────────┐
│                                               │
│ Habit: Morning Meditation                     │
│                                               │
│  Jul 2026                                     │
│  Su Mo Tu We Th Fr Sa                         │
│     [■] [■] [■] [ ] [■] [■] [■]  ← Week row │
│     [■] [■] [■] [■] [■] [■] [■]              │
│     [■] [■] [■] [■] [■] [■] [■]              │
│     [■] [■] [■] [■] [■] [ ] [■]              │
│     [■] [■] [ ]                               │
│                                               │
│ Completions: 24/31 (77%)                      │
│                                               │
│ [Legend: ■=Complete □=Incomplete -=Skipped]   │
└───────────────────────────────────────────────┘
```

**Actions:**

- `H` / `L` — Previous/next habit
- `[ ]` — Toggle day under cursor (cycle: Complete → Incomplete → Skipped)
- `+` — Add new habit
- `E` — Edit habit details
- `D` — Delete habit (with confirm)
- `N` — Add note to selected day

**State:**

- Selected habit (focused)
- Selected date/day (for detail panel or editing)

### Calendar Widget

Custom Textual widget (`HabitCalendar`) that renders:

- Month/year header
- Day names (Su-Sa)
- Grid of cells (7 columns, ~5 rows)
- Color coding:
  - `■` (full green) — Complete
  - `□` (light gray) — Incomplete
  - `-` (medium gray) — Skipped
  - ` ` (white) — No data yet (future date)
- Clickable cells to toggle status

## API Endpoints

**In `gtd/api.py`:**

### Habits CRUD

```
GET /habits
  Returns: [{"page_id": "...", "name": "...", "active": true, ...}, ...]

POST /habits
  Body: {"name": "...", "frequency": "...", "description": "..."}
  Returns: {"page_id": "...", ...}

PATCH /habits/{habit_id}
  Body: {"name": "...", "active": true, "notes": "..."}
  Returns: updated habit

DELETE /habits/{habit_id}
  Returns: {"deleted": true}
```

### Completions

```
GET /habits/{habit_id}/calendar?months=12
  Returns: {
    "habit_id": "...",
    "data": {
      "2026-07-20": "Complete",
      "2026-07-19": "Incomplete",
      ...
    }
  }

POST /habits/{habit_id}/complete
  Body: {"date": "2026-07-20", "status": "Complete", "notes": "..."}
  Returns: {"page_id": "...", "status": "Complete", ...}

GET /habits/{habit_id}/completions?from=2026-01-01&to=2026-12-31
  Returns: [{"date": "...", "status": "...", ...}, ...]
```

## Config

**In `config.json`:**

```json
{
  "ENABLE_HABITS": true,
  "HABITS_TAB_POSITION": 8,
  "HABIT_CALENDAR_MONTHS": 12
}
```

**In schema.py:**

```python
HABITS_ENABLED = get_config_value('ENABLE_HABITS', True)
HABIT_CALENDAR_MONTHS = get_config_value('HABIT_CALENDAR_MONTHS', 12)
```

## Implementation Roadmap

### Phase 1: Infrastructure

- [ ] Add Notion database IDs to env/config
- [ ] Create `Habit` + `HabitCompletion` dataclasses
- [ ] Implement client functions in `gtd/notion/habits.py`
- [ ] Write unit tests

### Phase 2: API

- [ ] Add `/habits` endpoints to `gtd/api.py`
- [ ] Test with curl/Shortcuts

### Phase 3: TUI

- [ ] Build `HabitCalendar` widget
- [ ] Create `HabitsContent` tab
- [ ] Add to main `GTDApp` tabs
- [ ] Implement all actions (H/L, toggle, add, edit, delete)

### Phase 4: Polish

- [ ] Config option to toggle Habits tab
- [ ] Weekly habit frequency validation
- [ ] Color customization
- [ ] Statistics/streaks display

## Mobile/Shortcuts Workflow

```
1. User opens Shortcuts on iPhone
2. Calls: GET /habits
3. Shows habit picker menu
4. User selects habit
5. Shows calendar or quick toggle
6. User marks complete: POST /habits/{id}/complete
7. Response: updated status + streak info
```

## Example Queries

**Get all incomplete habits for today:**

```python
today = date.today().isoformat()
all_completions = get_completions_for_date(today)
incomplete = [c for c in all_completions if c.status != 'Complete']
```

**Get habit streak (consecutive complete days):**

```python
completions = get_completions_for_habit(habit_id, from_date, to_date)
# Work backwards from today counting consecutive "Complete" statuses
```

**Get completion percentage for month:**

```python
completions = get_completions_for_habit(habit_id, month_start, month_end)
total = len(completions)
completed = len([c for c in completions if c.status == 'Complete'])
percentage = (completed / total) * 100 if total > 0 else 0
```

## Potential Future Enhancements

- Streaks visualization (current, longest, lost streaks)
- Habit stacking (suggested order to do habits)
- Notifications/reminders (via API or push)
- Export completion data
- Habit sharing/comparison with others
- Weekly/monthly summaries on TUI
- Custom colors per habit
- Habit categories/tags
- Time tracking (minutes spent on habit)
