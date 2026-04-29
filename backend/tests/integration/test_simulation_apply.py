"""Integration tests for scenario apply and archive endpoints."""

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.enums import (
    BalanceSource,
    IncomeStatus,
    LoanStatus,
    LoanType,
    PaymentAccuracy,
    PaymentMethod,
    PaymentStatus,
)
from app.domain.models.balance import LoanBalance
from app.domain.models.income import Income
from app.domain.models.loan import Loan
from app.domain.models.payment import PlannedPayment
from app.domain.models.user import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def auth_headers(db_session: AsyncSession, client: AsyncClient) -> dict:
    user = User(
        email="apply@settle.local",
        password_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    resp = await client.post(
        "/api/auth/login",
        json={"email": "apply@settle.local", "password": "testpass123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
async def seed_data(db_session: AsyncSession, auth_headers: dict) -> dict:
    result = await db_session.execute(
        select(User).where(User.email == "apply@settle.local")
    )
    user = result.scalar_one()

    loan = Loan(
        user_id=user.id,
        code="APPLY01",
        creditor="Apply Bank",
        name="Apply Credit",
        loan_type=LoanType.CREDIT,
        payment_method=PaymentMethod.ANNUITY,
        original_amount=Decimal("60000.00"),
        interest_rate=Decimal("10.0000"),
        opening_date=date(2026, 1, 1),
        months_remaining=6,
        payment_day=15,
        status=LoanStatus.ACTIVE,
    )
    db_session.add(loan)
    await db_session.flush()

    balance = LoanBalance(
        loan_id=loan.id,
        snapshot_date=date(2026, 5, 1),
        principal_balance=Decimal("50000.00"),
        accrued_interest=Decimal("500.00"),
        current_balance=Decimal("50500.00"),
        source=BalanceSource.IMPORTED,
    )
    db_session.add(balance)

    pp1 = PlannedPayment(
        user_id=user.id,
        loan_id=loan.id,
        due_date=date(2026, 6, 15),
        amount=Decimal("8700.00"),
        principal_part=Decimal("8000.00"),
        interest_part=Decimal("700.00"),
        status=PaymentStatus.PENDING,
        accuracy=PaymentAccuracy.CALCULATED_ANNUITY,
    )
    db_session.add(pp1)

    income = Income(
        user_id=user.id,
        name="Salary",
        code="SAL_APPLY",
        amount=Decimal("90000.00"),
        expected_date=date(2026, 6, 10),
        status=IncomeStatus.EXPECTED,
    )
    db_session.add(income)
    await db_session.flush()

    return {"user": user, "loan": loan, "payment": pp1, "income": income}


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_archive_scenario(
    client: AsyncClient,
    auth_headers: dict,
    seed_data: dict,
) -> None:
    """Archive changes status to archived."""
    resp = await client.post(
        "/api/scenarios",
        json={"name": "To archive", "base_date": "2026-05-01"},
        headers=auth_headers,
    )
    scenario_id = resp.json()["id"]

    resp = await client.post(
        f"/api/scenarios/{scenario_id}/archive",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


# ---------------------------------------------------------------------------
# Apply non-draft returns 400
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_apply_archived_scenario_returns_400(
    client: AsyncClient,
    auth_headers: dict,
    seed_data: dict,
) -> None:
    """Applying a non-draft scenario returns 400."""
    resp = await client.post(
        "/api/scenarios",
        json={"name": "Already archived", "base_date": "2026-05-01"},
        headers=auth_headers,
    )
    scenario_id = resp.json()["id"]

    # Archive it first
    await client.post(
        f"/api/scenarios/{scenario_id}/archive",
        headers=auth_headers,
    )

    # Try to apply
    resp = await client.post(
        f"/api/scenarios/{scenario_id}/apply",
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Apply with add_income materializes income
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_apply_add_income_creates_real_income(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    seed_data: dict,
) -> None:
    """Applying add_income action creates a real Income record."""
    user = seed_data["user"]

    resp = await client.post(
        "/api/scenarios",
        json={"name": "Income scenario", "base_date": "2026-05-01"},
        headers=auth_headers,
    )
    scenario_id = resp.json()["id"]

    resp = await client.post(
        f"/api/scenarios/{scenario_id}/actions",
        json={
            "action_type": "add_income",
            "effective_date": "2026-07-01",
            "params": {"amount": "30000", "name": "Freelance"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # Count incomes before
    result = await db_session.execute(
        select(Income).where(
            Income.user_id == user.id,
            Income.is_deleted.is_(False),
        )
    )
    incomes_before = len(list(result.scalars().all()))

    # Apply
    resp = await client.post(
        f"/api/scenarios/{scenario_id}/apply",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["applied_actions"] == 1

    # Verify income was created
    result = await db_session.execute(
        select(Income).where(
            Income.user_id == user.id,
            Income.is_deleted.is_(False),
        )
    )
    incomes_after = list(result.scalars().all())
    assert len(incomes_after) == incomes_before + 1

    new_income = [i for i in incomes_after if i.name == "Freelance"][0]
    assert new_income.amount == Decimal("30000.00")
    assert new_income.expected_date == date(2026, 7, 1)


# ---------------------------------------------------------------------------
# Apply with skip materializes planned_payment status change
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_apply_skip_changes_planned_status(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    seed_data: dict,
) -> None:
    """Applying skip action marks planned payment as skipped in DB."""
    pp = seed_data["payment"]

    resp = await client.post(
        "/api/scenarios",
        json={"name": "Skip scenario", "base_date": "2026-05-01"},
        headers=auth_headers,
    )
    scenario_id = resp.json()["id"]

    resp = await client.post(
        f"/api/scenarios/{scenario_id}/actions",
        json={
            "action_type": "skip",
            "planned_payment_id": str(pp.id),
            "effective_date": "2026-06-15",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # Apply
    resp = await client.post(
        f"/api/scenarios/{scenario_id}/apply",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Verify DB
    result = await db_session.execute(
        select(PlannedPayment).where(PlannedPayment.id == pp.id)
    )
    updated_pp = result.scalar_one()
    assert updated_pp.status == PaymentStatus.SKIPPED

    # Scenario status is now applied
    resp = await client.get(
        f"/api/scenarios/{scenario_id}",
        headers=auth_headers,
    )
    assert resp.json()["status"] == "applied"


# ---------------------------------------------------------------------------
# Apply nonexistent scenario returns 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_apply_nonexistent_returns_404(
    client: AsyncClient,
    auth_headers: dict,
    seed_data: dict,
) -> None:
    resp = await client.post(
        "/api/scenarios/00000000-0000-0000-0000-000000000000/apply",
        headers=auth_headers,
    )
    assert resp.status_code == 404
