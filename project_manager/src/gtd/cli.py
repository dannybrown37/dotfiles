import json
import shutil
import sys

import click

from gtd.models import Goal, TOTAL_WEEKS
from gtd.storage import (
    ensure_dirs,
    save_goal,
    load_goal,
    get_stored_goal_names,
    get_archived_goal_names,
    OUTPUT_PATH,
    ARCHIVE_PATH,
    _safe_filename,
)
from gtd.ui import (
    fzf_on_a_list,
    prompt_input,
    pause,
    CancelAction,
    score_indicator,
    score_pct,
)
from gtd.views import view_goal, detailed_view
from gtd.actions import (
    edit_goal,
    weekly_scorecard,
    view_score_history,
    add_tactic,
    log_update,
    add_todo,
    edit_tactic,
    remove_tactic,
    edit_todo,
    remove_todo,
    complete_todo,
    edit_settings,
    start_new_cycle,
)


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


def goal_menu(goal: Goal) -> None:  # noqa: C901
    if goal.is_complete:
        try:
            new_goal = start_new_cycle(goal)
        except CancelAction:
            return
        if new_goal is None:
            view_goal(goal)
            pause()
            return
        goal = new_goal

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
        try:
            selection = fzf_on_a_list(
                labels,
                prompt=(
                    f'{goal.name} (Wk {goal.current_week()}/{TOTAL_WEEKS})'
                ),
            )
        except CancelAction:
            break
        if not selection:
            break
        action = label_to_action.get(selection)
        if not action:
            continue
        if action == 'Other goals':
            break
        if action == 'Settings':
            try:
                edit_settings()
            except CancelAction:
                continue
        elif action in GOAL_ACTION_MAP:
            try:
                goal = GOAL_ACTION_MAP[action](goal)
            except CancelAction:
                continue
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
    src = OUTPUT_PATH / f'{_safe_filename(name)}.json'
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
    try:
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
    except CancelAction:
        return


def _print_status() -> None:
    """Print all goals' status to stdout (no fzf required)."""
    ensure_dirs()
    names = get_stored_goal_names()
    if not names:
        print('No goals configured.')
        return

    for name in names:
        goal = load_goal(name)
        week = goal.current_week()
        weeks_left = goal.weeks_remaining()
        status = (
            'COMPLETE'
            if goal.is_complete
            else (
                f'Week {week}/{TOTAL_WEEKS}'
                f'  •  {weeks_left} week{"s" if weeks_left != 1 else ""} left'
            )
        )
        print(f'{goal.name}')
        print(f'  {goal.progress_bar()}')
        print(f'  {status}')

        ex, tot = goal.overall_score()
        if tot > 0:
            pct = score_pct(ex, tot)
            indicator = score_indicator(ex / tot)
            print(f'  {indicator} Execution: {pct} ({ex}/{tot})')

        open_todos = [t for t in goal.todos if not t.completed]
        if open_todos:
            count = len(open_todos)
            suffix = 's' if count != 1 else ''
            print(f'  {count} open to-do{suffix}')
        print()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """pm — 12-Week Year CLI with Notion GTD integration."""
    if ctx.invoked_subcommand is None:
        _interactive()


@cli.command()
def status() -> None:
    """Print all goals' progress to stdout."""
    _print_status()


def _interactive() -> None:
    """Launch the interactive fzf-based TUI."""
    if shutil.which('fzf') is None:
        click.echo(
            'Error: fzf is required but not found on PATH.\n'
            'Install it: https://github.com/junegunn/fzf#installation',
        )
        sys.exit(1)

    ensure_dirs()
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
        try:
            action = fzf_on_a_list(TOP_MENU, prompt='12 Week Year')
        except CancelAction:
            break
        if not action:
            break
        _handle_top_menu_action(action, names)


def main() -> None:
    """Entry point."""
    cli()
