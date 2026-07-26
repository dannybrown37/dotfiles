#!/usr/bin/env python3
"""Queue management for AI-assisted work items."""

import re
import sys
from datetime import datetime
from pathlib import Path


class QueueItem:
    """A single work item from the queue."""

    def __init__(self, title: str, content: str, raw_section: str) -> None:
        self.title = title
        self.content = content
        self.raw_section = raw_section

    def __repr__(self) -> str:
        lines = self.content.split('\n')
        preview = lines[0][:60] if lines else ''
        return f'{self.title}\n  {preview}...'


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


def add_to_completed(
    complete_path: Path,
    item: QueueItem,
    start_time: datetime,
    end_time: datetime,
) -> None:
    """Add completed item to .queue-complete with timestamps."""
    if not complete_path.exists():
        complete_path.write_text('# Completed\n\n')

    existing = complete_path.read_text()

    start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')

    entry = f"""## {item.title}
- Started: {start_str}
- Completed: {end_str}

{item.content}

---

"""

    new_content = existing.rstrip() + '\n\n' + entry
    complete_path.write_text(new_content)


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


def action_complete(
    queue_path: Path,
    complete_path: Path,
    item_title: str,
    start_time: str,
    end_time: str,
) -> None:
    """Mark item complete and move to .queue-complete."""
    items = parse_queue_file(queue_path)
    item = next((i for i in items if i.title == item_title), None)
    if not item:
        msg = f"Error: Item '{item_title}' not found"
        print(msg, file=sys.stderr)
        sys.exit(1)

    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)

    add_to_completed(complete_path, item, start_dt, end_dt)
    remove_item_from_queue(queue_path, item)
    print(f'✓ Completed: {item.title}')


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Queue management for Claude Code',
    )
    parser.add_argument(
        'action',
        choices=['next', 'list', 'complete'],
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
        '--start-time',
        type=str,
        help='ISO format start time for --complete action',
    )
    parser.add_argument(
        '--end-time',
        type=str,
        help='ISO format end time for --complete action',
    )
    parser.add_argument(
        '--item-title',
        type=str,
        help='Title of item to complete',
    )

    args = parser.parse_args()

    queue_path = args.queue_path or Path.cwd() / '.queue'
    complete_path = args.complete_path or Path.cwd() / '.queue-complete'

    if args.action == 'next':
        action_next(queue_path)
    elif args.action == 'list':
        action_list(queue_path)
    elif args.action == 'complete':
        if not args.item_title:
            msg = '--item-title required for complete action'
            print(f'Error: {msg}', file=sys.stderr)
            sys.exit(1)
        if not args.start_time or not args.end_time:
            msg = '--start-time and --end-time required for complete action'
            print(f'Error: {msg}', file=sys.stderr)
            sys.exit(1)

        action_complete(
            queue_path,
            complete_path,
            args.item_title,
            args.start_time,
            args.end_time,
        )


if __name__ == '__main__':
    main()
