"""Integration tests for bin/skill-audit.sh.

skill-audit is a sourced shell function, so each test sources it into a
throwaway bash process and calls it directly rather than executing the file.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

BIN_DIR = Path(__file__).parent.parent / 'bin'
SKILL_AUDIT = BIN_DIR / 'skill-audit.sh'
BASH = shutil.which('bash') or 'bash'


class AuditHarness:
    """A throwaway repo skills dir plus global skills dir."""

    def __init__(self, root: Path) -> None:
        self.repo_skills = root / 'dotfiles' / '.claude' / 'skills'
        self.global_skills = root / 'global' / 'skills'
        self.repo_skills.mkdir(parents=True)
        self.global_skills.mkdir(parents=True)

    def add_repo_skill(self, name: str, body: str = 'body') -> Path:
        skill_dir = self.repo_skills / name
        skill_dir.mkdir()
        (skill_dir / 'SKILL.md').write_text(body)
        return skill_dir

    def add_global_skill(self, name: str, body: str = 'body') -> Path:
        skill_dir = self.global_skills / name
        skill_dir.mkdir()
        (skill_dir / 'SKILL.md').write_text(body)
        return skill_dir

    def symlink_global(self, name: str, target: Path) -> Path:
        link = self.global_skills / name
        link.symlink_to(target)
        return link

    def run(
        self,
        args: list[str],
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            'DOTFILES_DIR': str(self.repo_skills.parent.parent),
            'CLAUDE_GLOBAL_SKILLS_DIR': str(self.global_skills),
        }
        command = f'source "{SKILL_AUDIT}"; skill-audit "$@"'
        return subprocess.run(  # noqa: S603
            [BASH, '-c', command, 'skill-audit', *args],
            env=env,
            capture_output=True,
            text=True,
            input=input_text,
            check=False,
        )


@pytest.fixture
def harness(tmp_path: Path) -> AuditHarness:
    return AuditHarness(tmp_path)


def test_reports_missing_skill(harness: AuditHarness) -> None:
    harness.add_repo_skill('foo')

    result = harness.run([])

    assert 'MISSING   foo' in result.stdout


def test_reports_in_sync_skill(harness: AuditHarness) -> None:
    harness.add_repo_skill('foo', body='same')
    harness.add_global_skill('foo', body='same')

    result = harness.run([])

    assert 'OK        foo  (in sync)' in result.stdout


def test_reports_stale_skill(harness: AuditHarness) -> None:
    harness.add_repo_skill('foo', body='new content')
    harness.add_global_skill('foo', body='old content')

    result = harness.run([])

    assert 'STALE     foo' in result.stdout


def test_reports_in_sync_when_symlinked_to_repo(
    harness: AuditHarness,
) -> None:
    source = harness.add_repo_skill('foo')
    harness.symlink_global('foo', source)

    result = harness.run([])

    assert 'OK        foo  (symlinked to repo)' in result.stdout


def test_reports_external_symlink(harness: AuditHarness) -> None:
    harness.add_repo_skill('foo')
    other_repo_skill = harness.global_skills.parent / 'elsewhere'
    other_repo_skill.mkdir()
    harness.symlink_global('foo', other_repo_skill)

    result = harness.run([])

    assert 'EXTERNAL  foo' in result.stdout
    assert 'not this repo -- skipped' in result.stdout


def test_reports_orphan_global_skill(harness: AuditHarness) -> None:
    harness.add_global_skill('untracked')

    result = harness.run([])

    assert 'ORPHAN    untracked' in result.stdout


def test_does_not_flag_external_symlink_orphan_as_untracked(
    harness: AuditHarness,
) -> None:
    other_repo_skill = harness.global_skills.parent / 'elsewhere'
    other_repo_skill.mkdir()
    harness.symlink_global('backlog', other_repo_skill)

    result = harness.run([])

    assert 'EXTERNAL  backlog' in result.stdout
    assert 'ORPHAN    backlog' not in result.stdout


def test_sync_copies_missing_skill_with_yes_flag(
    harness: AuditHarness,
) -> None:
    harness.add_repo_skill('foo', body='new')

    result = harness.run(['sync', '--yes'])

    global_copy = harness.global_skills / 'foo' / 'SKILL.md'
    assert global_copy.read_text() == 'new'
    assert 'Synced foo' in result.stdout


def test_sync_overwrites_stale_skill_with_yes_flag(
    harness: AuditHarness,
) -> None:
    harness.add_repo_skill('foo', body='new content')
    harness.add_global_skill('foo', body='old content')

    harness.run(['sync', '--yes'])

    global_copy = harness.global_skills / 'foo' / 'SKILL.md'
    assert global_copy.read_text() == 'new content'


def test_sync_without_confirmation_leaves_missing_skill_untouched(
    harness: AuditHarness,
) -> None:
    harness.add_repo_skill('foo')

    harness.run(['sync'], input_text='n\n')

    assert not (harness.global_skills / 'foo').exists()


def test_sync_scopes_to_single_named_skill(harness: AuditHarness) -> None:
    harness.add_repo_skill('foo')
    harness.add_repo_skill('bar')

    harness.run(['sync', 'foo', '--yes'])

    assert (harness.global_skills / 'foo').exists()
    assert not (harness.global_skills / 'bar').exists()


def test_sync_leaves_repo_symlinked_skill_untouched(
    harness: AuditHarness,
) -> None:
    source = harness.add_repo_skill('foo')
    link = harness.symlink_global('foo', source)

    harness.run(['sync', '--yes'])

    assert link.is_symlink()
    assert link.resolve() == source.resolve()
