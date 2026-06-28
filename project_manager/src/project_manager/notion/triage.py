"""Interactive triage flow for processing inbox items."""

from dateutil import parser as dateparser

from project_manager.notion.client import (
    get_select_options,
    query_database,
    update_page,
    build_property_update,
)
from project_manager.notion.models import ProjectEntry
from project_manager.ui import fzf_on_a_list, prompt_input, CancelAction


STATUSES = ['Current Project', 'Someday/Maybe']


def _get_triage_entries() -> list[ProjectEntry]:
    """Fetch all items in Triage status or with no status set."""
    pages = query_database(
        filter_obj={
            'or': [
                {'property': 'Status', 'select': {'equals': 'Triage'}},
                {'property': 'Status', 'select': {'is_empty': True}},
            ],
        },
    )
    return [ProjectEntry.from_page(p) for p in pages]


def _process_single_entry(entry: ProjectEntry) -> bool:
    """Process one triage item. Returns True if processed, False if skipped."""
    print(f'\n  ── Processing: {entry.header} ──')
    if entry.details:
        print(f'  Details: {entry.details}')
    print()

    # Status
    status = fzf_on_a_list(
        STATUSES,
        prompt=f'"{entry.header}" → Status',
    )
    if not status:
        return False

    # Context
    contexts = get_select_options('Context')
    context = fzf_on_a_list(
        contexts,
        prompt=f'"{entry.header}" → Context',
    )
    if not context:
        return False

    # Next Actionable Step
    next_step = prompt_input('Next actionable step: ')
    if next_step is None:
        return False

    # Optional Due Date
    due_date_input = prompt_input(
        'Due date (e.g. Jul 15, 2026-08-01, blank to skip): ',
    )
    due_iso: str | None = None
    if due_date_input:
        parsed = dateparser.parse(due_date_input, fuzzy=True)
        if parsed:
            due_iso = parsed.strftime('%Y-%m-%d')
        else:
            print(f'  Could not parse "{due_date_input}", skipping due date.')

    # Optional Follow-Up Date
    follow_up_input = prompt_input(
        'Follow-up date (blank to skip): ',
    )
    follow_up_iso: str | None = None
    if follow_up_input:
        parsed = dateparser.parse(follow_up_input, fuzzy=True)
        if parsed:
            follow_up_iso = parsed.strftime('%Y-%m-%d')
        else:
            print(
                f'  Could not parse "{follow_up_input}", '
                f'skipping follow-up date.',
            )

    # Build and send update
    props = build_property_update(
        status=status,
        context=context,
        next_step=next_step or None,
        due_date=due_iso,
        follow_up_date=follow_up_iso,
    )
    update_page(entry.page_id, props)
    print(f'  ✓ "{entry.header}" → {status} [{context}]')
    return True


def process_triage() -> None:
    """Interactive triage processing flow."""
    entries = _get_triage_entries()
    if not entries:
        print('No items in Triage. Inbox zero! 🎉')
        return

    print(
        f'\n  {len(entries)} item{"s" if len(entries) != 1 else ""}'
        f' in Triage\n'
    )

    from project_manager.notion.commands import (  # noqa: PLC0415
        select_entry,
    )

    if len(entries) == 1:
        items_to_process = entries
    else:
        process_all = '▶ Process all in order'
        choices = [process_all, 'Pick one']
        choice = fzf_on_a_list(choices, prompt='Triage')
        if not choice:
            return
        if choice == process_all:
            items_to_process = entries
        else:
            entry = select_entry(entries, prompt='Triage')
            if not entry:
                return
            items_to_process = [entry]

    processed = 0
    for entry in items_to_process:
        try:
            if _process_single_entry(entry):
                processed += 1
        except CancelAction:
            break

    if processed:
        suffix = 's' if processed != 1 else ''
        print(f'\n  ✓ Processed {processed} item{suffix}')
