"""Tests for the start/ship/done aliases in config/.gitconfig.

`gh` is stubbed on PATH so tests never hit GitHub.
"""

import os
import subprocess
from pathlib import Path

import pytest

GITCONFIG = Path(__file__).parent.parent / 'config' / '.gitconfig'
FIVE_LINES = 'a\nb\nc\nd\ne\n'


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
    gh.write_text('#!/usr/bin/env bash\necho "gh $*" >> "${GH_CALLS_FILE}"\n')
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
        f'gh pr create --title {title} --body {body}\n'
        'gh pr merge --auto --squash --delete-branch\n'
        'gh pr checks --watch\n'
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
