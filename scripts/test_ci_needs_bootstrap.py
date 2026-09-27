"""Tests for ci_needs_bootstrap.sh, which gates the slow CI bootstrap job."""

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / 'ci_needs_bootstrap.sh'
ZERO_SHA = '0' * 40


def git(repo: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        [
            '/usr/bin/env',
            'git',
            '-C',
            str(repo),
            '-c',
            'user.name=test',
            '-c',
            'user.email=test@example.com',
            '-c',
            'commit.gpgsign=false',
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def commit_file(repo: Path, relative_path: str) -> str:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'{relative_path}\n')
    git(repo, 'add', '--all')
    git(repo, 'commit', '--quiet', '--message', f'change {relative_path}')
    return git(repo, 'rev-parse', 'HEAD')


def needs_bootstrap(repo: Path, base: str, head: str) -> str:
    result = subprocess.run(  # noqa: S603
        ['/usr/bin/env', 'bash', str(SCRIPT), base, head],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, 'init', '--quiet')
    commit_file(tmp_path, 'seed.txt')
    return tmp_path


@pytest.mark.parametrize(
    ('changed_path', 'expected'),
    [
        ('install/apt.sh', 'true'),
        ('justfile', 'false'),
        ('config/.newrc', 'true'),
        ('.github/workflows/ci.yml', 'true'),
        ('scripts/just-help.sh', 'false'),
        ('README.md', 'false'),
        ('bin/gwt.sh', 'false'),
        ('scripts/other.py', 'false'),
        ('.github/workflows/pr-title.yml', 'false'),
        ('docs/justfile-notes.md', 'false'),
    ],
)
def test_decides_from_changed_paths(
    repo: Path,
    changed_path: str,
    expected: str,
) -> None:
    base = git(repo, 'rev-parse', 'HEAD')
    head = commit_file(repo, changed_path)

    assert needs_bootstrap(repo, base, head) == expected


@pytest.mark.parametrize(
    ('change', 'expected'),
    [
        (['sh', '-c', 'echo edited >> config/.bashrc'], 'false'),
        (['git', 'rm', '--quiet', 'config/.bashrc'], 'true'),
        (['git', 'mv', 'config/.bashrc', 'config/.bashrc2'], 'true'),
    ],
)
def test_config_only_bootstraps_when_files_come_or_go(
    repo: Path,
    change: list[str],
    expected: str,
) -> None:
    """Bootstrap only symlinks config/ files, so edits can't break it."""
    base = commit_file(repo, 'config/.bashrc')
    subprocess.run(['/usr/bin/env', *change], cwd=repo, check=True)  # noqa: S603
    git(repo, 'commit', '--quiet', '--all', '--message', 'change config')
    head = git(repo, 'rev-parse', 'HEAD')

    assert needs_bootstrap(repo, base, head) == expected


@pytest.mark.parametrize('base', [ZERO_SHA, '', 'deadbeef' * 5])
def test_unknown_base_runs_bootstrap(repo: Path, base: str) -> None:
    """New branches send an all-zeros base; force pushes, an unseen one."""
    head = commit_file(repo, 'README.md')

    assert needs_bootstrap(repo, base, head) == 'true'
