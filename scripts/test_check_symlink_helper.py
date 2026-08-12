"""Tests for scripts/check-symlink-helper.sh.

The hook scans a directory of install scripts, so every test writes a
throwaway `install/`-shaped tree and points the hook at it.
"""

import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).parent / 'check-symlink-helper.sh'
USAGE_ERROR = 2

HELPER = """\
#!/usr/bin/env bash
link_config() {
    ln -s "$1" "$2"
}
"""


class InstallDir:
    """A throwaway install/ directory to run the hook against."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.write('link_config.sh', HELPER)

    def write(self, name: str, content: str) -> None:
        (self.root / name).write_text(content)

    def run(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            ['bash', str(HOOK), str(self.root)],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
        )


@pytest.fixture
def install(tmp_path: Path) -> InstallDir:
    return InstallDir(tmp_path)


def test_passes_when_every_script_uses_the_helper(install: InstallDir) -> None:
    install.write(
        'thing.sh',
        '#!/usr/bin/env bash\nlink_config "${src}" "${dest}"\n',
    )

    result = install.run()

    assert result.returncode == 0


def test_is_silent_on_pass(install: InstallDir) -> None:
    install.write('thing.sh', '#!/usr/bin/env bash\nlink_config a b\n')

    result = install.run()

    assert result.stdout == ''
    assert result.stderr == ''


def test_blocks_a_raw_ln_s(install: InstallDir) -> None:
    install.write(
        'thing.sh',
        '#!/usr/bin/env bash\nln -s "${src}" "${HOME}/.thingrc"\n',
    )

    result = install.run()

    assert result.returncode == 1
    assert 'thing.sh:2' in result.stderr
    assert 'link_config' in result.stderr


@pytest.mark.parametrize(
    'command',
    [
        'ln -s a b',
        'ln -sf a b',
        'ln -sfn a b',
        'ln -nsf a b',
        'ln --symbolic a b',
        'sudo ln -s a b',
        'ln    -s    a b',
    ],
)
def test_blocks_every_symlink_invocation_spelling(
    install: InstallDir,
    command: str,
) -> None:
    install.write('thing.sh', f'#!/usr/bin/env bash\n{command}\n')

    assert install.run().returncode == 1


@pytest.mark.parametrize(
    'command',
    [
        'ln a b',
        'ln --help',
        'link_config a b',
    ],
)
def test_ignores_things_that_are_not_symlink_creation(
    install: InstallDir,
    command: str,
) -> None:
    install.write('thing.sh', f'#!/usr/bin/env bash\n{command}\n')

    assert install.run().returncode == 0


def test_exempts_the_file_that_defines_link_config(
    install: InstallDir,
) -> None:
    """The helper is the one place a raw ln -s belongs."""
    assert install.run().returncode == 0


def test_exemption_follows_the_helper_through_a_rename(
    tmp_path: Path,
) -> None:
    """Found by grepping for the definition, not by a hardcoded filename."""
    install = InstallDir(tmp_path)
    (tmp_path / 'link_config.sh').rename(tmp_path / 'renamed_helper.sh')

    assert install.run().returncode == 0


def test_allows_an_explicitly_marked_exception(install: InstallDir) -> None:
    install.write(
        'nvim.sh',
        '#!/usr/bin/env bash\n'
        'sudo ln -s /squashfs-root/AppRun /usr/bin/nvim'
        '  # allow-raw-symlink: root-owned system path, not a config link\n',
    )

    result = install.run()

    assert result.returncode == 0


def test_marker_only_exempts_its_own_line(install: InstallDir) -> None:
    install.write(
        'thing.sh',
        '#!/usr/bin/env bash\n'
        'ln -s /a /usr/bin/a  # allow-raw-symlink: fine\n'
        'ln -s "${src}" "${HOME}/.thingrc"\n',
    )

    result = install.run()

    assert result.returncode == 1
    assert 'thing.sh:3' in result.stderr
    assert 'thing.sh:2' not in result.stderr


def test_ignores_ln_inside_a_comment(install: InstallDir) -> None:
    install.write(
        'thing.sh',
        '#!/usr/bin/env bash\n'
        '# Every caller used to hand-roll its own ln -s.\n',
    )

    assert install.run().returncode == 0


def test_reports_every_offender_not_just_the_first(
    install: InstallDir,
) -> None:
    install.write('one.sh', '#!/usr/bin/env bash\nln -s a b\n')
    install.write('two.sh', '#!/usr/bin/env bash\nln -s c d\n')

    result = install.run()

    assert result.returncode == 1
    assert 'one.sh' in result.stderr
    assert 'two.sh' in result.stderr


def test_passes_on_an_empty_directory(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603
        ['bash', str(HOOK), str(tmp_path)],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0


def test_errors_on_a_missing_directory(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603
        ['bash', str(HOOK), str(tmp_path / 'nope')],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == USAGE_ERROR
    assert 'nope' in result.stderr
