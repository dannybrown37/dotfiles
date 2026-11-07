"""Tests for talon_slash_list: skill discovery and the Talon list it writes."""

import json
from pathlib import Path

import pytest

from talon_slash_list import render_talon_list, skill_names, spoken_form


def make_skill(skills_dir: Path, name: str) -> None:
    (skills_dir / name).mkdir(parents=True)
    (skills_dir / name / 'SKILL.md').write_text('---\n')


def install_claude_plugin(home: Path, install_path: Path) -> None:
    plugins = home / '.claude' / 'plugins'
    plugins.mkdir(parents=True, exist_ok=True)
    installed = {
        'version': 2,
        'plugins': {'x@y': [{'installPath': str(install_path)}]},
    }
    (plugins / 'installed_plugins.json').write_text(json.dumps(installed))


@pytest.mark.parametrize(
    ('name', 'expected'),
    [
        ('verify', 'verify'),
        ('code-review', 'code review'),
        ('grill_me', 'grill me'),
        ('two-axis-review', 'two axis review'),
        ('debug-ci', 'debug see eye'),
        ('cli-ergonomics', 'see el eye ergonomics'),
        ('tui-screenshots', 'tooey screenshots'),
        ('docx', 'word doc'),
    ],
)
def test_spoken_form(name: str, expected: str) -> None:
    assert spoken_form(name) == expected


def test_skill_names_finds_copilot_and_claude_user_skills(
    tmp_path: Path,
) -> None:
    make_skill(tmp_path / '.copilot' / 'skills', 'grill-me')
    make_skill(tmp_path / '.claude' / 'skills', 'mine')
    make_skill(tmp_path / '.claude' / 'skills' / 'synced' / 'abc', 'docx')

    assert skill_names(tmp_path) == {'grill-me', 'mine', 'docx'}


def test_skill_names_finds_plugin_skills_and_commands(tmp_path: Path) -> None:
    plugin = tmp_path / 'plugin'
    make_skill(plugin / 'skills', 'verify')
    (plugin / 'commands').mkdir()
    (plugin / 'commands' / 'ship-it.md').write_text('')
    install_claude_plugin(tmp_path, plugin)

    assert skill_names(tmp_path) == {'verify', 'ship-it'}


def test_skill_names_ignores_dirs_without_skill_md(tmp_path: Path) -> None:
    (tmp_path / '.copilot' / 'skills' / 'half-made').mkdir(parents=True)

    assert skill_names(tmp_path) == set()


def test_skill_names_survives_missing_and_broken_plugin_file(
    tmp_path: Path,
) -> None:
    assert skill_names(tmp_path) == set()

    plugins = tmp_path / '.claude' / 'plugins'
    plugins.mkdir(parents=True)
    (plugins / 'installed_plugins.json').write_text('{not json')

    assert skill_names(tmp_path) == set()


@pytest.mark.parametrize('name', ['v2-tool', 'Upper', 'has space', 'a:b'])
def test_skill_names_skips_names_talon_cannot_say(
    tmp_path: Path,
    name: str,
) -> None:
    make_skill(tmp_path / '.copilot' / 'skills', name)

    assert skill_names(tmp_path) == set()


def test_render_talon_list_is_sorted_with_header() -> None:
    assert render_talon_list({'verify', 'code-review'}) == (
        'list: user.slash_skill\n-\ncode review: code-review\nverify: verify\n'
    )
