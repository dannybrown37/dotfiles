"""The fleet dashboard: agents, review radar and a Ctrl+P action palette."""

import asyncio
import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from fleet import radar
from fleet.agents import AGENT_KINDS, AgentState
from fleet.ops import (
    HOOK_PATH,
    DashboardRow,
    SpawnRequest,
    agent_binary,
    dashboard_rows,
    default_agent_kind,
    default_store,
    default_tmux,
    fleet_session,
    kill_agent,
    review_agent_kind,
    spawn_agent,
)
from fleet.palette import (
    PaletteEntry,
    RankedReview,
    by_urgency,
    find_local_clone,
    find_repos,
    palette_entries,
    parse_pr_url,
    pr_from_text,
    review_agent_name,
)
from fleet.procs import AgentProcess, scan_agent_processes
from fleet.store import Store, default_state_dir
from fleet.tmux import Tmux
from fleet.worktree import DiffStat, diff_stat, git, is_dirty

AGENT_REFRESH_SECONDS = 2.0
PREVIEW_REFRESH_SECONDS = 1.0
SLOW_REFRESH_SECONDS = 30.0
RADAR_REFRESH_SECONDS = 300.0
HIGH_SCORE = 60
NEEDS_YOU = frozenset(
    {AgentState.WAITING, AgentState.IDLE, AgentState.ERROR, AgentState.EXITED},
)
STATE_STYLE = {
    AgentState.WAITING: ('● waiting', 'bold black on yellow'),
    AgentState.IDLE: ('✓ your turn', 'bold green'),
    AgentState.WORKING: ('⟳ working', 'cyan'),
    AgentState.ERROR: ('✗ error', 'bold red'),
    AgentState.EXITED: ('■ exited', 'dim'),
    AgentState.GONE: ('? gone', 'dim red'),
    AgentState.UNKNOWN: ('… starting', 'dim'),
}
CHECKS_STYLE = {
    radar.ChecksState.PASSING: ('✓', 'green'),
    radar.ChecksState.FAILING: ('✗', 'bold red'),
    radar.ChecksState.PENDING: ('⟳', 'yellow'),
    radar.ChecksState.NONE: ('·', 'dim'),
}
DEEP_REVIEW_PROMPT = """\
Review pull request {url} locally. Check it out with `gh pr checkout {number}`,
read the code around every change, and run the relevant tests.
Do not push, comment, approve or post anything to GitHub: report your
findings here, most important first, with file:line references.
"""


@dataclass(frozen=True)
class AgentPr:
    number: int
    url: str
    checks: radar.ChecksState


def relative_age(seconds: float) -> str:
    if seconds < 60:  # noqa: PLR2004
        return f'{int(seconds)}s'
    if seconds < 3600:  # noqa: PLR2004
        return f'{int(seconds // 60)}m'
    if seconds < 86400:  # noqa: PLR2004
        return f'{int(seconds // 3600)}h'
    return f'{int(seconds // 86400)}d'


def format_diff(stat: DiffStat | None) -> Text:
    if stat is None:
        return Text('-', style='dim')
    text = Text()
    text.append(f'+{stat.added}', style='green')
    text.append(f' -{stat.removed}', style='red')
    extras = []
    if stat.commits:
        extras.append(f'{stat.commits}c')
    if stat.untracked:
        extras.append(f'{stat.untracked}new')
    if extras:
        text.append(' ' + ' '.join(extras), style='dim')
    return text


def open_in_browser(pr_url: str) -> None:
    subprocess.run(  # noqa: S603
        ['gh', 'pr', 'view', pr_url, '--web'],  # noqa: S607
        capture_output=True,
        check=False,
    )


def review_markdown(text: str) -> str:
    """Markdown joins the RISK/SUMMARY lines into one paragraph; split them."""
    header, separator, body = text.partition('\n\n')
    lines = []
    for line in header.splitlines():
        label, colon, value = line.partition(':')
        if colon and label.strip().lower() in {'risk', 'summary'}:
            lines.append(f'**{label.strip().title()}:** {value.strip()}')
        else:
            return text
    return '  \n'.join(lines) + separator + body


def agent_pr(worktree: Path) -> AgentPr | None:
    result = subprocess.run(
        ['gh', 'pr', 'view', '--json', 'number,url,statusCheckRollup'],  # noqa: S607
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    data = json.loads(result.stdout)
    return AgentPr(
        number=int(data['number']),
        url=str(data['url']),
        checks=radar.checks_state(data.get('statusCheckRollup') or []),
    )


def read_clipboard() -> str:
    """win32yank only: the PowerShell fallback costs a second per read."""
    if shutil.which('win32yank.exe') is None:
        return ''
    try:
        result = subprocess.run(
            ['win32yank.exe', '-o', '--lf'],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ''
    return result.stdout


def projects_dir() -> Path:
    return Path(os.environ.get('FLEET_PROJECTS_DIR', Path.home() / 'projects'))


class FleetCommands(Provider):
    entries: list[PaletteEntry]

    async def startup(self) -> None:
        app = self.app
        assert isinstance(app, FleetApp)
        clipboard = await asyncio.to_thread(read_clipboard)
        repos = await asyncio.to_thread(find_repos, app.projects_dir)
        self.entries = palette_entries(
            app.rows,
            app.ranked,
            repos,
            pr_from_text(clipboard),
        )

    def callback(self, entry: PaletteEntry) -> Callable[[], None]:
        app = self.app
        assert isinstance(app, FleetApp)
        return partial(app.run_palette_entry, entry)

    async def discover(self) -> Hits:
        for entry in self.entries:
            yield DiscoveryHit(
                entry.label,
                self.callback(entry),
                help=entry.help,
            )

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for entry in self.entries:
            score = matcher.match(entry.label)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(entry.label),
                    self.callback(entry),
                    help=entry.help,
                )


@dataclass(frozen=True)
class NewAgentForm:
    name: str
    kind: str
    repo_dir: str
    base: str
    prompt: str


class NewAgentScreen(ModalScreen[NewAgentForm | None]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding('escape', 'cancel', 'Cancel'),
        Binding('ctrl+s', 'submit', 'Start'),
    ]

    def __init__(self, repo_dir: str, kind: str) -> None:
        super().__init__()
        self.repo_dir = repo_dir
        self.kind = kind

    def compose(self) -> ComposeResult:
        with Vertical(id='dialog'):
            yield Label('New agent  [dim](ctrl+s start · esc cancel)[/]')
            yield Input(placeholder='name (also the branch)', id='name')
            yield Select(
                [(kind, kind) for kind in AGENT_KINDS],
                value=self.kind,
                allow_blank=False,
                id='kind',
            )
            yield Input(value=self.repo_dir, placeholder='repo dir', id='repo')
            yield Input(
                placeholder='base ref (blank = current branch)',
                id='base',
            )
            yield TextArea(id='prompt')

    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Input.Submitted)
    def action_submit(self) -> None:
        name = self.query_one('#name', Input).value.strip()
        if not name:
            self.notify('name is required', severity='error')
            return
        self.dismiss(
            NewAgentForm(
                name=name,
                kind=str(self.query_one('#kind', Select).value),
                repo_dir=self.query_one('#repo', Input).value.strip() or '.',
                base=self.query_one('#base', Input).value.strip(),
                prompt=self.query_one('#prompt', TextArea).text.strip(),
            ),
        )


class SendScreen(ModalScreen[str | None]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding('escape', 'cancel', 'Cancel'),
        Binding('ctrl+s', 'submit', 'Send'),
    ]

    def __init__(self, name: str) -> None:
        super().__init__()
        self.agent_name = name

    def compose(self) -> ComposeResult:
        with Vertical(id='dialog'):
            yield Label(
                f'Message to {self.agent_name}  '
                '[dim](ctrl+s send · esc cancel)[/]',
            )
            yield TextArea(id='message')

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_submit(self) -> None:
        self.dismiss(self.query_one('#message', TextArea).text.strip() or None)


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding('y', 'answer(True)', 'Yes'),
        Binding('n,escape', 'answer(False)', 'No'),
    ]

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(id='dialog'):
            yield Label(self.question)
            with Horizontal():
                yield Button('Yes (y)', id='yes', variant='error')
                yield Button('No (n)', id='no')

    @on(Button.Pressed)
    def pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == 'yes')

    def action_answer(self, answer: bool) -> None:  # noqa: FBT001
        self.dismiss(answer)


class FleetApp(App[int]):
    TITLE = 'fleet'
    # Fleet's actions only: Textual's built-ins crowd them out.
    COMMANDS: ClassVar = {FleetCommands}
    CSS = """
    #agents-table, #reviews-table { height: 1fr; }
    #preview, #review-preview { height: 2fr; border-top: solid $accent; }
    #preview { overflow-y: auto; }
    #dialog {
        width: 80%; height: auto; max-height: 90%;
        padding: 1 2; border: thick $accent; background: $surface;
    }
    #dialog TextArea { height: 8; }
    ModalScreen { align: center middle; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding('1', 'tab("agents")', 'Agents', show=False),
        Binding('2', 'tab("reviews")', 'Reviews', show=False),
        Binding('n', 'new', 'New'),
        Binding('s', 'send', 'Send'),
        Binding('d', 'diff', 'Diff'),
        Binding('g', 'lazygit', 'Lazygit'),
        Binding('o', 'browser', 'Browser'),
        Binding('x', 'stop', 'Stop'),
        Binding('X', 'stop_and_remove', 'Stop+rm'),
        Binding('r', 'review', 'Pre-review'),
        Binding('R', 'review_all', 'Review all'),
        Binding('a', 'deep_review', 'Agent review'),
        Binding('ctrl+r', 'refresh', 'Refresh', show=False),
        Binding('q', 'quit', 'Quit'),
    ]
    AGENT_ACTIONS = frozenset(
        {'send', 'diff', 'lazygit', 'stop', 'stop_and_remove'},
    )
    REVIEW_ACTIONS = frozenset({'review', 'review_all', 'deep_review'})

    def __init__(
        self,
        store: Store,
        tmux: Tmux,
        fetch_prs: Callable[
            [],
            list[radar.PullRequest],
        ] = radar.fetch_review_requests,
        projects: Path | None = None,
        scan_processes: Callable[
            [],
            list[AgentProcess],
        ] = scan_agent_processes,
    ) -> None:
        super().__init__()
        self.store = store
        self.tmux = tmux
        self.fetch_prs = fetch_prs
        self.scan_processes = scan_processes
        self.projects_dir = projects or projects_dir()
        self.review_cache = radar.ReviewCache(default_state_dir() / 'reviews')
        self.rows: list[DashboardRow] = []
        self.diffstats: dict[str, DiffStat | None] = {}
        self.agent_prs: dict[str, AgentPr | None] = {}
        self.prs: list[radar.PullRequest] = []
        self.ranked: list[RankedReview] = []
        self.reviewing: set[str] = set()
        self.last_states: dict[str, AgentState] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id='tabs'):
            with TabPane('Agents', id='agents'):
                yield DataTable(
                    id='agents-table',
                    cursor_type='row',
                    zebra_stripes=True,
                )
                yield Static(id='preview')
            with TabPane('Reviews', id='reviews'):
                yield DataTable(
                    id='reviews-table',
                    cursor_type='row',
                    zebra_stripes=True,
                )
                yield Markdown(id='review-preview')
        yield Footer()

    def on_mount(self) -> None:
        agents = self.query_one('#agents-table', DataTable)
        agents.add_columns(
            'State',
            'Agent',
            'Name',
            'Where',
            'Changes',
            'PR',
            'Age',
            'Note',
        )
        reviews = self.query_one('#reviews-table', DataTable)
        reviews.add_columns('Score', '', 'PR', 'Title', 'Why')
        self.refresh_agents()
        self.refresh_slow()
        self.refresh_radar()
        self.set_interval(AGENT_REFRESH_SECONDS, self.refresh_agents)
        self.set_interval(PREVIEW_REFRESH_SECONDS, self.refresh_preview)
        self.set_interval(SLOW_REFRESH_SECONDS, self.refresh_slow)
        self.set_interval(RADAR_REFRESH_SECONDS, self.refresh_radar)

    # ---- which actions apply where --------------------------------------

    def active_tab(self) -> str:
        return self.query_one('#tabs', TabbedContent).active

    def check_action(
        self,
        action: str,
        parameters: tuple[object, ...],  # noqa: ARG002
    ) -> bool | None:
        if action in self.AGENT_ACTIONS:
            return self.active_tab() == 'agents'
        if action in self.REVIEW_ACTIONS:
            return self.active_tab() == 'reviews'
        return True

    @on(TabbedContent.TabActivated)
    def tab_changed(self) -> None:
        self.refresh_bindings()

    def action_tab(self, tab: str) -> None:
        self.query_one('#tabs', TabbedContent).active = tab

    # ---- agents ----------------------------------------------------------

    def find_row(self, key: str) -> DashboardRow | None:
        return next((row for row in self.rows if row.key == key), None)

    def selected_row(self) -> DashboardRow | None:
        table = self.query_one('#agents-table', DataTable)
        if table.row_count == 0 or table.cursor_row < 0:
            return None
        key = table.coordinate_to_cell_key(
            table.cursor_coordinate,
        ).row_key.value
        return self.find_row(str(key))

    def pick_row(self, key: str = '') -> DashboardRow | None:
        row = self.find_row(key) if key else self.selected_row()
        if row is None:
            self.notify(
                'no agent selected; press n to start one',
                severity='warning',
            )
        return row

    def note_for(self, row: DashboardRow) -> str:
        if row.state is AgentState.WAITING and not row.message and row.record:
            return 'no hook yet: answer its startup dialog (enter jumps in)'
        if row.state is AgentState.UNKNOWN and row.record is None:
            return 'no state yet (hooks off? fleet hooks install)'
        return row.message

    def refresh_agents(self) -> None:
        selected = self.selected_row()
        self.rows = by_urgency(
            dashboard_rows(self.store, self.tmux, self.scan_processes()),
        )
        self.announce_state_changes()
        table = self.query_one('#agents-table', DataTable)
        table.clear()
        now = time.time()
        for row in self.rows:
            label, style = STATE_STYLE[row.state]
            if row.state is AgentState.UNKNOWN and row.record is None:
                label, style = '· no data', 'dim'
            pr = self.agent_prs.get(row.key)
            pr_cell = Text('-', style='dim')
            if pr:
                mark, mark_style = CHECKS_STYLE[pr.checks]
                pr_cell = Text(f'#{pr.number} ') + Text(mark, style=mark_style)
            table.add_row(
                Text(label, style=style),
                row.kind,
                Text(row.name, style='bold' if row.record else ''),
                Text(row.where, style='dim' if not row.target else ''),
                format_diff(self.diffstats.get(row.key)),
                pr_cell,
                relative_age(now - row.started_at),
                self.note_for(row).replace('\n', ' ')[:70],
                key=row.key,
            )
        if selected:
            keys = [row.key for row in self.rows]
            if selected.key in keys:
                table.move_cursor(row=keys.index(selected.key))
        tabs = self.query_one('#tabs', TabbedContent)
        needs_you = sum(row.state in NEEDS_YOU for row in self.rows)
        tabs.get_tab('agents').label = f'Agents ({needs_you}/{len(self.rows)})'

    def announce_state_changes(self) -> None:
        for row in self.rows:
            before = self.last_states.get(row.key)
            if before is AgentState.WORKING and row.state in NEEDS_YOU:
                label, _ = STATE_STYLE[row.state]
                self.notify(
                    f'{row.name} ({row.where}): {label}',
                    title='agent needs you',
                )
                self.bell()
        self.last_states = {row.key: row.state for row in self.rows}

    def refresh_preview(self) -> None:
        if self.active_tab() != 'agents':
            return
        row = self.selected_row()
        preview = self.query_one('#preview', Static)
        if row is None:
            preview.update(
                Text(
                    'No agents. Press n (or ctrl+p) to start one.',
                    style='dim',
                ),
            )
        elif not row.target:
            preview.update(
                Text(
                    f'{row.where} session in {row.cwd}: no tmux pane to show.',
                    style='dim',
                ),
            )
        else:
            self.capture_preview(row.target, preview.size.height)

    @work(thread=True, exclusive=True, group='preview')
    def capture_preview(self, target: str, height: int) -> None:
        """Only as many lines as fit, so the newest output is what shows."""
        captured = self.tmux.capture(target, lines=max(height, 1))
        captured = '\n'.join(
            captured.rstrip('\n').splitlines()[-max(height, 1) :],
        )
        self.call_from_thread(
            self.query_one('#preview', Static).update,
            Text.from_ansi(captured),
        )

    @work(thread=True, exclusive=True, group='slow')
    def refresh_slow(self) -> None:
        for row in list(self.rows):
            self.diffstats[row.key] = diff_stat(row.cwd, row.diff_base)
            if row.cwd.is_dir():
                self.agent_prs[row.key] = agent_pr(row.cwd)

    @on(DataTable.RowSelected, '#agents-table')
    def jump_to_selected(self) -> None:
        row = self.pick_row()
        if row:
            self.jump(row)

    def jump(self, row: DashboardRow) -> None:
        if not row.target:
            self.notify(
                f'{row.name} ({row.where}) has no tmux pane to jump to',
                severity='warning',
            )
            return
        command = self.tmux.jump_command(row.target)
        if 'switch-client' in command:
            subprocess.run(command, check=False)  # noqa: S603
            return
        with self.suspend():
            subprocess.run(command, check=False)  # noqa: S603

    def action_new(self, repo_dir: str = '') -> None:
        default_repo = repo_dir or str(Path.cwd())
        self.push_screen(
            NewAgentScreen(default_repo, default_agent_kind()),
            self.spawn_from_form,
        )

    def spawn_from_form(self, form: NewAgentForm | None) -> None:
        if form:
            self.spawn(
                form.kind,
                form.name,
                Path(form.repo_dir).expanduser(),
                form.base,
                form.prompt,
            )

    @work(thread=True)
    def spawn(
        self,
        kind: str,
        name: str,
        repo_dir: Path,
        base: str,
        prompt: str,
    ) -> None:
        request = SpawnRequest(
            kind=kind,
            name=name,
            repo_dir=repo_dir,
            base=base,
            prompt=prompt,
            extra_args=[],
            binary=agent_binary(kind),
            hook_path=str(HOOK_PATH),
            session=fleet_session(),
            auto_trust=True,
        )
        try:
            record = spawn_agent(self.store, self.tmux, request)
        except (
            ValueError,
            FileExistsError,
            subprocess.CalledProcessError,
        ) as error:
            detail = getattr(error, 'stderr', '') or error
            self.call_from_thread(
                self.notify,
                f'could not start {name}: {detail}',
                severity='error',
            )
            return
        self.call_from_thread(
            self.notify,
            f'started {record.kind} agent {record.name}',
        )
        self.call_from_thread(self.refresh_agents)

    def action_send(self, key: str = '') -> None:
        row = self.pick_row(key)
        if row is None:
            return
        if not row.target:
            self.notify(
                f'{row.name} has no tmux pane to type into',
                severity='warning',
            )
            return

        def send(text: str | None) -> None:
            if text:
                self.tmux.send_text(row.target, text)
                self.notify(f'sent to {row.name}')

        self.push_screen(SendScreen(row.name), send)

    def action_diff(self, key: str = '') -> None:
        row = self.pick_row(key)
        if row is None:
            return
        try:
            merge_base = git(
                row.cwd,
                'merge-base',
                row.diff_base,
                'HEAD',
            ).strip()
        except (subprocess.CalledProcessError, OSError):
            self.notify(
                f'cannot diff {row.name}: {row.cwd} is not a git checkout',
                severity='error',
            )
            return
        diff_command = ['git', '-C', str(row.cwd), 'diff', merge_base]
        with self.suspend():
            subprocess.run(diff_command, check=False)  # noqa: S603

    def action_lazygit(self) -> None:
        row = self.pick_row()
        if row is None or shutil.which('lazygit') is None:
            return
        with self.suspend():
            subprocess.run(['lazygit', '-p', str(row.cwd)], check=False)  # noqa: S603, S607

    def action_browser(self) -> None:
        if self.active_tab() == 'reviews':
            review = self.selected_review()
            url = review.pr.url if review else ''
        else:
            row = self.selected_row()
            pr = self.agent_prs.get(row.key) if row else None
            url = pr.url if pr else ''
        if not url:
            self.notify('no PR here yet', severity='warning')
            return
        open_in_browser(url)

    def action_stop(self, key: str = '') -> None:
        self.confirm_stop(key, remove_checkout=False)

    def action_stop_and_remove(self) -> None:
        self.confirm_stop('', remove_checkout=True)

    def confirm_stop(self, key: str, *, remove_checkout: bool) -> None:
        row = self.pick_row(key)
        if row is None:
            return
        record = row.record
        if record is None:
            self.notify(
                'fleet only stops agents it started; jump in and quit there',
                severity='warning',
            )
            return
        question = f'Stop {record.name}? Branch {record.branch} is kept.'
        force = False
        if remove_checkout:
            dirty = Path(record.worktree).is_dir() and is_dirty(
                Path(record.worktree),
            )
            question = f'Stop {record.name} and delete {record.worktree}?'
            if dirty:
                question += '\n[bold red]UNCOMMITTED changes will be lost.[/]'
                force = True

        def answer(yes: bool | None) -> None:  # noqa: FBT001  Textual callback
            if not yes:
                return
            try:
                kill_agent(
                    self.store,
                    self.tmux,
                    record,
                    remove_checkout=remove_checkout,
                    force=force,
                )
            except (ValueError, subprocess.CalledProcessError) as error:
                self.notify(
                    str(getattr(error, 'stderr', '') or error),
                    severity='error',
                )
                return
            self.notify(f'stopped {record.name}')
            self.refresh_agents()

        self.push_screen(ConfirmScreen(question), answer)

    # ---- reviews ---------------------------------------------------------

    def selected_review(self) -> RankedReview | None:
        table = self.query_one('#reviews-table', DataTable)
        if table.row_count == 0 or table.cursor_row < 0:
            return None
        key = table.coordinate_to_cell_key(
            table.cursor_coordinate,
        ).row_key.value
        return next((r for r in self.ranked if r.pr.url == key), None)

    @work(thread=True, exclusive=True, group='radar')
    def refresh_radar(self) -> None:
        try:
            prs = self.fetch_prs()
        except (subprocess.CalledProcessError, ValueError, OSError) as error:
            self.call_from_thread(
                self.notify,
                f'radar: {error}',
                severity='error',
            )
            return
        self.prs = prs
        self.call_from_thread(self.rerank)

    def rerank(self) -> None:
        now = datetime.now(UTC)
        ranked = []
        for pr in self.prs:
            review = self.review_cache.get(pr)
            score = radar.score_pull_request(
                pr,
                now,
                review.risk if review else '',
            )
            ranked.append(RankedReview(pr=pr, score=score, review=review))
        self.ranked = sorted(ranked, key=lambda r: r.score.score, reverse=True)
        table = self.query_one('#reviews-table', DataTable)
        selected = self.selected_review()
        table.clear()
        for row in self.ranked:
            reviewing = row.pr.url in self.reviewing
            why = ', '.join(row.score.reasons)
            if reviewing:
                why = '⟳ reviewing… ' + why
            elif row.review:
                why = f'{row.review.summary}  [{why}]'
            table.add_row(
                Text(
                    str(row.score.score),
                    style='bold' if row.score.score >= HIGH_SCORE else '',
                ),
                '⚡' if row.score.quick else '',
                f'{row.pr.repo}#{row.pr.number}',
                row.pr.title[:60],
                why[:120],
                key=row.pr.url,
            )
        if selected:
            urls = [r.pr.url for r in self.ranked]
            if selected.pr.url in urls:
                table.move_cursor(row=urls.index(selected.pr.url))
        tabs = self.query_one('#tabs', TabbedContent)
        tabs.get_tab('reviews').label = f'Reviews ({len(self.ranked)})'
        self.show_review_preview()

    @on(DataTable.RowHighlighted, '#reviews-table')
    def show_review_preview(self) -> None:
        row = self.selected_review()
        preview = self.query_one('#review-preview', Markdown)
        if row is None:
            preview.update('_No open review requests._')
        elif row.review:
            preview.update(
                f'**{row.pr.title}** · {row.pr.author} · '
                f'{row.review.agent}\n\n' + review_markdown(row.review.text),
            )
        else:
            preview.update(
                f'**{row.pr.title}** · {row.pr.author}\n\n'
                f'Why: {", ".join(row.score.reasons) or "-"}\n\n'
                '_No pre-review yet. Press **r** to run one locally '
                '(nothing is posted)._',
            )

    @on(DataTable.RowSelected, '#reviews-table')
    def open_selected_review(self) -> None:
        self.action_browser()

    def review_kind(self) -> str:
        return review_agent_kind(None)

    def action_review(self) -> None:
        row = self.selected_review()
        if row:
            self.run_reviews([row.pr])

    def action_review_all(self) -> None:
        self.run_reviews(
            [pr for pr in self.prs if self.review_cache.get(pr) is None],
        )

    @work(thread=True, group='reviews')
    def run_reviews(self, prs: list[radar.PullRequest]) -> None:
        kind = self.review_kind()
        for pr in prs:
            if pr.url in self.reviewing:
                continue
            self.reviewing.add(pr.url)
            self.call_from_thread(self.rerank)
            try:
                review = radar.run_review(
                    pr,
                    kind,
                    agent_binary(kind),
                    os.environ.get('FLEET_REVIEW_MODEL', ''),
                )
            except (
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
                OSError,
            ) as error:
                self.call_from_thread(
                    self.notify,
                    f'review of {pr.repo}#{pr.number} failed: {error}',
                    severity='error',
                )
            else:
                self.review_cache.put(pr, review)
                self.call_from_thread(
                    self.notify,
                    f'{pr.repo}#{pr.number}: {review.risk or "?"} risk',
                )
            finally:
                self.reviewing.discard(pr.url)
            self.call_from_thread(self.rerank)

    def action_deep_review(self, url: str = '') -> None:
        if not url:
            row = self.selected_review()
            url = row.pr.url if row else ''
        if not url:
            return
        owner, repo, number = parse_pr_url(url)
        clone = find_local_clone(
            find_repos(self.projects_dir),
            f'{owner}/{repo}',
        )
        if clone is None:
            self.notify(
                f'no local clone of {owner}/{repo} in {self.projects_dir}',
                severity='error',
            )
            return
        prompt = DEEP_REVIEW_PROMPT.format(url=url, number=number)
        self.spawn(
            self.review_kind(),
            review_agent_name(url),
            clone,
            '',
            prompt,
        )

    # ---- palette ---------------------------------------------------------

    def run_palette_entry(self, entry: PaletteEntry) -> None:
        handlers: dict[str, Callable[[], None]] = {
            'jump': lambda: self.jump_to_key(entry.target),
            'send': lambda: self.action_send(entry.target),
            'diff': lambda: self.action_diff(entry.target),
            'stop': lambda: self.action_stop(entry.target),
            'open-review': lambda: self.focus_review(entry.target),
            'deep-review': lambda: self.action_deep_review(entry.target),
            'browser': lambda: open_in_browser(entry.target),
            'new': self.action_new,
            'new-agent': lambda: self.action_new(entry.target),
            'refresh': self.action_refresh,
            'review-all': self.action_review_all,
        }
        handlers[entry.action]()

    def jump_to_key(self, key: str) -> None:
        row = self.pick_row(key)
        if row:
            self.jump(row)

    def focus_review(self, url: str) -> None:
        self.action_tab('reviews')
        urls = [r.pr.url for r in self.ranked]
        if url in urls:
            self.query_one('#reviews-table', DataTable).move_cursor(
                row=urls.index(url),
            )

    def action_refresh(self) -> None:
        self.refresh_agents()
        self.refresh_slow()
        self.refresh_radar()


def run_dashboard() -> int:
    FleetApp(default_store(), default_tmux()).run()
    return 0
