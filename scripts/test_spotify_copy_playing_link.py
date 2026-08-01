"""Tests for bin/spotify.sh's spotify_copy_playing_link function.

spotify_player and the clipboard/musiclink scripts it shells out to are all
stubbed, so nothing here touches Spotify's API, the Windows clipboard, or
the network.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SPOTIFY_SH = REPO_ROOT / 'bin' / 'spotify.sh'
BASH = shutil.which('bash')
EXIT_USAGE = 2

TRACK_URL = 'https://open.spotify.com/track/7si4G8Ky9JCTgzlg8BtFTq'
MUSICLINK_URL = 'https://song.link/s/7si4G8Ky9JCTgzlg8BtFTq'
PLAYBACK_JSON = f'{{"item":{{"external_urls":{{"spotify":"{TRACK_URL}"}}}}}}'
NO_PLAYBACK_JSON = 'null'


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(
        path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH,
    )


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    path = tmp_path / 'bin'
    path.mkdir()
    return path


@pytest.fixture
def dotfiles_dir(tmp_path: Path) -> Path:
    path = tmp_path / 'dotfiles'
    (path / 'scripts').mkdir(parents=True)
    return path


def install_spotify_player_stub(
    stub_bin: Path,
    playback_json: str,
    exit_code: int = 0,
) -> None:
    path = stub_bin / 'spotify_player'
    _write_executable(
        path,
        f"#!/usr/bin/env bash\necho '{playback_json}'\nexit {exit_code}\n",
    )


def install_clipboard_stub(dotfiles_dir: Path, capture_file: Path) -> None:
    path = dotfiles_dir / 'scripts' / 'tmux-copy-to-clipboard.sh'
    _write_executable(path, f"#!/usr/bin/env bash\ncat > '{capture_file}'\n")


def install_musiclink_stub(dotfiles_dir: Path, output: str) -> None:
    path = dotfiles_dir / 'scripts' / 'musiclink.sh'
    _write_executable(path, f"#!/usr/bin/env bash\necho '{output}'\n")


def run(
    stub_bin: Path,
    dotfiles_dir: Path,
    args: list[str],
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        'PATH': f'{stub_bin}:/usr/bin:/bin',
        'DOTFILES_DIR': str(dotfiles_dir),
    }
    script = f'source "{SPOTIFY_SH}"; spotify_copy_playing_link "$@"'
    return subprocess.run(  # noqa: S603
        [BASH, '-c', script, 'spotify_copy_playing_link', *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_copies_the_currently_playing_track_link(
    stub_bin: Path,
    dotfiles_dir: Path,
    tmp_path: Path,
) -> None:
    install_spotify_player_stub(stub_bin, PLAYBACK_JSON)
    capture_file = tmp_path / 'clipboard'
    install_clipboard_stub(dotfiles_dir, capture_file)

    result = run(stub_bin, dotfiles_dir, [])

    assert result.returncode == 0, result.stderr
    assert capture_file.read_text() == TRACK_URL
    assert TRACK_URL in result.stdout


def test_musiclink_flag_converts_before_copying(
    stub_bin: Path,
    dotfiles_dir: Path,
    tmp_path: Path,
) -> None:
    install_spotify_player_stub(stub_bin, PLAYBACK_JSON)
    install_musiclink_stub(dotfiles_dir, MUSICLINK_URL)
    capture_file = tmp_path / 'clipboard'
    install_clipboard_stub(dotfiles_dir, capture_file)

    result = run(stub_bin, dotfiles_dir, ['-m'])

    assert result.returncode == 0, result.stderr
    assert capture_file.read_text() == MUSICLINK_URL


def test_no_active_playback_is_reported_not_swallowed(
    stub_bin: Path,
    dotfiles_dir: Path,
) -> None:
    install_spotify_player_stub(stub_bin, NO_PLAYBACK_JSON)

    result = run(stub_bin, dotfiles_dir, [])

    assert result.returncode == 1
    assert 'no track currently playing' in result.stderr


def test_spotify_player_failure_is_reported(
    stub_bin: Path,
    dotfiles_dir: Path,
) -> None:
    install_spotify_player_stub(stub_bin, 'boom', exit_code=1)

    result = run(stub_bin, dotfiles_dir, [])

    assert result.returncode == 1
    assert 'spotify_player get key playback failed' in result.stderr
    assert 'boom' in result.stderr


def test_missing_spotify_player_binary_is_reported(
    stub_bin: Path,
    dotfiles_dir: Path,
) -> None:
    result = run(stub_bin, dotfiles_dir, [])

    assert result.returncode == 1
    assert 'spotify_player not found' in result.stderr


def test_unknown_flag_is_a_usage_error(
    stub_bin: Path,
    dotfiles_dir: Path,
) -> None:
    install_spotify_player_stub(stub_bin, PLAYBACK_JSON)

    result = run(stub_bin, dotfiles_dir, ['--bogus'])

    assert result.returncode == EXIT_USAGE
    assert 'usage' in result.stderr.lower()
