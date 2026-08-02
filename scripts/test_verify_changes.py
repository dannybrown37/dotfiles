"""Tests for the Stop-hook change verifier."""

import json
import subprocess
from pathlib import Path

import pytest

from verify_changes import (
    BLOCK_EXIT_CODE,
    changed_paths,
    main,
    parse_porcelain,
    read_payload,
    staging_hook_ids,
)

GIT = '/usr/bin/git'

CONFIG_WITH_STAGING_HOOKS = """\
repos:
  - repo: local
    hooks:
      - id: ruff-check
      - id: ruff-format
      - id: check-dirdesc
        entry: bash -c 'bash scripts/check-dirdesc.sh'
      - id: sync-readme-make
        entry: bash -c 'bash scripts/sync-readme-make.sh && git add README.md'
"""


def git(repo: Path, *args: str) -> None:
    subprocess.run([GIT, *args], cwd=repo, check=True)  # noqa: S603


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.email', 'test@example.com')
    git(tmp_path, 'config', 'user.name', 'Test')
    (tmp_path / 'tracked.py').write_text('x = 1\n')
    (tmp_path / 'stale.py').write_text('y = 2\n')
    git(tmp_path, 'add', '-A')
    git(tmp_path, 'commit', '-qm', 'init')
    return tmp_path


@pytest.mark.parametrize(
    ('config_text', 'expected'),
    [
        (
            CONFIG_WITH_STAGING_HOOKS,
            ['ruff-check', 'ruff-format', 'sync-readme-make'],
        ),
        ('repos:\n  - repo: local\n    hooks:\n      - id: solo\n', []),
        ('', []),
    ],
)
def test_staging_hook_ids_finds_hooks_that_stage(
    config_text: str,
    expected: list[str],
) -> None:
    assert staging_hook_ids(config_text) == expected


def test_staging_hook_ids_matches_the_real_repo_config() -> None:
    config = Path(__file__).parent.parent / '.pre-commit-config.yaml'

    ids = staging_hook_ids(config.read_text())

    # ruff-check and ruff-format now come from git-a-grip, which stages inside
    # the hook rather than via a `git add` in this config's entry.
    assert 'ruff-format' in ids
    assert 'ruff-check' in ids
    assert 'sync-readme-commands' in ids
    assert 'gtd-tests' not in ids


@pytest.mark.parametrize(
    ('payload', 'expected'),
    [
        (' M a.py\0', ['a.py']),
        ('?? new.py\0', ['new.py']),
        ('M  a.py\0?? b.py\0', ['a.py', 'b.py']),
        ('R  new.py\0old.py\0 M c.py\0', ['new.py', 'c.py']),
        (' D gone.py\0', ['gone.py']),
        ('', []),
        ('\0\0', []),
    ],
)
def test_parse_porcelain_extracts_current_paths(
    payload: str,
    expected: list[str],
) -> None:
    assert parse_porcelain(payload) == expected


def test_changed_paths_reports_modified_and_untracked(repo: Path) -> None:
    (repo / 'tracked.py').write_text('x = 2\n')
    (repo / 'brand_new.py').write_text('z = 3\n')

    assert changed_paths(repo) == ['brand_new.py', 'tracked.py']


def test_changed_paths_omits_deleted_files(repo: Path) -> None:
    (repo / 'stale.py').unlink()

    assert changed_paths(repo) == []


def test_changed_paths_omits_gitignored_files(repo: Path) -> None:
    (repo / '.gitignore').write_text('secret.txt\n')
    (repo / 'secret.txt').write_text('shh\n')

    assert changed_paths(repo) == ['.gitignore']


def test_changed_paths_is_empty_on_a_clean_tree(repo: Path) -> None:
    assert changed_paths(repo) == []


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('{"stop_hook_active": true}', {'stop_hook_active': True}),
        ('', {}),
        ('not json at all', {}),
        ('[1, 2, 3]', {}),
    ],
)
def test_read_payload_tolerates_bad_input(
    raw: str,
    expected: dict[str, object],
) -> None:
    assert read_payload(raw) == expected


def test_main_does_not_recurse_when_already_blocking(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (repo / 'tracked.py').write_text('x = 2\n')
    monkeypatch.setattr(
        'verify_changes.run_pre_commit',
        _fail_if_called,
    )

    payload = json.dumps({'cwd': str(repo), 'stop_hook_active': True})

    assert main(payload) == 0


def test_main_skips_verification_when_disabled(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (repo / 'tracked.py').write_text('x = 2\n')
    monkeypatch.setenv('VERIFY_CHANGES_SKIP', '1')
    monkeypatch.setattr('verify_changes.run_pre_commit', _fail_if_called)

    assert main(json.dumps({'cwd': str(repo)})) == 0


def test_main_passes_when_tree_is_clean(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('verify_changes.run_pre_commit', _fail_if_called)

    assert main(json.dumps({'cwd': str(repo)})) == 0


def test_main_passes_outside_a_git_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('verify_changes.run_pre_commit', _fail_if_called)

    assert main(json.dumps({'cwd': str(tmp_path)})) == 0


def test_main_passes_without_a_pre_commit_config(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (repo / 'tracked.py').write_text('x = 2\n')
    monkeypatch.setattr('verify_changes.run_pre_commit', _fail_if_called)

    assert main(json.dumps({'cwd': str(repo)})) == 0


def test_main_blocks_when_pre_commit_fails(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (repo / '.pre-commit-config.yaml').write_text(CONFIG_WITH_STAGING_HOOKS)
    (repo / 'tracked.py').write_text('import os\n')
    monkeypatch.setattr(
        'verify_changes.run_pre_commit',
        _stub_result(1, 'Ruff check...Failed\nF401 unused import'),
    )

    assert main(json.dumps({'cwd': str(repo)})) == BLOCK_EXIT_CODE
    assert 'F401 unused import' in capsys.readouterr().err


def test_main_allows_stop_when_pre_commit_passes(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (repo / '.pre-commit-config.yaml').write_text(CONFIG_WITH_STAGING_HOOKS)
    (repo / 'tracked.py').write_text('x = 2\n')
    monkeypatch.setattr(
        'verify_changes.run_pre_commit',
        _stub_result(0, 'all good'),
    )

    assert main(json.dumps({'cwd': str(repo)})) == 0


def test_main_forwards_changed_paths_and_skips_to_pre_commit(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (repo / '.pre-commit-config.yaml').write_text(CONFIG_WITH_STAGING_HOOKS)
    (repo / 'tracked.py').write_text('x = 2\n')
    (repo / 'extra.py').write_text('w = 9\n')
    seen: dict[str, object] = {}

    def capture(
        repo_root: Path,
        paths: list[str],
        skip_ids: list[str],
    ) -> subprocess.CompletedProcess[str]:
        seen.update(repo_root=repo_root, paths=paths, skip_ids=skip_ids)
        return subprocess.CompletedProcess([], 0, '', '')

    monkeypatch.setattr('verify_changes.run_pre_commit', capture)
    main(json.dumps({'cwd': str(repo)}))

    assert seen['paths'] == [
        '.pre-commit-config.yaml',
        'extra.py',
        'tracked.py',
    ]
    assert seen['skip_ids'] == [
        'ruff-check',
        'ruff-format',
        'sync-readme-make',
    ]


def test_main_does_not_block_when_pre_commit_is_missing(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (repo / '.pre-commit-config.yaml').write_text(CONFIG_WITH_STAGING_HOOKS)
    (repo / 'tracked.py').write_text('x = 2\n')

    def raise_missing(
        repo_root: Path,  # noqa: ARG001
        paths: list[str],  # noqa: ARG001
        skip_ids: list[str],  # noqa: ARG001
    ) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError

    monkeypatch.setattr('verify_changes.run_pre_commit', raise_missing)

    assert main(json.dumps({'cwd': str(repo)})) == 0


def _fail_if_called(
    repo_root: Path,  # noqa: ARG001
    paths: list[str],  # noqa: ARG001
    skip_ids: list[str],  # noqa: ARG001
) -> subprocess.CompletedProcess[str]:
    msg = 'pre-commit should not have run'
    raise AssertionError(msg)


def _stub_result(returncode: int, stdout: str) -> object:
    def run(
        repo_root: Path,  # noqa: ARG001
        paths: list[str],  # noqa: ARG001
        skip_ids: list[str],  # noqa: ARG001
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], returncode, stdout, '')

    return run
