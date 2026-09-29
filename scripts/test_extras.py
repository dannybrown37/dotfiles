"""Tests for scripts/extras.sh, the opt-in tool picker.

Each test builds a throwaway install/extras/ directory of fake install
scripts, so nothing here installs anything real.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
EXTRAS = REPO_ROOT / 'scripts' / 'extras.sh'
BASH = shutil.which('bash') or '/bin/bash'
EXIT_USAGE = 2

EXTRA_SCRIPT = """\
#!/usr/bin/env bash
## @extra {binary} | {desc}
echo "ran {name}" >> "${{CALL_LOG}}"
"""


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    extras = tmp_path / 'install' / 'extras'
    extras.mkdir(parents=True)
    for name, binary, desc in [
        ('alpha', 'alpha-bin', 'First tool'),
        ('beta', 'beta', 'Second tool'),
    ]:
        (extras / f'{name}.sh').write_text(
            EXTRA_SCRIPT.format(name=name, binary=binary, desc=desc),
        )
    (extras / 'helper.sh').write_text('#!/usr/bin/env bash\n')
    return tmp_path


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    path = tmp_path / 'bin'
    path.mkdir()
    return path


def run_extras(
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
        [BASH, str(EXTRAS), *args],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def calls(root: Path) -> list[str]:
    log = root / 'calls.log'
    return log.read_text().splitlines() if log.exists() else []


@pytest.mark.parametrize(
    ('installed', 'expected'),
    [
        ([], {'alpha': '·', 'beta': '·'}),
        (['alpha-bin'], {'alpha': '✓', 'beta': '·'}),
        (['alpha-bin', 'beta'], {'alpha': '✓', 'beta': '✓'}),
    ],
)
def test_list_marks_installed_by_binary(
    root: Path,
    stub_bin: Path,
    installed: list[str],
    expected: dict[str, str],
) -> None:
    for binary in installed:
        _write_executable(stub_bin / binary, '#!/bin/sh\n')

    result = run_extras(root, stub_bin, '--list')

    assert result.returncode == 0
    rows = {
        line.split()[1]: line.split()[0] for line in result.stdout.splitlines()
    }
    assert rows == expected


def test_list_skips_scripts_without_header(root: Path, stub_bin: Path) -> None:
    result = run_extras(root, stub_bin, '--list')

    assert 'helper' not in result.stdout
    assert 'Second tool' in result.stdout


def test_named_extras_run_their_scripts(root: Path, stub_bin: Path) -> None:
    result = run_extras(root, stub_bin, 'beta', 'alpha')

    assert result.returncode == 0
    assert calls(root) == ['ran beta', 'ran alpha']


def test_unknown_name_fails_before_running_anything(
    root: Path,
    stub_bin: Path,
) -> None:
    result = run_extras(root, stub_bin, 'alpha', 'nope')

    assert result.returncode == EXIT_USAGE
    assert 'nope' in result.stderr
    assert calls(root) == []


def test_no_args_without_tty_prints_list_and_usage(
    root: Path,
    stub_bin: Path,
) -> None:
    result = run_extras(root, stub_bin)

    assert result.returncode == 0
    assert 'alpha' in result.stdout
    assert 'just extras <name>' in result.stdout
    assert calls(root) == []


@pytest.mark.parametrize('flag', ['-h', '--help'])
def test_help(root: Path, stub_bin: Path, flag: str) -> None:
    result = run_extras(root, stub_bin, flag)

    assert result.returncode == 0
    assert 'Usage' in result.stdout
