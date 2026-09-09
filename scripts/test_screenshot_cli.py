"""Tests for screenshot_cli. Pure-logic functions only (no Windows interop)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from screenshot_cli import (
    IMAGE_SUFFIXES,
    NO_SCREENSHOTS_YET,
    SKIPPED_WINDOWS_USERS,
    ScreenshotError,
    candidate_dirs,
    free_destination,
    latest_screenshot,
    move_screenshots,
    newest_mtime,
    powershell_string_literal,
    resolve_screenshot_dir,
    screenshot_paths,
    user_profiles,
)


# -- user_profiles --


def test_user_profiles_named_hit(tmp_path: Path) -> None:
    (tmp_path / 'danny').mkdir()
    assert user_profiles(tmp_path, 'danny') == [tmp_path / 'danny']


def test_user_profiles_named_miss(tmp_path: Path) -> None:
    assert user_profiles(tmp_path, 'ghost') == []


def test_user_profiles_scan_skips_system(tmp_path: Path) -> None:
    for name in ('danny', 'Public', 'Default'):
        (tmp_path / name).mkdir()
    result = user_profiles(tmp_path, None)
    assert result == [tmp_path / 'danny']


def test_user_profiles_nonexistent_root() -> None:
    assert user_profiles(Path('/no/such/root'), None) == []


# -- candidate_dirs --


def test_candidate_dirs_finds_both_subpaths(tmp_path: Path) -> None:
    pictures = tmp_path / 'user' / 'Pictures' / 'Screenshots'
    onedrive = tmp_path / 'user' / 'OneDrive' / 'Pictures' / 'Screenshots'
    pictures.mkdir(parents=True)
    onedrive.mkdir(parents=True)
    result = candidate_dirs(tmp_path, 'user')
    assert set(result) == {pictures, onedrive}


def test_candidate_dirs_empty_when_no_match(tmp_path: Path) -> None:
    (tmp_path / 'user').mkdir()
    assert candidate_dirs(tmp_path, 'user') == []


# -- screenshot_paths --


def test_screenshot_paths_sorted_newest_first(tmp_path: Path) -> None:
    names = ['old.png', 'mid.png', 'new.png']
    for i, name in enumerate(names):
        p = tmp_path / name
        p.write_bytes(b'x')
        import os

        os.utime(p, (i * 100, i * 100))
    result = screenshot_paths(tmp_path)
    assert [p.name for p in result] == ['new.png', 'mid.png', 'old.png']


def test_screenshot_paths_filters_non_images(tmp_path: Path) -> None:
    (tmp_path / 'readme.txt').write_text('hi')
    (tmp_path / 'shot.png').write_bytes(b'x')
    result = screenshot_paths(tmp_path)
    assert len(result) == 1
    assert result[0].name == 'shot.png'


def test_screenshot_paths_limit(tmp_path: Path) -> None:
    expected = 2
    for i in range(5):
        (tmp_path / f's{i}.png').write_bytes(b'x')
    assert len(screenshot_paths(tmp_path, limit=2)) == expected


@pytest.mark.parametrize('suffix', sorted(IMAGE_SUFFIXES))
def test_screenshot_paths_accepts_all_image_suffixes(
    tmp_path: Path,
    suffix: str,
) -> None:
    (tmp_path / f'img{suffix}').write_bytes(b'x')
    assert len(screenshot_paths(tmp_path)) == 1


# -- newest_mtime --


def test_newest_mtime_empty_dir(tmp_path: Path) -> None:
    assert newest_mtime(tmp_path) == NO_SCREENSHOTS_YET


def test_newest_mtime_returns_float(tmp_path: Path) -> None:
    (tmp_path / 'a.png').write_bytes(b'x')
    assert isinstance(newest_mtime(tmp_path), float)
    assert newest_mtime(tmp_path) != NO_SCREENSHOTS_YET


# -- latest_screenshot --


def test_latest_screenshot_raises_on_empty(tmp_path: Path) -> None:
    with pytest.raises(ScreenshotError, match='No screenshots found'):
        latest_screenshot(tmp_path)


def test_latest_screenshot_returns_newest(tmp_path: Path) -> None:
    import os

    for i, name in enumerate(['old.png', 'new.png']):
        p = tmp_path / name
        p.write_bytes(b'x')
        os.utime(p, (i * 100, i * 100))
    assert latest_screenshot(tmp_path).name == 'new.png'


# -- resolve_screenshot_dir --


def test_resolve_screenshot_dir_override(tmp_path: Path) -> None:
    result = resolve_screenshot_dir(str(tmp_path), Path('/unused'), None)
    assert result == tmp_path


def test_resolve_screenshot_dir_override_bad_path() -> None:
    with pytest.raises(ScreenshotError, match='Not a directory'):
        resolve_screenshot_dir('/no/such/dir', Path('/unused'), None)


def test_resolve_screenshot_dir_no_candidates(tmp_path: Path) -> None:
    with pytest.raises(ScreenshotError, match='No screenshots directory'):
        resolve_screenshot_dir(None, tmp_path, None)


def test_resolve_screenshot_dir_picks_newest(tmp_path: Path) -> None:
    import os

    user = tmp_path / 'user'
    pics = user / 'Pictures' / 'Screenshots'
    od = user / 'OneDrive' / 'Pictures' / 'Screenshots'
    pics.mkdir(parents=True)
    od.mkdir(parents=True)
    old = pics / 'old.png'
    old.write_bytes(b'x')
    os.utime(old, (100, 100))
    new = od / 'new.png'
    new.write_bytes(b'x')
    os.utime(new, (200, 200))
    result = resolve_screenshot_dir(None, tmp_path, 'user')
    assert result == od


# -- free_destination --


def test_free_destination_no_conflict(tmp_path: Path) -> None:
    target = tmp_path / 'shot.png'
    assert free_destination(target) == target


def test_free_destination_suffixes_on_conflict(tmp_path: Path) -> None:
    target = tmp_path / 'shot.png'
    target.write_bytes(b'x')
    result = free_destination(target)
    assert result == tmp_path / 'shot-1.png'


def test_free_destination_increments(tmp_path: Path) -> None:
    for name in ['shot.png', 'shot-1.png', 'shot-2.png']:
        (tmp_path / name).write_bytes(b'x')
    assert free_destination(tmp_path / 'shot.png') == tmp_path / 'shot-3.png'


# -- move_screenshots --


def test_move_screenshots_moves_files(tmp_path: Path) -> None:
    src = tmp_path / 'src'
    dst = tmp_path / 'dst'
    src.mkdir()
    (src / 'a.png').write_bytes(b'img')
    moved = move_screenshots([src / 'a.png'], dst)
    assert len(moved) == 1
    assert moved[0].is_file()
    assert not (src / 'a.png').exists()


def test_move_screenshots_creates_dest(tmp_path: Path) -> None:
    src = tmp_path / 'a.png'
    src.write_bytes(b'x')
    dst = tmp_path / 'new' / 'dir'
    move_screenshots([src], dst)
    assert (dst / 'a.png').is_file()


def test_move_screenshots_deconflicts(tmp_path: Path) -> None:
    src = tmp_path / 'src'
    dst = tmp_path / 'dst'
    src.mkdir()
    dst.mkdir()
    (dst / 'a.png').write_bytes(b'existing')
    (src / 'a.png').write_bytes(b'new')
    moved = move_screenshots([src / 'a.png'], dst)
    assert moved[0].name == 'a-1.png'


def test_move_screenshots_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ScreenshotError, match='No such file'):
        move_screenshots([tmp_path / 'gone.png'], tmp_path / 'dst')


def test_move_screenshots_rejects_file_as_dest(tmp_path: Path) -> None:
    src = tmp_path / 'a.png'
    src.write_bytes(b'x')
    dst = tmp_path / 'notadir'
    dst.write_bytes(b'x')
    with pytest.raises(ScreenshotError, match='Not a directory'):
        move_screenshots([src], dst)


# -- powershell_string_literal --


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('simple', "'simple'"),
        ("it's here", "'it''s here'"),
        ("a''b", "'a''''b'"),
        ('$var', "'$var'"),
    ],
)
def test_powershell_string_literal(value: str, expected: str) -> None:
    assert powershell_string_literal(value) == expected


# -- SKIPPED_WINDOWS_USERS is a frozenset --


def test_skipped_users_is_frozen() -> None:
    assert isinstance(SKIPPED_WINDOWS_USERS, frozenset)


# -- main() arg parsing --


def test_main_no_args_defaults_to_take() -> None:
    with (
        patch('screenshot_cli.capture_screen') as mock_capture,
        patch('screenshot_cli.resolve_screenshot_dir') as mock_resolve,
        patch('screenshot_cli.emit_path'),
        patch('sys.argv', ['screenshot_cli.py']),
    ):
        mock_resolve.return_value = Path('/fake')
        mock_capture.return_value = Path('/fake/shot.png')
        from screenshot_cli import main

        main()
        mock_capture.assert_called_once_with(Path('/fake'))
