"""Tests for the link_config config-symlink helper."""

import subprocess
from pathlib import Path

import pytest

HELPER = Path(__file__).resolve().parent.parent / 'install' / 'symlinks.sh'


def link_config(src: Path, dest: Path) -> subprocess.CompletedProcess[str]:
    """Source the helper in a fresh shell and run it once."""
    return subprocess.run(  # noqa: S603
        [
            '/usr/bin/env',
            'bash',
            '-c',
            f'source "{HELPER}"; link_config "{src}" "{dest}"',
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def src(tmp_path: Path) -> Path:
    path = tmp_path / 'repo' / 'config' / 'thing.toml'
    path.parent.mkdir(parents=True)
    path.write_text('managed = true\n')
    return path


def test_creates_link_and_missing_parent_dirs(
    tmp_path: Path,
    src: Path,
) -> None:
    dest = tmp_path / 'home' / '.config' / 'deep' / 'thing.toml'

    result = link_config(src, dest)

    assert result.returncode == 0
    assert dest.is_symlink()
    assert dest.resolve() == src.resolve()


def test_is_idempotent(tmp_path: Path, src: Path) -> None:
    dest = tmp_path / 'home' / 'thing.toml'

    link_config(src, dest)
    second = link_config(src, dest)

    assert second.returncode == 0
    assert 'already symlinked' in second.stdout
    assert dest.resolve() == src.resolve()


def test_repoints_a_stale_link(tmp_path: Path, src: Path) -> None:
    old = tmp_path / 'repo' / 'config' / 'old.toml'
    old.write_text('stale\n')
    dest = tmp_path / 'home' / 'thing.toml'
    dest.parent.mkdir(parents=True)
    dest.symlink_to(old)

    result = link_config(src, dest)

    assert result.returncode == 0
    assert dest.resolve() == src.resolve()


def test_repointing_a_directory_link_does_not_nest(tmp_path: Path) -> None:
    """Without `ln -sfn`, this writes the link *inside* the old target dir."""
    old_dir = tmp_path / 'repo' / 'old_nvim'
    old_dir.mkdir(parents=True)
    new_dir = tmp_path / 'repo' / 'nvim'
    new_dir.mkdir()
    dest = tmp_path / 'home' / '.config' / 'nvim'
    dest.parent.mkdir(parents=True)
    dest.symlink_to(old_dir)

    result = link_config(new_dir, dest)

    assert result.returncode == 0
    assert dest.resolve() == new_dir.resolve()
    assert not (old_dir / 'nvim').exists()


def test_refuses_to_clobber_a_real_file(tmp_path: Path, src: Path) -> None:
    dest = tmp_path / 'home' / 'thing.toml'
    dest.parent.mkdir(parents=True)
    dest.write_text('hand-written, precious\n')

    result = link_config(src, dest)

    assert result.returncode == 1
    assert not dest.is_symlink()
    assert dest.read_text() == 'hand-written, precious\n'
    assert 'not a symlink' in result.stderr


def test_rejects_a_missing_source(tmp_path: Path) -> None:
    dest = tmp_path / 'home' / 'thing.toml'

    result = link_config(tmp_path / 'repo' / 'nope.toml', dest)

    assert result.returncode == 1
    assert not dest.exists()
    assert 'does not exist' in result.stderr


@pytest.mark.parametrize(
    ('dest_state', 'expected_code'),
    [
        ('missing', 0),
        ('correct_link', 0),
        ('stale_link', 0),
        ('real_file', 1),
        ('real_dir', 1),
    ],
)
def test_exit_code_by_dest_state(
    tmp_path: Path,
    src: Path,
    dest_state: str,
    expected_code: int,
) -> None:
    dest = tmp_path / 'home' / 'thing.toml'
    dest.parent.mkdir(parents=True)

    if dest_state == 'correct_link':
        dest.symlink_to(src)
    elif dest_state == 'stale_link':
        other = tmp_path / 'repo' / 'other.toml'
        other.write_text('x\n')
        dest.symlink_to(other)
    elif dest_state == 'real_file':
        dest.write_text('x\n')
    elif dest_state == 'real_dir':
        dest.mkdir()

    assert link_config(src, dest).returncode == expected_code
