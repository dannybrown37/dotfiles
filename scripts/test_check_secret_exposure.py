"""Tests for the PreToolUse secret-exposure guard."""

import json

import pytest

from check_secret_exposure import (
    BLOCK_EXIT_CODE,
    detect_bash_risk,
    is_secret_file,
    main,
    read_payload,
)


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
