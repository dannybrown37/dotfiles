"""Read-only AWS for the palette: alarms firing now, and log tails.

Profiles come from FLEET_AWS_PROFILES (`name[@region]`, comma-separated) and
log groups from FLEET_AWS_LOG_GROUPS (`[profile:]group`). Only describe and
tail calls are made; nothing here changes AWS state.
"""

import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

PROFILE_NAME = re.compile(r'[A-Za-z0-9_][\w.+-]*')
REGION = re.compile(r'[a-z]{2}(-[a-z]+)+-\d')
LOG_GROUP = re.compile(r'[\w.#/][\w.#/-]*')
EXPIRED_LOGIN = re.compile(
    r'token has expired|session associated with this profile has expired'
    r'|ExpiredToken|error when retrieving token from sso',
    re.IGNORECASE,
)
ALARM_TIMEOUT_SECONDS = 30
OLDEST = datetime.min.replace(tzinfo=UTC)


@dataclass(frozen=True)
class AwsProfile:
    name: str
    region: str

    @property
    def label(self) -> str:
        return f'{self.name}@{self.region}' if self.region else self.name

    def cli_args(self) -> list[str]:
        region = ['--region', self.region] if self.region else []
        return ['--profile', self.name, *region]


@dataclass(frozen=True)
class LogGroup:
    name: str
    profile: AwsProfile


@dataclass(frozen=True)
class Alarm:
    name: str
    reason: str
    updated: str
    profile: AwsProfile
    region: str = ''


@dataclass(frozen=True)
class ProfileAlarms:
    profile: AwsProfile
    alarms: tuple[Alarm, ...]
    needs_login: bool
    error: str


def split_list(value: str) -> list[str]:
    items = [item.strip() for item in value.split(',')]
    return list(dict.fromkeys(item for item in items if item))


def parse_profile(spec: str) -> AwsProfile:
    name, at, region = spec.partition('@')
    if not PROFILE_NAME.fullmatch(name) or (
        at and not REGION.fullmatch(region)
    ):
        msg = (
            f'FLEET_AWS_PROFILES: bad entry {spec!r} '
            '(want name or name@region)'
        )
        raise ValueError(msg)
    return AwsProfile(name, region)


def configured_profiles(
    env: Mapping[str, str] = os.environ,
) -> list[AwsProfile]:
    return [
        parse_profile(spec)
        for spec in split_list(
            env.get('FLEET_AWS_PROFILES') or env.get('AWS_PROFILE', ''),
        )
    ]


def configured_log_groups(
    env: Mapping[str, str],
    profiles: Sequence[AwsProfile],
) -> list[LogGroup]:
    specs = split_list(env.get('FLEET_AWS_LOG_GROUPS', ''))
    if specs and not profiles:
        msg = 'FLEET_AWS_LOG_GROUPS needs FLEET_AWS_PROFILES to be set'
        raise ValueError(msg)
    by_name = {profile.name: profile for profile in profiles}
    groups = []
    for spec in specs:
        profile_name, colon, group = spec.rpartition(':')
        profile = by_name.get(profile_name) if colon else profiles[0]
        if profile is None:
            msg = (
                f'FLEET_AWS_LOG_GROUPS: profile {profile_name!r} '
                'is not in FLEET_AWS_PROFILES'
            )
            raise ValueError(msg)
        if not LOG_GROUP.fullmatch(group):
            msg = f'FLEET_AWS_LOG_GROUPS: bad log group name {group!r}'
            raise ValueError(msg)
        groups.append(LogGroup(group, profile))
    return groups


def alarms_command(profile: AwsProfile) -> list[str]:
    return [
        'aws',
        'cloudwatch',
        'describe-alarms',
        '--state-value',
        'ALARM',
        '--alarm-types',
        'MetricAlarm',
        'CompositeAlarm',
        '--output',
        'json',
        *profile.cli_args(),
    ]


def log_tail_command(group: LogGroup) -> list[str]:
    return [
        'aws',
        'logs',
        'tail',
        group.name,
        '--follow',
        '--since',
        '15m',
        '--format',
        'short',
        *group.profile.cli_args(),
    ]


def sso_login_command(profile: AwsProfile) -> list[str]:
    return ['aws', 'sso', 'login', '--profile', profile.name]


def updated_at(alarm: Alarm) -> datetime:
    try:
        when = datetime.fromisoformat(alarm.updated)
    except ValueError:
        return OLDEST
    return when if when.tzinfo else when.replace(tzinfo=UTC)


def arn_region(arn: str) -> str:
    """arn:aws:cloudwatch:<region>:<account>:alarm:<name> → <region>."""
    parts = arn.split(':')
    if len(parts) > 3 and parts[0] == 'arn' and REGION.fullmatch(parts[3]):  # noqa: PLR2004
        return parts[3]
    return ''


def parse_alarms(raw: str, profile: AwsProfile) -> list[Alarm]:
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if not isinstance(data, dict):
        msg = f'describe-alarms returned no alarms object: {raw[:80]!r}'
        raise ValueError(msg)  # noqa: TRY004  bad CLI output, not a caller bug
    alarms = []
    for key in ('MetricAlarms', 'CompositeAlarms'):
        items = data.get(key)
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or not item.get('AlarmName'):
                continue
            alarms.append(
                Alarm(
                    name=str(item['AlarmName']),
                    reason=str(item.get('StateReason', '')),
                    updated=str(item.get('StateUpdatedTimestamp', '')),
                    profile=profile,
                    region=arn_region(str(item.get('AlarmArn', ''))),
                ),
            )
    return sorted(alarms, key=updated_at, reverse=True)


def log_group_console_url(group: LogGroup) -> str | None:
    """The console double-encodes the group name and swaps % for $."""
    region = group.profile.region
    if not region:
        return None
    name = quote(quote(group.name, safe=''), safe='').replace('%', '$')
    return (
        f'https://{region}.console.aws.amazon.com/cloudwatch/home'
        f'?region={region}#logsV2:log-groups/log-group/{name}'
    )


def alarm_console_url(alarm: Alarm) -> str:
    region = alarm.region or alarm.profile.region
    host = (
        f'{region}.console.aws.amazon.com'
        if region
        else 'console.aws.amazon.com'
    )
    query = f'?region={region}' if region else ''
    name = quote(alarm.name, safe='')
    return f'https://{host}/cloudwatch/home{query}#alarmsV2:alarm/{name}'


def is_expired_login(stderr: str) -> bool:
    return bool(EXPIRED_LOGIN.search(stderr))


def run_aws(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=ALARM_TIMEOUT_SECONDS,
    )


def profile_alarms(
    profile: AwsProfile,
    run: Callable[[list[str]], subprocess.CompletedProcess[str]],
) -> ProfileAlarms:
    try:
        result = run(alarms_command(profile))
    except (FileNotFoundError, PermissionError):
        missing = 'aws CLI not found on PATH'
        return ProfileAlarms(profile, (), needs_login=False, error=missing)
    except (OSError, subprocess.TimeoutExpired) as error:
        return ProfileAlarms(profile, (), needs_login=False, error=str(error))
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if is_expired_login(stderr):
            return ProfileAlarms(profile, (), needs_login=True, error='')
        return ProfileAlarms(
            profile,
            (),
            needs_login=False,
            error=stderr[:300],
        )
    try:
        alarms = parse_alarms(result.stdout, profile)
    except ValueError as error:
        return ProfileAlarms(profile, (), needs_login=False, error=str(error))
    return ProfileAlarms(profile, tuple(alarms), needs_login=False, error='')


def fetch_alarms(
    profiles: Sequence[AwsProfile],
    run: Callable[[list[str]], subprocess.CompletedProcess[str]] = run_aws,
) -> list[ProfileAlarms]:
    if not profiles:
        return []
    with ThreadPoolExecutor(max_workers=min(len(profiles), 6)) as pool:
        return list(pool.map(lambda p: profile_alarms(p, run), profiles))
