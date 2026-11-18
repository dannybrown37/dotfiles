"""Autopilot: an agent takes a task to a draft PR, with two human gates.

    task ─► agent writes .fleet/plan.md, stops    (gate 1: you say "go")
         ─► agent builds, tests, reviews, writes .fleet/pr.md, stops
         ─► `fleet pr NAME`                        (gate 2: you ship it)
              commit (no AI trailers) ─► push ─► gh pr create --draft

The agent never commits or pushes; fleet does, so the commit message
is checked before anything leaves the machine.
"""

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

PLAN_FILE = '.fleet/plan.md'
PR_FILE = '.fleet/pr.md'
EXCLUDE_LINE = '/.fleet/'
COMMIT_SHA = re.compile(r'[0-9a-f]{7,40}')
AI_TRAILER = re.compile(
    r'^\s*(?:co-authored-by:.*\b(?:claude|copilot|anthropic|openai)\b'
    r'|.*generated (?:with|by) .*\b(?:claude|copilot)\b).*$',
    re.IGNORECASE,
)

GhRunner = Callable[[list[str], str], str]


@dataclass(frozen=True)
class PrDraft:
    title: str
    body: str


def autopilot_prompt(task: str) -> str:
    return (
        f'{task}\n\n'
        'You are on autopilot with two human gates. Follow these phases.\n\n'
        f'1. Plan. Read the code, then write your plan to {PLAN_FILE}: the '
        'approach, the files you will touch, the tests you will add, and '
        'open questions. Then stop and wait. Do not change code until I '
        'say go.\n'
        '2. Build. When I say go: write the tests first, implement, run the '
        'tests and linters until they pass, then run /code-review on your '
        'own diff and fix what it finds.\n'
        f'3. Hand off. Write {PR_FILE}: line 1 is a conventional-commit '
        'title (e.g. "fix: ..."), then a blank line, then the PR body (why, '
        'what, how you tested it). Then stop.\n\n'
        'Do not commit, push, or open a PR: I run that step myself. Never '
        'add Co-authored-by or "Generated with" lines anywhere.'
    )


def strip_ai_trailers(message: str) -> str:
    kept = [
        line for line in message.splitlines() if not AI_TRAILER.match(line)
    ]
    return '\n'.join(kept).rstrip() + '\n'


def parse_pr_file(text: str) -> PrDraft:
    lines = strip_ai_trailers(text).strip().splitlines()
    title = lines[0].lstrip('#').strip() if lines else ''
    if not title:
        msg = f'{PR_FILE} needs a title on its first line'
        raise ValueError(msg)
    return PrDraft(title, '\n'.join(lines[1:]).strip())


def git(cwd: Path, *args: str, stdin: str | None = None) -> str:
    return subprocess.run(  # noqa: S603
        ['git', *args],  # noqa: S607
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def exclude_fleet_dir(worktree: Path) -> None:
    """Keeps plan.md and pr.md out of `git add -A` and `git status`."""
    common = Path(git(worktree, 'rev-parse', '--git-common-dir').strip())
    exclude = (worktree / common / 'info' / 'exclude').resolve()
    existing = exclude.read_text() if exclude.exists() else ''
    if EXCLUDE_LINE in existing.splitlines():
        return
    exclude.parent.mkdir(parents=True, exist_ok=True)
    separator = '' if not existing or existing.endswith('\n') else '\n'
    exclude.write_text(f'{existing}{separator}{EXCLUDE_LINE}\n')


def ai_trailer_commits(worktree: Path, base: str) -> list[str]:
    log = git(worktree, 'log', '--format=%h%x00%B%x01', f'{base}..HEAD')
    found = []
    for entry in log.split('\x01'):
        sha, _, body = entry.strip().partition('\x00')
        if sha and strip_ai_trailers(body).strip() != body.strip():
            found.append(sha)
    return found


def live_gh(args: list[str], body: str) -> str:
    return subprocess.run(  # noqa: S603
        ['gh', *args],  # noqa: S607
        input=body,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def open_draft_pr(
    worktree: Path,
    branch: str,
    base: str,
    gh: GhRunner = live_gh,
) -> str:
    pr_file = worktree / PR_FILE
    if not pr_file.is_file():
        msg = f'no {PR_FILE} yet: the agent has not handed off'
        raise ValueError(msg)
    draft = parse_pr_file(pr_file.read_text())
    exclude_fleet_dir(worktree)
    git(worktree, 'add', '-A')
    staged = git(worktree, 'diff', '--cached', '--name-only').strip()
    ahead = git(worktree, 'rev-list', '--count', f'{base}..HEAD').strip()
    if not staged and ahead == '0':
        msg = f'nothing to ship: no changes on {branch} since {base}'
        raise ValueError(msg)
    if staged:
        message = f'{draft.title}\n\n{draft.body}'.strip() + '\n'
        git(worktree, 'commit', '-F', '-', stdin=message)
    offenders = ai_trailer_commits(worktree, base)
    if offenders:
        msg = (
            f'commits {", ".join(offenders)} carry AI attribution; reword '
            'them (git rebase -i) before shipping. Nothing was pushed.'
        )
        raise ValueError(msg)
    git(worktree, 'push', '-u', 'origin', f'HEAD:refs/heads/{branch}')
    args = [
        'pr',
        'create',
        '--draft',
        '--head',
        branch,
        '--title',
        draft.title,
    ]
    if not COMMIT_SHA.fullmatch(base):
        args += ['--base', base]
    args += ['--body-file', '-']
    return gh(args, draft.body).strip()
