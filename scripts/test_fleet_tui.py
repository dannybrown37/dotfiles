"""Headless tests for the fleet dashboard, driven through Textual's pilot."""

import asyncio
import subprocess
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from textual.coordinate import Coordinate
from textual.pilot import Pilot
from textual.widget import Widget
from textual.widgets import DataTable, Input, Markdown, TextArea

from fleet.agents import AgentState
from fleet.github_org import OrgRepo
from fleet.jira import DEFAULT_JQL, JiraConfig, Ticket
from fleet.palette import PaletteEntry
from fleet.procs import AgentProcess
from fleet.radar import ChecksState, PullRequest, Review, ReviewCache
from fleet.store import AgentRecord, Store
from fleet.tmux import Tmux
from fleet.tui import FleetApp, relative_age, review_markdown, run_captured
from fleet.work import Fetchers


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('FLEET_STATE_DIR', str(tmp_path / 'state'))
    monkeypatch.setattr('fleet.tui.agent_pr', lambda _worktree: None)


def make_pr(number: int, files: tuple[str, ...]) -> PullRequest:
    return PullRequest(
        repo='acme/api',
        number=number,
        title=f'PR {number}',
        author='sam',
        is_bot=False,
        url=f'https://github.com/acme/api/pull/{number}',
        is_draft=False,
        created_at=datetime.now(UTC) - timedelta(hours=1),
        additions=10,
        deletions=1,
        files=files,
        head_sha=f'sha{number:09d}',
        checks=ChecksState.PASSING,
    )


def make_app(
    tmp_path: Path,
    prs: list[PullRequest],
    processes: list[AgentProcess] | None = None,
    work_env: dict[str, str] | None = None,
    work_fetchers: Fetchers | None = None,
) -> FleetApp:
    store = Store(tmp_path / 'state')
    store.save(
        AgentRecord(
            name='fix-x',
            kind='claude',
            repo=str(tmp_path),
            worktree=str(tmp_path / 'missing'),
            branch='fix-x',
            base='main',
            prompt='fix the flaky test',
            created_at=1.0,
            window_id='@999',
        ),
    )
    tmux = Tmux(socket='fleet-tui-test-no-server')
    return FleetApp(
        store,
        tmux,
        fetch_prs=lambda: prs,
        projects=tmp_path,
        scan_processes=lambda: processes or [],
        work_fetchers=work_fetchers,
        work_env=work_env or {},
    )


def run_with_pilot(
    app: FleetApp,
    scenario: Callable[[Pilot[int]], Awaitable[None]],
) -> None:
    async def runner() -> None:
        async with app.run_test(size=(140, 40)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            await scenario(pilot)

    asyncio.run(runner())


async def modal_field[W: Widget](
    pilot: Pilot[int],
    selector: str,
    kind: type[W],
) -> W:
    """Pushed modals compose a tick later; under -n 6 one pause can miss it."""
    for _ in range(100):
        found = pilot.app.screen.query(selector)
        if found:
            return found.first(kind)
        await pilot.pause(0.05)
    msg = f'{selector} never appeared on {type(pilot.app.screen).__name__}'
    raise AssertionError(msg)


def cell_text(table: DataTable[object], row: int, column: int) -> str:
    return str(table.get_cell_at(Coordinate(row, column)))


def test_agent_row_shows_gone_state_and_prompt(tmp_path: Path) -> None:
    app = make_app(tmp_path, [])

    async def scenario(_pilot: Pilot[int]) -> None:
        table = app.query_one('#agents-table', DataTable)
        assert table.row_count == 1
        assert 'gone' in cell_text(table, 0, 0)
        assert cell_text(table, 0, 2) == 'fix-x'
        assert 'flaky' in cell_text(table, 0, 7)

    run_with_pilot(app, scenario)


def test_session_fleet_did_not_start_is_listed_but_not_stoppable(
    tmp_path: Path,
) -> None:
    session = AgentProcess(
        pid=4321,
        kind='copilot',
        cwd='/home/u/projects/web',
        start_time=1,
        tmux_socket='',
        tmux_pane='',
        fleet_agent='',
        background=False,
    )
    Store(tmp_path / 'state').write_session(
        4321,
        1,
        AgentState.WAITING,
        'notification',
        'allow shell?',
        1.0,
    )
    app = make_app(tmp_path, [], [session])

    async def scenario(pilot: Pilot[int]) -> None:
        table = app.query_one('#agents-table', DataTable)
        assert table.row_count == 2  # noqa: PLR2004
        assert cell_text(table, 0, 2) == 'web'
        assert 'waiting' in cell_text(table, 0, 0)
        assert cell_text(table, 0, 3) == 'terminal'
        assert 'allow shell?' in cell_text(table, 0, 7)
        await pilot.press('x')
        await pilot.pause()
        assert type(app.screen).__name__ == 'Screen'

    run_with_pilot(app, scenario)


def test_reviews_ranked_with_risky_pr_first(tmp_path: Path) -> None:
    safe = make_pr(1, ('README.md',))
    risky = make_pr(2, ('src/auth/token.py', 'db/migrations/1.sql'))
    app = make_app(tmp_path, [safe, risky])

    async def scenario(pilot: Pilot[int]) -> None:
        await pilot.press('2')
        await pilot.pause()
        table = app.query_one('#reviews-table', DataTable)
        assert table.row_count == 2  # noqa: PLR2004
        assert cell_text(table, 0, 2) == 'acme/api#2'
        assert cell_text(table, 1, 1) == '⚡'

    run_with_pilot(app, scenario)


def test_cached_review_shows_in_preview(tmp_path: Path) -> None:
    pr = make_pr(3, ('src/a.py',))
    ReviewCache(tmp_path / 'state' / 'reviews').put(
        pr,
        Review(text='RISK: high\nSUMMARY: rewrites billing', agent='copilot'),
    )
    app = make_app(tmp_path, [pr])

    async def scenario(pilot: Pilot[int]) -> None:
        await pilot.press('2')
        await pilot.pause()
        table = app.query_one('#reviews-table', DataTable)
        assert 'rewrites billing' in cell_text(table, 0, 4)
        markdown = app.query_one('#review-preview', Markdown)
        assert 'copilot' in markdown.source

    run_with_pilot(app, scenario)


def test_agent_actions_hidden_on_reviews_tab(tmp_path: Path) -> None:
    app = make_app(tmp_path, [])

    async def scenario(pilot: Pilot[int]) -> None:
        assert app.check_action('send', ()) is True
        assert app.check_action('review', ()) is False
        await pilot.press('2')
        await pilot.pause()
        assert app.check_action('send', ()) is False
        assert app.check_action('review', ()) is True

    run_with_pilot(app, scenario)


@pytest.mark.parametrize(
    ('keys', 'expected_row'),
    [
        (('j',), 1),
        (('j', 'j', 'k'), 1),
        (('G',), 2),
        (('G', 'g'), 0),
        (('k',), 0),
    ],
)
def test_vim_keys_move_the_review_cursor(
    tmp_path: Path,
    keys: tuple[str, ...],
    expected_row: int,
) -> None:
    app = make_app(tmp_path, [make_pr(n, ('src/a.py',)) for n in (1, 2, 3)])

    async def scenario(pilot: Pilot[int]) -> None:
        await pilot.press('2', *keys)
        await pilot.pause()
        assert (
            app.query_one('#reviews-table', DataTable).cursor_row
            == expected_row
        )

    run_with_pilot(app, scenario)


@pytest.mark.parametrize(
    ('keys', 'expected_tab'),
    [
        (('l',), 'reviews'),
        (('l', 'l'), 'reviews'),
        (('l', 'h'), 'agents'),
        (('h',), 'agents'),
    ],
)
def test_h_and_l_switch_tabs(
    tmp_path: Path,
    keys: tuple[str, ...],
    expected_tab: str,
) -> None:
    app = make_app(tmp_path, [make_pr(1, ('src/a.py',))])

    async def scenario(pilot: Pilot[int]) -> None:
        await pilot.press(*keys)
        await pilot.pause()
        assert app.active_tab() == expected_tab
        assert app.focused is app.query_one(
            f'#{expected_tab}-table',
            DataTable,
        )

    run_with_pilot(app, scenario)


def test_lazygit_moved_off_g_so_g_can_mean_top() -> None:
    keys = {binding.key: binding.action for binding in FleetApp.BINDINGS}  # type: ignore[union-attr]
    assert keys['L'] == 'lazygit'
    assert keys['g'] == 'table("scroll_top")'


def test_new_agent_dialog_opens_and_cancels(tmp_path: Path) -> None:
    app = make_app(tmp_path, [])

    async def scenario(pilot: Pilot[int]) -> None:
        await pilot.press('n')
        await pilot.pause()
        assert type(app.screen).__name__ == 'NewAgentScreen'
        await pilot.press('escape')
        await pilot.pause()
        assert type(app.screen).__name__ == 'Screen'

    run_with_pilot(app, scenario)


TICKET = Ticket(
    key='ABC-7',
    summary='Fix login',
    status='To Do',
    issue_type='Bug',
    priority='High',
    url='https://tracker.example.test/browse/ABC-7',
    description='Users cannot log in.',
)
JIRA = JiraConfig('https://tracker.example.test', 'dc', '', 't', DEFAULT_JQL)


def work_fetchers(
    tickets: list[Ticket] | None = None,
    org_repos: list[OrgRepo] | None = None,
) -> Fetchers:
    return Fetchers(
        org_repos=lambda _orgs, _cache: (org_repos or [], []),
        jira_config=lambda _env: JIRA,
        tickets=lambda _config: tickets or [],
        alarms=lambda _profiles: [],
    )


def test_work_items_load_on_mount(tmp_path: Path) -> None:
    app = make_app(tmp_path, [], work_fetchers=work_fetchers([TICKET]))

    async def scenario(_pilot: Pilot[int]) -> None:
        assert app.work.tickets == (TICKET,)
        assert app.sub_title == '🎫 1 ticket'

    run_with_pilot(app, scenario)


def test_work_errors_are_shown_once(tmp_path: Path) -> None:
    def jira_down(_config: JiraConfig) -> list[Ticket]:
        msg = 'Jira 503'
        raise ValueError(msg)

    fetchers = Fetchers(
        org_repos=lambda _orgs, _cache: ([], []),
        jira_config=lambda _env: JIRA,
        tickets=jira_down,
        alarms=lambda _profiles: [],
    )
    app = make_app(tmp_path, [], work_fetchers=fetchers)

    async def scenario(pilot: Pilot[int]) -> None:
        app.refresh_work()
        await app.workers.wait_for_complete()
        await pilot.pause()
        jira_notes = [n for n in app._notifications if 'Jira 503' in n.message]  # noqa: SLF001
        assert len(jira_notes) == 1

    run_with_pilot(app, scenario)


def test_agent_from_ticket_prefills_new_agent_form(tmp_path: Path) -> None:
    app = make_app(tmp_path, [], work_fetchers=work_fetchers([TICKET]))

    async def scenario(pilot: Pilot[int]) -> None:
        app.run_palette_entry(PaletteEntry('', '', 'jira-agent', 'ABC-7'))
        await pilot.pause()
        name = await modal_field(pilot, '#name', Input)
        assert type(app.screen).__name__ == 'NewAgentScreen'
        assert name.value == 'abc-7-fix-login'
        prompt = (await modal_field(pilot, '#prompt', TextArea)).text
        assert 'Users cannot log in.' in prompt

    run_with_pilot(app, scenario)


def test_run_entry_opens_a_window_and_jumps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_app(tmp_path, [])
    opened: list[tuple[str, tuple[str, ...]]] = []
    jumped: list[str] = []

    def new_window(
        _session: str,
        name: str,
        _cwd: Path,
        _env: dict[str, str],
        command: list[str],
    ) -> str:
        opened.append((name, tuple(command)))
        return '@42'

    monkeypatch.setattr(app.tmux, 'new_window', new_window)
    monkeypatch.setattr(app, 'jump_to_target', jumped.append)

    async def scenario(pilot: Pilot[int]) -> None:
        app.run_palette_entry(
            PaletteEntry(
                '',
                '',
                'run',
                'logs-api',
                ('aws', 'logs', 'tail', '/x'),
            ),
        )
        await pilot.pause()
        assert opened == [('logs-api', ('aws', 'logs', 'tail', '/x'))]
        assert jumped == ['@42']

    run_with_pilot(app, scenario)


def test_remote_agent_clones_first_then_opens_form(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_app(tmp_path, [])
    commands: list[list[str]] = []

    def fake_run(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        Path(command[-1]).mkdir()
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr('fleet.tui.run_captured', fake_run)

    async def scenario(pilot: Pilot[int]) -> None:
        app.run_palette_entry(
            PaletteEntry('', '', 'new-agent-remote', 'acme/api'),
        )
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert commands == [
            ['gh', 'repo', 'clone', 'acme/api', str(tmp_path / 'api')],
        ]
        repo = await modal_field(pilot, '#repo', Input)
        assert type(app.screen).__name__ == 'NewAgentScreen'
        assert repo.value == str(
            tmp_path / 'api',
        )

    run_with_pilot(app, scenario)


def test_deep_review_without_local_clone_clones_then_spawns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It used to stop at 'no local clone'; now it clones first."""
    app = make_app(tmp_path, [])
    cloned: list[list[str]] = []
    spawned: list[tuple[str, Path]] = []

    def fake_clone(command: list[str]) -> subprocess.CompletedProcess[str]:
        cloned.append(command)
        Path(command[-1]).mkdir()
        return subprocess.CompletedProcess(command, 0, '', '')

    def fake_spawn(
        _kind: str,
        name: str,
        repo_dir: Path,
        _base: str,
        _prompt: str,
    ) -> None:
        spawned.append((name, repo_dir))

    monkeypatch.setattr('fleet.tui.run_captured', fake_clone)
    monkeypatch.setattr(app, 'spawn', fake_spawn)

    async def scenario(pilot: Pilot[int]) -> None:
        app.action_deep_review('https://github.com/acme/api/pull/7')
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert cloned == [
            ['gh', 'repo', 'clone', 'acme/api', str(tmp_path / 'api')],
        ]
        assert spawned == [('review-api-7', tmp_path / 'api')]

    run_with_pilot(app, scenario)


def test_remote_agent_refuses_to_clone_over_existing_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / 'api').mkdir()
    app = make_app(tmp_path, [])

    def no_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError

    monkeypatch.setattr('fleet.tui.run_captured', no_run)

    async def scenario(pilot: Pilot[int]) -> None:
        app.run_palette_entry(
            PaletteEntry('', '', 'new-agent-remote', 'acme/api'),
        )
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert type(app.screen).__name__ == 'Screen'

    run_with_pilot(app, scenario)


def test_review_markdown_keeps_header_lines_apart() -> None:
    text = (
        'RISK: high\nSUMMARY: rewrites billing\n\n'
        '## Blast radius\nall users\nand admins'
    )
    rendered = review_markdown(text)
    assert rendered.startswith(
        '**Risk:** high  \n**Summary:** rewrites billing',
    )
    assert rendered.endswith('## Blast radius\nall users\nand admins')


def test_review_markdown_leaves_unexpected_shapes_alone() -> None:
    assert review_markdown('just prose') == 'just prose'


@pytest.mark.parametrize(
    ('seconds', 'expected'),
    [(5, '5s'), (125, '2m'), (7200, '2h'), (200_000, '2d')],
)
def test_relative_age(seconds: float, expected: str) -> None:
    assert relative_age(seconds) == expected


def test_clone_never_prompts_on_the_dashboard_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs)
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr('fleet.tui.subprocess.run', fake_run)
    run_captured(['gh', 'repo', 'clone', 'acme/api', 'dest'])
    assert seen['stdin'] == subprocess.DEVNULL
    assert seen['timeout']
    env = seen['env']
    assert isinstance(env, dict)
    assert env['GIT_TERMINAL_PROMPT'] == '0'
    assert 'BatchMode=yes' in env['GIT_SSH_COMMAND']


def test_clone_timeout_is_reported_not_raised(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_app(tmp_path, [])

    def hang(command: list[str]) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr('fleet.tui.run_captured', hang)

    async def scenario(pilot: Pilot[int]) -> None:
        app.run_palette_entry(
            PaletteEntry('', '', 'new-agent-remote', 'acme/api'),
        )
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert any('timed out' in n.message for n in app._notifications)  # noqa: SLF001

    run_with_pilot(app, scenario)


def test_broken_browser_is_a_notification_not_a_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_app(tmp_path, [])

    def no_browser(_url: str) -> None:
        msg = 'xdg-open'
        raise FileNotFoundError(msg)

    monkeypatch.setattr('fleet.tui.open_url', no_browser)

    async def scenario(pilot: Pilot[int]) -> None:
        app.run_palette_entry(
            PaletteEntry('', '', 'open-url', 'https://example.test'),
        )
        await pilot.pause()
        assert app.is_running
        assert any(
            'could not open' in n.message
            for n in app._notifications  # noqa: SLF001
        )

    run_with_pilot(app, scenario)
