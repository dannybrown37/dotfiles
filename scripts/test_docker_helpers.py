"""Tests for the Docker Engine branch of docker-up and docker-doctor.

When dockerd is installed the daemon is a systemd service in this distro, so
nothing may reach for Docker Desktop. docker, dockerd, sudo, systemctl, id and
sleep are all stubs; nothing here starts a real daemon.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
DOCKER_SH = REPO_ROOT / 'bin' / 'docker.sh'
BASH = shutil.which('bash') or '/bin/bash'

# The daemon counts as up once the `started` file exists, which the sudo stub
# creates for `systemctl start docker`.
DOCKER_STUB = """\
#!/usr/bin/env bash
echo "docker $*" >> "${CALL_LOG}"
[[ -f "${STATE_DIR}/started" ]] || exit 1
echo 29.0.0
"""

SUDO_STUB = """\
#!/usr/bin/env bash
echo "sudo $*" >> "${CALL_LOG}"
[[ "$*" == "systemctl start docker" ]] && touch "${STATE_DIR}/started"
exit 0
"""

SYSTEMCTL_STUB = """\
#!/usr/bin/env bash
[[ -f "${STATE_DIR}/started" ]] && exit 0
exit 3
"""


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    path = tmp_path / 'bin'
    path.mkdir()
    _write_executable(path / 'docker', DOCKER_STUB)
    _write_executable(path / 'dockerd', '#!/bin/sh\n')
    _write_executable(path / 'sudo', SUDO_STUB)
    _write_executable(path / 'systemctl', SYSTEMCTL_STUB)
    _write_executable(path / 'sleep', '#!/bin/sh\n')
    _write_executable(
        path / 'tasklist.exe',
        '#!/usr/bin/env bash\necho "tasklist.exe" >> "${CALL_LOG}"\n',
    )
    _write_executable(path / 'id', '#!/bin/sh\necho tester\n')
    return path


def run_helper(
    tmp_path: Path,
    stub_bin: Path,
    command: str,
    *,
    started: bool = False,
) -> subprocess.CompletedProcess[str]:
    if started:
        (tmp_path / 'started').touch()
    env = {
        **os.environ,
        'CALL_LOG': str(tmp_path / 'calls.log'),
        'STATE_DIR': str(tmp_path),
        'PATH': f'{stub_bin}:/usr/bin:/bin',
    }
    env.pop('ON_WINDOWS', None)
    return subprocess.run(  # noqa: S603
        [BASH, '-c', f'source "{DOCKER_SH}"; {command}'],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def calls(tmp_path: Path) -> list[str]:
    log = tmp_path / 'calls.log'
    return log.read_text().splitlines() if log.exists() else []


def test_up_starts_engine_service_without_touching_desktop(
    tmp_path: Path,
    stub_bin: Path,
) -> None:
    result = run_helper(tmp_path, stub_bin, 'docker-up 10')

    assert result.returncode == 0, result.stderr
    assert 'sudo systemctl start docker' in calls(tmp_path)
    assert 'tasklist.exe' not in calls(tmp_path)


def test_up_is_a_no_op_when_engine_already_answers(
    tmp_path: Path,
    stub_bin: Path,
) -> None:
    result = run_helper(tmp_path, stub_bin, 'docker-up', started=True)

    assert result.returncode == 0
    assert 'already up' in result.stdout
    assert not [c for c in calls(tmp_path) if c.startswith('sudo')]


@pytest.mark.parametrize(
    ('started', 'groups', 'expected_fixes'),
    [
        (False, 'tester docker', ['sudo systemctl start docker']),
        (True, 'tester', ['usermod -aG docker']),
        (
            False,
            'tester',
            ['sudo systemctl start docker', 'usermod -aG docker'],
        ),
    ],
)
def test_doctor_names_each_engine_problem(
    tmp_path: Path,
    stub_bin: Path,
    started: bool,  # noqa: FBT001
    groups: str,
    expected_fixes: list[str],
) -> None:
    _write_executable(stub_bin / 'id', f"#!/bin/sh\necho '{groups}'\n")
    # Stopped, or running but refusing a user outside the docker group: the
    # CLI can't reach it either way.
    _write_executable(stub_bin / 'docker', '#!/bin/sh\nexit 1\n')

    result = run_helper(tmp_path, stub_bin, 'docker-doctor', started=started)

    assert result.returncode == 1
    for fix in expected_fixes:
        assert fix in result.stdout
    assert 'tasklist.exe' not in calls(tmp_path)
