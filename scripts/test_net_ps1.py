"""Tests for the pure decision logic in windows/net.ps1.

These run the real Windows PowerShell through WSL interop, so they are skipped
anywhere powershell.exe is missing (CI included). Only functions that take data
and return data are called: nothing here reads or changes an adapter.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).parent.parent
NET_PS1 = REPO_ROOT / 'windows' / 'net.ps1'
POWERSHELL = shutil.which('powershell.exe')
WSLPATH = shutil.which('wslpath')
SWITCH = 'vEthernet (homestead-external)'
GATEWAY = '192.168.1.1'

pytestmark = pytest.mark.skipif(
    POWERSHELL is None or WSLPATH is None,
    reason='needs Windows PowerShell via WSL interop',
)

HEALTHY_FACTS: dict[str, Any] = {
    'Alias': SWITCH,
    'LinkUp': True,
    'IPv4': ['192.168.1.200'],
    'Gateway': GATEWAY,
    'GatewayReachable': True,
    'InternetReachable': True,
    'DnsServers': [GATEWAY],
    'DnsAnswers': True,
}
CHECK_COUNT = 7


def windows_path(path: Path) -> str:
    assert WSLPATH is not None
    return subprocess.run(  # noqa: S603
        [WSLPATH, '-w', str(path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def run_powershell(
    tmp_path: Path,
    payload: dict[str, Any],
    expression: str,
) -> subprocess.CompletedProcess[str]:
    """Run `expression` with $in bound to the payload, printing JSON."""
    assert POWERSHELL is not None
    payload_file = tmp_path / 'payload.json'
    payload_file.write_text(json.dumps(payload))
    command = (
        "$ErrorActionPreference = 'Stop'; "
        f". '{windows_path(NET_PS1)}'; "
        f"$in = Get-Content -Raw '{windows_path(payload_file)}' "
        '| ConvertFrom-Json; '
        f'ConvertTo-Json -Depth 5 -Compress -InputObject @({expression})'
    )
    return subprocess.run(  # noqa: S603
        [
            POWERSHELL,
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-Command',
            command,
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def findings(tmp_path: Path, **changes: Any) -> list[dict[str, Any]]:  # noqa: ANN401
    result = run_powershell(
        tmp_path,
        {**HEALTHY_FACTS, **changes},
        'Get-NetDoctorFindings -Facts $in',
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def restore_plan(
    tmp_path: Path,
    snapshot: list[dict[str, Any]],
    current: list[dict[str, Any]],
    *,
    full: bool = False,
) -> subprocess.CompletedProcess[str]:
    return run_powershell(
        tmp_path,
        {'Snapshot': snapshot, 'Current': current},
        'Get-NetRestorePlan -Snapshot $in.Snapshot -Current $in.Current '
        f"-TargetAlias '{SWITCH}' -Full:${str(full).lower()}",
    )


def adapter(alias: str, **changes: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        'Alias': alias,
        'IPv4': '192.168.1.200',
        'PrefixLength': 24,
        'Gateway': GATEWAY,
        'Dns': [GATEWAY],
        'Dhcp': False,
        **changes,
    }


def test_healthy_facts_pass_every_check(tmp_path: Path) -> None:
    result = findings(tmp_path)

    assert [f['Status'] for f in result] == ['ok'] * CHECK_COUNT


@pytest.mark.parametrize(
    ('changes', 'message', 'fix'),
    [
        pytest.param(
            {'LinkUp': False},
            'is not up',
            f"Enable-NetAdapter -Name '{SWITCH}'",
            id='link-down',
        ),
        pytest.param(
            {'IPv4': []},
            'has no IPv4 address',
            'net-restore -Full',
            id='no-ipv4',
        ),
        pytest.param(
            {'Gateway': None, 'GatewayReachable': False},
            'No default gateway',
            f"New-NetRoute -InterfaceAlias '{SWITCH}'",
            id='no-gateway',
        ),
        pytest.param(
            {'GatewayReachable': False, 'InternetReachable': False},
            f'Gateway {GATEWAY} does not answer',
            'cable',
            id='gateway-unreachable',
        ),
        pytest.param(
            {'InternetReachable': False},
            '1.1.1.1 is unreachable',
            'router or ISP',
            id='internet-unreachable',
        ),
        pytest.param(
            {'DnsServers': [], 'DnsAnswers': False},
            f"No DNS server configured on '{SWITCH}'",
            f'dns-set {GATEWAY}',
            id='no-dns-server',
        ),
        pytest.param(
            {'DnsAnswers': False},
            f'DNS server {GATEWAY} is not answering',
            'dns-set 1.1.1.1',
            id='dns-not-answering',
        ),
    ],
)
def test_findings_name_the_failure_and_fix_with_the_real_adapter(
    tmp_path: Path,
    changes: dict[str, Any],
    message: str,
    fix: str,
) -> None:
    failures = [
        f for f in findings(tmp_path, **changes) if f['Status'] == 'fail'
    ]

    assert failures, 'expected at least one failing check'
    assert message in failures[0]['Message']
    assert fix in failures[0]['Fix']


def test_missing_dns_fix_spells_out_the_raw_command(tmp_path: Path) -> None:
    [failure] = [
        f
        for f in findings(tmp_path, DnsServers=[], DnsAnswers=False)
        if f['Status'] == 'fail'
    ]

    assert (
        f"Set-DnsClientServerAddress -InterfaceAlias '{SWITCH}' "
        f"-ServerAddresses '{GATEWAY}'"
    ) in failure['Fix']


def test_gateway_ignoring_ping_is_a_warning_when_internet_answers(
    tmp_path: Path,
) -> None:
    statuses = [
        f['Status'] for f in findings(tmp_path, GatewayReachable=False)
    ]

    assert 'warn' in statuses
    assert 'fail' not in statuses


def test_no_adapter_at_all_is_a_single_failure(tmp_path: Path) -> None:
    [only] = findings(tmp_path, Alias=None, LinkUp=False)

    assert only['Status'] == 'fail'
    assert 'No network adapter' in only['Message']


def test_restore_puts_dns_on_the_adapter_that_now_holds_the_gateway(
    tmp_path: Path,
) -> None:
    result = restore_plan(
        tmp_path,
        snapshot=[adapter('Ethernet')],
        current=[adapter(SWITCH, Dns=[])],
    )

    assert result.returncode == 0, result.stderr
    [plan] = json.loads(result.stdout)
    expected = (
        f"Set-DnsClientServerAddress -InterfaceAlias '{SWITCH}' "
        f"-ServerAddresses '{GATEWAY}'"
    )
    assert plan['Commands'] == [expected]


def test_restore_has_nothing_to_do_when_dns_already_matches(
    tmp_path: Path,
) -> None:
    result = restore_plan(
        tmp_path,
        snapshot=[adapter(SWITCH)],
        current=[adapter(SWITCH)],
        full=True,
    )

    assert result.returncode == 0, result.stderr
    [plan] = json.loads(result.stdout)
    assert plan['Commands'] == []


def test_full_restore_refuses_ip_changes_when_the_adapter_was_renamed(
    tmp_path: Path,
) -> None:
    result = restore_plan(
        tmp_path,
        snapshot=[adapter('Ethernet')],
        current=[adapter(SWITCH, IPv4='192.168.1.77', Dns=[])],
        full=True,
    )

    assert result.returncode == 0, result.stderr
    [plan] = json.loads(result.stdout)
    assert len(plan['Commands']) == 1
    assert 'New-NetIPAddress' not in ' '.join(plan['Commands'])
    assert 'Ethernet' in ' '.join(plan['Notes'])


def test_full_restore_reapplies_a_static_address_on_the_same_adapter(
    tmp_path: Path,
) -> None:
    result = restore_plan(
        tmp_path,
        snapshot=[adapter(SWITCH)],
        current=[adapter(SWITCH, IPv4='192.168.1.77')],
        full=True,
    )

    assert result.returncode == 0, result.stderr
    [plan] = json.loads(result.stdout)
    assert plan['Commands'][-1] == (
        f"New-NetIPAddress -InterfaceAlias '{SWITCH}' "
        f"-IPAddress '192.168.1.200' "
        f"-PrefixLength 24 -DefaultGateway '{GATEWAY}'"
    )


def test_restore_rejects_a_snapshot_carrying_anything_but_ip_addresses(
    tmp_path: Path,
) -> None:
    result = restore_plan(
        tmp_path,
        snapshot=[
            adapter('Ethernet', Dns=["1.1.1.1'; Start-Process calc; '"]),
        ],
        current=[adapter(SWITCH, Dns=[])],
    )

    assert result.returncode != 0
    assert 'not an IPv4 address' in result.stderr
