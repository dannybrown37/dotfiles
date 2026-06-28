"""Weekly review and Someday/Maybe review flows."""

__all__ = ['brain_dump', 'review_someday', 'weekly_review']

from gtd.notion.client import (
    archive_page,
    build_property_update,
    get_page_body,
    get_select_options,
    query_database,
    update_page,
)
from gtd.notion.entries import (
    _edit_entry_fields,
    _entry_preview_text,
    _escape_for_shell,
    update_entry_by_ref,
)
from gtd.notion.log import _confirm_delete, _infer_cadence
from gtd.notion.models import ProjectEntry
from gtd.notion.triage import process_triage
from gtd.ui import fzf_on_a_list, pause, prompt_input


def review_someday() -> None:  # noqa: C901
    """Review Someday/Maybe items — keep, activate, or drop each."""
    pages = query_database(
        filter_obj={
            'property': 'Status',
            'select': {'equals': 'Someday/Maybe'},
        },
    )
    entries = [ProjectEntry.from_page(p) for p in pages]

    if not entries:
        print('No Someday/Maybe items. 🎉')
        return

    print(
        f'\n  ── Someday/Maybe Review ({len(entries)} items) ──\n',
    )

    activated = 0
    dropped = 0
    total = len(entries)

    for i, entry in enumerate(entries, 1):
        body = get_page_body(entry.page_id)
        preview = _escape_for_shell(
            _entry_preview_text(entry, body),
        )

        action = fzf_on_a_list(
            [
                'Keep',
                'Update',
                'Activate (→ Current Project)',
                'Drop (archive)',
            ],
            prompt=f'[{i}/{total}] "{entry.header.strip()}"',
            preview=f"echo '{preview}'",
        )
        if not action:
            break

        if action == 'Update':
            update_entry_by_ref(entry)
        elif action.startswith('Activate'):
            props = build_property_update(status='Current Project')
            update_page(entry.page_id, props)
            print(f'  ✓ Activated: {entry.header.strip()}')
            activated += 1
        elif action.startswith('Drop'):
            if _confirm_delete(entry):
                archive_page(entry.page_id)
                print(f'  ✓ Dropped: {entry.header.strip()}')
                dropped += 1
            else:
                print('  Kept.')

        print()

    parts = []
    if activated:
        parts.append(f'{activated} activated')
    if dropped:
        parts.append(f'{dropped} dropped')
    kept = len(entries) - activated - dropped
    if kept:
        parts.append(f'{kept} kept')
    if parts:
        print(f'  Review complete: {", ".join(parts)}')


def brain_dump() -> None:
    """Rapid-fire capture loop — get everything out of your head."""
    from gtd.notion.capture import capture_item  # noqa: PLC0415

    print('\n── 🧠 Brain Dump ──')
    print('  Get it all out. Capture everything.\n')

    captured = 0
    while True:
        action = fzf_on_a_list(
            ['Capture an idea', 'Done brainstorming'],
            prompt='Brain dump',
        )
        if not action or action == 'Done brainstorming':
            break
        capture_item()
        captured += 1

    if captured:
        print(f'  ✓ Captured {captured} new item(s) → Triage\n')
    else:
        print('  No new items captured.\n')


def _review_get_clear() -> None:
    """Phase 1: Get Clear — empty inbox."""
    from gtd.notion.triage import (  # noqa: PLC0415
        _get_triage_entries,
    )

    print('─── Phase 1: Get Clear ───')
    print('  Goal: Empty your inbox. Process every item.\n')

    triage_items = _get_triage_entries()
    if triage_items:
        summary_lines = [
            f'── Triage Inbox ({len(triage_items)} items) ──',
            '',
        ]
        for item in triage_items:
            detail = f'  {item.details}' if item.details else ''
            summary_lines.append(f'  • {item.header.strip()}{detail}')
        preview = _escape_for_shell('\n'.join(summary_lines))

        print(f'  ⚠ {len(triage_items)} item(s) in Triage\n')
        action = fzf_on_a_list(
            ['Process triage now', 'Skip for now'],
            prompt='Inbox',
            preview=f"echo '{preview}'",
        )
        if action == 'Process triage now':
            process_triage()
            print()
    else:
        print('  ✓ Inbox zero! 🎉\n')


def _review_get_current() -> None:  # noqa: C901, PLR0912, PLR0915
    """Phase 2: Get Current — review active projects and Someday/Maybe."""
    print('─── Phase 2: Get Current ───')
    print('  Goal: Review every active project. Is the next action right?\n')

    current_pages = query_database(
        filter_obj={
            'property': 'Status',
            'select': {'equals': 'Current Project'},
        },
    )
    current_entries = [ProjectEntry.from_page(p) for p in current_pages]

    if not current_entries:
        print('  No current projects.\n')
    else:
        missing_next = [e for e in current_entries if not e.next_step]
        print(f'  {len(current_entries)} current project(s)')
        if missing_next:
            print(
                f'  ⚠ {len(missing_next)} missing a next action: '
                + ', '.join(e.header.strip() for e in missing_next),
            )
        print()

        total = len(current_entries)
        updated = 0
        for i, entry in enumerate(current_entries, 1):
            body = get_page_body(entry.page_id)
            preview = _escape_for_shell(_entry_preview_text(entry, body))

            action = fzf_on_a_list(
                [
                    'Looks good',
                    'Update fields',
                    'Mark done',
                    'Move to Someday/Maybe',
                ],
                prompt=f'[{i}/{total}] {entry.header.strip()}',
                preview=f"echo '{preview}'",
            )
            if not action:
                break

            match action:
                case 'Update fields':
                    _edit_entry_fields(entry)
                    updated += 1
                case 'Mark done':
                    if _confirm_delete(entry):
                        archive_page(entry.page_id)
                        print(
                            f'  ✓ "{entry.header.strip()}" → deleted',
                        )
                    else:
                        print('  Cancelled.')
                case 'Move to Someday/Maybe':
                    props = build_property_update(status='Someday/Maybe')
                    update_page(entry.page_id, props)
                    print(f'  ✓ "{entry.header.strip()}" → Someday/Maybe')
                case _:
                    pass

            print()

        if updated:
            print(f'  {updated} project(s) updated\n')

    # Someday/Maybe review
    someday_pages = query_database(
        filter_obj={
            'property': 'Status',
            'select': {'equals': 'Someday/Maybe'},
        },
    )
    someday_entries = [ProjectEntry.from_page(p) for p in someday_pages]

    if not someday_entries:
        print('  No Someday/Maybe items.\n')
    else:
        summary_lines = [
            f'── Someday/Maybe ({len(someday_entries)} items) ──',
            '',
        ]
        for entry in someday_entries:
            ctx = f' [{entry.context}]' if entry.context else ''
            summary_lines.append(f'  • {entry.header.strip()}{ctx}')
        preview = _escape_for_shell('\n'.join(summary_lines))

        print(f'  {len(someday_entries)} Someday/Maybe item(s)\n')
        action = fzf_on_a_list(
            ['Review now', 'Skip for now'],
            prompt='Someday/Maybe',
            preview=f"echo '{preview}'",
        )
        if action == 'Review now':
            review_someday()
            print()


def _review_get_creative() -> None:
    """Phase 3: Get Creative — brain dump new ideas."""
    print('─── Phase 3: Get Creative ───')
    print('  Goal: Brain dump. Any new projects, ideas, or someday/maybes?\n')

    from gtd.notion.capture import capture_item  # noqa: PLC0415

    captured = 0
    while True:
        action = fzf_on_a_list(
            ['Capture an idea', 'Done brainstorming'],
            prompt='Brain dump',
        )
        if not action or action == 'Done brainstorming':
            break
        capture_item()
        captured += 1

    if captured:
        print(f'  ✓ Captured {captured} new item(s) → Triage\n')
    else:
        print('  No new items captured.\n')


def _review_check_goals() -> None:  # noqa: C901, PLR0912, PLR0915
    """Phase 0: Check 12-Week Year goals — local + Notion."""
    from gtd.models import TOTAL_WEEKS, Goal, Tactic  # noqa: PLC0415
    from gtd.storage import (  # noqa: PLC0415
        ensure_dirs,
        get_stored_goal_names,
        load_goal,
        save_goal,
    )
    from gtd.ui import (  # noqa: PLC0415
        score_indicator,
        score_pct,
    )

    print('─── Phase 0: Check Goals ───')
    print('  Goal: Review 12-Week Year execution. Score if needed.\n')

    ensure_dirs()
    local_names = get_stored_goal_names()

    notion_goal_groups: dict[str, list[ProjectEntry]] = {}
    try:
        contexts = get_select_options('Context')
        goal_contexts = [c for c in contexts if c.startswith('12-Week Goal')]
        if goal_contexts:
            pages = query_database(
                filter_obj={
                    'or': [
                        {
                            'property': 'Context',
                            'select': {'equals': c},
                        }
                        for c in goal_contexts
                    ],
                },
            )
            for p in pages:
                entry = ProjectEntry.from_page(p)
                notion_goal_groups.setdefault(
                    entry.context,
                    [],
                ).append(entry)
    except SystemExit:
        pass
    except Exception as exc:
        print(f'  (Notion query failed: {exc})\n')

    if not local_names and not notion_goal_groups:
        print('  No 12-Week Year goals configured.\n')
        return

    goals_to_score: list[tuple] = []
    for name in local_names:
        goal = load_goal(name)
        week = goal.current_week()
        print(f'  📊 {goal.name}')
        print(f'     {goal.progress_bar()}')

        ex, tot = goal.overall_score()
        if tot > 0:
            pct = score_pct(ex, tot)
            indicator = score_indicator(ex / tot)
            print(f'     {indicator} Execution: {pct} ({ex}/{tot})')
        else:
            print('     No scores yet')

        if not goal.is_complete:
            weeks_to_check = []
            if week > 1:
                prev_key = str(week - 1)
                prev_unscored = [
                    t for t in goal.tactics if prev_key not in t.weekly_scores
                ]
                if prev_unscored:
                    weeks_to_check.append(week - 1)
                    print(
                        f'     ⚠ Week {week - 1}/{TOTAL_WEEKS}: '
                        f'{len(prev_unscored)} tactic(s) unscored',
                    )

            cur_key = str(week)
            cur_unscored = [
                t for t in goal.tactics if cur_key not in t.weekly_scores
            ]
            if cur_unscored:
                weeks_to_check.append(week)
                print(
                    f'     ⚠ Week {week}/{TOTAL_WEEKS}: '
                    f'{len(cur_unscored)} tactic(s) unscored',
                )

            for w in weeks_to_check:
                goals_to_score.append((goal, w))
        print()

    local_set = {n.lower() for n in local_names}
    for ctx, entries in sorted(notion_goal_groups.items()):
        goal_name = ctx.removeprefix('12-Week Goal:').strip()
        if goal_name.lower() in local_set:
            continue

        print(f'  🎯 {goal_name} (Notion, {len(entries)} items)')
        for entry in entries:
            due = f' (due {entry.due_date})' if entry.due_date else ''
            print(f'     • {entry.header.strip()}{due}')

        print(f'\n  ⚠ No local scoring file for "{goal_name}"')
        create = fzf_on_a_list(
            ['Create local goal for scoring', 'Skip'],
            prompt=f'"{goal_name}"',
        )
        if create and create.startswith('Create'):
            tactics = []
            for entry in entries:
                header = entry.header.strip()
                cadence = _infer_cadence(header)
                tactics.append(
                    Tactic(
                        description=header,
                        reminder_cadence=cadence,
                    )
                )

            if local_names:
                ref = load_goal(local_names[0])
                goal = Goal(
                    name=goal_name,
                    description=ctx,
                    start_date=ref.start_date,
                    end_date=ref.end_date,
                    tactics=tactics,
                )
            else:
                goal = Goal.new(
                    name=goal_name,
                    description=ctx,
                )
                goal.tactics = tactics

            save_goal(goal)
            week = goal.current_week()
            print(
                f'  ✓ Created "{goal_name}" with {len(tactics)} tactic(s)',
            )
            goals_to_score.append((goal, week))
        print()

    if not goals_to_score:
        return

    action = fzf_on_a_list(
        ['Score unscored weeks', 'Skip scoring'],
        prompt='12-Week Goals',
    )
    if action != 'Score unscored weeks':
        return

    for goal, week in goals_to_score:
        wk_key = str(week)
        print(f'\n  ── {goal.name} (Week {week}) ──\n')
        max_len = max(len(t.description) for t in goal.tactics)
        for tactic in goal.tactics:
            current = tactic.weekly_scores.get(wk_key)
            if current is not None:
                continue
            padded = tactic.description.ljust(max_len)
            answer = prompt_input(
                f'  {padded}  | score 1-10: ',
            )
            if answer and answer.isdigit():
                score = max(1, min(10, int(answer)))
                tactic.weekly_scores[wk_key] = score
        save_goal(goal)

        sc, mx = goal.week_score(week)
        if mx > 0:
            pct = score_pct(sc, mx)
            print(f'\n  Week {week}: {pct} ({sc}/{mx})')
    print()


def weekly_review() -> None:
    """Guided weekly review: Goals → Clear → Current → Creative."""
    print('\n══════════════════════════════════')
    print('       📋 GTD Weekly Review')
    print('══════════════════════════════════\n')

    _review_check_goals()
    pause('Press Enter to continue to next step...')
    _review_get_clear()
    pause('Press Enter to continue to next step...')
    _review_get_current()
    pause('Press Enter to continue to next step...')
    _review_get_creative()

    print('══════════════════════════════════')
    print('  ✓ Weekly review complete!')
    print('══════════════════════════════════\n')
