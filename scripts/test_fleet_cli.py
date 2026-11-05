"""Tests for fleet.cli argument handling. Launching is in test_fleet_ops."""

import json
from pathlib import Path

import pytest

from fleet import VERSION, cli
from fleet.store import AgentRecord, Store


@pytest.fixture(autouse=True)
def isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('FLEET_STATE_DIR', str(tmp_path / 'state'))
    monkeypatch.setenv('FLEET_TMUX_SOCKET', 'fleet-cli-test-unused')
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('fleet.cli.scan_agent_processes', list)


def test_version_needs_no_state(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main(['--version'])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f'fleet {VERSION}'


def test_bare_run_off_tty_prints_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main([]) == 0
    assert 'usage: fleet' in capsys.readouterr().out


def test_new_without_name_off_tty_names_the_argument(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(['new']) == 2  # noqa: PLR2004
    assert 'NAME' in capsys.readouterr().err


@pytest.mark.parametrize(
    ('argv', 'expected_fleet', 'expected_agent'),
    [
        (['new', 'x'], ['new', 'x'], []),
        (
            ['new', 'x', '--', '--model', 'opus'],
            ['new', 'x'],
            ['--model', 'opus'],
        ),
        (['ls', '--', 'a', '--', 'b'], ['ls'], ['a', '--', 'b']),
    ],
)
def test_split_agent_args(
    argv: list[str],
    expected_fleet: list[str],
    expected_agent: list[str],
) -> None:
    assert cli.split_agent_args(argv) == (expected_fleet, expected_agent)


def test_replay_command_quotes_values() -> None:
    line = cli.replay_command(
        name='fix-x',
        kind='copilot',
        repo_dir=Path('/my repo'),
        base='main',
        prompt="fix the 'thing' *now*",
        extra_args=['--model', 'auto'],
    )
    assert line == (
        "fleet new fix-x -a copilot -C '/my repo' -b main "
        "-p 'fix the '\"'\"'thing'\"'\"' *now*' -- --model auto"
    )


def test_ls_json_lists_records(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    Store(tmp_path / 'state').save(
        AgentRecord(
            name='fix-x',
            kind='claude',
            repo='/r',
            worktree='/w',
            branch='fix-x',
            base='main',
            prompt='p',
            created_at=1.0,
            window_id='@99',
        ),
    )
    assert cli.main(['ls', '--json']) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]['name'] == 'fix-x'
    assert rows[0]['state'] == 'gone'
    assert rows[0]['managed'] is True


def test_unknown_agent_name_is_a_clean_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(['send', 'nobody', 'hi']) == 1
    assert "no agent named 'nobody'" in capsys.readouterr().err


def test_new_rejects_bad_name_before_touching_git(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(['new', 'bad name', '-p', 'x']) == 1
    assert 'invalid agent name' in capsys.readouterr().err
