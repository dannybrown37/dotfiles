#!/usr/bin/env python3
"""Aggregate Claude Code session logs into usage statistics.

Reads the JSONL transcripts under ~/.claude/projects and reports totals on
demand. Nothing is written or cached -- every run re-reads the logs, so the
numbers only cover transcripts still present on this machine.
"""

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from collections.abc import Iterator

DEFAULT_LOG_ROOT = Path.home() / '.claude' / 'projects'
SUBAGENT_DIR = 'subagents'
FALLBACK_TERMINAL_SIZE = (80, 24)
COLUMN_GAP = 4

RESET = '\x1b[0m'
BOLD = '\x1b[1m'
DIM = '\x1b[2m'
CYAN = '\x1b[36m'


@dataclass
class UsageStats:
    """Totals across every transcript that matched the requested window."""

    session_ids: set[str] = field(default_factory=set)
    prompts: int = 0
    replies: int = 0
    output_tokens: int = 0
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    thinking_blocks: int = 0
    subagent_runs: int = 0
    longest_prompt_chars: int = 0
    models: Counter = field(default_factory=Counter)
    tools: Counter = field(default_factory=Counter)
    output_tokens_by_day: dict[date, int] = field(default_factory=dict)
    first_seen: datetime | None = None
    last_seen: datetime | None = None

    @property
    def sessions(self) -> int:
        return len(self.session_ids)

    @property
    def cache_hit_ratio(self) -> float | None:
        """Share of input tokens served from cache rather than sent fresh."""
        denominator = self.cache_read_tokens + self.input_tokens
        if denominator == 0:
            return None
        return self.cache_read_tokens / denominator

    @property
    def cache_efficiency(self) -> float | None:
        """Cache reads per cache write -- how many times a write paid off."""
        if self.cache_write_tokens == 0:
            return None
        return self.cache_read_tokens / self.cache_write_tokens


def find_logs(roots: list[Path]) -> list[Path]:
    """Every transcript under the given roots, newest last."""
    logs: list[Path] = []
    for root in roots:
        if root.is_file():
            logs.append(root)
        elif root.is_dir():
            logs.extend(sorted(root.rglob('*.jsonl')))
    return logs


def iter_records(path: Path) -> Iterator[dict]:
    """Yield parsed records, skipping lines left truncated by a crash."""
    with path.open(encoding='utf-8', errors='replace') as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return None


def is_prompt(record: dict) -> bool:
    """True for text the human typed, not a tool result or injected note."""
    if record.get('type') != 'user':
        return False
    if record.get('toolUseResult') is not None or record.get('isMeta'):
        return False

    content = record.get('message', {}).get('content')
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return any(
            block.get('type') == 'text'
            for block in content
            if isinstance(block, dict)
        )
    return False


def prompt_text(record: dict) -> str:
    content = record.get('message', {}).get('content')
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(
            block.get('text', '')
            for block in content
            if isinstance(block, dict)
        )
    return ''


def count_patch_lines(patch: object) -> tuple[int, int]:
    """Added and removed line counts from an Edit/Write structuredPatch."""
    added = removed = 0
    if not isinstance(patch, list):
        return added, removed

    for hunk in patch:
        if not isinstance(hunk, dict):
            continue
        for line in hunk.get('lines', []):
            if not isinstance(line, str):
                continue
            if line.startswith('+'):
                added += 1
            elif line.startswith('-'):
                removed += 1
    return added, removed


def in_window(
    stamp: datetime | None,
    since: date | None,
    until: date | None,
) -> bool:
    if stamp is None:
        return since is None and until is None
    day = stamp.date()
    if since and day < since:
        return False
    return not (until and day > until)


def tally_assistant(stats: UsageStats, record: dict, day: date | None) -> None:
    message = record.get('message', {})
    stats.replies += 1

    model = message.get('model')
    if model:
        stats.models[model] += 1

    usage = message.get('usage') or {}
    output = usage.get('output_tokens', 0) or 0
    stats.output_tokens += output
    stats.input_tokens += usage.get('input_tokens', 0) or 0
    stats.cache_read_tokens += usage.get('cache_read_input_tokens', 0) or 0
    stats.cache_write_tokens += (
        usage.get('cache_creation_input_tokens', 0) or 0
    )

    if day is not None and output:
        stats.output_tokens_by_day[day] = (
            stats.output_tokens_by_day.get(day, 0) + output
        )

    for block in message.get('content', []):
        if not isinstance(block, dict):
            continue
        kind = block.get('type')
        if kind == 'thinking':
            stats.thinking_blocks += 1
        elif kind == 'tool_use':
            stats.tools[block.get('name', 'unknown')] += 1


def track_span(stats: UsageStats, stamp: datetime) -> None:
    if stats.first_seen is None or stamp < stats.first_seen:
        stats.first_seen = stamp
    if stats.last_seen is None or stamp > stats.last_seen:
        stats.last_seen = stamp


def tally_record(stats: UsageStats, record: dict, day: date | None) -> None:
    if record.get('type') == 'assistant':
        tally_assistant(stats, record, day)
    elif is_prompt(record):
        stats.prompts += 1
        stats.longest_prompt_chars = max(
            stats.longest_prompt_chars,
            len(prompt_text(record)),
        )

    result = record.get('toolUseResult')
    if isinstance(result, dict):
        added, removed = count_patch_lines(result.get('structuredPatch'))
        stats.lines_added += added
        stats.lines_removed += removed


def collect_stats(
    roots: list[Path],
    since: date | None = None,
    until: date | None = None,
) -> UsageStats:
    """Walk every transcript under roots and total up the interesting bits."""
    stats = UsageStats()

    for path in find_logs(roots):
        is_subagent = path.parent.name == SUBAGENT_DIR
        counted_subagent = False

        for record in iter_records(path):
            stamp = parse_timestamp(record.get('timestamp'))
            if not in_window(stamp, since, until):
                continue

            if stamp:
                track_span(stats, stamp)

            session = record.get('sessionId') or record.get('session_id')
            if session:
                stats.session_ids.add(session)

            if is_subagent and not counted_subagent:
                stats.subagent_runs += 1
                counted_subagent = True

            tally_record(stats, record, stamp.date() if stamp else None)

    return stats


def humanize(value: int) -> str:
    scales = ((1_000_000_000, 'B'), (1_000_000, 'M'), (1_000, 'K'))
    for limit, suffix in scales:
        if value >= limit:
            return f'{value / limit:.1f}{suffix}'
    return str(value)


def supports_color() -> bool:
    """Whether the terminal we're writing to can render ANSI colors."""
    return sys.stdout.isatty() and not os.environ.get('NO_COLOR')


def colorize(text: str, *codes: str, color: bool) -> str:
    if not color:
        return text
    return f'{"".join(codes)}{text}{RESET}'


def merge_side_by_side(
    left: list[str],
    right: list[str],
    width: int,
) -> list[str]:
    """Lay two report blocks side by side if they both fit in width.

    Falls back to stacking them (left block, blank line, right block)
    when the terminal is too narrow for both columns.
    """
    if not left or not right:
        return left + right

    left_width = max(len(line) for line in left)
    right_width = max(len(line) for line in right)
    if left_width + COLUMN_GAP + right_width > width:
        return [*left, '', *right]

    row_count = max(len(left), len(right))
    padded_left = [line.ljust(left_width) for line in left]
    padded_left += [' ' * left_width] * (row_count - len(padded_left))
    padded_right = right + [''] * (row_count - len(right))
    gap = ' ' * COLUMN_GAP
    return [
        f'{lft}{gap}{rgt}'
        for lft, rgt in zip(padded_left, padded_right, strict=True)
    ]


def report_span(stats: UsageStats) -> str:
    if not (stats.first_seen and stats.last_seen):
        return 'no transcripts found'
    return (
        f'{stats.first_seen:%Y-%m-%d} - {stats.last_seen:%Y-%m-%d}'
        f'  ({len(stats.output_tokens_by_day)} active days)'
    )


def totals_and_tokens_lines(
    stats: UsageStats,
) -> tuple[list[str], list[str]]:
    totals = (
        ('sessions', stats.sessions),
        ('prompts', stats.prompts),
        ('replies', stats.replies),
        ('thinking blocks', stats.thinking_blocks),
        ('subagent runs', stats.subagent_runs),
        ('lines added', stats.lines_added),
        ('lines removed', stats.lines_removed),
    )
    totals_lines = [f'  {label:<22} {value:>12,}' for label, value in totals]

    tokens = (
        ('tokens out', stats.output_tokens),
        ('tokens in', stats.input_tokens),
        ('cache read', stats.cache_read_tokens),
        ('cache written', stats.cache_write_tokens),
    )
    tokens_lines = [
        f'  {label:<22} {humanize(value):>12}' for label, value in tokens
    ]

    return totals_lines, tokens_lines


def cache_efficiency_lines(stats: UsageStats) -> list[str]:
    lines = []
    if stats.cache_hit_ratio is not None:
        lines.append(
            f'  {"cache hit ratio":<22} {stats.cache_hit_ratio:>11.1%} '
            '  (cache_read / (cache_read + input))',
        )
    if stats.cache_efficiency is not None:
        lines.append(
            f'  {"cache efficiency":<22} {stats.cache_efficiency:>10.1f}x '
            '  (cache_read / cache_write; >=2 is healthy @ 5m TTL)',
        )
    return lines


def model_and_tool_lines(stats: UsageStats) -> tuple[list[str], list[str]]:
    model_lines = []
    if stats.models:
        model_lines.append('  model mix')
        total = sum(stats.models.values())
        for model, count in stats.models.most_common():
            share = 100 * count / total
            model_lines.append(
                f'    {model:<34} {share:>5.1f}%  {count:>6,}',
            )

    tool_lines = []
    if stats.tools:
        tool_lines.append('  top tools')
        for tool, count in stats.tools.most_common(10):
            tool_lines.append(f'    {tool:<34} {count:>13,}')

    return model_lines, tool_lines


def format_report(
    stats: UsageStats,
    *,
    width: int | None = None,
    color: bool | None = None,
) -> str:
    if width is None:
        width = shutil.get_terminal_size(FALLBACK_TERMINAL_SIZE).columns
    if color is None:
        color = supports_color()

    lines: list[str] = ['']
    header = f'  Claude Code usage    {report_span(stats)}'
    lines.append(colorize(header, BOLD, CYAN, color=color))
    separator = f'  {"-" * 55}'
    lines.append(colorize(separator, DIM, color=color))

    totals_lines, tokens_lines = totals_and_tokens_lines(stats)
    lines.append('')
    lines.extend(merge_side_by_side(totals_lines, tokens_lines, width))

    efficiency_lines = cache_efficiency_lines(stats)
    if efficiency_lines:
        lines.append('')
        lines.extend(efficiency_lines)

    model_lines, tool_lines = model_and_tool_lines(stats)
    if model_lines or tool_lines:
        merged = merge_side_by_side(model_lines, tool_lines, width)
        merged[0] = colorize(merged[0], BOLD, color=color)
        lines.append('')
        lines.extend(merged)

    if stats.longest_prompt_chars:
        lines.append('')
        lines.append(
            f'  longest prompt: {stats.longest_prompt_chars:,} chars',
        )

    lines.append('')
    return '\n'.join(lines)


def stats_as_dict(stats: UsageStats) -> dict:
    first, last = stats.first_seen, stats.last_seen
    return {
        'span': {
            'first': first.isoformat() if first else None,
            'last': last.isoformat() if last else None,
        },
        'sessions': stats.sessions,
        'prompts': stats.prompts,
        'replies': stats.replies,
        'thinking_blocks': stats.thinking_blocks,
        'subagent_runs': stats.subagent_runs,
        'lines_added': stats.lines_added,
        'lines_removed': stats.lines_removed,
        'tokens': {
            'output': stats.output_tokens,
            'input': stats.input_tokens,
            'cache_read': stats.cache_read_tokens,
            'cache_write': stats.cache_write_tokens,
        },
        'cache_hit_ratio': stats.cache_hit_ratio,
        'cache_efficiency': stats.cache_efficiency,
        'models': dict(stats.models.most_common()),
        'tools': dict(stats.tools.most_common()),
        'longest_prompt_chars': stats.longest_prompt_chars,
        'output_tokens_by_day': {
            day.isoformat(): value
            for day, value in sorted(stats.output_tokens_by_day.items())
        },
    }


def parse_day(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        msg = f'expected YYYY-MM-DD, got {raw!r}'
        raise argparse.ArgumentTypeError(msg) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Summarize local Claude Code session logs.',
    )
    parser.add_argument(
        'log_root',
        nargs='*',
        type=Path,
        default=[DEFAULT_LOG_ROOT],
        help=f'transcript roots (default: {DEFAULT_LOG_ROOT})',
    )
    parser.add_argument('--since', type=parse_day, help='earliest day')
    parser.add_argument('--until', type=parse_day, help='latest day')
    parser.add_argument(
        '--json',
        action='store_true',
        help='emit machine-readable JSON instead of a report',
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='disable ANSI colors in the report',
    )

    args = parser.parse_args()
    roots = args.log_root or [DEFAULT_LOG_ROOT]

    missing = [root for root in roots if not root.exists()]
    if missing:
        paths = ', '.join(str(root) for root in missing)
        print(f'No such log root: {paths}', file=sys.stderr)
        sys.exit(1)

    stats = collect_stats(roots, since=args.since, until=args.until)

    if args.json:
        print(json.dumps(stats_as_dict(stats), indent=2))
    else:
        color = False if args.no_color else None
        print(format_report(stats, color=color))


if __name__ == '__main__':
    main()
