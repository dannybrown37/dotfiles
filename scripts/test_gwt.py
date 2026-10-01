"""Tests for the gwt worktree helper in bin/gwt.sh.

`npm` is stubbed on PATH so bootstrap runs are observable and instant.
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
SCRIPT = REPO / 'bin' / 'gwt.sh'
NPM_STUB = '#!/usr/bin/env bash\necho "npm $*" >> "${NPM_CALLS_FILE}"\n'


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    stub_dir = tmp_path / 'stubs'
    stub_dir.mkdir()
    npm = stub_dir / 'npm'
    npm.write_text(NPM_STUB)
    npm.chmod(0o755)
    return {
        **os.environ,
        'PATH': f'{stub_dir}:{os.environ["PATH"]}',
        'NPM_CALLS_FILE': str(tmp_path / 'npm_calls'),
        'GIT_CONFIG_GLOBAL': '/dev/null',
        'GIT_AUTHOR_NAME': 't',
        'GIT_AUTHOR_EMAIL': 't@t',
        'GIT_COMMITTER_NAME': 't',
        'GIT_COMMITTER_EMAIL': 't@t',
    }


@pytest.fixture
def repo(tmp_path: Path, env: dict[str, str]) -> Path:
    path = tmp_path / 'proj'
    path.mkdir()
    (path / 'package.json').write_text('{}')
    for cmd in (
        ['git', 'init', '-q', '-b', 'main'],
        ['git', 'add', '.'],
        ['git', 'commit', '-qm', 'init'],
    ):
        subprocess.run(cmd, cwd=path, env=env, check=True)  # noqa: S603
    return path


def run_gwt(
    repo: Path,
    env: dict[str, str],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    quoted = ' '.join(f"'{a}'" for a in args)
    return subprocess.run(  # noqa: S603
        ['bash', '-c', f'source "{SCRIPT}" && gwt {quoted} && pwd'],  # noqa: S607
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


@pytest.mark.parametrize(
    ('args', 'expect_bootstrap'),
    [
        (('add', 'feat', 'HEAD'), False),
        (('add', 'feat', 'HEAD', '--bootstrap'), True),
        (('add', '-b', 'feat', 'HEAD'), True),
        (('add', 'feat', '--bootstrap', 'HEAD'), True),
    ],
)
def test_add_bootstrap_is_opt_in(
    repo: Path,
    env: dict[str, str],
    args: tuple[str, ...],
    expect_bootstrap: bool,  # noqa: FBT001
) -> None:
    result = run_gwt(repo, env, *args)

    worktree = repo.parent / 'proj-worktrees' / 'feat'
    assert result.returncode == 0, result.stderr
    assert worktree.is_dir()
    assert result.stdout.strip().endswith(str(worktree))
    assert Path(env['NPM_CALLS_FILE']).exists() is expect_bootstrap


def test_add_without_bootstrap_hints_at_command(
    repo: Path,
    env: dict[str, str],
) -> None:
    result = run_gwt(repo, env, 'add', 'feat', 'HEAD')

    assert 'gwt bootstrap' in result.stdout


def test_bootstrap_subcommand_runs_in_current_worktree(
    repo: Path,
    env: dict[str, str],
) -> None:
    result = run_gwt(repo, env, 'bootstrap')

    assert result.returncode == 0, result.stderr
    assert Path(env['NPM_CALLS_FILE']).read_text().startswith('npm install')


def test_add_rejects_unknown_flag(repo: Path, env: dict[str, str]) -> None:
    result = run_gwt(repo, env, 'add', 'feat', 'HEAD', '--nope')

    assert result.returncode != 0
    assert 'Unknown option' in result.stderr
    assert not (repo.parent / 'proj-worktrees' / 'feat').exists()
