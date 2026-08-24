"""Integration tests for the tmux clipboard copy/paste scripts.

Windows clipboard access (Set-Clipboard/Get-Clipboard) throws a transient
"OpenClipboard failed" whenever another process (clipboard history,
antivirus, OneDrive, ...) has the clipboard locked for a few ms. These
scripts must retry through that instead of failing on the first collision,
and only give up (loudly) if the failure is not transient.

powershell.exe is stubbed on PATH so no real Windows clipboard is touched.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent
COPY_SCRIPT = SCRIPTS_DIR / 'tmux-copy-to-clipboard.sh'
PASTE_SCRIPT = SCRIPTS_DIR / 'tmux-paste-from-clipboard.sh'
WSLPATH = shutil.which('wslpath')
MAX_RETRY_ATTEMPTS = 10

pytestmark = pytest.mark.skipif(
    WSLPATH is None,
    reason='these scripts only run under WSL',
)

COPY_STUB = """#!/usr/bin/env bash
set -uo pipefail
count_file="${STUB_COUNTER_FILE}"
count=$(( $(cat "${count_file}" 2>/dev/null || echo 0) + 1 ))
echo "${count}" > "${count_file}"

if (( count <= "${STUB_FAIL_COUNT:-0}" )); then
    echo "Set-Clipboard : OpenClipboard failed" >&2
    exit 1
fi

if [[ -n "${STUB_CAPTURE_FILE:-}" ]]; then
    command_arg="${3:-}"
    win_path=$(grep -oP "(?<=-Path ')[^']+" <<<"${command_arg}")
    linux_path=$(wslpath -u "${win_path}")
    cat "${linux_path}" > "${STUB_CAPTURE_FILE}"
fi
exit 0
"""

PASTE_STUB = """#!/usr/bin/env bash
set -uo pipefail
count_file="${STUB_COUNTER_FILE}"
count=$(( $(cat "${count_file}" 2>/dev/null || echo 0) + 1 ))
echo "${count}" > "${count_file}"

if (( count <= "${STUB_FAIL_COUNT:-0}" )); then
    echo "Get-Clipboard : OpenClipboard failed" >&2
    exit 1
fi

printf '%s' "${STUB_CLIPBOARD_CONTENT:-}"
exit 0
"""


def install_stub(bin_dir: Path, body: str) -> None:
    path = bin_dir / 'powershell.exe'
    path.write_text(body)
    path.chmod(0o755)


def _path_without(binary: str) -> str:
    """Return $PATH with directories containing *binary* removed."""
    return os.pathsep.join(
        d
        for d in os.environ['PATH'].split(os.pathsep)
        if not (Path(d) / binary).is_file()
    )


def run_script(
    script: Path,
    bin_dir: Path,
    env_overrides: dict[str, str],
    stdin_text: str = '',
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        'PATH': f'{bin_dir}{os.pathsep}{_path_without("win32yank.exe")}',
        **env_overrides,
    }
    return subprocess.run(  # noqa: S603
        [str(script)],
        input=stdin_text,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def bin_dir(tmp_path: Path) -> Path:
    path = tmp_path / 'bin'
    path.mkdir()
    return path


@pytest.mark.parametrize('fail_count', [0, 1, 4])
def test_paste_retries_through_transient_clipboard_lock(
    tmp_path: Path,
    bin_dir: Path,
    fail_count: int,
) -> None:
    install_stub(bin_dir, PASTE_STUB)
    counter_file = tmp_path / 'count'
    result = run_script(
        PASTE_SCRIPT,
        bin_dir,
        {
            'STUB_COUNTER_FILE': str(counter_file),
            'STUB_FAIL_COUNT': str(fail_count),
            'STUB_CLIPBOARD_CONTENT': 'hello\r\nworld\r\n',
        },
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == 'hello\nworld\n'


def test_paste_gives_up_after_max_attempts(
    tmp_path: Path,
    bin_dir: Path,
) -> None:
    install_stub(bin_dir, PASTE_STUB)
    counter_file = tmp_path / 'count'
    result = run_script(
        PASTE_SCRIPT,
        bin_dir,
        {
            'STUB_COUNTER_FILE': str(counter_file),
            'STUB_FAIL_COUNT': '999',
        },
    )
    assert result.returncode != 0
    assert 'OpenClipboard failed' in result.stderr
    assert int(counter_file.read_text()) <= MAX_RETRY_ATTEMPTS, (
        'should give up rather than retry forever'
    )


@pytest.mark.parametrize('fail_count', [0, 1, 4])
def test_copy_retries_through_transient_clipboard_lock(
    tmp_path: Path,
    bin_dir: Path,
    fail_count: int,
) -> None:
    install_stub(bin_dir, COPY_STUB)
    counter_file = tmp_path / 'count'
    capture_file = tmp_path / 'captured'
    result = run_script(
        COPY_SCRIPT,
        bin_dir,
        {
            'STUB_COUNTER_FILE': str(counter_file),
            'STUB_FAIL_COUNT': str(fail_count),
            'STUB_CAPTURE_FILE': str(capture_file),
        },
        stdin_text='copied text\n',
    )
    assert result.returncode == 0, result.stderr
    assert capture_file.read_text() == 'copied text\n'


def test_copy_gives_up_after_max_attempts(
    tmp_path: Path,
    bin_dir: Path,
) -> None:
    install_stub(bin_dir, COPY_STUB)
    counter_file = tmp_path / 'count'
    result = run_script(
        COPY_SCRIPT,
        bin_dir,
        {
            'STUB_COUNTER_FILE': str(counter_file),
            'STUB_FAIL_COUNT': '999',
        },
        stdin_text='copied text\n',
    )
    assert result.returncode != 0
    assert 'OpenClipboard failed' in result.stderr
    assert int(counter_file.read_text()) <= MAX_RETRY_ATTEMPTS, (
        'should give up rather than retry forever'
    )
