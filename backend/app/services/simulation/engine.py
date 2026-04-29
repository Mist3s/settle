"""Simulation engine — builds as-is / to-be / diff projections.

Architecture §6.5: GET /api/scenarios/{id}/forecast returns both
projections in one response so the frontend can render side-by-side.

This module is the orchestrator: it loads DB state into ProjectedState,
applies scenario actions to a copy, then computes daily balance curves
and numeric diffs.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import IncomeStatus, LoanStatus, PaymentStatus
from app.domain.models.balance import LoanBalance
from app.domain.models.income import Income
from app.domain.models.loan import Loan
from app.domain.models.payment import PlannedPayment
from app.domain.models.scenario import Scenario
from app.domain.schemas.dashboard import DailyBalance
from app.domain.schemas.simulation import (
    PaymentSummary,
    ProjectionData,
    ScenarioForecastDiff,
    ScenarioForecastResponse,
)
from app.services.simulation.actions import apply_action
from app.services.simulation.projected_state import (
    ProjectedIncome,
    ProjectedLoan,
    ProjectedPayment,
    ProjectedState,
)


async def _load_projected_state(
    session: AsyncSession,
    user_id: uuid.UUID,
    from_date: date,
    to_date: date,
) -> ProjectedState:
    """Load current DB state into an in-memory ProjectedState."""
    state = ProjectedState()

    # Load active loans with latest balance
    loan_stmt = select(Loan).where(
        Loan.user_id == user_id,
        Loan.status == LoanStatus.ACTIVE,
        Loan.is_deleted.is_(False),
    )
    loan_rows = await session.execute(loan_stmt)
    loans = list(loan_rows.scalars().all())

    for loan in loans:
        # Get latest balance snapshot
        bal_stmt = (
            select(LoanBalance)
            .where(LoanBalance.loan_id == loan.id)
            .order_by(LoanBalance.snapshot_date.desc())
            .limit(1)
        )
        bal_row = await session.execute(bal_stmt)
        balance = bal_row.scalar_one_or_none()

        state.loans[loan.id] = ProjectedLoan(
            id=loan.id,
            name=loan.name,
            creditor=loan.creditor or "",
            principal_balance=balance.principal_balance if balance else Decimal("0.00"),
            accrued_interest=balance.accrued_interest if balance else Decimal("0.00"),
            interest_rate=loan.interest_rate,
            months_remaining=loan.months_remaining,
            payment_day=loan.payment_day,
            prepayment_strategy=(
                loan.prepayment_strategy.value
                if loan.prepayment_strategy
                else "reduce_payment"
            ),
            status=loan.status.value,
        )

    # Load pending planned payments in range
    pp_stmt = select(PlannedPayment).where(
        and_(
            PlannedPayment.user_id == user_id,
            PlannedPayment.due_date >= from_date,
            PlannedPayment.due_date <= to_date,
            PlannedPayment.status == PaymentStatus.PENDING,
            PlannedPayment.is_deleted.is_(False),
        )
    )
    pp_rows = await session.execute(pp_stmt)
    for pp in pp_rows.scalars().all():
        loan_info = state.loans.get(pp.loan_id)
        state.payments.append(
            ProjectedPayment(
                id=pp.id,
                loan_id=pp.loan_id,
                loan_name=loan_info.name if loan_info else "",
                due_date=pp.due_date,
                amount=pp.amount,
                principal_part=pp.principal_part or Decimal("0.00"),
                interest_part=pp.interest_part or Decimal("0.00"),
                status="pending",
                kind="real",
            )
        )

    # Load expected incomes in range
    inc_stmt = select(Income).where(
        and_(
            Income.user_id == user_id,
            Income.expected_date >= from_date,
            Income.expected_date <= to_date,
            Income.status.in_([IncomeStatus.EXPECTED, IncomeStatus.RECEIVED]),
            Income.is_deleted.is_(False),
        )
    )
    inc_rows = await session.execute(inc_stmt)
    for inc in inc_rows.scalars().all():
        state.incomes.append(
            ProjectedIncome(
                id=inc.id,
                expected_date=inc.expected_date,
                amount=inc.amount,
                name=inc.name,
                kind="real",
            )
        )

    return state


def _compute_daily_balance(
    state: ProjectedState,
    from_date: date,
    to_date: date,
    starting_balance: Decimal,
) -> list[DailyBalance]:
    """Walk day-by-day computing balance from projected state."""
    # Build lookup dicts
    income_by_date: dict[date, Decimal] = {}
    for inc in state.incomes:
        d = inc.expected_date
        income_by_date[d] = income_by_date.get(d, Decimal("0")) + inc.amount

    payment_by_date: dict[date, Decimal] = {}
    for p in state.payments:
        if p.status not in ("pending",):
            continue
        d = p.due_date
        payment_by_date[d] = payment_by_date.get(d, Decimal("0")) + p.amount

    points: list[DailyBalance] = []
    balance = starting_balance
    current = from_date
    while current <= to_date:
        balance += income_by_date.get(current, Decimal("0"))
        balance -= payment_by_date.get(current, Decimal("0"))
        points.append(DailyBalance.from_values(current, balance))
        current += timedelta(days=1)

    return points


def _build_payment_summaries(state: ProjectedState) -> list[PaymentSummary]:
    """Convert projected payments to response DTOs."""
    return [
        PaymentSummary(
            loan_id=str(p.loan_id),
            loan_name=p.loan_name,
            due_date=p.due_date,
            amount=str(p.amount),
            status=p.status,
            kind=p.kind,
        )
        for p in state.payments
    ]


def _compute_diff(
    current_state: ProjectedState,
    scenario_state: ProjectedState,
    current_points: list[DailyBalance],
    scenario_points: list[DailyBalance],
) -> ScenarioForecastDiff:
    """Compute numeric difference between two projections."""
    # Total paid = sum of pending payment amounts
    current_total = sum(
        p.amount for p in current_state.payments if p.status == "pending"
    )
    scenario_total = sum(
        p.amount for p in scenario_state.payments if p.status == "pending"
    )
    total_diff = scenario_total - current_total

    # Interest saved: sum of interest parts
    current_interest = sum(
        p.interest_part for p in current_state.payments if p.status == "pending"
    )
    scenario_interest = sum(
        p.interest_part for p in scenario_state.payments if p.status == "pending"
    )
    interest_saved = current_interest - scenario_interest  # positive = saved

    # First zero balance date (when all loans paid off)
    def _first_zero(points: list[DailyBalance]) -> date | None:
        # Not exactly "zero balance" but rather the last payment date
        # More meaningful: date when total debt reaches zero
        return None  # simplified for now — proper implementation needs
        # tracking of per-loan balances over time

    return ScenarioForecastDiff(
        total_paid_difference=str(total_diff),
        total_interest_saved=str(interest_saved),
        first_zero_balance_date_current=None,
        first_zero_balance_date_scenario=None,
    )


async def build_forecast(
    session: AsyncSession,
    user_id: uuid.UUID,
    scenario: Scenario,
    from_date: date,
    to_date: date,
    starting_balance: Decimal,
) -> ScenarioForecastResponse:
    """Build as-is + to-be forecast for a scenario.

    Architecture §6.5: one endpoint, both projections.

    1. Load current state from DB
    2. Compute as-is daily balance
    3. Deep-copy state, apply scenario actions
    4. Compute to-be daily balance
    5. Compute diff
    """
    # 1. Load base state
    base_state = await _load_projected_state(session, user_id, from_date, to_date)

    # Get unavailable_balance for starting balance adjustment
    from app.services.forecast_service import _get_setting_decimal

    unavailable = await _get_setting_decimal(session, user_id, "unavailable_balance")
    adjusted_balance = starting_balance - unavailable

    # 2. As-is projection
    current_points = _compute_daily_balance(base_state, from_date, to_date, adjusted_balance)
    current_payments = _build_payment_summaries(base_state)

    # 3. Copy and apply actions
    scenario_state = base_state.copy()
    actions = sorted(scenario.actions, key=lambda a: a.effective_date)
    for action in actions:
        apply_action(
            scenario_state,
            action_type=action.action_type.value,
            loan_id=action.loan_id,
            planned_payment_id=action.planned_payment_id,
            effective_date=action.effective_date,
            params=action.params,
        )

    # 4. To-be projection
    scenario_points = _compute_daily_balance(
        scenario_state, from_date, to_date, adjusted_balance
    )
    scenario_payments = _build_payment_summaries(scenario_state)

    # 5. Diff
    diff = _compute_diff(base_state, scenario_state, current_points, scenario_points)

    return ScenarioForecastResponse(
        current=ProjectionData(
            balance_by_day=current_points,
            payments=current_payments,
        ),
        scenario=ProjectionData(
            balance_by_day=scenario_points,
            payments=scenario_payments,
        ),
        diff=diff,
    )
