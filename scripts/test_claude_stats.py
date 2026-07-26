"""Tests for scripts/claude_stats.py."""

import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pytest

from claude_stats import (
    UsageStats,
    collect_stats,
    format_report,
    supports_color,
)

STAMP = '2026-07-26T09:00:00.000Z'
REPLY_OUTPUT_TOKENS = 10
REPLY_CACHE_READ_TOKENS = 100
LONG_PROMPT_CHARS = 500
EXPECTED_GENUINE_PROMPTS = 2
EXPECTED_ADDED_LINES = 2
EXPECTED_REMOVED_LINES = 1
EXPECTED_BASH_USES = 2
NARROW_WIDTH = 60
WIDE_WIDTH = 200


def _assistant(**overrides: object) -> dict:
    record = {
        'type': 'assistant',
        'sessionId': 's1',
        'timestamp': STAMP,
        'message': {
            'model': 'claude-opus-5',
            'content': [{'type': 'text', 'text': 'hi'}],
            'usage': {
                'output_tokens': 10,
                'cache_read_input_tokens': 100,
                'input_tokens': 1,
            },
        },
    }
    record.update(overrides)
    return record


def _prompt(text: str = 'do a thing', **overrides: object) -> dict:
    record = {
        'type': 'user',
        'sessionId': 's1',
        'timestamp': STAMP,
        'message': {'role': 'user', 'content': text},
    }
    record.update(overrides)
    return record


def _write_log(tmp_path: Path, records: list[dict], name: str = 'a') -> Path:
    path = tmp_path / f'{name}.jsonl'
    path.write_text(
        ''.join(json.dumps(record) + '\n' for record in records),
    )
    return path


def test_counts_only_genuine_prompts(tmp_path: Path) -> None:
    """Tool results and meta records outnumber prompts ~6:1 in real logs."""
    _write_log(
        tmp_path,
        [
            _prompt('real one'),
            _prompt('tool output', toolUseResult={'stdout': 'x'}),
            _prompt('injected context', isMeta=True),
            _prompt(
                'with blocks',
                message={
                    'role': 'user',
                    'content': [{'type': 'text', 'text': 'blocks'}],
                },
            ),
        ],
    )

    stats = collect_stats([tmp_path])

    assert stats.prompts == EXPECTED_GENUINE_PROMPTS


def test_sums_token_usage_and_counts_replies(tmp_path: Path) -> None:
    replies = [_assistant(), _assistant()]
    _write_log(tmp_path, replies)

    stats = collect_stats([tmp_path])

    assert stats.replies == len(replies)
    assert stats.output_tokens == len(replies) * REPLY_OUTPUT_TOKENS
    assert stats.cache_read_tokens == len(replies) * REPLY_CACHE_READ_TOKENS


def test_counts_lines_added_and_removed_from_patches(tmp_path: Path) -> None:
    patch = [
        {'lines': ['+added one', '-removed one', ' context', '+added two']},
    ]
    _write_log(
        tmp_path,
        [_prompt('edit', toolUseResult={'structuredPatch': patch})],
    )

    stats = collect_stats([tmp_path])

    assert stats.lines_added == EXPECTED_ADDED_LINES
    assert stats.lines_removed == EXPECTED_REMOVED_LINES


def test_tallies_models_tools_and_thinking_blocks(tmp_path: Path) -> None:
    _write_log(
        tmp_path,
        [
            _assistant(
                message={
                    'model': 'claude-opus-5',
                    'usage': {},
                    'content': [
                        {'type': 'thinking', 'thinking': '...'},
                        {'type': 'tool_use', 'name': 'Bash'},
                    ],
                },
            ),
            _assistant(
                message={
                    'model': 'claude-haiku-4-5-20251001',
                    'usage': {},
                    'content': [{'type': 'tool_use', 'name': 'Bash'}],
                },
            ),
        ],
    )

    stats = collect_stats([tmp_path])

    assert stats.thinking_blocks == 1
    assert stats.tools['Bash'] == EXPECTED_BASH_USES
    assert stats.models['claude-opus-5'] == 1
    assert stats.models['claude-haiku-4-5-20251001'] == 1


def test_groups_output_tokens_by_day(tmp_path: Path) -> None:
    _write_log(
        tmp_path,
        [
            _assistant(timestamp='2026-07-25T23:00:00.000Z'),
            _assistant(timestamp='2026-07-26T01:00:00.000Z'),
            _assistant(timestamp='2026-07-26T02:00:00.000Z'),
        ],
    )

    stats = collect_stats([tmp_path])

    assert stats.output_tokens_by_day == {
        date(2026, 7, 25): REPLY_OUTPUT_TOKENS,
        date(2026, 7, 26): 2 * REPLY_OUTPUT_TOKENS,
    }


@pytest.mark.parametrize(
    ('since', 'until', 'expected_replies'),
    [
        (None, None, 3),
        (date(2026, 7, 26), None, 2),
        (None, date(2026, 7, 25), 1),
        (date(2026, 7, 26), date(2026, 7, 26), 2),
    ],
)
def test_date_filters_bound_the_window(
    tmp_path: Path,
    since: date | None,
    until: date | None,
    expected_replies: int,
) -> None:
    _write_log(
        tmp_path,
        [
            _assistant(timestamp='2026-07-25T12:00:00.000Z'),
            _assistant(timestamp='2026-07-26T12:00:00.000Z'),
            _assistant(timestamp='2026-07-26T13:00:00.000Z'),
        ],
    )

    stats = collect_stats([tmp_path], since=since, until=until)

    assert stats.replies == expected_replies


def test_counts_distinct_sessions_and_subagent_runs(tmp_path: Path) -> None:
    _write_log(tmp_path, [_assistant(sessionId='s1')], name='one')
    _write_log(tmp_path, [_assistant(sessionId='s2')], name='two')
    subagents = tmp_path / 'subagents'
    subagents.mkdir()
    _write_log(subagents, [_assistant(sessionId='s3')], name='agent')

    stats = collect_stats([tmp_path])

    assert stats.sessions == len({'s1', 's2', 's3'})
    assert stats.subagent_runs == 1


def test_skips_malformed_lines_without_failing(tmp_path: Path) -> None:
    path = tmp_path / 'a.jsonl'
    path.write_text(
        '\n'.join(
            [
                'not json at all',
                json.dumps(_assistant()),
                '{"truncated": ',
                '',
            ],
        ),
    )

    stats = collect_stats([tmp_path])

    assert stats.replies == 1


def test_tracks_longest_prompt(tmp_path: Path) -> None:
    _write_log(tmp_path, [_prompt('short'), _prompt('x' * LONG_PROMPT_CHARS)])

    stats = collect_stats([tmp_path])

    assert stats.longest_prompt_chars == LONG_PROMPT_CHARS


def _stats_with_full_report_data() -> UsageStats:
    return UsageStats(
        session_ids={'s1'},
        prompts=5,
        replies=5,
        output_tokens=1000,
        input_tokens=500,
        cache_read_tokens=200,
        cache_write_tokens=100,
        lines_added=10,
        lines_removed=3,
        thinking_blocks=2,
        subagent_runs=1,
        longest_prompt_chars=42,
        models=Counter(
            {'claude-opus-5': 3, 'claude-haiku-4-5-20251001': 2},
        ),
        tools=Counter({'Bash': 4, 'Read': 2}),
        first_seen=datetime.fromisoformat(STAMP.replace('Z', '+00:00')),
        last_seen=datetime.fromisoformat(STAMP.replace('Z', '+00:00')),
    )


def _lines_mentioning_both(
    report: str,
    left_needle: str,
    right_needle: str,
) -> list[str]:
    return [
        line
        for line in report.split('\n')
        if left_needle in line and right_needle in line
    ]


def test_format_report_stacks_totals_and_tokens_when_narrow() -> None:
    report = format_report(
        _stats_with_full_report_data(),
        width=NARROW_WIDTH,
        color=False,
    )

    assert not _lines_mentioning_both(report, 'sessions', 'tokens out')


def test_format_report_columns_totals_and_tokens_when_wide() -> None:
    report = format_report(
        _stats_with_full_report_data(),
        width=WIDE_WIDTH,
        color=False,
    )

    assert _lines_mentioning_both(report, 'sessions', 'tokens out')


def test_format_report_stacks_models_and_tools_when_narrow() -> None:
    report = format_report(
        _stats_with_full_report_data(),
        width=NARROW_WIDTH,
        color=False,
    )

    assert not _lines_mentioning_both(report, 'model mix', 'top tools')


def test_format_report_columns_models_and_tools_when_wide() -> None:
    report = format_report(
        _stats_with_full_report_data(),
        width=WIDE_WIDTH,
        color=False,
    )

    assert _lines_mentioning_both(report, 'model mix', 'top tools')


def test_format_report_includes_ansi_codes_when_color_enabled() -> None:
    report = format_report(
        _stats_with_full_report_data(),
        width=WIDE_WIDTH,
        color=True,
    )

    assert '\x1b[' in report


def test_format_report_omits_ansi_codes_when_color_disabled() -> None:
    report = format_report(
        _stats_with_full_report_data(),
        width=WIDE_WIDTH,
        color=False,
    )

    assert '\x1b[' not in report


@pytest.mark.parametrize(
    ('is_a_tty', 'no_color_env', 'expected'),
    [
        (True, None, True),
        (False, None, False),
        (True, '1', False),
    ],
)
def test_supports_color_reflects_tty_and_no_color_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    is_a_tty: bool,
    no_color_env: str | None,
    expected: bool,
) -> None:
    monkeypatch.setattr('sys.stdout.isatty', lambda: is_a_tty)
    if no_color_env is None:
        monkeypatch.delenv('NO_COLOR', raising=False)
    else:
        monkeypatch.setenv('NO_COLOR', no_color_env)

    assert supports_color() is expected
