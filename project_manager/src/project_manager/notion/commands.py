"""CLI commands for Notion integration."""

from project_manager.notion.client import (
    get_select_options,
    query_database,
)
from project_manager.notion.models import ProjectEntry
from project_manager.notion.display import format_entry_list
from project_manager.notion.triage import process_triage
from project_manager.ui import CancelAction


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
