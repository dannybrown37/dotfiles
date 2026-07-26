"""Regression tests for scripts/queue.py."""

from pathlib import Path

from queue import (
    action_complete,
    parse_queue_file,
    remove_item_from_queue,
)


def _write_queue(tmp_path: Path, body: str) -> Path:
    queue_path = tmp_path / '.queue'
    queue_path.write_text(body)
    return queue_path


def test_remove_item_from_queue_drops_item_with_blank_line_before_body(
    tmp_path: Path,
) -> None:
    queue_path = _write_queue(
        tmp_path,
        '# Queue\n'
        '\n'
        '## First Item\n'
        '\n'
        'First body text.\n'
        '\n'
        '## Second Item\n'
        '\n'
        'Second body text.\n',
    )

    items = parse_queue_file(queue_path)
    first_item = next(item for item in items if item.title == 'First Item')

    remove_item_from_queue(queue_path, first_item)

    remaining = parse_queue_file(queue_path)
    remaining_titles = [item.title for item in remaining]

    assert remaining_titles == ['Second Item']


def test_action_complete_removes_item_from_active_queue(
    tmp_path: Path,
) -> None:
    queue_path = _write_queue(
        tmp_path,
        '# Queue\n'
        '\n'
        '## First Item\n'
        '\n'
        'First body text.\n'
        '\n'
        '## Second Item\n'
        '\n'
        'Second body text.\n',
    )
    complete_path = tmp_path / '.queue-complete'

    action_complete(
        queue_path,
        complete_path,
        'First Item',
        '2026-01-01T00:00:00',
        '2026-01-01T01:00:00',
    )

    remaining = parse_queue_file(queue_path)
    remaining_titles = [item.title for item in remaining]

    assert remaining_titles == ['Second Item']
    assert 'First Item' in complete_path.read_text()
