"""Open a URL: $BROWSER, else explorer.exe on WSL, else xdg-open."""

import os
import platform
import shlex
import subprocess
from collections.abc import Mapping


def running_on_wsl() -> bool:
    return 'microsoft' in platform.release().lower()


def browser_command(
    url: str,
    env: Mapping[str, str],
    *,
    is_wsl: bool,
) -> list[str]:
    if not url.startswith('https://'):
        msg = f'refusing to open a non-https URL: {url!r}'
        raise ValueError(msg)
    browser = shlex.split(env.get('BROWSER', ''))
    if browser:
        return [*browser, url]
    return ['explorer.exe' if is_wsl else 'xdg-open', url]


def open_url(url: str) -> None:
    subprocess.run(  # noqa: S603
        browser_command(url, os.environ, is_wsl=running_on_wsl()),
        capture_output=True,
        check=False,
    )
