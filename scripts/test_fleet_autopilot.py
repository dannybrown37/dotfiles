"""Tests for fleet.autopilot: gated ticket-to-draft-PR flow."""

import subprocess
from pathlib import Path

import pytest

from fleet.autopilot import (
    PR_FILE,
    PrDraft,
    ai_trailer_commits,
    autopilot_prompt,
    exclude_fleet_dir,
    open_draft_pr,
    parse_pr_file,
    strip_ai_trailers,
)


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ['git', *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    remote = tmp_path / 'remote.git'
    work = tmp_path / 'work'
    git(tmp_path, 'init', '-q', '--bare', str(remote))
    git(tmp_path, 'init', '-q', '-b', 'main', str(work))
    git(work, 'config', 'user.email', 'me@example.test')
    git(work, 'config', 'user.name', 'Me')
    git(work, 'config', 'core.hooksPath', '/dev/null')
    (work / 'a.txt').write_text('a\n')
    git(work, 'add', '-A')
    git(work, 'commit', '-qm', 'init')
    git(work, 'remote', 'add', 'origin', str(remote))
    git(work, 'push', '-q', 'origin', 'main')
    git(work, 'switch', '-qc', 'abc-1-fix')
    return work


def test_prompt_wraps_task_with_both_gates() -> None:
    prompt = autopilot_prompt('Fix the thing')
    assert 'Fix the thing' in prompt
    assert '.fleet/plan.md' in prompt
    assert PR_FILE in prompt
    assert 'Do not commit' in prompt
    assert prompt.index('.fleet/plan.md') < prompt.index(PR_FILE)


@pytest.mark.parametrize(
    'trailer',
    [
        'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>',
        'Co-authored-by: Copilot <175728472+Copilot@users.noreply.github.com>',
        'co-authored-by: github-copilot[bot] <x@example.test>',
        '🤖 Generated with [Claude Code](https://claude.com/claude-code)',
        'Generated with GitHub Copilot',
    ],
)
def test_strip_ai_trailers_removes_agent_attribution(trailer: str) -> None:
    message = f'fix: thing\n\nBody line.\n\n{trailer}\n'
    assert strip_ai_trailers(message) == 'fix: thing\n\nBody line.\n'


def test_strip_ai_trailers_keeps_human_coauthors() -> None:
    message = 'fix: thing\n\nCo-authored-by: Pat <pat@example.test>\n'
    assert strip_ai_trailers(message) == message


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('fix: x\n\nWhy.\n', PrDraft('fix: x', 'Why.')),
        ('# feat: y\nbody', PrDraft('feat: y', 'body')),
        ('\n\nfix: z\n', PrDraft('fix: z', '')),
    ],
)
def test_parse_pr_file(text: str, expected: PrDraft) -> None:
    assert parse_pr_file(text) == expected


def test_parse_pr_file_strips_ai_trailers_from_body() -> None:
    draft = parse_pr_file('fix: x\n\nWhy.\n\nCo-Authored-By: Claude <a@b.c>\n')
    assert draft.body == 'Why.'


@pytest.mark.parametrize('text', ['', '\n  \n', '#  \nbody'])
def test_parse_pr_file_needs_a_title(text: str) -> None:
    with pytest.raises(ValueError, match='title'):
        parse_pr_file(text)


def test_exclude_fleet_dir_is_idempotent(repo: Path) -> None:
    exclude_fleet_dir(repo)
    exclude_fleet_dir(repo)
    common = Path(git(repo, 'rev-parse', '--git-common-dir').strip())
    exclude = (repo / common / 'info' / 'exclude').read_text()
    assert exclude.count('/.fleet/') == 1


def test_ai_trailer_commits_finds_offending_commits(repo: Path) -> None:
    (repo / 'b.txt').write_text('b\n')
    git(repo, 'add', '-A')
    git(repo, 'commit', '-qm', 'fix: b\n\nCo-Authored-By: Claude <a@b.c>')
    assert len(ai_trailer_commits(repo, 'main')) == 1


def fake_gh(calls: list[list[str]]) -> object:
    def run(args: list[str], body: str) -> str:
        calls.append([*args, body])
        return 'https://github.example.test/o/r/pull/7\n'

    return run


def write_pr_file(repo: Path, text: str) -> None:
    exclude_fleet_dir(repo)
    (repo / '.fleet').mkdir(exist_ok=True)
    (repo / PR_FILE).write_text(text)


def test_open_draft_pr_commits_pushes_and_opens(repo: Path) -> None:
    (repo / 'a.txt').write_text('changed\n')
    write_pr_file(repo, 'fix: a\n\nWhy.\n\nCo-Authored-By: Claude <a@b.c>\n')
    calls: list[list[str]] = []
    url = open_draft_pr(repo, 'abc-1-fix', 'main', fake_gh(calls))  # type: ignore[arg-type]
    assert url == 'https://github.example.test/o/r/pull/7'
    message = git(repo, 'log', '-1', '--format=%B')
    assert message.strip() == 'fix: a\n\nWhy.'
    assert '.fleet' not in git(repo, 'show', '--stat', 'HEAD')
    assert git(repo, 'ls-remote', 'origin', 'abc-1-fix').strip()
    args = calls[0]
    assert args[:3] == ['pr', 'create', '--draft']
    assert args[args.index('--title') + 1] == 'fix: a'
    assert args[args.index('--base') + 1] == 'main'
    assert args[-1] == 'Why.'


def test_open_draft_pr_with_nothing_to_ship_fails(repo: Path) -> None:
    write_pr_file(repo, 'fix: a\n')
    with pytest.raises(ValueError, match='nothing to ship'):
        open_draft_pr(repo, 'abc-1-fix', 'main', fake_gh([]))  # type: ignore[arg-type]


def test_open_draft_pr_without_pr_file_fails(repo: Path) -> None:
    (repo / 'a.txt').write_text('changed\n')
    with pytest.raises(ValueError, match=PR_FILE):
        open_draft_pr(repo, 'abc-1-fix', 'main', fake_gh([]))  # type: ignore[arg-type]


def test_open_draft_pr_refuses_agent_commits_with_trailers(repo: Path) -> None:
    (repo / 'b.txt').write_text('b\n')
    git(repo, 'add', '-A')
    git(repo, 'commit', '-qm', 'fix: b\n\nCo-Authored-By: Claude <a@b.c>')
    write_pr_file(repo, 'fix: b\n')
    calls: list[list[str]] = []
    with pytest.raises(ValueError, match='AI attribution'):
        open_draft_pr(repo, 'abc-1-fix', 'main', fake_gh(calls))  # type: ignore[arg-type]
    assert not calls
    assert not git(repo, 'ls-remote', 'origin', 'abc-1-fix').strip()


def test_open_draft_pr_ships_agent_commits_without_new_changes(
    repo: Path,
) -> None:
    (repo / 'b.txt').write_text('b\n')
    git(repo, 'add', '-A')
    git(repo, 'commit', '-qm', 'fix: b')
    write_pr_file(repo, 'fix: b\n\nWhy.\n')
    calls: list[list[str]] = []
    open_draft_pr(repo, 'abc-1-fix', 'main', fake_gh(calls))  # type: ignore[arg-type]
    assert git(repo, 'log', '-1', '--format=%s').strip() == 'fix: b'
    assert calls


def test_open_draft_pr_omits_base_for_a_commit_sha(repo: Path) -> None:
    (repo / 'a.txt').write_text('changed\n')
    write_pr_file(repo, 'fix: a\n')
    sha = git(repo, 'rev-parse', 'main').strip()
    calls: list[list[str]] = []
    open_draft_pr(repo, 'abc-1-fix', sha, fake_gh(calls))  # type: ignore[arg-type]
    assert '--base' not in calls[0]
