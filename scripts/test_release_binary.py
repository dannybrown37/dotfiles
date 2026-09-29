"""Tests for install/release_binary.sh.

curl and sudo are stubbed on PATH: curl serves a tarball built here, sudo runs
its command as-is so the install lands in a temp dir.
"""

import os
import subprocess
import tarfile
from pathlib import Path

import pytest

HELPER = Path(__file__).parent.parent / 'install' / 'release_binary.sh'
URL = 'https://example.com/tool.tar.gz'
CURL_STUB = """#!/usr/bin/env bash
echo "curl $*" >> "${CALL_LOG}"
cat "${TARBALL}"
"""
SUDO_STUB = '#!/usr/bin/env bash\n"$@"\n'


def fake_binary(path: Path, version: str) -> None:
    path.write_text(f'#!/usr/bin/env bash\necho "tool {version}"\n')
    path.chmod(0o755)


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    stub_bin = tmp_path / 'bin'
    stub_bin.mkdir()
    for name, body in (('curl', CURL_STUB), ('sudo', SUDO_STUB)):
        (stub_bin / name).write_text(body)
        (stub_bin / name).chmod(0o755)
    install_dir = tmp_path / 'install'
    install_dir.mkdir()
    built = tmp_path / 'tool'
    fake_binary(built, '2.0.0')
    tarball = tmp_path / 'tool.tar.gz'
    with tarfile.open(tarball, 'w:gz') as tar:
        tar.add(built, arcname='tool-2.0.0/tool')
    return {
        **os.environ,
        'PATH': f'{install_dir}:{stub_bin}:{os.environ["PATH"]}',
        'CALL_LOG': str(tmp_path / 'calls'),
        'TARBALL': str(tarball),
        'RELEASE_BIN_DIR': str(install_dir),
    }


def install(env: dict[str, str], *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            'bash',
            '-c',
            f'source {HELPER} && install_release_binary "$@"',
            '_',
            *args,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return subprocess.run(
        ['tool'],  # noqa: S607
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.mark.parametrize(
    ('installed', 'args', 'expected', 'downloads'),
    [
        (None, [], 'tool 2.0.0', True),
        ('1.0.0', [], 'tool 1.0.0', False),
        ('1.0.0', ['2.0.0'], 'tool 2.0.0', True),
        ('2.0.0', ['2.0.0'], 'tool 2.0.0', False),
    ],
)
def test_installs_or_upgrades_only_when_needed(
    env: dict[str, str],
    *,
    installed: str | None,
    args: list[str],
    expected: str,
    downloads: bool,
) -> None:
    if installed:
        fake_binary(Path(env['RELEASE_BIN_DIR']) / 'tool', installed)

    assert install(env, 'tool', URL, *args) == expected
    assert Path(env['CALL_LOG']).exists() == downloads
