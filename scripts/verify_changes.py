#!/usr/bin/env python3
"""Run this repo's pre-commit suite before Claude Code ends a turn.

Wired as a Stop hook. Without it the verification step is `git commit`,
which means the human is the one who discovers the lint error or the
broken test and pastes it back -- exactly the loop this removes.

Hooks that stage their own fixes (`git add`) are skipped: the assistant
has read-only git access, so silently mutating the index is off limits.
Formatting is therefore left for commit time, where it auto-fixes.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

BLOCK_EXIT_CODE = 2
DISABLE_ENV_VAR = 'VERIFY_CHANGES_SKIP'
PRE_COMMIT_TIMEOUT_SECONDS = 300
STAGING_MARKER = 'git add'
STATUS_PREFIX_WIDTH = 3
RENAME_STATUSES = ('R', 'C')

# Hooks that stage inside their own source rather than in a `git add` visible
# in this config's `entry:`. Scraping the config text cannot see those, so the
# ids have to be named here -- these come from the git-a-grip repo.
EXTERNAL_STAGING_HOOK_IDS = frozenset({'ruff-check', 'ruff-format'})

HOOK_ID_PATTERN = re.compile(r'^\s*-\s*id:\s*(\S+)')

FAILURE_HEADER = (
    'Stop blocked: pre-commit failed on the files changed this turn. '
    'Fix these before reporting the work as done -- do not hand them to '
    'the user.'
)


def read_payload(raw: str) -> dict[str, object]:
    """Parse the Stop hook's stdin JSON, tolerating anything unexpected."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def staging_hook_ids(config_text: str) -> list[str]:
    """Find pre-commit hooks whose entry stages files with `git add`."""
    ids: list[str] = []
    current = ''
    for line in config_text.splitlines():
        match = HOOK_ID_PATTERN.match(line)
        if match:
            current = match.group(1)
            if current in EXTERNAL_STAGING_HOOK_IDS and current not in ids:
                ids.append(current)
        elif STAGING_MARKER in line and current and current not in ids:
            ids.append(current)
    return ids


def parse_porcelain(payload: str) -> list[str]:
    """Pull the current path out of each `git status --porcelain -z` entry."""
    fields = payload.split('\0')
    paths: list[str] = []
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if len(entry) <= STATUS_PREFIX_WIDTH:
            continue
        status = entry[:2]
        paths.append(entry[STATUS_PREFIX_WIDTH:])
        if status[0] in RENAME_STATUSES:
            index += 1
    return paths


def find_repo_root(start: Path) -> Path | None:
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],  # noqa: S607
        cwd=start,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def changed_paths(repo_root: Path) -> list[str]:
    """List repo-relative paths that exist and differ from HEAD."""
    result = subprocess.run(
        ['git', 'status', '--porcelain', '-z', '-uall'],  # noqa: S607
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return sorted(
        path
        for path in parse_porcelain(result.stdout)
        if (repo_root / path).is_file()
    )


def run_pre_commit(
    repo_root: Path,
    paths: list[str],
    skip_ids: list[str],
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, 'SKIP': ','.join(skip_ids)}
    return subprocess.run(  # noqa: S603
        ['pre-commit', 'run', '--files', *paths],  # noqa: S607
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=PRE_COMMIT_TIMEOUT_SECONDS,
    )


def verification_target(
    payload: dict[str, object],
) -> tuple[Path, Path, list[str]] | None:
    """Resolve the repo, its hook config, and what changed -- or None."""
    cwd = payload.get('cwd')
    start = Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()
    repo_root = find_repo_root(start)
    if repo_root is None:
        return None

    config = repo_root / '.pre-commit-config.yaml'
    if not config.is_file():
        return None

    paths = changed_paths(repo_root)
    if not paths:
        return None
    return repo_root, config, paths


def main(raw_payload: str) -> int:
    payload = read_payload(raw_payload)
    if payload.get('stop_hook_active') or os.environ.get(DISABLE_ENV_VAR):
        return 0

    target = verification_target(payload)
    if target is None:
        return 0
    repo_root, config, paths = target

    try:
        result = run_pre_commit(
            repo_root,
            paths,
            staging_hook_ids(config.read_text()),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0

    if result.returncode == 0:
        return 0

    print(FAILURE_HEADER, file=sys.stderr)
    print(result.stdout, file=sys.stderr)
    print(result.stderr, file=sys.stderr)
    return BLOCK_EXIT_CODE


if __name__ == '__main__':
    sys.exit(main(sys.stdin.read()))
