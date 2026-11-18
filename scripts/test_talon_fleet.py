"""Fleet voice commands: .talon files, coach overlay and talon.md agree."""

import importlib.util
import re
from pathlib import Path

import pytest

TALON = Path(__file__).resolve().parent.parent / 'talon'
CAPTURES = {'<user.text>': '<words>'}


def load_commands() -> tuple[tuple[str, str, str], ...]:
    spec = importlib.util.spec_from_file_location(
        'fleet_commands',
        TALON / 'fleet_commands.py',
    )
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.COMMANDS


def spoken_rules() -> list[str]:
    rules = []
    for path in sorted(TALON.glob('fleet*.talon')):
        _, _, body = path.read_text().partition('\n-\n')
        for line in body.splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            rule = line.partition(':')[0].strip().strip('^$')
            for capture, word in CAPTURES.items():
                rule = rule.replace(capture, word)
            rules.append(rule)
    return rules


COMMANDS = load_commands()
SPOKEN = [spoken for _, spoken, _ in COMMANDS]


def test_every_rule_is_on_the_cheat_sheet_and_back() -> None:
    assert sorted(spoken_rules()) == sorted(SPOKEN)


def test_no_duplicate_rules() -> None:
    rules = spoken_rules()
    assert len(rules) == len(set(rules))


@pytest.mark.parametrize('spoken', SPOKEN)
def test_talon_md_documents_each_command(spoken: str) -> None:
    doc = (TALON / 'talon.md').read_text()
    section = re.search(r'## Fleet by voice\n(.*?)(?=\n## |\Z)', doc, re.S)
    assert section, 'talon.md needs a "## Fleet by voice" section'
    assert f'`{spoken}`' in section.group(1)
