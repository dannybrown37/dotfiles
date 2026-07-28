"""Tests for scripts/check-privacy-terms.sh.

Builds a throwaway git repo with its own config/.secrets so nothing here
touches the real password-store-backed secrets file.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent
GIT = shutil.which('git') or 'git'


class PrivacyHookHarness:
    """A throwaway repo to run check-privacy-terms.sh against."""

    def __init__(self, root: Path) -> None:
        self.repo = root

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [GIT, *args],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        )

    def write_secrets(self, terms: list[str]) -> None:
        (self.repo / 'config').mkdir(parents=True, exist_ok=True)
        array = ' '.join(f'"{t}"' for t in terms)
        (self.repo / 'config' / '.secrets').write_text(
            f'PRIVACY_TERMS=({array})\n',
        )

    def stage_file(self, path: str, content: str) -> None:
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        self._git('add', path)

    def commit(self, message: str) -> None:
        self._git('commit', '--quiet', '-m', message)

    def run_hook(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            ['bash', str(SCRIPTS_DIR / 'check-privacy-terms.sh')],  # noqa: S607
            cwd=self.repo,
            check=False,
            capture_output=True,
            text=True,
        )


@pytest.fixture
def harness(tmp_path: Path) -> PrivacyHookHarness:
    setup = PrivacyHookHarness(tmp_path)
    subprocess.run(  # noqa: S603
        [GIT, 'init', '--quiet'],
        cwd=setup.repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(  # noqa: S603
        [GIT, 'config', 'user.email', 'test@example.com'],
        cwd=setup.repo,
        check=True,
    )
    subprocess.run(  # noqa: S603
        [GIT, 'config', 'user.name', 'Test'],
        cwd=setup.repo,
        check=True,
    )
    return setup


def test_blocks_commit_containing_a_privacy_term(
    harness: PrivacyHookHarness,
) -> None:
    harness.write_secrets(['AcmeCorp'])
    harness.stage_file('notes.txt', 'Meeting notes for AcmeCorp project.\n')

    result = harness.run_hook()

    assert result.returncode == 1
    assert 'AcmeCorp' in result.stderr
    assert 'notes.txt' in result.stderr


def test_match_is_case_insensitive(harness: PrivacyHookHarness) -> None:
    harness.write_secrets(['AcmeCorp'])
    harness.stage_file('notes.txt', 'talked to someone at acmecorp today\n')

    result = harness.run_hook()

    assert result.returncode == 1


def test_allows_commit_with_no_matching_terms(
    harness: PrivacyHookHarness,
) -> None:
    harness.write_secrets(['AcmeCorp'])
    harness.stage_file('notes.txt', 'unrelated content\n')

    result = harness.run_hook()

    assert result.returncode == 0


def test_no_op_when_privacy_terms_is_empty(
    harness: PrivacyHookHarness,
) -> None:
    harness.write_secrets([])
    harness.stage_file('notes.txt', 'AcmeCorp mentioned here\n')

    result = harness.run_hook()

    assert result.returncode == 0


def test_no_op_when_secrets_file_is_missing(
    harness: PrivacyHookHarness,
) -> None:
    harness.stage_file('notes.txt', 'AcmeCorp mentioned here\n')

    result = harness.run_hook()

    assert result.returncode == 0


def test_survives_a_secrets_file_ending_in_a_false_guarded_source(
    harness: PrivacyHookHarness,
) -> None:
    """Mirrors the real config/.secrets, whose last line is a bare.

    `[[ -f x ]] && . x` -- the false branch must not trip set -e.
    """
    (harness.repo / 'config').mkdir(parents=True, exist_ok=True)
    (harness.repo / 'config' / '.secrets').write_text(
        'PRIVACY_TERMS=("AcmeCorp")\n'
        '[[ -f /nonexistent/path/for/this/test ]] && . /nonexistent\n',
    )
    harness.stage_file('notes.txt', 'talked about AcmeCorp today\n')

    result = harness.run_hook()

    assert result.returncode == 1
    assert 'AcmeCorp' in result.stderr


def test_ignores_preexisting_occurrences_outside_the_diff(
    harness: PrivacyHookHarness,
) -> None:
    harness.write_secrets(['AcmeCorp'])
    harness.stage_file('notes.txt', 'line about AcmeCorp\nunrelated line\n')
    harness.commit('initial')

    harness.stage_file(
        'notes.txt',
        'line about AcmeCorp\nunrelated line, edited\n',
    )
    result = harness.run_hook()

    assert result.returncode == 0
