"""Overlay action handlers — pure functions, no DB access.

Architecture §6.3: each handler mutates a ProjectedState copy in memory.
All calculations use decimal.Decimal.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.services.schedule_service import recalculate_after_prepayment
from app.services.simulation.projected_state import (
    ProjectedPayment,
    ProjectedState,
)

# ---------------------------------------------------------------------------
# Individual action handlers
# ---------------------------------------------------------------------------


def apply_close_early_full(
    state: ProjectedState,
    *,
    loan_id: uuid.UUID,
    effective_date: date,
) -> None:
    """Close a loan fully on effective_date.

    Architecture §6.2 close_early_full:
    - Removes all future pending payments for this loan after effective_date
    - Adds a synthetic full-payoff payment
    - Sets loan balance to zero
    """
    loan = state.loans.get(loan_id)
    if loan is None:
        return

    balance = loan.principal_balance + loan.accrued_interest
    if balance <= Decimal("0.00"):
        return

    # Cancel future pending payments
    for p in state.pending_payments(loan_id=loan_id):
        if p.due_date >= effective_date:
            p.status = "cancelled"

    # Add synthetic full payoff
    state.add_synthetic_payment(
        loan_id=loan_id,
        loan_name=loan.name,
        due_date=effective_date,
        amount=balance,
        principal_part=loan.principal_balance,
        interest_part=loan.accrued_interest,
    )

    loan.principal_balance = Decimal("0.00")
    loan.accrued_interest = Decimal("0.00")
    loan.status = "paid_off"


def apply_prepayment_partial(
    state: ProjectedState,
    *,
    loan_id: uuid.UUID,
    effective_date: date,
    amount: Decimal,
) -> None:
    """Partial prepayment — reduce balance, regenerate schedule.

    Architecture §6.2 prepayment_partial:
    - Decrease principal by amount
    - Cancel future pending payments after effective_date
    - Regenerate schedule from new principal using loan's prepayment_strategy
    """
    loan = state.loans.get(loan_id)
    if loan is None:
        return

    # Reduce principal
    actual_reduction = min(amount, loan.principal_balance)
    new_principal = loan.principal_balance - actual_reduction
    loan.principal_balance = new_principal

    # Add synthetic prepayment
    state.add_synthetic_payment(
        loan_id=loan_id,
        loan_name=loan.name,
        due_date=effective_date,
        amount=actual_reduction,
        principal_part=actual_reduction,
        interest_part=Decimal("0.00"),
    )

    if new_principal <= Decimal("0.00"):
        # Fully paid off
        loan.status = "paid_off"
        for p in state.pending_payments(loan_id=loan_id):
            if p.due_date > effective_date:
                p.status = "cancelled"
        return

    # Cancel future pending payments
    for p in state.pending_payments(loan_id=loan_id):
        if p.due_date > effective_date:
            p.status = "cancelled"

    # Regenerate schedule from new principal
    _regenerate_projected_schedule(
        state,
        loan=loan,
        new_principal=new_principal,
        from_date=effective_date,
    )


def apply_reduce_payment(
    state: ProjectedState,
    *,
    planned_payment_id: uuid.UUID,
    new_amount: Decimal,
) -> None:
    """Change the amount of a specific planned payment.

    Architecture §6.2 reduce_payment:
    Used for closing Split installments early with a reduced amount.
    """
    for p in state.payments:
        if p.id == planned_payment_id and p.status == "pending":
            p.amount = new_amount
            break


def apply_skip(
    state: ProjectedState,
    *,
    planned_payment_id: uuid.UUID,
) -> None:
    """Skip a planned payment.

    Architecture §6.2 skip:
    The payment is marked as skipped in the projection.
    """
    for p in state.payments:
        if p.id == planned_payment_id and p.status == "pending":
            p.status = "skipped"
            break


def apply_add_income(
    state: ProjectedState,
    *,
    effective_date: date,
    amount: Decimal,
    name: str,
) -> None:
    """Add a synthetic income event.

    Architecture §6.2 add_income:
    Additional income (bonus, sale, etc.) injected into the projection.
    """
    state.add_synthetic_income(
        expected_date=effective_date,
        amount=amount,
        name=name,
    )


def apply_change_payment_date(
    state: ProjectedState,
    *,
    planned_payment_id: uuid.UUID,
    new_date: date,
) -> None:
    """Move a planned payment to a new date.

    Architecture §6.2 change_payment_date:
    Reschedules a specific payment.
    """
    for p in state.payments:
        if p.id == planned_payment_id and p.status == "pending":
            p.due_date = new_date
            break


# ---------------------------------------------------------------------------
# Dispatcher — applies a single action to state
# ---------------------------------------------------------------------------


def apply_action(
    state: ProjectedState,
    *,
    action_type: str,
    loan_id: uuid.UUID | None,
    planned_payment_id: uuid.UUID | None,
    effective_date: date,
    params: dict | None,
) -> None:
    """Apply one scenario action to the projected state.

    This is the central dispatcher called by the engine for each action.
    """
    p = params or {}

    if action_type == "close_early_full":
        if loan_id is None:
            return
        apply_close_early_full(state, loan_id=loan_id, effective_date=effective_date)

    elif action_type == "prepayment_partial":
        if loan_id is None:
            return
        apply_prepayment_partial(
            state,
            loan_id=loan_id,
            effective_date=effective_date,
            amount=Decimal(p.get("amount", "0")),
        )

    elif action_type == "reduce_payment":
        if planned_payment_id is None:
            return
        apply_reduce_payment(
            state,
            planned_payment_id=planned_payment_id,
            new_amount=Decimal(p.get("new_amount", "0")),
        )

    elif action_type == "skip":
        if planned_payment_id is None:
            return
        apply_skip(state, planned_payment_id=planned_payment_id)

    elif action_type == "add_income":
        apply_add_income(
            state,
            effective_date=effective_date,
            amount=Decimal(p.get("amount", "0")),
            name=p.get("name", ""),
        )

    elif action_type == "change_payment_date":
        if planned_payment_id is None:
            return
        apply_change_payment_date(
            state,
            planned_payment_id=planned_payment_id,
            new_date=(
                date.fromisoformat(p["new_date"])
                if isinstance(p.get("new_date"), str)
                else p.get("new_date", effective_date)
            ),
        )


# ---------------------------------------------------------------------------
# Internal: schedule regeneration for overlay
# ---------------------------------------------------------------------------


def _regenerate_projected_schedule(
    state: ProjectedState,
    *,
    loan: ProjectedLoan,  # noqa: F821 — forward ref, same module
    new_principal: Decimal,
    from_date: date,
) -> None:
    """Regenerate future schedule entries in the projection.

    Uses the same ScheduleService pure functions as the real engine.
    """
    months = loan.months_remaining
    if months is None or months <= 0:
        return

    payment_day = loan.payment_day or from_date.day
    strategy = loan.prepayment_strategy

    # Find the current annuity for shorten_term strategy
    current_annuity: Decimal | None = None
    if strategy == "shorten_term":
        pending = [
            p for p in state.payments
            if p.loan_id == loan.id and p.status == "pending" and p.kind == "real"
        ]
        if pending:
            current_annuity = pending[0].amount

    new_entries = recalculate_after_prepayment(
        new_principal=new_principal,
        annual_rate=loan.interest_rate,
        months_remaining=months,
        prepayment_date=from_date,
        payment_day=payment_day,
        strategy=strategy,
        current_annuity=current_annuity,
    )

    for entry in new_entries:
        state.payments.append(
            ProjectedPayment(
                id=None,
                loan_id=loan.id,
                loan_name=loan.name,
                due_date=entry.due_date,
                amount=entry.amount,
                principal_part=entry.principal_part,
                interest_part=entry.interest_part,
                status="pending",
                kind="synthetic",
            )
        )
