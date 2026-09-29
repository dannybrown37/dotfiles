"""Tests for scripts/just-help.sh, which builds `just` help from headers."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
HELP = REPO_ROOT / 'scripts' / 'just-help.sh'
BASH = shutil.which('bash') or '/bin/bash'


@pytest.mark.parametrize(
    'recipe',
    [
        'plain:',
        "with-default runs='10':",
        'variadic *names:',
    ],
)
def test_justfile_recipe_is_listed(tmp_path: Path, recipe: str) -> None:
    (tmp_path / 'install').mkdir()
    (tmp_path / 'install' / 'tool.sh').write_text('#!/usr/bin/env bash\n')
    (tmp_path / 'install' / 'tool.ps1').write_text('')
    (tmp_path / 'justfile').write_text(
        f'## @just 10 Section | Does a thing\n{recipe}\n    echo hi\n',
    )

    result = subprocess.run(  # noqa: S603
        [BASH, str(HELP)],
        env={**os.environ, 'DOTFILES_ROOT': str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )

    name = recipe.split(maxsplit=1)[0].rstrip(':')
    assert f'  {name}' in result.stdout
    assert 'Does a thing' in result.stdout
