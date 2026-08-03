"""Regression tests for scripts/screenshot_cli.py."""

import os
import pty
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

import screenshot_cli
from screenshot_cli import (
    CAPTURE_NAME_FORMAT,
    IMAGE_SUFFIXES,
    SKIPPED_WINDOWS_USERS,
    ScreenshotError,
    capture_screen,
    free_destination,
    latest_screenshot,
    move_screenshots,
    resolve_screenshot_dir,
    screenshot_paths,
)

CLI = Path(__file__).parent / 'screenshot_cli.py'


def make_image(directory: Path, name: str, mtime: float) -> Path:
    """Create a stub image file with a controlled modification time."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(b'stub')
    os.utime(path, (mtime, mtime))
    return path


@pytest.fixture
def users_root(tmp_path: Path) -> Path:
    return tmp_path / 'mnt' / 'c' / 'Users'


def resolve(users_root: Path, **kwargs: object) -> Path:
    defaults: dict[str, object] = {
        'override': None,
        'users_root': users_root,
        'windows_username': None,
    }
    defaults.update(kwargs)
    return resolve_screenshot_dir(**defaults)  # type: ignore[arg-type]


class TestResolveScreenshotDir:
    def test_override_wins_over_everything(
        self,
        users_root: Path,
        tmp_path: Path,
    ) -> None:
        explicit = tmp_path / 'elsewhere'
        explicit.mkdir()
        make_image(
            users_root / 'danny' / 'Pictures' / 'Screenshots',
            'a.png',
            1,
        )

        assert resolve(users_root, override=str(explicit)) == explicit

    def test_override_that_does_not_exist_is_an_error(
        self,
        users_root: Path,
        tmp_path: Path,
    ) -> None:
        missing = tmp_path / 'nope'

        with pytest.raises(ScreenshotError, match='nope'):
            resolve(users_root, override=str(missing))

    @pytest.mark.parametrize(
        'subpath',
        [
            'OneDrive/Pictures/Screenshots',
            'Pictures/Screenshots',
        ],
    )
    def test_finds_either_onedrive_or_plain_pictures(
        self,
        users_root: Path,
        subpath: str,
    ) -> None:
        expected = users_root / 'danny' / subpath
        make_image(expected, 'a.png', 1)

        assert resolve(users_root, windows_username='danny') == expected

    def test_prefers_the_directory_holding_the_newest_screenshot(
        self,
        users_root: Path,
    ) -> None:
        """A OneDrive migration leaves a stale local dir behind."""
        stale = users_root / 'danny' / 'Pictures' / 'Screenshots'
        fresh = users_root / 'danny' / 'OneDrive' / 'Pictures' / 'Screenshots'
        make_image(stale, 'old.png', 1_000)
        make_image(fresh, 'new.png', 2_000)

        assert resolve(users_root, windows_username='danny') == fresh

    def test_discovers_the_user_when_username_is_unset(
        self,
        users_root: Path,
    ) -> None:
        expected = users_root / 'danny' / 'Pictures' / 'Screenshots'
        make_image(expected, 'a.png', 1)

        assert resolve(users_root) == expected

    @pytest.mark.parametrize('skipped', sorted(SKIPPED_WINDOWS_USERS))
    def test_skips_windows_system_profiles(
        self,
        users_root: Path,
        skipped: str,
    ) -> None:
        make_image(
            users_root / skipped / 'Pictures' / 'Screenshots',
            'a.png',
            2_000,
        )
        real = users_root / 'danny' / 'Pictures' / 'Screenshots'
        make_image(real, 'a.png', 1_000)

        assert resolve(users_root) == real

    def test_named_username_is_not_overridden_by_another_profile(
        self,
        users_root: Path,
    ) -> None:
        make_image(
            users_root / 'other' / 'Pictures' / 'Screenshots',
            'newer.png',
            2_000,
        )
        mine = users_root / 'danny' / 'Pictures' / 'Screenshots'
        make_image(mine, 'older.png', 1_000)

        assert resolve(users_root, windows_username='danny') == mine

    def test_empty_but_existing_directory_still_resolves(
        self,
        users_root: Path,
    ) -> None:
        expected = users_root / 'danny' / 'Pictures' / 'Screenshots'
        expected.mkdir(parents=True)

        assert resolve(users_root, windows_username='danny') == expected

    def test_no_candidate_directory_is_an_error(
        self,
        users_root: Path,
    ) -> None:
        users_root.mkdir(parents=True)

        with pytest.raises(ScreenshotError, match='No screenshots directory'):
            resolve(users_root)


class TestScreenshotPaths:
    def test_returns_newest_first(self, tmp_path: Path) -> None:
        make_image(tmp_path, 'old.png', 1_000)
        make_image(tmp_path, 'new.png', 3_000)
        make_image(tmp_path, 'mid.png', 2_000)

        names = [path.name for path in screenshot_paths(tmp_path)]

        assert names == ['new.png', 'mid.png', 'old.png']

    def test_ties_break_on_name_for_determinism(self, tmp_path: Path) -> None:
        make_image(tmp_path, 'b.png', 1_000)
        make_image(tmp_path, 'a.png', 1_000)

        names = [path.name for path in screenshot_paths(tmp_path)]

        assert names == ['b.png', 'a.png']

    @pytest.mark.parametrize('suffix', sorted(IMAGE_SUFFIXES))
    def test_accepts_every_supported_suffix(
        self,
        tmp_path: Path,
        suffix: str,
    ) -> None:
        make_image(tmp_path, f'shot{suffix}', 1_000)

        assert len(screenshot_paths(tmp_path)) == 1

    def test_suffix_match_is_case_insensitive(self, tmp_path: Path) -> None:
        make_image(tmp_path, 'shot.PNG', 1_000)

        assert len(screenshot_paths(tmp_path)) == 1

    def test_ignores_non_images_and_subdirectories(
        self,
        tmp_path: Path,
    ) -> None:
        make_image(tmp_path, 'shot.png', 1_000)
        (tmp_path / 'notes.txt').write_text('nope')
        (tmp_path / 'nested').mkdir()

        names = [path.name for path in screenshot_paths(tmp_path)]

        assert names == ['shot.png']

    def test_limit_truncates_to_the_newest_n(self, tmp_path: Path) -> None:
        for index in range(5):
            make_image(tmp_path, f'{index}.png', 1_000 + index)

        names = [path.name for path in screenshot_paths(tmp_path, limit=2)]

        assert names == ['4.png', '3.png']


class TestLatestScreenshot:
    def test_returns_the_newest_file(self, tmp_path: Path) -> None:
        make_image(tmp_path, 'old.png', 1_000)
        newest = make_image(tmp_path, 'new.png', 2_000)

        assert latest_screenshot(tmp_path) == newest

    def test_empty_directory_is_an_error(self, tmp_path: Path) -> None:
        with pytest.raises(ScreenshotError, match='No screenshots found'):
            latest_screenshot(tmp_path)


def out_path_from_script(script: str) -> str:
    """The path capture_screen embedded in its PowerShell script."""
    first_line = script.splitlines()[0]
    literal = first_line.split(' = ', 1)[1]
    return literal.strip("'").replace("''", "'")


@pytest.fixture
def fake_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for the Windows side: interop present, paths passthrough."""
    # The stub PowerShell runs under WSL, so it wants a WSL path.
    monkeypatch.setattr(screenshot_cli, 'windows_path', str)
    monkeypatch.setattr(
        screenshot_cli.shutil,
        'which',
        lambda name: f'/fake/{name}',
    )


@pytest.mark.usefixtures('fake_windows')
class TestCaptureScreen:
    """The PowerShell call is stubbed; only our side of it is under test."""

    def runner_writing(
        self,
        written: list[Sequence[str]],
        *,
        returncode: int = 0,
        stderr: str = '',
    ) -> screenshot_cli.Runner:
        """A stub PowerShell that creates the file it was asked to write."""

        def run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
            written.append(command)
            if returncode == 0:
                Path(out_path_from_script(command[-1])).write_bytes(b'png')
            return subprocess.CompletedProcess(
                list(command),
                returncode,
                '',
                stderr,
            )

        return run

    def test_writes_into_the_screenshots_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        written: list[Sequence[str]] = []
        moment = datetime(2026, 8, 2, 22, 13, 5, tzinfo=UTC)

        captured = capture_screen(
            tmp_path,
            now=moment,
            runner=self.runner_writing(written),
        )

        assert captured.parent == tmp_path
        assert captured.name == moment.strftime(CAPTURE_NAME_FORMAT)
        assert captured.is_file()
        assert len(written) == 1

    def test_does_not_clobber_a_same_second_capture(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        moment = datetime(2026, 8, 2, 22, 13, 5, tzinfo=UTC)
        existing = make_image(
            tmp_path,
            moment.strftime(CAPTURE_NAME_FORMAT),
            1_000,
        )

        captured = capture_screen(
            tmp_path,
            now=moment,
            runner=self.runner_writing([]),
        )

        assert captured != existing
        assert captured.name.endswith('-1.png')

    def test_failing_powershell_is_an_error(
        self,
        tmp_path: Path,
    ) -> None:
        runner = self.runner_writing([], returncode=1, stderr='boom')

        with pytest.raises(ScreenshotError, match='boom'):
            capture_screen(tmp_path, runner=runner)

    def test_silent_powershell_that_wrote_nothing_is_an_error(
        self,
        tmp_path: Path,
    ) -> None:
        def wrote_nothing(
            command: Sequence[str],
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(list(command), 0, '', '')

        with pytest.raises(ScreenshotError, match='wrote nothing'):
            capture_screen(tmp_path, runner=wrote_nothing)

    def test_quotes_in_a_path_cannot_break_the_script(
        self,
        tmp_path: Path,
    ) -> None:
        awkward = tmp_path / "danny's shots"
        written: list[Sequence[str]] = []

        captured = capture_screen(
            awkward,
            runner=self.runner_writing(written),
        )

        assert captured.is_file()
        assert "''" in written[0][-1].splitlines()[0]

    def test_without_windows_interop_it_says_so(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(screenshot_cli.shutil, 'which', lambda _: None)

        with pytest.raises(ScreenshotError, match='only works from WSL'):
            capture_screen(tmp_path)


@pytest.mark.usefixtures('fake_windows')
class TestOpenInWindows:
    def recording_runner(
        self,
        seen: list[Sequence[str]],
        *,
        returncode: int = 0,
        stderr: str = '',
    ) -> screenshot_cli.Runner:
        def run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
            seen.append(command)
            return subprocess.CompletedProcess(
                list(command),
                returncode,
                '',
                stderr,
            )

        return run

    def test_hands_the_path_to_start_process(self, tmp_path: Path) -> None:
        shot = make_image(tmp_path, 'shot.png', 1_000)
        seen: list[Sequence[str]] = []

        screenshot_cli.open_in_windows(
            shot,
            runner=self.recording_runner(seen),
        )

        script = seen[0][-1]
        assert script.startswith('Start-Process -FilePath ')
        assert str(shot) in script

    def test_a_failed_open_is_an_error(self, tmp_path: Path) -> None:
        shot = make_image(tmp_path, 'shot.png', 1_000)
        runner = self.recording_runner([], returncode=1, stderr='nope')

        with pytest.raises(ScreenshotError, match='Could not open'):
            screenshot_cli.open_in_windows(shot, runner=runner)


class TestFreeDestination:
    def test_unused_name_is_returned_unchanged(self, tmp_path: Path) -> None:
        target = tmp_path / 'shot.png'

        assert free_destination(target) == target

    def test_taken_name_gets_a_suffix(self, tmp_path: Path) -> None:
        make_image(tmp_path, 'shot.png', 1_000)

        assert free_destination(tmp_path / 'shot.png') == (
            tmp_path / 'shot-1.png'
        )

    def test_suffix_increments_past_earlier_collisions(
        self,
        tmp_path: Path,
    ) -> None:
        make_image(tmp_path, 'shot.png', 1_000)
        make_image(tmp_path, 'shot-1.png', 1_000)

        assert free_destination(tmp_path / 'shot.png') == (
            tmp_path / 'shot-2.png'
        )


class TestMoveScreenshots:
    def test_moves_files_and_returns_new_paths(self, tmp_path: Path) -> None:
        source = make_image(tmp_path / 'shots', 'shot.png', 1_000)
        destination_dir = tmp_path / 'keep'

        moved = move_screenshots([source], destination_dir)

        assert moved == [destination_dir / 'shot.png']
        assert not source.exists()
        assert moved[0].read_bytes() == b'stub'

    def test_creates_a_missing_destination_directory(
        self,
        tmp_path: Path,
    ) -> None:
        source = make_image(tmp_path / 'shots', 'shot.png', 1_000)
        destination_dir = tmp_path / 'nested' / 'keep'

        move_screenshots([source], destination_dir)

        assert (destination_dir / 'shot.png').is_file()

    def test_never_overwrites_an_existing_file(self, tmp_path: Path) -> None:
        source = make_image(tmp_path / 'shots', 'shot.png', 1_000)
        destination_dir = tmp_path / 'keep'
        existing = make_image(destination_dir, 'shot.png', 2_000)
        existing.write_bytes(b'original')

        moved = move_screenshots([source], destination_dir)

        assert moved == [destination_dir / 'shot-1.png']
        assert existing.read_bytes() == b'original'

    def test_missing_source_is_an_error(self, tmp_path: Path) -> None:
        with pytest.raises(ScreenshotError, match='No such file'):
            move_screenshots([tmp_path / 'gone.png'], tmp_path / 'keep')

    def test_destination_that_is_a_file_is_an_error(
        self,
        tmp_path: Path,
    ) -> None:
        source = make_image(tmp_path / 'shots', 'shot.png', 1_000)
        blocker = tmp_path / 'keep'
        blocker.write_text('not a directory')

        with pytest.raises(ScreenshotError, match='Not a directory'):
            move_screenshots([source], blocker)

        assert source.is_file()


class TestCli:
    @pytest.fixture
    def populated(self, tmp_path: Path) -> Path:
        make_image(tmp_path, 'old.png', 1_000)
        make_image(tmp_path, 'new.png', 2_000)
        return tmp_path

    def run(
        self,
        *args: str,
        env_dir: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [sys.executable, str(CLI), *args],
            capture_output=True,
            text=True,
            env={'SCREENSHOT_DIR': str(env_dir), 'PATH': '/usr/bin:/bin'},
            check=False,
        )

    def test_latest_prints_the_newest_path(self, populated: Path) -> None:
        result = self.run('latest', env_dir=populated)

        assert result.returncode == 0
        assert result.stdout.strip() == str(populated / 'new.png')

    def test_piped_output_is_unquoted_even_with_spaces(
        self,
        tmp_path: Path,
    ) -> None:
        """A pipe is a caller parsing paths, not a human pasting one."""
        make_image(tmp_path, 'Screenshot 2026-08-02 221305.png', 1_000)

        result = self.run('latest', env_dir=tmp_path)

        assert result.stdout.strip() == str(
            tmp_path / 'Screenshot 2026-08-02 221305.png',
        )

    def test_terminal_output_is_also_unquoted(self, tmp_path: Path) -> None:
        """Regression: quoting a path stops a terminal linkifying it.

        Wrapping the path in quotes for the human made it unclickable,
        which defeats the point -- the clipboard carries the quoted form.
        """
        name = 'Screenshot 2026-08-02 221305.png'
        make_image(tmp_path, name, 1_000)
        primary, secondary = pty.openpty()

        try:
            subprocess.run(  # noqa: S603
                [sys.executable, str(CLI), 'latest'],
                stdout=secondary,
                stderr=subprocess.DEVNULL,
                # No clip.exe on this PATH, so the clipboard is left alone.
                env={'SCREENSHOT_DIR': str(tmp_path), 'PATH': '/usr/bin:/bin'},
                check=True,
            )
            os.close(secondary)
            printed = os.read(primary, 4096).decode()
        finally:
            os.close(primary)

        assert printed.strip() == str(tmp_path / name)

    def test_dir_prints_the_resolved_directory(self, populated: Path) -> None:
        result = self.run('dir', env_dir=populated)

        assert result.returncode == 0
        assert result.stdout.strip() == str(populated)

    def test_list_prints_newest_first(self, populated: Path) -> None:
        result = self.run('list', env_dir=populated)

        assert result.returncode == 0
        assert result.stdout.splitlines() == [
            str(populated / 'new.png'),
            str(populated / 'old.png'),
        ]

    def test_list_honours_the_count_flag(self, populated: Path) -> None:
        result = self.run('list', '-n', '1', env_dir=populated)

        assert result.stdout.splitlines() == [str(populated / 'new.png')]

    def test_move_relocates_the_given_paths(
        self,
        populated: Path,
        tmp_path: Path,
    ) -> None:
        destination_dir = tmp_path / 'keep'

        result = self.run(
            'move',
            '--dest',
            str(destination_dir),
            '--',
            str(populated / 'new.png'),
            env_dir=populated,
        )

        assert result.returncode == 0
        assert result.stdout.strip() == str(destination_dir / 'new.png')
        assert not (populated / 'new.png').exists()
        assert (populated / 'old.png').exists()

    def test_move_without_a_destination_exits_nonzero(
        self,
        populated: Path,
    ) -> None:
        result = self.run(
            'move',
            str(populated / 'new.png'),
            env_dir=populated,
        )

        assert result.returncode != 0
        assert (populated / 'new.png').exists()

    def test_move_without_paths_exits_nonzero(self, populated: Path) -> None:
        result = self.run(
            'move',
            '--dest',
            str(populated / 'keep'),
            env_dir=populated,
        )

        assert result.returncode != 0

    def test_empty_directory_exits_nonzero_with_a_message(
        self,
        tmp_path: Path,
    ) -> None:
        result = self.run('latest', env_dir=tmp_path)

        assert result.returncode == 1
        assert 'No screenshots found' in result.stderr
        assert not result.stdout.strip()
