"""What the Ctrl+P palette offers, as plain data the TUI turns into hits."""

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path

from fleet.agents import AgentState
from fleet.aws import (
    LogGroup,
    ProfileAlarms,
    alarm_console_url,
    log_group_console_url,
    updated_at,
    log_tail_command,
    sso_login_command,
)
from fleet.github_org import OrgRepo
from fleet.jira import Ticket
from fleet.ops import DashboardRow
from fleet.radar import PullRequest, Review, Score
from fleet.work import WorkItems

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
    command: tuple[str, ...] = ()


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


def cloned_remotes(repos: Sequence[Path]) -> frozenset[str]:
    """owner/repo (lowercased) of each local clone; reads .git/config."""
    return frozenset(
        found.lower() for clone in repos if (found := remote_repo(clone))
    )


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
                    f'✕ delete {row.name}',
                    'stop agent, remove worktree and branch',
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


def window_name(prefix: str, text: str) -> str:
    tail = text.rstrip('/').rsplit('/', 1)[-1]
    return f'{prefix}-{re.sub(r"[^A-Za-z0-9_-]+", "-", tail)}'[:40]


def alarm_entries(results: Sequence[ProfileAlarms]) -> list[PaletteEntry]:
    firing = sorted(
        (alarm for result in results for alarm in result.alarms),
        key=updated_at,
        reverse=True,
    )
    entries = [
        PaletteEntry(
            f'🚨 {alarm.name} ({alarm.profile.label})',
            alarm.reason or 'CloudWatch alarm firing',
            'open-url',
            alarm_console_url(alarm),
        )
        for alarm in firing
    ]
    for result in results:
        if result.needs_login:
            entries.append(
                PaletteEntry(
                    f'🔑 aws sso login {result.profile.name}',
                    'AWS login expired; alarms are hidden until you log in',
                    'run',
                    window_name('aws-login', result.profile.name),
                    tuple(sso_login_command(result.profile)),
                ),
            )
    return entries


def ticket_entries(tickets: Sequence[Ticket]) -> list[PaletteEntry]:
    entries = []
    for ticket in tickets:
        about = ' · '.join(
            part
            for part in (ticket.status, ticket.issue_type, ticket.priority)
            if part
        )
        entries += [
            PaletteEntry(
                f'🎫 {ticket.key} {ticket.summary}',
                about or ticket.url,
                'open-url',
                ticket.url,
            ),
            PaletteEntry(
                f'+ agent from {ticket.key}',
                f'new agent with the ticket as its task: {ticket.summary}',
                'jira-agent',
                ticket.key,
            ),
        ]
    return entries


def log_group_entries(groups: Sequence[LogGroup]) -> list[PaletteEntry]:
    entries = []
    for group in groups:
        entries.append(
            PaletteEntry(
                f'📜 tail {group.name} ({group.profile.label})',
                'aws logs tail --follow in a fleet window',
                'run',
                window_name('logs', group.name),
                tuple(log_tail_command(group)),
            ),
        )
        url = log_group_console_url(group)
        if url:
            entries.append(
                PaletteEntry(
                    f'🌐 logs {group.name} ({group.profile.label})',
                    'open the log group in the CloudWatch console',
                    'open-url',
                    url,
                ),
            )
    return entries


def org_repo_entries(
    org_repos: Sequence[OrgRepo],
    cloned: Collection[str],
) -> list[PaletteEntry]:
    entries = []
    for repo in org_repos:
        entries.append(
            PaletteEntry(
                f'🌐 {repo.name_with_owner}',
                repo.url,
                'open-url',
                repo.url,
            ),
        )
        if repo.name_with_owner.lower() not in cloned:
            entries.append(
                PaletteEntry(
                    f'+ new agent in {repo.name_with_owner}',
                    'clone it into the projects dir, then start an agent',
                    'new-agent-remote',
                    repo.name_with_owner,
                ),
            )
    return entries


def palette_entries(
    rows: Sequence[DashboardRow],
    ranked: Sequence[RankedReview],
    repos: Sequence[Path],
    clipboard_pr: str | None,
    *,
    work: WorkItems = WorkItems(),  # noqa: B008  frozen, safe to share
    cloned_repos: Collection[str] = (),
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
    entries += alarm_entries(work.alarms)
    entries += agent_entries(rows)
    entries += review_entries(ranked)
    entries += ticket_entries(work.tickets)
    entries += [
        PaletteEntry('+ new agent', 'start an agent in a worktree', 'new'),
        PaletteEntry(
            '⟳ refresh',
            'reload agents, review requests and work items',
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
    entries += org_repo_entries(work.org_repos, cloned_repos)
    entries += log_group_entries(work.log_groups)
    return entries
