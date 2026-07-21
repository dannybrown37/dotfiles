from __future__ import annotations

from typing import TYPE_CHECKING
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
    ('post', '/capture'),
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
