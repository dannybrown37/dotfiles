"""Tests for install/release_binary.sh.

curl and sudo are stubbed on PATH: curl serves a tarball built here, or for
the GitHub API a release whose asset digest is $DIGEST. sudo runs its command
as-is, so the install lands in a temp dir.
"""

import hashlib
import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

HELPER = Path(__file__).parent.parent / 'install' / 'release_binary.sh'
URL = 'https://example.com/tool.tar.gz'
GH_URL = 'https://github.com/o/r/releases/download/v2.0.0/tool.tar.gz'
CURL_STUB = """#!/usr/bin/env bash
if [[ "$*" == *api.github.com/repos/o/r/releases/tags/v2.0.0* ]]; then
    echo "${RELEASE_JSON}"
    exit 0
fi
echo "curl $*" >> "${CALL_LOG}"
out=''
while [[ $# -gt 0 ]]; do
    [[ "$1" == -*o ]] && { out="$2"; shift; }
    shift
done
if [[ -n "${out}" ]]; then cp "${TARBALL}" "${out}"; else cat "${TARBALL}"; fi
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


def run_install(
    env: dict[str, str],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
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


def install(env: dict[str, str], *args: str) -> str:
    result = run_install(env, *args)
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


def release_json(digest: str | None) -> str:
    asset = {'name': 'tool.tar.gz'}
    if digest:
        asset['digest'] = digest
    return json.dumps({'assets': [asset, {'name': 'other.zip'}]})


def sha256_of(path: str) -> str:
    return 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ('digest', 'returncode', 'message'),
    [
        ('match', 0, ''),
        ('sha256:' + '0' * 64, 1, 'sha256 mismatch'),
        (None, 0, 'no sha256 published'),
    ],
)
def test_verifies_github_asset_digest(
    env: dict[str, str],
    digest: str | None,
    returncode: int,
    message: str,
) -> None:
    if digest == 'match':
        digest = sha256_of(env['TARBALL'])
    env['RELEASE_JSON'] = release_json(digest)

    result = run_install(env, 'tool', GH_URL)

    assert result.returncode == returncode, result.stderr
    assert message in result.stderr
    installed = (Path(env['RELEASE_BIN_DIR']) / 'tool').exists()
    assert installed == (returncode == 0)
