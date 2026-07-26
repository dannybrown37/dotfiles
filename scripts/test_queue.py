"""Regression tests for scripts/queue.py."""

import re
from datetime import datetime
from pathlib import Path

import pytest

from queue import (
    IN_PROGRESS_MARKER,
    MAX_COMPLETED_CONTENT_LINES,
    action_claim,
    action_complete,
    list_titles,
    parse_queue_file,
    remove_item_from_queue,
    trim_content,
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
    'end_time',
    [None, '2026-01-01T01:00:00'],
)
def test_action_complete_defaults_missing_end_time_to_now(
    tmp_path: Path,
    end_time: str | None,
) -> None:
    queue_path = _write_queue(tmp_path, TWO_ITEM_QUEUE)
    complete_path = tmp_path / '.queue-complete'
    before = datetime.now().replace(microsecond=0)

    action_complete(
        queue_path,
        complete_path,
        'First Item',
        end_time,
    )

    written = complete_path.read_text()
    stamps = re.findall(r'- Completed: (.+)', written)
    assert len(stamps) == 1

    parsed = datetime.fromisoformat(stamps[0])
    if end_time is None:
        assert parsed >= before
    else:
        assert parsed == datetime.fromisoformat(end_time)

    assert [item.title for item in parse_queue_file(queue_path)] == [
        'Second Item',
    ]


def test_action_complete_does_not_write_started_timestamp(
    tmp_path: Path,
) -> None:
    queue_path = _write_queue(tmp_path, TWO_ITEM_QUEUE)
    complete_path = tmp_path / '.queue-complete'

    action_complete(queue_path, complete_path, 'First Item')

    assert 'Started' not in complete_path.read_text()


def test_parse_queue_file_detects_in_progress_marker(
    tmp_path: Path,
) -> None:
    queue_path = _write_queue(
        tmp_path,
        f'# Queue\n\n## First Item{IN_PROGRESS_MARKER}\n\nbody\n',
    )

    items = parse_queue_file(queue_path)

    assert items[0].title == f'First Item{IN_PROGRESS_MARKER}'
    assert items[0].in_progress is True


def test_parse_queue_file_treats_unmarked_item_as_not_in_progress(
    tmp_path: Path,
) -> None:
    queue_path = _write_queue(tmp_path, TWO_ITEM_QUEUE)

    items = parse_queue_file(queue_path)

    assert all(not item.in_progress for item in items)


def test_action_claim_adds_marker_to_queue_file(
    tmp_path: Path,
) -> None:
    queue_path = _write_queue(tmp_path, TWO_ITEM_QUEUE)

    action_claim(queue_path, 'First Item')

    items = parse_queue_file(queue_path)
    first = next(item for item in items if 'First Item' in item.title)
    second = next(item for item in items if item.title == 'Second Item')

    assert first.in_progress is True
    assert second.in_progress is False


def test_action_claim_errors_when_item_not_found(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    queue_path = _write_queue(tmp_path, TWO_ITEM_QUEUE)

    with pytest.raises(SystemExit) as exc_info:
        action_claim(queue_path, 'Nonexistent Item')

    assert exc_info.value.code == 1
    assert 'not found' in capsys.readouterr().err


def test_action_claim_errors_when_item_already_in_progress(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    queue_path = _write_queue(tmp_path, TWO_ITEM_QUEUE)
    action_claim(queue_path, 'First Item')

    with pytest.raises(SystemExit) as exc_info:
        action_claim(queue_path, 'First Item')

    assert exc_info.value.code == 1
    assert 'already in progress' in capsys.readouterr().err


@pytest.mark.parametrize(
    ('line_count', 'expect_trimmed'),
    [
        (50, False),
        (51, True),
        (1500, True),
    ],
)
def test_trim_content_only_trims_over_max_lines(
    line_count: int,
    *,
    expect_trimmed: bool,
) -> None:
    content = '\n'.join(f'line {n}' for n in range(line_count))

    result = trim_content(content)

    if expect_trimmed:
        max_lines = MAX_COMPLETED_CONTENT_LINES
        assert len(result.split('\n')) > max_lines
        assert f'Trimmed from {line_count} to {max_lines}' in result
        assert 'line 0' in result
        assert f'line {line_count - 1}' not in result
    else:
        assert result == content


def test_action_complete_trims_oversized_content_in_complete_file(
    tmp_path: Path,
) -> None:
    huge_body = '\n'.join(f'line {n}' for n in range(1500))
    queue_path = _write_queue(
        tmp_path,
        f'# Queue\n\n## Huge Item\n\n{huge_body}\n',
    )
    complete_path = tmp_path / '.queue-complete'

    action_complete(queue_path, complete_path, 'Huge Item')

    completed = complete_path.read_text()
    assert 'Trimmed from 1500 to 50 lines' in completed
    assert 'line 1499' not in completed


def test_action_complete_does_not_trim_short_content(
    tmp_path: Path,
) -> None:
    queue_path = _write_queue(tmp_path, TWO_ITEM_QUEUE)
    complete_path = tmp_path / '.queue-complete'

    action_complete(queue_path, complete_path, 'First Item')

    completed = complete_path.read_text()
    assert 'Trimmed' not in completed
    assert 'First body text.' in completed


def test_action_complete_matches_item_regardless_of_marker(
    tmp_path: Path,
) -> None:
    queue_path = _write_queue(tmp_path, TWO_ITEM_QUEUE)
    complete_path = tmp_path / '.queue-complete'
    action_claim(queue_path, 'First Item')

    action_complete(queue_path, complete_path, 'First Item')

    remaining_titles = [item.title for item in parse_queue_file(queue_path)]
    assert remaining_titles == ['Second Item']
    completed = complete_path.read_text()
    assert 'First Item' in completed
    assert IN_PROGRESS_MARKER not in completed
