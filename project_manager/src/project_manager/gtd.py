"""GTD CLI — David Allen's Getting Things Done powered by Notion."""

import shutil
import sys

import click

from project_manager.ui import CancelAction


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
def triage() -> None:
    """Interactively process items needing triage."""
    from project_manager.notion.triage import (  # noqa: PLC0415
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
    from project_manager.notion.commands import (  # noqa: PLC0415
        list_12_week_entries,
    )

    list_12_week_entries(verbose=ctx.obj.get('verbose', False))


@cli.command(name='filter')
@click.argument('context', nargs=-1, required=True)
@click.pass_context
def filter_context(ctx: click.Context, context: tuple[str, ...]) -> None:
    """Filter by context name (e.g. gtd filter Phone)."""
    from project_manager.notion.commands import (  # noqa: PLC0415
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
    from project_manager.notion.commands import (  # noqa: PLC0415
        list_today,
    )

    list_today()


@cli.command()
def done() -> None:
    """Mark a current project as done (archives it)."""
    from project_manager.notion.commands import (  # noqa: PLC0415
        mark_done,
    )

    try:
        mark_done()
    except CancelAction:
        return


@cli.command()
def update() -> None:
    """Update fields on an existing project."""
    from project_manager.notion.commands import (  # noqa: PLC0415
        update_entry,
    )

    try:
        update_entry()
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
    from project_manager.notion.capture import capture_item  # noqa: PLC0415

    try:
        capture_item(header=' '.join(header) if header else None)
    except CancelAction:
        return


def _interactive_menu(verbose: bool) -> None:  # noqa: C901, PLR0912
    """Launch interactive fzf menu for GTD actions."""
    from project_manager.notion.commands import (  # noqa: PLC0415
        list_entries,
        list_12_week_entries,
        list_today,
        mark_done,
        update_entry,
    )
    from project_manager.notion.capture import (  # noqa: PLC0415
        capture_item,
    )
    from project_manager.notion.triage import (  # noqa: PLC0415
        process_triage,
    )
    from project_manager.ui import (  # noqa: PLC0415
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
        'Today',
        'View all projects',
        'Triage inbox',
        'Capture new item',
        'Update project',
        'Mark done',
        '12-Week Goals',
        'Filter by context',
    ]

    while True:
        try:
            selection = fzf_on_a_list(menu_items, prompt='GTD')
        except CancelAction:
            break
        if not selection:
            break

        try:
            match selection:
                case 'Today':
                    list_today()
                    pause()
                case 'View all projects':
                    list_entries(verbose=verbose)
                    pause()
                case 'Triage inbox':
                    process_triage()
                case 'Capture new item':
                    capture_item()
                case 'Update project':
                    update_entry()
                case 'Mark done':
                    mark_done()
                case '12-Week Goals':
                    list_12_week_entries(verbose=verbose)
                    pause()
                case 'Filter by context':
                    from project_manager.notion.client import (  # noqa: PLC0415
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
