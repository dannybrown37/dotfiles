"""Tests for scripts/bench-shell.sh's budget mode.

HOME points at a temp dir with an empty .bashrc, so the timed shell is fast.
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent / 'bench-shell.sh'
README = Path(__file__).parent.parent / 'README.md'


@pytest.mark.parametrize(
    ('budget', 'returncode', 'verdict'),
    [('100000', 0, 'within'), ('0', 1, 'over')],
)
def test_budget_mode_gates_on_median_and_skips_readme(
    tmp_path: Path,
    budget: str,
    returncode: int,
    verdict: str,
) -> None:
    (tmp_path / '.bashrc').write_text('')
    readme_before = README.read_text()

    result = subprocess.run(  # noqa: S603
        ['bash', str(SCRIPT), '2'],  # noqa: S607
        env={**os.environ, 'HOME': str(tmp_path), 'SHELL_BUDGET_MS': budget},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == returncode, result.stderr
    assert f'{verdict} the {budget}ms budget' in result.stdout + result.stderr
    assert README.read_text() == readme_before
