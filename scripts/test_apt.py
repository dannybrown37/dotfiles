"""Tests for install/apt.sh.

sudo, wget and dpkg are stubbed on PATH, so nothing touches the real system.
"""

import os
import subprocess
from pathlib import Path

import pytest

APT_SH = Path(__file__).parent.parent / 'install' / 'apt.sh'
STUB = (
    '#!/usr/bin/env bash\n'
    'echo "$(basename "$0") $*" >> "${CALL_LOG}"\n'
    '[[ "${1:-}" == tee ]] && cat > /dev/null\n'
    'true\n'
)


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    stub_bin = tmp_path / 'bin'
    stub_bin.mkdir()
    for name in ('sudo', 'wget', 'dpkg'):
        (stub_bin / name).write_text(STUB)
        (stub_bin / name).chmod(0o755)
    return {
        **os.environ,
        'PATH': f'{stub_bin}:{os.environ["PATH"]}',
        'CALL_LOG': str(tmp_path / 'calls'),
        'GH_APT_LIST': str(tmp_path / 'github-cli.list'),
    }


def run_apt(env: dict[str, str]) -> list[str]:
    result = subprocess.run(  # noqa: S603
        ['bash', str(APT_SH)],  # noqa: S607
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return Path(env['CALL_LOG']).read_text().splitlines()


def test_adds_github_cli_apt_repo_before_apt_update(
    env: dict[str, str],
) -> None:
    calls = run_apt(env)

    key_fetch = next(
        i for i, c in enumerate(calls) if 'githubcli-archive-keyring.gpg' in c
    )
    source_write = next(
        i for i, c in enumerate(calls) if c == f'sudo tee {env["GH_APT_LIST"]}'
    )
    assert key_fetch < source_write < calls.index('sudo apt -y update')


def test_skips_github_cli_repo_when_already_configured(
    env: dict[str, str],
) -> None:
    Path(env['GH_APT_LIST']).write_text('deb ... cli.github.com ...\n')

    calls = run_apt(env)

    assert not any('githubcli' in c for c in calls)
