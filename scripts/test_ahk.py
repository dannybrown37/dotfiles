"""Tests for the AutoHotkey scripts in ahk/.

The trigger checks are plain text parsing and run everywhere. The rest drive
the real AutoHotkey v2 interpreter, so they only run under WSL on a machine
that has it installed.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
AHK_DIR = REPO / 'ahk'
AHK_EXE = Path('/mnt/c/Program Files/AutoHotkey/v2/AutoHotkey64.exe')
HOTSTRING_TRIGGER = re.compile(r'^:([^:]*):(,,[^:]+)::', re.MULTILINE)
ALIAS_NAME = re.compile(r'^\s*alias\s+([\w.-]+)=', re.MULTILINE)
DYNAMIC_ALIAS_NAMES = {'song', 'sorn'}

requires_ahk = pytest.mark.skipif(
    not AHK_EXE.exists(),
    reason='AutoHotkey v2 not installed',
)


def hotstring_triggers() -> dict[str, str]:
    text = (AHK_DIR / 'hotstrings.ahk').read_text()
    return {
        trigger: options
        for options, trigger in HOTSTRING_TRIGGER.findall(text)
    }


def alias_triggers() -> set[str]:
    text = (REPO / 'config' / '.bash_aliases').read_text()
    return {
        f',,{name}'
        for name in ALIAS_NAME.findall(text)
        if name not in DYNAMIC_ALIAS_NAMES
    }


def windows_path(path: Path) -> str:
    return subprocess.run(  # noqa: S603
        ['/usr/bin/wslpath', '-w', str(path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def run_ahk(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(AHK_EXE), '/ErrorStdOut', *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


STAR_TRIGGERS = sorted(
    trigger
    for trigger, options in hotstring_triggers().items()
    if '*' in options
)


def test_static_hotstrings_fire_without_end_char() -> None:
    assert STAR_TRIGGERS, (
        'expected the static ,, hotstrings to use the * option'
    )


@pytest.mark.parametrize('star_trigger', STAR_TRIGGERS)
def test_star_trigger_does_not_shadow_a_longer_trigger(
    star_trigger: str,
) -> None:
    all_triggers = set(hotstring_triggers()) | alias_triggers()
    shadowed = sorted(
        t
        for t in all_triggers
        if t != star_trigger and t.startswith(star_trigger)
    )
    assert not shadowed, f'{star_trigger} fires before {shadowed} can be typed'


@requires_ahk
def test_text_library_unit_tests() -> None:
    result = run_ahk(windows_path(AHK_DIR / 'tests' / 'test_text.ahk'))
    assert result.returncode == 0, result.stdout + result.stderr


@requires_ahk
def test_main_script_validates_without_warnings() -> None:
    result = run_ahk('/validate', windows_path(AHK_DIR / 'main.ahk'))
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (result.stdout + result.stderr).strip()
