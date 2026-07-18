from __future__ import annotations

from typing import Any, TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from gtd import api

if TYPE_CHECKING:
    from flask.testing import FlaskClient
    from collections.abc import Iterator


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[FlaskClient]:
    monkeypatch.setenv('GTD_API_KEY', 'test-key')
    api.app.config['TESTING'] = True
    with api.app.test_client() as c:
        yield c


@pytest.fixture()
def auth_header() -> dict[str, str]:
    return {'Authorization': 'Bearer test-key'}


ROUTES = [
    ('get', '/today'),
    ('get', '/inbox'),
    ('get', '/statuses'),
    ('post', '/capture'),
    ('post', '/done/abc123'),
    ('post', '/snooze/abc123'),
    ('patch', '/entry/abc123'),
]


@pytest.mark.parametrize(('method', 'route'), ROUTES)
def test_missing_auth_header_returns_401(
    client: FlaskClient,
    method: str,
    route: str,
) -> None:
    response = getattr(client, method)(route)
    assert response.status_code == 401


@pytest.mark.parametrize(('method', 'route'), ROUTES)
def test_wrong_api_key_returns_401(
    client: FlaskClient,
    method: str,
    route: str,
) -> None:
    headers = {'Authorization': 'Bearer wrong-key'}
    response = getattr(client, method)(route, headers=headers)
    assert response.status_code == 401


def test_missing_server_key_returns_500(
    client: FlaskClient,
    auth_header: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv('GTD_API_KEY', raising=False)
    response = client.get('/statuses', headers=auth_header)
    assert response.status_code == 500


def test_statuses_returns_status_list(
    client: FlaskClient,
    auth_header: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api, 'STATUSES', ['Triage', 'Current Project'])
    response = client.get('/statuses', headers=auth_header)
    assert response.status_code == 200
    assert response.get_json() == ['Triage', 'Current Project']


def test_capture_creates_page(
    client: FlaskClient,
    auth_header: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        api, '_create_page', MagicMock(return_value={'id': 'page-1'})
    )
    response = client.post(
        '/capture', json={'header': ' buy milk '}, headers=auth_header
    )
    assert response.status_code == 201
    assert response.get_json() == {'page_id': 'page-1', 'header': 'buy milk'}


def test_capture_rejects_empty_header(
    client: FlaskClient,
    auth_header: dict[str, str],
) -> None:
    response = client.post(
        '/capture', json={'header': '   '}, headers=auth_header
    )
    assert response.status_code == 400


def test_today_returns_entry_list(
    client: FlaskClient,
    auth_header: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = MagicMock()
    monkeypatch.setattr(
        api,
        '_get_today_entries',
        MagicMock(return_value=[entry]),
    )
    monkeypatch.setattr(
        api, '_entry_dict', MagicMock(return_value={'id': '1'})
    )
    response = client.get('/today', headers=auth_header)
    assert response.status_code == 200
    assert response.get_json() == [{'id': '1'}]


def test_done_archives_page(
    client: FlaskClient,
    auth_header: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_mock = MagicMock()
    monkeypatch.setattr(api, 'archive_page', archive_mock)
    response = client.post('/done/page-1', headers=auth_header)
    assert response.status_code == 200
    assert response.get_json() == {'page_id': 'page-1', 'status': 'archived'}
    archive_mock.assert_called_once_with('page-1')


@pytest.mark.parametrize(
    ('body', 'expect_status'),
    [
        ({'days': 3}, 200),
        ({'until': '2026-08-01'}, 200),
        ({'until': 'not a date'}, 400),
    ],
)
def test_snooze_variants(
    client: FlaskClient,
    auth_header: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    body: dict[str, Any],
    expect_status: int,
) -> None:
    monkeypatch.setattr(api, 'update_page', MagicMock())
    monkeypatch.setattr(
        api, 'build_property_update', MagicMock(return_value={})
    )
    if 'until' in body and body['until'] == '2026-08-01':
        monkeypatch.setattr(
            api, '_parse_date_input', MagicMock(return_value='2026-08-01')
        )
    elif 'until' in body:
        monkeypatch.setattr(
            api, '_parse_date_input', MagicMock(return_value=None)
        )
    response = client.post('/snooze/page-1', json=body, headers=auth_header)
    assert response.status_code == expect_status


def test_update_entry_rejects_invalid_status(
    client: FlaskClient,
    auth_header: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api, 'STATUSES', ['Triage'])
    response = client.patch(
        '/entry/page-1',
        json={'status': 'Nonexistent'},
        headers=auth_header,
    )
    assert response.status_code == 400


def test_update_entry_rejects_empty_body(
    client: FlaskClient,
    auth_header: dict[str, str],
) -> None:
    response = client.patch('/entry/page-1', json={}, headers=auth_header)
    assert response.status_code == 400


def test_update_entry_applies_fields(
    client: FlaskClient,
    auth_header: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    update_mock = MagicMock()
    monkeypatch.setattr(api, 'update_page', update_mock)
    monkeypatch.setattr(
        api, 'build_property_update', MagicMock(return_value={})
    )
    response = client.patch(
        '/entry/page-1',
        json={'context': 'Home'},
        headers=auth_header,
    )
    assert response.status_code == 200
    assert response.get_json() == {
        'page_id': 'page-1',
        'updated': {'context': 'Home'},
    }
