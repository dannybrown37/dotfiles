"""Tests for net-doctor and rescue in bin/net.sh.

ip, ping, getent, wslpath and powershell.exe are stubs driven by environment
variables, so nothing here touches the real network or the Windows host.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
NET_SH = REPO_ROOT / 'bin' / 'net.sh'
BASH = shutil.which('bash') or '/bin/bash'

GATEWAY = '192.168.1.1'
INTERNET = '1.1.1.1'
LINK_UP = 'lo UNKNOWN 00:00:00:00:00:00\neth0 UP 00:15:5d:00:00:01'
ADDRESS = 'eth0 UP 192.168.1.200/24'
ROUTE = f'default via {GATEWAY} dev eth0 proto kernel metric 281'

IP_STUB = """\
#!/usr/bin/env bash
case "$*" in
*"link show up"*) printf '%s\\n' "${NET_LINK}" ;;
*"addr show"*) printf '%s\\n' "${NET_ADDR}" ;;
*"route show default"*) printf '%s\\n' "${NET_ROUTE}" ;;
esac
"""

PING_STUB = """\
#!/usr/bin/env bash
target="${*: -1}"
[[ " ${PING_OK} " == *" ${target} "* ]]
"""

GETENT_STUB = """\
#!/usr/bin/env bash
[[ "${DNS_OK}" == 1 ]] && echo "93.184.216.34 example.com"
"""

POWERSHELL_STUB = """\
#!/usr/bin/env bash
echo "powershell.exe $*" >> "${CALL_LOG}"
echo "windows doctor ran"
"""

WSLPATH_STUB = """\
#!/usr/bin/env bash
echo "WIN:${*: -1}"
"""

HEALTHY = {
    'NET_LINK': LINK_UP,
    'NET_ADDR': ADDRESS,
    'NET_ROUTE': ROUTE,
    'PING_OK': f'{GATEWAY} {INTERNET}',
    'DNS_OK': '1',
}
CHECK_COUNT = 7


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    path = tmp_path / 'bin'
    path.mkdir()
    _write_executable(path / 'ip', IP_STUB)
    _write_executable(path / 'ping', PING_STUB)
    _write_executable(path / 'getent', GETENT_STUB)
    _write_executable(path / 'wslpath', WSLPATH_STUB)
    return path


def run_net(
    tmp_path: Path,
    stub_bin: Path,
    command: str,
    *,
    overrides: dict[str, str] | None = None,
    nameservers: tuple[str, ...] = ('10.255.255.254',),
    on_windows: bool = False,
) -> subprocess.CompletedProcess[str]:
    resolv_conf = tmp_path / 'resolv.conf'
    resolv_conf.write_text(
        '# generated\n' + ''.join(f'nameserver {ns}\n' for ns in nameservers),
    )
    env = {
        **os.environ,
        **HEALTHY,
        **(overrides or {}),
        'CALL_LOG': str(tmp_path / 'calls.log'),
        'NET_DOCTOR_RESOLV_CONF': str(resolv_conf),
        'DOTFILES_DIR': str(REPO_ROOT),
        'PATH': f'{stub_bin}:/usr/bin:/bin',
    }
    env.pop('ON_WINDOWS', None)
    if on_windows:
        env['ON_WINDOWS'] = 'true'
    return subprocess.run(  # noqa: S603
        [BASH, '-c', f'source "{NET_SH}"; {command}'],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def calls(tmp_path: Path) -> list[str]:
    log = tmp_path / 'calls.log'
    return log.read_text().splitlines() if log.exists() else []


def test_healthy_network_passes_every_check(
    tmp_path: Path,
    stub_bin: Path,
) -> None:
    result = run_net(tmp_path, stub_bin, 'net-doctor')

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count('✅') == CHECK_COUNT
    assert '❌' not in result.stdout


@pytest.mark.parametrize(
    ('overrides', 'nameservers', 'expected'),
    [
        pytest.param(
            {'NET_LINK': 'lo UNKNOWN 00:00:00:00:00:00', 'NET_ROUTE': ''},
            ('10.255.255.254',),
            ['No network interface is up', 'sudo ip link set'],
            id='link-down',
        ),
        pytest.param(
            {'NET_ADDR': 'eth0 UP'},
            ('10.255.255.254',),
            ['eth0 has no IPv4 address', 'sudo dhclient eth0'],
            id='no-ipv4',
        ),
        pytest.param(
            {'NET_ROUTE': '', 'PING_OK': ''},
            ('10.255.255.254',),
            ['No default gateway', 'sudo ip route add default via'],
            id='no-gateway',
        ),
        pytest.param(
            {'PING_OK': ''},
            ('10.255.255.254',),
            [
                f'Gateway {GATEWAY} does not answer',
                f'{INTERNET} is unreachable',
            ],
            id='gateway-and-internet-unreachable',
        ),
        pytest.param(
            {'PING_OK': GATEWAY},
            ('10.255.255.254',),
            [f'{INTERNET} is unreachable', 'router'],
            id='internet-unreachable',
        ),
        pytest.param(
            {'DNS_OK': '0'},
            (),
            [
                'No DNS server configured',
                f"echo 'nameserver {GATEWAY}' | sudo tee",
            ],
            id='no-dns-server',
        ),
        pytest.param(
            {'DNS_OK': '0'},
            ('192.168.1.53',),
            ['DNS server 192.168.1.53 is not answering'],
            id='dns-not-answering',
        ),
    ],
)
def test_doctor_names_the_failure_and_its_fix(
    tmp_path: Path,
    stub_bin: Path,
    overrides: dict[str, str],
    nameservers: tuple[str, ...],
    expected: list[str],
) -> None:
    result = run_net(
        tmp_path,
        stub_bin,
        'net-doctor',
        overrides=overrides,
        nameservers=nameservers,
    )

    assert result.returncode == 1
    for text in expected:
        assert text in result.stdout


def test_gateway_ignoring_ping_is_a_warning_when_internet_answers(
    tmp_path: Path,
    stub_bin: Path,
) -> None:
    result = run_net(
        tmp_path,
        stub_bin,
        'net-doctor',
        overrides={'PING_OK': INTERNET},
    )

    assert result.returncode == 0, result.stdout
    assert '⚠️' in result.stdout
    assert '❌' not in result.stdout


def test_wsl_dns_failure_points_at_windows_and_runs_its_doctor(
    tmp_path: Path,
    stub_bin: Path,
) -> None:
    _write_executable(stub_bin / 'powershell.exe', POWERSHELL_STUB)

    result = run_net(
        tmp_path,
        stub_bin,
        'net-doctor',
        overrides={'DNS_OK': '0'},
        on_windows=True,
    )

    assert result.returncode == 1
    assert 'relays Windows' in result.stdout
    assert 'windows doctor ran' in result.stdout
    assert 'sudo tee' not in result.stdout
    [call] = calls(tmp_path)
    assert 'net.ps1' in call
    assert call.rstrip('"').endswith('net-doctor')


def test_wsl_healthy_network_never_starts_powershell(
    tmp_path: Path,
    stub_bin: Path,
) -> None:
    _write_executable(stub_bin / 'powershell.exe', POWERSHELL_STUB)

    result = run_net(tmp_path, stub_bin, 'net-doctor', on_windows=True)

    assert result.returncode == 0
    assert calls(tmp_path) == []


def test_wsl_without_interop_says_how_to_run_the_windows_doctor(
    tmp_path: Path,
    stub_bin: Path,
) -> None:
    result = run_net(
        tmp_path,
        stub_bin,
        'net-doctor',
        overrides={'DNS_OK': '0'},
        on_windows=True,
    )

    assert result.returncode == 1
    assert 'open Windows PowerShell and run: net-doctor' in result.stdout


def test_rescue_prints_the_offline_cheat_sheet(
    tmp_path: Path,
    stub_bin: Path,
) -> None:
    result = run_net(tmp_path, stub_bin, 'rescue')

    assert result.returncode == 0
    for text in (
        'Set-DnsClientServerAddress',
        'vmconnect.exe localhost homestead',
        'wsl --shutdown',
    ):
        assert text in result.stdout
