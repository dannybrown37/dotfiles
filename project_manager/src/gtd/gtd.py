"""GTD CLI — David Allen's Getting Things Done powered by Notion."""

import shutil
import sys

import click

from gtd.ui import CancelAction


@click.group(invoke_without_command=True)
@click.option('-v', '--verbose', is_flag=True, help='Show details')
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """gtd — Getting Things Done CLI powered by Notion."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

    if ctx.invoked_subcommand is None:
        _interactive_menu(verbose)


@cli.command()
@click.option(
    '--upgrade',
    is_flag=True,
    help='Upgrade existing database schema',
)
def init(upgrade: bool) -> None:
    """Set up or upgrade the GTD Notion database."""
    from gtd.notion.init import init_database  # noqa: PLC0415

    try:
        init_database(upgrade=upgrade)
    except CancelAction:
        return


@cli.command()
def triage() -> None:
    """Interactively process items needing triage."""
    from gtd.notion.triage import (  # noqa: PLC0415
        process_triage,
    )

    try:
        process_triage()
    except CancelAction:
        return


@cli.command()
@click.pass_context
def goals(ctx: click.Context) -> None:
    """Show 12-week goal entries."""
    from gtd.notion.commands import (  # noqa: PLC0415
        list_12_week_entries,
    )

    list_12_week_entries(verbose=ctx.obj.get('verbose', False))


@cli.command(name='filter')
@click.argument('context', nargs=-1, required=True)
@click.pass_context
def filter_context(ctx: click.Context, context: tuple[str, ...]) -> None:
    """Filter by context name (e.g. gtd filter Phone)."""
    from gtd.notion.commands import (  # noqa: PLC0415
        list_entries,
    )

    context_str = ' '.join(context)
    list_entries(
        context=context_str,
        verbose=ctx.obj.get('verbose', False),
    )


@cli.command()
def today() -> None:
    """Show actionable items for today."""
    from gtd.notion.commands import (  # noqa: PLC0415
        list_today,
    )

    list_today()


@cli.command()
def snooze() -> None:
    """Snooze today's items until tomorrow."""
    from gtd.notion.commands import (  # noqa: PLC0415
        snooze_today,
    )

    try:
        snooze_today()
    except CancelAction:
        return


@cli.command(name='log')
def log_cmd() -> None:
    """Log a note and reschedule a recurring item."""
    from gtd.notion.commands import (  # noqa: PLC0415
        log_and_reschedule,
    )

    try:
        log_and_reschedule()
    except CancelAction:
        return


@cli.command()
def done() -> None:
    """Mark a current project as done (archives it)."""
    from gtd.notion.commands import (  # noqa: PLC0415
        mark_done,
    )

    try:
        mark_done()
    except CancelAction:
        return


@cli.command()
def review() -> None:
    """Run the GTD weekly review ritual."""
    from gtd.notion.commands import (  # noqa: PLC0415
        weekly_review,
    )

    try:
        weekly_review()
    except CancelAction:
        return


@cli.command()
def update() -> None:
    """Update fields on an existing project."""
    from gtd.notion.commands import (  # noqa: PLC0415
        update_entry,
    )

    try:
        update_entry()
    except CancelAction:
        return


@cli.command()
def defer() -> None:
    """Defer a project by setting a follow-up date."""
    from gtd.notion.commands import (  # noqa: PLC0415
        defer_entry,
    )

    try:
        defer_entry()
    except CancelAction:
        return


@cli.command()
def someday() -> None:
    """Review Someday/Maybe items — keep, activate, or drop."""
    from gtd.notion.commands import (  # noqa: PLC0415
        review_someday,
    )

    try:
        review_someday()
    except CancelAction:
        return


@cli.command()
@click.argument('header', nargs=-1)
def capture(header: tuple[str, ...]) -> None:
    """Quick-capture an item to the GTD inbox.

    Examples:
        gtd capture Buy groceries
        gtd capture               (interactive prompt)
    """
    from gtd.notion.capture import capture_item  # noqa: PLC0415

    try:
        capture_item(header=' '.join(header) if header else None)
    except CancelAction:
        return


@cli.command()
def dump() -> None:
    """Rapid-fire brain dump — capture everything, triage later."""
    from gtd.notion.commands import brain_dump  # noqa: PLC0415

    try:
        brain_dump()
    except CancelAction:
        return


def _interactive_menu(verbose: bool) -> None:  # noqa: C901, PLR0912, PLR0915
    """Launch interactive fzf menu for GTD actions."""
    from gtd.notion.commands import (  # noqa: PLC0415
        brain_dump,
        list_entries,
        list_12_week_entries,
        list_today,
        mark_done,
        defer_entry,
        update_entry,
        review_someday,
        weekly_review,
        snooze_today,
        log_and_reschedule,
    )
    from gtd.notion.capture import (  # noqa: PLC0415
        capture_item,
    )
    from gtd.notion.triage import (  # noqa: PLC0415
        process_triage,
    )
    from gtd.ui import (  # noqa: PLC0415
        fzf_on_a_list,
        pause,
    )

    if shutil.which('fzf') is None:
        click.echo(
            'Error: fzf is required but not found on PATH.\n'
            'Install it: https://github.com/junegunn/fzf#installation',
        )
        sys.exit(1)

    menu_items = [
        ('Do', 'Today'),
        ('Do', 'Log & Reschedule'),
        ('Do', 'Snooze until tomorrow'),
        ('Do', 'Capture new item'),
        ('Do', 'Brain dump'),
        ('Do', 'Triage inbox'),
        ('Manage', 'Update project'),
        ('Manage', 'Defer project until date'),
        ('Manage', 'Mark done'),
        ('Review', 'Weekly Review'),
        ('Review', 'Review Someday/Maybe'),
        ('View', 'View all projects'),
        ('View', '12-Week Goals'),
        ('View', 'Filter by context'),
    ]

    labels = [
        f'{i + 1:>2}. {cat:<10}{action}'
        for i, (cat, action) in enumerate(menu_items)
    ]
    label_to_action = {
        label.strip(): action
        for label, (_, action) in zip(
            labels,
            menu_items,
            strict=True,
        )
    }

    while True:
        try:
            selection = fzf_on_a_list(labels, prompt='GTD')
        except CancelAction:
            break
        if not selection:
            break

        action = label_to_action.get(selection)
        if not action:
            continue

        try:
            match action:
                case 'Today':
                    list_today()
                case 'Log & Reschedule':
                    log_and_reschedule()
                case 'Snooze until tomorrow':
                    snooze_today()
                case 'View all projects':
                    list_entries(verbose=verbose)
                    pause()
                case 'Triage inbox':
                    process_triage()
                case 'Capture new item':
                    capture_item()
                case 'Brain dump':
                    brain_dump()
                case 'Update project':
                    update_entry()
                case 'Defer project until date':
                    defer_entry()
                case 'Mark done':
                    mark_done()
                case 'Weekly Review':
                    weekly_review()
                case 'Review Someday/Maybe':
                    review_someday()
                case '12-Week Goals':
                    list_12_week_entries(verbose=verbose)
                    pause()
                case 'Filter by context':
                    from gtd.notion.client import (  # noqa: PLC0415
                        get_select_options,
                    )

                    contexts = get_select_options('Context')
                    ctx = fzf_on_a_list(contexts, prompt='Context')
                    if ctx:
                        list_entries(context=ctx, verbose=verbose)
                        pause()
        except CancelAction:
            continue


def main() -> None:
    """Entry point for gtd command."""
    cli()
