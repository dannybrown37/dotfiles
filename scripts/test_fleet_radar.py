"""Tests for fleet.radar: ranking review requests and local pre-reviews."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fleet.radar import (
    ChecksState,
    PullRequest,
    Review,
    ReviewCache,
    checks_state,
    parse_pull_request,
    parse_review_risk,
    review_command,
    score_pull_request,
    trim_diff,
)

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


def make_pr(**overrides: object) -> PullRequest:
    fields: dict[str, object] = {
        'repo': 'acme/api',
        'number': 7,
        'title': 'Add thing',
        'author': 'sam',
        'is_bot': False,
        'url': 'https://github.com/acme/api/pull/7',
        'is_draft': False,
        'created_at': NOW - timedelta(hours=1),
        'additions': 10,
        'deletions': 2,
        'files': ('src/thing.py', 'tests/test_thing.py'),
        'head_sha': 'abc123def4567890',
        'checks': ChecksState.PASSING,
    }
    fields.update(overrides)
    return PullRequest(**fields)  # type: ignore[arg-type]


def test_parse_pull_request_merges_search_and_detail() -> None:
    search = {
        'repository': {'nameWithOwner': 'acme/api'},
        'number': 7,
        'title': 'Add thing',
        'author': {'login': 'renovate', 'is_bot': True},
        'url': 'https://github.com/acme/api/pull/7',
        'isDraft': False,
        'createdAt': '2026-11-05T11:00:00Z',
    }
    detail = {
        'additions': 3,
        'deletions': 1,
        'files': [{'path': 'package.json'}],
        'headRefOid': 'deadbeef',
        'statusCheckRollup': [],
    }
    pr = parse_pull_request(search, detail)
    assert pr.repo == 'acme/api'
    assert pr.is_bot
    assert pr.files == ('package.json',)
    assert pr.created_at == datetime(2026, 11, 5, 11, 0, tzinfo=UTC)
    assert pr.checks == ChecksState.NONE


@pytest.mark.parametrize(
    ('rollup', 'expected'),
    [
        ([], ChecksState.NONE),
        (
            [{'status': 'COMPLETED', 'conclusion': 'SUCCESS'}],
            ChecksState.PASSING,
        ),
        (
            [
                {'status': 'COMPLETED', 'conclusion': 'SUCCESS'},
                {'status': 'COMPLETED', 'conclusion': 'SKIPPED'},
                {'state': 'SUCCESS'},
            ],
            ChecksState.PASSING,
        ),
        (
            [
                {'status': 'IN_PROGRESS', 'conclusion': ''},
                {'status': 'COMPLETED', 'conclusion': 'SUCCESS'},
            ],
            ChecksState.PENDING,
        ),
        (
            [
                {'status': 'IN_PROGRESS', 'conclusion': ''},
                {'status': 'COMPLETED', 'conclusion': 'FAILURE'},
            ],
            ChecksState.FAILING,
        ),
        ([{'state': 'ERROR'}], ChecksState.FAILING),
        ([{'state': 'PENDING'}], ChecksState.PENDING),
        (
            [{'status': 'COMPLETED', 'conclusion': 'TIMED_OUT'}],
            ChecksState.FAILING,
        ),
    ],
)
def test_checks_state(
    rollup: list[dict[str, str]],
    expected: ChecksState,
) -> None:
    assert checks_state(rollup) == expected


def reasons_for(pr: PullRequest, risk: str = '') -> list[str]:
    return score_pull_request(pr, NOW, risk).reasons


@pytest.mark.parametrize(
    ('files', 'reason'),
    [
        (('db/migrations/0042_add.sql', 'tests/t.py'), 'migration'),
        (('src/auth/session.py', 'tests/t.py'), 'auth'),
        (('infra/main.tf', 'tests/t.py'), 'infra'),
        (('.github/workflows/ci.yml',), 'CI'),
        (('package.json', 'package-lock.json'), 'deps'),
        (('Dockerfile',), 'infra'),
    ],
)
def test_score_flags_risky_paths(files: tuple[str, ...], reason: str) -> None:
    assert reason in reasons_for(make_pr(files=files))


def test_score_flags_code_without_tests() -> None:
    assert 'no tests' in reasons_for(make_pr(files=('src/a.py', 'src/b.py')))


def test_score_does_not_flag_docs_only_change_as_untested() -> None:
    reasons = reasons_for(make_pr(files=('README.md', 'docs/x.md')))
    assert 'no tests' not in reasons


def test_risky_pr_outranks_trivial_pr() -> None:
    risky = make_pr(files=('src/auth/token.py', 'db/migrations/1.sql'))
    trivial = make_pr(files=('README.md',), additions=1, deletions=0)
    assert (
        score_pull_request(risky, NOW, '').score
        > score_pull_request(trivial, NOW, '').score
    )


def test_long_wait_raises_score() -> None:
    fresh = make_pr()
    stale = make_pr(created_at=NOW - timedelta(days=3))
    stale_score = score_pull_request(stale, NOW, '')
    assert stale_score.score > score_pull_request(fresh, NOW, '').score
    assert 'waiting 3d' in stale_score.reasons


def test_bot_and_red_ci_lower_score() -> None:
    base = score_pull_request(make_pr(), NOW, '').score
    bot = score_pull_request(make_pr(is_bot=True), NOW, '')
    red = score_pull_request(make_pr(checks=ChecksState.FAILING), NOW, '')
    assert bot.score < base
    assert red.score < base
    assert 'CI red' in red.reasons


def test_agent_high_risk_raises_score() -> None:
    plain = score_pull_request(make_pr(), NOW, '').score
    flagged = score_pull_request(make_pr(), NOW, 'high')
    assert flagged.score > plain
    assert 'agent: high risk' in flagged.reasons


def test_small_safe_pr_is_quick_win() -> None:
    assert score_pull_request(make_pr(), NOW, 'low').quick
    big = make_pr(additions=900)
    assert not score_pull_request(big, NOW, 'low').quick
    assert (
        'huge' in score_pull_request(make_pr(additions=1500), NOW, '').reasons
    )


def test_score_is_clamped_to_0_100() -> None:
    worst = make_pr(
        files=(
            'db/migrations/1.sql',
            'src/auth/a.py',
            'infra/x.tf',
            '.github/workflows/c.yml',
            'package-lock.json',
        ),
        additions=5000,
        created_at=NOW - timedelta(days=30),
    )
    assert score_pull_request(worst, NOW, 'high').score == 100  # noqa: PLR2004
    best = make_pr(is_bot=True, checks=ChecksState.FAILING, files=())
    assert score_pull_request(best, NOW, 'low').score >= 0


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('RISK: high\nSUMMARY: x', 'high'),
        ('Some preamble\n**RISK:** Medium\n', 'medium'),
        ('risk: low', 'low'),
        ('no verdict here', ''),
        ('RISK: catastrophic', ''),
    ],
)
def test_parse_review_risk(text: str, expected: str) -> None:
    assert parse_review_risk(text) == expected


DIFF = """diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1 +1 @@
-old
+new
diff --git a/package-lock.json b/package-lock.json
--- a/package-lock.json
+++ b/package-lock.json
@@ -1 +1 @@
-{"v": 1}
+{"v": 2}
"""


def test_trim_diff_drops_lockfiles_and_notes_them() -> None:
    trimmed = trim_diff(DIFF, max_chars=10_000)
    assert '+new' in trimmed
    assert '"v": 2' not in trimmed
    assert 'package-lock.json' in trimmed.splitlines()[-1]


def test_trim_diff_truncates_and_says_so() -> None:
    trimmed = trim_diff('x' * 500, max_chars=100)
    assert len(trimmed) < 200  # noqa: PLR2004
    assert 'truncated' in trimmed


@pytest.mark.parametrize(
    ('kind', 'expected_start'),
    [
        ('claude', ['claude', '-p', '--tools', '']),
        ('copilot', ['copilot', '-s', '--no-ask-user']),
    ],
)
def test_review_command_disables_tools(
    kind: str,
    expected_start: list[str],
) -> None:
    """The diff is untrusted input; the reviewer must not be able to act."""
    cmd = review_command(kind, binary=kind, model='')
    assert cmd[: len(expected_start)] == expected_start


def test_review_command_passes_model() -> None:
    cmd = review_command('claude', binary='claude', model='sonnet')
    assert cmd[cmd.index('--model') + 1] == 'sonnet'


def test_review_cache_keyed_by_head_sha(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)
    pr = make_pr()
    assert cache.get(pr) is None
    cache.put(pr, Review(text='RISK: high\nSUMMARY: scary', agent='claude'))
    cached = cache.get(pr)
    assert cached is not None
    assert cached.risk == 'high'
    assert cached.summary == 'scary'
    assert cache.get(make_pr(head_sha='newsha000000')) is None


def test_review_cache_paths_are_safe_for_odd_repo_names(
    tmp_path: Path,
) -> None:
    cache = ReviewCache(tmp_path)
    pr = make_pr(repo='../../etc/passwd')
    cache.put(pr, Review(text='x', agent='claude'))
    assert all(p.parent == tmp_path for p in tmp_path.rglob('*.md'))
