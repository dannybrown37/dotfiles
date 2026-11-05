"""Gather every configured work integration; one failure hides no other."""

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from fleet import aws, github_org, jira
from fleet.errors import FETCH_ERRORS, describe_error

ORG_CACHE_NAME = 'github-org-repos.json'


@dataclass(frozen=True)
class WorkItems:
    """What the work integrations found; each is empty when not configured."""

    org_repos: tuple[github_org.OrgRepo, ...] = ()
    tickets: tuple[jira.Ticket, ...] = ()
    alarms: tuple[aws.ProfileAlarms, ...] = ()
    log_groups: tuple[aws.LogGroup, ...] = ()


@dataclass(frozen=True)
class Fetchers:
    org_repos: Callable[
        [Sequence[str], Path],
        tuple[list[github_org.OrgRepo], list[str]],
    ]
    jira_config: Callable[[Mapping[str, str]], jira.JiraConfig | None]
    tickets: Callable[[jira.JiraConfig], list[jira.Ticket]]
    alarms: Callable[[Sequence[aws.AwsProfile]], list[aws.ProfileAlarms]]


def live_fetchers() -> Fetchers:
    return Fetchers(
        org_repos=github_org.fetch_org_repos,
        jira_config=jira.jira_config,
        tickets=jira.fetch_assigned,
        alarms=aws.fetch_alarms,
    )


Found = tuple[WorkItems, list[str]]


def contained(source: str, fetch: Callable[[], Found]) -> Found:
    """Run one source; anything it raises becomes an error line, no crash."""
    try:
        return fetch()
    except FETCH_ERRORS as error:
        return WorkItems(), [f'{source}: {describe_error(error)}']
    except Exception as error:
        return WorkItems(), [f'{source}: {type(error).__name__}: {error}']


def load_work_items(
    env: Mapping[str, str],
    state_dir: Path,
    fetchers: Fetchers,
) -> Found:
    def github() -> Found:
        orgs = github_org.configured_orgs(env)
        if not orgs:
            return WorkItems(), []
        repos, errors = fetchers.org_repos(orgs, state_dir / ORG_CACHE_NAME)
        return (
            WorkItems(org_repos=tuple(repos)),
            [f'github {error}' for error in errors],
        )

    def tickets() -> Found:
        config = fetchers.jira_config(env)
        if config is None:
            return WorkItems(), []
        return WorkItems(tickets=tuple(fetchers.tickets(config))), []

    def alarms() -> Found:
        profiles = aws.configured_profiles(env)
        groups = aws.configured_log_groups(env, profiles)
        results = fetchers.alarms(profiles) if profiles else []
        errors = [
            f'aws {result.profile.label}: {result.error}'
            for result in results
            if result.error
        ]
        return WorkItems(
            alarms=tuple(results),
            log_groups=tuple(groups),
        ), errors

    sources = {'github': github, 'jira': tickets, 'aws': alarms}
    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        futures = [
            pool.submit(contained, name, fetch)
            for name, fetch in sources.items()
        ]
        (gh, gh_errors), (jr, jira_errors), (aw, aws_errors) = (
            future.result() for future in futures
        )
    items = WorkItems(
        org_repos=gh.org_repos,
        tickets=jr.tickets,
        alarms=aw.alarms,
        log_groups=aw.log_groups,
    )
    return items, gh_errors + jira_errors + aws_errors


def integration_status(
    env: Mapping[str, str],
    read_jira_config: Callable[
        [Mapping[str, str]],
        jira.JiraConfig | None,
    ] = jira.jira_config,
) -> list[str]:
    """One line per integration: what is configured, never a secret."""
    lines = []
    orgs = github_org.configured_orgs(env)
    lines.append(
        f'github: orgs {", ".join(orgs)}'
        if orgs
        else 'github: off (set FLEET_GITHUB_ORGS)',
    )
    pass_entry = env.get('FLEET_JIRA_PASS_ENTRY', '')
    token_source = ''
    status_env = env
    if pass_entry and not env.get('FLEET_JIRA_TOKEN'):
        # Status must not decrypt a secret just to say it is configured.
        token_source = f' (token from pass {pass_entry})'
        status_env = {**env, 'FLEET_JIRA_TOKEN': 'not-read'}
    try:
        config = read_jira_config(status_env)
    except FETCH_ERRORS as error:
        lines.append(f'jira: misconfigured: {describe_error(error)}')
    else:
        lines.append(
            f'jira: {config.flavor} at {config.base_url}{token_source}'
            if config
            else 'jira: off (set FLEET_JIRA_URL)',
        )
    try:
        profiles = aws.configured_profiles(env)
        groups = aws.configured_log_groups(env, profiles)
    except ValueError as error:
        lines.append(f'aws: misconfigured: {error}')
    else:
        if profiles:
            names = ', '.join(p.label for p in profiles)
            group_names = ', '.join(g.name for g in groups) or 'none'
            lines.append(f'aws: profiles {names}; log groups {group_names}')
        else:
            lines.append('aws: off (set FLEET_AWS_PROFILES)')
    return lines


def plural(count: int, noun: str) -> str:
    return f'{count} {noun}' + ('' if count == 1 else 's')


def work_summary(items: WorkItems) -> str:
    """One line for the dashboard header: what needs you outside the agents."""
    parts = []
    alarm_count = sum(len(result.alarms) for result in items.alarms)
    if alarm_count:
        parts.append(f'🚨 {plural(alarm_count, "alarm")}')
    parts += [
        f'🔑 {result.profile.name} login expired'
        for result in items.alarms
        if result.needs_login
    ]
    if items.tickets:
        parts.append(f'🎫 {plural(len(items.tickets), "ticket")}')
    return ' · '.join(parts)
