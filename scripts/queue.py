#!/usr/bin/env python3
"""Queue management for AI-assisted work items."""

import re
import sys
from datetime import datetime
from pathlib import Path

IN_PROGRESS_MARKER = ' [in-progress]'
MAX_COMPLETED_CONTENT_LINES = 50


class QueueItem:
    """A single work item from the queue."""

    def __init__(self, title: str, content: str, raw_section: str) -> None:
        self.title = title
        self.content = content
        self.raw_section = raw_section

    @property
    def in_progress(self) -> bool:
        return self.title.endswith(IN_PROGRESS_MARKER.strip())

    def __repr__(self) -> str:
        lines = self.content.split('\n')
        preview = lines[0][:60] if lines else ''
        return f'{self.title}\n  {preview}...'


def strip_in_progress_marker(title: str) -> str:
    """Drop the trailing in-progress marker, if present, from a title."""
    marker = IN_PROGRESS_MARKER.strip()
    if title.endswith(marker):
        return title[: -len(marker)].rstrip()
    return title


def find_item(items: list[QueueItem], title: str) -> QueueItem | None:
    """Find an item by title, ignoring whether it's marked in-progress."""
    target = strip_in_progress_marker(title)
    return next(
        (
            item
            for item in items
            if strip_in_progress_marker(item.title) == target
        ),
        None,
    )


def parse_queue_file(file_path: Path) -> list[QueueItem]:
    """Parse .queue markdown file and extract items under ## headers."""
    if not file_path.exists():
        return []

    content = file_path.read_text()
    lines = content.split('\n')

    items = []
    current_title = None
    current_content = []
    current_raw_lines = []

    def finalize_current_item() -> None:
        item_content = '\n'.join(current_content).strip()
        raw_section = '\n'.join(current_raw_lines)
        items.append(QueueItem(current_title, item_content, raw_section))

    for line in lines:
        if line.startswith('## '):
            if current_title is not None:
                finalize_current_item()
            current_title = line[3:].strip()
            current_content = []
            current_raw_lines = [line]
        elif current_title is not None:
            current_content.append(line)
            current_raw_lines.append(line)

    if current_title is not None:
        finalize_current_item()

    return items


def remove_item_from_queue(queue_path: Path, item: QueueItem) -> None:
    """Remove an item from the queue file."""
    if not queue_path.exists():
        return

    content = queue_path.read_text()
    updated = content.replace(item.raw_section, '', 1)
    updated = re.sub(r'\n{3,}', '\n\n', updated).strip()
    queue_path.write_text(updated + '\n')


def trim_content(
    content: str,
    max_lines: int = MAX_COMPLETED_CONTENT_LINES,
) -> str:
    """Cap content at max_lines and note the trim so it's unambiguous."""
    lines = content.split('\n')
    if len(lines) <= max_lines:
        return content

    kept = '\n'.join(lines[:max_lines])
    note = f'_[Trimmed from {len(lines)} to {max_lines} lines]_'
    return f'{kept}\n\n{note}'


def add_to_completed(
    complete_path: Path,
    item: QueueItem,
    end_time: datetime,
) -> None:
    """Add completed item to .queue-complete with a completion timestamp."""
    if not complete_path.exists():
        complete_path.write_text('# Completed\n\n')

    existing = complete_path.read_text()

    end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
    title = strip_in_progress_marker(item.title)

    entry = f"""## {title}
- Completed: {end_str}

{trim_content(item.content)}

---

"""

    new_content = existing.rstrip() + '\n\n' + entry
    complete_path.write_text(new_content)


def mark_item_in_progress(queue_path: Path, item: QueueItem) -> None:
    """Append the in-progress marker to an item's header in .queue."""
    content = queue_path.read_text()
    old_header = f'## {item.title}'
    new_header = f'## {item.title}{IN_PROGRESS_MARKER}'
    new_raw_section = new_header + item.raw_section[len(old_header) :]
    updated = content.replace(item.raw_section, new_raw_section, 1)
    queue_path.write_text(updated)


def get_next_item(
    queue_path: Path | None = None,
) -> QueueItem | None:
    """Get the first item from .queue file."""
    if queue_path is None:
        queue_path = Path.cwd() / '.queue'

    items = parse_queue_file(queue_path)
    return items[0] if items else None


def list_items(
    queue_path: Path | None = None,
    limit: int = 5,
) -> list[QueueItem]:
    """Get first N items from .queue file."""
    if queue_path is None:
        queue_path = Path.cwd() / '.queue'

    items = parse_queue_file(queue_path)
    return items[:limit]


def list_titles(queue_path: Path) -> list[str]:
    """Every queued title, one per item, for an external picker to offer."""
    return [item.title for item in parse_queue_file(queue_path)]


def show_item(item: QueueItem) -> None:
    """Display an item for review."""
    print(f"\n{'='*70}")
    print(f'📋 {item.title}')
    print(f"{'='*70}")
    print(item.content)
    print(f"{'='*70}\n")


def action_next(queue_path: Path) -> None:
    """Show next item for discussion."""
    item = get_next_item(queue_path)
    if item:
        show_item(item)
        print(f'Proceed with: {item.title}? (y/n)')
    else:
        print('✓ Queue is empty!')


def action_list(queue_path: Path) -> None:
    """List next items."""
    items = list_items(queue_path, limit=10)
    if not items:
        print('✓ Queue is empty!')
    else:
        print(f'\n📋 Next {len(items)} items:\n')
        for i, item in enumerate(items, 1):
            print(f'{i}. {item.title}')
            if item.content:
                lines = item.content.split('\n')
                preview = lines[0][:60]
                print(f'   {preview}')
        print()


def action_titles(queue_path: Path) -> None:
    """Print bare titles, one per line, for piping into fzf."""
    for title in list_titles(queue_path):
        print(title)


def action_claim(queue_path: Path, item_title: str) -> None:
    """Mark an item in-progress so other agents know it's taken."""
    items = parse_queue_file(queue_path)
    item = find_item(items, item_title)
    if not item:
        msg = f"Error: Item '{item_title}' not found"
        print(msg, file=sys.stderr)
        sys.exit(1)

    if item.in_progress:
        title = strip_in_progress_marker(item.title)
        msg = f"Error: '{title}' is already in progress"
        print(msg, file=sys.stderr)
        sys.exit(1)

    mark_item_in_progress(queue_path, item)
    print(f'→ Claimed: {item.title}')


def action_complete(
    queue_path: Path,
    complete_path: Path,
    item_title: str,
    end_time: str | None = None,
) -> None:
    """Mark item complete and move to .queue-complete."""
    items = parse_queue_file(queue_path)
    item = find_item(items, item_title)
    if not item:
        msg = f"Error: Item '{item_title}' not found"
        print(msg, file=sys.stderr)
        sys.exit(1)

    end_dt = datetime.fromisoformat(end_time) if end_time else datetime.now()

    add_to_completed(complete_path, item, end_dt)
    remove_item_from_queue(queue_path, item)
    print(f'✓ Completed: {strip_in_progress_marker(item.title)}')


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Queue management for Claude Code',
    )
    parser.add_argument(
        'action',
        choices=['next', 'list', 'titles', 'claim', 'complete'],
        help='Queue action to perform',
    )
    parser.add_argument(
        '--queue-path',
        type=Path,
        default=None,
        help='Path to .queue file (default: ./.queue)',
    )
    parser.add_argument(
        '--complete-path',
        type=Path,
        default=None,
        help='Path to .queue-complete file (default: ./.queue-complete)',
    )
    parser.add_argument(
        '--end-time',
        type=str,
        help='ISO format completion time for complete action (default: now)',
    )
    parser.add_argument(
        '--item-title',
        type=str,
        help='Title of item to claim or complete',
    )

    args = parser.parse_args()

    queue_path = args.queue_path or Path.cwd() / '.queue'
    complete_path = args.complete_path or Path.cwd() / '.queue-complete'

    if args.action == 'next':
        action_next(queue_path)
    elif args.action == 'list':
        action_list(queue_path)
    elif args.action == 'titles':
        action_titles(queue_path)
    elif args.action in ('claim', 'complete'):
        if not args.item_title:
            # The shell wrapper picks a title with fzf; anything else gets the
            # list so the exact string is easy to copy.
            print('Error: --item-title required', file=sys.stderr)
            for title in list_titles(queue_path):
                print(f'  {title}', file=sys.stderr)
            sys.exit(1)

        if args.action == 'claim':
            action_claim(queue_path, args.item_title)
        else:
            action_complete(
                queue_path,
                complete_path,
                args.item_title,
                args.end_time,
            )


if __name__ == '__main__':
    main()
