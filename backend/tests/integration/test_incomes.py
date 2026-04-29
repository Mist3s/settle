"""Integration tests for incomes CRUD."""

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


INCOME_DATA = {
    "code": "SALARY_2026_05_10",
    "expected_date": "2026-05-10",
    "amount": "45000.00",
    "name": "Зарплата",
}


@pytest.mark.asyncio()
async def test_income_crud(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    # Create
    resp = await client.post("/api/incomes", json=INCOME_DATA, headers=auth_headers)
    assert resp.status_code == 201
    income_id = resp.json()["id"]

    # List
    resp = await client.get("/api/incomes", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Update
    resp = await client.patch(
        f"/api/incomes/{income_id}",
        json={"amount": "50000.00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == "50000.00"

    # Receive
    resp = await client.post(
        f"/api/incomes/{income_id}/receive",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"

    # Delete
    resp = await client.delete(
        f"/api/incomes/{income_id}", headers=auth_headers,
    )
    assert resp.status_code == 204
