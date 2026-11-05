"""Turn a failed fetch into one readable line."""

import subprocess

FETCH_ERRORS = (ValueError, OSError, subprocess.SubprocessError)


def describe_error(error: Exception) -> str:
    if isinstance(error, subprocess.CalledProcessError):
        stderr = error.stderr if isinstance(error.stderr, str) else ''
        return (
            stderr.strip()[:300] or f'{error.cmd[0]} exited {error.returncode}'
        )
    if isinstance(error, subprocess.TimeoutExpired):
        return f'{error.cmd[0]} timed out after {error.timeout:.0f}s'
    return str(error)
