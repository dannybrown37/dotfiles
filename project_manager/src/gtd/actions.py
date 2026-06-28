from datetime import datetime, timedelta
from pathlib import Path

from dateutil import parser as dateparser

from gtd.models import (
    Goal,
    Tactic,
    Todo,
    Update,
    TOTAL_WEEKS,
    SCORE_GREEN_THRESHOLD,
)
from gtd.storage import (
    save_goal,
    load_config,
    save_config,
    OUTPUT_PATH,
    _safe_filename,
)
from gtd.ui import (
    fzf_on_a_list,
    select_tactic_index,
    prompt_input,
    score_indicator,
    score_pct,
)


def edit_goal(goal: Goal) -> Goal:
    print(f'  Current name: {goal.name}')
    name = prompt_input('New name (Enter to keep): ')
    print(f'  Current description: {goal.description}')
    desc = prompt_input('New description (Enter to keep): ')
    old_path = (
        OUTPUT_PATH / f'{_safe_filename(goal.name)}.json' if name else None
    )
    if name:
        goal.name = name
    if desc:
        goal.description = desc
    save_goal(goal)
    if (
        old_path
        and old_path != OUTPUT_PATH / f'{_safe_filename(goal.name)}.json'
    ):
        old_path.unlink(missing_ok=True)
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
    if goal.is_complete:
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
    for w in range(1, min(week, TOTAL_WEEKS) + 1):
        ex, tot = goal.week_score(w)
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

    total_ex, total_tot = goal.overall_score()
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
            parsed = dateparser.parse(due, fuzzy=True)
            if parsed is None:
                print(
                    f'Could not parse "{due}", saving without due date.',
                )
            else:
                due_iso = parsed.isoformat()
        except Exception:
            print(
                f'Could not parse "{due}", saving without due date.',
            )
    goal.todos.append(Todo(description=description, due_date=due_iso))
    save_goal(goal)
    print('\n✓ To-do added')
    return goal


def complete_todo(goal: Goal) -> Goal:
    open_todos = [(i, t) for i, t in enumerate(goal.todos) if not t.completed]
    if not open_todos:
        print('No open to-dos.')
        return goal
    labels = [f'{i}: {t.description}' for i, t in open_todos]
    selection = fzf_on_a_list(labels, prompt='Mark complete')
    if not selection:
        return goal
    idx = int(selection.split(':', 1)[0])
    goal.todos[idx].completed = True
    save_goal(goal)
    print(f'\n✓ "{goal.todos[idx].description}" marked complete')
    return goal


def remove_todo(goal: Goal) -> Goal:
    if not goal.todos:
        print('No to-dos.')
        return goal
    labels = [f'{i}: {t.description}' for i, t in enumerate(goal.todos)]
    selection = fzf_on_a_list(labels, prompt='Remove to-do')
    if not selection:
        return goal
    idx = int(selection.split(':', 1)[0])
    removed = goal.todos.pop(idx)
    save_goal(goal)
    print(f'\n✓ Removed: {removed.description}')
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
            parsed = dateparser.parse(
                due,
                fuzzy=True,
            )
            if parsed is None:
                print(f'Could not parse "{due}", due date unchanged.')
            else:
                t.due_date = parsed.isoformat()
        except Exception:
            print(f'Could not parse "{due}", due date unchanged.')


def edit_todo(goal: Goal) -> Goal:
    if not goal.todos:
        print('No to-dos yet.')
        return goal
    labels = [f'{i}: {t.description}' for i, t in enumerate(goal.todos)]
    selection = fzf_on_a_list(labels, prompt='Select to-do to edit')
    if not selection:
        return goal
    idx = int(selection.split(':', 1)[0])
    _apply_todo_edits(goal.todos[idx])
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


def start_new_cycle(goal: Goal) -> Goal | None:
    """Offer to start a new 12-week cycle from a completed goal."""
    ex, tot = goal.overall_score()
    pct = score_pct(ex, tot)
    indicator = score_indicator(ex / tot) if tot > 0 else ''

    print(f'\n  ── 12-Week Cycle Complete: {goal.name} ──')
    print(f'  {indicator} Final score: {pct} ({ex}/{tot})')
    print()

    choice = fzf_on_a_list(
        [
            'Start new cycle (carry over tactics)',
            'Start fresh cycle (no carry-over)',
            'Just view the completed goal',
        ],
        prompt='Cycle complete',
    )
    if not choice or choice.startswith('Just view'):
        return None

    now = datetime.now()
    carry_tactics = choice.startswith('Start new cycle')

    new_tactics = []
    if carry_tactics:
        for t in goal.tactics:
            new_tactics.append(
                Tactic(
                    description=t.description,
                    reminder_cadence=t.reminder_cadence,
                ),
            )

    open_todos = [
        Todo(description=t.description, due_date=t.due_date)
        for t in goal.todos
        if not t.completed
    ]

    new_goal = Goal(
        name=goal.name,
        description=goal.description,
        start_date=now.isoformat(),
        end_date=(now + timedelta(weeks=TOTAL_WEEKS)).isoformat(),
        tactics=new_tactics,
        todos=open_todos,
    )
    save_goal(new_goal)

    carried = []
    if new_tactics:
        carried.append(f'{len(new_tactics)} tactics')
    if open_todos:
        carried.append(f'{len(open_todos)} open to-dos')
    carry_msg = f' (carried: {", ".join(carried)})' if carried else ''

    print(
        f'\n✓ New cycle started for "{new_goal.name}"{carry_msg}',
    )
    print(f'  {new_goal.date_range_display()}')
    return new_goal
