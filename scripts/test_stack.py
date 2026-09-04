"""Tests for scripts/stack.sh.

`gh` is stubbed on PATH so tests never hit GitHub.
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent
STACK = SCRIPTS_DIR / 'stack.sh'
EXIT_USAGE = 2

GH_STUB = """#!/usr/bin/env bash
echo "$*" >>"${GH_CALLS_FILE}"

if [[ "${1:-}" == "auth" && "${2:-}" == "status" ]]; then
    case "${GH_AUTH_MODE:-ok}" in
    ok)
        echo "Logged in to github.com as test-user"
        exit 0
        ;;
    fail)
        echo "not logged in"
        exit 1
        ;;
    esac
fi

if [[ "${1:-}" == "extension" && "${2:-}" == "list" ]]; then
    if [[ "${GH_STACK_INSTALLED:-1}" == "1" ]]; then
        printf 'gh stack\tgithub/gh-stack\tv9.9.9\n'
    fi
    exit 0
fi

if [[ "${1:-}" == "extension" && "${2:-}" == "install" ]]; then
    exit 0
fi

if [[ "${1:-}" == "extension" && "${2:-}" == "upgrade" ]]; then
    exit 0
fi

if [[ "${1:-}" == "stack" ]]; then
    exit 0
fi
"""


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    gh = bin_dir / 'gh'
    gh.write_text(GH_STUB)
    gh.chmod(0o755)
    return bin_dir


def run(
    stub_bin: Path,
    tmp_path: Path,
    args: list[str],
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    calls_file = tmp_path / 'gh_calls'
    calls_file.write_text('')
    env = {
        **os.environ,
        'PATH': f'{stub_bin}{os.pathsep}{os.environ["PATH"]}',
        'GH_CALLS_FILE': str(calls_file),
        **(env_overrides or {}),
    }
    result = subprocess.run(  # noqa: S603
        [str(STACK), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    result.calls = calls_file.read_text().splitlines()  # type: ignore[attr-defined]
    return result


def test_no_args_prints_help_and_usage_exit_code(
    stub_bin: Path,
    tmp_path: Path,
) -> None:
    result = run(stub_bin, tmp_path, [])
    assert result.returncode == EXIT_USAGE
    assert 'Usage:' in result.stdout


def test_version_reports_wrapper_and_extension_versions(
    stub_bin: Path,
    tmp_path: Path,
) -> None:
    result = run(stub_bin, tmp_path, ['--version'])
    assert result.returncode == 0
    assert 'stack wrapper 0.1.0 | gh-stack v9.9.9' in result.stdout


@pytest.mark.parametrize(
    ('args', 'expected_call'),
    [
        (['start', 'feature-auth'], 'stack init feature-auth'),
        (['next', 'feature-api'], 'stack add feature-api'),
        (['show', '--short'], 'stack view --short'),
        (['publish', '--auto'], 'stack submit --auto'),
        (['ship'], 'stack submit --open'),
        (['sync'], 'stack sync'),
        (['land', '3'], 'stack merge 3'),
        (['view', '--json'], 'stack view --json'),
    ],
)
def test_shortcuts_and_passthrough_map_to_gh_stack(
    stub_bin: Path,
    tmp_path: Path,
    args: list[str],
    expected_call: str,
) -> None:
    result = run(stub_bin, tmp_path, args)
    assert result.returncode == 0
    assert any(call == expected_call for call in result.calls)  # type: ignore[attr-defined]


def test_doctor_fails_loudly_when_not_logged_in(
    stub_bin: Path,
    tmp_path: Path,
) -> None:
    result = run(stub_bin, tmp_path, ['doctor'], {'GH_AUTH_MODE': 'fail'})
    assert result.returncode == 1
    assert "gh auth: run 'gh auth login'" in result.stderr


def test_requires_stack_extension_for_stack_commands(
    stub_bin: Path,
    tmp_path: Path,
) -> None:
    result = run(stub_bin, tmp_path, ['show'], {'GH_STACK_INSTALLED': '0'})
    assert result.returncode == 1
    assert 'gh-stack extension not installed' in result.stderr
