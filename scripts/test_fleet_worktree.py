"""Tests for fleet.worktree against real throwaway git repos."""

import os
import subprocess
from pathlib import Path

import pytest

from fleet.worktree import (
    DiffStat,
    create_worktree,
    diff_stat,
    is_dirty,
    remove_worktree,
    repo_root,
    worktree_path,
)

GIT_ENV = {
    'GIT_CONFIG_GLOBAL': '/dev/null',
    'GIT_AUTHOR_NAME': 't',
    'GIT_AUTHOR_EMAIL': 't@t',
    'GIT_COMMITTER_NAME': 't',
    'GIT_COMMITTER_EMAIL': 't@t',
}


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in GIT_ENV.items():
        monkeypatch.setenv(key, value)


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ['git', *args],  # noqa: S607
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **GIT_ENV},
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / 'proj'
    path.mkdir()
    git(path, 'init', '-q', '-b', 'main')
    (path / 'a.txt').write_text('one\n')
    git(path, 'add', '.')
    git(path, 'commit', '-qm', 'init')
    return path


@pytest.mark.parametrize(
    ('branch', 'expected'),
    [
        ('fix-x', '/w/proj-worktrees/fix-x'),
        ('feat/y', '/w/proj-worktrees/feat-y'),
    ],
)
def test_worktree_path_matches_gwt_layout(branch: str, expected: str) -> None:
    assert worktree_path(Path('/w/proj'), branch) == Path(expected)


def test_repo_root_from_subdir_and_from_worktree(repo: Path) -> None:
    sub = repo / 'sub'
    sub.mkdir()
    assert repo_root(sub) == repo
    path = create_worktree(repo, 'fix-x', 'main')
    assert repo_root(path) == repo


def test_repo_root_outside_git_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='not inside a git repository'):
        repo_root(tmp_path)


def test_create_worktree_new_branch_from_base(repo: Path) -> None:
    path = create_worktree(repo, 'fix-x', 'main')
    assert path == repo.parent / 'proj-worktrees' / 'fix-x'
    assert git(path, 'branch', '--show-current').strip() == 'fix-x'


def test_create_worktree_reuses_existing_branch(repo: Path) -> None:
    git(repo, 'branch', 'existing')
    path = create_worktree(repo, 'existing', 'main')
    assert git(path, 'branch', '--show-current').strip() == 'existing'


def test_create_worktree_reuses_existing_worktree(repo: Path) -> None:
    first = create_worktree(repo, 'fix-x', 'main')
    (first / 'keep.txt').write_text('work in progress')
    assert create_worktree(repo, 'fix-x', 'main') == first
    assert (first / 'keep.txt').exists()


def test_create_worktree_refuses_non_worktree_directory(repo: Path) -> None:
    worktree_path(repo, 'fix-x').mkdir(parents=True)
    with pytest.raises(FileExistsError):
        create_worktree(repo, 'fix-x', 'main')


def test_diff_stat_counts_commits_edits_and_untracked(repo: Path) -> None:
    path = create_worktree(repo, 'fix-x', 'main')
    (path / 'a.txt').write_text('one\ntwo\n')
    git(path, 'commit', '-qam', 'two')
    (path / 'a.txt').write_text('ONE\ntwo\nthree\n')
    (path / 'new.txt').write_text('x\n')
    assert diff_stat(path, 'main') == DiffStat(
        files=1,
        added=3,
        removed=1,
        untracked=1,
        commits=1,
    )


def test_diff_stat_missing_worktree_is_none(tmp_path: Path) -> None:
    assert diff_stat(tmp_path / 'gone', 'main') is None


def test_is_dirty_and_remove(repo: Path) -> None:
    path = create_worktree(repo, 'fix-x', 'main')
    assert not is_dirty(path)
    (path / 'b.txt').write_text('x')
    assert is_dirty(path)
    with pytest.raises(subprocess.CalledProcessError):
        remove_worktree(repo, path, force=False)
    remove_worktree(repo, path, force=True)
    assert not path.exists()
    assert 'fix-x' in git(repo, 'branch', '--list', 'fix-x')
