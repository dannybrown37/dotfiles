"""Tests for fleet.browser: which command opens a URL."""

import pytest

from fleet.browser import browser_command

URL = 'https://example.test/a?b=1&c=2'


@pytest.mark.parametrize(
    ('env', 'is_wsl', 'expected'),
    [
        ({}, False, ['xdg-open', URL]),
        ({}, True, ['explorer.exe', URL]),
        ({'BROWSER': 'firefox'}, True, ['firefox', URL]),
        ({'BROWSER': 'wslview --x'}, False, ['wslview', '--x', URL]),
        ({'BROWSER': '  '}, False, ['xdg-open', URL]),
    ],
)
def test_browser_command(
    env: dict[str, str],
    is_wsl: bool,  # noqa: FBT001
    expected: list[str],
) -> None:
    assert browser_command(URL, env, is_wsl=is_wsl) == expected


@pytest.mark.parametrize(
    'url',
    ['http://example.test', 'javascript:alert(1)', 'file:///etc/passwd', '-x'],
)
def test_browser_command_only_opens_https(url: str) -> None:
    with pytest.raises(ValueError, match='https'):
        browser_command(url, {}, is_wsl=False)
