#!/usr/bin/env python3
"""Aggregate Claude Code session logs into usage statistics.

Reads the JSONL transcripts under ~/.claude/projects and reports totals on
demand -- every run re-reads the logs, so the numbers only cover transcripts
still present on this machine. Each run also upserts today's rollup into the
sqlite history db (see --db-path), so daily totals survive log rotation;
--record backfills a --since/--until range instead of printing a report.
"""

import argparse
import json
import math
import os
import shutil
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from collections.abc import Iterator

DEFAULT_LOG_ROOT = Path.home() / '.claude' / 'projects'
DEFAULT_DB_PATH = Path.home() / '.claude' / 'ccstats.db'
SUBAGENT_DIR = 'subagents'
TURN_DURATION_SUBTYPE = 'turn_duration'
P50 = 0.5
P95 = 0.95
MILLISECONDS_PER_SECOND = 1000
FALLBACK_TERMINAL_SIZE = (80, 24)
COLUMN_GAP = 4
DEFAULT_PRICING_PATH = Path(__file__).resolve().parent / 'model_pricing.json'
PRICING_STALE_AFTER_DAYS = 60
TOKENS_PER_MILLION = 1_000_000

RESET = '\x1b[0m'
BOLD = '\x1b[1m'
DIM = '\x1b[2m'
CYAN = '\x1b[36m'


@dataclass
class ModelUsage:
    """Per-model token totals -- needed because prices differ by model."""

    output_tokens: int = 0
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True)
class ModelPrice:
    """Dollars per million tokens for one model, from model_pricing.json."""

    input_per_million: float
    output_per_million: float
    expires: date | None = None
    note: str | None = None


@dataclass(frozen=True)
class PricingTable:
    as_of: date
    cache_write_multiplier: float
    cache_read_multiplier: float
    models: dict[str, ModelPrice]


@dataclass
class CostBreakdown:
    """Estimated spend for a UsageStats snapshot, priced via a PricingTable."""

    total: float
    by_category: dict[str, float]
    by_model: dict[str, float]
    unpriced_models: set[str]
    expired_models: set[str]
    pricing_as_of: date
    pricing_stale: bool


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
    model_usage: dict[str, ModelUsage] = field(default_factory=dict)
    output_tokens_by_day: dict[date, int] = field(default_factory=dict)
    wall_durations_ms: list[int] = field(default_factory=list)
    model_durations_ms: list[float] = field(default_factory=list)
    model_durations_ms_by_model: dict[str, list[float]] = field(
        default_factory=dict,
    )
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


@dataclass
class TurnTracker:
    """Per-turn timing, rebuilt from the gaps between records.

    A turn's `turn_duration` record names no model, so the turn is credited
    to whichever model produced the most replies inside it -- a turn that
    delegates to a subagent still belongs to the model driving it.

    Model time counts only the gaps that end at a reply. A gap ending at a
    tool result is where tool execution and any wait for the human's approval
    live, so excluding those yields generation time alone rather than trying
    to subtract an approval wait that is never logged.
    """

    models: Counter = field(default_factory=Counter)
    previous_stamp: datetime | None = None
    model_ms: float = 0.0

    def begin_turn(self, stamp: datetime | None) -> None:
        self.models.clear()
        self.model_ms = 0.0
        self.previous_stamp = stamp

    def note_record(
        self,
        stamp: datetime | None,
        *,
        from_model: bool,
    ) -> None:
        if stamp is None:
            return
        if from_model and self.previous_stamp is not None:
            gap = (stamp - self.previous_stamp).total_seconds()
            self.model_ms += max(gap, 0.0) * MILLISECONDS_PER_SECOND
        self.previous_stamp = stamp

    def note_reply(self, model: str | None, stamp: datetime | None) -> None:
        if model:
            self.models[model] += 1
        self.note_record(stamp, from_model=True)

    def close_turn(self) -> tuple[str | None, float]:
        dominant = self.models.most_common(1)
        model_ms = self.model_ms
        self.begin_turn(None)
        return (dominant[0][0] if dominant else None), model_ms


def percentile(values: list[float], fraction: float) -> float | None:
    """Nearest-rank percentile, or None for an empty sample."""
    if not values:
        return None
    ordered = sorted(values)
    rank = math.ceil(fraction * len(ordered))
    return float(ordered[max(rank - 1, 0)])


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

    usage = message.get('usage') or {}
    output = usage.get('output_tokens', 0) or 0
    input_ = usage.get('input_tokens', 0) or 0
    cache_read = usage.get('cache_read_input_tokens', 0) or 0
    cache_write = usage.get('cache_creation_input_tokens', 0) or 0

    stats.output_tokens += output
    stats.input_tokens += input_
    stats.cache_read_tokens += cache_read
    stats.cache_write_tokens += cache_write

    if model:
        stats.models[model] += 1
        model_usage = stats.model_usage.setdefault(model, ModelUsage())
        model_usage.output_tokens += output
        model_usage.input_tokens += input_
        model_usage.cache_read_tokens += cache_read
        model_usage.cache_write_tokens += cache_write

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


def is_turn_boundary(record: dict) -> bool:
    return (
        record.get('type') == 'system'
        and record.get('subtype') == TURN_DURATION_SUBTYPE
    )


def tally_turn_duration(
    stats: UsageStats,
    record: dict,
    turn: TurnTracker,
) -> None:
    duration = record.get('durationMs')
    model, model_ms = turn.close_turn()

    if isinstance(duration, int):
        stats.wall_durations_ms.append(duration)
    if model_ms <= 0:
        return

    stats.model_durations_ms.append(model_ms)
    if model:
        stats.model_durations_ms_by_model.setdefault(model, []).append(
            model_ms,
        )


def tally_record(
    stats: UsageStats,
    record: dict,
    stamp: datetime | None,
    turn: TurnTracker,
) -> None:
    day = stamp.date() if stamp else None

    if record.get('type') == 'assistant':
        tally_assistant(stats, record, day)
        turn.note_reply(record.get('message', {}).get('model'), stamp)
    elif is_turn_boundary(record):
        tally_turn_duration(stats, record, turn)
    elif is_prompt(record):
        stats.prompts += 1
        stats.longest_prompt_chars = max(
            stats.longest_prompt_chars,
            len(prompt_text(record)),
        )
        turn.begin_turn(stamp)
    elif record.get('type') == 'user':
        turn.note_record(stamp, from_model=False)

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
        turn = TurnTracker()

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

            tally_record(stats, record, stamp, turn)

    return stats


def load_pricing(path: Path) -> PricingTable:
    """Load scripts/model_pricing.json (or an override path)."""
    data = json.loads(path.read_text())
    models = {
        name: ModelPrice(
            input_per_million=entry['input'],
            output_per_million=entry['output'],
            expires=(
                date.fromisoformat(entry['expires'])
                if entry.get('expires')
                else None
            ),
            note=entry.get('note'),
        )
        for name, entry in data['models'].items()
    }
    return PricingTable(
        as_of=date.fromisoformat(data['as_of']),
        cache_write_multiplier=data['cache_write_multiplier'],
        cache_read_multiplier=data['cache_read_multiplier'],
        models=models,
    )


def find_model_price(model: str, pricing: PricingTable) -> ModelPrice | None:
    """Longest-prefix match, so dated model IDs (…-20251001) still resolve."""
    matches = [name for name in pricing.models if model.startswith(name)]
    if not matches:
        return None
    return pricing.models[max(matches, key=len)]


def compute_cost(
    stats: UsageStats,
    pricing: PricingTable,
    *,
    today: date | None = None,
) -> CostBreakdown:
    """Estimate spend per token category and per model.

    Cache write/read costs use the pricing table's flat multipliers rather
    than a per-request TTL, since the JSONL logs don't record which TTL a
    given cache write used.
    """
    today = today or date.today()
    by_category = {
        'output': 0.0,
        'input': 0.0,
        'cache_read': 0.0,
        'cache_write': 0.0,
    }
    by_model: dict[str, float] = {}
    unpriced_models: set[str] = set()
    expired_models: set[str] = set()

    for model, usage in stats.model_usage.items():
        price = find_model_price(model, pricing)
        if price is None:
            unpriced_models.add(model)
            continue
        if price.expires is not None and today > price.expires:
            expired_models.add(model)

        output_cost = (
            usage.output_tokens / TOKENS_PER_MILLION * price.output_per_million
        )
        input_cost = (
            usage.input_tokens / TOKENS_PER_MILLION * price.input_per_million
        )
        cache_read_cost = (
            usage.cache_read_tokens
            / TOKENS_PER_MILLION
            * price.input_per_million
            * pricing.cache_read_multiplier
        )
        cache_write_cost = (
            usage.cache_write_tokens
            / TOKENS_PER_MILLION
            * price.input_per_million
            * pricing.cache_write_multiplier
        )

        by_category['output'] += output_cost
        by_category['input'] += input_cost
        by_category['cache_read'] += cache_read_cost
        by_category['cache_write'] += cache_write_cost
        by_model[model] = (
            output_cost + input_cost + cache_read_cost + cache_write_cost
        )

    stale = (today - pricing.as_of).days > PRICING_STALE_AFTER_DAYS or bool(
        expired_models,
    )

    return CostBreakdown(
        total=sum(by_category.values()),
        by_category=by_category,
        by_model=by_model,
        unpriced_models=unpriced_models,
        expired_models=expired_models,
        pricing_as_of=pricing.as_of,
        pricing_stale=stale,
    )


DAILY_STATS_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_totals (
    day TEXT PRIMARY KEY,
    sessions INTEGER NOT NULL,
    prompts INTEGER NOT NULL,
    replies INTEGER NOT NULL,
    thinking_blocks INTEGER NOT NULL,
    subagent_runs INTEGER NOT NULL,
    lines_added INTEGER NOT NULL,
    lines_removed INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER NOT NULL,
    cache_write_tokens INTEGER NOT NULL,
    cost_total REAL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_model_usage (
    day TEXT NOT NULL,
    model TEXT NOT NULL,
    output_tokens INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER NOT NULL,
    cache_write_tokens INTEGER NOT NULL,
    cost REAL,
    PRIMARY KEY (day, model)
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(DAILY_STATS_SCHEMA)


def record_day(
    conn: sqlite3.Connection,
    day: date,
    stats: UsageStats,
    cost: CostBreakdown | None,
) -> bool:
    """Upsert one day's totals and per-model rows; False if the day is idle.

    Per-model rows are deleted and reinserted rather than replaced in place,
    so a model dropped from the day's usage doesn't leave a stale row behind.
    """
    if not stats.session_ids:
        return False

    day_key = day.isoformat()
    conn.execute(
        """
        INSERT OR REPLACE INTO daily_totals (
            day, sessions, prompts, replies, thinking_blocks,
            subagent_runs, lines_added, lines_removed, output_tokens,
            input_tokens, cache_read_tokens, cache_write_tokens,
            cost_total, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            day_key,
            stats.sessions,
            stats.prompts,
            stats.replies,
            stats.thinking_blocks,
            stats.subagent_runs,
            stats.lines_added,
            stats.lines_removed,
            stats.output_tokens,
            stats.input_tokens,
            stats.cache_read_tokens,
            stats.cache_write_tokens,
            cost.total if cost else None,
            datetime.now().isoformat(),
        ),
    )

    conn.execute('DELETE FROM daily_model_usage WHERE day = ?', (day_key,))
    for model, usage in stats.model_usage.items():
        model_cost = cost.by_model.get(model) if cost else None
        conn.execute(
            """
            INSERT INTO daily_model_usage (
                day, model, output_tokens, input_tokens,
                cache_read_tokens, cache_write_tokens, cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                day_key,
                model,
                usage.output_tokens,
                usage.input_tokens,
                usage.cache_read_tokens,
                usage.cache_write_tokens,
                model_cost,
            ),
        )

    return True


def iter_days(since: date, until: date) -> Iterator[date]:
    day = since
    while day <= until:
        yield day
        day += timedelta(days=1)


def record_range(
    conn: sqlite3.Connection,
    roots: list[Path],
    since: date,
    until: date,
    pricing: PricingTable | None,
) -> int:
    """Record each day in [since, until] and return how many had activity."""
    written = 0
    for day in iter_days(since, until):
        stats = collect_stats(roots, since=day, until=day)
        cost = compute_cost(stats, pricing) if pricing else None
        if record_day(conn, day, stats, cost):
            written += 1
    return written


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


CACHE_ROW_WIDTH = 20
CACHE_VALUE_WIDTH = 10


def cache_efficiency_lines(stats: UsageStats) -> list[str]:
    rows = []
    if stats.cache_hit_ratio is not None:
        rows.append(('cache hit ratio', f'{stats.cache_hit_ratio:.1%}'))
    if stats.cache_efficiency is not None:
        rows.append(('cache efficiency', f'{stats.cache_efficiency:.1f}x'))
    if not rows:
        return []

    lines = ['  caching']
    lines.extend(
        f'    {label:<{CACHE_ROW_WIDTH}} {value:>{CACHE_VALUE_WIDTH}}'
        for label, value in rows
    )
    lines.append(
        '    hit ratio = cache_read / (cache_read + input);'
        ' efficiency = cache_read / cache_write (>=2x healthy @ 5m TTL)',
    )
    return lines


TURN_LABEL_WIDTH = 30
TURN_STAT_WIDTH = 8


def turn_duration_row(label: str, durations: list[float]) -> str:
    p50 = percentile(durations, P50) or 0.0
    p95 = percentile(durations, P95) or 0.0
    return (
        f'    {label:<{TURN_LABEL_WIDTH}}'
        f' {p50 / MILLISECONDS_PER_SECOND:>{TURN_STAT_WIDTH}.1f}s'
        f' {p95 / MILLISECONDS_PER_SECOND:>{TURN_STAT_WIDTH}.1f}s'
        f' {len(durations):>7,}'
    )


def turn_duration_lines(stats: UsageStats) -> list[str]:
    if not (stats.model_durations_ms or stats.wall_durations_ms):
        return []

    header = (
        f'    {"":<{TURN_LABEL_WIDTH}}'
        f' {"p50":>{TURN_STAT_WIDTH + 1}}'
        f' {"p95":>{TURN_STAT_WIDTH + 1}}'
        f' {"turns":>7}'
    )
    lines = ['  turn duration', header]
    lines.append(turn_duration_row('model time', stats.model_durations_ms))
    lines.append(turn_duration_row('wall clock', stats.wall_durations_ms))

    by_model = sorted(
        stats.model_durations_ms_by_model.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    )
    lines.extend(
        turn_duration_row(model, durations) for model, durations in by_model
    )
    lines.append(
        '    model time = gaps ending at a reply, so tool runs and approval '
        'waits are excluded; per-model rows are model time',
    )
    return lines


COST_CATEGORY_LABELS = (
    ('output', 'output'),
    ('input', 'input (uncached)'),
    ('cache_read', 'cache read'),
    ('cache_write', 'cache write'),
)
COST_ROW_WIDTH = 20
COST_PERCENT_WIDTH = 6
COST_AMOUNT_WIDTH = 9


def cost_row(label: str, percent: str, amount: float) -> str:
    return (
        f'    {label:<{COST_ROW_WIDTH}} {percent:>{COST_PERCENT_WIDTH}}'
        f'  $ {amount:>{COST_AMOUNT_WIDTH}.2f}'
    )


def cost_lines(cost: CostBreakdown) -> list[str]:
    lines = ['  estimated spend', cost_row('total', '', cost.total)]

    for key, label in COST_CATEGORY_LABELS:
        amount = cost.by_category[key]
        share = 100 * amount / cost.total if cost.total else 0.0
        lines.append(cost_row(label, f'{share:.1f}%', amount))

    if cost.unpriced_models:
        names = ', '.join(sorted(cost.unpriced_models))
        lines.append(f'    (excluded, no pricing on file: {names})')

    if cost.pricing_stale:
        expired = ''
        if cost.expired_models:
            names = ', '.join(sorted(cost.expired_models))
            expired = f'expired pricing for {names}; '
        lines.append(
            f'    pricing dated {cost.pricing_as_of} looks stale -- {expired}'
            'ask Claude to refresh scripts/model_pricing.json',
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
    cost: CostBreakdown | None = None,
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
        efficiency_lines[0] = colorize(efficiency_lines[0], BOLD, color=color)
        lines.append('')
        lines.extend(efficiency_lines)

    turn_lines = turn_duration_lines(stats)
    if turn_lines:
        turn_lines[0] = colorize(turn_lines[0], BOLD, color=color)
        lines.append('')
        lines.extend(turn_lines)

    if cost is not None:
        spend_lines = cost_lines(cost)
        spend_lines[0] = colorize(spend_lines[0], BOLD, color=color)
        lines.append('')
        lines.extend(spend_lines)

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


def cost_as_dict(cost: CostBreakdown | None) -> dict | None:
    if cost is None:
        return None
    return {
        'total': cost.total,
        'by_category': cost.by_category,
        'by_model': cost.by_model,
        'unpriced_models': sorted(cost.unpriced_models),
        'expired_models': sorted(cost.expired_models),
        'pricing_as_of': cost.pricing_as_of.isoformat(),
        'pricing_stale': cost.pricing_stale,
    }


def duration_as_dict(durations: list[float]) -> dict:
    return {
        'turns': len(durations),
        'p50': percentile(durations, P50),
        'p95': percentile(durations, P95),
    }


def turn_duration_as_dict(stats: UsageStats) -> dict:
    by_model = stats.model_durations_ms_by_model.items()
    return {
        'model_time': duration_as_dict(stats.model_durations_ms),
        'wall_clock': duration_as_dict(
            [float(ms) for ms in stats.wall_durations_ms],
        ),
        'by_model': {
            model: duration_as_dict(durations) for model, durations in by_model
        },
    }


def stats_as_dict(
    stats: UsageStats,
    cost: CostBreakdown | None = None,
) -> dict:
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
        'turn_duration_ms': turn_duration_as_dict(stats),
        'cost': cost_as_dict(cost),
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
    parser.add_argument(
        '--pricing-path',
        type=Path,
        default=DEFAULT_PRICING_PATH,
        help=f'model pricing file (default: {DEFAULT_PRICING_PATH})',
    )
    parser.add_argument(
        '--record',
        action='store_true',
        help=(
            'backfill --since/--until into --db-path instead of printing '
            "a report; every normal run already records today's snapshot"
        ),
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f'sqlite history db (default: {DEFAULT_DB_PATH})',
    )

    args = parser.parse_args()
    roots = args.log_root or [DEFAULT_LOG_ROOT]

    missing = [root for root in roots if not root.exists()]
    if missing:
        paths = ', '.join(str(root) for root in missing)
        print(f'No such log root: {paths}', file=sys.stderr)
        sys.exit(1)

    pricing = None
    if args.pricing_path.exists():
        pricing = load_pricing(args.pricing_path)
    else:
        print(
            f'No pricing file at {args.pricing_path} -- '
            'spend estimates disabled',
            file=sys.stderr,
        )

    if args.record:
        today = date.today()
        since = args.since or today
        until = args.until or today
        conn = sqlite3.connect(args.db_path)
        try:
            ensure_schema(conn)
            written = record_range(conn, roots, since, until, pricing)
            conn.commit()
        finally:
            conn.close()
        print(f'recorded {written} day(s) to {args.db_path}')
        return

    stats = collect_stats(roots, since=args.since, until=args.until)
    cost = compute_cost(stats, pricing) if pricing else None

    today = date.today()
    conn = sqlite3.connect(args.db_path)
    try:
        ensure_schema(conn)
        record_range(conn, roots, today, today, pricing)
        conn.commit()
    finally:
        conn.close()

    if args.json:
        print(json.dumps(stats_as_dict(stats, cost), indent=2))
    else:
        color = False if args.no_color else None
        print(format_report(stats, color=color, cost=cost))


if __name__ == '__main__':
    main()
