"""Integration tests for simulation forecast endpoint.

Critical test: overlay does NOT write to the DB (architecture invariant).
Tests each action type through the forecast endpoint.
"""

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
        email="sim@settle.local",
        password_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    resp = await client.post(
        "/api/auth/login",
        json={"email": "sim@settle.local", "password": "testpass123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
async def seed_data(
    db_session: AsyncSession, client: AsyncClient, auth_headers: dict
) -> dict:
    """Create a loan, balance, planned payments, and incomes for testing."""
    # Get user_id from token
    resp = await client.get("/api/loans", headers=auth_headers)
    # Need user from DB
    result = await db_session.execute(
        select(User).where(User.email == "sim@settle.local")
    )
    user = result.scalar_one()

    # Create loan
    loan = Loan(
        user_id=user.id,
        code="SIMTEST01",
        creditor="Test Bank",
        name="Sim Test Credit",
        loan_type=LoanType.CREDIT,
        payment_method=PaymentMethod.ANNUITY,
        original_amount=Decimal("120000.00"),
        interest_rate=Decimal("12.0000"),
        opening_date=date(2026, 1, 1),
        months_remaining=12,
        payment_day=15,
        status=LoanStatus.ACTIVE,
    )
    db_session.add(loan)
    await db_session.flush()

    # Create balance snapshot
    balance = LoanBalance(
        loan_id=loan.id,
        snapshot_date=date(2026, 5, 1),
        principal_balance=Decimal("100000.00"),
        accrued_interest=Decimal("1000.00"),
        current_balance=Decimal("101000.00"),
        source=BalanceSource.IMPORTED,
    )
    db_session.add(balance)

    # Create planned payments
    pp1 = PlannedPayment(
        user_id=user.id,
        loan_id=loan.id,
        due_date=date(2026, 6, 15),
        amount=Decimal("11000.00"),
        principal_part=Decimal("10000.00"),
        interest_part=Decimal("1000.00"),
        status=PaymentStatus.PENDING,
        accuracy=PaymentAccuracy.CALCULATED_ANNUITY,
    )
    pp2 = PlannedPayment(
        user_id=user.id,
        loan_id=loan.id,
        due_date=date(2026, 7, 15),
        amount=Decimal("11000.00"),
        principal_part=Decimal("10100.00"),
        interest_part=Decimal("900.00"),
        status=PaymentStatus.PENDING,
        accuracy=PaymentAccuracy.CALCULATED_ANNUITY,
    )
    pp3 = PlannedPayment(
        user_id=user.id,
        loan_id=loan.id,
        due_date=date(2026, 8, 15),
        amount=Decimal("11000.00"),
        principal_part=Decimal("10200.00"),
        interest_part=Decimal("800.00"),
        status=PaymentStatus.PENDING,
        accuracy=PaymentAccuracy.CALCULATED_ANNUITY,
    )
    db_session.add_all([pp1, pp2, pp3])

    # Create an income
    income = Income(
        user_id=user.id,
        name="Salary",
        code="SAL001",
        amount=Decimal("90000.00"),
        expected_date=date(2026, 6, 10),
        status=IncomeStatus.EXPECTED,
    )
    db_session.add(income)
    await db_session.flush()

    return {
        "user": user,
        "loan": loan,
        "balance": balance,
        "payments": [pp1, pp2, pp3],
        "income": income,
    }


# ---------------------------------------------------------------------------
# Overlay invariant: DB snapshot before/after
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_forecast_does_not_write_to_db(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    seed_data: dict,
) -> None:
    """Critical test: overlay forecast does NOT modify the database.

    Architecture invariant from risk table + implementation plan.
    """
    loan = seed_data["loan"]

    # Create scenario with close_early_full action
    resp = await client.post(
        "/api/scenarios",
        json={"name": "Close test", "base_date": "2026-05-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    scenario_id = resp.json()["id"]

    resp = await client.post(
        f"/api/scenarios/{scenario_id}/actions",
        json={
            "action_type": "close_early_full",
            "loan_id": str(loan.id),
            "effective_date": "2026-06-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # Snapshot DB state before forecast
    bal_before = await db_session.execute(
        select(LoanBalance).where(LoanBalance.loan_id == loan.id)
    )
    balances_before = list(bal_before.scalars().all())
    bal_count_before = len(balances_before)
    principal_before = balances_before[0].principal_balance

    pp_before = await db_session.execute(
        select(PlannedPayment).where(PlannedPayment.loan_id == loan.id)
    )
    pp_count_before = len(list(pp_before.scalars().all()))

    # Call forecast
    resp = await client.get(
        f"/api/scenarios/{scenario_id}/forecast",
        params={
            "from": "2026-06-01",
            "to": "2026-08-31",
            "starting_balance": "50000",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify response structure
    assert "current" in data
    assert "scenario" in data
    assert "diff" in data
    assert len(data["current"]["balance_by_day"]) > 0
    assert len(data["scenario"]["balance_by_day"]) > 0

    # Snapshot DB state AFTER forecast — must be identical
    bal_after = await db_session.execute(
        select(LoanBalance).where(LoanBalance.loan_id == loan.id)
    )
    balances_after = list(bal_after.scalars().all())
    assert len(balances_after) == bal_count_before
    assert balances_after[0].principal_balance == principal_before

    pp_after = await db_session.execute(
        select(PlannedPayment).where(PlannedPayment.loan_id == loan.id)
    )
    assert len(list(pp_after.scalars().all())) == pp_count_before

    # Loan status unchanged
    result = await db_session.execute(
        select(Loan).where(Loan.id == loan.id)
    )
    loan_after = result.scalar_one()
    assert loan_after.status == LoanStatus.ACTIVE


# ---------------------------------------------------------------------------
# Forecast with add_income action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_forecast_add_income_shows_higher_balance(
    client: AsyncClient,
    auth_headers: dict,
    seed_data: dict,
) -> None:
    """add_income action should result in higher balance in to-be curve."""
    # Create scenario
    resp = await client.post(
        "/api/scenarios",
        json={"name": "Bonus scenario", "base_date": "2026-05-01"},
        headers=auth_headers,
    )
    scenario_id = resp.json()["id"]

    # Add income action
    resp = await client.post(
        f"/api/scenarios/{scenario_id}/actions",
        json={
            "action_type": "add_income",
            "effective_date": "2026-06-05",
            "params": {"amount": "50000", "name": "Bonus"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # Get forecast
    resp = await client.get(
        f"/api/scenarios/{scenario_id}/forecast",
        params={
            "from": "2026-06-01",
            "to": "2026-06-30",
            "starting_balance": "10000",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Scenario should have higher balance after June 5
    current_june_30 = Decimal(data["current"]["balance_by_day"][-1]["balance"])
    scenario_june_30 = Decimal(data["scenario"]["balance_by_day"][-1]["balance"])
    assert scenario_june_30 > current_june_30
    assert scenario_june_30 - current_june_30 == Decimal("50000")


# ---------------------------------------------------------------------------
# Forecast with skip action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_forecast_skip_removes_payment(
    client: AsyncClient,
    auth_headers: dict,
    seed_data: dict,
) -> None:
    """skip action should remove the payment from the to-be projection."""
    pp1 = seed_data["payments"][0]

    # Create scenario
    resp = await client.post(
        "/api/scenarios",
        json={"name": "Skip scenario", "base_date": "2026-05-01"},
        headers=auth_headers,
    )
    scenario_id = resp.json()["id"]

    # Skip first payment
    resp = await client.post(
        f"/api/scenarios/{scenario_id}/actions",
        json={
            "action_type": "skip",
            "planned_payment_id": str(pp1.id),
            "effective_date": "2026-06-15",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # Get forecast
    resp = await client.get(
        f"/api/scenarios/{scenario_id}/forecast",
        params={
            "from": "2026-06-01",
            "to": "2026-06-30",
            "starting_balance": "10000",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # In scenario, balance on June 30 should be higher (payment skipped)
    current_june_30 = Decimal(data["current"]["balance_by_day"][-1]["balance"])
    scenario_june_30 = Decimal(data["scenario"]["balance_by_day"][-1]["balance"])
    assert scenario_june_30 > current_june_30


# ---------------------------------------------------------------------------
# Forecast with close_early_full
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_forecast_close_early_full_projects_payoff(
    client: AsyncClient,
    auth_headers: dict,
    seed_data: dict,
) -> None:
    """close_early_full action should show full payoff in scenario."""
    loan = seed_data["loan"]

    resp = await client.post(
        "/api/scenarios",
        json={"name": "Payoff", "base_date": "2026-05-01"},
        headers=auth_headers,
    )
    scenario_id = resp.json()["id"]

    resp = await client.post(
        f"/api/scenarios/{scenario_id}/actions",
        json={
            "action_type": "close_early_full",
            "loan_id": str(loan.id),
            "effective_date": "2026-06-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    resp = await client.get(
        f"/api/scenarios/{scenario_id}/forecast",
        params={
            "from": "2026-06-01",
            "to": "2026-08-31",
            "starting_balance": "200000",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Scenario should have a synthetic payoff payment
    scenario_payments = data["scenario"]["payments"]
    synthetic = [p for p in scenario_payments if p.get("kind") == "synthetic"]
    assert len(synthetic) >= 1

    # Future regular payments cancelled in scenario
    cancelled = [
        p for p in scenario_payments
        if p.get("status") == "cancelled" and p.get("kind") == "real"
    ]
    assert len(cancelled) == 3  # all 3 pending payments


# ---------------------------------------------------------------------------
# Forecast nonexistent scenario returns 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_forecast_nonexistent_scenario_returns_404(
    client: AsyncClient,
    auth_headers: dict,
    seed_data: dict,
) -> None:
    resp = await client.get(
        "/api/scenarios/00000000-0000-0000-0000-000000000000/forecast",
        params={"from": "2026-06-01", "to": "2026-06-30", "starting_balance": "0"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
