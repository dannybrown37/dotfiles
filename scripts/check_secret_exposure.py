#!/usr/bin/env python3
"""Block Bash/Read tool calls that would put a secret into the transcript.

Wired as a PreToolUse hook. A hook can stop the call before it runs, which
is the only place raw secrets can be kept out of the conversation history --
once `cat config/.secrets` or `echo $GITHUB_TOKEN` executes, its output is
already part of the transcript.

This is a heuristic blocklist, not a parser: it pattern-matches the command
text rather than fully understanding shell semantics, so it can be worked
around on purpose. It exists to catch the ordinary, first-instinct commands
that caused the incidents this guards against.
"""

import json
import os
import re
import shlex
import sys
from pathlib import Path

BLOCK_EXIT_CODE = 2
SKIP_ENV_VAR = 'SECRET_GUARD_SKIP'

SECRET_NAME_PATTERN = re.compile(
    r'TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|(?:^|_)KEY(?:_|$)|(?:^|_)PAT(?:_|$)',
    re.IGNORECASE,
)
VAR_REFERENCE_PATTERN = re.compile(r'\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?')
COMMAND_SEGMENT_SPLIT_PATTERN = re.compile(r'&&|\|\||[;|\n]')

ENV_DUMP_COMMANDS = {'env', 'printenv', 'set'}
PRINT_COMMANDS = {'echo', 'printf', 'print'}
FILE_READ_COMMANDS = {
    'cat',
    'less',
    'more',
    'bat',
    'head',
    'tail',
    'nl',
    'strings',
    'xxd',
    'od',
    'grep',
    'egrep',
    'fgrep',
    'rg',
    'ag',
    'sed',
    'awk',
}

SECRET_FILE_EXACT_NAMES = {'.secrets', '.secrets.bak', 'secrets.ahk'}
DOTENV_PREFIX = '.env'

FAILURE_HEADER = (
    'Blocked: this command would put a secret directly into the '
    'conversation transcript. Check the value indirectly (length, hash, '
    "whether it's set) instead of printing it -- see "
    'scripts/git_auth_doctor.sh (token_fingerprint) for the pattern. Set '
    f'{SKIP_ENV_VAR}=1 to bypass for a genuine one-off need.'
)


def read_payload(raw: str) -> dict[str, object]:
    """Parse the PreToolUse hook's stdin JSON, tolerating bad input."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def is_secret_file(path_str: str) -> bool:
    name = Path(path_str).name
    if name in SECRET_FILE_EXACT_NAMES:
        return True
    return name == DOTENV_PREFIX or name.startswith(f'{DOTENV_PREFIX}.')


def _command_segments(command: str) -> list[str]:
    return [
        segment.strip()
        for segment in COMMAND_SEGMENT_SPLIT_PATTERN.split(command)
        if segment.strip()
    ]


def _tokenize(segment: str) -> list[str]:
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def _env_dump_reason(base: str, args: list[str]) -> str | None:
    if base == 'env':
        runs_a_command = any(
            '=' not in arg and not arg.startswith('-') for arg in args
        )
        return (
            None
            if runs_a_command
            else 'bare `env` dumps the entire environment'
        )
    if base == 'printenv':
        names = [arg for arg in args if not arg.startswith('-')]
        if not names:
            return 'bare `printenv` dumps the entire environment'
        for name in names:
            if SECRET_NAME_PATTERN.search(name):
                return f'`printenv {name}` looks like a secret'
        return None
    if base == 'set':
        return None if args else 'bare `set` dumps every shell variable'
    return None


def _echoed_secret_var(segment: str) -> str | None:
    for match in VAR_REFERENCE_PATTERN.finditer(segment):
        name = match.group(1)
        if SECRET_NAME_PATTERN.search(name):
            return name
    return None


def detect_bash_risk(command: str) -> str | None:
    """Return a human-readable reason the command is risky, or None."""
    for segment in _command_segments(command):
        tokens = _tokenize(segment)
        if not tokens:
            continue
        base = Path(tokens[0]).name
        args = tokens[1:]

        if base in ENV_DUMP_COMMANDS:
            reason = _env_dump_reason(base, args)
            if reason:
                return reason

        if base in PRINT_COMMANDS:
            name = _echoed_secret_var(segment)
            if name:
                return f'echoes ${name}, which looks like a secret'

        if base in FILE_READ_COMMANDS:
            for token in args:
                if is_secret_file(token):
                    return f'reads {token} directly, which may contain secrets'

    return None


def main(raw_payload: str) -> int:
    if os.environ.get(SKIP_ENV_VAR):
        return 0

    payload = read_payload(raw_payload)
    tool_name = payload.get('tool_name')
    tool_input = payload.get('tool_input')
    if not isinstance(tool_input, dict):
        return 0

    reason = None
    if tool_name == 'Bash':
        command = tool_input.get('command')
        if isinstance(command, str):
            reason = detect_bash_risk(command)
    elif tool_name == 'Read':
        file_path = tool_input.get('file_path')
        if isinstance(file_path, str) and is_secret_file(file_path):
            reason = f'{file_path} may contain secrets'

    if reason is None:
        return 0

    print(FAILURE_HEADER, file=sys.stderr)
    print(f'Reason: {reason}', file=sys.stderr)
    return BLOCK_EXIT_CODE


if __name__ == '__main__':
    sys.exit(main(sys.stdin.read()))
