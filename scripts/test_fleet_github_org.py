"""Tests for fleet.github_org: the GitHub org repos the palette offers."""

import json
import subprocess
from pathlib import Path

import pytest

from fleet.github_org import (
    OrgRepo,
    clone_command,
    configured_orgs,
    fetch_org_repos,
    parse_repo_list,
    CACHE_SECONDS,
)

ACME_JSON = json.dumps(
    [
        {'nameWithOwner': 'acme/web', 'url': 'https://github.com/acme/web'},
        {'nameWithOwner': 'acme/api', 'url': 'https://github.com/acme/api'},
    ],
)


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('', []),
        ('acme', ['acme']),
        ('acme, beta ,,acme', ['acme', 'beta']),
        ('  ', []),
    ],
)
def test_configured_orgs(value: str, expected: list[str]) -> None:
    assert configured_orgs({'FLEET_GITHUB_ORGS': value}) == expected


def test_configured_orgs_unset_is_off() -> None:
    assert configured_orgs({}) == []


def test_parse_repo_list_sorts_by_name() -> None:
    assert parse_repo_list(ACME_JSON) == [
        OrgRepo('acme/api', 'https://github.com/acme/api'),
        OrgRepo('acme/web', 'https://github.com/acme/web'),
    ]


@pytest.mark.parametrize(
    'raw',
    [
        '[{"url": "https://github.com/acme/x"}]',
        '[{"nameWithOwner": "acme/x"}]',
        '[{"nameWithOwner": "not a repo", "url": "https://x"}]',
        '[{"nameWithOwner": "acme/x", "url": "javascript:alert(1)"}]',
        '["acme/x"]',
    ],
)
def test_parse_repo_list_skips_malformed_items(raw: str) -> None:
    assert parse_repo_list(raw) == []


@pytest.mark.parametrize('raw', ['', 'not json', '{"a": 1}'])
def test_parse_repo_list_rejects_non_list(raw: str) -> None:
    with pytest.raises(ValueError, match='repo list'):
        parse_repo_list(raw)


def test_repo_name_is_the_part_after_the_owner() -> None:
    assert OrgRepo('acme/api', 'https://github.com/acme/api').name == 'api'


def repos_for(org: str) -> str:
    return json.dumps(
        [
            {
                'nameWithOwner': f'{org}/svc',
                'url': f'https://github.com/{org}/svc',
            },
        ],
    )


class FakeGh:
    def __init__(self, failing: frozenset[str] = frozenset()) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.failing = failing

    def __call__(self, *args: str) -> str:
        self.calls.append(args)
        org = args[2]
        if org in self.failing:
            raise subprocess.CalledProcessError(1, ['gh'], '', f'no org {org}')
        return repos_for(org)


def fetch(
    orgs: list[str],
    cache: Path,
    gh: FakeGh,
    now: float,
) -> tuple[list[str], list[str]]:
    repos, errors = fetch_org_repos(orgs, cache, run=gh, now=now)
    return [r.name_with_owner for r in repos], errors


def test_fetch_calls_gh_per_org_sorted_and_flags_archived(
    tmp_path: Path,
) -> None:
    gh = FakeGh()
    names, errors = fetch(['beta', 'acme'], tmp_path / 'c.json', gh, now=5.0)
    assert names == ['acme/svc', 'beta/svc']
    assert errors == []
    assert gh.calls[0][:3] == ('repo', 'list', 'beta')
    assert '--no-archived' in gh.calls[0]


@pytest.mark.parametrize(
    ('later', 'calls_gh'),
    [
        (5.0 + CACHE_SECONDS - 1, False),
        (5.0 + CACHE_SECONDS + 1, True),
        (4.0, True),
    ],
)
def test_cache_freshness_per_org(
    tmp_path: Path,
    later: float,
    calls_gh: bool,  # noqa: FBT001
) -> None:
    cache = tmp_path / 'c.json'
    fetch(['acme'], cache, FakeGh(), now=5.0)
    gh = FakeGh()
    names, _ = fetch(['acme'], cache, gh, now=later)
    assert names == ['acme/svc']
    assert bool(gh.calls) is calls_gh


def test_adding_an_org_only_fetches_the_new_one(tmp_path: Path) -> None:
    cache = tmp_path / 'c.json'
    fetch(['acme'], cache, FakeGh(), now=5.0)
    gh = FakeGh()
    names, _ = fetch(['acme', 'beta'], cache, gh, now=6.0)
    assert names == ['acme/svc', 'beta/svc']
    assert [call[2] for call in gh.calls] == ['beta']


def test_one_failing_org_keeps_the_others(tmp_path: Path) -> None:
    cache = tmp_path / 'c.json'
    names, errors = fetch(
        ['acme', 'typo'],
        cache,
        FakeGh(frozenset({'typo'})),
        now=5.0,
    )
    assert names == ['acme/svc']
    assert errors == ['typo: no org typo']
    gh = FakeGh()
    fetch(['acme', 'typo'], cache, gh, now=6.0)
    assert [call[2] for call in gh.calls] == ['typo']


def test_failing_org_falls_back_to_stale_cache(tmp_path: Path) -> None:
    cache = tmp_path / 'c.json'
    fetch(['acme'], cache, FakeGh(), now=5.0)
    names, errors = fetch(
        ['acme'],
        cache,
        FakeGh(frozenset({'acme'})),
        now=5.0 + CACHE_SECONDS * 3,
    )
    assert names == ['acme/svc']
    assert errors == ['acme: no org acme (showing cached list)']


@pytest.mark.parametrize(
    'content',
    ['', 'garbage', '{"orgs": 3}', '{"orgs": {"acme": {"fetched_at": "x"}}}'],
)
def test_unreadable_cache_is_refetched(tmp_path: Path, content: str) -> None:
    cache = tmp_path / 'c.json'
    cache.write_text(content)
    gh = FakeGh()
    names, _ = fetch(['acme'], cache, gh, now=5.0)
    assert names == ['acme/svc']
    assert gh.calls


def test_fetch_with_no_orgs_does_nothing(tmp_path: Path) -> None:
    assert fetch([], tmp_path / 'c.json', FakeGh(), now=0.0) == ([], [])


def test_clone_command_targets_projects_dir(tmp_path: Path) -> None:
    repo = OrgRepo('acme/api', 'https://github.com/acme/api')
    assert clone_command(repo.name_with_owner, tmp_path) == (
        ['gh', 'repo', 'clone', 'acme/api', str(tmp_path / 'api')],
        tmp_path / 'api',
    )


def test_clone_command_rejects_bad_repo(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='owner/repo'):
        clone_command('../../etc', tmp_path)


def test_empty_org_is_a_warning_and_not_cached(tmp_path: Path) -> None:
    """`gh repo list <typo> --no-archived` prints [] and exits 0."""
    cache = tmp_path / 'c.json'

    def empty(*_args: str) -> str:
        return '[]'

    repos, errors = fetch_org_repos(['typo'], cache, run=empty, now=5.0)
    assert repos == []
    assert errors == [
        'typo: no repos found (check the org name and `gh auth status`)',
    ]
    gh = FakeGh()
    fetch(['typo'], cache, gh, now=6.0)
    assert gh.calls
