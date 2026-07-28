"""Integration tests for the merge wiring in scripts/secrets.sh.

`pass` is stubbed with a script backed by a plain directory, so nothing here
touches the real password-store.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent
GIT = shutil.which('git') or 'git'

STUB_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail

store="${STUB_STORE}"

case "$1" in
show)
    entry="${store}/$2"
    [[ -f "${entry}" ]] || exit 1
    cat "${entry}"
    ;;
insert)
    shift
    while [[ "$1" == -* ]]; do shift; done
    entry="${store}/$1"
    mkdir -p "$(dirname "${entry}")"
    cat >"${entry}"
    ;;
git)
    shift
    exec git -C "${PASSWORD_STORE_DIR}" "$@"
    ;;
*)
    exit 0
    ;;
esac
"""

# A minimal stand-in for skill-tree's queue_cli.py -- title-only, synthetic
# bodies, deterministic ordering. It exists to test that secrets.sh resolves
# the right script, passes the right paths, and reconciles queue-complete
# before queue -- not to re-verify real merge semantics, which are skill-tree's
# own test suite's job (queue_cli.py moved there wholesale, unchanged).
STUB_QUEUE_CLI = """#!/usr/bin/env python3
import sys
from pathlib import Path


def parse_args(argv):
    args = {}
    it = iter(argv)
    for tok in it:
        if tok.startswith('--'):
            args[tok] = next(it, '')
    return args


def titles(text):
    seen, ordered = set(), []
    for line in text.splitlines():
        if line.startswith('## '):
            title = line.removeprefix('## ').strip()
            if title not in seen:
                seen.add(title)
                ordered.append(title)
    return ordered


def read(path):
    p = Path(path) if path else None
    return p.read_text() if p and p.exists() else ''


def render(header, all_titles):
    body = ''.join(f'## {t}\\n\\nstub body.\\n\\n' for t in all_titles)
    return f'{header}\\n\\n{body}'


def main():
    action = sys.argv[1]
    args = parse_args(sys.argv[2:])

    if action == 'merge-queue':
        local = titles(read(args['--queue-path']))
        incoming = titles(read(args['--incoming']))
        tombstones = set(titles(read(args['--complete-path'])))
        merged = [t for t in local if t not in tombstones]
        merged += [
            t for t in incoming if t not in tombstones and t not in merged
        ]
        Path(args['--queue-path']).write_text(render('# Queue', merged))
        print(f'  merged queue ({len(merged)} open)')
    elif action == 'merge-completed':
        local = titles(read(args['--complete-path']))
        incoming = titles(read(args['--incoming']))
        merged = local + [t for t in incoming if t not in local]
        Path(args['--complete-path']).write_text(render('# Completed', merged))
        print(f'  merged queue-complete ({len(merged)} completed)')


if __name__ == '__main__':
    main()
"""

# Real `pass` commits every insert, so the store is a working tree too.
GIT_ENV = {
    'GIT_AUTHOR_NAME': 'Test',
    'GIT_AUTHOR_EMAIL': 'test@example.com',
    'GIT_COMMITTER_NAME': 'Test',
    'GIT_COMMITTER_EMAIL': 'test@example.com',
    # The user's own config sets pull/signing defaults for ~/.password-store.
    'GIT_CONFIG_GLOBAL': os.devnull,
    'GIT_CONFIG_SYSTEM': os.devnull,
}

# The queue lives outside every repo now, so its manifest entries are
# home-relative. queue-complete deliberately precedes queue: the tombstones
# have to be reconciled first regardless of what order the manifest lists
# them in.
MANIFEST = (
    'queue/active:~/.claude/queue/queue\n'
    'queue/complete:~/.claude/queue/queue-complete\n'
)


class SyncHarness:
    """A throwaway repo plus fake store to run secrets.sh against."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.repo = root / 'repo'
        self.store = root / 'store'
        # Entries live in the store so a git-backed store can version them.
        self.entries = self.store
        self.bin = root / 'bin'
        self.projects = root / 'projects'
        self.home = root / 'home'
        self.queue = self.home / '.claude' / 'queue' / 'queue'
        self.complete = self.home / '.claude' / 'queue' / 'queue-complete'
        # Under $PROJECTS_DIR, so secrets.sh finds it via the same
        # ${SKILL_TREE_DIR:-${PROJECTS_DIR}/skill-tree} fallback as production.
        self.skill_tree = self.projects / 'skill-tree'

    def run(
        self,
        action: str,
        extra_env: dict[str, str] | None = None,
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            **GIT_ENV,
            'PATH': f'{self.bin}{os.pathsep}{os.environ["PATH"]}',
            'STUB_STORE': str(self.entries),
            'PASSWORD_STORE_DIR': str(self.store),
            'PROJECTS_DIR': str(self.projects),
            'HOME': str(self.home),
        }
        env.update(extra_env or {})
        return subprocess.run(  # noqa: S603
            [str(self.repo / 'scripts' / 'secrets.sh'), action],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            check=check,
        )

    def install_sibling(self, name: str) -> Path:
        """Create a sibling repo under PROJECTS_DIR, as a clone would look."""
        sibling = self.projects / name
        sibling.mkdir(parents=True)
        return sibling

    def store_entry(self, name: str) -> str:
        return (self.entries / name).read_text()

    def write_store_entry(self, name: str, text: str) -> None:
        path = self.entries / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


@pytest.fixture
def harness(tmp_path: Path) -> SyncHarness:
    setup = SyncHarness(tmp_path)

    (setup.repo / 'scripts').mkdir(parents=True)
    shutil.copy(
        SCRIPTS_DIR / 'secrets.sh',
        setup.repo / 'scripts' / 'secrets.sh',
    )
    (setup.repo / 'scripts' / 'secrets.sh').chmod(0o755)
    subprocess.run(  # noqa: S603
        [GIT, 'init', '--quiet'],
        cwd=setup.repo,
        check=True,
        capture_output=True,
    )

    setup.store.mkdir()
    setup.bin.mkdir()
    setup.queue.parent.mkdir(parents=True)
    fake_pass = setup.bin / 'pass'
    fake_pass.write_text(STUB_SCRIPT)
    fake_pass.chmod(0o755)

    setup.projects.mkdir()
    (setup.skill_tree / 'scripts').mkdir(parents=True)
    stub = setup.skill_tree / 'scripts' / 'queue_cli.py'
    stub.write_text(STUB_QUEUE_CLI)
    stub.chmod(0o755)
    setup.write_store_entry('manifest', MANIFEST)
    return setup


def _queue(*titles: str) -> str:
    sections = ''.join(f'## {t}\n\n{t} body.\n\n' for t in titles)
    return f'# Queue\n\n{sections}'


def _titles(queue_text: str) -> list[str]:
    return [
        line.removeprefix('## ').strip()
        for line in queue_text.splitlines()
        if line.startswith('## ')
    ]


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        [GIT, *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **GIT_ENV},
    )


def _commit_store(harness: SyncHarness, message: str) -> None:
    _git(harness.store, 'add', '-A')
    _git(harness.store, 'commit', '-m', message)


def _git_backed_store(harness: SyncHarness) -> Path:
    """Turn the store into a clone of a bare remote, as a real one is."""
    remote = harness.root / 'remote.git'
    _git(harness.root, 'init', '--bare', '-b', 'main', str(remote))
    _git(harness.store, 'init', '-b', 'main')
    _commit_store(harness, 'initial')
    _git(harness.store, 'remote', 'add', 'origin', str(remote))
    _git(harness.store, 'push', '-u', 'origin', 'main')
    return remote


def _other_machine_pushes(
    harness: SyncHarness,
    remote: Path,
    name: str,
    text: str,
) -> None:
    other = harness.root / 'other'
    if not other.exists():
        _git(harness.root, 'clone', '--quiet', str(remote), str(other))
    entry = other / name
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text(text)
    _git(other, 'add', '-A')
    _git(other, 'commit', '-m', f'update {name}')
    _git(other, 'push', '--quiet', 'origin', 'main')


def _rebase_in_progress(store: Path) -> bool:
    git_dir = store / '.git'
    return any(
        (git_dir / state).exists()
        for state in ('rebase-merge', 'rebase-apply')
    )


def test_load_pulls_when_both_machines_have_committed(
    harness: SyncHarness,
) -> None:
    """The reported bug: --ff-only refused every diverged store."""
    remote = _git_backed_store(harness)
    _other_machine_pushes(harness, remote, 'some/token', 'from-there\n')
    harness.write_store_entry('some/other', 'from-here\n')
    _commit_store(harness, 'local work')

    harness.run('load')

    assert harness.store_entry('some/token') == 'from-there\n'
    assert harness.store_entry('some/other') == 'from-here\n'
    assert not _rebase_in_progress(harness.store)


def test_load_surfaces_the_entry_the_other_machine_pushed(
    harness: SyncHarness,
) -> None:
    """A pull that never lands is the symptom the user actually sees."""
    remote = _git_backed_store(harness)
    _other_machine_pushes(
        harness,
        remote,
        'manifest',
        MANIFEST + 'some/token:.token\n',
    )
    _other_machine_pushes(harness, remote, 'some/token', 'newest-value\n')
    harness.write_store_entry('some/other', 'from-here\n')
    _commit_store(harness, 'local work')

    harness.run('load')

    assert (harness.repo / '.token').read_text() == 'newest-value\n'


def test_save_pulls_before_pushing(harness: SyncHarness) -> None:
    """Otherwise the push is rejected the moment the stores diverge."""
    remote = _git_backed_store(harness)
    _other_machine_pushes(harness, remote, 'some/token', 'from-there\n')
    harness.queue.write_text(_queue('Added Here'))

    harness.run('save')

    assert harness.store_entry('some/token') == 'from-there\n'


def test_conflicting_pull_fails_loudly_and_leaves_store_usable(
    harness: SyncHarness,
) -> None:
    """A half-finished rebase would strand later inserts on a detached HEAD."""
    remote = _git_backed_store(harness)
    _other_machine_pushes(harness, remote, 'some/token', 'from-there\n')
    harness.write_store_entry('some/token', 'from-here\n')
    _commit_store(harness, 'local edit of the same entry')

    result = harness.run('load', check=False)

    assert result.returncode != 0
    assert 'conflict' in result.stderr.lower()
    assert not _rebase_in_progress(harness.store)


def test_load_keeps_local_items_the_store_has_not_seen(
    harness: SyncHarness,
) -> None:
    """The reported bug: a load used to replace .queue outright."""
    harness.queue.write_text(_queue('Added Here'))
    harness.write_store_entry('queue/active', _queue('Added There'))

    harness.run('load')

    assert _titles(harness.queue.read_text()) == [
        'Added Here',
        'Added There',
    ]


def test_save_keeps_items_the_other_machine_pushed(
    harness: SyncHarness,
) -> None:
    harness.queue.write_text(_queue('Added Here'))
    harness.write_store_entry('queue/active', _queue('Added There'))

    harness.run('save')

    assert _titles(harness.store_entry('queue/active')) == [
        'Added Here',
        'Added There',
    ]


def test_load_drops_items_completed_on_the_other_machine(
    harness: SyncHarness,
) -> None:
    """Proves .queue-complete reconciles before .queue, not manifest order."""
    harness.queue.write_text(_queue('Keep', 'Done There'))
    harness.complete.write_text('# Completed\n\n')
    harness.write_store_entry('queue/active', _queue('Keep'))
    harness.write_store_entry(
        'queue/complete',
        '# Completed\n\n## Done There\n- Completed: 2026-01-01 01:00:00\n\n'
        'body\n\n---\n',
    )

    harness.run('load')

    assert _titles(harness.queue.read_text()) == ['Keep']
    assert 'Done There' in harness.complete.read_text()


def test_repeated_sync_stops_rewriting_the_store(
    harness: SyncHarness,
) -> None:
    """Order churn would mean a new encrypted blob on every single push."""
    harness.queue.write_text(_queue('Added Here'))
    harness.write_store_entry('queue/active', _queue('Added There'))

    harness.run('save')
    settled = harness.store_entry('queue/active')

    harness.run('load')
    harness.run('save')

    assert harness.store_entry('queue/active') == settled
    assert harness.queue.read_text() == settled


def test_missing_skill_tree_fails_loudly_not_with_a_python_traceback(
    harness: SyncHarness,
) -> None:
    shutil.rmtree(harness.skill_tree)
    harness.queue.write_text(_queue('Added Here'))
    harness.write_store_entry('queue/active', _queue('Added There'))

    result = harness.run('load', check=False)

    assert result.returncode != 0
    assert 'skill-tree' in result.stderr.lower()


def test_non_merge_entries_are_still_copied_verbatim(
    harness: SyncHarness,
) -> None:
    harness.write_store_entry('manifest', MANIFEST + 'some/token:.token\n')
    harness.write_store_entry('some/token', 'secret-value\n')

    harness.run('load')

    assert (harness.repo / '.token').read_text() == 'secret-value\n'


def test_home_path_resolves_under_home_regardless_of_repo(
    harness: SyncHarness,
) -> None:
    """Not just the queue -- any ~/-prefixed entry escapes the repo root."""
    harness.write_store_entry(
        'manifest',
        MANIFEST + 'some/dotfile:~/.some-dotfile\n',
    )
    harness.write_store_entry('some/dotfile', 'from-store\n')

    harness.run('load')

    assert (harness.home / '.some-dotfile').read_text() == 'from-store\n'
    assert not (harness.repo / '.some-dotfile').exists()


def test_home_path_saves_from_home_regardless_of_repo(
    harness: SyncHarness,
) -> None:
    (harness.home / '.some-dotfile').write_text('from-disk\n')
    harness.write_store_entry(
        'manifest',
        MANIFEST + 'some/dotfile:~/.some-dotfile\n',
    )

    harness.run('save')

    assert harness.store_entry('some/dotfile') == 'from-disk\n'


@pytest.mark.parametrize('malformed', ['~foo', '~', '~/'])
def test_malformed_home_path_fails_loudly(
    harness: SyncHarness,
    malformed: str,
) -> None:
    harness.write_store_entry(
        'manifest',
        MANIFEST + f'some/dotfile:{malformed}\n',
    )

    result = harness.run('load', check=False)

    assert result.returncode != 0
    assert 'home path' in result.stderr.lower()


ANCHORED_MANIFEST = MANIFEST + 'app/env:@sibling/.env\n'


def test_anchored_path_loads_into_the_sibling_repo(
    harness: SyncHarness,
) -> None:
    """The reported bug: a repo moved out, so a relative path missed it."""
    sibling = harness.install_sibling('sibling')
    harness.write_store_entry('manifest', ANCHORED_MANIFEST)
    harness.write_store_entry('app/env', 'TOKEN=from-store\n')

    harness.run('load')

    assert (sibling / '.env').read_text() == 'TOKEN=from-store\n'
    assert not (harness.repo / 'sibling').exists()


def test_anchored_path_saves_from_the_sibling_repo(
    harness: SyncHarness,
) -> None:
    sibling = harness.install_sibling('sibling')
    (sibling / '.env').write_text('TOKEN=from-disk\n')
    harness.write_store_entry('manifest', ANCHORED_MANIFEST)

    harness.run('save')

    assert harness.store_entry('app/env') == 'TOKEN=from-disk\n'


def test_home_var_beats_projects_dir(
    harness: SyncHarness,
    tmp_path: Path,
) -> None:
    harness.install_sibling('sibling')
    elsewhere = tmp_path / 'checkouts' / 'sibling'
    elsewhere.mkdir(parents=True)
    harness.write_store_entry('manifest', ANCHORED_MANIFEST)
    harness.write_store_entry('app/env', 'TOKEN=from-store\n')

    harness.run('load', extra_env={'SIBLING_HOME': str(elsewhere)})

    assert (elsewhere / '.env').read_text() == 'TOKEN=from-store\n'
    assert not (harness.projects / 'sibling' / '.env').exists()


@pytest.mark.parametrize(
    ('action', 'extra_env'),
    [
        ('load', {}),
        ('save', {}),
        ('load', {'SIBLING_HOME': '/nonexistent/sibling'}),
    ],
)
def test_uninstalled_anchor_is_skipped_not_written(
    harness: SyncHarness,
    action: str,
    extra_env: dict[str, str],
) -> None:
    """A machine missing that repo must sync everything else and say so."""
    harness.queue.write_text(_queue('Untouched'))
    harness.write_store_entry('manifest', ANCHORED_MANIFEST)
    harness.write_store_entry('app/env', 'TOKEN=from-store\n')

    result = harness.run(action, extra_env=extra_env)

    assert 'not installed' in result.stdout
    assert not (harness.repo / 'sibling').exists()
    assert not (harness.repo / '@sibling').exists()
    assert _titles(harness.queue.read_text()) == ['Untouched']


def test_installed_anchor_with_no_file_reports_missing(
    harness: SyncHarness,
) -> None:
    """An empty checkout is a different problem from an absent one."""
    harness.install_sibling('sibling')
    harness.write_store_entry('manifest', ANCHORED_MANIFEST)

    result = harness.run('save')

    assert 'missing' in result.stdout
    assert 'not installed' not in result.stdout


def test_malformed_anchor_fails_loudly(harness: SyncHarness) -> None:
    harness.install_sibling('sibling')
    harness.write_store_entry('manifest', MANIFEST + 'app/env:@sibling\n')

    result = harness.run('load', check=False)

    assert result.returncode != 0
    assert 'anchor' in result.stderr.lower()


def test_anchored_merge_path_merges_in_place(harness: SyncHarness) -> None:
    """Merge handlers must use the resolved path, not the dotfiles root."""
    sibling = harness.install_sibling('sibling')
    (sibling / 'queue').write_text(_queue('Added Here'))
    (sibling / 'queue-complete').write_text('# Completed\n\n')
    harness.write_store_entry('manifest', 'app/queue:@sibling/queue\n')
    harness.write_store_entry('app/queue', _queue('Added There'))

    harness.run('load')

    assert _titles((sibling / 'queue').read_text()) == [
        'Added Here',
        'Added There',
    ]
    assert not (harness.repo / 'queue').exists()
