from datetime import datetime, timedelta
import json
from pathlib import Path
import subprocess
import sys

from dateutil import parser as dateparser
from pydantic import BaseModel, Field


OUTPUT_PATH = Path.home() / '.local' / 'bin' / 'project_manager'
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
ARCHIVE_PATH = OUTPUT_PATH / 'archive'
ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = OUTPUT_PATH / 'config.json'


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    with CONFIG_PATH.open('w') as f:
        json.dump(config, f, indent=2)


# --- Models ---


class Tactic(BaseModel):
    description: str
    reminder_cadence: str  # e.g. "daily", "weekly", "2x/week"
    updates: list[dict] = Field(default_factory=list)
    # Weekly execution: {"1": true, "3": true, "5": false, ...}
    weekly_scores: dict[str, int] = Field(
        default_factory=dict,
    )  # week -> 1-10 score


class Todo(BaseModel):
    description: str
    due_date: str | None = None  # ISO format, optional
    completed: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Goal(BaseModel):
    name: str
    description: str
    start_date: str  # ISO format
    end_date: str  # ISO format
    tactics: list[dict] = Field(default_factory=list)
    todos: list[dict] = Field(default_factory=list)

    @classmethod
    def new(cls, name: str, description: str) -> 'Goal':
        now = datetime.now()
        return cls(
            name=name,
            description=description,
            start_date=now.isoformat(),
            end_date=(now + timedelta(weeks=12)).isoformat(),
        )

    def get_tactics(self) -> list[Tactic]:
        return [Tactic(**t) for t in self.tactics]

    def get_todos(self) -> list[Todo]:
        return [Todo(**t) for t in self.todos]

    def add_tactic(self, tactic: Tactic) -> None:
        self.tactics.append(tactic.model_dump())

    def current_week(self) -> int:
        start = datetime.fromisoformat(self.start_date)
        elapsed = (datetime.now() - start).days // 7
        return min(max(elapsed + 1, 1), 13)  # 1-indexed, cap at 13

    def weeks_remaining(self) -> int:
        return max(0, 12 - self.current_week())

    def week_start_date(self, week_num: int) -> datetime:
        start = datetime.fromisoformat(self.start_date)
        return start + timedelta(weeks=week_num - 1)

    def date_range_display(self) -> str:
        start = datetime.fromisoformat(self.start_date)
        end = datetime.fromisoformat(self.end_date)
        return f'{start:%b %-d} -- {end:%b %-d, %Y}'

    def week_score(self, week_num: int) -> tuple[int, int]:
        """Returns (total_score, max_possible) for a given week. Each tactic scored 1-10."""
        total = 0
        max_possible = 0
        for t in self.get_tactics():
            key = str(week_num)
            if key in t.weekly_scores:
                max_possible += 10
                total += t.weekly_scores[key]
        return total, max_possible

    def overall_score(self) -> tuple[int, int]:
        """Returns (total_executed, total_possible) across all scored weeks."""
        executed = 0
        total = 0
        for week in range(1, self.current_week() + 1):
            e, t = self.week_score(week)
            executed += e
            total += t
        return executed, total

    def progress_bar(self) -> str:
        week = self.current_week()
        completed = max(0, week - 1)  # weeks fully completed
        filled = '█' * completed
        empty = '░' * (12 - completed)
        return f'[{filled}{empty}] Week {week}/12'


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


def fzf_on_a_list(
    items: list[str],
    multiple: bool = False,
    prompt: str = '',
) -> str | list[str] | None:
    """Pass in a list of strings and run fzf via subprocess on the list."""
    prompt = f'{prompt}: ' if prompt and not prompt.endswith(': ') else prompt
    if multiple:
        cmd = ['fzf', '-m', '--prompt', f'{prompt}Shift+Tab to unselect > ']
    else:
        cmd = ['fzf', '--prompt', prompt]
    result = subprocess.run(
        cmd,
        input='\n'.join(items),
        stdout=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode == 130:  # Ctrl+C
        sys.exit(0)
    if not multiple:
        return result.stdout.strip() or None
    return [item.strip() for item in result.stdout.split('\n') if item.strip()]


def select_tactic_index(
    goal: Goal, prompt: str = 'Select tactic',
) -> int | None:
    tactics = goal.get_tactics()
    if not tactics:
        print(f'No tactics for "{goal.name}" yet.')
        return None
    descriptions = [t.description for t in tactics]
    selection = fzf_on_a_list(descriptions, prompt=prompt)
    if selection is None:
        return None
    return descriptions.index(selection)


def pause() -> None:
    input('\nPress Enter to go back to menu...')


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


# --- Goal actions (all take a Goal, return updated Goal) ---


def view_goal(goal: Goal) -> Goal:
    """Compact view — fits on one screen."""
    week = goal.current_week()
    weeks_left = goal.weeks_remaining()
    print(f'\n{"─" * 55}')
    print(f'  {goal.name}')
    print(f'  {goal.date_range_display()}')
    print(
        f'  {goal.progress_bar()}  •  Week {week}  •  {weeks_left} week{"s" if weeks_left != 1 else ""} left',
    )
    print(f'  {goal.description}')

    # Overall score
    ex, tot = goal.overall_score()
    if tot > 0:
        pct = score_pct(ex, tot)
        indicator = (
            '🟢' if ex / tot >= 0.85 else '🟡' if ex / tot >= 0.65 else '🔴'
        )
        print(f'\n  {indicator} Overall execution: {pct} ({ex}/{tot})')

    # This week's score
    ex_w, tot_w = goal.week_score(week)
    if tot_w > 0:
        print(
            f'  Week {week} score: {score_pct(ex_w, tot_w)} ({ex_w}/{tot_w})',
        )

    # Tactics — one line each
    tactics = goal.get_tactics()
    if not tactics:
        print('\n  No tactics yet.')
    else:
        print(f'\n  Tactics ({len(tactics)}):')
        for i, t in enumerate(tactics, 1):
            wk_key = str(week)
            if wk_key in t.weekly_scores:
                mark = f'{t.weekly_scores[wk_key]}/10'
            else:
                mark = '—'
            updates = f'  [{len(t.updates)} logs]' if t.updates else ''
            print(
                f'  {i}. [{mark:>4}] {t.description}  ({t.reminder_cadence}){updates}',
            )

    # To-dos — open only, done as count
    todos = goal.get_todos()
    open_todos = [t for t in todos if not t.completed]
    done_count = sum(1 for t in todos if t.completed)
    if not todos:
        print('\n  No to-dos yet.')
    else:
        if open_todos:
            print(f'\n  To-dos — Open ({len(open_todos)}):')
            for t in open_todos:
                due = (
                    f'  (due {datetime.fromisoformat(t.due_date):%b %-d})'
                    if t.due_date
                    else ''
                )
                print(f'    ☐  {t.description}{due}')
        if done_count:
            print(f'\n  To-dos — Done: {done_count}')

    print(f'{"─" * 55}\n')
    return goal


def detailed_view(goal: Goal) -> Goal:
    """Full detail piped through less."""
    week = goal.current_week()
    weeks_left = goal.weeks_remaining()
    lines = []
    lines.append(f'{"─" * 55}')
    lines.append(f'  {goal.name}')
    lines.append(f'  {goal.date_range_display()}')
    lines.append(
        f'  {goal.progress_bar()}  •  Week {week}  •  {weeks_left} week{"s" if weeks_left != 1 else ""} left',
    )
    lines.append(f'  {goal.description}')

    # Overall score
    ex, tot = goal.overall_score()
    if tot > 0:
        pct = score_pct(ex, tot)
        indicator = (
            '🟢' if ex / tot >= 0.85 else '🟡' if ex / tot >= 0.65 else '🔴'
        )
        lines.append(f'\n  {indicator} Overall execution: {pct} ({ex}/{tot})')

    ex_w, tot_w = goal.week_score(week)
    if tot_w > 0:
        lines.append(
            f'  Week {week} score: {score_pct(ex_w, tot_w)} ({ex_w}/{tot_w})',
        )

    # Tactics — full detail with logs
    tactics = goal.get_tactics()
    if not tactics:
        lines.append('\n  No tactics yet.')
    else:
        lines.append(f'\n  Tactics ({len(tactics)}):')
        for i, t in enumerate(tactics, 1):
            wk_key = str(week)
            if wk_key in t.weekly_scores:
                mark = f'{t.weekly_scores[wk_key]}/10'
            else:
                mark = '—'
            lines.append(
                f'\n  {i}. [{mark:>4}] {t.description}  ({t.reminder_cadence})',
            )
            if t.updates:
                lines.append(f'     Updates ({len(t.updates)}):')
                for u in t.updates:
                    date = datetime.fromisoformat(u['date']).strftime('%b %-d')
                    lines.append(f'       {date}: {u["note"]}')

    # All to-dos
    todos = goal.get_todos()
    open_todos = [t for t in todos if not t.completed]
    done_todos = [t for t in todos if t.completed]
    if not todos:
        lines.append('\n  No to-dos yet.')
    else:
        if open_todos:
            lines.append(f'\n  To-dos — Open ({len(open_todos)}):')
            for t in open_todos:
                due = (
                    f'  (due {datetime.fromisoformat(t.due_date):%b %-d})'
                    if t.due_date
                    else ''
                )
                lines.append(f'    ☐  {t.description}{due}')
        if done_todos:
            lines.append(f'\n  To-dos — Done ({len(done_todos)}):')
            for t in done_todos:
                lines.append(f'    ✓  {t.description}')

    # Score history
    lines.append('\n  Score History:')
    for w in range(1, min(week, 12) + 1):
        e, t = goal.week_score(w)
        if t == 0:
            lines.append(f'  Week {w:>2}: (not scored)')
        else:
            pct_val = e / t
            indicator = (
                '🟢' if pct_val >= 0.85 else '🟡' if pct_val >= 0.65 else '🔴'
            )
            current = ' ◀' if w == week else ''
            lines.append(
                f'  Week {w:>2}: {indicator} {score_pct(e, t):>4} ({e}/{t}){current}',
            )

    lines.append(f'{"─" * 55}')

    # Pipe through less
    output = '\n'.join(lines)
    subprocess.run(['less', '-R'], input=output, text=True, check=False)
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
        prompt_input('Reminder cadence (e.g. daily, weekly, 2x/week): ')
        or 'weekly'
    )
    goal.add_tactic(Tactic(description=description, reminder_cadence=cadence))
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
    goal.tactics[idx]['updates'].append(
        {
            'date': datetime.now().isoformat(),
            'note': note,
        },
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
    print(f'\n✓ Removed: {removed["description"]}')
    return goal


def weekly_scorecard(goal: Goal) -> Goal:
    week = goal.current_week()
    if week > 12:
        print('This 12-week year is complete!')
        return goal

    tactics = goal.get_tactics()
    if not tactics:
        print('No tactics to score. Add some first.')
        return goal

    print(f'\n  ── Week {week} Scorecard ──\n')
    for i, t in enumerate(tactics):
        wk_key = str(week)
        current = goal.tactics[i].get('weekly_scores', {}).get(wk_key)
        status = f' (current: {current}/10)' if current is not None else ''

        answer = prompt_input(f'  {t.description} — score 1-10{status}: ')
        if answer and answer.isdigit():
            score = max(1, min(10, int(answer)))
            goal.tactics[i].setdefault('weekly_scores', {})[wk_key] = score

    save_goal(goal)

    sc, mx = goal.week_score(week)
    pct = score_pct(sc, mx)
    threshold = (
        '🟢 On track!'
        if mx > 0 and sc / mx >= 0.85
        else '🔴 Below 85% threshold'
        if mx > 0
        else ''
    )
    print(f'\n  Week {week} score: {pct} ({sc}/{mx})  {threshold}')
    return goal


def view_score_history(goal: Goal) -> Goal:
    week = goal.current_week()
    print(f'\n  ── Score History: {goal.name} ──\n')
    total_ex = 0
    total_tot = 0
    for w in range(1, min(week, 12) + 1):
        ex, tot = goal.week_score(w)
        total_ex += ex
        total_tot += tot
        if tot == 0:
            bar = '  (not scored)'
        else:
            pct = ex / tot
            filled = round(pct * 20)
            bar_str = '█' * filled + '░' * (20 - filled)
            indicator = '🟢' if pct >= 0.85 else '🟡' if pct >= 0.65 else '🔴'
            bar = (
                f'{indicator} [{bar_str}] {score_pct(ex, tot):>4} ({ex}/{tot})'
            )
        current = ' ◀' if w == week else ''
        print(f'  Week {w:>2}: {bar}{current}')

    if total_tot > 0:
        print(
            f'\n  Overall: {score_pct(total_ex, total_tot)} ({total_ex}/{total_tot})',
        )
    print()
    return goal


def add_todo(goal: Goal) -> Goal:
    description = prompt_input('To-do description: ')
    if not description:
        print('Description required.')
        return goal
    due = (
        prompt_input('Due date (e.g. Aug 29, tomorrow, blank to skip): ')
        or None
    )
    due_iso = None
    if due:
        try:
            due_iso = dateparser.parse(due, fuzzy=True).isoformat()
        except Exception:
            print(f'Could not parse "{due}", saving without due date.')
    goal.todos.append(
        Todo(description=description, due_date=due_iso).model_dump(),
    )
    save_goal(goal)
    print('\n✓ To-do added')
    return goal


def complete_todo(goal: Goal) -> Goal:
    open_todos = [t for t in goal.get_todos() if not t.completed]
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
        if t['description'] == selection and not t['completed']:
            t['completed'] = True
            break
    save_goal(goal)
    print(f'\n✓ "{selection}" marked complete')
    return goal


def remove_todo(goal: Goal) -> Goal:
    todos = goal.get_todos()
    if not todos:
        print('No to-dos.')
        return goal
    selection = fzf_on_a_list(
        [t.description for t in todos], prompt='Remove to-do',
    )
    if not selection:
        return goal
    goal.todos = [t for t in goal.todos if t['description'] != selection]
    save_goal(goal)
    print(f'\n✓ Removed: {selection}')
    return goal


def edit_tactic(goal: Goal) -> Goal:
    idx = select_tactic_index(goal, prompt='Select tactic to edit')
    if idx is None:
        return goal
    t = goal.tactics[idx]
    print(f'  Current description: {t["description"]}')
    desc = prompt_input('New description (Enter to keep): ')
    print(f'  Current cadence: {t["reminder_cadence"]}')
    cadence = prompt_input('New cadence (Enter to keep): ')
    if desc:
        t['description'] = desc
    if cadence:
        t['reminder_cadence'] = cadence
    save_goal(goal)
    print('\n✓ Tactic updated')
    return goal


def edit_todo(goal: Goal) -> Goal:
    todos = goal.get_todos()
    if not todos:
        print('No to-dos yet.')
        return goal
    selection = fzf_on_a_list(
        [t.description for t in todos],
        prompt='Select to-do to edit',
    )
    if not selection:
        return goal
    for t in goal.todos:
        if t['description'] == selection:
            print(f'  Current description: {t["description"]}')
            desc = prompt_input('New description (Enter to keep): ')
            current_due = t.get('due_date')
            due_display = (
                datetime.fromisoformat(current_due).strftime('%b %-d')
                if current_due
                else 'none'
            )
            print(f'  Current due date: {due_display}')
            due = prompt_input(
                'New due date (Enter to keep, "clear" to remove): ',
            )
            if t['completed']:
                reopen = prompt_input('Re-open this to-do? (y/N): ')
                if reopen and reopen.lower().startswith('y'):
                    t['completed'] = False
            if desc:
                t['description'] = desc
            if due and due.lower() == 'clear':
                t['due_date'] = None
            elif due:
                try:
                    t['due_date'] = dateparser.parse(
                        due, fuzzy=True,
                    ).isoformat()
                except Exception:
                    print(f'Could not parse "{due}", due date unchanged.')
            break
    save_goal(goal)
    print('\n✓ To-do updated')
    return goal


def edit_settings() -> None:
    config = load_config()
    print(f'  Current reminder dir: {config.get("reminder_dir", "not set")}')
    reminder_dir = prompt_input(
        'Reminder directory (Enter to keep, "clear" to remove): ',
    )
    if reminder_dir and reminder_dir.lower() == 'clear':
        config.pop('reminder_dir', None)
    elif reminder_dir:
        config['reminder_dir'] = str(Path(reminder_dir).expanduser().resolve())
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


def goal_menu(goal: Goal) -> None:
    labels = [
        f'{i + 1:>2}. {cat:<10}{action}'
        for i, (cat, action) in enumerate(GOAL_MENU_ITEMS)
    ]
    label_to_action = {
        label.strip(): action
        for label, (_, action) in zip(labels, GOAL_MENU_ITEMS, strict=False)
    }
    while True:
        selection = fzf_on_a_list(
            labels,
            prompt=f'{goal.name} (Wk {goal.current_week()}/12)',
        )
        if not selection:
            break
        action = label_to_action.get(selection)
        if not action:
            continue
        match action:
            case 'View goal':
                goal = view_goal(goal)
            case 'Detailed view':
                goal = detailed_view(goal)
            case 'Edit goal':
                goal = edit_goal(goal)
            case 'Weekly scorecard':
                goal = weekly_scorecard(goal)
            case 'Score history':
                goal = view_score_history(goal)
            case 'Add tactic':
                goal = add_tactic(goal)
            case 'Log update on tactic':
                goal = log_update(goal)
            case 'Add to-do':
                goal = add_todo(goal)
            case 'Edit tactic':
                goal = edit_tactic(goal)
            case 'Remove tactic':
                goal = remove_tactic(goal)
            case 'Edit to-do':
                goal = edit_todo(goal)
            case 'Remove to-do':
                goal = remove_todo(goal)
            case 'Complete to-do':
                goal = complete_todo(goal)
            case 'Other goals':
                break
            case 'Settings':
                edit_settings()
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
        f'\n✓ Goal "{goal.name}" created — {goal.date_range_display()} ({goal.weeks_remaining()} weeks)',
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
    confirm = prompt_input(f'Remove "{name}"? Type "yes" to confirm: ')
    if not confirm or confirm.lower() != 'yes':
        print('Cancelled.')
        return
    src = OUTPUT_PATH / f'{name}.json'
    goal = load_goal(name)
    has_data = goal.tactics or goal.todos
    if has_data:
        # Soft delete — move to archive
        dest = ARCHIVE_PATH / f'{name}.json'
        src.rename(dest)
        print(f'\n✓ "{name}" archived (data retained in {ARCHIVE_PATH})')
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


def main() -> None:
    first_run = True
    while True:
        names = get_stored_goal_names()

        if len(names) == 0:
            print('No goals yet.')
            create_new_goal()
            first_run = False
            continue

        # Auto-load only on first run with a single goal
        if first_run and len(names) == 1:
            first_run = False
            goal_menu(load_goal(names[0]))
            continue

        first_run = False
        action = fzf_on_a_list(TOP_MENU, prompt='12 Week Year')
        if not action:
            break
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


if __name__ == '__main__':
    main()
