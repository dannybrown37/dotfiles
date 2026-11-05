"""Tests for fleet.work: gather every work integration, isolate failures."""

import threading
from pathlib import Path

import pytest

from fleet.aws import Alarm, AwsProfile, LogGroup, ProfileAlarms
from fleet.github_org import OrgRepo
from fleet.jira import DEFAULT_JQL, JiraConfig, Ticket
from fleet.work import (
    Fetchers,
    WorkItems,
    integration_status,
    load_work_items,
    work_summary,
)

REPO = OrgRepo('acme/api', 'https://github.com/acme/api')
TICKET = Ticket(
    'ABC-1',
    's',
    '',
    '',
    '',
    'https://t.example.test/browse/ABC-1',
    '',
)
PROD = AwsProfile('prod', 'us-east-1')
CONFIG = JiraConfig(
    'https://t.example.test',
    'dc',
    '',
    'secret-token',
    DEFAULT_JQL,
)


def fetchers(**overrides: object) -> Fetchers:
    defaults: dict[str, object] = {
        'org_repos': lambda _orgs, _cache: ([REPO], []),
        'jira_config': lambda _env: CONFIG,
        'tickets': lambda _config: [TICKET],
        'alarms': lambda profiles: [
            ProfileAlarms(p, (), needs_login=False, error='') for p in profiles
        ],
    }
    return Fetchers(**(defaults | overrides))  # type: ignore[arg-type]


FULL_ENV = {
    'FLEET_GITHUB_ORGS': 'acme',
    'FLEET_JIRA_URL': 'https://t.example.test',
    'FLEET_AWS_PROFILES': 'prod@us-east-1',
    'FLEET_AWS_LOG_GROUPS': '/aws/lambda/api',
}


def test_nothing_configured_means_nothing_fetched(tmp_path: Path) -> None:
    def boom(*_args: object) -> list[object]:
        raise AssertionError

    items, errors = load_work_items(
        {},
        tmp_path,
        fetchers(
            org_repos=boom,
            tickets=boom,
            alarms=boom,
            jira_config=lambda _e: None,
        ),
    )
    assert items.org_repos == ()
    assert items.tickets == ()
    assert items.alarms == ()
    assert errors == []


def test_everything_configured(tmp_path: Path) -> None:
    items, errors = load_work_items(FULL_ENV, tmp_path, fetchers())
    assert items.org_repos == (REPO,)
    assert items.tickets == (TICKET,)
    assert [a.profile for a in items.alarms] == [PROD]
    assert items.log_groups == (LogGroup('/aws/lambda/api', PROD),)
    assert errors == []


def test_one_failing_source_does_not_hide_the_others(tmp_path: Path) -> None:
    def jira_down(_config: JiraConfig) -> list[Ticket]:
        msg = 'Jira 503 Service Unavailable'
        raise ValueError(msg)

    items, errors = load_work_items(
        FULL_ENV,
        tmp_path,
        fetchers(tickets=jira_down),
    )
    assert items.org_repos == (REPO,)
    assert items.tickets == ()
    assert errors == ['jira: Jira 503 Service Unavailable']


@pytest.mark.parametrize(
    ('env', 'source'),
    [
        ({'FLEET_AWS_PROFILES': 'bad profile'}, 'aws'),
        ({'FLEET_GITHUB_ORGS': 'acme'}, 'github'),
    ],
)
def test_config_and_fetch_errors_are_reported_per_source(
    tmp_path: Path,
    env: dict[str, str],
    source: str,
) -> None:
    def gh_fails(_orgs: object, _cache: object) -> list[OrgRepo]:
        msg = 'gh: not found'
        raise OSError(msg)

    _, errors = load_work_items(env, tmp_path, fetchers(org_repos=gh_fails))
    assert len(errors) == 1
    assert errors[0].startswith(f'{source}: ')


def test_aws_profile_errors_are_reported(tmp_path: Path) -> None:
    def denied(profiles: list[AwsProfile]) -> list[ProfileAlarms]:
        return [
            ProfileAlarms(
                profiles[0],
                (),
                needs_login=False,
                error='AccessDenied',
            ),
        ]

    _, errors = load_work_items(
        {'FLEET_AWS_PROFILES': 'prod@us-east-1'},
        tmp_path,
        fetchers(alarms=denied),
    )
    assert errors == ['aws prod@us-east-1: AccessDenied']


def test_status_names_each_integration_without_secrets() -> None:
    lines = integration_status(
        FULL_ENV | {'FLEET_JIRA_TOKEN': 'secret-token'},
        read_jira_config=lambda _env: CONFIG,
    )
    text = '\n'.join(lines)
    assert 'secret-token' not in text
    assert 'github: orgs acme' in text
    assert 'jira: dc at https://t.example.test' in text
    assert 'aws: profiles prod@us-east-1; log groups /aws/lambda/api' in text


def test_status_when_nothing_set() -> None:
    lines = integration_status({}, read_jira_config=lambda _env: None)
    assert lines == [
        'github: off (set FLEET_GITHUB_ORGS)',
        'jira: off (set FLEET_JIRA_URL)',
        'aws: off (set FLEET_AWS_PROFILES)',
    ]


def test_status_shows_config_errors() -> None:
    def bad(_env: object) -> JiraConfig:
        msg = 'Jira needs a token'
        raise ValueError(msg)

    lines = integration_status(
        {'FLEET_JIRA_URL': 'https://x'},
        read_jira_config=bad,
    )
    assert 'jira: misconfigured: Jira needs a token' in lines


def test_summary_empty_when_nothing_found() -> None:
    assert work_summary(WorkItems()) == ''


def test_summary_counts_alarms_logins_and_tickets() -> None:
    dev = AwsProfile('dev', '')
    alarm = Alarm('api-5xx', '', '', PROD)
    items = WorkItems(
        tickets=(TICKET, TICKET),
        alarms=(
            ProfileAlarms(PROD, (alarm, alarm), needs_login=False, error=''),
            ProfileAlarms(dev, (), needs_login=True, error=''),
        ),
    )
    assert (
        work_summary(items)
        == '🚨 2 alarms · 🔑 dev login expired · 🎫 2 tickets'
    )


def test_summary_singular() -> None:
    items = WorkItems(
        tickets=(TICKET,),
        alarms=(
            ProfileAlarms(
                PROD,
                (Alarm('x', '', '', PROD),),
                needs_login=False,
                error='',
            ),
        ),
    )
    assert work_summary(items) == '🚨 1 alarm · 🎫 1 ticket'


def test_org_fetch_errors_are_reported_with_partial_repos(
    tmp_path: Path,
) -> None:
    items, errors = load_work_items(
        {'FLEET_GITHUB_ORGS': 'acme,typo'},
        tmp_path,
        fetchers(org_repos=lambda _o, _c: ([REPO], ['typo: not found'])),
    )
    assert items.org_repos == (REPO,)
    assert errors == ['github typo: not found']


def test_unexpected_exception_in_one_source_is_contained(
    tmp_path: Path,
) -> None:
    def buggy(_config: JiraConfig) -> list[Ticket]:
        msg = 'surprise'
        raise TypeError(msg)

    items, errors = load_work_items(
        FULL_ENV,
        tmp_path,
        fetchers(tickets=buggy),
    )
    assert items.org_repos == (REPO,)
    assert errors == ['jira: TypeError: surprise']


def test_sources_are_fetched_in_parallel(tmp_path: Path) -> None:
    barrier = threading.Barrier(3, timeout=5)

    def org_repos(_o: object, _c: object) -> tuple[list[OrgRepo], list[str]]:
        barrier.wait()
        return [REPO], []

    def tickets(_config: JiraConfig) -> list[Ticket]:
        barrier.wait()
        return [TICKET]

    def alarms(profiles: list[AwsProfile]) -> list[ProfileAlarms]:
        barrier.wait()
        return [
            ProfileAlarms(p, (), needs_login=False, error='') for p in profiles
        ]

    _, errors = load_work_items(
        FULL_ENV,
        tmp_path,
        fetchers(org_repos=org_repos, tickets=tickets, alarms=alarms),
    )
    assert errors == []


def test_status_never_decrypts_the_pass_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_pass(*_args: object, **_kwargs: object) -> None:
        raise AssertionError

    monkeypatch.setattr('fleet.jira.subprocess.run', no_pass)
    lines = integration_status(
        {
            'FLEET_JIRA_URL': 'https://t.example.test',
            'FLEET_JIRA_PASS_ENTRY': 'work/jira',
        },
    )
    assert (
        'jira: dc at https://t.example.test (token from pass work/jira)'
        in lines
    )
