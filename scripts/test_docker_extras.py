"""Tests for the docker-desktop and docker-engine extras.

The two provide the same docker CLI and fight over it, so each refuses to
install while the other is present. PATH holds only stubs, so nothing here
touches apt, winget, or systemd.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
EXTRAS_DIR = REPO_ROOT / 'install' / 'extras'
BASH = shutil.which('bash') or '/bin/bash'

# PATH holds only stubs, so they run bash by absolute path and use builtins.
LOGGING_STUB = f"""\
#!{BASH}
echo "${{0##*/}} $*" >> "${{CALL_LOG}}"
"""

ID_STUB = f"""\
#!{BASH}
case "$1" in
-u) echo 1000 ;;
-nG) echo tester ;;
-un) printf 'tester\\n' ;;
esac
"""


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    path = tmp_path / 'bin'
    path.mkdir()
    for name in ['sudo', 'winget.exe', 'dpkg']:
        _write_executable(path / name, LOGGING_STUB)
    _write_executable(path / 'id', ID_STUB)
    return path


def run_extra(
    name: str,
    stub_bin: Path,
    call_log: Path,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        'CALL_LOG': str(call_log),
        'PATH': str(stub_bin),
    }
    return subprocess.run(  # noqa: S603
        [BASH, str(EXTRAS_DIR / f'{name}.sh')],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def calls(call_log: Path) -> list[str]:
    return call_log.read_text().splitlines() if call_log.exists() else []


@pytest.mark.parametrize(
    ('extra', 'other_binary', 'removal_hint'),
    [
        ('docker-desktop', 'dockerd', 'sudo apt purge docker-ce'),
        (
            'docker-engine',
            'docker-credential-desktop.exe',
            'winget.exe uninstall --id Docker.DockerDesktop',
        ),
    ],
)
def test_refuses_while_the_other_docker_is_installed(
    tmp_path: Path,
    stub_bin: Path,
    extra: str,
    other_binary: str,
    removal_hint: str,
) -> None:
    _write_executable(stub_bin / other_binary, '#!/bin/sh\n')
    call_log = tmp_path / 'calls.log'

    result = run_extra(extra, stub_bin, call_log)

    assert result.returncode == 1
    assert removal_hint in result.stderr
    assert calls(call_log) == []


@pytest.mark.parametrize(
    ('dockerd_present', 'expect_apt_install'),
    [(False, True), (True, False)],
)
def test_engine_installs_packages_only_when_dockerd_missing(
    tmp_path: Path,
    stub_bin: Path,
    dockerd_present: bool,  # noqa: FBT001
    expect_apt_install: bool,  # noqa: FBT001
) -> None:
    if dockerd_present:
        _write_executable(stub_bin / 'dockerd', '#!/bin/sh\n')
    call_log = tmp_path / 'calls.log'

    result = run_extra('docker-engine', stub_bin, call_log)

    assert result.returncode == 0, result.stderr
    apt_installs = [
        c for c in calls(call_log) if 'apt install -y docker-ce' in c
    ]
    assert bool(apt_installs) == expect_apt_install


@pytest.mark.parametrize(
    ('groups', 'expect_usermod'),
    [('tester', True), ('tester docker', False)],
)
def test_engine_adds_user_to_docker_group_once(
    tmp_path: Path,
    stub_bin: Path,
    groups: str,
    expect_usermod: bool,  # noqa: FBT001
) -> None:
    _write_executable(stub_bin / 'dockerd', '#!/bin/sh\n')
    _write_executable(
        stub_bin / 'id',
        ID_STUB.replace('echo tester', f"echo '{groups}'"),
    )
    call_log = tmp_path / 'calls.log'

    result = run_extra('docker-engine', stub_bin, call_log)

    assert result.returncode == 0, result.stderr
    usermods = [c for c in calls(call_log) if 'usermod -aG docker' in c]
    assert bool(usermods) == expect_usermod
