from datetime import datetime, timedelta
import json
from pathlib import Path
import subprocess
import sys
from typing import Literal, overload

from dateutil import parser as dateparser
from pydantic import BaseModel, Field


OUTPUT_PATH = Path.home() / '.local' / 'bin' / 'project_manager'
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
ARCHIVE_PATH = OUTPUT_PATH / 'archive'
ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = OUTPUT_PATH / 'config.json'

# 12 Week Year constants
TOTAL_WEEKS = 12
SCORE_GREEN_THRESHOLD = 0.85
SCORE_YELLOW_THRESHOLD = 0.65
FZF_CTRL_C_CODE = 130


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    with CONFIG_PATH.open('w') as f:
        json.dump(config, f, indent=2)


# --- Models ---


class Update(BaseModel):
    date: str  # ISO format
    note: str


class Tactic(BaseModel):
    description: str
    reminder_cadence: str  # e.g. "daily", "weekly", "2x/week"
    updates: list[Update] = Field(default_factory=list)
    weekly_scores: dict[str, int] = Field(
        default_factory=dict,
    )  # week number (str) -> 1-10 score


class Todo(BaseModel):
    description: str
    due_date: str | None = None
    completed: bool = False
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
    )


class Goal(BaseModel):
    name: str
    description: str
    start_date: str
    end_date: str
    tactics: list[Tactic] = Field(default_factory=list)
    todos: list[Todo] = Field(default_factory=list)

    @classmethod
    def new(cls, name: str, description: str) -> 'Goal':
        now = datetime.now()
        return cls(
            name=name,
            description=description,
            start_date=now.isoformat(),
            end_date=(now + timedelta(weeks=12)).isoformat(),
        )

    def current_week(self) -> int:
        start = datetime.fromisoformat(self.start_date)
        elapsed = (datetime.now() - start).days // 7
        return min(max(elapsed + 1, 1), 13)

    def weeks_remaining(self) -> int:
        return max(0, TOTAL_WEEKS - self.current_week())

    def week_start_date(self, week_num: int) -> datetime:
        start = datetime.fromisoformat(self.start_date)
        return start + timedelta(weeks=week_num - 1)

    def date_range_display(self) -> str:
        start = datetime.fromisoformat(self.start_date)
        end = datetime.fromisoformat(self.end_date)
        return f'{start:%b %-d} | {end:%b %-d, %Y}'

    def week_score(self, week_num: int) -> tuple[int, int]:
        """Returns (total_score, max_possible) for a given week."""
        total = 0
        max_possible = 0
        key = str(week_num)
        for t in self.tactics:
            if key in t.weekly_scores:
                max_possible += 10
                total += t.weekly_scores[key]
        return total, max_possible

    def overall_score(self) -> tuple[int, int]:
        """Returns (total_score, total_possible) across all scored weeks."""
        executed = 0
        total = 0
        for week in range(1, self.current_week() + 1):
            e, t = self.week_score(week)
            executed += e
            total += t
        return executed, total

    def progress_bar(self) -> str:
        week = self.current_week()
        completed = max(0, week - 1)
        filled = '█' * completed
        empty = '░' * (TOTAL_WEEKS - completed)
        return f'[{filled}{empty}] Week {week}/{TOTAL_WEEKS}'


# --- Storage ---


def save_goal(goal: Goal) -> None:
    path = OUTPUT_PATH / f'{goal.name}.json'
    with path.open('w') as f:
        json.dump(goal.model_dump(), f, indent=2)


def load_goal(name: str) -> Goal:
    path = OUTPUT_PATH / f'{name}.json'
    with path.open() as f:
        data = json.load(f)
    return Goal.model_validate(data)


def get_stored_goal_names() -> list[str]:
    return [
        f.stem
        for f in sorted(OUTPUT_PATH.glob('*.json'))
        if f.name != 'config.json'
    ]


# --- fzf helpers ---


@overload
def fzf_on_a_list(
    items: list[str],
    *,
    multiple: Literal[True],
    prompt: str = '',
) -> list[str] | None: ...


@overload
def fzf_on_a_list(
    items: list[str],
    *,
    multiple: Literal[False] = False,
    prompt: str = '',
) -> str | None: ...


def fzf_on_a_list(
    items: list[str],
    *,
    multiple: bool = False,
    prompt: str = '',
) -> str | list[str] | None:
    """Run fzf on a list of strings."""
    prompt = f'{prompt}: ' if prompt and not prompt.endswith(': ') else prompt
    if multiple:
        cmd = [
            'fzf',
            '-m',
            '--prompt',
            f'{prompt}Shift+Tab to unselect > ',
        ]
    else:
        cmd = ['/usr/bin/fzf', '--prompt', prompt]
    result = subprocess.run(  # noqa: S603
        cmd,
        input='\n'.join(items),
        stdout=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode == FZF_CTRL_C_CODE:
        sys.exit(0)
    if not multiple:
        return result.stdout.strip() or None
    return [item.strip() for item in result.stdout.split('\n') if item.strip()]


def select_tactic_index(
    goal: Goal,
    prompt: str = 'Select tactic',
) -> int | None:
    if not goal.tactics:
        print(f'No tactics for "{goal.name}" yet.')
        return None
    descriptions = [t.description for t in goal.tactics]
    selection = fzf_on_a_list(descriptions, prompt=prompt)
    if selection is None:
        return None
    return descriptions.index(selection)


def pause() -> None:
    input('\nPress Enter to go back to menu...')


def score_indicator(pct: float) -> str:
    """Return emoji indicator based on score percentage."""
    if pct >= SCORE_GREEN_THRESHOLD:
        return '🟢'
    if pct >= SCORE_YELLOW_THRESHOLD:
        return '🟡'
    return '🔴'


def prompt_input(label: str) -> str | None:
    """Like input() but Ctrl+C returns None instead of raising."""
    try:
        return input(label).strip()
    except KeyboardInterrupt:
        print()
        return None


def score_pct(executed: int, total: int) -> str:
    if total == 0:
        return '—'
    return f'{executed / total * 100:.0f}%'


# --- Goal actions ---


def _tactics_compact_lines(goal: Goal) -> list[str]:
    """Build compact tactics section (one line each)."""
    week = goal.current_week()
    if not goal.tactics:
        return ['\n  No tactics yet.']
    lines = [f'\n  Tactics ({len(goal.tactics)}):']
    for i, t in enumerate(goal.tactics, 1):
        wk_key = str(week)
        mark = (
            f'{t.weekly_scores[wk_key]}/10'
            if wk_key in t.weekly_scores
            else '—'
        )
        logs = f'  [{len(t.updates)} logs]' if t.updates else ''
        lines.append(
            f'  {i}. [{mark:>4}] '
            f'{t.description}  ({t.reminder_cadence}){logs}',
        )
    return lines


def view_goal(goal: Goal) -> Goal:
    """Compact view -- fits on one screen."""
    lines = _goal_header_lines(goal)
    lines.extend(_tactics_compact_lines(goal))
    lines.extend(_todos_lines(goal, compact=True))
    lines.append(f'{"─" * 55}\n')
    print('\n' + '\n'.join(lines))
    return goal


def _goal_header_lines(goal: Goal) -> list[str]:
    """Build the header section for goal display."""
    week = goal.current_week()
    weeks_left = goal.weeks_remaining()
    lines = [
        f'{"─" * 55}',
        f'  {goal.name}',
        f'  {goal.date_range_display()}',
        (
            f'  {goal.progress_bar()}  •  Week {week}'
            f'  •  {weeks_left} week{"s" if weeks_left != 1 else ""} left'
        ),
        f'  {goal.description}',
    ]
    ex, tot = goal.overall_score()
    if tot > 0:
        pct = score_pct(ex, tot)
        indicator = score_indicator(ex / tot)
        lines.append(
            f'\n  {indicator} Overall execution: {pct} ({ex}/{tot})',
        )
    ex_w, tot_w = goal.week_score(week)
    if tot_w > 0:
        lines.append(
            f'  Week {week} score: {score_pct(ex_w, tot_w)} ({ex_w}/{tot_w})',
        )
    return lines


def _tactics_detail_lines(goal: Goal) -> list[str]:
    """Build detailed tactics section with all logs."""
    week = goal.current_week()
    if not goal.tactics:
        return ['\n  No tactics yet.']
    lines = [f'\n  Tactics ({len(goal.tactics)}):']
    for i, t in enumerate(goal.tactics, 1):
        wk_key = str(week)
        mark = (
            f'{t.weekly_scores[wk_key]}/10'
            if wk_key in t.weekly_scores
            else '—'
        )
        lines.append(
            f'\n  {i}. [{mark:>4}] {t.description}  ({t.reminder_cadence})',
        )
        if t.updates:
            lines.append(f'     Updates ({len(t.updates)}):')
            for u in t.updates:
                date = datetime.fromisoformat(
                    u.date,
                ).strftime('%b %-d')
                lines.append(f'       {date}: {u.note}')
    return lines


def _todos_lines(goal: Goal, *, compact: bool = False) -> list[str]:
    """Build to-do section lines."""
    open_todos = [t for t in goal.todos if not t.completed]
    done_todos = [t for t in goal.todos if t.completed]
    if not goal.todos:
        return ['\n  No to-dos yet.']
    lines = []
    if open_todos:
        lines.append(f'\n  To-dos | Open ({len(open_todos)}):')
        for t in open_todos:
            due = (
                f'  (due {datetime.fromisoformat(t.due_date):%b %-d})'
                if t.due_date
                else ''
            )
            lines.append(f'    ☐  {t.description}{due}')
    if done_todos:
        if compact:
            lines.append(f'\n  To-dos | Done: {len(done_todos)}')
        else:
            lines.append(
                f'\n  To-dos | Done ({len(done_todos)}):',
            )
            for t in done_todos:
                lines.append(f'    ✓  {t.description}')
    return lines


def _score_history_lines(goal: Goal) -> list[str]:
    """Build score history section."""
    week = goal.current_week()
    lines = ['\n  Score History:']
    for w in range(1, min(week, TOTAL_WEEKS) + 1):
        e, t = goal.week_score(w)
        if t == 0:
            lines.append(f'  Week {w:>2}: (not scored)')
        else:
            pct_val = e / t
            indicator = score_indicator(pct_val)
            current = ' ◀' if w == week else ''
            lines.append(
                f'  Week {w:>2}: {indicator} '
                f'{score_pct(e, t):>4} ({e}/{t}){current}',
            )
    return lines


def detailed_view(goal: Goal) -> Goal:
    """Full detail piped through less."""
    lines = _goal_header_lines(goal)
    lines.extend(_tactics_detail_lines(goal))
    lines.extend(_todos_lines(goal))
    lines.extend(_score_history_lines(goal))
    lines.append(f'{"─" * 55}')

    output = '\n'.join(lines)
    subprocess.run(
        ['/usr/bin/less', '-R'],
        input=output,
        text=True,
        check=False,
    )
    return goal


def edit_goal(goal: Goal) -> Goal:
    print(f'  Current name: {goal.name}')
    name = prompt_input('New name (Enter to keep): ')
    print(f'  Current description: {goal.description}')
    desc = prompt_input('New description (Enter to keep): ')
    if name:
        old_path = OUTPUT_PATH / f'{goal.name}.json'
        goal.name = name
        old_path.unlink(missing_ok=True)
    if desc:
        goal.description = desc
    save_goal(goal)
    print('\n✓ Goal updated')
    return goal


def add_tactic(goal: Goal) -> Goal:
    description = prompt_input('Tactic description: ')
    if not description:
        print('Description required.')
        return goal
    cadence = (
        prompt_input(
            'Reminder cadence (e.g. daily, weekly, 2x/week): ',
        )
        or 'weekly'
    )
    goal.tactics.append(
        Tactic(description=description, reminder_cadence=cadence),
    )
    save_goal(goal)
    print('\n✓ Tactic added')
    return goal


def log_update(goal: Goal) -> Goal:
    idx = select_tactic_index(goal, prompt='Select tactic to update')
    if idx is None:
        return goal
    note = prompt_input('Update note: ')
    if not note:
        print('Note required.')
        return goal
    goal.tactics[idx].updates.append(
        Update(date=datetime.now().isoformat(), note=note),
    )
    save_goal(goal)
    print('\n✓ Update logged')
    return goal


def remove_tactic(goal: Goal) -> Goal:
    idx = select_tactic_index(goal, prompt='Select tactic to remove')
    if idx is None:
        return goal
    removed = goal.tactics.pop(idx)
    save_goal(goal)
    print(f'\n✓ Removed: {removed.description}')
    return goal


def weekly_scorecard(goal: Goal) -> Goal:
    week = goal.current_week()
    if week > TOTAL_WEEKS:
        print('This 12-week year is complete!')
        return goal

    if not goal.tactics:
        print('No tactics to score. Add some first.')
        return goal

    # Let user pick which week to score
    weeks = [f'Week {w}' for w in range(1, min(week, TOTAL_WEEKS) + 1)]
    if len(weeks) > 1:
        week_choice = fzf_on_a_list(
            weeks,
            prompt='Score which week',
        )
        if not week_choice:
            return goal
        score_week = int(week_choice.split()[-1])
    else:
        score_week = week

    wk_key = str(score_week)
    max_desc_len = max(len(t.description) for t in goal.tactics)
    print(f'\n  ── Week {score_week} Scorecard ──\n')
    for tactic in goal.tactics:
        current = tactic.weekly_scores.get(wk_key)
        status = f' (current: {current}/10)' if current is not None else ''
        padded = tactic.description.ljust(max_desc_len)
        answer = prompt_input(
            f'  {padded}  | score 1-10{status}: ',
        )
        if answer and answer.isdigit():
            score = max(1, min(10, int(answer)))
            tactic.weekly_scores[wk_key] = score

    save_goal(goal)

    sc, mx = goal.week_score(score_week)
    pct = score_pct(sc, mx)
    threshold = (
        '🟢 On track!'
        if mx > 0 and sc / mx >= SCORE_GREEN_THRESHOLD
        else '🔴 Below 85% threshold'
        if mx > 0
        else ''
    )
    print(f'\n  Week {score_week} score: {pct} ({sc}/{mx})  {threshold}')
    return goal


def view_score_history(goal: Goal) -> Goal:
    week = goal.current_week()
    print(f'\n  ── Score History: {goal.name} ──\n')
    total_ex = 0
    total_tot = 0
    for w in range(1, min(week, TOTAL_WEEKS) + 1):
        ex, tot = goal.week_score(w)
        total_ex += ex
        total_tot += tot
        if tot == 0:
            bar = '  (not scored)'
        else:
            pct = ex / tot
            filled = round(pct * 20)
            bar_str = '█' * filled + '░' * (20 - filled)
            indicator = score_indicator(pct)
            bar = (
                f'{indicator} [{bar_str}] {score_pct(ex, tot):>4} ({ex}/{tot})'
            )
        current = ' ◀' if w == week else ''
        print(f'  Week {w:>2}: {bar}{current}')

    if total_tot > 0:
        print(
            f'\n  Overall: '
            f'{score_pct(total_ex, total_tot)} '
            f'({total_ex}/{total_tot})',
        )
    print()
    return goal


def add_todo(goal: Goal) -> Goal:
    description = prompt_input('To-do description: ')
    if not description:
        print('Description required.')
        return goal
    due = (
        prompt_input(
            'Due date (e.g. Aug 29, tomorrow, blank to skip): ',
        )
        or None
    )
    due_iso = None
    if due:
        try:
            due_iso = dateparser.parse(due, fuzzy=True).isoformat()
        except Exception:
            print(
                f'Could not parse "{due}", saving without due date.',
            )
    goal.todos.append(Todo(description=description, due_date=due_iso))
    save_goal(goal)
    print('\n✓ To-do added')
    return goal


def complete_todo(goal: Goal) -> Goal:
    open_todos = [t for t in goal.todos if not t.completed]
    if not open_todos:
        print('No open to-dos.')
        return goal
    selection = fzf_on_a_list(
        [t.description for t in open_todos],
        prompt='Mark complete',
    )
    if not selection:
        return goal
    for t in goal.todos:
        if t.description == selection and not t.completed:
            t.completed = True
            break
    save_goal(goal)
    print(f'\n✓ "{selection}" marked complete')
    return goal


def remove_todo(goal: Goal) -> Goal:
    if not goal.todos:
        print('No to-dos.')
        return goal
    selection = fzf_on_a_list(
        [t.description for t in goal.todos],
        prompt='Remove to-do',
    )
    if not selection:
        return goal
    goal.todos = [t for t in goal.todos if t.description != selection]
    save_goal(goal)
    print(f'\n✓ Removed: {selection}')
    return goal


def edit_tactic(goal: Goal) -> Goal:
    idx = select_tactic_index(goal, prompt='Select tactic to edit')
    if idx is None:
        return goal
    tactic = goal.tactics[idx]
    print(f'  Current description: {tactic.description}')
    desc = prompt_input('New description (Enter to keep): ')
    print(f'  Current cadence: {tactic.reminder_cadence}')
    cadence = prompt_input('New cadence (Enter to keep): ')
    if desc:
        tactic.description = desc
    if cadence:
        tactic.reminder_cadence = cadence
    save_goal(goal)
    print('\n✓ Tactic updated')
    return goal


def _apply_todo_edits(t: Todo) -> None:
    """Prompt for and apply edits to a single to-do."""
    print(f'  Current description: {t.description}')
    desc = prompt_input('New description (Enter to keep): ')
    due_display = (
        datetime.fromisoformat(t.due_date).strftime('%b %-d')
        if t.due_date
        else 'none'
    )
    print(f'  Current due date: {due_display}')
    due = prompt_input(
        'New due date (Enter to keep, "clear" to remove): ',
    )
    if t.completed:
        reopen = prompt_input('Re-open this to-do? (y/N): ')
        if reopen and reopen.lower().startswith('y'):
            t.completed = False
    if desc:
        t.description = desc
    if due and due.lower() == 'clear':
        t.due_date = None
    elif due:
        try:
            t.due_date = dateparser.parse(
                due,
                fuzzy=True,
            ).isoformat()
        except Exception:
            print(f'Could not parse "{due}", due date unchanged.')


def edit_todo(goal: Goal) -> Goal:
    if not goal.todos:
        print('No to-dos yet.')
        return goal
    selection = fzf_on_a_list(
        [t.description for t in goal.todos],
        prompt='Select to-do to edit',
    )
    if not selection:
        return goal
    for t in goal.todos:
        if t.description == selection:
            _apply_todo_edits(t)
            break
    save_goal(goal)
    print('\n✓ To-do updated')
    return goal


def edit_settings() -> None:
    config = load_config()
    print(
        f'  Current reminder dir: {config.get("reminder_dir", "not set")}',
    )
    reminder_dir = prompt_input(
        'Reminder directory (Enter to keep, "clear" to remove): ',
    )
    if reminder_dir and reminder_dir.lower() == 'clear':
        config.pop('reminder_dir', None)
    elif reminder_dir:
        config['reminder_dir'] = str(
            Path(reminder_dir).expanduser().resolve(),
        )
    save_config(config)
    print('\n✓ Settings updated')


# --- Menus ---

GOAL_MENU_ITEMS = [
    ('Goal', 'View goal'),
    ('Goal', 'Detailed view'),
    ('Goal', 'Edit goal'),
    ('Score', 'Weekly scorecard'),
    ('Score', 'Score history'),
    ('Tactics', 'Add tactic'),
    ('Tactics', 'Edit tactic'),
    ('Tactics', 'Remove tactic'),
    ('Tactics', 'Log update on tactic'),
    ('To-do', 'Add to-do'),
    ('To-do', 'Edit to-do'),
    ('To-do', 'Remove to-do'),
    ('To-do', 'Complete to-do'),
    ('', 'Other goals'),
    ('', 'Settings'),
]

TOP_MENU = [
    'Select goal',
    'New goal',
    'Remove goal',
    'View archived goals',
    'Restore archived goal',
]


GOAL_ACTION_MAP = {
    'View goal': view_goal,
    'Detailed view': detailed_view,
    'Edit goal': edit_goal,
    'Weekly scorecard': weekly_scorecard,
    'Score history': view_score_history,
    'Add tactic': add_tactic,
    'Log update on tactic': log_update,
    'Add to-do': add_todo,
    'Edit tactic': edit_tactic,
    'Remove tactic': remove_tactic,
    'Edit to-do': edit_todo,
    'Remove to-do': remove_todo,
    'Complete to-do': complete_todo,
}


def goal_menu(goal: Goal) -> None:
    labels = [
        f'{i + 1:>2}. {cat:<10}{action}'
        for i, (cat, action) in enumerate(GOAL_MENU_ITEMS)
    ]
    label_to_action = {
        label.strip(): action
        for label, (_, action) in zip(
            labels,
            GOAL_MENU_ITEMS,
            strict=True,
        )
    }
    while True:
        selection = fzf_on_a_list(
            labels,
            prompt=(f'{goal.name} (Wk {goal.current_week()}/{TOTAL_WEEKS})'),
        )
        if not selection:
            break
        action = label_to_action.get(selection)
        if not action:
            continue
        if action == 'Other goals':
            break
        if action == 'Settings':
            edit_settings()
        elif action in GOAL_ACTION_MAP:
            goal = GOAL_ACTION_MAP[action](goal)
        pause()


def create_new_goal() -> None:
    name = prompt_input('Goal name: ')
    if not name:
        print('Name required.')
        return
    description = prompt_input('Describe this goal: ') or ''
    goal = Goal.new(name, description)
    save_goal(goal)
    print(
        f'\n✓ Goal "{goal.name}" created | '
        f'{goal.date_range_display()} '
        f'({goal.weeks_remaining()} weeks)',
    )
    pause()
    goal_menu(goal)


def remove_goal() -> None:
    names = get_stored_goal_names()
    if not names:
        print('No goals to remove.')
        return
    name = fzf_on_a_list(names, prompt='Remove goal')
    if not name:
        return
    confirm = prompt_input(
        f'Remove "{name}"? Type "yes" to confirm: ',
    )
    if not confirm or confirm.lower() != 'yes':
        print('Cancelled.')
        return
    src = OUTPUT_PATH / f'{name}.json'
    goal = load_goal(name)
    has_data = goal.tactics or goal.todos
    if has_data:
        dest = ARCHIVE_PATH / f'{name}.json'
        src.rename(dest)
        print(
            f'\n✓ "{name}" archived (data retained in {ARCHIVE_PATH})',
        )
    else:
        src.unlink()
        print(f'\n✓ "{name}" removed')


def get_archived_goal_names() -> list[str]:
    return [f.stem for f in sorted(ARCHIVE_PATH.glob('*.json'))]


def view_archived_goals() -> None:
    names = get_archived_goal_names()
    if not names:
        print('No archived goals.')
        return
    name = fzf_on_a_list(names, prompt='View archived goal')
    if not name:
        return
    path = ARCHIVE_PATH / f'{name}.json'
    with path.open() as f:
        data = json.load(f)
    goal = Goal.model_validate(data)
    view_goal(goal)


def restore_archived_goal() -> None:
    names = get_archived_goal_names()
    if not names:
        print('No archived goals to restore.')
        return
    name = fzf_on_a_list(names, prompt='Restore goal')
    if not name:
        return
    src = ARCHIVE_PATH / f'{name}.json'
    dest = OUTPUT_PATH / f'{name}.json'
    src.rename(dest)
    print(f'\n✓ "{name}" restored')


def _handle_top_menu_action(action: str, names: list[str]) -> None:
    """Dispatch a top-level menu action."""
    match action:
        case 'New goal':
            create_new_goal()
        case 'Select goal':
            name = fzf_on_a_list(names, prompt='Select goal')
            if name:
                goal_menu(load_goal(name))
        case 'Remove goal':
            remove_goal()
        case 'View archived goals':
            view_archived_goals()
            pause()
        case 'Restore archived goal':
            restore_archived_goal()


def main() -> None:
    first_run = True
    while True:
        names = get_stored_goal_names()

        if len(names) == 0:
            print('No goals yet.')
            create_new_goal()
            first_run = False
            continue

        if first_run and len(names) == 1:
            first_run = False
            goal_menu(load_goal(names[0]))
            continue

        first_run = False
        action = fzf_on_a_list(TOP_MENU, prompt='12 Week Year')
        if not action:
            break
        _handle_top_menu_action(action, names)


if __name__ == '__main__':
    main()
