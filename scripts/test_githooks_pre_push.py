"""Tests for githooks/pre-push, which forwards pushed ranges to prek."""

import os
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / 'githooks' / 'pre-push'
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
    (repo / relative_path).write_text(f'{relative_path}\n')
    git(repo, 'add', '--all')
    git(repo, 'commit', '--quiet', '--message', f'change {relative_path}')
    return git(repo, 'rev-parse', 'HEAD')


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / 'repo'
    repo.mkdir()
    git(repo, 'init', '--quiet')
    commit_file(repo, '.pre-commit-config.yaml')
    git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
    return repo


@pytest.fixture
def fake_bin(tmp_path: Path) -> Path:
    """A `prek` stub that logs one line of args per call."""
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    prek = bin_dir / 'prek'
    prek.write_text(f'#!/usr/bin/env bash\necho "$*" >> {tmp_path}/prek.log\n')
    prek.chmod(0o755)
    return bin_dir


def run_hook(
    repo: Path,
    path: str,
    stdin: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [
            '/usr/bin/env',
            'bash',
            str(HOOK),
            'origin',
            'https://example.com/repo.git',
        ],
        cwd=repo,
        input=stdin,
        capture_output=True,
        text=True,
        env={**os.environ, 'PATH': path},
        check=False,
    )


def prek_calls(tmp_path: Path) -> list[str]:
    log = tmp_path / 'prek.log'
    return log.read_text().splitlines() if log.exists() else []


def with_fake_prek(fake_bin: Path) -> str:
    return f'{fake_bin}:{os.environ["PATH"]}'


def pre_push_call(from_ref: str, to_ref: str) -> str:
    return f'run --hook-stage pre-push --from-ref {from_ref} --to-ref {to_ref}'


def test_existing_branch_checks_commits_since_remote_tip(
    repo: Path,
    fake_bin: Path,
    tmp_path: Path,
) -> None:
    remote_tip = commit_file(repo, 'a.py')
    local_tip = commit_file(repo, 'b.py')
    stdin = f'refs/heads/topic {local_tip} refs/heads/topic {remote_tip}\n'

    result = run_hook(repo, with_fake_prek(fake_bin), stdin)

    assert result.returncode == 0, result.stderr
    assert prek_calls(tmp_path) == [pre_push_call(remote_tip, local_tip)]


def test_new_branch_checks_commits_since_origin_main(
    repo: Path,
    fake_bin: Path,
    tmp_path: Path,
) -> None:
    base = git(repo, 'rev-parse', 'origin/main')
    local_tip = commit_file(repo, 'a.py')
    stdin = f'refs/heads/topic {local_tip} refs/heads/topic {ZERO_SHA}\n'

    result = run_hook(repo, with_fake_prek(fake_bin), stdin)

    assert result.returncode == 0, result.stderr
    assert prek_calls(tmp_path) == [pre_push_call(base, local_tip)]


def test_branch_delete_runs_nothing(
    repo: Path,
    fake_bin: Path,
    tmp_path: Path,
) -> None:
    remote_tip = git(repo, 'rev-parse', 'HEAD')
    stdin = f'(delete) {ZERO_SHA} refs/heads/topic {remote_tip}\n'

    result = run_hook(repo, with_fake_prek(fake_bin), stdin)

    assert result.returncode == 0, result.stderr
    assert prek_calls(tmp_path) == []


@pytest.mark.parametrize('prek_exit', [0, 1])
def test_exit_code_follows_prek(
    repo: Path,
    fake_bin: Path,
    prek_exit: int,
) -> None:
    (fake_bin / 'prek').write_text(f'#!/usr/bin/env bash\nexit {prek_exit}\n')
    local_tip = commit_file(repo, 'a.py')
    stdin = f'refs/heads/topic {local_tip} refs/heads/topic {ZERO_SHA}\n'

    result = run_hook(repo, with_fake_prek(fake_bin), stdin)

    assert result.returncode == prek_exit


def test_without_prek_push_proceeds(repo: Path, tmp_path: Path) -> None:
    local_tip = commit_file(repo, 'a.py')
    stdin = f'refs/heads/topic {local_tip} refs/heads/topic {ZERO_SHA}\n'

    result = run_hook(repo, '/usr/bin:/bin', stdin)

    assert result.returncode == 0, result.stderr
    assert prek_calls(tmp_path) == []
