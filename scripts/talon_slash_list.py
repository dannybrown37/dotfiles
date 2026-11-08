#!/usr/bin/env python3
"""Print a Talon list of installed Claude Code and Copilot skill names."""

import json
import re
from collections.abc import Iterator
from pathlib import Path

# Talon only hears words: digits, capitals and plugin prefixes have no
# spoken form the generated list could use.
SAYABLE_NAME = re.compile(r'[a-z][a-z_-]*')

# Abbreviations the speech engine can't hear as written.
SPOKEN_WORDS = {
    'ci': 'see eye',
    'cli': 'see el eye',
    'docx': 'word doc',
    'dynamodb': 'dynamo',
    'pdf': 'pea dee eff',
    'pptx': 'power point',
    'tui': 'tooey',
    'ui': 'you eye',
    'xlsx': 'excel',
}


def spoken_form(name: str) -> str:
    words = re.split(r'[-_]', name)
    return ' '.join(SPOKEN_WORDS.get(word, word) for word in words)


def claude_plugin_paths(home: Path) -> Iterator[Path]:
    installed = home / '.claude' / 'plugins' / 'installed_plugins.json'
    try:
        plugins = json.loads(installed.read_text())['plugins']
    except (OSError, ValueError, KeyError):
        return
    for installs in plugins.values():
        for install in installs:
            yield Path(install['installPath'])


def skill_names(home: Path) -> set[str]:
    skill_files = [
        *(home / '.copilot' / 'skills').glob('*/SKILL.md'),
        *(home / '.claude' / 'skills').rglob('SKILL.md'),
    ]
    command_files: list[Path] = []
    for plugin in claude_plugin_paths(home):
        skill_files += plugin.glob('skills/*/SKILL.md')
        command_files += plugin.glob('commands/*.md')
    names = {path.parent.name for path in skill_files}
    names |= {path.stem for path in command_files}
    return {name for name in names if SAYABLE_NAME.fullmatch(name)}


def render_talon_list(names: set[str]) -> str:
    lines = [f'{spoken_form(name)}: {name}\n' for name in sorted(names)]
    return 'list: user.slash_skill\n-\n' + ''.join(lines)


if __name__ == '__main__':
    print(render_talon_list(skill_names(Path.home())), end='')
