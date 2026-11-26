"""Tests for install/curl_retry.sh.

curl is stubbed on PATH: it logs its args, writes $BODY to its -o target, and
exits $CURL_RC.
"""

import os
import subprocess
from pathlib import Path

import pytest

HELPER = Path(__file__).parent.parent / 'install' / 'curl_retry.sh'
CURL_STUB = """#!/usr/bin/env bash
echo "$*" > "${CALL_LOG}"
out=/dev/stdout
while [[ $# -gt 0 ]]; do
    [[ "$1" == -o ]] && { out="$2"; shift; }
    shift
done
printf '%s' "${BODY}" > "${out}"
exit "${CURL_RC}"
"""


def run_buffered(
    tmp_path: Path,
    curl_rc: int,
) -> subprocess.CompletedProcess[str]:
    stub_bin = tmp_path / 'bin'
    stub_bin.mkdir()
    (stub_bin / 'curl').write_text(CURL_STUB)
    (stub_bin / 'curl').chmod(0o755)
    return subprocess.run(  # noqa: S603
        [  # noqa: S607
            'bash',
            '-c',
            f'source {HELPER} && curl_buffered "$@"',
            '_',
            '-fsSL',
            'https://example.com/install.sh',
        ],
        env={
            **os.environ,
            'PATH': f'{stub_bin}:{os.environ["PATH"]}',
            'CALL_LOG': str(tmp_path / 'calls'),
            'BODY': 'echo half',
            'CURL_RC': str(curl_rc),
            'TMPDIR': str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ('curl_rc', 'stdout'),
    [
        (0, 'echo half'),
        (56, ''),
    ],
)
def test_prints_body_only_when_download_completes(
    tmp_path: Path,
    curl_rc: int,
    stdout: str,
) -> None:
    result = run_buffered(tmp_path, curl_rc)

    assert result.returncode == curl_rc
    assert result.stdout == stdout


def test_passes_retry_flags_and_caller_args(tmp_path: Path) -> None:
    run_buffered(tmp_path, 0)

    args = (tmp_path / 'calls').read_text()
    assert args.startswith(
        '--retry 3 --retry-all-errors --retry-delay 2 -fsSL ',
    )
    assert 'https://example.com/install.sh -o ' in args


def test_removes_temp_file(tmp_path: Path) -> None:
    run_buffered(tmp_path, 56)

    assert sorted(p.name for p in tmp_path.iterdir()) == ['bin', 'calls']
