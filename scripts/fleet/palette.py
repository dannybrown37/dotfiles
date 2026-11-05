"""What the Ctrl+P palette offers, as plain data the TUI turns into hits."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from fleet.agents import AgentState
from fleet.ops import DashboardRow
from fleet.radar import PullRequest, Review, Score

PR_URL = re.compile(r'https://github\.com/([\w.-]+)/([\w.-]+)/pull/(\d+)')
REMOTE_URL = re.compile(r'^\s*url\s*=\s*(\S+)', re.MULTILINE)
REMOTE_REPO = re.compile(r'[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$')

# Agents that need you sort first: that is why you opened the palette.
STATE_ORDER = {
    AgentState.WAITING: 0,
    AgentState.IDLE: 1,
    AgentState.ERROR: 2,
    AgentState.EXITED: 3,
    AgentState.WORKING: 4,
    AgentState.UNKNOWN: 5,
    AgentState.GONE: 6,
}


@dataclass(frozen=True)
class PaletteEntry:
    label: str
    help: str
    action: str
    target: str = ''


@dataclass(frozen=True)
class RankedReview:
    pr: PullRequest
    score: Score
    review: Review | None


def pr_from_text(text: str) -> str | None:
    match = PR_URL.search(text)
    return match.group(0) if match else None


def parse_pr_url(url: str) -> tuple[str, str, int]:
    match = PR_URL.fullmatch(url)
    if not match:
        msg = f'not a GitHub PR URL: {url}'
        raise ValueError(msg)
    owner, repo, number = match.groups()
    return owner, repo, int(number)


def review_agent_name(url: str) -> str:
    _, repo, number = parse_pr_url(url)
    safe_repo = re.sub(r'[^A-Za-z0-9_-]', '-', repo)
    return f'review-{safe_repo}-{number}'[:60]


def find_repos(projects_dir: Path) -> list[Path]:
    if not projects_dir.is_dir():
        return []
    return sorted(
        path
        for path in projects_dir.iterdir()
        if (path / '.git').is_dir() and not path.name.endswith('-worktrees')
    )


def remote_repo(clone: Path) -> str | None:
    try:
        config = (clone / '.git' / 'config').read_text()
    except OSError:
        return None
    for url in REMOTE_URL.findall(config):
        match = REMOTE_REPO.search(url)
        if match:
            return match.group(1)
    return None


def find_local_clone(repos: Sequence[Path], repo: str) -> Path | None:
    """Read .git/config directly: one file read per repo, no git process."""
    wanted = repo.lower()
    for clone in repos:
        found = remote_repo(clone)
        if found and found.lower() == wanted:
            return clone
    return None


def by_urgency(rows: Sequence[DashboardRow]) -> list[DashboardRow]:
    return sorted(
        rows,
        key=lambda r: (STATE_ORDER.get(r.state, 9), r.record is None, r.name),
    )


def agent_entries(rows: Sequence[DashboardRow]) -> list[PaletteEntry]:
    entries = []
    for row in by_urgency(rows):
        about = f'{row.kind}, {row.state.value}, {row.where}'
        if row.target:
            entries += [
                PaletteEntry(
                    f'→ {row.name}',
                    f'jump in ({about})',
                    'jump',
                    row.key,
                ),
                PaletteEntry(
                    f'✉ send to {row.name}',
                    'type a message into it',
                    'send',
                    row.key,
                ),
            ]
        entries.append(
            PaletteEntry(f'± diff {row.name}', str(row.cwd), 'diff', row.key),
        )
        if row.record:
            entries.append(
                PaletteEntry(
                    f'✕ stop {row.name}',
                    'stop agent, keep branch',
                    'stop',
                    row.key,
                ),
            )
    return entries


def review_entries(ranked: Sequence[RankedReview]) -> list[PaletteEntry]:
    entries = []
    for row in sorted(ranked, key=lambda r: r.score.score, reverse=True):
        pr = row.pr
        ref = f'{pr.repo}#{pr.number}'
        summary = (
            row.review.summary if row.review else ', '.join(row.score.reasons)
        )
        entries += [
            PaletteEntry(
                f'★ {row.score.score} {ref} {pr.title}',
                summary or 'open pre-review',
                'open-review',
                pr.url,
            ),
            PaletteEntry(
                f'🔍 agent review {ref}',
                'deep review in a local worktree',
                'deep-review',
                pr.url,
            ),
            PaletteEntry(f'🌐 browser {ref}', pr.url, 'browser', pr.url),
        ]
    return entries


def palette_entries(
    rows: Sequence[DashboardRow],
    ranked: Sequence[RankedReview],
    repos: Sequence[Path],
    clipboard_pr: str | None,
) -> list[PaletteEntry]:
    entries = []
    if clipboard_pr:
        entries.append(
            PaletteEntry(
                f'🔍 agent review clipboard PR {clipboard_pr.removeprefix("https://github.com/")}',
                'deep review in a local worktree',
                'deep-review',
                clipboard_pr,
            ),
        )
    entries += agent_entries(rows)
    entries += review_entries(ranked)
    entries += [
        PaletteEntry('+ new agent', 'start an agent in a worktree', 'new'),
        PaletteEntry(
            '⟳ refresh',
            'reload agents and review requests',
            'refresh',
        ),
        PaletteEntry(
            '★ pre-review all',
            'run the reviewer on unreviewed PRs',
            'review-all',
        ),
    ]
    for repo in repos:
        entries.append(
            PaletteEntry(
                f'+ new agent in {repo.name}',
                str(repo),
                'new-agent',
                str(repo),
            ),
        )
    return entries
