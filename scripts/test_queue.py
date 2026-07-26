"""Regression tests for scripts/queue.py."""

import re
from datetime import datetime
from pathlib import Path

import pytest

from queue import (
    action_complete,
    list_titles,
    parse_queue_file,
    remove_item_from_queue,
)

TWO_ITEM_QUEUE = (
    '# Queue\n'
    '\n'
    '## First Item\n'
    '\n'
    'First body text.\n'
    '\n'
    '## Second Item\n'
    '\n'
    'Second body text.\n'
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


@pytest.mark.parametrize(
    ('body', 'expected'),
    [
        (TWO_ITEM_QUEUE, ['First Item', 'Second Item']),
        ('# Queue\n', []),
        ('# Queue\n\n## Only One\n\nbody\n', ['Only One']),
    ],
)
def test_list_titles_returns_one_title_per_item(
    tmp_path: Path,
    body: str,
    expected: list[str],
) -> None:
    assert list_titles(_write_queue(tmp_path, body)) == expected


def test_list_titles_preserves_titles_containing_markup(
    tmp_path: Path,
) -> None:
    """fzf matches on the exact string queue.py later looks up."""
    body = '# Queue\n\n## Add `.queue` to pass -- now\n\nbody\n'

    assert list_titles(_write_queue(tmp_path, body)) == [
        'Add `.queue` to pass -- now',
    ]


@pytest.mark.parametrize(
    ('start_time', 'end_time'),
    [
        (None, None),
        (None, '2026-01-01T01:00:00'),
        ('2026-01-01T00:00:00', None),
    ],
)
def test_action_complete_defaults_missing_timestamps_to_now(
    tmp_path: Path,
    start_time: str | None,
    end_time: str | None,
) -> None:
    queue_path = _write_queue(tmp_path, TWO_ITEM_QUEUE)
    complete_path = tmp_path / '.queue-complete'
    before = datetime.now().replace(microsecond=0)

    action_complete(
        queue_path,
        complete_path,
        'First Item',
        start_time,
        end_time,
    )

    written = complete_path.read_text()
    stamps = re.findall(r'- (?:Started|Completed): (.+)', written)
    given_times = (start_time, end_time)
    assert len(stamps) == len(given_times)

    for given, stamp in zip(given_times, stamps, strict=True):
        parsed = datetime.fromisoformat(stamp)
        if given is None:
            assert parsed >= before
        else:
            assert parsed == datetime.fromisoformat(given)

    assert [item.title for item in parse_queue_file(queue_path)] == [
        'Second Item',
    ]
