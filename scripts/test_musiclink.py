"""Tests for scripts/musiclink.sh.

`curl` is stubbed on PATH so nothing here touches the network.
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent
MUSICLINK = SCRIPTS_DIR / 'musiclink.sh'
EXIT_USAGE = 2

SPOTIFY_URL = 'https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC'
YOUTUBE_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
PAGE_URL = 'https://song.link/s/4uLU6hMCjMI75M1A2tKUQC'

CURL_STUB = """#!/usr/bin/env bash
requested_url=""
for arg in "$@"; do
    [[ "${{arg}}" == https://api.song.link/* ]] && requested_url="${{arg}}"
done
echo "${{requested_url}}" >>"${{STUB_CALLS_FILE}}"

case "${{STUB_MODE:-ok}}" in
ok)
    printf '{body}\n200'
    ;;
not_found)
    printf '{{"statusCode":400,"code":"could_not_resolve_entity"}}\n400'
    ;;
http_error)
    exit 7
    ;;
esac
"""


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    return tmp_path / 'bin'


def install_curl_stub(stub_bin: Path, body: str) -> None:
    stub_bin.mkdir(exist_ok=True)
    path = stub_bin / 'curl'
    path.write_text(CURL_STUB.format(body=body))
    path.chmod(0o755)


def run(
    stub_bin: Path,
    tmp_path: Path,
    args: list[str],
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    calls_file = tmp_path / 'curl_calls'
    calls_file.write_text('')
    env = {
        **os.environ,
        'PATH': f'{stub_bin}{os.pathsep}{os.environ["PATH"]}',
        'STUB_CALLS_FILE': str(calls_file),
        **(env_overrides or {}),
    }
    result = subprocess.run(  # noqa: S603
        [str(MUSICLINK), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    result.calls = calls_file.read_text().splitlines()  # type: ignore[attr-defined]
    return result


@pytest.mark.parametrize('url', [SPOTIFY_URL, YOUTUBE_URL])
def test_prints_the_page_url_for_a_supported_link(
    stub_bin: Path,
    tmp_path: Path,
    url: str,
) -> None:
    install_curl_stub(stub_bin, f'{{"pageUrl":"{PAGE_URL}"}}')
    result = run(stub_bin, tmp_path, [url])
    assert result.returncode == 0
    assert result.stdout.strip() == PAGE_URL


def test_url_encodes_the_link_passed_to_the_api(
    stub_bin: Path,
    tmp_path: Path,
) -> None:
    install_curl_stub(stub_bin, f'{{"pageUrl":"{PAGE_URL}"}}')
    result = run(stub_bin, tmp_path, [YOUTUBE_URL])
    assert len(result.calls) == 1
    assert 'url=https%3A%2F%2Fwww.youtube.com' in result.calls[0]


def test_missing_argument_is_a_usage_error(
    stub_bin: Path,
    tmp_path: Path,
) -> None:
    install_curl_stub(stub_bin, f'{{"pageUrl":"{PAGE_URL}"}}')
    result = run(stub_bin, tmp_path, [])
    assert result.returncode == EXIT_USAGE
    assert 'usage' in result.stderr.lower()
    assert result.calls == []


def test_unresolvable_link_fails_with_a_clear_message(
    stub_bin: Path,
    tmp_path: Path,
) -> None:
    install_curl_stub(stub_bin, '')
    result = run(
        stub_bin,
        tmp_path,
        ['https://example.com/not-music'],
        {'STUB_MODE': 'not_found'},
    )
    assert result.returncode == 1
    assert 'could_not_resolve_entity' in result.stderr


def test_network_failure_is_reported_not_swallowed(
    stub_bin: Path,
    tmp_path: Path,
) -> None:
    install_curl_stub(stub_bin, '')
    result = run(
        stub_bin,
        tmp_path,
        [SPOTIFY_URL],
        {'STUB_MODE': 'http_error'},
    )
    assert result.returncode == 1
    assert 'curl' in result.stderr.lower()


def test_missing_page_url_in_response_is_reported(
    stub_bin: Path,
    tmp_path: Path,
) -> None:
    install_curl_stub(stub_bin, '{"entityUniqueId":"SPOTIFY_SONG::abc"}')
    result = run(stub_bin, tmp_path, [SPOTIFY_URL])
    assert result.returncode == 1
    assert 'pageUrl' in result.stderr
