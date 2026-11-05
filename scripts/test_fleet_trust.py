"""Tests for fleet.trust: answering an agent's folder-trust dialog safely."""

import json
from pathlib import Path

import pytest

from fleet.trust import (
    SELECTED,
    TrustKey,
    source_is_trusted,
    trust_dialog_key,
)

WORKTREE = '/home/u/projects/api-worktrees/fix-x'

CLAUDE_DIALOG = f"""
 Accessing workspace:
 {WORKTREE}
 Quick safety check: Is this a project you created or one you trust?
 {SELECTED} No, exit
   Yes, I trust this folder
 Enter to confirm · Esc to cancel
"""

CLAUDE_DIALOG_ON_YES = CLAUDE_DIALOG.replace(
    f'{SELECTED} No, exit',
    '  No, exit',
).replace(
    '  Yes, I trust',
    f'{SELECTED} Yes, I trust',
)

COPILOT_DIALOG = f"""
│ Confirm folder trust                                          │
│ │ {WORKTREE}           │ │
│ Do you trust the files in this folder?                        │
│ {SELECTED} 1. Yes                                                      │
│   2. Yes, and remember this folder for future sessions        │
│   3. No (Esc)                                                 │
"""

COPILOT_DIALOG_ON_REMEMBER = COPILOT_DIALOG.replace(
    f'{SELECTED} 1. Yes',
    '  1. Yes',
).replace(
    '  2. Yes, and remember',
    f'{SELECTED} 2. Yes, and remember',
)


@pytest.mark.parametrize(
    ('screen', 'expected'),
    [
        (CLAUDE_DIALOG, TrustKey.DOWN),
        (CLAUDE_DIALOG_ON_YES, TrustKey.ENTER),
        (COPILOT_DIALOG, TrustKey.ENTER),
        # Only "this session" is ever picked, never "remember forever".
        (COPILOT_DIALOG_ON_REMEMBER, TrustKey.UP),
        (f'{SELECTED} Try "refactor <filepath>"', None),
        ('', None),
    ],
)
def test_trust_dialog_key(screen: str, expected: TrustKey | None) -> None:
    assert trust_dialog_key(screen, WORKTREE) == expected


def test_trust_dialog_for_another_folder_is_never_answered() -> None:
    other = CLAUDE_DIALOG_ON_YES.replace(WORKTREE, '/home/u/Downloads/evil')
    assert trust_dialog_key(other, WORKTREE) is None


def test_trust_dialog_for_parent_folder_is_never_answered() -> None:
    parent = CLAUDE_DIALOG_ON_YES.replace(
        WORKTREE,
        '/home/u/projects/api-worktrees',
    )
    assert (
        trust_dialog_key(parent, '/home/u/projects/api-worktrees/fix') is None
    )


def write_claude_json(path: Path, projects: dict[str, bool]) -> Path:
    path.write_text(
        json.dumps(
            {
                'projects': {
                    folder: {'hasTrustDialogAccepted': trusted}
                    for folder, trusted in projects.items()
                },
            },
        ),
    )
    return path


def write_copilot_config(path: Path, folders: list[str]) -> Path:
    path.write_text(
        '// User settings belong in settings.json.\n'
        '// This file is managed automatically.\n'
        + json.dumps(
            {'trustedFolders': folders, 'copilotTokens': {'x': 'secret'}},
        ),
    )
    return path


@pytest.mark.parametrize(
    ('claude_projects', 'copilot_folders', 'root', 'expected'),
    [
        ({'/p/api': True}, [], '/p/api', True),
        ({'/p/api': False}, [], '/p/api', False),
        ({}, ['/p/api'], '/p/api', True),
        ({}, ['/p'], '/p/api', True),
        ({}, ['/p/ap'], '/p/api', False),
        ({'/p/api-other': True}, [], '/p/api', False),
        ({}, [], '/p/api', False),
    ],
)
def test_source_is_trusted(
    tmp_path: Path,
    claude_projects: dict[str, bool],
    copilot_folders: list[str],
    root: str,
    expected: bool,  # noqa: FBT001
) -> None:
    claude_json = write_claude_json(tmp_path / 'claude.json', claude_projects)
    copilot_json = write_copilot_config(
        tmp_path / 'config.json',
        copilot_folders,
    )
    assert source_is_trusted(Path(root), claude_json, copilot_json) is expected


def test_source_is_trusted_survives_missing_and_corrupt_files(
    tmp_path: Path,
) -> None:
    corrupt = tmp_path / 'bad.json'
    corrupt.write_text('{nope')
    assert (
        source_is_trusted(Path('/p'), corrupt, tmp_path / 'missing') is False
    )
