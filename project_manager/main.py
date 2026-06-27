from datetime import datetime, timedelta
import json
from pathlib import Path
import subprocess
import sys

from dateutil import parser as dateparser
from pydantic import BaseModel, Field


OUTPUT_PATH = Path.home() / '.local' / 'bin' / 'project_manager'
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = OUTPUT_PATH / 'config.json'


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    with CONFIG_PATH.open('w') as f:
        json.dump(config, f, indent=2)


class Tactic(BaseModel):
    description: str
    reminder_cadence: str  # e.g. "daily", "weekly", "2x/week"
    updates: list[dict] = Field(default_factory=list)


class Todo(BaseModel):
    description: str
    due_date: str | None = None  # ISO format, optional
    completed: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Goal(BaseModel):
    name: str
    description: str
    start_date: str  # ISO format
    end_date: str    # ISO format
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

    def weeks_remaining(self) -> int:
        end = datetime.fromisoformat(self.end_date)
        return max(0, (end - datetime.now()).days // 7)

    def date_range_display(self) -> str:
        start = datetime.fromisoformat(self.start_date)
        end = datetime.fromisoformat(self.end_date)
        return f'{start:%b %-d} – {end:%b %-d, %Y}'


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
    return [f.stem for f in sorted(OUTPUT_PATH.glob('*.json'))]


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


def select_tactic_index(goal: Goal, prompt: str = 'Select tactic') -> int | None:
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
    input('\nPress Enter to continue...')


def prompt_input(label: str) -> str | None:
    """Like input() but Ctrl+C returns None instead of raising."""
    try:
        return input(label).strip()
    except KeyboardInterrupt:
        print()
        return None


# --- Goal actions (all take a Goal, return updated Goal) ---

def view_goal(goal: Goal) -> Goal:
    weeks = goal.weeks_remaining()
    print(f'\n{"─" * 50}')
    print(f'  {goal.name}')
    print(f'  {goal.date_range_display()}  ({weeks} week{"s" if weeks != 1 else ""} remaining)')
    print(f'  {goal.description}')

    tactics = goal.get_tactics()
    if not tactics:
        print('\n  No tactics yet.')
    else:
        print(f'\n  Tactics ({len(tactics)}):')
        for i, t in enumerate(tactics, 1):
            n = len(t.updates)
            print(f'\n  {i}. {t.description}')
            print(f'     Cadence: {t.reminder_cadence}')
            print(f'     Updates: {n}')
            if t.updates:
                for u in t.updates[-3:]:
                    date = datetime.fromisoformat(u["date"]).strftime("%b %-d")
                    print(f'       {date}: {u["note"]}')

    todos = goal.get_todos()
    open_todos = [t for t in todos if not t.completed]
    done_todos = [t for t in todos if t.completed]
    if not todos:
        print('\n  No to-dos yet.')
    else:
        if open_todos:
            print(f'\n  To-dos — Open ({len(open_todos)}):')
            for t in open_todos:
                due = f'  (due {datetime.fromisoformat(t.due_date):%b %-d})' if t.due_date else ''
                print(f'    ☐  {t.description}{due}')
        if done_todos:
            print(f'\n  To-dos — Done ({len(done_todos)}):')
            for t in done_todos:
                print(f'    ✓  {t.description}')

    print(f'{"─" * 50}\n')
    return goal


def edit_goal(goal: Goal) -> Goal:
    print(f'  Current name: {goal.name}')
    name = prompt_input('New name (Enter to keep): ')
    print(f'  Current description: {goal.description}')
    desc = prompt_input('New description (Enter to keep): ')

    if name:
        # rename the file
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
    cadence = prompt_input('Reminder cadence (e.g. daily, weekly, 2x/week): ') or 'weekly'
    goal.add_tactic(Tactic(description=description, reminder_cadence=cadence))
    save_goal(goal)
    print(f'\n✓ Tactic added')
    return goal


def log_update(goal: Goal) -> Goal:
    idx = select_tactic_index(goal, prompt='Select tactic to update')
    if idx is None:
        return goal
    note = prompt_input('Update note: ')
    if not note:
        print('Note required.')
        return goal
    goal.tactics[idx]['updates'].append({
        'date': datetime.now().isoformat(),
        'note': note,
    })
    save_goal(goal)
    print('\n✓ Update logged')
    return goal


def add_todo(goal: Goal) -> Goal:
    description = prompt_input('To-do description: ')
    if not description:
        print('Description required.')
        return goal
    due = prompt_input('Due date (e.g. Aug 29, tomorrow, blank to skip): ') or None
    due_iso = None
    if due:
        try:
            due_iso = dateparser.parse(due, fuzzy=True).isoformat()
        except Exception:
            print(f'Could not parse "{due}", saving without due date.')
    goal.todos.append(Todo(description=description, due_date=due_iso).model_dump())
    save_goal(goal)
    print(f'\n✓ Todo added')
    return goal


def view_todos(goal: Goal) -> Goal:
    todos = goal.get_todos()
    if not todos:
        print(f'\nNo todos for "{goal.name}".')
        return goal
    open_todos = [t for t in todos if not t.completed]
    done_todos = [t for t in todos if t.completed]
    print(f'\n{"─" * 50}')
    print(f'  {goal.name} — Todos')
    if open_todos:
        print(f'\n  Open ({len(open_todos)}):')
        for t in open_todos:
            due = f'  (due {datetime.fromisoformat(t.due_date):%b %-d})' if t.due_date else ''
            print(f'    ☐  {t.description}{due}')
    if done_todos:
        print(f'\n  Done ({len(done_todos)}):')
        for t in done_todos:
            print(f'    ✓  {t.description}')
    print(f'{"─" * 50}\n')
    return goal


def complete_todo(goal: Goal) -> Goal:
    open_todos = [t for t in goal.get_todos() if not t.completed]
    if not open_todos:
        print('No open todos.')
        return goal
    selection = fzf_on_a_list([t.description for t in open_todos], prompt='Mark complete')
    if not selection:
        return goal
    for t in goal.todos:
        if t['description'] == selection and not t['completed']:
            t['completed'] = True
            break
    save_goal(goal)
    print(f'\n✓ "{selection}" marked complete')
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
    selection = fzf_on_a_list([t.description for t in todos], prompt='Select to-do to edit')
    if not selection:
        return goal
    for t in goal.todos:
        if t['description'] == selection:
            print(f'  Current description: {t["description"]}')
            desc = prompt_input('New description (Enter to keep): ')
            current_due = t.get('due_date')
            due_display = datetime.fromisoformat(current_due).strftime("%b %-d") if current_due else "none"
            print(f'  Current due date: {due_display}')
            due = prompt_input('New due date (Enter to keep, "clear" to remove): ')
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
                    t['due_date'] = dateparser.parse(due, fuzzy=True).isoformat()
                except Exception:
                    print(f'Could not parse "{due}", due date unchanged.')
            break
    save_goal(goal)
    print('\n✓ To-do updated')
    return goal


def edit_settings() -> None:
    config = load_config()
    print(f'  Current reminder dir: {config.get("reminder_dir", "not set")}')
    reminder_dir = prompt_input('Reminder directory (Enter to keep, "clear" to remove): ')
    if reminder_dir and reminder_dir.lower() == 'clear':
        config.pop('reminder_dir', None)
    elif reminder_dir:
        config['reminder_dir'] = str(Path(reminder_dir).expanduser().resolve())
    save_config(config)
    print('\n✓ Settings updated')


# --- Menus ---

GOAL_MENU_ITEMS = [
    ('Goal',    'View goal'),
    ('Goal',    'Edit goal'),
    ('Tactics', 'Add tactic'),
    ('Tactics', 'Edit tactic'),
    ('Tactics', 'Log update on tactic'),
    ('To-do',   'Add to-do'),
    ('To-do',   'Edit to-do'),
    ('To-do',   'Complete to-do'),
    ('',        'New goal'),
    ('',        'Settings'),
]


def goal_menu(goal: Goal) -> None:
    labels = [f'{cat:<10}{action}' for cat, action in GOAL_MENU_ITEMS]
    label_to_action = {label.strip(): action for label, (_, action) in zip(labels, GOAL_MENU_ITEMS)}
    while True:
        selection = fzf_on_a_list(labels, prompt=goal.name)
        if not selection:
            break
        action = label_to_action.get(selection)
        if not action:
            continue
        match action:
            case 'View goal':
                goal = view_goal(goal)
            case 'Edit goal':
                goal = edit_goal(goal)
            case 'Add tactic':
                goal = add_tactic(goal)
            case 'Log update on tactic':
                goal = log_update(goal)
            case 'Add to-do':
                goal = add_todo(goal)
            case 'Edit tactic':
                goal = edit_tactic(goal)
            case 'Edit to-do':
                goal = edit_todo(goal)
            case 'Complete to-do':
                goal = complete_todo(goal)
            case 'New goal':
                create_new_goal()
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
    print(f'\n✓ Goal "{goal.name}" created — {goal.date_range_display()} ({goal.weeks_remaining()} weeks)')
    pause()
    goal_menu(goal)


def main() -> None:
    while True:
        names = get_stored_goal_names()

        # Auto-load if only one goal exists
        if len(names) == 1:
            goal_menu(load_goal(names[0]))
            continue

        action = fzf_on_a_list(TOP_MENU, prompt='12 Week Year')
        if not action:
            break
        match action:
            case 'New goal':
                create_new_goal()
            case 'Select goal':
                if not names:
                    print('No goals yet. Create one first.')
                    pause()
                    continue
                name = fzf_on_a_list(names, prompt='Select goal')
                if name:
                    goal_menu(load_goal(name))


if __name__ == '__main__':
    main()
