"""Tests for the non-interactive paths of scripts/refs.sh."""

import os
import re
import subprocess
from pathlib import Path

import pytest

REFS = Path(__file__).parent / 'refs.sh'
EXIT_USAGE = 2
ANSI = re.compile(r'\x1b\[[0-9;]*m')

SAMPLE = """# Title

Intro text.

---

## First Entry
First description.
[First link](https://example.com/one)

## Second Entry
Second description
spans two lines.
[Second link](https://example.com/two?a=b)

## No Link Entry
Just text.
"""


@pytest.fixture
def ref_file(tmp_path: Path) -> Path:
    path = tmp_path / 'ref.md'
    path.write_text(SAMPLE)
    return path


def run(
    *args: str,
    refs_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, 'REFS_DIR': str(refs_dir)} if refs_dir else None
    return subprocess.run(  # noqa: S603
        [str(REFS), *args],
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
        env=env,
    )


@pytest.fixture
def refs_dir(tmp_path: Path) -> Path:
    (tmp_path / 'beta.md').write_text(SAMPLE)
    (tmp_path / 'alpha.md').write_text(SAMPLE)
    (tmp_path / 'notes.md').write_text('## heading\nno link lines\n')
    (tmp_path / 'skip.txt').write_text(SAMPLE)
    return tmp_path


def test_files_lists_every_markdown_file(refs_dir: Path) -> None:
    result = run('files', refs_dir=refs_dir)
    assert result.returncode == 0
    assert result.stdout.splitlines() == ['alpha', 'beta', 'notes']


@pytest.mark.parametrize(
    'name',
    [
        'media',
        'mental-models',
        'vim-notes',
        'home-server-setup',
        'git-workflow',
        'net-rescue',
    ],
)
def test_default_refs_include_repo_docs(name: str) -> None:
    assert name in run('files').stdout.splitlines()


@pytest.mark.parametrize(
    ('name', 'path'),
    [
        ('home-server-setup', 'wsl/home-server-setup.md'),
        ('git-workflow', 'docs/git-workflow.md'),
        ('net-rescue', 'windows/net-rescue.md'),
    ],
)
def test_default_name_resolves_outside_references(
    name: str,
    path: str,
) -> None:
    result = run(name)
    assert result.returncode == 0
    assert result.stdout == (REFS.parent.parent / path).read_text()


def test_name_resolves_to_refs_dir_file(refs_dir: Path) -> None:
    result = run('url', 'beta', '1', refs_dir=refs_dir)
    assert result.stdout == 'https://example.com/one\n'


@pytest.mark.parametrize('name', ['nope', 'skip'])
def test_unknown_name_shows_valid_names(refs_dir: Path, name: str) -> None:
    result = run(name, refs_dir=refs_dir)
    assert result.returncode == EXIT_USAGE
    assert 'alpha' in result.stderr
    assert 'beta' in result.stderr


def test_bare_run_off_tty_prints_usage_with_names(refs_dir: Path) -> None:
    result = run(refs_dir=refs_dir)
    assert result.returncode == EXIT_USAGE
    assert 'Usage' in result.stderr
    assert 'alpha' in result.stderr


def test_list_numbers_entries(ref_file: Path) -> None:
    result = run('list', str(ref_file))
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        '1\tFirst Entry',
        '2\tSecond Entry',
        '3\tNo Link Entry',
    ]


def test_view_off_tty_prints_file(ref_file: Path) -> None:
    result = run(str(ref_file))
    assert result.returncode == 0
    assert result.stdout == SAMPLE


@pytest.mark.parametrize(
    ('index', 'expected'),
    [
        ('1', 'https://example.com/one\n'),
        ('2', 'https://example.com/two?a=b\n'),
        ('3', ''),
    ],
)
def test_url_prints_first_link(
    ref_file: Path,
    index: str,
    expected: str,
) -> None:
    result = run('url', str(ref_file), index)
    assert result.stdout == expected


@pytest.mark.parametrize(
    'args',
    [
        [],
        ['bogus'],
        ['list'],
        ['url', 'MISSING_FILE', '1'],
        ['links'],
    ],
)
def test_bad_usage_exits_nonzero(args: list[str], tmp_path: Path) -> None:
    resolved = [
        str(tmp_path / 'nope.md') if a == 'MISSING_FILE' else a for a in args
    ]
    result = run(*resolved)
    assert result.returncode == EXIT_USAGE
    assert 'Usage' in result.stderr


def test_version() -> None:
    result = run('--version')
    assert result.returncode == 0
    assert result.stdout.strip()


def test_add_appends_entry(ref_file: Path) -> None:
    result = run(
        'add',
        str(ref_file),
        'New One',
        'Why it matters.',
        'https://x.io/a',
    )
    assert result.returncode == 0
    assert ref_file.read_text() == (
        SAMPLE + '\n## New One\nWhy it matters.\n[New One](https://x.io/a)\n'
    )
    assert run('url', str(ref_file), '4').stdout == 'https://x.io/a\n'


@pytest.mark.parametrize(
    'args',
    [
        ['add', 'REF'],
        ['add', 'REF', 'Title', 'Desc', 'not-a-url'],
        ['edit', 'REF'],
    ],
)
def test_add_and_edit_off_tty_do_not_prompt(
    ref_file: Path,
    args: list[str],
) -> None:
    result = run(*[str(ref_file) if a == 'REF' else a for a in args])
    assert result.returncode == EXIT_USAGE
    assert ref_file.read_text() == SAMPLE


def test_add_by_name_writes_to_refs_dir(refs_dir: Path) -> None:
    result = run('add', 'alpha', 'T', 'D', 'https://x.io', refs_dir=refs_dir)
    assert result.returncode == 0
    assert (refs_dir / 'alpha.md').read_text().endswith('[T](https://x.io)\n')


def test_preview_renders_ref_by_name(refs_dir: Path) -> None:
    result = run('preview', 'notes', refs_dir=refs_dir)
    assert result.returncode == 0
    assert 'no link lines' in ANSI.sub('', result.stdout)


def test_preview_renders_h2_without_literal_hashes(refs_dir: Path) -> None:
    result = run('preview', 'notes', refs_dir=refs_dir)
    plain = ANSI.sub('', result.stdout)
    assert 'heading' in plain
    assert '## heading' not in plain


def test_preview_unknown_ref_is_usage_error(refs_dir: Path) -> None:
    result = run('preview', 'nope', refs_dir=refs_dir)
    assert result.returncode == EXIT_USAGE
