"""Tests for scripts/windows.sh, the Windows-side tool picker.

powershell.exe and win32yank.sh are stubbed, so nothing real installs.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
WINDOWS = REPO_ROOT / 'scripts' / 'windows.sh'
BASH = shutil.which('bash') or '/bin/bash'
EXIT_USAGE = 2

POWERSHELL_STUB = """\
#!/bin/sh
case "$*" in
*-List*) printf 'git\\t1\\tGit\\r\\nnode\\t0\\tNode.js LTS\\r\\n' ;;
*-Only*) echo "ps only ${*##*-Only }" >> "${CALL_LOG}" ;;
*) echo "ps all" >> "${CALL_LOG}" ;;
esac
"""


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    install = tmp_path / 'install'
    install.mkdir()
    (install / 'win-dev.ps1').write_text('')
    (install / 'win32yank.sh').write_text(
        'echo "ran win32yank" >> "${CALL_LOG}"\n',
    )
    return tmp_path


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    path = tmp_path / 'bin'
    path.mkdir()
    _write_executable(path / 'powershell.exe', POWERSHELL_STUB)
    return path


def run_windows(
    root: Path,
    stub_bin: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        'DOTFILES_ROOT': str(root),
        'CALL_LOG': str(root / 'calls.log'),
        'PATH': f'{stub_bin}:/usr/bin:/bin',
    }
    return subprocess.run(  # noqa: S603
        [BASH, str(WINDOWS), *args],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def calls(root: Path) -> list[str]:
    log = root / 'calls.log'
    return log.read_text().splitlines() if log.exists() else []


def rows(stdout: str) -> dict[str, str]:
    return {line.split()[1]: line.split()[0] for line in stdout.splitlines()}


@pytest.mark.parametrize(
    ('win32yank_installed', 'expected'),
    [
        (False, {'git': '✓', 'node': '·', 'win32yank': '·'}),
        (True, {'git': '✓', 'node': '·', 'win32yank': '✓'}),
    ],
)
def test_list_marks_installed(
    root: Path,
    stub_bin: Path,
    win32yank_installed: bool,  # noqa: FBT001
    expected: dict[str, str],
) -> None:
    if win32yank_installed:
        _write_executable(stub_bin / 'win32yank.exe', '#!/bin/sh\n')

    result = run_windows(root, stub_bin, '--list')

    assert result.returncode == 0
    assert rows(result.stdout) == expected
    assert '\r' not in result.stdout


@pytest.mark.parametrize(
    ('args', 'expected'),
    [
        (['node'], ['ps only node']),
        (['win32yank'], ['ran win32yank']),
        (['git', 'win32yank', 'node'], ['ps only git,node', 'ran win32yank']),
    ],
)
def test_named_items_route_to_installer(
    root: Path,
    stub_bin: Path,
    args: list[str],
    expected: list[str],
) -> None:
    result = run_windows(root, stub_bin, *args)

    assert result.returncode == 0
    assert calls(root) == expected


def test_all_installs_everything(root: Path, stub_bin: Path) -> None:
    result = run_windows(root, stub_bin, '--all')

    assert result.returncode == 0
    assert calls(root) == ['ps all', 'ran win32yank']


def test_unknown_name_fails_before_running_anything(
    root: Path,
    stub_bin: Path,
) -> None:
    result = run_windows(root, stub_bin, 'git', 'nope')

    assert result.returncode == EXIT_USAGE
    assert 'nope' in result.stderr
    assert calls(root) == []


def test_no_args_without_tty_prints_list_and_usage(
    root: Path,
    stub_bin: Path,
) -> None:
    result = run_windows(root, stub_bin)

    assert result.returncode == 0
    assert 'git' in result.stdout
    assert 'just windows <name>' in result.stdout
    assert calls(root) == []


def test_fails_fast_off_windows(root: Path, stub_bin: Path) -> None:
    (stub_bin / 'powershell.exe').unlink()

    result = run_windows(root, stub_bin, '--list')

    assert result.returncode == 1
    assert 'WSL' in result.stderr


@pytest.mark.parametrize('flag', ['-h', '--help'])
def test_help(root: Path, stub_bin: Path, flag: str) -> None:
    result = run_windows(root, stub_bin, flag)

    assert result.returncode == 0
    assert 'Usage' in result.stdout
