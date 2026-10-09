"""Human-run scripts answer --version without doing their real work.

HOME points at an empty temp dir, so a script that ignores the flag and runs
anyway shows up as extra output or a non-zero exit.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent


@pytest.mark.parametrize(
    'script',
    ['bench-shell.sh', 'check-tool-wiring.sh', 'dotfiles_audit.sh'],
)
def test_version_prints_one_line_and_exits_zero(
    tmp_path: Path,
    script: str,
) -> None:
    result = subprocess.run(  # noqa: S603
        ['bash', str(SCRIPTS / script), '--version'],  # noqa: S607
        capture_output=True,
        text=True,
        env={**os.environ, 'HOME': str(tmp_path)},
        stdin=subprocess.DEVNULL,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert re.fullmatch(
        rf'{re.escape(script.removesuffix(".sh"))} \d+\.\d+\.\d+\n',
        result.stdout,
    )
