"""Integration tests for loans CRUD + audit_log."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.models.audit import AuditLog
from app.domain.models.user import User


@pytest.fixture()
async def auth_headers(db_session: AsyncSession, client: AsyncClient) -> dict:
    """Create a test user and return auth headers."""
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
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


LOAN_DATA = {
    "code": "TEST_LOAN_01",
    "creditor": "Тестовый Банк",
    "name": "Тестовый кредит",
    "loan_type": "credit",
    "payment_method": "annuity",
    "original_amount": "500000.00",
    "interest_rate": "15.5000",
    "months_remaining": 36,
    "payment_day": 15,
}


@pytest.mark.asyncio()
async def test_create_loan(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    resp = await client.post("/api/loans", json=LOAN_DATA, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "TEST_LOAN_01"
    assert data["creditor"] == "Тестовый Банк"
    assert data["original_amount"] == "500000.00"
    assert data["interest_rate"] == "15.5000"
    assert data["status"] == "active"
    assert data["id"] is not None


@pytest.mark.asyncio()
async def test_list_loans(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    await client.post("/api/loans", json=LOAN_DATA, headers=auth_headers)
    resp = await client.get("/api/loans", headers=auth_headers)
    assert resp.status_code == 200
    loans = resp.json()
    assert len(loans) >= 1
    assert any(ln["code"] == "TEST_LOAN_01" for ln in loans)


@pytest.mark.asyncio()
async def test_get_loan(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    create_resp = await client.post(
        "/api/loans", json=LOAN_DATA, headers=auth_headers,
    )
    loan_id = create_resp.json()["id"]
    resp = await client.get(f"/api/loans/{loan_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == loan_id


@pytest.mark.asyncio()
async def test_update_loan(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    create_resp = await client.post(
        "/api/loans", json=LOAN_DATA, headers=auth_headers,
    )
    loan_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/loans/{loan_id}",
        json={"name": "Обновлённый кредит", "priority": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Обновлённый кредит"
    assert resp.json()["priority"] == 5


@pytest.mark.asyncio()
async def test_delete_loan_soft(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    create_resp = await client.post(
        "/api/loans", json=LOAN_DATA, headers=auth_headers,
    )
    loan_id = create_resp.json()["id"]
    del_resp = await client.delete(
        f"/api/loans/{loan_id}", headers=auth_headers,
    )
    assert del_resp.status_code == 204

    # Should not be visible in list
    list_resp = await client.get("/api/loans", headers=auth_headers)
    ids = [ln["id"] for ln in list_resp.json()]
    assert loan_id not in ids

    # Should return 404 on get
    get_resp = await client.get(
        f"/api/loans/{loan_id}", headers=auth_headers,
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio()
async def test_audit_log_on_create(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
) -> None:
    create_resp = await client.post(
        "/api/loans", json=LOAN_DATA, headers=auth_headers,
    )
    loan_id = create_resp.json()["id"]

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "loans",
            AuditLog.entity_id == loan_id,
            AuditLog.action == "create",
        )
    )
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.after_state is not None
    assert audit.after_state["code"] == "TEST_LOAN_01"


@pytest.mark.asyncio()
async def test_audit_log_on_delete(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
) -> None:
    create_resp = await client.post(
        "/api/loans", json=LOAN_DATA, headers=auth_headers,
    )
    loan_id = create_resp.json()["id"]
    await client.delete(f"/api/loans/{loan_id}", headers=auth_headers)

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "loans",
            AuditLog.entity_id == loan_id,
            AuditLog.action == "delete",
        )
    )
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.before_state is not None


@pytest.mark.asyncio()
async def test_create_balance_correction(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    create_resp = await client.post(
        "/api/loans", json=LOAN_DATA, headers=auth_headers,
    )
    loan_id = create_resp.json()["id"]
    bal_resp = await client.post(
        f"/api/loans/{loan_id}/balance",
        json={
            "amount": "480000.00",
            "snapshot_date": "2026-04-29",
        },
        headers=auth_headers,
    )
    assert bal_resp.status_code == 201
    data = bal_resp.json()
    assert data["current_balance"] == "480000.00"
    assert data["source"] == "manual"


@pytest.mark.asyncio()
async def test_extra_field_rejected(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    bad_data = {**LOAN_DATA, "unknown_field": "value"}
    resp = await client.post("/api/loans", json=bad_data, headers=auth_headers)
    assert resp.status_code == 422
