#!/usr/bin/env python3
"""Block Bash/Read/Grep tool calls that would put a secret into the transcript.

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
    'base64',
    'cut',
}

# `pass <entry>` is `pass show <entry>`, so allow only subcommands that never
# print a decrypted value.
PASS_SAFE_SUBCOMMANDS = {
    'ls',
    'list',
    'find',
    'init',
    'insert',
    'add',
    'edit',
    'rm',
    'remove',
    'delete',
    'mv',
    'rename',
    'cp',
    'copy',
    'git',
    'help',
    'version',
}
PASS_CLIP_FLAGS = {'-c', '--clip'}
GH_SHOW_TOKEN_FLAGS = {'-t', '--show-token'}

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


def _secret_name_reason(base: str, names: list[str]) -> str | None:
    for name in names:
        if SECRET_NAME_PATTERN.search(name):
            return f'`{base} {name}` looks like a secret'
    return None


def _non_flags(args: list[str]) -> list[str]:
    return [arg for arg in args if not arg.startswith('-')]


def _env_reason(args: list[str]) -> str | None:
    runs_a_command = any('=' not in arg for arg in _non_flags(args))
    return (
        None if runs_a_command else 'bare `env` dumps the entire environment'
    )


def _printenv_reason(args: list[str]) -> str | None:
    names = _non_flags(args)
    if not names:
        return 'bare `printenv` dumps the entire environment'
    return _secret_name_reason('printenv', names)


def _set_reason(args: list[str]) -> str | None:
    return None if args else 'bare `set` dumps every shell variable'


def _export_reason(args: list[str]) -> str | None:
    return None if _non_flags(args) else 'bare `export` dumps the environment'


def _declare_reason(args: list[str]) -> str | None:
    names = _non_flags(args)
    if not names:
        return 'bare `declare` dumps every shell variable'
    return _secret_name_reason('declare', names)


def _pass_reason(args: list[str]) -> str | None:
    if not args or args[0] in PASS_SAFE_SUBCOMMANDS:
        return None
    if PASS_CLIP_FLAGS.intersection(args):
        return None
    return '`pass` would print a decrypted entry'


def _gh_reason(args: list[str]) -> str | None:
    if args[:2] == ['auth', 'token']:
        return '`gh auth token` prints the GitHub token'
    shows_token = GH_SHOW_TOKEN_FLAGS.intersection(args)
    if args[:2] == ['auth', 'status'] and shows_token:
        return '`gh auth status` with a show-token flag prints the token'
    return None


def _git_reason(args: list[str]) -> str | None:
    if args[:2] == ['credential', 'fill']:
        return '`git credential fill` prints the stored password'
    return None


COMMAND_CHECKS = {
    'env': _env_reason,
    'printenv': _printenv_reason,
    'set': _set_reason,
    'export': _export_reason,
    'declare': _declare_reason,
    'typeset': _declare_reason,
    'pass': _pass_reason,
    'gh': _gh_reason,
    'git': _git_reason,
}


def _echoed_secret_var(segment: str) -> str | None:
    for match in VAR_REFERENCE_PATTERN.finditer(segment):
        name = match.group(1)
        if SECRET_NAME_PATTERN.search(name):
            return name
    return None


def _segment_reason(segment: str) -> str | None:
    tokens = _tokenize(segment)
    if not tokens:
        return None
    base = Path(tokens[0]).name
    args = tokens[1:]

    check = COMMAND_CHECKS.get(base)
    if check:
        return check(args)

    if base in PRINT_COMMANDS:
        name = _echoed_secret_var(segment)
        return f'echoes ${name}, which looks like a secret' if name else None

    if base in FILE_READ_COMMANDS:
        for token in args:
            if is_secret_file(token):
                return f'reads {token} directly, which may contain secrets'
    return None


def detect_bash_risk(command: str) -> str | None:
    """Return a human-readable reason the command is risky, or None."""
    for segment in _command_segments(command):
        reason = _segment_reason(segment)
        if reason:
            return reason
    return None


def _bash_tool_reason(tool_input: dict[str, object]) -> str | None:
    command = tool_input.get('command')
    return detect_bash_risk(command) if isinstance(command, str) else None


def _read_tool_reason(tool_input: dict[str, object]) -> str | None:
    file_path = tool_input.get('file_path')
    if isinstance(file_path, str) and is_secret_file(file_path):
        return f'{file_path} may contain secrets'
    return None


def _grep_tool_reason(tool_input: dict[str, object]) -> str | None:
    for key in ('path', 'glob'):
        target = tool_input.get(key)
        if isinstance(target, str) and is_secret_file(target):
            return f'Grep {key} {target} may contain secrets'
    return None


TOOL_CHECKS = {
    'Bash': _bash_tool_reason,
    'Read': _read_tool_reason,
    'Grep': _grep_tool_reason,
}


def main(raw_payload: str) -> int:
    if os.environ.get(SKIP_ENV_VAR):
        return 0

    payload = read_payload(raw_payload)
    tool_input = payload.get('tool_input')
    check = TOOL_CHECKS.get(str(payload.get('tool_name')))
    if check is None or not isinstance(tool_input, dict):
        return 0

    reason = check(tool_input)
    if reason is None:
        return 0

    print(FAILURE_HEADER, file=sys.stderr)
    print(f'Reason: {reason}', file=sys.stderr)
    return BLOCK_EXIT_CODE


if __name__ == '__main__':
    sys.exit(main(sys.stdin.read()))
