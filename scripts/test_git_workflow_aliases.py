"""Tests for the start/ship/rescue/done aliases in config/.gitconfig.

The aliases delegate to scripts/git_workflow.sh. `gh` is stubbed on PATH so
tests never hit GitHub.
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
GITCONFIG = REPO / 'config' / '.gitconfig'
SCRIPT = REPO / 'scripts' / 'git_workflow.sh'
FIVE_LINES = 'a\nb\nc\nd\ne\n'
EDGES_EDITED = 'A\nb\nc\nd\nE\n'
EXIT_USAGE = 2
GH_STUB = """#!/usr/bin/env bash
echo "gh $*" >> "${GH_CALLS_FILE}"
if [ "$1 $2" = 'pr view' ] && [ -n "${3:-}" ] && [ "${3#-}" = "$3" ]; then
    [ -n "${GH_PARENT_STATE:-}" ] || exit 1
    echo "${GH_PARENT_STATE}"
    exit 0
fi
if [ "$1 $2" = 'pr view' ]; then
    if [ -e "${GH_CALLS_FILE}.watched" ] \\
        && [ -n "${GH_PR_STATE_AFTER_WATCH:-}" ]; then
        GH_PR_STATE="${GH_PR_STATE_AFTER_WATCH}"
    fi
    [ -n "${GH_PR_STATE:-}" ] || { echo 'no pull requests found' >&2; exit 1; }
    case "$*" in
        *headRefOid*) echo "${GH_PR_STATE} ${GH_PR_HEAD:-}" ;;
        *) echo "${GH_PR_STATE}" ;;
    esac
fi
if [ "$1 $2" = 'pr merge' ] && [ -n "${GH_MERGE_FAILS:-}" ]; then
    echo "${GH_MERGE_FAILS}" >&2
    exit 1
fi
if [ "$*" = 'pr checks --watch' ]; then
    touch "${GH_CALLS_FILE}.watched"
    [ -z "${GH_WATCH_FAILS:-}" ] || exit 1
fi
if [ "$*" = 'pr checks' ]; then
    n=$(( $(cat "${GH_CALLS_FILE}.polls" 2>/dev/null || echo 0) + 1 ))
    echo "$n" > "${GH_CALLS_FILE}.polls"
    if [ "$n" -le "${GH_NO_CHECKS_FOR:-0}" ]; then
        echo "no checks reported on the 'topic' branch" >&2
        exit 1
    fi
fi
"""


def git(
    cwd: Path,
    *args: str,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ['git', *args],  # noqa: S607
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    stub_bin = tmp_path / 'bin'
    stub_bin.mkdir()
    gh = stub_bin / 'gh'
    gh.write_text(GH_STUB)
    gh.chmod(0o755)
    return {
        **os.environ,
        'PATH': f'{stub_bin}:{os.environ["PATH"]}',
        'HOME': str(tmp_path / 'home'),
        'GIT_CONFIG_GLOBAL': str(GITCONFIG),
        'GIT_CONFIG_NOSYSTEM': '1',
        'DOTFILES_DIR': str(REPO),
        'GIT_AUTHOR_NAME': 't',
        'GIT_AUTHOR_EMAIL': 't@example.com',
        'GIT_COMMITTER_NAME': 't',
        'GIT_COMMITTER_EMAIL': 't@example.com',
        'GH_CALLS_FILE': str(tmp_path / 'gh_calls'),
        'GIT_SHIP_POLL_SECS': '0',
    }


@pytest.fixture
def base() -> str:
    return 'main'


@pytest.fixture
def clone(tmp_path: Path, env: dict[str, str], base: str) -> Path:
    origin = tmp_path / 'origin.git'
    git(tmp_path, 'init', '--bare', '-b', base, str(origin), env=env)
    seed = tmp_path / 'seed'
    git(tmp_path, 'clone', str(origin), str(seed), env=env)
    (seed / 'f.txt').write_text(FIVE_LINES)
    git(seed, 'add', 'f.txt', env=env)
    git(seed, 'commit', '-m', 'first', env=env)
    git(seed, 'push', 'origin', *{f'HEAD:{base}', 'HEAD:main'}, env=env)
    work = tmp_path / 'work'
    git(tmp_path, 'clone', str(origin), str(work), env=env)
    git(seed, 'commit', '--allow-empty', '-m', 'upstream', env=env)
    git(seed, 'push', 'origin', f'HEAD:{base}', env=env)
    return work


def run_script(
    *args: str,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize('flag', ['--version', '-v'])
def test_script_prints_version_without_git_repo(
    env: dict[str, str],
    flag: str,
) -> None:
    result = run_script(flag, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith('git_workflow ')


@pytest.mark.parametrize(
    ('args', 'returncode'),
    [
        ([], 2),
        (['--help'], 0),
        (['bogus'], 2),
    ],
)
def test_script_prints_usage(
    env: dict[str, str],
    args: list[str],
    returncode: int,
) -> None:
    result = run_script(*args, env=env)

    assert result.returncode == returncode
    assert 'git start <topic>' in result.stdout + result.stderr


def test_gitconfig_aliases_only_delegate_to_script() -> None:
    lines = GITCONFIG.read_text().splitlines()
    script = '${DOTFILES_DIR:-$HOME/projects/dotfiles}/scripts/git_workflow.sh'
    for name in ('start', 'ship', 'rescue', 'done'):
        assert f'    {name} = "!\\"{script}\\" {name}"' in lines


def test_start_branches_from_freshly_pulled_main(
    clone: Path,
    env: dict[str, str],
) -> None:
    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode == 0, result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    subject = git(clone, 'log', '-1', '--format=%s', env=env).stdout.strip()
    assert (branch, subject) == ('my-topic', 'upstream')


def on_branch_with_committed_edit(clone: Path, env: dict[str, str]) -> None:
    git(clone, 'switch', '-c', 'old-topic', env=env)
    (clone / 'f.txt').write_text(FIVE_LINES.replace('a', 'A'))
    git(clone, 'commit', '-am', 'feat: edit a', env=env)


def test_start_carries_uncommitted_changes_to_new_branch(
    clone: Path,
    env: dict[str, str],
) -> None:
    on_branch_with_committed_edit(clone, env)
    (clone / 'f.txt').write_text(
        FIVE_LINES.replace('a', 'A').replace('e', 'E'),
    )
    (clone / 'new.txt').write_text('untracked\n')

    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode == 0, result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    assert branch == 'my-topic'
    assert (clone / 'f.txt').read_text() == FIVE_LINES.replace('e', 'E')
    assert (clone / 'new.txt').read_text() == 'untracked\n'
    assert git(clone, 'stash', 'list', env=env).stdout == ''


def test_start_keeps_stash_and_explains_when_carry_conflicts(
    clone: Path,
    env: dict[str, str],
) -> None:
    on_branch_with_committed_edit(clone, env)
    (clone / 'f.txt').write_text(FIVE_LINES.replace('a', 'AA'))

    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode != 0
    assert 'git stash drop' in result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    assert branch == 'my-topic'
    assert git(clone, 'stash', 'list', env=env).stdout.count('\n') == 1


def test_start_failure_restores_branch_and_changes(
    clone: Path,
    env: dict[str, str],
) -> None:
    (clone / 'main_only.txt').write_text('diverged\n')
    git(clone, 'add', 'main_only.txt', env=env)
    git(clone, 'commit', '-m', 'diverge main', env=env)
    on_branch_with_committed_edit(clone, env)
    (clone / 'new.txt').write_text('untracked\n')

    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode != 0
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    assert branch == 'old-topic'
    assert (clone / 'new.txt').read_text() == 'untracked\n'
    assert git(clone, 'stash', 'list', env=env).stdout == ''


def test_start_with_clean_tree_leaves_older_stashes_alone(
    clone: Path,
    env: dict[str, str],
) -> None:
    (clone / 'old.txt').write_text('stashed earlier\n')
    git(clone, 'stash', '-u', env=env)

    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode == 0, result.stderr
    assert not (clone / 'old.txt').exists()
    assert git(clone, 'stash', 'list', env=env).stdout.count('\n') == 1


@pytest.mark.parametrize(
    'args',
    [(), ('-s',), ('a', 'b'), ('--bogus', 'a')],
)
def test_start_rejects_bad_arguments_with_usage(
    clone: Path,
    env: dict[str, str],
    args: tuple[str, ...],
) -> None:
    result = git(clone, 'start', *args, env=env)

    assert result.returncode == EXIT_USAGE
    assert 'usage: git start [-s] <topic>' in result.stderr


@pytest.mark.parametrize(
    ('subjects', 'title'),
    [
        (['ci: one', 'feat: two'], 'feat: main branch protection'),
        (['docs: one', 'chore(deps): two'], 'docs: main branch protection'),
        (['fix!: one', 'feat: two'], 'feat!: main branch protection'),
    ],
)
def test_ship_titles_pr_with_top_prefix_and_branch_name(
    clone: Path,
    env: dict[str, str],
    subjects: list[str],
    title: str,
) -> None:
    git(clone, 'start', 'main-branch-protection', env=env)
    for subject in subjects:
        git(clone, 'commit', '--allow-empty', '-m', subject, env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode == 0, result.stderr
    remote = git(
        clone,
        'ls-remote',
        'origin',
        'main-branch-protection',
        env=env,
    )
    assert 'refs/heads/main-branch-protection' in remote.stdout
    body = '\n'.join(f'- {s}' for s in subjects)
    assert (
        Path(env['GH_CALLS_FILE'])
        .read_text()
        .startswith(
            'gh pr view --json state -q .state\n'
            f'gh pr create --base main --title {title} --body {body}\n'
            'gh pr merge --auto --squash --delete-branch\n'
            'gh pr checks\n'
            'gh pr checks --watch\n',
        )
    )


@pytest.mark.parametrize(
    ('no_checks_for', 'returncode'),
    [
        (2, 0),
        (30, 1),
    ],
)
def test_ship_waits_for_ci_checks_before_watching(
    clone: Path,
    env: dict[str, str],
    no_checks_for: int,
    returncode: int,
) -> None:
    env['GH_NO_CHECKS_FOR'] = str(no_checks_for)
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: one', env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode == returncode, result.stderr
    calls = Path(env['GH_CALLS_FILE']).read_text().splitlines()
    watched = returncode == 0
    assert ('gh pr checks --watch' in calls) == watched
    assert ('run gh pr checks --watch later' in result.stderr) != watched


@pytest.mark.parametrize(
    'state',
    ['OPEN', 'CLOSED'],
)
def test_ship_reuses_open_pr(
    clone: Path,
    env: dict[str, str],
    state: str,
) -> None:
    env['GH_PR_STATE'] = state
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: one', env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode == 0, result.stderr
    calls = Path(env['GH_CALLS_FILE']).read_text().splitlines()
    creates = state != 'OPEN'
    assert any(c.startswith('gh pr create') for c in calls) == creates
    merge = calls.index('gh pr merge --auto --squash --delete-branch')
    assert calls[merge : merge + 3] == [
        'gh pr merge --auto --squash --delete-branch',
        'gh pr checks',
        'gh pr checks --watch',
    ]


def test_ship_watches_ci_when_auto_merge_not_allowed(
    clone: Path,
    env: dict[str, str],
) -> None:
    env['GH_MERGE_FAILS'] = 'Auto merge is not allowed for this repository'
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: one', env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode == 0, result.stderr
    calls = Path(env['GH_CALLS_FILE']).read_text().splitlines()
    assert calls[-2:] == ['gh pr checks', 'gh pr checks --watch']
    assert 'Auto merge is not allowed' in result.stderr
    assert 'gh pr merge --squash --delete-branch' in result.stderr


def test_ship_refuses_when_pr_already_merged(
    clone: Path,
    env: dict[str, str],
) -> None:
    env['GH_PR_STATE'] = 'MERGED'
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: one', env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode != 0
    assert 'already merged: run git done' in result.stderr
    assert 'git rescue <topic>' in result.stderr
    assert git(clone, 'ls-remote', 'origin', 'topic', env=env).stdout == ''
    assert Path(env['GH_CALLS_FILE']).read_text() == (
        'gh pr view --json state -q .state\n'
    )


def test_ship_refuses_without_conventional_commits(
    clone: Path,
    env: dict[str, str],
) -> None:
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'no prefix', env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode != 0
    assert 'no conventional commit prefix' in result.stderr
    assert not Path(env['GH_CALLS_FILE']).exists()


def test_ship_refuses_on_main(clone: Path, env: dict[str, str]) -> None:
    result = git(clone, 'ship', env=env)

    assert result.returncode != 0
    assert 'on main' in result.stderr
    assert not Path(env['GH_CALLS_FILE']).exists()


def head(clone: Path, env: dict[str, str]) -> str:
    return git(clone, 'rev-parse', 'HEAD', env=env).stdout.strip()


def ready_to_ship(clone: Path, env: dict[str, str]) -> None:
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: one', env=env)
    env['GH_PR_STATE_AFTER_WATCH'] = 'MERGED'
    env['GH_PR_HEAD'] = head(clone, env)


def current_branch(clone: Path, env: dict[str, str]) -> str:
    return git(clone, 'branch', '--show-current', env=env).stdout.strip()


def test_ship_runs_done_after_auto_merge(
    clone: Path,
    env: dict[str, str],
) -> None:
    ready_to_ship(clone, env)
    (clone / 'new.txt').write_text('untracked\n')

    result = git(clone, 'ship', env=env)

    assert result.returncode == 0, result.stderr
    subject = git(clone, 'log', '-1', '--format=%s', env=env).stdout.strip()
    assert (current_branch(clone, env), subject) == ('main', 'upstream')
    assert (clone / 'new.txt').read_text() == 'untracked\n'


@pytest.mark.parametrize(
    ('args', 'env_overrides', 'message'),
    [
        ((), {'GH_PR_HEAD': '0' * 40}, 'git rescue <topic>'),
        (
            (),
            {'GH_PR_STATE_AFTER_WATCH': 'OPEN'},
            'run git done once it merges',
        ),
        (('--no-done',), {}, ''),
        (
            (),
            {'GH_MERGE_FAILS': 'Auto merge is not allowed'},
            'gh pr merge --squash --delete-branch',
        ),
    ],
    ids=['commits-after-ship', 'never-merged', 'no-done', 'auto-merge-off'],
)
def test_ship_stays_on_branch_when_done_is_unsafe(
    clone: Path,
    env: dict[str, str],
    args: tuple[str, ...],
    env_overrides: dict[str, str],
    message: str,
) -> None:
    ready_to_ship(clone, env)
    env.update(env_overrides)

    result = git(clone, 'ship', *args, env=env)

    assert result.returncode == 0, result.stderr
    assert current_branch(clone, env) == 'topic'
    assert message in result.stderr


def test_ship_stays_on_branch_when_ci_fails(
    clone: Path,
    env: dict[str, str],
) -> None:
    ready_to_ship(clone, env)
    env['GH_WATCH_FAILS'] = '1'

    result = git(clone, 'ship', env=env)

    assert result.returncode != 0
    assert current_branch(clone, env) == 'topic'


def test_ship_rejects_unknown_argument(
    clone: Path,
    env: dict[str, str],
) -> None:
    ready_to_ship(clone, env)

    result = git(clone, 'ship', '--bogus', env=env)

    assert result.returncode == EXIT_USAGE
    assert 'usage: git ship [--no-done]' in result.stderr
    assert not Path(env['GH_CALLS_FILE']).exists()


def on_merged_branch(clone: Path, env: dict[str, str]) -> None:
    git(clone, 'start', 'topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: merged', env=env)
    env['GH_PR_STATE'] = 'MERGED'
    env['GH_PR_HEAD'] = head(clone, env)


def test_rescue_moves_commits_after_merge_onto_new_branch(
    clone: Path,
    env: dict[str, str],
) -> None:
    on_merged_branch(clone, env)
    git(clone, 'commit', '--allow-empty', '-m', 'fix: late one', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'fix: late two', env=env)

    result = git(clone, 'rescue', 'late-fixes', env=env)

    assert result.returncode == 0, result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    subjects = git(
        clone,
        'log',
        '--format=%s',
        'origin/main..HEAD',
        env=env,
    ).stdout.splitlines()
    base = git(clone, 'merge-base', 'HEAD', 'origin/main', env=env)
    assert branch == 'late-fixes'
    assert subjects == ['fix: late two', 'fix: late one']
    assert (
        base.stdout.strip()
        == git(
            clone,
            'rev-parse',
            'origin/main',
            env=env,
        ).stdout.strip()
    )


def assert_rescue_refused(
    clone: Path,
    env: dict[str, str],
    message: str,
) -> None:
    before = head(clone, env)

    result = git(clone, 'rescue', 'late-fixes', env=env)

    assert result.returncode != 0
    assert message in result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    assert (branch, head(clone, env)) == ('topic', before)


@pytest.mark.parametrize(
    ('state', 'late_commits', 'message'),
    [
        ('OPEN', 1, 'no merged PR for this branch: use git ship'),
        ('', 1, 'no merged PR for this branch: use git ship'),
        ('MERGED', 0, 'nothing to rescue: run git done'),
    ],
)
def test_rescue_refuses_without_merged_pr_and_late_commits(
    clone: Path,
    env: dict[str, str],
    state: str,
    late_commits: int,
    message: str,
) -> None:
    on_merged_branch(clone, env)
    env['GH_PR_STATE'] = state
    for _ in range(late_commits):
        git(clone, 'commit', '--allow-empty', '-m', 'fix: late', env=env)

    assert_rescue_refused(clone, env, message)


def test_rescue_refuses_with_uncommitted_changes(
    clone: Path,
    env: dict[str, str],
) -> None:
    on_merged_branch(clone, env)
    git(clone, 'commit', '--allow-empty', '-m', 'fix: late', env=env)
    (clone / 'f.txt').write_text('changed\n')

    assert_rescue_refused(clone, env, 'commit or stash them first')


def test_rescue_without_topic_prints_usage(
    clone: Path,
    env: dict[str, str],
) -> None:
    result = git(clone, 'rescue', env=env)

    assert result.returncode != 0
    assert 'usage: git rescue <topic>' in result.stderr


def test_done_returns_to_updated_main(
    clone: Path,
    env: dict[str, str],
) -> None:
    git(clone, 'switch', '-c', 'my-topic', env=env)

    result = git(clone, 'done', env=env)

    assert result.returncode == 0, result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    subject = git(clone, 'log', '-1', '--format=%s', env=env).stdout.strip()
    assert (branch, subject) == ('main', 'upstream')


def main_diverged_from_origin(
    clone: Path,
    env: dict[str, str],
    upstream_text: str,
) -> None:
    """Local main gets a direct commit; origin gets a squash of its own."""
    (clone / 'f.txt').write_text('squashed\n')
    git(clone, 'commit', '-am', 'fix: direct on main', env=env)
    seed = clone.parent / 'seed'
    git(seed, 'pull', '--quiet', env=env)
    (seed / 'f.txt').write_text(upstream_text)
    git(seed, 'commit', '-am', 'fix: squash (#1)', env=env)
    git(seed, 'push', 'origin', 'HEAD:main', env=env)
    git(clone, 'switch', '-c', 'my-topic', env=env)


def test_done_resets_main_already_squash_merged(
    clone: Path,
    env: dict[str, str],
) -> None:
    main_diverged_from_origin(clone, env, upstream_text='squashed\n')
    (clone / 'untracked.txt').write_text('keep me\n')

    result = git(clone, 'done', env=env)

    assert result.returncode == 0, result.stderr
    subject = git(clone, 'log', '-1', '--format=%s', env=env).stdout.strip()
    assert subject == 'fix: squash (#1)'
    assert (clone / 'untracked.txt').read_text() == 'keep me\n'


def test_done_refuses_when_local_main_has_unmerged_work(
    clone: Path,
    env: dict[str, str],
) -> None:
    main_diverged_from_origin(clone, env, upstream_text='other\n')

    result = git(clone, 'done', env=env)

    assert result.returncode != 0
    assert 'local main has commits not on origin/main' in result.stderr
    subject = git(clone, 'log', '-1', '--format=%s', env=env).stdout.strip()
    assert subject == 'fix: direct on main'


def test_done_carries_uncommitted_changes_to_main(
    clone: Path,
    env: dict[str, str],
) -> None:
    git(clone, 'switch', '-c', 'my-topic', env=env)
    (clone / 'f.txt').write_text(FIVE_LINES.replace('e', 'E'))
    (clone / 'new.txt').write_text('untracked\n')

    result = git(clone, 'done', env=env)

    assert result.returncode == 0, result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    subject = git(clone, 'log', '-1', '--format=%s', env=env).stdout.strip()
    assert (branch, subject) == ('main', 'upstream')
    assert (clone / 'f.txt').read_text() == FIVE_LINES.replace('e', 'E')
    assert (clone / 'new.txt').read_text() == 'untracked\n'
    assert git(clone, 'stash', 'list', env=env).stdout == ''
    assert 'git start <topic>' in result.stderr


def test_done_failure_restores_branch_and_changes(
    clone: Path,
    env: dict[str, str],
) -> None:
    main_diverged_from_origin(clone, env, upstream_text='other\n')
    (clone / 'new.txt').write_text('untracked\n')

    result = git(clone, 'done', env=env)

    assert result.returncode != 0
    assert 'local main has commits not on origin/main' in result.stderr
    branch = git(clone, 'branch', '--show-current', env=env).stdout.strip()
    assert branch == 'my-topic'
    assert (clone / 'new.txt').read_text() == 'untracked\n'
    assert git(clone, 'stash', 'list', env=env).stdout == ''


@pytest.mark.parametrize(
    'args',
    [('done',), ('start', 'my-topic')],
)
def test_never_checks_out_stale_main(
    clone: Path,
    env: dict[str, str],
    args: tuple[str, ...],
) -> None:
    stale_main = git(clone, 'rev-parse', 'main', env=env).stdout.strip()
    git(clone, 'switch', '-c', 'old-topic', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'feat: work', env=env)
    seen_before = len(reflog(clone, env))

    result = git(clone, *args, env=env)

    assert result.returncode == 0, result.stderr
    assert stale_main not in reflog(clone, env)[: -seen_before or None]


def reflog(clone: Path, env: dict[str, str]) -> list[str]:
    return git(clone, 'reflog', '--format=%H', 'HEAD', env=env).stdout.split()


NON_MAIN_BASES = pytest.mark.parametrize('base', ['develop', 'master'])


def subject_of(clone: Path, env: dict[str, str], rev: str = 'HEAD') -> str:
    return git(clone, 'log', '-1', '--format=%s', rev, env=env).stdout.strip()


@NON_MAIN_BASES
def test_start_branches_from_remote_default_branch(
    clone: Path,
    env: dict[str, str],
    base: str,
) -> None:
    git(clone, 'switch', '-c', 'old-topic', env=env)
    git(clone, 'branch', '-D', base, env=env)

    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode == 0, result.stderr
    assert current_branch(clone, env) == 'my-topic'
    assert subject_of(clone, env) == 'upstream'
    assert subject_of(clone, env, base) == 'upstream'


@NON_MAIN_BASES
def test_start_finds_base_without_origin_head(
    clone: Path,
    env: dict[str, str],
    base: str,
) -> None:
    git(clone, 'remote', 'set-head', 'origin', '--delete', env=env)

    result = git(clone, 'start', 'my-topic', env=env)

    assert result.returncode == 0, result.stderr
    assert subject_of(clone, env) == 'upstream'
    assert subject_of(clone, env, base) == 'upstream'


@NON_MAIN_BASES
def test_done_returns_to_remote_default_branch(
    clone: Path,
    env: dict[str, str],
    base: str,
) -> None:
    git(clone, 'switch', '-c', 'my-topic', env=env)

    result = git(clone, 'done', env=env)

    assert result.returncode == 0, result.stderr
    assert (current_branch(clone, env), subject_of(clone, env)) == (
        base,
        'upstream',
    )


@NON_MAIN_BASES
def test_ship_targets_remote_default_branch(
    clone: Path,
    env: dict[str, str],
    base: str,
) -> None:
    ready_to_ship(clone, env)

    result = git(clone, 'ship', env=env)

    assert result.returncode == 0, result.stderr
    calls = Path(env['GH_CALLS_FILE']).read_text().splitlines()
    assert (
        f'gh pr create --base {base} --title feat: topic --body - feat: one'
        in calls
    )
    assert (current_branch(clone, env), subject_of(clone, env)) == (
        base,
        'upstream',
    )


@NON_MAIN_BASES
def test_ship_refuses_on_base(
    clone: Path,
    env: dict[str, str],
    base: str,
) -> None:
    git(clone, 'switch', base, env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode != 0
    assert f'on {base}: run git start <topic> first' in result.stderr


@NON_MAIN_BASES
def test_rescue_rebases_onto_remote_default_branch(
    clone: Path,
    env: dict[str, str],
    base: str,
) -> None:
    on_merged_branch(clone, env)
    git(clone, 'commit', '--allow-empty', '-m', 'fix: late', env=env)

    result = git(clone, 'rescue', 'late-fixes', env=env)

    assert result.returncode == 0, result.stderr
    subjects = git(
        clone,
        'log',
        '--format=%s',
        f'origin/{base}..HEAD',
        env=env,
    ).stdout.splitlines()
    assert subjects == ['fix: late']
    assert subject_of(clone, env, 'HEAD~1') == 'upstream'


def stack_config(clone: Path, env: dict[str, str], key: str) -> str:
    return git(
        clone,
        'config',
        '--get',
        f'branch.{key}',
        env=env,
    ).stdout.strip()


def stacked(clone: Path, env: dict[str, str]) -> None:
    git(clone, 'start', 'parent', env=env)
    (clone / 'f.txt').write_text(FIVE_LINES.replace('a', 'A'))
    git(clone, 'commit', '-am', 'feat: parent', env=env)
    git(clone, 'push', '-u', 'origin', 'parent', env=env)
    git(clone, 'start', '-s', 'child', env=env)
    (clone / 'f.txt').write_text(EDGES_EDITED)
    git(clone, 'commit', '-am', 'feat: child', env=env)


def squash_merge_parent(clone: Path, env: dict[str, str], text: str) -> None:
    seed = clone.parent / 'seed'
    git(seed, 'pull', '--quiet', env=env)
    (seed / 'f.txt').write_text(text)
    git(seed, 'commit', '-am', 'feat: parent (#1)', env=env)
    git(seed, 'push', 'origin', 'HEAD:main', ':parent', env=env)
    env['GH_PARENT_STATE'] = 'MERGED'


def own_subjects(clone: Path, env: dict[str, str], since: str) -> list[str]:
    log = git(clone, 'log', '--format=%s', f'{since}..HEAD', env=env)
    return log.stdout.splitlines()


@pytest.mark.parametrize(
    'args',
    [('-s', 'child'), ('--stack', 'child'), ('child', '-s')],
)
def test_start_stack_branches_from_current_branch(
    clone: Path,
    env: dict[str, str],
    args: tuple[str, ...],
) -> None:
    on_branch_with_committed_edit(clone, env)
    parent_head = head(clone, env)
    (clone / 'f.txt').write_text(EDGES_EDITED)

    result = git(clone, 'start', *args, env=env)

    assert result.returncode == 0, result.stderr
    assert (current_branch(clone, env), head(clone, env)) == (
        'child',
        parent_head,
    )
    assert stack_config(clone, env, 'child.stackParent') == 'old-topic'
    assert stack_config(clone, env, 'child.stackBase') == parent_head
    assert (clone / 'f.txt').read_text() == EDGES_EDITED


def test_start_stack_refuses_on_base(
    clone: Path,
    env: dict[str, str],
) -> None:
    result = git(clone, 'start', '-s', 'child', env=env)

    assert result.returncode == EXIT_USAGE
    assert 'on main: nothing to stack on' in result.stderr
    assert current_branch(clone, env) == 'main'


def test_ship_stacked_targets_parent_without_auto_merge(
    clone: Path,
    env: dict[str, str],
) -> None:
    stacked(clone, env)

    result = git(clone, 'ship', env=env)

    assert result.returncode == 0, result.stderr
    assert Path(env['GH_CALLS_FILE']).read_text().splitlines() == [
        'gh pr view parent --json state -q .state',
        'gh pr view --json state -q .state',
        'gh pr create --base parent --title feat: child --body - feat: child',
        'gh pr checks',
        'gh pr checks --watch',
    ]
    assert current_branch(clone, env) == 'child'
    assert 'once parent merges, run git done' in result.stderr


def test_ship_stacked_lists_only_own_commits_after_rebase_on_parent(
    clone: Path,
    env: dict[str, str],
) -> None:
    stacked(clone, env)
    git(clone, 'switch', 'parent', env=env)
    git(clone, 'commit', '--allow-empty', '-m', 'fix: review', env=env)
    git(clone, 'push', 'origin', 'parent', env=env)
    git(clone, 'switch', 'child', env=env)
    git(clone, 'rebase', 'parent', env=env)

    result = git(clone, 'ship', env=env)

    assert result.returncode == 0, result.stderr
    calls = Path(env['GH_CALLS_FILE']).read_text().splitlines()
    assert (
        'gh pr create --base parent --title feat: child --body - feat: child'
        in calls
    )


@pytest.mark.parametrize(
    ('before_ship', 'parent_state', 'message'),
    [
        (
            ('push', 'origin', ':parent'),
            '',
            'parent is not on origin: git ship it first',
        ),
        (
            (),
            'MERGED',
            'parent already merged: run git done first',
        ),
    ],
    ids=['parent-not-pushed', 'parent-merged'],
)
def test_ship_stacked_refuses_without_open_parent(
    clone: Path,
    env: dict[str, str],
    before_ship: tuple[str, ...],
    parent_state: str,
    message: str,
) -> None:
    stacked(clone, env)
    if before_ship:
        git(clone, *before_ship, env=env)
    env['GH_PARENT_STATE'] = parent_state

    result = git(clone, 'ship', env=env)

    assert result.returncode == EXIT_USAGE
    assert message in result.stderr
    assert git(clone, 'ls-remote', 'origin', 'child', env=env).stdout == ''
    calls = Path(env['GH_CALLS_FILE'])
    assert not calls.exists() or 'pr create' not in calls.read_text()


def test_done_moves_stacked_branch_onto_base_after_parent_merges(
    clone: Path,
    env: dict[str, str],
) -> None:
    stacked(clone, env)
    git(clone, 'push', '-u', 'origin', 'child', env=env)
    env['GH_PR_STATE'] = 'OPEN'
    squash_merge_parent(clone, env, FIVE_LINES.replace('a', 'A'))
    (clone / 'f.txt').write_text('A\nb\nC\nd\nE\n')

    result = git(clone, 'done', env=env)

    assert result.returncode == 0, result.stderr
    assert current_branch(clone, env) == 'child'
    assert own_subjects(clone, env, 'origin/main') == ['feat: child']
    assert (clone / 'f.txt').read_text() == 'A\nb\nC\nd\nE\n'
    assert stack_config(clone, env, 'child.stackParent') == ''
    assert stack_config(clone, env, 'child.stackBase') == ''
    remote = git(clone, 'ls-remote', 'origin', 'child', env=env).stdout
    assert remote.startswith(head(clone, env))
    calls = Path(env['GH_CALLS_FILE']).read_text().splitlines()
    assert 'gh pr edit --base main' in calls


def test_done_restacks_grandchild_onto_moved_parent(
    clone: Path,
    env: dict[str, str],
) -> None:
    stacked(clone, env)
    git(clone, 'start', '-s', 'grandchild', env=env)
    (clone / 'g.txt').write_text('g\n')
    git(clone, 'add', 'g.txt', env=env)
    git(clone, 'commit', '-m', 'feat: grandchild', env=env)
    squash_merge_parent(clone, env, FIVE_LINES.replace('a', 'A'))
    git(clone, 'switch', 'child', env=env)
    git(clone, 'done', env=env)
    git(clone, 'switch', 'grandchild', env=env)
    env['GH_PARENT_STATE'] = 'OPEN'

    result = git(clone, 'done', env=env)

    assert result.returncode == 0, result.stderr
    assert own_subjects(clone, env, 'child') == ['feat: grandchild']
    assert own_subjects(clone, env, 'origin/main') == [
        'feat: grandchild',
        'feat: child',
    ]
    child_head = git(clone, 'rev-parse', 'child', env=env).stdout.strip()
    assert stack_config(clone, env, 'grandchild.stackParent') == 'child'
    assert stack_config(clone, env, 'grandchild.stackBase') == child_head


def test_done_stacked_waits_for_unmerged_unmoved_parent(
    clone: Path,
    env: dict[str, str],
) -> None:
    stacked(clone, env)
    before = head(clone, env)
    env['GH_PARENT_STATE'] = 'OPEN'

    result = git(clone, 'done', env=env)

    assert result.returncode == 0, result.stderr
    assert 'parent not merged yet' in result.stderr
    assert (current_branch(clone, env), head(clone, env)) == ('child', before)
