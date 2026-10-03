"""Tests for scripts/extras.sh, the opt-in tool picker.

Each test builds a throwaway install/extras/ directory of fake install
scripts, so nothing here installs anything real.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
EXTRAS = REPO_ROOT / 'scripts' / 'extras.sh'
BASH = shutil.which('bash') or '/bin/bash'
EXIT_USAGE = 2
ESCAPE = '\x1b'
RESET = f'{ESCAPE}[0m'
SOURCE_COLORS = {
    'mine': f'{ESCAPE}[1;35m',
    'runtime': f'{ESCAPE}[36m',
    'cargo': f'{ESCAPE}[33m',
    'gh': f'{ESCAPE}[34m',
    'apt': f'{ESCAPE}[32m',
}

EXTRA_SCRIPT = """\
#!/usr/bin/env bash
## @extra {binary} | {desc}
echo "ran {name}" >> "${{CALL_LOG}}"
"""


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    extras = tmp_path / 'install' / 'extras'
    extras.mkdir(parents=True)
    for name, binary, desc in [
        ('alpha', 'alpha-bin', 'First tool'),
        ('beta', 'beta', 'Second tool'),
    ]:
        (extras / f'{name}.sh').write_text(
            EXTRA_SCRIPT.format(name=name, binary=binary, desc=desc),
        )
    (extras / 'helper.sh').write_text('#!/usr/bin/env bash\n')
    return tmp_path


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    path = tmp_path / 'bin'
    path.mkdir()
    return path


def run_extras(
    root: Path,
    stub_bin: Path,
    *args: str,
    color_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    inherited = {
        key: value
        for key, value in os.environ.items()
        if key not in {'NO_COLOR', 'FORCE_COLOR'}
    }
    env = {
        **inherited,
        'DOTFILES_ROOT': str(root),
        'CALL_LOG': str(root / 'calls.log'),
        'PATH': f'{stub_bin}:/usr/bin:/bin',
        **(color_env or {}),
    }
    return subprocess.run(  # noqa: S603
        [BASH, str(EXTRAS), *args],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def calls(root: Path) -> list[str]:
    log = root / 'calls.log'
    return log.read_text().splitlines() if log.exists() else []


@pytest.mark.parametrize(
    ('installed', 'expected'),
    [
        ([], {'alpha': '·', 'beta': '·'}),
        (['alpha-bin'], {'alpha': '✓', 'beta': '·'}),
        (['alpha-bin', 'beta'], {'alpha': '✓', 'beta': '✓'}),
    ],
)
def test_list_marks_installed_by_binary(
    root: Path,
    stub_bin: Path,
    installed: list[str],
    expected: dict[str, str],
) -> None:
    for binary in installed:
        _write_executable(stub_bin / binary, '#!/bin/sh\n')

    result = run_extras(root, stub_bin, '--list')

    assert result.returncode == 0
    rows = {
        line.split()[1]: line.split()[0] for line in result.stdout.splitlines()
    }
    assert rows == expected


@pytest.mark.parametrize(
    ('gh_extensions', 'expected'),
    [
        ('', '·'),
        ('gh dash\tdlvhdr/gh-dash\tv4.26.0\n', '✓'),
        ('gh dashboard\tother/gh-dashboard\tv1.0.0\n', '·'),
    ],
)
def test_list_marks_gh_extension_installed_via_gh(
    root: Path,
    stub_bin: Path,
    gh_extensions: str,
    expected: str,
) -> None:
    (root / 'install' / 'extras' / 'gh-dash.sh').write_text(
        EXTRA_SCRIPT.format(
            name='gh-dash',
            binary='gh-dash',
            desc='Dashboard',
        ),
    )
    _write_executable(
        stub_bin / 'gh',
        f"#!/bin/sh\nprintf '{gh_extensions}'\n",
    )

    result = run_extras(root, stub_bin, '--list')

    rows = {
        line.split()[1]: line.split()[0] for line in result.stdout.splitlines()
    }
    assert rows['gh-dash'] == expected


def test_list_skips_scripts_without_header(root: Path, stub_bin: Path) -> None:
    result = run_extras(root, stub_bin, '--list')

    assert 'helper' not in result.stdout
    assert 'Second tool' in result.stdout


@pytest.mark.parametrize(
    ('body', 'source'),
    [
        ('## @mine\ngit clone https://example.com/tool\n', 'mine'),
        ('## @mine\n## @runtime\ncargo install tool\n', 'mine'),
        ('## @runtime\ncurl -fsSL https://example.com | sh\n', 'runtime'),
        ('sudo apt install -y build\ncargo install --locked tool\n', 'cargo'),
        ('gh extension install owner/gh-tool\n', 'gh'),
        ('sudo apt install -y tool\n', 'apt'),
        ('sudo apt-get install -y -qq tool\n', 'apt'),
        ('sudo apt install -y dep\ncurl -fsSLo t https://example.com\n', None),
        ('install_release_binary tool "https://example.com" 1.0\n', None),
        ('## needs cargo install and apt install\n', None),
        ('winget.exe install --id Tool\n', None),
    ],
)
def test_list_colors_name_by_source(
    root: Path,
    stub_bin: Path,
    body: str,
    source: str | None,
) -> None:
    (root / 'install' / 'extras' / 'tool.sh').write_text(
        EXTRA_SCRIPT.format(name='tool', binary='tool', desc='A tool') + body,
    )

    result = run_extras(
        root,
        stub_bin,
        '--list',
        color_env={'FORCE_COLOR': '1'},
    )

    row = next(line for line in result.stdout.splitlines() if 'A tool' in line)
    name = f'{"tool":<12}'
    colored = f'{SOURCE_COLORS[source]}{name}{RESET}' if source else name
    assert row == f'· {colored} A tool'


def test_colored_list_ends_with_legend(root: Path, stub_bin: Path) -> None:
    result = run_extras(
        root,
        stub_bin,
        '--list',
        color_env={'FORCE_COLOR': '1'},
    )

    legend = result.stdout.splitlines()[-1]
    for source, color in SOURCE_COLORS.items():
        assert f'{color}{source}{RESET}' in legend


@pytest.mark.parametrize(
    'color_env',
    [{}, {'NO_COLOR': '1'}, {'NO_COLOR': '1', 'FORCE_COLOR': '1'}],
)
def test_list_is_plain_without_color(
    root: Path,
    stub_bin: Path,
    color_env: dict[str, str],
) -> None:
    result = run_extras(root, stub_bin, '--list', color_env=color_env)

    assert result.stdout.splitlines() == [
        '· alpha        First tool',
        '· beta         Second tool',
    ]


def test_named_extras_run_their_scripts(root: Path, stub_bin: Path) -> None:
    result = run_extras(root, stub_bin, 'beta', 'alpha')

    assert result.returncode == 0
    assert calls(root) == ['ran beta', 'ran alpha']


@pytest.mark.parametrize(
    ('args', 'expected'),
    [
        (['alpha', 'lang'], ['ran lang', 'ran alpha']),
        (['beta', 'lang', 'alpha'], ['ran lang', 'ran beta', 'ran alpha']),
        (['alpha'], ['ran alpha']),
    ],
)
def test_runtimes_install_before_other_extras(
    root: Path,
    stub_bin: Path,
    args: list[str],
    expected: list[str],
) -> None:
    (root / 'install' / 'extras' / 'lang.sh').write_text(
        EXTRA_SCRIPT.format(name='lang', binary='lang', desc='A runtime')
        + '## @runtime\n',
    )

    result = run_extras(root, stub_bin, *args)

    assert result.returncode == 0
    assert calls(root) == expected


def test_unknown_name_fails_before_running_anything(
    root: Path,
    stub_bin: Path,
) -> None:
    result = run_extras(root, stub_bin, 'alpha', 'nope')

    assert result.returncode == EXIT_USAGE
    assert 'nope' in result.stderr
    assert calls(root) == []


def test_no_args_without_tty_prints_list_and_usage(
    root: Path,
    stub_bin: Path,
) -> None:
    result = run_extras(root, stub_bin)

    assert result.returncode == 0
    assert 'alpha' in result.stdout
    assert 'just extras <name>' in result.stdout
    assert calls(root) == []


@pytest.mark.parametrize('flag', ['-h', '--help'])
def test_help(root: Path, stub_bin: Path, flag: str) -> None:
    result = run_extras(root, stub_bin, flag)

    assert result.returncode == 0
    assert 'Usage' in result.stdout
