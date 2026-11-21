"""Tests for the PreToolUse secret-exposure guard."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from check_secret_exposure import (
    BLOCK_EXIT_CODE,
    SKIP_ENV_VAR,
    detect_bash_risk,
    is_secret_file,
    main,
    read_payload,
)

SCRIPT = Path(__file__).parent / 'check_secret_exposure.py'


@pytest.mark.parametrize(
    ('stdin', 'expected_code'),
    [
        pytest.param(b'\xff\xfe', 0, id='undecodable'),
        pytest.param(b'', 0, id='empty'),
        pytest.param(
            b'{"tool_name": "Bash", "tool_input": {"command": "printenv"}}',
            BLOCK_EXIT_CODE,
            id='still-blocks',
        ),
    ],
)
def test_script_exit_codes(stdin: bytes, expected_code: int) -> None:
    env = {k: v for k, v in os.environ.items() if k != SKIP_ENV_VAR}
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)],
        input=stdin,
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode == expected_code
    assert result.stdout == b''
    if expected_code == 0:
        assert result.stderr == b''


@pytest.mark.parametrize(
    'command',
    [
        'env',
        'env | grep TOKEN',
        'printenv',
        'printenv GITHUB_TOKEN',
        'printenv MY_GITHUB_TOKEN',
        'set',
        'echo $GITHUB_TOKEN',
        'echo "$MY_GITHUB_TOKEN"',
        'echo ${GITHUB_TOKEN}',
        'printf "%s" "$API_KEY"',
        'cat config/.secrets',
        'cat config/.secrets.bak',
        'less .env',
        'head -n1 .env.local',
        'bat ahk/secrets.ahk',
        'ls && cat config/.secrets',
        'grep TOKEN config/.secrets',
        'rg PRIVACY config/.secrets',
        'sed -n 1p config/.secrets',
        'awk "{print}" .env',
        'pass show manifest',
        'pass manifest',
        'pass some/token',
        'pass grep TOKEN',
        'pass generate new/entry',
        'gh auth token',
        'gh auth status --show-token',
        'gh auth status -t',
        'export -p',
        'export',
        'declare -p',
        'declare -p GITHUB_TOKEN',
        'typeset -p',
        'git credential fill <<<"protocol=https"',
        'base64 config/.secrets',
        'cut -c1- config/.secrets',
        'glow config/.secrets',
        'glow -s dark -w 80 .env',
        'tac .env',
        'diff .env .env.example',
    ],
)
def test_detect_bash_risk_flags_dangerous_commands(command: str) -> None:
    assert detect_bash_risk(command) is not None


@pytest.mark.parametrize(
    'command',
    [
        'echo hello',
        'printenv HOME',
        'env FOO=bar make test',
        'set -euo pipefail',
        'set -x',
        'cat notes.txt',
        'grep TOKEN notes.txt',
        'source config/.secrets',
        'ls config/',
        'echo "$HOME/bin"',
        'wc -l config/.secrets',
        'pass',
        'pass ls',
        'pass git pull --rebase',
        'pass insert -m some/token',
        'pass show -c manifest',
        'pass generate -c new/entry',
        'gh auth status',
        'export FOO=bar',
        'declare -p HOME',
        'git credential-cache exit',
    ],
)
def test_detect_bash_risk_allows_safe_commands(command: str) -> None:
    assert detect_bash_risk(command) is None


@pytest.mark.parametrize(
    ('path', 'expected'),
    [
        ('config/.secrets', True),
        ('config/.secrets.bak', True),
        ('ahk/secrets.ahk', True),
        ('.env', True),
        ('.env.local', True),
        ('/home/danny/projects/dotfiles/.env.production', True),
        ('config/.secrets.example', False),
        ('notes.txt', False),
        ('envelope.txt', False),
    ],
)
def test_is_secret_file(path: str, *, expected: bool) -> None:
    assert is_secret_file(path) == expected


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('{"tool_name": "Bash"}', {'tool_name': 'Bash'}),
        ('', {}),
        ('not json', {}),
        ('[1, 2]', {}),
    ],
)
def test_read_payload_tolerates_bad_input(
    raw: str,
    expected: dict[str, object],
) -> None:
    assert read_payload(raw) == expected


def test_main_blocks_risky_bash_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = json.dumps(
        {
            'tool_name': 'Bash',
            'tool_input': {'command': 'cat config/.secrets'},
        },
    )

    assert main(payload) == BLOCK_EXIT_CODE
    assert 'config/.secrets' in capsys.readouterr().err


def test_main_allows_safe_bash_command() -> None:
    payload = json.dumps(
        {'tool_name': 'Bash', 'tool_input': {'command': 'ls -la'}},
    )

    assert main(payload) == 0


def test_main_blocks_read_of_secret_file(
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = json.dumps(
        {'tool_name': 'Read', 'tool_input': {'file_path': 'config/.secrets'}},
    )

    assert main(payload) == BLOCK_EXIT_CODE
    assert 'config/.secrets' in capsys.readouterr().err


def test_main_allows_read_of_ordinary_file() -> None:
    payload = json.dumps(
        {'tool_name': 'Read', 'tool_input': {'file_path': 'README.md'}},
    )

    assert main(payload) == 0


@pytest.mark.parametrize(
    'tool_input',
    [
        {'pattern': '.', 'path': 'config/.secrets'},
        {'pattern': 'TOKEN', 'path': 'config', 'glob': '.secrets'},
        {'pattern': 'KEY', 'glob': '**/.env.*'},
    ],
)
def test_main_blocks_grep_of_secret_file(tool_input: dict[str, str]) -> None:
    payload = json.dumps({'tool_name': 'Grep', 'tool_input': tool_input})

    assert main(payload) == BLOCK_EXIT_CODE


def test_main_allows_grep_of_ordinary_files() -> None:
    payload = json.dumps(
        {'tool_name': 'Grep', 'tool_input': {'pattern': 'x', 'path': 'src'}},
    )

    assert main(payload) == 0


def test_main_ignores_other_tools() -> None:
    payload = json.dumps(
        {'tool_name': 'Glob', 'tool_input': {'pattern': '**/.secrets'}},
    )

    assert main(payload) == 0


def test_main_respects_skip_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('SECRET_GUARD_SKIP', '1')
    payload = json.dumps(
        {
            'tool_name': 'Bash',
            'tool_input': {'command': 'cat config/.secrets'},
        },
    )

    assert main(payload) == 0


def test_main_tolerates_missing_tool_input() -> None:
    assert main(json.dumps({'tool_name': 'Bash'})) == 0


def test_main_tolerates_garbage_payload() -> None:
    assert main('not json at all') == 0
