"""Repos of the GitHub orgs in FLEET_GITHUB_ORGS, cached on disk for an hour.

Org names come from the environment only, so none land in the repo.
"""

import json
import os
import re
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from fleet.errors import FETCH_ERRORS, describe_error
from fleet.store import read_json, write_json_atomically

CACHE_SECONDS = 3600
REPO_LIMIT = '200'
GH_TIMEOUT_SECONDS = 60
NAME_WITH_OWNER = re.compile(r'[\w.-]+/[\w.-]+')


@dataclass(frozen=True)
class OrgRepo:
    name_with_owner: str
    url: str

    @property
    def name(self) -> str:
        return self.name_with_owner.partition('/')[2]


def configured_orgs(env: Mapping[str, str] = os.environ) -> list[str]:
    orgs = [org.strip() for org in env.get('FLEET_GITHUB_ORGS', '').split(',')]
    return list(dict.fromkeys(org for org in orgs if org))


def parse_repo_item(item: object) -> OrgRepo | None:
    if not isinstance(item, dict):
        return None
    name = item.get('nameWithOwner')
    url = item.get('url')
    if not isinstance(name, str) or not NAME_WITH_OWNER.fullmatch(name):
        return None
    if not isinstance(url, str) or not url.startswith('https://'):
        return None
    return OrgRepo(name, url)


def parse_repo_list(raw: str) -> list[OrgRepo]:
    try:
        items = json.loads(raw)
    except ValueError:
        items = None
    if not isinstance(items, list):
        msg = f'gh returned no repo list: {raw[:80]!r}'
        raise ValueError(msg)  # noqa: TRY004  bad CLI output, not a caller bug
    repos = [repo for item in items if (repo := parse_repo_item(item))]
    return sorted(repos, key=lambda r: r.name_with_owner.lower())


def gh_with_timeout(*args: str) -> str:
    return subprocess.run(  # noqa: S603
        ['gh', *args],  # noqa: S607
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        text=True,
        timeout=GH_TIMEOUT_SECONDS,
    ).stdout


def read_cache(path: Path) -> dict[str, tuple[float, list[OrgRepo]]]:
    """org → (fetched_at, repos); anything malformed is simply absent."""
    data = read_json(path)
    orgs = data.get('orgs') if data else None
    if not isinstance(orgs, dict):
        return {}
    cache = {}
    for org, entry in orgs.items():
        if not isinstance(entry, dict):
            continue
        fetched_at = entry.get('fetched_at')
        items = entry.get('repos')
        if isinstance(fetched_at, (int, float)) and isinstance(items, list):
            repos = [repo for item in items if (repo := parse_repo_item(item))]
            cache[org] = (float(fetched_at), repos)
    return cache


def write_cache(
    path: Path,
    cache: Mapping[str, tuple[float, Sequence[OrgRepo]]],
) -> None:
    write_json_atomically(
        path,
        {
            'orgs': {
                org: {
                    'fetched_at': fetched_at,
                    'repos': [
                        {'nameWithOwner': r.name_with_owner, 'url': r.url}
                        for r in repos
                    ],
                }
                for org, (fetched_at, repos) in cache.items()
            },
        },
    )


def fetch_org_repos(
    orgs: Sequence[str],
    cache_path: Path,
    run: Callable[..., str] = gh_with_timeout,
    now: float | None = None,
) -> tuple[list[OrgRepo], list[str]]:
    """Each org is cached and fails alone; failures fall back to stale data."""
    if not orgs:
        return [], []
    now = time.time() if now is None else now
    cache = read_cache(cache_path)
    repos: list[OrgRepo] = []
    errors: list[str] = []
    changed = False
    for org in orgs:
        cached = cache.get(org)
        if cached and 0 <= now - cached[0] < CACHE_SECONDS:
            repos += cached[1]
            continue
        try:
            fresh = parse_repo_list(
                run(
                    'repo',
                    'list',
                    org,
                    '--json',
                    'nameWithOwner,url',
                    '--limit',
                    REPO_LIMIT,
                    '--no-archived',
                ),
            )
        except FETCH_ERRORS as error:
            stale = ' (showing cached list)' if cached else ''
            errors.append(f'{org}: {describe_error(error)}{stale}')
            repos += cached[1] if cached else []
            continue
        if not fresh:
            # gh prints [] and exits 0 for an unknown owner with --no-archived.
            errors.append(
                f'{org}: no repos found '
                '(check the org name and `gh auth status`)',
            )
            continue
        cache[org] = (now, fresh)
        repos += fresh
        changed = True
    if changed:
        write_cache(cache_path, cache)
    return sorted(repos, key=lambda r: r.name_with_owner.lower()), errors


def clone_command(
    name_with_owner: str,
    projects_dir: Path,
) -> tuple[list[str], Path]:
    if (
        not NAME_WITH_OWNER.fullmatch(name_with_owner)
        or '..' in name_with_owner
    ):
        msg = f'expected owner/repo, got {name_with_owner!r}'
        raise ValueError(msg)
    destination = projects_dir / name_with_owner.partition('/')[2]
    return (
        ['gh', 'repo', 'clone', name_with_owner, str(destination)],
        destination,
    )
