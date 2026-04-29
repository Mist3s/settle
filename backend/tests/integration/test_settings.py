"""Integration tests for settings CRUD."""

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
async def test_settings_upsert_and_list(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    # Create settings
    resp = await client.patch(
        "/api/settings",
        json={
            "items": [
                {"key": "usd_rub_rate", "value": "92.50"},
                {"key": "salary_usd", "value": "2000"},
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    settings = resp.json()
    assert len(settings) == 2

    # List
    resp = await client.get("/api/settings", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Update existing
    resp = await client.patch(
        "/api/settings",
        json={"items": [{"key": "usd_rub_rate", "value": "95.00"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    rate = next(s for s in resp.json() if s["key"] == "usd_rub_rate")
    assert rate["value"] == "95.00"
