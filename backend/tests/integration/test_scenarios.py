"""Integration tests for scenarios CRUD."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.models.user import User


@pytest.fixture()
async def auth_headers(db_session: AsyncSession, client: AsyncClient) -> dict:
    user = User(
        email="test@settle.local",
        password_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    response = await client.post(
        "/api/auth/login",
        json={"email": "test@settle.local", "password": "testpass123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio()
async def test_scenario_crud(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    # Create
    resp = await client.post(
        "/api/scenarios",
        json={"name": "Тестовый сценарий", "base_date": "2026-05-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    scenario_id = resp.json()["id"]

    # List
    resp = await client.get("/api/scenarios", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Get
    resp = await client.get(
        f"/api/scenarios/{scenario_id}", headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Тестовый сценарий"

    # Update
    resp = await client.patch(
        f"/api/scenarios/{scenario_id}",
        json={"name": "Обновлённый сценарий"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Обновлённый сценарий"

    # Delete
    resp = await client.delete(
        f"/api/scenarios/{scenario_id}", headers=auth_headers,
    )
    assert resp.status_code == 204


@pytest.mark.asyncio()
async def test_scenario_action_crud(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    # Create scenario
    resp = await client.post(
        "/api/scenarios",
        json={"name": "Сценарий с действиями", "base_date": "2026-05-01"},  # noqa: RUF001
        headers=auth_headers,
    )
    scenario_id = resp.json()["id"]

    # Create action
    resp = await client.post(
        f"/api/scenarios/{scenario_id}/actions",
        json={
            "action_type": "add_income",
            "effective_date": "2026-05-15",
            "params": {"amount": "10000", "name": "Премия"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    action_id = resp.json()["id"]

    # Update action
    resp = await client.patch(
        f"/api/scenarios/{scenario_id}/actions/{action_id}",
        json={"params": {"amount": "15000", "name": "Бонус"}},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Delete action
    resp = await client.delete(
        f"/api/scenarios/{scenario_id}/actions/{action_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204
