"""DashboardService — aggregates for the main dashboard view.

Provides a single ``get_dashboard()`` that returns all widgets in one call,
matching the architecture §8.2 Dashboard contract.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import IncomeStatus, LoanStatus, PaymentStatus
from app.domain.models.balance import LoanBalance
from app.domain.models.income import Income
from app.domain.models.loan import Loan
from app.domain.models.payment import PlannedPayment
from app.domain.models.settings import Setting
from app.domain.schemas.dashboard import (
    CurrentPeriod,
    DashboardResponse,
    DashboardTotals,
    DashboardWarning,
    NextPayment,
)


async def _get_setting_value(
    session: AsyncSession,
    user_id: uuid.UUID,
    key: str,
    default: str = "0",
) -> str:
    stmt = select(Setting.value).where(
        Setting.user_id == user_id,
        Setting.key == key,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() or default


async def _next_payments(
    session: AsyncSession,
    user_id: uuid.UUID,
    today: date,
    limit: int = 3,
) -> list[NextPayment]:
    """Return the next N pending/overdue payments with loan info."""
    stmt = (
        select(
            PlannedPayment.loan_id,
            PlannedPayment.due_date,
            PlannedPayment.amount,
            PlannedPayment.status,
            PlannedPayment.can_pay_early,
            Loan.name.label("loan_name"),
            Loan.creditor,
        )
        .join(Loan, PlannedPayment.loan_id == Loan.id)
        .where(
            PlannedPayment.user_id == user_id,
            PlannedPayment.due_date >= today,
            PlannedPayment.status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE]),
            PlannedPayment.is_deleted.is_(False),
            Loan.is_deleted.is_(False),
        )
        .order_by(PlannedPayment.due_date)
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return [
        NextPayment(
            loan_id=str(r.loan_id),
            loan_name=r.loan_name,
            creditor=r.creditor,
            due_date=r.due_date,
            amount=str(r.amount),
            status=r.status,
            can_pay_early=r.can_pay_early,
        )
        for r in rows
    ]


async def _current_period(
    session: AsyncSession,
    user_id: uuid.UUID,
    today: date,
) -> CurrentPeriod:
    """Compute the financial summary for the current salary period.

    Salary period = [current_income_date .. next_income_date - 1].
    If today is before the first income, show the first full period.
    """
    income_filter = and_(
        Income.user_id == user_id,
        Income.status.in_([IncomeStatus.EXPECTED, IncomeStatus.RECEIVED]),
        Income.is_deleted.is_(False),
    )

    # 1. Find the most recent income on or before today (prev_income).
    stmt_prev = (
        select(Income.expected_date, Income.amount)
        .where(income_filter, Income.expected_date <= today)
        .order_by(Income.expected_date.desc())
        .limit(1)
    )
    prev_row = (await session.execute(stmt_prev)).first()

    # 2. Find the first income strictly after today (next_income).
    stmt_next = (
        select(Income.expected_date, Income.amount)
        .where(income_filter, Income.expected_date > today)
        .order_by(Income.expected_date)
        .limit(1)
    )
    next_row = (await session.execute(stmt_next)).first()

    if prev_row is not None:
        # We are inside an existing salary period.
        period_start = prev_row.expected_date
        income_amount = prev_row.amount
        if next_row is not None:
            period_end = next_row.expected_date - timedelta(days=1)
        else:
            # No next income — assume 30 days from period start.
            period_end = period_start + timedelta(days=30)
    elif next_row is not None:
        # Today is before the first income — show the first full period.
        period_start = next_row.expected_date
        income_amount = next_row.amount
        # Find the income after the first one for the period end.
        stmt_second = (
            select(Income.expected_date)
            .where(income_filter, Income.expected_date > next_row.expected_date)
            .order_by(Income.expected_date)
            .limit(1)
        )
        second_row = (await session.execute(stmt_second)).first()
        if second_row is not None:
            period_end = second_row.expected_date - timedelta(days=1)
        else:
            period_end = period_start + timedelta(days=30)
    else:
        # No incomes at all — fallback.
        period_start = today
        period_end = today + timedelta(days=30)
        income_amount = Decimal("0")

    # Sum pending planned payments in period [period_start, period_end].
    stmt_payments = select(func.coalesce(func.sum(PlannedPayment.amount), 0)).where(
        and_(
            PlannedPayment.user_id == user_id,
            PlannedPayment.due_date >= period_start,
            PlannedPayment.due_date <= period_end,
            PlannedPayment.status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE]),
            PlannedPayment.is_deleted.is_(False),
        )
    )
    payments_total = (await session.execute(stmt_payments)).scalar() or Decimal("0")
    payments_total = Decimal(str(payments_total))

    # Get living minimum setting
    living_min_raw = await _get_setting_value(
        session, user_id, "living_minimum_per_period"
    )
    living_min = Decimal(living_min_raw) if living_min_raw != "0" else Decimal("0")

    remaining = income_amount - payments_total
    remaining_for_living = remaining - living_min

    # Traffic light status
    if remaining_for_living >= living_min:
        status = "comfortable"
    elif remaining_for_living >= Decimal("0"):
        status = "tight"
    else:
        status = "deficit"

    return CurrentPeriod(
        from_date=period_start,
        to_date=period_end,
        income=str(income_amount),
        planned_payments_total=str(payments_total),
        remaining_for_living=str(remaining_for_living),
        status=status,
    )


async def _totals(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> DashboardTotals:
    """Compute aggregate debt totals across all active loans."""
    # Active loans count
    stmt_count = select(func.count()).where(
        Loan.user_id == user_id,
        Loan.status == LoanStatus.ACTIVE,
        Loan.is_deleted.is_(False),
    )
    active_count = (await session.execute(stmt_count)).scalar() or 0

    # Total debt: sum of latest balance per active loan
    # Subquery: latest balance per loan
    latest_balance_sq = (
        select(
            LoanBalance.loan_id,
            func.max(LoanBalance.snapshot_date).label("max_date"),
        )
        .group_by(LoanBalance.loan_id)
        .subquery()
    )

    stmt_debt = select(func.coalesce(func.sum(LoanBalance.current_balance), 0)).where(
        and_(
            LoanBalance.loan_id == latest_balance_sq.c.loan_id,
            LoanBalance.snapshot_date == latest_balance_sq.c.max_date,
        )
    )
    # Filter to active loans only
    active_loan_ids = select(Loan.id).where(
        Loan.user_id == user_id,
        Loan.status == LoanStatus.ACTIVE,
        Loan.is_deleted.is_(False),
    )
    stmt_debt = stmt_debt.where(LoanBalance.loan_id.in_(active_loan_ids))
    total_debt = Decimal(str((await session.execute(stmt_debt)).scalar() or 0))

    # Month-to-month change: simplified — diff of total_debt vs 30 days ago
    # For now return "0.00" as a placeholder; proper calculation needs
    # historical balance data or a materialized snapshot, which isn't
    # available until we have accrue_interest running daily.
    m2m_change = Decimal("0.00")

    return DashboardTotals(
        total_debt=str(total_debt),
        active_loans=active_count,
        month_to_month_change=str(m2m_change),
    )


async def _warnings(
    session: AsyncSession,
    user_id: uuid.UUID,
    today: date,
) -> list[DashboardWarning]:
    """Generate dashboard warnings."""
    warnings: list[DashboardWarning] = []

    # 1. Overdue payments
    stmt_overdue = (
        select(
            PlannedPayment.due_date,
            PlannedPayment.amount,
            Loan.name.label("loan_name"),
        )
        .join(Loan, PlannedPayment.loan_id == Loan.id)
        .where(
            PlannedPayment.user_id == user_id,
            PlannedPayment.status == PaymentStatus.OVERDUE,
            PlannedPayment.is_deleted.is_(False),
        )
        .order_by(PlannedPayment.due_date)
        .limit(5)
    )
    overdue_rows = await session.execute(stmt_overdue)
    for r in overdue_rows:
        warnings.append(DashboardWarning(
            type="overdue_payment",
            message=f"Просрочен платёж: {r.loan_name} — {r.amount} ₽ ({r.due_date})",
        ))

    # 2. Fixed-date payments coming soon (can_pay_early=False within 7 days)
    week_ahead = today + timedelta(days=7)
    stmt_fixed = (
        select(
            PlannedPayment.due_date,
            PlannedPayment.amount,
            Loan.name.label("loan_name"),
        )
        .join(Loan, PlannedPayment.loan_id == Loan.id)
        .where(
            PlannedPayment.user_id == user_id,
            PlannedPayment.due_date >= today,
            PlannedPayment.due_date <= week_ahead,
            PlannedPayment.can_pay_early.is_(False),
            PlannedPayment.status == PaymentStatus.PENDING,
            PlannedPayment.is_deleted.is_(False),
        )
        .order_by(PlannedPayment.due_date)
        .limit(5)
    )
    fixed_rows = await session.execute(stmt_fixed)
    for r in fixed_rows:
        warnings.append(DashboardWarning(
            type="fixed_date_payment",
            message=(
                f"{r.due_date.strftime('%d %B')} — {r.loan_name} "
                f"{r.amount} ₽, нельзя погасить заранее"
            ),
        ))

    return warnings


async def get_dashboard(
    session: AsyncSession,
    user_id: uuid.UUID,
    today: date | None = None,
) -> DashboardResponse:
    """Build the full dashboard response in one call.

    ``today`` can be overridden for testing.
    """
    if today is None:
        today = date.today()

    next_pay = await _next_payments(session, user_id, today)
    period = await _current_period(session, user_id, today)
    total = await _totals(session, user_id)
    warns = await _warnings(session, user_id, today)

    return DashboardResponse(
        next_payments=next_pay,
        current_period=period,
        totals=total,
        warnings=warns,
    )
