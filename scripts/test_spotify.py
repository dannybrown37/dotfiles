"""Tests for bin/spotify.sh's playing-track functions.

Covers spotify_copy_playing_link and spotify_now_playing_markdown.
spotify_player and the clipboard/musiclink scripts they shell out to are all
stubbed, so nothing here touches Spotify's API, the Windows clipboard, or
the network.
"""

import json
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
TRACK_TITLE = 'The Fox in Motion'
ARTISTS = ['Hop Along']
NO_PLAYBACK_JSON = 'null'


def playback_json(
    title: str = TRACK_TITLE,
    artists: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            'item': {
                'name': title,
                'artists': [{'name': a} for a in (artists or ARTISTS)],
                'external_urls': {'spotify': TRACK_URL},
            },
        },
    )


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
    playback: str,
    exit_code: int = 0,
) -> None:
    path = stub_bin / 'spotify_player'
    _write_executable(
        path,
        f"#!/usr/bin/env bash\necho '{playback}'\nexit {exit_code}\n",
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
    function: str,
    args: list[str],
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        'PATH': f'{stub_bin}:/usr/bin:/bin',
        'DOTFILES_DIR': str(dotfiles_dir),
    }
    script = f'source "{SPOTIFY_SH}"; {function} "$@"'
    return subprocess.run(  # noqa: S603
        [BASH, '-c', script, function, *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class TestSpotifyCopyPlayingLink:
    def test_copies_the_currently_playing_track_link(
        self,
        stub_bin: Path,
        dotfiles_dir: Path,
        tmp_path: Path,
    ) -> None:
        install_spotify_player_stub(stub_bin, playback_json())
        capture_file = tmp_path / 'clipboard'
        install_clipboard_stub(dotfiles_dir, capture_file)

        result = run(stub_bin, dotfiles_dir, 'spotify_copy_playing_link', [])

        assert result.returncode == 0, result.stderr
        assert capture_file.read_text() == TRACK_URL
        assert result.stdout.strip() == TRACK_URL

    def test_musiclink_flag_converts_before_copying(
        self,
        stub_bin: Path,
        dotfiles_dir: Path,
        tmp_path: Path,
    ) -> None:
        install_spotify_player_stub(stub_bin, playback_json())
        install_musiclink_stub(dotfiles_dir, MUSICLINK_URL)
        capture_file = tmp_path / 'clipboard'
        install_clipboard_stub(dotfiles_dir, capture_file)

        result = run(
            stub_bin,
            dotfiles_dir,
            'spotify_copy_playing_link',
            ['-m'],
        )

        assert result.returncode == 0, result.stderr
        assert capture_file.read_text() == MUSICLINK_URL

    def test_unknown_flag_is_a_usage_error(
        self,
        stub_bin: Path,
        dotfiles_dir: Path,
    ) -> None:
        install_spotify_player_stub(stub_bin, playback_json())

        result = run(
            stub_bin,
            dotfiles_dir,
            'spotify_copy_playing_link',
            ['--bogus'],
        )

        assert result.returncode == EXIT_USAGE
        assert 'usage' in result.stderr.lower()


class TestSpotifyNowPlayingMarkdown:
    def test_copies_the_song_on_right_now_markdown_blurb(
        self,
        stub_bin: Path,
        dotfiles_dir: Path,
        tmp_path: Path,
    ) -> None:
        install_spotify_player_stub(stub_bin, playback_json())
        install_musiclink_stub(dotfiles_dir, MUSICLINK_URL)
        capture_file = tmp_path / 'clipboard'
        install_clipboard_stub(dotfiles_dir, capture_file)

        result = run(
            stub_bin,
            dotfiles_dir,
            'spotify_now_playing_markdown',
            [],
        )

        blurb = f'[{TRACK_TITLE}]({MUSICLINK_URL})" by Hop Along'
        expected = f'Song On Right Now: "{blurb}'
        assert result.returncode == 0, result.stderr
        assert capture_file.read_text() == expected
        assert result.stdout.strip() == expected

    def test_joins_multiple_artists_with_a_comma(
        self,
        stub_bin: Path,
        dotfiles_dir: Path,
        tmp_path: Path,
    ) -> None:
        install_spotify_player_stub(
            stub_bin,
            playback_json(artists=['Hop Along', 'Frances Quinlan']),
        )
        install_musiclink_stub(dotfiles_dir, MUSICLINK_URL)
        install_clipboard_stub(dotfiles_dir, tmp_path / 'clipboard')

        result = run(
            stub_bin,
            dotfiles_dir,
            'spotify_now_playing_markdown',
            [],
        )

        assert result.returncode == 0, result.stderr
        assert 'by Hop Along, Frances Quinlan' in result.stdout


@pytest.mark.parametrize(
    'function',
    ['spotify_copy_playing_link', 'spotify_now_playing_markdown'],
)
class TestSharedPlaybackErrors:
    def test_no_active_playback_is_reported_not_swallowed(
        self,
        stub_bin: Path,
        dotfiles_dir: Path,
        function: str,
    ) -> None:
        install_spotify_player_stub(stub_bin, NO_PLAYBACK_JSON)

        result = run(stub_bin, dotfiles_dir, function, [])

        assert result.returncode == 1
        assert 'no track currently playing' in result.stderr

    def test_spotify_player_failure_is_reported(
        self,
        stub_bin: Path,
        dotfiles_dir: Path,
        function: str,
    ) -> None:
        install_spotify_player_stub(stub_bin, 'boom', exit_code=1)

        result = run(stub_bin, dotfiles_dir, function, [])

        assert result.returncode == 1
        assert 'spotify_player get key playback failed' in result.stderr
        assert 'boom' in result.stderr

    def test_missing_spotify_player_binary_is_reported(
        self,
        stub_bin: Path,
        dotfiles_dir: Path,
        function: str,
    ) -> None:
        result = run(stub_bin, dotfiles_dir, function, [])

        assert result.returncode == 1
        assert 'spotify_player not found' in result.stderr
