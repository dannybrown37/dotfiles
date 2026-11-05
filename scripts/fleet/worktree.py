"""Git worktrees for agents, laid out the same way `gwt add` does."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiffStat:
    files: int
    added: int
    removed: int
    untracked: int
    commits: int


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ['git', '-C', str(cwd), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def repo_root(path: Path) -> Path:
    """The main checkout, even when `path` is inside a linked worktree."""
    try:
        common_dir = git(
            path,
            'rev-parse',
            '--path-format=absolute',
            '--git-common-dir',
        ).strip()
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        NotADirectoryError,
    ) as error:
        msg = f'{path} is not inside a git repository'
        raise ValueError(msg) from error
    return Path(common_dir).parent


def current_branch(path: Path) -> str | None:
    """The checked-out branch, the short sha when detached, None if not git."""
    if not path.is_dir():
        return None
    try:
        branch = git(path, 'branch', '--show-current').strip()
        return branch or git(path, 'rev-parse', '--short', 'HEAD').strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def worktree_path(root: Path, branch: str) -> Path:
    safe_branch = branch.replace('/', '-')
    return root.parent / f'{root.name}-worktrees' / safe_branch


def branch_exists(root: Path, branch: str) -> bool:
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            'git',
            '-C',
            str(root),
            'show-ref',
            '--verify',
            '--quiet',
            f'refs/heads/{branch}',
        ],
        check=False,
    )
    return result.returncode == 0


def create_worktree(root: Path, branch: str, base: str) -> Path:
    path = worktree_path(root, branch)
    if path.exists():
        msg = f'worktree already exists: {path}'
        raise FileExistsError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    if branch_exists(root, branch):
        git(root, 'worktree', 'add', str(path), branch)
    else:
        git(root, 'worktree', 'add', '-b', branch, str(path), base)
    return path


def remove_worktree(root: Path, path: Path, *, force: bool) -> None:
    """Remove the checkout. The branch stays, so no commits are lost."""
    git(root, 'worktree', 'remove', *(['--force'] if force else []), str(path))


def is_dirty(path: Path) -> bool:
    return bool(git(path, 'status', '--porcelain').strip())


def diff_stat(path: Path, base: str) -> DiffStat | None:
    """Everything the agent changed since it branched, committed or not."""
    if not path.is_dir():
        return None
    try:
        merge_base = git(path, 'merge-base', base, 'HEAD').strip()
        numstat = git(path, 'diff', '--numstat', merge_base)
        untracked = git(path, 'ls-files', '--others', '--exclude-standard')
        commits = git(path, 'rev-list', '--count', f'{merge_base}..HEAD')
    except subprocess.CalledProcessError:
        return None
    added = removed = files = 0
    for line in numstat.splitlines():
        line_added, line_removed, _ = line.split('\t', 2)
        files += 1
        # Binary files report '-' for both counts.
        added += int(line_added) if line_added.isdigit() else 0
        removed += int(line_removed) if line_removed.isdigit() else 0
    return DiffStat(
        files=files,
        added=added,
        removed=removed,
        untracked=len(untracked.splitlines()),
        commits=int(commits.strip() or 0),
    )
