import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.telegram_account import AccountStatus


_ACCOUNT_PAYLOAD = {
    "phone_number": "+12025550100",
    "api_id": 123456,
    "api_hash": "abc123def456",
    "session_string": "fake_session_string",
}


def _add_account(client, admin_headers, payload=None):
    """Helper: POST /accounts with a mocked Telegram connect."""
    payload = payload or _ACCOUNT_PAYLOAD
    with patch.object(
        client.app.state.account_manager,
        "add_account",
        new_callable=AsyncMock,
    ):
        return client.post("/api/v1/accounts", json=payload, headers=admin_headers)


def test_list_accounts_empty(client, admin_headers):
    response = client.get("/api/v1/accounts", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_accounts_requires_admin_key(client):
    response = client.get("/api/v1/accounts")
    assert response.status_code == 403


def test_add_account_created(client, admin_headers):
    response = _add_account(client, admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["phone_number"] == _ACCOUNT_PAYLOAD["phone_number"]
    assert data["status"] == AccountStatus.active
    uuid.UUID(data["id"])  # valid UUID


def test_add_account_duplicate_rejected(client, admin_headers):
    _add_account(client, admin_headers)
    response = _add_account(client, admin_headers)
    assert response.status_code == 409


def test_get_account(client, admin_headers):
    created = _add_account(client, admin_headers).json()
    account_id = created["id"]

    response = client.get(f"/api/v1/accounts/{account_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == account_id


def test_get_account_not_found(client, admin_headers):
    response = client.get(f"/api/v1/accounts/{uuid.uuid4()}", headers=admin_headers)
    assert response.status_code == 404


def test_update_account_status(client, admin_headers):
    created = _add_account(client, admin_headers).json()
    account_id = created["id"]

    with patch.object(
        client.app.state.account_manager,
        "remove_account",
        new_callable=AsyncMock,
    ):
        response = client.put(
            f"/api/v1/accounts/{account_id}",
            json={"status": "inactive"},
            headers=admin_headers,
        )
    assert response.status_code == 200
    assert response.json()["status"] == AccountStatus.inactive


def test_delete_account(client, admin_headers):
    created = _add_account(client, admin_headers).json()
    account_id = created["id"]

    with patch.object(
        client.app.state.account_manager,
        "remove_account",
        new_callable=AsyncMock,
    ):
        response = client.delete(
            f"/api/v1/accounts/{account_id}", headers=admin_headers
        )
    assert response.status_code == 204

    # Confirm it's gone
    get = client.get(f"/api/v1/accounts/{account_id}", headers=admin_headers)
    assert get.status_code == 404


def test_list_accounts_shows_added(client, admin_headers):
    second = {**_ACCOUNT_PAYLOAD, "phone_number": "+12025550101"}
    _add_account(client, admin_headers)
    _add_account(client, admin_headers, second)

    response = client.get("/api/v1/accounts", headers=admin_headers)
    assert response.status_code == 200
    phones = {a["phone_number"] for a in response.json()}
    assert _ACCOUNT_PAYLOAD["phone_number"] in phones
    assert second["phone_number"] in phones
