"""Answer an agent's folder-trust dialog for a worktree fleet just made.

Both CLIs ask again for every new folder, so each agent would stop on a
dialog before doing anything. Fleet answers it only when the dialog names
the exact worktree it created and the repo it came from is already trusted
in Claude's or Copilot's own records. Anything else is left to the user.
"""

import json
import re
import time
from enum import StrEnum
from pathlib import Path

from fleet.store import AgentRecord, Store
from fleet.tmux import Tmux

CLAUDE_STATE = Path.home() / '.claude.json'
COPILOT_CONFIG = Path.home() / '.copilot' / 'config.json'
TRUST_PROMPTS = (
    'Yes, I trust this folder',
    'Do you trust the files in this folder',
)
# Copilot's "1. Yes" trusts this session only; never pick "remember".
YES_OPTION = re.compile(r'^\W*(Yes, I trust this folder|1\. Yes)\W*$')
# The cursor both CLIs draw on the chosen option (U+276F, not '>').
SELECTED = '❯'  # noqa: RUF001
TRUST_WAIT_SECONDS = 15.0
POLL_SECONDS = 0.3
MAX_KEYPRESSES = 4


class TrustKey(StrEnum):
    UP = 'Up'
    DOWN = 'Down'
    ENTER = 'Enter'


def without_borders(line: str) -> str:
    """Copilot draws the path inside a box inside a box: `│ │ path │ │`."""
    return line.strip(' │')


def option_lines(screen: str) -> list[tuple[bool, str]]:
    options = []
    for line in screen.splitlines():
        cleaned = without_borders(line)
        if not cleaned:
            continue
        selected = cleaned.startswith(SELECTED)
        text = cleaned.removeprefix(SELECTED).strip()
        if YES_OPTION.match(text) or re.match(r'^(\d\.\s|No\b)', text):
            options.append((selected, text))
    return options


def names_worktree(screen: str, worktree: str) -> bool:
    """The path must stand alone on its line, so a parent never matches."""
    return any(
        without_borders(line) == worktree for line in screen.splitlines()
    )


def trust_dialog_key(screen: str, worktree: str) -> TrustKey | None:
    if not any(prompt in screen for prompt in TRUST_PROMPTS):
        return None
    if not names_worktree(screen, worktree):
        return None
    options = option_lines(screen)
    yes_index = next(
        (i for i, (_, text) in enumerate(options) if YES_OPTION.match(text)),
        None,
    )
    selected_index = next(
        (i for i, (selected, _) in enumerate(options) if selected),
        None,
    )
    if yes_index is None or selected_index is None:
        return None
    if selected_index == yes_index:
        return TrustKey.ENTER
    return TrustKey.DOWN if selected_index < yes_index else TrustKey.UP


def read_jsonc(path: Path) -> dict[str, object]:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return {}
    try:
        data = json.loads(
            '\n'.join(
                line for line in lines if not line.lstrip().startswith('//')
            ),
        )
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def is_within(path: Path, folder: str) -> bool:
    return path == Path(folder) or Path(folder) in path.parents


def source_is_trusted(
    root: Path,
    claude_state: Path = CLAUDE_STATE,
    copilot_config: Path = COPILOT_CONFIG,
) -> bool:
    """Read-only, and only the trust keys: these files also hold tokens."""
    projects = read_jsonc(claude_state).get('projects') or {}
    if isinstance(projects, dict):
        entry = projects.get(str(root)) or {}
        if (
            isinstance(entry, dict)
            and entry.get('hasTrustDialogAccepted') is True
        ):
            return True
    folders = read_jsonc(copilot_config).get('trustedFolders') or []
    return isinstance(folders, list) and any(
        is_within(root, str(f)) for f in folders
    )


def answer_trust_dialog(
    tmux: Tmux,
    store: Store,
    record: AgentRecord,
    worktree: str,
) -> bool:
    """Wait for the agent's first hook or its trust dialog, whichever comes."""
    deadline = time.monotonic() + TRUST_WAIT_SECONDS
    presses = 0
    window_id = record.window_id
    while time.monotonic() < deadline and presses <= MAX_KEYPRESSES:
        if store.read_state(record.name, record.launch_id) is not None:
            return False
        key = trust_dialog_key(
            tmux.capture(window_id, lines=40, color=False),
            worktree,
        )
        if key is not None:
            tmux.run('send-keys', '-t', window_id, key.value)
            presses += 1
            if key is TrustKey.ENTER:
                return True
        time.sleep(POLL_SECONDS)
    return False
