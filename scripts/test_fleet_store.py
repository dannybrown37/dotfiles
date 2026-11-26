"""Tests for fleet.store: agent records and hook-written state on disk."""

import json
from pathlib import Path

import pytest

from fleet.agents import AgentState
from fleet.store import (
    AgentRecord,
    Steps,
    Store,
    default_state_dir,
    parse_steps,
)


def make_record(name: str = 'fix-x') -> AgentRecord:
    return AgentRecord(
        name=name,
        kind='claude',
        repo='/r',
        worktree='/r-worktrees/fix-x',
        branch='fix-x',
        base='main',
        prompt='do it',
        created_at=100.0,
        window_id='@3',
    )


@pytest.mark.parametrize(
    ('env', 'expected'),
    [
        ({'FLEET_STATE_DIR': '/x/fleet'}, Path('/x/fleet')),
        ({'XDG_STATE_HOME': '/s'}, Path('/s/fleet')),
        ({'HOME': '/h'}, Path('/h/.local/state/fleet')),
    ],
)
def test_default_state_dir(env: dict[str, str], expected: Path) -> None:
    assert default_state_dir(env) == expected


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.save(make_record())
    assert store.load('fix-x') == make_record()


def test_list_records_sorted_by_creation(tmp_path: Path) -> None:
    store = Store(tmp_path)
    late = make_record('late')
    late.created_at = 200.0
    store.save(late)
    store.save(make_record('early'))
    assert [r.name for r in store.list_records()] == ['early', 'late']


def test_list_records_skips_corrupt_files(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.save(make_record())
    (tmp_path / 'agents' / 'broken.json').write_text('{nope')
    assert [r.name for r in store.list_records()] == ['fix-x']


def test_list_records_ignores_state_files(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.save(make_record())
    store.write_state('fix-x', AgentState.IDLE, 'Stop', '', now=5.0)
    assert len(store.list_records()) == 1


def test_write_state_then_read_state(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.write_state('fix-x', AgentState.WAITING, 'Notification', 'ok?', 7.0)
    state = store.read_state('fix-x')
    assert state is not None
    assert state.state == AgentState.WAITING
    assert state.event == 'Notification'
    assert state.message == 'ok?'
    assert state.updated_at == 7.0  # noqa: PLR2004


def test_read_state_missing_is_none(tmp_path: Path) -> None:
    assert Store(tmp_path).read_state('nobody') is None


def test_read_state_unknown_value_is_none(tmp_path: Path) -> None:
    store = Store(tmp_path)
    (tmp_path / 'agents').mkdir()
    (tmp_path / 'agents' / 'x.state.json').write_text(
        json.dumps({'state': 'dancing', 'event': 'e', 'updated_at': 1}),
    )
    assert store.read_state('x') is None


def test_write_state_leaves_no_temp_files(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.write_state('fix-x', AgentState.IDLE, 'Stop', '', now=1.0)
    names = sorted(p.name for p in (tmp_path / 'agents').iterdir())
    assert names == ['fix-x.state.json']


def test_delete_removes_record_and_state(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.save(make_record())
    store.write_state('fix-x', AgentState.IDLE, 'Stop', '', now=1.0)
    store.delete('fix-x')
    assert store.list_records() == []
    assert store.read_state('fix-x') is None


def test_session_state_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.write_session(
        42,
        777,
        AgentState.WAITING,
        'Notification',
        'ok?',
        9.0,
    )
    live = store.read_session(42, 777)
    assert live is not None
    assert (live.state, live.message) == (AgentState.WAITING, 'ok?')


def test_session_state_ignored_after_pid_reuse(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.write_session(42, 777, AgentState.IDLE, 'Stop', '', 9.0)
    assert store.read_session(42, 999) is None


def test_prune_sessions_keeps_only_live_processes(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.write_session(1, 10, AgentState.IDLE, 'Stop', '', 1.0)
    store.write_session(2, 20, AgentState.IDLE, 'Stop', '', 1.0)
    store.write_session(3, 30, AgentState.IDLE, 'Stop', '', 1.0)
    store.prune_sessions({(1, 10), (3, 99)})
    assert store.read_session(1, 10) is not None
    assert not store.session_path(2).exists()
    assert not store.session_path(3).exists()


def test_load_missing_raises_key_error(tmp_path: Path) -> None:
    with pytest.raises(KeyError, match='nobody'):
        Store(tmp_path).load('nobody')


@pytest.mark.parametrize(
    ('data', 'expected'),
    [
        ({'done': 2, 'total': 5, 'note': 'tests'}, Steps(2, 5, 'tests')),
        ({'done': 0, 'total': 3}, Steps(0, 3, '')),
        ({'done': 9, 'total': 4, 'note': ''}, Steps(4, 4, '')),
        ({'done': -1, 'total': 4}, Steps(0, 4, '')),
        ({'done': 1, 'total': 2, 'note': '  wire  '}, Steps(1, 2, 'wire')),
        ({'done': 1, 'total': 2, 'note': 'x' * 200}, Steps(1, 2, 'x' * 80)),
        ({'done': 1, 'total': 0}, None),
        ({'done': 1}, None),
        ({'done': 'two', 'total': 4}, None),
        ({'done': True, 'total': 4}, None),
        ({'done': 1.5, 'total': 4}, None),
        ({'done': 1, 'total': 4, 'note': 7}, Steps(1, 4, '7')),
    ],
)
def test_parse_steps(data: dict[str, object], expected: Steps | None) -> None:
    assert parse_steps(data) == expected


def test_write_steps_then_read_steps(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.write_steps('fix-x', Steps(1, 3, 'parse'), launch_id='L1')
    assert store.read_steps('fix-x', 'L1') == Steps(1, 3, 'parse')


def test_read_steps_from_an_earlier_launch_is_none(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.write_steps('fix-x', Steps(1, 3, ''), launch_id='old')
    assert store.read_steps('fix-x', 'new') is None


def test_read_steps_missing_or_corrupt_is_none(tmp_path: Path) -> None:
    store = Store(tmp_path)
    assert store.read_steps('nobody') is None
    store.steps_path('bad').parent.mkdir(parents=True, exist_ok=True)
    store.steps_path('bad').write_text('{nope')
    assert store.read_steps('bad') is None


def test_list_records_ignores_steps_files(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.save(make_record())
    store.write_steps('fix-x', Steps(1, 2, ''), launch_id='')
    assert [r.name for r in store.list_records()] == ['fix-x']


def test_delete_removes_steps(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.save(make_record())
    store.write_steps('fix-x', Steps(1, 2, ''), launch_id='')
    store.delete('fix-x')
    assert store.read_steps('fix-x') is None
