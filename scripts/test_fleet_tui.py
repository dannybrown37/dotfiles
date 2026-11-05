"""Headless tests for the fleet dashboard, driven through Textual's pilot."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from textual.coordinate import Coordinate
from textual.pilot import Pilot
from textual.widgets import DataTable, Markdown

from fleet.agents import AgentState
from fleet.procs import AgentProcess
from fleet.radar import ChecksState, PullRequest, Review, ReviewCache
from fleet.store import AgentRecord, Store
from fleet.tmux import Tmux
from fleet.tui import FleetApp, relative_age, review_markdown


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
