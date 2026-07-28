#!/usr/bin/env python3
"""Chain the atuin and cartoon PreToolUse hooks into one.

Both register as independent PreToolUse entries matching Bash in
~/.claude/settings.json. Claude Code runs matching hooks in parallel but
doesn't document how conflicting `updatedInput` results are merged --
in practice cartoon's rewrite was silently dropped. Running them in a
fixed sequence and only ever emitting cartoon's JSON removes that
ambiguity: atuin is a side-effect-only history logger, cartoon is the
one hook whose stdout matters.
"""

import contextlib
import shutil
import subprocess
import sys

ATUIN_TIMEOUT_S = 5
CARTOON_TIMEOUT_S = 5


def run_atuin(raw_payload: str) -> None:
    atuin = shutil.which('atuin')
    if atuin is None:
        return
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        subprocess.run(  # noqa: S603
            [atuin, 'hook', 'claude-code'],
            input=raw_payload,
            capture_output=True,
            timeout=ATUIN_TIMEOUT_S,
            text=True,
            check=False,
        )


def run_cartoon(raw_payload: str) -> str | None:
    cartoon = shutil.which('cartoon')
    if cartoon is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603
            [cartoon, 'hook', 'rewrite'],
            input=raw_payload,
            capture_output=True,
            timeout=CARTOON_TIMEOUT_S,
            text=True,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def main(raw_payload: str) -> int:
    run_atuin(raw_payload)
    rewritten = run_cartoon(raw_payload)
    if rewritten:
        sys.stdout.write(rewritten)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.stdin.read()))
