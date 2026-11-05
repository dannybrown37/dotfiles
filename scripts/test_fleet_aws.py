"""Tests for fleet.aws: read-only CloudWatch alarms and log tails."""

import json
import subprocess
from collections.abc import Callable

import pytest

from fleet.aws import (
    Alarm,
    AwsProfile,
    LogGroup,
    ProfileAlarms,
    alarm_console_url,
    alarms_command,
    configured_log_groups,
    configured_profiles,
    fetch_alarms,
    is_expired_login,
    log_group_console_url,
    log_tail_command,
    parse_alarms,
    sso_login_command,
)

PROD = AwsProfile('prod', 'us-east-1')


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('', []),
        ('prod', [AwsProfile('prod', '')]),
        (
            'prod@us-east-1, dev@eu-west-2,prod@us-east-1',
            [AwsProfile('prod', 'us-east-1'), AwsProfile('dev', 'eu-west-2')],
        ),
        (' , ', []),
    ],
)
def test_configured_profiles(value: str, expected: list[AwsProfile]) -> None:
    assert configured_profiles({'FLEET_AWS_PROFILES': value}) == expected


def test_profiles_unset_is_off() -> None:
    assert configured_profiles({}) == []


@pytest.mark.parametrize(
    'value',
    ['bad profile', 'prod@us east', 'prod@', '@us-east-1', '-rf'],
)
def test_bad_profile_specs_rejected(value: str) -> None:
    with pytest.raises(ValueError, match='FLEET_AWS_PROFILES'):
        configured_profiles({'FLEET_AWS_PROFILES': value})


def test_log_groups_default_to_first_profile() -> None:
    env = {
        'FLEET_AWS_PROFILES': 'prod@us-east-1,dev@eu-west-2',
        'FLEET_AWS_LOG_GROUPS': '/aws/lambda/api, dev:/ecs/web',
    }
    assert configured_log_groups(env, configured_profiles(env)) == [
        LogGroup('/aws/lambda/api', AwsProfile('prod', 'us-east-1')),
        LogGroup('/ecs/web', AwsProfile('dev', 'eu-west-2')),
    ]


def test_log_group_for_unknown_profile_rejected() -> None:
    env = {'FLEET_AWS_PROFILES': 'prod', 'FLEET_AWS_LOG_GROUPS': 'qa:/x'}
    with pytest.raises(ValueError, match='qa'):
        configured_log_groups(env, configured_profiles(env))


def test_log_groups_need_a_profile() -> None:
    env = {'FLEET_AWS_LOG_GROUPS': '/x'}
    with pytest.raises(ValueError, match='FLEET_AWS_PROFILES'):
        configured_log_groups(env, [])


@pytest.mark.parametrize('group', ['has space', '/x;rm', '-f'])
def test_bad_log_group_names_rejected(group: str) -> None:
    env = {'FLEET_AWS_PROFILES': 'prod', 'FLEET_AWS_LOG_GROUPS': group}
    with pytest.raises(ValueError, match='log group'):
        configured_log_groups(env, configured_profiles(env))


def test_alarms_command_is_read_only_and_scoped() -> None:
    command = alarms_command(PROD)
    assert command[:3] == ['aws', 'cloudwatch', 'describe-alarms']
    assert command[command.index('--state-value') + 1] == 'ALARM'
    assert command[command.index('--profile') + 1] == 'prod'
    assert command[command.index('--region') + 1] == 'us-east-1'


def test_alarms_command_without_region_lets_cli_decide() -> None:
    assert '--region' not in alarms_command(AwsProfile('prod', ''))


def test_log_tail_command() -> None:
    command = log_tail_command(LogGroup('/aws/lambda/api', PROD))
    assert command[:4] == ['aws', 'logs', 'tail', '/aws/lambda/api']
    assert '--follow' in command
    assert command[command.index('--profile') + 1] == 'prod'


def test_sso_login_command() -> None:
    assert sso_login_command(PROD) == [
        'aws',
        'sso',
        'login',
        '--profile',
        'prod',
    ]


ALARMS_JSON = json.dumps(
    {
        'MetricAlarms': [
            {
                'AlarmName': 'api-5xx',
                'StateReason': 'Threshold Crossed: 1 datapoint',
                'StateUpdatedTimestamp': '2026-11-04T10:00:00.000Z',
            },
        ],
        'CompositeAlarms': [
            {
                'AlarmName': 'checkout down',
                'StateReason': 'child alarms',
                'StateUpdatedTimestamp': '2026-11-04T11:00:00+00:00',
            },
        ],
    },
)


def test_parse_alarms_newest_first() -> None:
    alarms = parse_alarms(ALARMS_JSON, PROD)
    assert [a.name for a in alarms] == ['checkout down', 'api-5xx']
    assert alarms[1] == Alarm(
        name='api-5xx',
        reason='Threshold Crossed: 1 datapoint',
        updated='2026-11-04T10:00:00.000Z',
        profile=PROD,
    )


@pytest.mark.parametrize('raw', ['', 'nope', '[]'])
def test_parse_alarms_rejects_non_result(raw: str) -> None:
    with pytest.raises(ValueError, match='alarms'):
        parse_alarms(raw, PROD)


def test_parse_alarms_skips_nameless() -> None:
    raw = json.dumps({'MetricAlarms': [{'StateReason': 'x'}, 'junk']})
    assert parse_alarms(raw, PROD) == []


@pytest.mark.parametrize(
    ('region', 'expected'),
    [
        (
            'us-east-1',
            (
                'https://us-east-1.console.aws.amazon.com/cloudwatch/home'
                '?region=us-east-1#alarmsV2:alarm/checkout%20down'
            ),
        ),
        (
            '',
            (
                'https://console.aws.amazon.com/cloudwatch/home'
                '#alarmsV2:alarm/checkout%20down'
            ),
        ),
    ],
)
def test_alarm_console_url(region: str, expected: str) -> None:
    alarm = Alarm('checkout down', '', '', AwsProfile('prod', region))
    assert alarm_console_url(alarm) == expected


@pytest.mark.parametrize(
    ('stderr', 'expired'),
    [
        ('Error when retrieving token from sso: Token has expired', True),
        ('The SSO session associated with this profile has expired', True),
        ('An error occurred (ExpiredToken) when calling', True),
        ('An error occurred (AccessDenied)', False),
        ('', False),
    ],
)
def test_is_expired_login(stderr: str, expired: bool) -> None:  # noqa: FBT001
    assert is_expired_login(stderr) is expired


def fake_run(
    results: dict[str, tuple[int, str, str]],
) -> Callable[[list[str]], subprocess.CompletedProcess[str]]:
    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        profile = command[command.index('--profile') + 1]
        code, out, err = results[profile]
        return subprocess.CompletedProcess(command, code, out, err)

    return run


def test_fetch_alarms_per_profile_with_expiry_and_errors() -> None:
    dev = AwsProfile('dev', '')
    qa = AwsProfile('qa', '')
    run = fake_run(
        {
            'prod': (0, ALARMS_JSON, ''),
            'dev': (255, '', 'Token has expired and refresh failed'),
            'qa': (254, '', 'AccessDenied'),
        },
    )
    results = fetch_alarms([PROD, dev, qa], run=run)
    assert results[0].profile == PROD
    assert [a.name for a in results[0].alarms] == ['checkout down', 'api-5xx']
    assert results[1] == ProfileAlarms(dev, (), needs_login=True, error='')
    assert results[2].needs_login is False
    assert 'AccessDenied' in results[2].error


@pytest.mark.parametrize('error', [FileNotFoundError, PermissionError])
def test_missing_aws_cli_is_named(error: type[OSError]) -> None:
    def run(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise error(2, 'nope', 'aws')

    [result] = fetch_alarms([PROD], run=run)
    assert result.error == 'aws CLI not found on PATH'


def test_naive_and_aware_timestamps_sort_without_crashing() -> None:
    raw = json.dumps(
        {
            'MetricAlarms': [
                {
                    'AlarmName': 'a',
                    'StateUpdatedTimestamp': '2026-11-04T10:00:00',
                },
                {
                    'AlarmName': 'b',
                    'StateUpdatedTimestamp': '2026-11-04T11:00:00+00:00',
                },
                {'AlarmName': 'c', 'StateUpdatedTimestamp': 'garbage'},
            ],
        },
    )
    assert [a.name for a in parse_alarms(raw, PROD)] == ['b', 'a', 'c']


def test_console_url_takes_region_from_alarm_arn_when_profile_has_none() -> (
    None
):
    raw = json.dumps(
        {
            'MetricAlarms': [
                {
                    'AlarmName': 'x',
                    'AlarmArn': (
                        'arn:aws:cloudwatch:eu-west-1:123456789012:alarm:x'
                    ),
                },
            ],
        },
    )
    [alarm] = parse_alarms(raw, AwsProfile('dev', ''))
    assert alarm.region == 'eu-west-1'
    assert alarm_console_url(alarm).startswith(
        'https://eu-west-1.console.aws.amazon.com/cloudwatch/home?region=eu-west-1#',
    )


@pytest.mark.parametrize(
    'arn',
    ['', 'not-an-arn', 'arn:aws:cloudwatch::1:alarm:x'],
)
def test_alarm_without_usable_arn_falls_back_to_profile_region(
    arn: str,
) -> None:
    raw = json.dumps({'MetricAlarms': [{'AlarmName': 'x', 'AlarmArn': arn}]})
    [alarm] = parse_alarms(raw, PROD)
    assert alarm_console_url(alarm).startswith('https://us-east-1.')


@pytest.mark.parametrize(
    ('env', 'expected'),
    [
        ({'AWS_PROFILE': 'work'}, [AwsProfile('work', '')]),
        (
            {'AWS_PROFILE': 'work', 'FLEET_AWS_PROFILES': 'prod'},
            [AwsProfile('prod', '')],
        ),
        ({'AWS_PROFILE': ''}, []),
    ],
)
def test_aws_profile_is_the_fallback(
    env: dict[str, str],
    expected: list[AwsProfile],
) -> None:
    assert configured_profiles(env) == expected


@pytest.mark.parametrize(
    ('region', 'expected'),
    [
        (
            'us-east-1',
            (
                'https://us-east-1.console.aws.amazon.com/cloudwatch/home'
                '?region=us-east-1#logsV2:log-groups/log-group/'
                '$252Faws$252Flambda$252Fapi'
            ),
        ),
        ('', None),
    ],
)
def test_log_group_console_url(region: str, expected: str | None) -> None:
    group = LogGroup('/aws/lambda/api', AwsProfile('prod', region))
    assert log_group_console_url(group) == expected
