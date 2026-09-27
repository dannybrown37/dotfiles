"""Tests for the start/ship/rescue/done aliases in config/.gitconfig.

`gh` is stubbed on PATH so tests never hit GitHub.
"""

import os
import subprocess
from pathlib import Path

import pytest

GITCONFIG = Path(__file__).parent.parent / 'config' / '.gitconfig'
FIVE_LINES = 'a\nb\nc\nd\ne\n'
GH_STUB = """#!/usr/bin/env bash
echo "gh $*" >> "${GH_CALLS_FILE}"
if [ "$1 $2" = 'pr view' ]; then
    [ -n "${GH_PR_STATE:-}" ] || { echo 'no pull requests found' >&2; exit 1; }
    case "$*" in
        *headRefOid*) echo "${GH_PR_STATE} ${GH_PR_HEAD:-}" ;;
        *) echo "${GH_PR_STATE}" ;;
    esac
fi
if [ "$*" = 'pr checks' ]; then
    n=$(( $(cat "${GH_CALLS_FILE}.polls" 2>/dev/null || echo 0) + 1 ))
    echo "$n" > "${GH_CALLS_FILE}.polls"
    if [ "$n" -le "${GH_NO_CHECKS_FOR:-0}" ]; then
        echo "no checks reported on the 'topic' branch" >&2
        exit 1
    fi
fi
"""


def git(
    cwd: Path,
    *args: str,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ['git', *args],  # noqa: S607
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    stub_bin = tmp_path / 'bin'
    stub_bin.mkdir()
    gh = stub_bin / 'gh'
    gh.write_text(GH_STUB)
    gh.chmod(0o755)
    return {
        **os.environ,
        'PATH': f'{stub_bin}:{os.environ["PATH"]}',
        'HOME': str(tmp_path / 'home'),
        'GIT_CONFIG_GLOBAL': str(GITCONFIG),
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_AUTHOR_NAME': 't',
        'GIT_AUTHOR_EMAIL': 't@example.com',
        'GIT_COMMITTER_NAME': 't',
        'GIT_COMMITTER_EMAIL': 't@example.com',
        'GH_CALLS_FILE': str(tmp_path / 'gh_calls'),
        'GIT_SHIP_POLL_SECS': '0',
    }


@pytest.fixture
def clone(tmp_path: Path, env: dict[str, str]) -> Path:
    origin = tmp_path / 'origin.git'
    git(tmp_path, 'init', '--bare', '-b', 'main', str(origin), env=env)
    seed = tmp_path / 'seed'
    git(tmp_path, 'clone', str(origin), str(seed), env=env)
    (seed / 'f.txt').write_text(FIVE_LINES)
    git(seed, 'add', 'f.txt', env=env)
    git(seed, 'commit', '-m', 'first', env=env)
    git(seed, 'push', 'origin', 'HEAD:main', env=env)
    work = tmp_path / 'work'
    git(tmp_path, 'clone', str(origin), str(work), env=env)
    git(seed, 'commit', '--allow-empty', '-m', 'upstream', env=env)
    git(seed, 'push', 'origin', 'HEAD:main', env=env)
    return work


def test_start_branches_from_freshly_pulled_main(
    clone: Path,
    env: dict[str, str],
) -> None:
    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode == 0, result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    subject = git(clone, 'log', '-1', '--format=%s', env=env).stdout.strip()
    assert (branch, subject) == ('my-topic', 'upstream')


def on_branch_with_committed_edit(clone: Path, env: dict[str, str]) -> None:
    git(clone, 'switch', '-c', 'old-topic', env=env)
    (clone / 'f.txt').write_text(FIVE_LINES.replace('a', 'A'))
    git(clone, 'commit', '-am', 'feat: edit a', env=env)


def test_start_carries_uncommitted_changes_to_new_branch(
    clone: Path,
    env: dict[str, str],
) -> None:
    on_branch_with_committed_edit(clone, env)
    (clone / 'f.txt').write_text(
        FIVE_LINES.replace('a', 'A').replace('e', 'E'),
    )
    (clone / 'new.txt').write_text('untracked\n')

    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode == 0, result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    assert branch == 'my-topic'
    assert (clone / 'f.txt').read_text() == FIVE_LINES.replace('e', 'E')
    assert (clone / 'new.txt').read_text() == 'untracked\n'
    assert git(clone, 'stash', 'list', env=env).stdout == ''


def test_start_keeps_stash_and_explains_when_carry_conflicts(
    clone: Path,
    env: dict[str, str],
) -> None:
    on_branch_with_committed_edit(clone, env)
    (clone / 'f.txt').write_text(FIVE_LINES.replace('a', 'AA'))

    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode != 0
    assert 'git stash drop' in result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    assert branch == 'my-topic'
    assert git(clone, 'stash', 'list', env=env).stdout.count('\n') == 1


def test_start_failure_restores_branch_and_changes(
    clone: Path,
    env: dict[str, str],
) -> None:
    git(clone, 'commit', '--allow-empty', '-m', 'diverge main', env=env)
    on_branch_with_committed_edit(clone, env)
    (clone / 'new.txt').write_text('untracked\n')

    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode != 0
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    assert branch == 'old-topic'
    assert (clone / 'new.txt').read_text() == 'untracked\n'
    assert git(clone, 'stash', 'list', env=env).stdout == ''


def test_start_with_clean_tree_leaves_older_stashes_alone(
    clone: Path,
    env: dict[str, str],
) -> None:
    (clone / 'old.txt').write_text('stashed earlier\n')
    git(clone, 'stash', '-u', env=env)

    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode == 0, result.stderr
    assert not (clone / 'old.txt').exists()
    assert git(clone, 'stash', 'list', env=env).stdout.count('\n') == 1


def test_start_without_topic_prints_usage(
    clone: Path,
    env: dict[str, str],
) -> None:
    result = git(clone, 'start', env=env)

    assert result.returncode != 0
    assert 'usage: git start <topic>' in result.stderr


@pytest.mark.parametrize(
    ('subjects', 'title'),
    [
        (['ci: one', 'feat: two'], 'feat: main branch protection'),
        (['docs: one', 'chore(deps): two'], 'docs: main branch protection'),
        (['fix!: one', 'feat: two'], 'feat!: main branch protection'),
    ],
)
def test_ship_titles_pr_with_top_prefix_and_branch_name(
    clone: Path,
    env: dict[str, str],
    subjects: list[str],
    title: str,
) -> None:
    git(clone, 'start', 'main-branch-protection', env=env)
    for subject in subjects:
        git(clone, 'commit', '--allow-empty', '-m', subject, env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode == 0, result.stderr
    remote = git(
        clone,
        'ls-remote',
        'origin',
        'main-branch-protection',
        env=env,
    )
    assert 'refs/heads/main-branch-protection' in remote.stdout
    body = '\n'.join(f'- {s}' for s in subjects)
    assert Path(env['GH_CALLS_FILE']).read_text() == (
        'gh pr view --json state -q .state\n'
        f'gh pr create --title {title} --body {body}\n'
        'gh pr merge --auto --squash --delete-branch\n'
        'gh pr checks\n'
        'gh pr checks --watch\n'
    )


@pytest.mark.parametrize(
    ('no_checks_for', 'returncode'),
    [
        (2, 0),
        (30, 1),
    ],
)
def test_ship_waits_for_ci_checks_before_watching(
    clone: Path,
    env: dict[str, str],
    no_checks_for: int,
    returncode: int,
) -> None:
    env['GH_NO_CHECKS_FOR'] = str(no_checks_for)
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: one', env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode == returncode, result.stderr
    calls = Path(env['GH_CALLS_FILE']).read_text().splitlines()
    watched = returncode == 0
    assert ('gh pr checks --watch' in calls) == watched
    assert ('run gh pr checks --watch later' in result.stderr) != watched


@pytest.mark.parametrize(
    'state',
    ['OPEN', 'CLOSED'],
)
def test_ship_reuses_open_pr(
    clone: Path,
    env: dict[str, str],
    state: str,
) -> None:
    env['GH_PR_STATE'] = state
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: one', env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode == 0, result.stderr
    calls = Path(env['GH_CALLS_FILE']).read_text().splitlines()
    creates = state != 'OPEN'
    assert any(c.startswith('gh pr create') for c in calls) == creates
    assert calls[-3:] == [
        'gh pr merge --auto --squash --delete-branch',
        'gh pr checks',
        'gh pr checks --watch',
    ]


def test_ship_refuses_when_pr_already_merged(
    clone: Path,
    env: dict[str, str],
) -> None:
    env['GH_PR_STATE'] = 'MERGED'
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: one', env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode != 0
    assert 'already merged: run git done' in result.stderr
    assert 'git rescue <topic>' in result.stderr
    assert git(clone, 'ls-remote', 'origin', 'topic', env=env).stdout == ''
    assert Path(env['GH_CALLS_FILE']).read_text() == (
        'gh pr view --json state -q .state\n'
    )


def test_ship_refuses_without_conventional_commits(
    clone: Path,
    env: dict[str, str],
) -> None:
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'no prefix', env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode != 0
    assert 'no conventional commit prefix' in result.stderr
    assert not Path(env['GH_CALLS_FILE']).exists()


def test_ship_refuses_on_main(clone: Path, env: dict[str, str]) -> None:
    result = git(clone, 'ship', env=env)

    assert result.returncode != 0
    assert 'on main' in result.stderr
    assert not Path(env['GH_CALLS_FILE']).exists()


def head(clone: Path, env: dict[str, str]) -> str:
    return git(clone, 'rev-parse', 'HEAD', env=env).stdout.strip()


def on_merged_branch(clone: Path, env: dict[str, str]) -> None:
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: merged', env=env)
    env['GH_PR_STATE'] = 'MERGED'
    env['GH_PR_HEAD'] = head(clone, env)


def test_rescue_moves_commits_after_merge_onto_new_branch(
    clone: Path,
    env: dict[str, str],
) -> None:
    on_merged_branch(clone, env)
    git(clone, 'commit', '--allow-empty', '-m', 'fix: late one', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'fix: late two', env=env)

    result = git(clone, 'rescue', 'late-fixes', env=env)

    assert result.returncode == 0, result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    subjects = git(
        clone,
        'log',
        '--format=%s',
        'origin/main..HEAD',
        env=env,
    ).stdout.splitlines()
    base = git(clone, 'merge-base', 'HEAD', 'origin/main', env=env)
    assert branch == 'late-fixes'
    assert subjects == ['fix: late two', 'fix: late one']
    assert (
        base.stdout.strip()
        == git(
            clone,
            'rev-parse',
            'origin/main',
            env=env,
        ).stdout.strip()
    )


def assert_rescue_refused(
    clone: Path,
    env: dict[str, str],
    message: str,
) -> None:
    before = head(clone, env)

    result = git(clone, 'rescue', 'late-fixes', env=env)

    assert result.returncode != 0
    assert message in result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    assert (branch, head(clone, env)) == ('topic', before)


@pytest.mark.parametrize(
    ('state', 'late_commits', 'message'),
    [
        ('OPEN', 1, 'no merged PR for this branch: use git ship'),
        ('', 1, 'no merged PR for this branch: use git ship'),
        ('MERGED', 0, 'nothing to rescue: run git done'),
    ],
)
def test_rescue_refuses_without_merged_pr_and_late_commits(
    clone: Path,
    env: dict[str, str],
    state: str,
    late_commits: int,
    message: str,
) -> None:
    on_merged_branch(clone, env)
    env['GH_PR_STATE'] = state
    for _ in range(late_commits):
        git(clone, 'commit', '--allow-empty', '-m', 'fix: late', env=env)

    assert_rescue_refused(clone, env, message)


def test_rescue_refuses_with_uncommitted_changes(
    clone: Path,
    env: dict[str, str],
) -> None:
    on_merged_branch(clone, env)
    git(clone, 'commit', '--allow-empty', '-m', 'fix: late', env=env)
    (clone / 'f.txt').write_text('changed\n')

    assert_rescue_refused(clone, env, 'commit or stash them first')


def test_rescue_without_topic_prints_usage(
    clone: Path,
    env: dict[str, str],
) -> None:
    result = git(clone, 'rescue', env=env)

    assert result.returncode != 0
    assert 'usage: git rescue <topic>' in result.stderr


def test_done_returns_to_updated_main(
    clone: Path,
    env: dict[str, str],
) -> None:
    git(clone, 'switch', '-c', 'my-topic', env=env)

    result = git(clone, 'done', env=env)

    assert result.returncode == 0, result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    subject = git(clone, 'log', '-1', '--format=%s', env=env).stdout.strip()
    assert (branch, subject) == ('main', 'upstream')


def main_diverged_from_origin(
    clone: Path,
    env: dict[str, str],
    upstream_text: str,
) -> None:
    """Local main gets a direct commit; origin gets a squash of its own."""
    (clone / 'f.txt').write_text('squashed\n')
    git(clone, 'commit', '-am', 'fix: direct on main', env=env)
    seed = clone.parent / 'seed'
    git(seed, 'pull', '--quiet', env=env)
    (seed / 'f.txt').write_text(upstream_text)
    git(seed, 'commit', '-am', 'fix: squash (#1)', env=env)
    git(seed, 'push', 'origin', 'HEAD:main', env=env)
    git(clone, 'switch', '-c', 'my-topic', env=env)


def test_done_resets_main_already_squash_merged(
    clone: Path,
    env: dict[str, str],
) -> None:
    main_diverged_from_origin(clone, env, upstream_text='squashed\n')
    (clone / 'untracked.txt').write_text('keep me\n')

    result = git(clone, 'done', env=env)

    assert result.returncode == 0, result.stderr
    subject = git(clone, 'log', '-1', '--format=%s', env=env).stdout.strip()
    assert subject == 'fix: squash (#1)'
    assert (clone / 'untracked.txt').read_text() == 'keep me\n'


def test_done_refuses_when_local_main_has_unmerged_work(
    clone: Path,
    env: dict[str, str],
) -> None:
    main_diverged_from_origin(clone, env, upstream_text='other\n')

    result = git(clone, 'done', env=env)

    assert result.returncode != 0
    assert 'local main has commits not on origin/main' in result.stderr
    subject = git(clone, 'log', '-1', '--format=%s', env=env).stdout.strip()
    assert subject == 'fix: direct on main'
