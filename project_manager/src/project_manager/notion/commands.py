"""CLI commands for Notion integration."""

import json as json_mod
import tempfile
from datetime import datetime
from pathlib import Path

from dateutil import parser as dateparser

from project_manager.notion.client import (
    archive_page,
    build_property_update,
    get_page_body,
    get_select_options,
    query_database,
    update_page,
)
from project_manager.notion.models import ProjectEntry
from project_manager.notion.display import format_entry_list
from project_manager.notion.triage import process_triage
from project_manager.ui import CancelAction, fzf_on_a_list, prompt_input


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
        for s in ('Current Project', 'Triage', 'Someday/Maybe'):
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


def list_today() -> None:
    """Show actionable items for today.

    Criteria: Current Project, has a context, has a next actionable step,
    and Follow-Up Date is not in the future (or not set).
    """
    today = datetime.now().strftime('%Y-%m-%d')

    # Get Current Projects whose follow-up is today or earlier (or empty)
    filter_obj = {
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

    pages = query_database(filter_obj=filter_obj)
    entries = [ProjectEntry.from_page(p) for p in pages]

    # Filter for items with both a context and a next step
    actionable = [e for e in entries if e.context and e.next_step]

    if not actionable:
        print('\n  Nothing actionable today. Nice! 🎉\n')
        return

    # Group by context
    contexts: dict[str, list[ProjectEntry]] = {}
    for e in actionable:
        contexts.setdefault(e.context, []).append(e)

    print(
        f'\n── Today ({len(actionable)} actionable) ──\n',
    )
    for ctx in sorted(contexts):
        items = contexts[ctx]
        print(f'  [{ctx}]')
        for e in items:
            due = f'  (due {e.due_date})' if e.due_date else ''
            print(f'    • {e.header}{due}')
            print(f'      → {e.next_step}')
        print()


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

    archive_page(entry.page_id)
    print(f'✓ "{entry.header}" → Done (archived)')


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


def review_someday() -> None:
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

    for entry in entries:
        body = get_page_body(entry.page_id)
        preview = _escape_for_shell(
            _entry_preview_text(entry, body),
        )

        action = fzf_on_a_list(
            ['Keep', 'Activate (→ Current Project)', 'Drop (archive)'],
            prompt=f'"{entry.header.strip()}"',
            preview=f"echo '{preview}'",
        )
        if not action:
            break

        if action.startswith('Activate'):
            props = build_property_update(status='Current Project')
            update_page(entry.page_id, props)
            print(f'  ✓ Activated: {entry.header.strip()}')
            activated += 1
        elif action.startswith('Drop'):
            archive_page(entry.page_id)
            print(f'  ✓ Dropped: {entry.header.strip()}')
            dropped += 1

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


def _parse_date_input(raw: str) -> str | None:
    """Parse a date string, returning YYYY-MM-DD or None."""
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
        status = fzf_on_a_list(
            ['Current Project', 'Someday/Maybe'],
            prompt=f'"{entry.header}" → Status',
        )
        if status:
            kwargs['status'] = status

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
            '    try:\n'
            '        resp = httpx.get(url, headers=h)\n'
            '        blocks = resp.json().get("results", [])\n'
            '        lines = []\n'
            '        for b in blocks:\n'
            '            if b["type"] == "paragraph":\n'
            '                texts = b["paragraph"]["rich_text"]\n'
            '                c = " ".join('
            't["plain_text"] for t in texts).strip()\n'
            '                if c:\n'
            '                    lines.append(c)\n'
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
        selection = fzf_on_a_list(
            headers,
            prompt=prompt,
            preview=f'python3 {script_path} {{}}',
        )
    finally:
        Path(data_path).unlink(missing_ok=True)
        Path(script_path).unlink(missing_ok=True)

    if not selection:
        return None
    return entry_map[selection]


def update_entry() -> None:
    """Interactively update fields on an existing project."""
    pages = query_database(
        filter_obj={
            'or': [
                {
                    'property': 'Status',
                    'select': {'equals': 'Current Project'},
                },
                {
                    'property': 'Status',
                    'select': {'equals': 'Someday/Maybe'},
                },
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

    body = get_page_body(entry.page_id)
    preview = _escape_for_shell(_entry_preview_text(entry, body))

    fields = fzf_on_a_list(
        [
            'Next actionable step',
            'Context',
            'Status',
            'Due date',
            'Follow-up date',
        ],
        multiple=True,
        prompt=f'"{entry.header}" → Edit fields',
        preview=f"echo '{preview}'",
    )
    if not fields:
        return

    kwargs = _collect_field_updates(entry, fields)
    if not kwargs:
        print('  Nothing to update.')
        return

    props = build_property_update(**kwargs)
    update_page(entry.page_id, props)
    print(f'  ✓ "{entry.header}" updated')


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
