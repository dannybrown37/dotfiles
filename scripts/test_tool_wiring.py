"""Tests for the add-dotfiles-tooling skill's wiring checker.

Each test builds a throwaway repo skeleton with the five files the
checker inspects, optionally omitting one piece of wiring, then asserts
the checker notices exactly that omission.
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
CHECKER = REPO_ROOT / 'scripts' / 'check-tool-wiring.sh'

EXIT_FAILED_CHECKS = 1
EXIT_USAGE = 2

MAKEFILE = """\
.PHONY: help {phony}

help:
\t@echo "Developer Tools:"
{help_line}

{target_block}
"""

TARGET_BLOCK = 'widget:\n\tbash -c ". $(root_dir)/install/widget.sh"'

# Deliberately no '@doc' markers anywhere in this file's fixtures:
# sync-readme-commands.sh scans every file in scripts/, not just *.sh, and
# would scrape them into the README as if they were real commands.
STUBS = """\
# Passthrough stubs for third-party tools.

{stub_line}
zoxide() {{ command zoxide "$@"; }}
"""

AUDIT = """\
#!/usr/bin/env bash
{audit_line}
check "zoxide"  "zoxide --version"  "make bash"
"""

APT_PACKAGES = """\
#!/usr/bin/env bash
apt_packages=(
    curl
{apt_line}
    tmux
)
"""

# 'gadget' stands in for eza: no install/gadget.sh and not an apt package,
# but a shared install script builds it anyway.
BASH_INSTALL = """\
#!/usr/bin/env bash
if ! command -v gadget &>/dev/null; then
    cargo install gadget
fi
"""


def build_repo(root: Path, omit: str = '') -> None:
    """Write a fake dotfiles repo, leaving out one piece of wiring."""
    (root / 'install').mkdir(parents=True)
    (root / 'bin').mkdir()
    (root / 'scripts').mkdir()

    if omit != 'install':
        (root / 'install' / 'widget.sh').write_text(
            '#!/usr/bin/env bash\nset -euo pipefail\n',
        )

    (root / 'Makefile').write_text(
        MAKEFILE.format(
            phony='' if omit == 'phony' else 'widget',
            help_line=(
                ''
                if omit == 'help'
                else '\t@echo "  widget          Install widget"'
            ),
            target_block='' if omit == 'target' else TARGET_BLOCK,
        ),
    )

    (root / 'bin' / 'stubs.sh').write_text(
        STUBS.format(
            stub_line=(
                '' if omit == 'stub' else 'widget() { command widget "$@"; }'
            ),
        ),
    )

    (root / 'scripts' / 'dotfiles_audit.sh').write_text(
        AUDIT.format(
            audit_line=(
                ''
                if omit == 'audit'
                else 'check "widget"  "widget --version"  "make widget"'
            ),
        ),
    )

    (root / 'install' / 'apt_packages.sh').write_text(
        APT_PACKAGES.format(apt_line='    ripgrep'),
    )

    (root / 'install' / 'bash.sh').write_text(BASH_INSTALL)


def run_checker(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, 'DOTFILES_ROOT': str(root)}
    return subprocess.run(  # noqa: S603
        [str(CHECKER), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_fully_wired_dedicated_tool_passes(tmp_path: Path) -> None:
    build_repo(tmp_path)

    result = run_checker(tmp_path, 'widget')

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ('omit', 'expected_label'),
    [
        ('target', 'make target'),
        ('phony', '.PHONY entry'),
        ('help', 'make help entry'),
        ('stub', 'stubs.sh stub'),
        ('audit', 'audit entry'),
    ],
)
def test_missing_wiring_is_reported(
    tmp_path: Path,
    omit: str,
    expected_label: str,
) -> None:
    build_repo(tmp_path, omit=omit)

    result = run_checker(tmp_path, 'widget')
    output = result.stdout + result.stderr

    assert result.returncode == EXIT_FAILED_CHECKS, output
    assert expected_label in output


def test_apt_tool_skips_dedicated_install_checks(tmp_path: Path) -> None:
    build_repo(tmp_path)
    stubs = tmp_path / 'bin' / 'stubs.sh'
    stubs.write_text(
        stubs.read_text() + 'rg() { command rg "$@"; }\n',
    )

    result = run_checker(tmp_path, 'rg', '--apt-package', 'ripgrep')
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert 'n/a' in output


def test_apt_tool_missing_stub_fails(tmp_path: Path) -> None:
    build_repo(tmp_path)

    result = run_checker(tmp_path, 'rg', '--apt-package', 'ripgrep')
    output = result.stdout + result.stderr

    assert result.returncode == EXIT_FAILED_CHECKS, output
    assert 'stubs.sh stub' in output


def test_tool_installed_by_a_shared_script_is_recognised(
    tmp_path: Path,
) -> None:
    """eza-style tools: no dedicated script, built by install/bash.sh."""
    build_repo(tmp_path)
    stubs = tmp_path / 'bin' / 'stubs.sh'
    stubs.write_text(
        stubs.read_text() + 'gadget() { command gadget "$@"; }\n',
    )
    audit = tmp_path / 'scripts' / 'dotfiles_audit.sh'
    audit.write_text(
        audit.read_text() + 'check "gadget"  "gadget -V"  "make bash"\n',
    )

    result = run_checker(tmp_path, 'gadget')
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert 'bundled' in output
    assert 'bash.sh' in output


def test_no_stub_flag_skips_the_stub_requirement(tmp_path: Path) -> None:
    """Language runtimes deliberately have no passthrough stub."""
    build_repo(tmp_path, omit='stub')

    result = run_checker(tmp_path, 'widget', '--no-stub')
    output = result.stdout + result.stderr

    assert result.returncode == 0, output


def test_tool_with_no_install_path_at_all_fails(tmp_path: Path) -> None:
    build_repo(tmp_path, omit='install')

    result = run_checker(tmp_path, 'widget')
    output = result.stdout + result.stderr

    assert result.returncode == EXIT_FAILED_CHECKS, output
    assert 'install path' in output


def test_missing_tool_argument_is_a_usage_error(tmp_path: Path) -> None:
    build_repo(tmp_path)

    result = run_checker(tmp_path)

    assert result.returncode == EXIT_USAGE
    assert 'usage' in (result.stdout + result.stderr).lower()
