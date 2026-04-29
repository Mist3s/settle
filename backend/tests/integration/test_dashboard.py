"""Integration tests for dashboard and forecast API (architecture §8.2).

Tests exercise both the service layer directly and the HTTP layer
via AsyncClient with overridden ``get_session`` and ``get_current_user``.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.core.security import hash_password
from app.domain.enums import (
    IncomeStatus,
    LoanStatus,
    LoanType,
    PaymentMethod,
    PaymentStatus,
)
from app.domain.models.balance import LoanBalance
from app.domain.models.income import Income
from app.domain.models.loan import Loan
from app.domain.models.payment import PlannedPayment
from app.domain.models.settings import Setting
from app.domain.models.user import User
from app.main import app
from app.services import dashboard_service, forecast_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(session: AsyncSession) -> User:
    user = User(email="dash_test@settle.local", password_hash=hash_password("pw"))
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _create_loan(
    session: AsyncSession,
    user: User,
    code: str = "LOAN_01",
    interest_rate: Decimal = Decimal("12.0000"),
) -> Loan:
    loan = Loan(
        user_id=user.id,
        code=code,
        creditor="TestBank",
        name=f"Test Loan {code}",
        loan_type=LoanType.CREDIT,
        payment_method=PaymentMethod.ANNUITY,
        original_amount=Decimal("100000.00"),
        interest_rate=interest_rate,
        status=LoanStatus.ACTIVE,
    )
    session.add(loan)
    await session.flush()
    await session.refresh(loan)
    return loan


@pytest.fixture()
async def auth_client(db_session: AsyncSession):
    """AsyncClient with overridden DB session *and* current_user."""
    user = await _create_user(db_session)

    async def _override_session():
        yield db_session

    def _override_user():
        return user

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = _override_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# ForecastService direct tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_forecast_empty_range(db_session: AsyncSession):
    """Given: no data, When: forecast with from > to, Then: empty list."""
    user = await _create_user(db_session)
    points = await forecast_service.forecast_balance_by_day(
        db_session,
        user.id,
        starting_balance=Decimal("50000"),
        from_date=date(2026, 5, 10),
        to_date=date(2026, 5, 1),
    )
    assert points == []


@pytest.mark.asyncio()
async def test_forecast_flat_no_events(db_session: AsyncSession):
    """Given: no incomes or payments, When: forecast, Then: flat line."""
    user = await _create_user(db_session)
    points = await forecast_service.forecast_balance_by_day(
        db_session,
        user.id,
        starting_balance=Decimal("50000"),
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 3),
    )
    assert len(points) == 3
    for p in points:
        assert Decimal(p.balance) == Decimal("50000")


@pytest.mark.asyncio()
async def test_forecast_income_adds_balance(db_session: AsyncSession):
    """Given: one income, When: forecast, Then: step up on income date."""
    user = await _create_user(db_session)
    income = Income(
        user_id=user.id,
        code="SAL_01",
        expected_date=date(2026, 5, 2),
        amount=Decimal("45000.00"),
        status=IncomeStatus.EXPECTED,
    )
    db_session.add(income)
    await db_session.flush()

    points = await forecast_service.forecast_balance_by_day(
        db_session,
        user.id,
        starting_balance=Decimal("10000"),
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 3),
    )
    assert len(points) == 3
    assert Decimal(points[0].balance) == Decimal("10000")  # May 1
    assert Decimal(points[1].balance) == Decimal("55000")  # May 2: +45000
    assert Decimal(points[2].balance) == Decimal("55000")  # May 3: flat


@pytest.mark.asyncio()
async def test_forecast_payment_subtracts_balance(db_session: AsyncSession):
    """Given: one pending payment, When: forecast, Then: step down on due date."""
    user = await _create_user(db_session)
    loan = await _create_loan(db_session, user)

    pp = PlannedPayment(
        user_id=user.id,
        loan_id=loan.id,
        due_date=date(2026, 5, 2),
        amount=Decimal("15000.00"),
        status=PaymentStatus.PENDING,
    )
    db_session.add(pp)
    await db_session.flush()

    points = await forecast_service.forecast_balance_by_day(
        db_session,
        user.id,
        starting_balance=Decimal("50000"),
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 3),
    )
    assert Decimal(points[0].balance) == Decimal("50000")
    assert Decimal(points[1].balance) == Decimal("35000")  # -15000
    assert Decimal(points[2].balance) == Decimal("35000")


@pytest.mark.asyncio()
async def test_forecast_respects_unavailable_balance(db_session: AsyncSession):
    """Given: unavailable_balance setting, When: forecast, Then: subtracted from start."""
    user = await _create_user(db_session)
    setting = Setting(
        user_id=user.id,
        key="unavailable_balance",
        value="5000",
    )
    db_session.add(setting)
    await db_session.flush()

    points = await forecast_service.forecast_balance_by_day(
        db_session,
        user.id,
        starting_balance=Decimal("50000"),
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 1),
    )
    assert Decimal(points[0].balance) == Decimal("45000")


# ---------------------------------------------------------------------------
# DashboardService direct tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_dashboard_empty_db(db_session: AsyncSession):
    """Given: no data, When: get_dashboard, Then: valid empty response."""
    user = await _create_user(db_session)
    result = await dashboard_service.get_dashboard(
        db_session, user.id, today=date(2026, 5, 1)
    )
    assert result.next_payments == []
    assert result.totals.active_loans == 0
    assert result.totals.total_debt == "0"
    assert result.warnings == []


@pytest.mark.asyncio()
async def test_dashboard_next_payments(db_session: AsyncSession):
    """Given: pending payments, When: dashboard, Then: next_payments populated."""
    user = await _create_user(db_session)
    loan = await _create_loan(db_session, user)

    today = date(2026, 5, 1)
    for i in range(5):
        pp = PlannedPayment(
            user_id=user.id,
            loan_id=loan.id,
            due_date=today + timedelta(days=i),
            amount=Decimal("5000.00"),
            status=PaymentStatus.PENDING,
        )
        db_session.add(pp)
    await db_session.flush()

    result = await dashboard_service.get_dashboard(db_session, user.id, today=today)
    assert len(result.next_payments) == 3  # Limited to 3


@pytest.mark.asyncio()
async def test_dashboard_totals_with_balance(db_session: AsyncSession):
    """Given: loan with balance, When: dashboard, Then: totals reflect debt."""
    user = await _create_user(db_session)
    loan = await _create_loan(db_session, user)
    balance = LoanBalance(
        loan_id=loan.id,
        snapshot_date=date(2026, 5, 1),
        current_balance=Decimal("80000.00"),
        principal_balance=Decimal("78000.00"),
        accrued_interest=Decimal("2000.00"),
        source="calculated",
    )
    db_session.add(balance)
    await db_session.flush()

    result = await dashboard_service.get_dashboard(
        db_session, user.id, today=date(2026, 5, 1)
    )
    assert result.totals.active_loans == 1
    assert Decimal(result.totals.total_debt) == Decimal("80000.00")


@pytest.mark.asyncio()
async def test_dashboard_overdue_warning(db_session: AsyncSession):
    """Given: overdue payment, When: dashboard, Then: warning generated."""
    user = await _create_user(db_session)
    loan = await _create_loan(db_session, user)

    pp = PlannedPayment(
        user_id=user.id,
        loan_id=loan.id,
        due_date=date(2026, 4, 28),
        amount=Decimal("10000.00"),
        status=PaymentStatus.OVERDUE,
    )
    db_session.add(pp)
    await db_session.flush()

    result = await dashboard_service.get_dashboard(
        db_session, user.id, today=date(2026, 5, 1)
    )
    assert len(result.warnings) >= 1
    assert result.warnings[0].type == "overdue_payment"


@pytest.mark.asyncio()
async def test_dashboard_fixed_date_warning(db_session: AsyncSession):
    """Given: can_pay_early=False payment soon, When: dashboard, Then: fixed_date warning."""
    user = await _create_user(db_session)
    loan = await _create_loan(db_session, user)

    today = date(2026, 5, 1)
    pp = PlannedPayment(
        user_id=user.id,
        loan_id=loan.id,
        due_date=today + timedelta(days=3),
        amount=Decimal("18000.00"),
        status=PaymentStatus.PENDING,
        can_pay_early=False,
    )
    db_session.add(pp)
    await db_session.flush()

    result = await dashboard_service.get_dashboard(db_session, user.id, today=today)
    fixed_warns = [w for w in result.warnings if w.type == "fixed_date_payment"]
    assert len(fixed_warns) == 1


# ---------------------------------------------------------------------------
# HTTP API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_api_dashboard_returns_200(auth_client: AsyncClient):
    """Given: auth, When: GET /api/dashboard, Then: 200 + valid structure."""
    resp = await auth_client.get("/api/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert "next_payments" in body
    assert "current_period" in body
    assert "totals" in body
    assert "warnings" in body


@pytest.mark.asyncio()
async def test_api_forecast_returns_200(auth_client: AsyncClient):
    """Given: auth + params, When: GET /api/forecast/balance-by-day, Then: 200."""
    resp = await auth_client.get(
        "/api/forecast/balance-by-day",
        params={"from": "2026-05-01", "to": "2026-05-05", "starting_balance": "50000"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["from_date"] == "2026-05-01"
    assert body["to_date"] == "2026-05-05"
    assert len(body["points"]) == 5


@pytest.mark.asyncio()
async def test_api_forecast_invalid_balance_returns_400(auth_client: AsyncClient):
    """Given: bad starting_balance, When: GET forecast, Then: 400."""
    resp = await auth_client.get(
        "/api/forecast/balance-by-day",
        params={"from": "2026-05-01", "to": "2026-05-05", "starting_balance": "abc"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio()
async def test_api_dashboard_unauthenticated(db_session: AsyncSession):
    """Given: no auth, When: GET /api/dashboard, Then: 401/403."""
    async def _override_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            resp = await ac.get("/api/dashboard")
            assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()
