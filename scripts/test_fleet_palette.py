"""Tests for fleet.palette: what the Ctrl+P palette offers."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from fleet.agents import AgentState
from fleet.ops import DashboardRow
from fleet.palette import (
    PaletteEntry,
    RankedReview,
    find_local_clone,
    find_repos,
    palette_entries,
    parse_pr_url,
    pr_from_text,
    review_agent_name,
)
from fleet.radar import ChecksState, PullRequest, Score
from fleet.store import AgentRecord


def make_view(
    name: str,
    state: AgentState,
    *,
    managed: bool = True,
    target: str = '@1',
) -> DashboardRow:
    record = AgentRecord(
        name=name,
        kind='claude',
        repo='/r',
        worktree=f'/w/{name}',
        branch=name,
        base='main',
        prompt='',
        created_at=1.0,
        window_id='@1',
    )
    return DashboardRow(
        key=f'agent:{name}' if managed else f'pid:{name}',
        kind='claude',
        name=name,
        state=state,
        message='',
        cwd=Path(f'/w/{name}'),
        diff_base='main',
        target=target,
        started_at=1.0,
        where='fleet' if managed else 'tmux main:1',
        record=record if managed else None,
    )


def make_ranked(number: int, score: int) -> RankedReview:
    pr = PullRequest(
        repo='acme/api',
        number=number,
        title=f'PR {number}',
        author='sam',
        is_bot=False,
        url=f'https://github.com/acme/api/pull/{number}',
        is_draft=False,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        additions=1,
        deletions=1,
        files=(),
        head_sha='abc',
        checks=ChecksState.PASSING,
    )
    return RankedReview(
        pr=pr,
        score=Score(score=score, quick=False),
        review=None,
    )


def write_repo(path: Path, url: str) -> Path:
    (path / '.git').mkdir(parents=True)
    (path / '.git' / 'config').write_text(
        f'[core]\n\tbare = false\n[remote "origin"]\n\turl = {url}\n',
    )
    return path


def actions(entries: list[PaletteEntry]) -> list[tuple[str, str]]:
    return [(e.action, e.target) for e in entries]


def test_waiting_agents_come_before_working_ones() -> None:
    entries = palette_entries(
        [
            make_view('busy', AgentState.WORKING),
            make_view('blocked', AgentState.WAITING),
        ],
        [],
        [],
        None,
    )
    jumps = [e.target for e in entries if e.action == 'jump']
    assert jumps == ['agent:blocked', 'agent:busy']


def test_each_agent_gets_jump_send_diff_stop() -> None:
    entries = palette_entries([make_view('a', AgentState.IDLE)], [], [], None)
    expected = {
        ('jump', 'agent:a'),
        ('send', 'agent:a'),
        ('diff', 'agent:a'),
        ('stop', 'agent:a'),
    }
    assert expected <= set(actions(entries))


def test_discovered_session_cannot_be_stopped() -> None:
    entries = palette_entries(
        [make_view('9', AgentState.IDLE, managed=False)],
        [],
        [],
        None,
    )
    assert {e.action for e in entries if e.target == 'pid:9'} == {
        'jump',
        'send',
        'diff',
    }


def test_session_without_pane_offers_only_diff() -> None:
    row = make_view('9', AgentState.IDLE, managed=False, target='')
    entries = palette_entries([row], [], [], None)
    assert {e.action for e in entries if e.target == 'pid:9'} == {'diff'}


def test_reviews_ranked_by_score() -> None:
    entries = palette_entries(
        [],
        [make_ranked(1, 10), make_ranked(2, 90)],
        [],
        None,
    )
    opened = [e.target for e in entries if e.action == 'open-review']
    assert opened == [
        'https://github.com/acme/api/pull/2',
        'https://github.com/acme/api/pull/1',
    ]


def test_repo_entries_offer_new_agent(tmp_path: Path) -> None:
    entries = palette_entries([], [], [tmp_path / 'proj'], None)
    assert ('new-agent', str(tmp_path / 'proj')) in actions(entries)


def test_clipboard_pr_goes_first() -> None:
    entries = palette_entries(
        [make_view('a', AgentState.WAITING)],
        [],
        [],
        'https://github.com/acme/web/pull/12',
    )
    assert entries[0].action == 'deep-review'
    assert entries[0].target == 'https://github.com/acme/web/pull/12'
    assert 'clipboard' in entries[0].label


def test_global_actions_always_present() -> None:
    entries = palette_entries([], [], [], None)
    assert {'new', 'refresh', 'review-all'} <= {e.action for e in entries}


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        (
            'https://github.com/acme/api/pull/7',
            'https://github.com/acme/api/pull/7',
        ),
        (
            '  see https://github.com/acme/api/pull/7/files#diff-1 pls',
            'https://github.com/acme/api/pull/7',
        ),
        ('https://github.com/acme/api/issues/7', None),
        ('nothing here', None),
        ('', None),
    ],
)
def test_pr_from_text(text: str, expected: str | None) -> None:
    assert pr_from_text(text) == expected


@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        ('https://github.com/acme/api/pull/7', ('acme', 'api', 7)),
        ('https://github.com/a-b/c.d/pull/123', ('a-b', 'c.d', 123)),
    ],
)
def test_parse_pr_url(url: str, expected: tuple[str, str, int]) -> None:
    assert parse_pr_url(url) == expected


def test_parse_pr_url_rejects_non_pr() -> None:
    with pytest.raises(ValueError, match='not a GitHub PR URL'):
        parse_pr_url('https://github.com/acme/api/issues/7')


@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        ('https://github.com/acme/api/pull/7', 'review-api-7'),
        ('https://github.com/acme/my.site/pull/12', 'review-my-site-12'),
    ],
)
def test_review_agent_name(url: str, expected: str) -> None:
    assert review_agent_name(url) == expected


def test_find_repos_skips_worktree_dirs_and_non_repos(tmp_path: Path) -> None:
    write_repo(tmp_path / 'api', 'git@github.com:acme/api.git')
    (tmp_path / 'api-worktrees' / 'fix-x').mkdir(parents=True)
    (tmp_path / 'api-worktrees' / 'fix-x' / '.git').write_text('gitdir: x')
    (tmp_path / 'notes').mkdir()
    assert find_repos(tmp_path) == [tmp_path / 'api']


def test_find_repos_missing_dir_is_empty(tmp_path: Path) -> None:
    assert find_repos(tmp_path / 'nope') == []


@pytest.mark.parametrize(
    'url',
    [
        'git@github.com:acme/api.git',
        'https://github.com/acme/api.git',
        'https://github.com/acme/api',
        'git@github.com-work:acme/api.git',
    ],
)
def test_find_local_clone_matches_remote_forms(
    tmp_path: Path,
    url: str,
) -> None:
    clone = write_repo(tmp_path / 'whatever', url)
    write_repo(tmp_path / 'other', 'git@github.com:acme/api-v2.git')
    assert find_local_clone([tmp_path / 'other', clone], 'acme/api') == clone


def test_find_local_clone_none_when_absent(tmp_path: Path) -> None:
    write_repo(tmp_path / 'x', 'git@github.com:acme/other.git')
    assert find_local_clone([tmp_path / 'x'], 'acme/api') is None
