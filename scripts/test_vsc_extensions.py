"""Tests for .vscode/vsc_extensions.sh, with `code` stubbed."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / '.vscode' / 'vsc_extensions.sh'
BASH = shutil.which('bash') or '/bin/bash'
EXIT_USAGE = 2

CODE_STUB = """\
#!/bin/sh
case "$1" in
--list-extensions) printf 'eamodio.gitlens\\ncharliermarsh.ruff\\n' ;;
*) echo "$*" >> "${CALL_LOG}" ;;
esac
"""


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    code = tmp_path / 'code'
    code.write_text(CODE_STUB)
    code.chmod(code.stat().st_mode | stat.S_IEXEC)
    return tmp_path


def run(stub_bin: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        'CALL_LOG': str(stub_bin / 'calls.log'),
        'PATH': f'{stub_bin}:/usr/bin:/bin',
    }
    return subprocess.run(  # noqa: S603
        [BASH, str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def calls(stub_bin: Path) -> list[str]:
    log = stub_bin / 'calls.log'
    return log.read_text().splitlines() if log.exists() else []


@pytest.mark.parametrize(
    ('extension', 'mark'),
    [
        ('eamodio.gitlens', '✓'),
        ('charliermarsh.ruff', '✓'),
        ('usernamehw.errorlens', '·'),
        ('DavidAnson.vscode-markdownlint', '·'),
    ],
)
def test_list_marks_installed(
    stub_bin: Path,
    extension: str,
    mark: str,
) -> None:
    result = run(stub_bin, '--list')

    rows = {
        line.split()[1]: line.split()[0] for line in result.stdout.splitlines()
    }
    assert result.returncode == 0
    assert rows[extension] == mark


def test_named_installs_only_those(stub_bin: Path) -> None:
    result = run(stub_bin, 'usernamehw.errorlens', 'eamodio.gitlens')

    assert result.returncode == 0
    assert calls(stub_bin) == ['--install-extension usernamehw.errorlens']


def test_all_installs_every_missing(stub_bin: Path) -> None:
    result = run(stub_bin, '--all')

    installed = calls(stub_bin)
    assert result.returncode == 0
    assert '--install-extension usernamehw.errorlens' in installed
    assert '--install-extension eamodio.gitlens' not in installed


def test_unknown_name_fails_before_installing(stub_bin: Path) -> None:
    result = run(stub_bin, 'usernamehw.errorlens', 'nope.nope')

    assert result.returncode == EXIT_USAGE
    assert 'nope.nope' in result.stderr
    assert calls(stub_bin) == []


def test_no_args_without_tty_prints_list_and_usage(stub_bin: Path) -> None:
    result = run(stub_bin)

    assert result.returncode == 0
    assert 'eamodio.gitlens' in result.stdout
    assert 'Usage' in result.stdout
    assert calls(stub_bin) == []


def test_already_installed_says_so(stub_bin: Path) -> None:
    result = run(stub_bin, 'eamodio.gitlens')

    assert result.returncode == 0
    assert 'eamodio.gitlens already installed' in result.stdout
    assert calls(stub_bin) == []
