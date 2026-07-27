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
*)
    exit 0
    ;;
esac
"""

# .queue deliberately precedes .queue-complete: the tombstones have to be
# reconciled first regardless of what order the manifest lists them in.
MANIFEST = 'queue/active:.queue\nqueue/complete:.queue-complete\n'


class SyncHarness:
    """A throwaway repo plus fake store to run secrets.sh against."""

    def __init__(self, root: Path) -> None:
        self.repo = root / 'repo'
        self.store = root / 'store'
        self.entries = root / 'entries'
        self.bin = root / 'bin'
        self.queue = self.repo / '.queue'
        self.complete = self.repo / '.queue-complete'

    def run(self, action: str) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            'PATH': f'{self.bin}{os.pathsep}{os.environ["PATH"]}',
            'STUB_STORE': str(self.entries),
            'PASSWORD_STORE_DIR': str(self.store),
        }
        return subprocess.run(  # noqa: S603
            [str(self.repo / 'scripts' / 'secrets.sh'), action],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

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
    for script in ('secrets.sh', 'queue.py'):
        shutil.copy(SCRIPTS_DIR / script, setup.repo / 'scripts' / script)
    (setup.repo / 'scripts' / 'secrets.sh').chmod(0o755)
    subprocess.run(  # noqa: S603
        [GIT, 'init', '--quiet'],
        cwd=setup.repo,
        check=True,
        capture_output=True,
    )

    setup.store.mkdir()
    setup.bin.mkdir()
    fake_pass = setup.bin / 'pass'
    fake_pass.write_text(STUB_SCRIPT)
    fake_pass.chmod(0o755)

    setup.entries.mkdir()
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


def test_non_merge_entries_are_still_copied_verbatim(
    harness: SyncHarness,
) -> None:
    harness.write_store_entry('manifest', MANIFEST + 'some/token:.token\n')
    harness.write_store_entry('some/token', 'secret-value\n')

    harness.run('load')

    assert (harness.repo / '.token').read_text() == 'secret-value\n'
