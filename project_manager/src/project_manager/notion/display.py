"""Display formatting for Notion entries."""

from project_manager.notion.models import ProjectEntry
from project_manager.notion.schema import STATUS_ICONS


def format_entry(entry: ProjectEntry, *, verbose: bool = False) -> str:
    """Format a single entry for terminal display."""
    icon = STATUS_ICONS.get(entry.status, '·')
    context = f'[{entry.context}]' if entry.context else ''
    lines = [f'{icon} {entry.header}  {context}']

    if entry.next_step:
        lines.append(f'    Next: {entry.next_step}')
    if verbose and entry.details:
        lines.append(f'    Details: {entry.details[:80]}')
    if entry.due_date:
        lines.append(f'    Due: {entry.due_date}')
    if verbose and entry.follow_up_date:
        lines.append(f'    Follow-up: {entry.follow_up_date}')

    return '\n'.join(lines)


def format_entry_list(
    entries: list[ProjectEntry],
    *,
    verbose: bool = False,
) -> str:
    """Format a list of entries for terminal display."""
    if not entries:
        return '  (none)'
    return '\n'.join(format_entry(e, verbose=verbose) for e in entries)
