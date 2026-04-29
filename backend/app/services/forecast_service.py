"""ForecastService — daily balance projection.

Implements architecture §5.3: builds a "free money by day" curve
from a starting balance, incomes, and planned payments over a date range.

Pure read-only service — no writes to the database.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import IncomeStatus, PaymentStatus
from app.domain.models.income import Income
from app.domain.models.payment import PlannedPayment
from app.domain.models.settings import Setting
from app.domain.schemas.dashboard import DailyBalance


async def _get_setting_decimal(
    session: AsyncSession,
    user_id: uuid.UUID,
    key: str,
    default: Decimal = Decimal("0"),
) -> Decimal:
    """Read a numeric setting value from the DB."""
    stmt = select(Setting.value).where(
        Setting.user_id == user_id,
        Setting.key == key,
    )
    result = await session.execute(stmt)
    raw = result.scalar_one_or_none()
    if raw is None:
        return default
    try:
        return Decimal(raw)
    except Exception:
        return default


async def forecast_balance_by_day(
    session: AsyncSession,
    user_id: uuid.UUID,
    starting_balance: Decimal,
    from_date: date,
    to_date: date,
) -> list[DailyBalance]:
    """Build daily balance projection over [from_date, to_date].

    Algorithm (architecture §5.3):
    1. Start with starting_balance minus unavailable_balance setting.
    2. Walk each day from_date to to_date:
       - add incomes with expected_date == day and status in (expected, received)
       - subtract planned_payments with due_date == day and status == pending
    3. Return list of (date, balance) points.
    """
    if from_date > to_date:
        return []

    # Subtract unavailable reserve from starting balance
    unavailable = await _get_setting_decimal(
        session, user_id, "unavailable_balance"
    )
    balance = starting_balance - unavailable

    # Pre-fetch incomes in range
    incomes_by_date: dict[date, Decimal] = {}
    stmt_inc = select(Income.expected_date, Income.amount).where(
        and_(
            Income.user_id == user_id,
            Income.expected_date >= from_date,
            Income.expected_date <= to_date,
            Income.status.in_([IncomeStatus.EXPECTED, IncomeStatus.RECEIVED]),
            Income.is_deleted.is_(False),
        )
    )
    rows = await session.execute(stmt_inc)
    for row in rows:
        d = row.expected_date
        incomes_by_date[d] = incomes_by_date.get(d, Decimal("0")) + row.amount

    # Pre-fetch pending planned payments in range
    payments_by_date: dict[date, Decimal] = {}
    stmt_pay = select(PlannedPayment.due_date, PlannedPayment.amount).where(
        and_(
            PlannedPayment.user_id == user_id,
            PlannedPayment.due_date >= from_date,
            PlannedPayment.due_date <= to_date,
            PlannedPayment.status == PaymentStatus.PENDING,
            PlannedPayment.is_deleted.is_(False),
        )
    )
    rows = await session.execute(stmt_pay)
    for row in rows:
        d = row.due_date
        payments_by_date[d] = payments_by_date.get(d, Decimal("0")) + row.amount

    # Walk day by day.
    # On income days, reset balance to 0 first so each salary period
    # is independent — no carry-over from previous period.
    points: list[DailyBalance] = []
    current = from_date
    while current <= to_date:
        day_income = incomes_by_date.get(current, Decimal("0"))
        if day_income > 0:
            balance = Decimal("0")
        balance += day_income
        balance -= payments_by_date.get(current, Decimal("0"))
        points.append(DailyBalance.from_values(current, balance))
        current += timedelta(days=1)

    return points
