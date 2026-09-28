"""Tests for the `gp` push helper in config/.bash_aliases."""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
ALIASES = REPO / 'config' / '.bash_aliases'
GITCONFIG = REPO / 'config' / '.gitconfig'


def git(cwd: Path, *args: str, env: dict[str, str]) -> str:
    return subprocess.run(  # noqa: S603
        ['git', *args],  # noqa: S607
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def gp(
    cwd: Path,
    *args: str,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ['bash', '-c', f'source {ALIASES} && gp "$@"', 'gp', *args],  # noqa: S607
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    return {
        **os.environ,
        'HOME': str(tmp_path / 'home'),
        'GIT_CONFIG_GLOBAL': str(GITCONFIG),
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_AUTHOR_NAME': 't',
        'GIT_AUTHOR_EMAIL': 't@example.com',
        'GIT_COMMITTER_NAME': 't',
        'GIT_COMMITTER_EMAIL': 't@example.com',
    }


@pytest.fixture
def repos(tmp_path: Path, env: dict[str, str]) -> tuple[Path, Path]:
    origin = tmp_path / 'origin.git'
    git(tmp_path, 'init', '--bare', '-b', 'main', str(origin), env=env)
    seed = tmp_path / 'seed'
    git(tmp_path, 'clone', str(origin), str(seed), env=env)
    git(seed, 'commit', '--allow-empty', '-m', 'first', env=env)
    git(seed, 'push', 'origin', 'HEAD:main', env=env)
    work = tmp_path / 'work'
    git(tmp_path, 'clone', str(origin), str(work), env=env)
    git(work, 'commit', '--allow-empty', '-m', 'local', env=env)
    return seed, work


def log(cwd: Path, ref: str, env: dict[str, str]) -> list[str]:
    return git(cwd, 'log', '--format=%s', ref, env=env).splitlines()


def test_pushes_when_remote_not_ahead(
    repos: tuple[Path, Path],
    env: dict[str, str],
) -> None:
    _, work = repos

    result = gp(work, env=env)

    assert result.returncode == 0, result.stderr
    assert log(work, 'origin/main', env) == ['local', 'first']


def test_rebases_and_retries_when_remote_ahead(
    repos: tuple[Path, Path],
    env: dict[str, str],
) -> None:
    seed, work = repos
    git(seed, 'commit', '--allow-empty', '-m', 'upstream', env=env)
    git(seed, 'push', 'origin', 'HEAD:main', env=env)

    result = gp(work, env=env)

    assert result.returncode == 0, result.stderr
    git(work, 'fetch', env=env)
    assert log(work, 'origin/main', env) == ['local', 'upstream', 'first']


def test_does_not_pull_when_local_history_rewritten(
    repos: tuple[Path, Path],
    env: dict[str, str],
) -> None:
    _, work = repos
    git(work, 'push', env=env)
    git(work, 'commit', '--amend', '--allow-empty', '-m', 'amended', env=env)

    result = gp(work, env=env)

    assert result.returncode != 0
    assert log(work, 'HEAD', env) == ['amended', 'first']
