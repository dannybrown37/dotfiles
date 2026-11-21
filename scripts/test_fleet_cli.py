"""Tests for fleet.cli argument handling. Launching is in test_fleet_ops."""

import json
import subprocess
from pathlib import Path

import pytest

from fleet import VERSION, cli
from fleet.aws import Alarm, AwsProfile, ProfileAlarms
from fleet.github_org import OrgRepo
from fleet.jira import DEFAULT_JQL, JiraConfig, Ticket
from fleet.ops import SpawnRequest
from fleet.store import AgentRecord, Store
from fleet.work import WorkItems

WORK_ENV = (
    'FLEET_GITHUB_ORGS',
    'FLEET_JIRA_URL',
    'FLEET_JIRA_EMAIL',
    'FLEET_JIRA_TOKEN',
    'FLEET_JIRA_PASS_ENTRY',
    'JIRA_URL',
    'JIRA_API_KEY',
    'FLEET_AWS_PROFILES',
    'FLEET_AWS_LOG_GROUPS',
    'AWS_PROFILE',
)


@pytest.fixture(autouse=True)
def isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('FLEET_STATE_DIR', str(tmp_path / 'state'))
    monkeypatch.setenv('FLEET_TMUX_SOCKET', 'fleet-cli-test-unused')
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr('fleet.cli.scan_agent_processes', list)
    for name in WORK_ENV:
        monkeypatch.delenv(name, raising=False)


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


# ---- work integrations ----------------------

TICKET = Ticket(
    key='ABC-7',
    summary='Fix login',
    status='To Do',
    issue_type='Bug',
    priority='High',
    url='https://tracker.example.test/browse/ABC-7',
    description='Users cannot log in.',
)
JIRA = JiraConfig(
    'https://tracker.example.test',
    'dc',
    '',
    'hush',
    DEFAULT_JQL,
)
PROD = AwsProfile('prod', 'us-east-1')


def test_work_status_needs_no_network(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_fetch(*_args: object) -> None:
        raise AssertionError

    monkeypatch.setattr('fleet.cli.load_work_items', no_fetch)
    monkeypatch.setenv('FLEET_JIRA_URL', 'https://tracker.example.test')
    monkeypatch.setenv('FLEET_JIRA_TOKEN', 'hush')
    assert cli.main(['work', '--status']) == 0
    out = capsys.readouterr().out
    assert 'jira: dc at https://tracker.example.test' in out
    assert 'github: off' in out
    assert 'hush' not in out


def test_work_lists_items_and_fails_on_errors(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    items = WorkItems(
        org_repos=(OrgRepo('acme/api', 'https://github.com/acme/api'),),
        tickets=(TICKET,),
        alarms=(
            ProfileAlarms(
                PROD,
                (Alarm('api-5xx', 'Threshold Crossed', '', PROD),),
                needs_login=False,
                error='',
            ),
        ),
    )
    monkeypatch.setattr(
        'fleet.cli.load_work_items',
        lambda *_args: (items, ['aws dev: AccessDenied']),
    )
    assert cli.main(['work']) == 1
    captured = capsys.readouterr()
    assert 'ABC-7' in captured.out
    assert 'api-5xx' in captured.out
    assert '1 repos' in captured.out
    assert 'aws dev: AccessDenied' in captured.err


def test_work_json(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    items = WorkItems(tickets=(TICKET,))
    monkeypatch.setattr(
        'fleet.cli.load_work_items',
        lambda *_args: (items, []),
    )
    assert cli.main(['work', '--json']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['tickets'][0]['key'] == 'ABC-7'
    assert data['errors'] == []


def test_new_from_jira_ticket_derives_name_and_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requests: list[SpawnRequest] = []

    def fake_spawn(
        _store: object,
        _tmux: object,
        request: SpawnRequest,
    ) -> AgentRecord:
        requests.append(request)
        return AgentRecord(
            name=request.name,
            kind=request.kind,
            repo=str(request.repo_dir),
            worktree='/w',
            branch=request.name,
            base='main',
            prompt=request.prompt,
            created_at=1.0,
            window_id='@1',
        )

    monkeypatch.setattr('fleet.cli.spawn_agent', fake_spawn)
    monkeypatch.setattr('fleet.cli.jira.jira_config', lambda: JIRA)
    monkeypatch.setattr(
        'fleet.cli.jira.fetch_ticket',
        lambda _config, key: TICKET if key == 'ABC-7' else None,
    )
    assert cli.main(['new', '--jira', 'ABC-7', '-C', str(tmp_path)]) == 0
    assert requests[0].name == 'abc-7-fix-login'
    assert 'Users cannot log in.' in requests[0].prompt


def test_new_from_jira_without_config_is_a_clean_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('fleet.cli.jira.jira_config', lambda: None)
    assert cli.main(['new', '--jira', 'ABC-7']) == 1
    assert 'FLEET_JIRA_URL' in capsys.readouterr().err


def test_new_jira_without_key_off_tty_lists_your_tickets(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('fleet.cli.jira.jira_config', lambda: JIRA)
    monkeypatch.setattr('fleet.cli.jira.fetch_assigned', lambda _c: [TICKET])
    assert cli.main(['new', 'x', '--jira']) == 1
    err = capsys.readouterr().err
    assert 'missing KEY' in err
    assert 'ABC-7' in err


def test_pick_ticket_uses_fzf_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    monkeypatch.setattr('fleet.cli.shutil.which', lambda _name: '/usr/bin/fzf')
    shown: list[str] = []

    def fake_fzf(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        shown.append(str(kwargs['input']))
        return subprocess.CompletedProcess(
            command,
            0,
            'ABC-7\tFix login\n',
            '',
        )

    monkeypatch.setattr('fleet.cli.subprocess.run', fake_fzf)
    assert cli.pick_ticket([TICKET]) == TICKET
    assert shown == ['ABC-7\tTo Do\tFix login']


def test_picked_ticket_echoes_the_replay_command(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_spawn(
        _store: object,
        _tmux: object,
        request: SpawnRequest,
    ) -> AgentRecord:
        return AgentRecord(
            name=request.name,
            kind=request.kind,
            repo=str(request.repo_dir),
            worktree='/w',
            branch=request.name,
            base='main',
            prompt='',
            created_at=1.0,
            window_id='@1',
        )

    monkeypatch.setattr('fleet.cli.spawn_agent', fake_spawn)
    monkeypatch.setattr('fleet.cli.jira.jira_config', lambda: JIRA)
    monkeypatch.setattr('fleet.cli.jira.fetch_assigned', lambda _c: [TICKET])
    monkeypatch.setattr('fleet.cli.pick_ticket', lambda tickets: tickets[0])
    assert (
        cli.main(['new', '--jira', '-C', str(tmp_path), '-a', 'claude']) == 0
    )
    out = capsys.readouterr().out
    assert (
        f'fleet new abc-7-fix-login --jira ABC-7 -a claude -C {tmp_path}'
        in out
    )


def test_new_autopilot_wraps_the_task_and_flags_the_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requests: list[SpawnRequest] = []

    def fake_spawn(
        _store: object,
        _tmux: object,
        request: SpawnRequest,
    ) -> AgentRecord:
        requests.append(request)
        return AgentRecord(
            name=request.name,
            kind=request.kind,
            repo=str(request.repo_dir),
            worktree='/w',
            branch=request.name,
            base='main',
            prompt=request.prompt,
            created_at=1.0,
            window_id='@1',
        )

    monkeypatch.setattr('fleet.cli.spawn_agent', fake_spawn)
    argv = ['new', 'fix-x', '--autopilot', '-p', 'do it', '-C', str(tmp_path)]
    assert cli.main(argv) == 0
    assert requests[0].autopilot is True
    assert requests[0].prompt.startswith('do it')
    assert '.fleet/plan.md' in requests[0].prompt
    assert 'fleet pr fix-x' in capsys.readouterr().out


def test_new_autopilot_needs_a_task(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    argv = ['new', 'fix-x', '--autopilot', '-p', '', '-C', str(tmp_path)]
    assert cli.main(argv) == 1
    assert 'needs a task' in capsys.readouterr().err


def test_pr_opens_draft_for_the_agent_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    calls: list[tuple[Path, str, str]] = []

    def fake_open(worktree: Path, branch: str, base: str) -> str:
        calls.append((worktree, branch, base))
        return 'https://github.example.test/o/r/pull/7'

    monkeypatch.setattr('fleet.cli.open_draft_pr', fake_open)
    assert cli.main(['pr', 'fix-x']) == 0
    assert calls == [(Path('/w'), 'fix-x', 'main')]
    assert 'pull/7' in capsys.readouterr().out


def test_work_shows_mentions_in_text_and_json(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        'fleet.cli.load_work_items',
        lambda *_args: (WorkItems(mentions=(TICKET,)), []),
    )
    assert cli.main(['work']) == 0
    assert '💬 ABC-7' in capsys.readouterr().out
    assert cli.main(['work', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['mentions'][0]['key'] == 'ABC-7'


@pytest.fixture
def hook_homes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / 'home'
    source = tmp_path / 'fleet.json'
    source.write_text('{}')
    monkeypatch.setattr(
        'fleet.cli.CLAUDE_SETTINGS',
        home / '.claude' / 'settings.json',
    )
    monkeypatch.setattr(
        'fleet.cli.COPILOT_HOOK_LINK',
        home / '.copilot' / 'hooks' / 'fleet.json',
    )
    monkeypatch.setattr('fleet.cli.COPILOT_HOOK_FILE', source)
    monkeypatch.setattr('fleet.cli.HOOK_PATH', tmp_path / 'fleet-hook.sh')
    return home


def run_hooks(action: str, capsys: pytest.CaptureFixture[str]) -> list[str]:
    """Per-agent verbs, then the status lines, of one `fleet hooks` run."""
    assert cli.main(['hooks', action]) == 0
    lines = capsys.readouterr().out.splitlines()
    return [line.split(':')[0] for line in lines[:2]] + lines[2:]


def test_hooks_install_then_uninstall(
    hook_homes: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (hook_homes / '.claude').mkdir(parents=True)
    (hook_homes / '.copilot').mkdir()

    assert run_hooks('install', capsys) == [
        'installed',
        'installed',
        'claude hooks:  on',
        'copilot hooks: on',
    ]
    assert run_hooks('install', capsys)[:2] == ['already installed'] * 2
    assert run_hooks('uninstall', capsys) == [
        'removed',
        'removed',
        'claude hooks:  off',
        'copilot hooks: off',
    ]


def test_hooks_install_skips_agents_that_are_not_set_up(
    hook_homes: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_hooks('install', capsys) == [
        'skipped',
        'skipped',
        'claude hooks:  off',
        'copilot hooks: off',
    ]
    assert not hook_homes.exists()
