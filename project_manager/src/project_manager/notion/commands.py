"""CLI commands for Notion integration."""

import json as json_mod
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from dateutil import parser as dateparser

from project_manager.notion.client import (
    archive_page,
    build_property_update,
    get_page_body,
    get_select_options,
    query_database,
    replace_page_body,
    update_page,
)
from project_manager.notion.models import ProjectEntry
from project_manager.notion.display import format_entry_list
from project_manager.notion.triage import process_triage
from project_manager.ui import CancelAction, fzf_on_a_list, pause, prompt_input


def list_entries(
    *,
    status: str | None = None,
    context: str | None = None,
    verbose: bool = False,
) -> None:
    """List entries from the GTD Projects table."""
    filter_conditions = []
    if status:
        filter_conditions.append(
            {
                'property': 'Status',
                'select': {'equals': status},
            }
        )
    if context:
        filter_conditions.append(
            {
                'property': 'Context',
                'select': {'equals': context},
            }
        )

    filter_obj = None
    if len(filter_conditions) == 1:
        filter_obj = filter_conditions[0]
    elif len(filter_conditions) > 1:
        filter_obj = {'and': filter_conditions}

    pages = query_database(filter_obj=filter_obj)
    entries = [ProjectEntry.from_page(p) for p in pages]

    # Group by status
    if not status:
        from project_manager.notion.schema import STATUSES  # noqa: PLC0415

        for s in STATUSES:
            group = [e for e in entries if e.status == s]
            if group:
                print(f'\n── {s} ({len(group)}) ──')
                print(format_entry_list(group, verbose=verbose))
        print()
    else:
        print(f'\n── {status} ({len(entries)}) ──')
        print(format_entry_list(entries, verbose=verbose))
        print()


def list_12_week_entries(*, verbose: bool = False) -> None:
    """List only 12-Week Goal entries."""
    contexts = get_select_options('Context')
    goal_contexts = [c for c in contexts if c.startswith('12-Week Goal')]

    if not goal_contexts:
        print('No 12-Week Goal contexts found.')
        return

    if len(goal_contexts) == 1:
        list_entries(context=goal_contexts[0], verbose=verbose)
    else:
        # Multiple goal contexts — query with OR filter
        filter_obj = {
            'or': [
                {'property': 'Context', 'select': {'equals': c}}
                for c in goal_contexts
            ],
        }
        pages = query_database(filter_obj=filter_obj)
        entries = [ProjectEntry.from_page(p) for p in pages]
        for ctx in goal_contexts:
            group = [e for e in entries if e.context == ctx]
            if group:
                print(f'\n── {ctx} ({len(group)}) ──')
                print(format_entry_list(group, verbose=verbose))
        print()


def show_triage(*, verbose: bool = False) -> None:
    """Show items in Triage status."""
    list_entries(status='Triage', verbose=verbose)


def _today_filter() -> dict:
    """Build the Notion filter for today's actionable items."""
    today = datetime.now().strftime('%Y-%m-%d')
    return {
        'and': [
            {'property': 'Status', 'select': {'equals': 'Current Project'}},
            {
                'or': [
                    {
                        'property': 'Follow-Up Date',
                        'date': {'on_or_before': today},
                    },
                    {
                        'property': 'Follow-Up Date',
                        'date': {'is_empty': True},
                    },
                ],
            },
        ],
    }


def _get_today_entries() -> list[ProjectEntry]:
    """Fetch and filter today's actionable entries."""
    pages = query_database(filter_obj=_today_filter())
    entries = [ProjectEntry.from_page(p) for p in pages]
    return [e for e in entries if e.context and e.next_step]


def list_today() -> None:  # noqa: C901
    """Interactive today view — pick items and take action."""
    actionable = _get_today_entries()

    if not actionable:
        print('\n  Nothing actionable today. Nice! 🎉\n')
        return

    while actionable:
        entry = select_entry(
            actionable,
            prompt='Today',
            include_body=False,
        )
        if not entry:
            break

        body = get_page_body(entry.page_id)
        preview = _escape_for_shell(_entry_preview_text(entry, body))

        action = fzf_on_a_list(
            [
                'Log & Reschedule',
                'Snooze until tomorrow',
                'Update fields',
                'Mark done (moves to trash)',
                'Back to list',
            ],
            prompt=f'"{entry.header.strip()}"',
            preview=f"echo '{preview}'",
        )
        if not action or action == 'Back to list':
            continue

        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        match action:
            case 'Log & Reschedule':
                _log_and_reschedule_entry(entry)
                actionable = [
                    e for e in actionable if e.page_id != entry.page_id
                ]
            case 'Snooze until tomorrow':
                props = build_property_update(
                    follow_up_date=tomorrow,
                )
                update_page(entry.page_id, props)
                print(
                    f'  ✓ "{entry.header.strip()}" snoozed until {tomorrow}',
                )
                actionable = [
                    e for e in actionable if e.page_id != entry.page_id
                ]
            case 'Update fields':
                _edit_entry_fields(entry)
            case _ if action.startswith('Mark done'):
                confirm = prompt_input(
                    f'  Delete "{entry.header.strip()}"? (y/N): ',
                )
                if confirm and confirm.lower() == 'y':
                    archive_page(entry.page_id)
                    print(
                        f'  ✓ "{entry.header.strip()}" → deleted',
                    )
                    actionable = [
                        e for e in actionable if e.page_id != entry.page_id
                    ]
                else:
                    print('  Cancelled.')

        print()

    remaining = len(actionable)
    if remaining:
        print(f'  {remaining} item(s) remaining for today.\n')
    else:
        print('  All done for today! 🎉\n')


def mark_done() -> None:
    """Interactively select a Current Project to mark as done."""
    pages = query_database(
        filter_obj={
            'property': 'Status',
            'select': {'equals': 'Current Project'},
        },
    )
    entries = [ProjectEntry.from_page(p) for p in pages]

    if not entries:
        print('No current projects.')
        return

    entry = select_entry(entries, prompt='Mark done')
    if not entry:
        return

    confirm = prompt_input(
        f'  Delete "{entry.header.strip()}"? '
        "This moves it to Notion's trash. (y/N): ",
    )
    if not confirm or confirm.lower() != 'y':
        print('  Cancelled.')
        return

    archive_page(entry.page_id)
    print(f'✓ "{entry.header}" → deleted')


def defer_entry() -> None:
    """Set a follow-up date on a current project."""
    pages = query_database(
        filter_obj={
            'property': 'Status',
            'select': {'equals': 'Current Project'},
        },
    )
    entries = [ProjectEntry.from_page(p) for p in pages]

    if not entries:
        print('No current projects.')
        return

    entry = select_entry(entries, prompt='Defer')
    if not entry:
        return

    date_input = prompt_input(
        'Follow-up date (e.g. Monday, Jul 15, in 3 days): ',
    )
    if not date_input:
        return

    date_str = _parse_date_input(date_input)
    if not date_str:
        return

    props = build_property_update(follow_up_date=date_str)
    update_page(entry.page_id, props)
    print(f'✓ "{entry.header}" deferred until {date_str}')


def snooze_today() -> None:
    """Snooze today's actionable items until tomorrow."""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    actionable = _get_today_entries()

    if not actionable:
        print('Nothing to snooze — no actionable items today.')
        return

    headers = [e.header.strip() for e in actionable]
    selections = fzf_on_a_list(
        headers,
        multiple=True,
        prompt='Snooze until tomorrow',
    )
    if not selections:
        return

    selected_set = set(selections)
    count = 0
    for entry in actionable:
        if entry.header.strip() in selected_set:
            props = build_property_update(follow_up_date=tomorrow)
            update_page(entry.page_id, props)
            count += 1

    suffix = 's' if count != 1 else ''
    print(f'✓ Snoozed {count} item{suffix} until {tomorrow}')


_CADENCE_DAYS = {
    'daily': 1,
    'weekly': 7,
    '2x/week': 3,
    '3x/week': 2,
}


def _infer_reschedule_days(header: str) -> int | None:
    """Infer reschedule interval from header prefix like 'Daily:' etc."""
    lowered = header.lower().strip()
    for cadence, days in _CADENCE_DAYS.items():
        if lowered.startswith(f'{cadence}:'):
            return days
    return None


def _log_and_reschedule_entry(entry: ProjectEntry) -> None:
    """Log a note and reschedule a specific entry."""
    body = get_page_body(entry.page_id)
    editor = os.environ.get('EDITOR', 'nvim')
    fd, tmp_path = tempfile.mkstemp(suffix='.md')
    with open(fd, 'w') as f:  # noqa: PTH123
        f.write(body)
    subprocess.run(  # noqa: S603
        [editor, tmp_path],
        check=False,
    )
    new_body = Path(tmp_path).read_text()
    Path(tmp_path).unlink(missing_ok=True)
    if new_body != body:
        replace_page_body(entry.page_id, new_body)
        print(f'  ✓ Notes updated for "{entry.header.strip()}"')

    inferred_days = _infer_reschedule_days(entry.header)
    if inferred_days:
        next_date = (datetime.now() + timedelta(days=inferred_days)).strftime(
            '%Y-%m-%d'
        )
        suffix = 's' if inferred_days != 1 else ''
        print(
            f'  Rescheduling in {inferred_days} day{suffix} ({next_date})',
        )
    else:
        date_input = prompt_input(
            'Reschedule to (e.g. tomorrow, Monday, Jul 15): ',
        )
        if not date_input:
            return
        next_date = _parse_date_input(date_input)
        if not next_date:
            return

    props = build_property_update(follow_up_date=next_date)
    update_page(entry.page_id, props)
    print(f'  ✓ "{entry.header.strip()}" → {next_date}')


def log_and_reschedule() -> None:
    """Log a note and reschedule recurring items."""
    actionable = _get_today_entries()

    if not actionable:
        print('Nothing actionable today.')
        return

    entry = select_entry(actionable, prompt='Log & Reschedule')
    if not entry:
        return

    _log_and_reschedule_entry(entry)


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

    # Fetch bodies one at a time as we go (one per item reviewed)
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
            confirm = prompt_input(
                f'  Delete "{entry.header.strip()}"? (y/N): ',
            )
            if confirm and confirm.lower() == 'y':
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


_RELATIVE_DAYS = {
    'today': 0,
    'tomorrow': 1,
    'yesterday': -1,
}


def _parse_date_input(raw: str) -> str | None:
    """Parse a date string, returning YYYY-MM-DD or None."""
    lowered = raw.lower().strip()
    if lowered in _RELATIVE_DAYS:
        result = datetime.now() + timedelta(days=_RELATIVE_DAYS[lowered])
        return result.strftime('%Y-%m-%d')
    parsed = dateparser.parse(raw, fuzzy=True)
    if parsed:
        return parsed.strftime('%Y-%m-%d')
    print(f'  Could not parse "{raw}", skipping.')
    return None


def _collect_field_updates(  # noqa: C901, PLR0912
    entry: ProjectEntry,
    fields: list[str],
) -> dict:
    """Prompt for updated values for the selected fields."""
    kwargs: dict = {}

    if 'Name' in fields:
        new_name = prompt_input(
            f'Name (current: {entry.header.strip()}): ',
        )
        if new_name is not None:
            kwargs['name'] = new_name

    if 'Next actionable step' in fields:
        step = prompt_input(
            f'Next step (current: {entry.next_step or "none"}): ',
        )
        if step is not None:
            kwargs['next_step'] = step

    if 'Context' in fields:
        contexts = get_select_options('Context')
        ctx = fzf_on_a_list(
            contexts,
            prompt=f'"{entry.header}" → Context',
        )
        if ctx:
            kwargs['context'] = ctx

    if 'Status' in fields:
        from project_manager.notion.schema import STATUSES  # noqa: PLC0415

        status = fzf_on_a_list(
            STATUSES,
            prompt=f'"{entry.header}" → Status',
        )
        if status:
            kwargs['status'] = status
            if status == 'Waiting For':
                waiting_on = prompt_input(
                    'Who/what are you waiting on? '
                    f'(current: {entry.next_step or "none"}): ',
                )
                if waiting_on is not None:
                    kwargs['next_step'] = waiting_on
                followup = prompt_input(
                    'Follow-up date (e.g. Friday, in 3 days): ',
                )
                if followup:
                    parsed = _parse_date_input(followup)
                    if parsed:
                        kwargs['follow_up_date'] = parsed

    if 'Due date' in fields:
        due = prompt_input(
            'Due date (blank to clear, e.g. Jul 15): ',
        )
        if due is not None:
            if due == '':
                kwargs['due_date'] = ''
            else:
                result = _parse_date_input(due)
                if result:
                    kwargs['due_date'] = result

    if 'Follow-up date' in fields:
        fup = prompt_input('Follow-up date (blank to clear): ')
        if fup is not None:
            if fup == '':
                kwargs['follow_up_date'] = ''
            else:
                result = _parse_date_input(fup)
                if result:
                    kwargs['follow_up_date'] = result

    return kwargs


def _escape_for_shell(text: str) -> str:
    """Escape text for use in single-quoted shell strings."""
    return text.replace("'", "'\\''")


def _entry_preview_text(
    entry: ProjectEntry,
    body: str = '',
) -> str:
    """Build a preview string for an entry."""
    lines = [
        f'── {entry.header.strip()} ──',
        '',
        f'Status:    {entry.status}',
        f'Context:   {entry.context or "(none)"}',
        f'Next step: {entry.next_step or "(none)"}',
        f'Due:       {entry.due_date or "(none)"}',
        f'Follow-up: {entry.follow_up_date or "(none)"}',
    ]
    if entry.details:
        lines.append(f'Details:   {entry.details}')
    if body:
        lines.append('')
        lines.append('── Notes ──')
        for line in body.split('\n'):
            lines.append(f'  {line}')
    return '\n'.join(lines)


def select_entry(
    entries: list[ProjectEntry],
    *,
    prompt: str = 'Select',
    include_body: bool = True,
) -> ProjectEntry | None:
    """Show an fzf picker with preview for a list of entries."""
    if not entries:
        return None

    entry_map = {e.header.strip(): e for e in entries}
    headers = list(entry_map.keys())

    # Properties + page IDs; body fetched lazily by preview script
    preview_data = {
        e.header.strip(): {
            'props': _entry_preview_text(e),
            'page_id': e.page_id if include_body else None,
            'body': None,
        }
        for e in entries
    }

    fd, data_path = tempfile.mkstemp(suffix='.json')
    with open(fd, 'w') as f:  # noqa: PTH123
        f.write(json_mod.dumps(preview_data))

    # Preview script: show props, lazy-fetch + cache body in the JSON
    fd2, script_path = tempfile.mkstemp(suffix='.py')
    with open(fd2, 'w') as f:  # noqa: PTH123
        f.write(
            'import json, sys, os, fcntl\n'
            f'DATA = "{data_path}"\n'
            'key = sys.argv[1]\n'
            'with open(DATA) as f:\n'
            '    fcntl.flock(f, fcntl.LOCK_SH)\n'
            '    d = json.load(f)\n'
            'entry = d.get(key, {})\n'
            'if not entry:\n'
            '    sys.exit(0)\n'
            'print(entry["props"])\n'
            'page_id = entry.get("page_id")\n'
            'if not page_id:\n'
            '    sys.exit(0)\n'
            'body = entry.get("body")\n'
            'if body is None:\n'
            '    import httpx\n'
            '    token = os.environ.get("NOTION_NOTES_TOKEN", "")\n'
            '    url = f"https://api.notion.com/v1/blocks/{page_id}'
            '/children"\n'
            '    h = {"Authorization": f"Bearer {token}",'
            ' "Notion-Version": "2022-06-28"}\n'
            '    prefixes = {"paragraph": "", '
            '"bulleted_list_item": "• ",'
            ' "numbered_list_item": "· ",'
            ' "to_do": "☐ "}\n'
            '    try:\n'
            '        resp = httpx.get(url, headers=h)\n'
            '        blocks = resp.json().get("results", [])\n'
            '        lines = []\n'
            '        for b in blocks:\n'
            '            bt = b["type"]\n'
            '            if bt in prefixes:\n'
            '                texts = b[bt].get("rich_text", [])\n'
            '                c = " ".join('
            't["plain_text"] for t in texts).strip()\n'
            '                if c:\n'
            '                    lines.append(prefixes[bt] + c)\n'
            '        body = chr(10).join(lines)\n'
            '    except Exception:\n'
            '        body = ""\n'
            '    d[key]["body"] = body\n'
            '    with open(DATA, "w") as f:\n'
            '        fcntl.flock(f, fcntl.LOCK_EX)\n'
            '        json.dump(d, f)\n'
            'if body and body.strip():\n'
            '    print()\n'
            '    print("── Notes ──")\n'
            '    for line in body.split(chr(10)):\n'
            '        print(f"  {line}")\n',
        )

    try:
        python = sys.executable
        selection = fzf_on_a_list(
            headers,
            prompt=prompt,
            preview=f'{python} {script_path} {{}}',
        )
    finally:
        Path(data_path).unlink(missing_ok=True)
        Path(script_path).unlink(missing_ok=True)

    if not selection:
        return None
    return entry_map[selection]


def update_entry() -> None:
    """Interactively update fields on an existing project."""
    active_statuses = [
        s for s in get_select_options('Status') if s != 'Triage'
    ]
    if not active_statuses:
        print('No statuses configured.')
        return

    pages = query_database(
        filter_obj={
            'or': [
                {'property': 'Status', 'select': {'equals': s}}
                for s in active_statuses
            ],
        },
    )
    entries = [ProjectEntry.from_page(p) for p in pages]

    if not entries:
        print('No projects to update.')
        return

    entry = select_entry(entries, prompt='Update')
    if not entry:
        return

    _edit_entry_fields(entry)


def update_entry_by_ref(entry: ProjectEntry) -> None:
    """Update fields on a specific entry (no picker)."""
    _edit_entry_fields(entry)


def _edit_entry_fields(entry: ProjectEntry) -> None:
    """Prompt for field edits and push to Notion."""
    body = get_page_body(entry.page_id)
    preview = _escape_for_shell(_entry_preview_text(entry, body))

    fields = fzf_on_a_list(
        [
            'Name',
            'Next actionable step',
            'Edit notes',
            'Context',
            'Status',
            'Due date',
            'Follow-up date',
        ],
        multiple=True,
        prompt=f'"{entry.header.strip()}" → Edit fields',
        preview=f"echo '{preview}'",
    )
    if not fields:
        return

    if 'Edit notes' in fields:
        editor = os.environ.get('EDITOR', 'nvim')
        fd, tmp_path = tempfile.mkstemp(suffix='.md')
        with open(fd, 'w') as f:  # noqa: PTH123
            f.write(body)
        subprocess.run(  # noqa: S603
            [editor, tmp_path],
            check=False,
        )
        new_body = Path(tmp_path).read_text()
        Path(tmp_path).unlink(missing_ok=True)
        if new_body != body:
            replace_page_body(entry.page_id, new_body)
            print(f'  ✓ Notes updated for "{entry.header.strip()}"')
        else:
            print('  (no changes)')

    prop_fields = [f for f in fields if f != 'Edit notes']
    if not prop_fields:
        return

    kwargs = _collect_field_updates(entry, prop_fields)
    if not kwargs:
        return

    props = build_property_update(**kwargs)
    update_page(entry.page_id, props)
    print(f'  ✓ "{entry.header.strip()}" updated')


def _review_get_clear() -> None:
    """Phase 1: Get Clear — empty inbox."""
    from project_manager.notion.triage import (  # noqa: PLC0415
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
                    confirm = prompt_input(
                        f'  Delete "{entry.header.strip()}"? (y/N): ',
                    )
                    if confirm and confirm.lower() == 'y':
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
    from project_manager.notion.capture import capture_item  # noqa: PLC0415

    print('─── Phase 3: Get Creative ───')
    print('  Goal: Brain dump. Any new projects, ideas, or someday/maybes?\n')

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


def weekly_review() -> None:
    """Guided GTD weekly review: Get Clear → Get Current → Get Creative."""
    print('\n══════════════════════════════════')
    print('       📋 GTD Weekly Review')
    print('══════════════════════════════════\n')

    _review_get_clear()
    pause('Press Enter to continue to next step...')
    _review_get_current()
    pause('Press Enter to continue to next step...')
    _review_get_creative()

    print('══════════════════════════════════')
    print('  ✓ Weekly review complete!')
    print('══════════════════════════════════\n')


def notion_command(args: list[str]) -> None:
    """Dispatch notion subcommands.

    Usage:
        pm notion             — list all entries grouped by status
        pm notion triage      — show items needing triage
        pm notion process     — interactively process triage items
        pm notion goals       — show 12-week goal entries
        pm notion <context>   — filter by context name
        pm notion -v [...]    — verbose output (show details)
    """
    verbose = '-v' in args or '--verbose' in args
    args = [a for a in args if a not in ('-v', '--verbose')]

    if not args:
        list_entries(verbose=verbose)
    elif args[0] == 'triage':
        show_triage(verbose=verbose)
    elif args[0] == 'process':
        try:
            process_triage()
        except CancelAction:
            return
    elif args[0] == 'goals':
        list_12_week_entries(verbose=verbose)
    elif args[0] == 'help':
        print(notion_command.__doc__)
    else:
        # Treat as context filter
        context = ' '.join(args)
        list_entries(context=context, verbose=verbose)
