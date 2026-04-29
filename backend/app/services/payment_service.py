"""PaymentService — payment registration with full financial chain.

This is the core mutating engine (architecture section 5.2).
Registration of an actual payment triggers:
  1. Determine payment type from amount comparison
  2. Create actual_payment record
  3. Recalculate balance snapshot
  4. Regenerate future schedule (if prepayment/overpayment)
  5. Update planned_payment status
  6. Audit log all mutations
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    ActualPaymentType,
    AuditAction,
    BalanceSource,
    PaymentAccuracy,
    PaymentStatus,
)
from app.domain.models.loan import Loan
from app.domain.models.payment import ActualPayment, PlannedPayment
from app.repositories.loan_repo import LoanRepository
from app.repositories.payment_repo import (
    ActualPaymentRepository,
    PlannedPaymentRepository,
)
from app.services import audit_service, balance_service, schedule_service

# ------------------------------------------------------------------
# Planned Payments (unchanged CRUD from stage 4)
# ------------------------------------------------------------------


async def list_planned(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    loan_id: uuid.UUID | None = None,
    income_id: uuid.UUID | None = None,
) -> list[PlannedPayment]:
    repo = PlannedPaymentRepository(session)
    filters: dict = {"user_id": user_id}
    if loan_id is not None:
        filters["loan_id"] = loan_id
    if income_id is not None:
        filters["income_id"] = income_id
    return await repo.list(filters=filters)


async def get_planned(
    session: AsyncSession,
    user_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> PlannedPayment | None:
    repo = PlannedPaymentRepository(session)
    payment = await repo.get(payment_id)
    if payment is None or payment.user_id != user_id:
        return None
    return payment


async def update_planned(
    session: AsyncSession,
    user_id: uuid.UUID,
    payment_id: uuid.UUID,
    **kwargs,
) -> PlannedPayment | None:
    repo = PlannedPaymentRepository(session)
    payment = await repo.get(payment_id)
    if payment is None or payment.user_id != user_id:
        return None
    before = audit_service.model_to_dict(payment)
    if kwargs:
        await repo.update(payment_id, **kwargs)
    after = audit_service.model_to_dict(payment)
    await audit_service.record(
        session,
        entity_type="planned_payments",
        entity_id=payment.id,
        action=AuditAction.UPDATE,
        before_state=before,
        after_state=after,
        changed_by=user_id,
    )
    return payment


# ------------------------------------------------------------------
# Actual Payments — simple CRUD helpers
# ------------------------------------------------------------------


async def list_actual(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    loan_id: uuid.UUID | None = None,
) -> list[ActualPayment]:
    """List actual payments for user's loans."""
    loan_repo = LoanRepository(session)
    filters_loan: dict = {"user_id": user_id}
    if loan_id is not None:
        filters_loan["id"] = loan_id
    user_loans = await loan_repo.list(filters=filters_loan)
    user_loan_ids = {ln.id for ln in user_loans}
    if not user_loan_ids:
        return []

    repo = ActualPaymentRepository(session)
    result: list[ActualPayment] = []
    for lid in user_loan_ids:
        result.extend(await repo.list(filters={"loan_id": lid}))
    return result


async def delete_actual(
    session: AsyncSession,
    user_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> ActualPayment | None:
    """Delete an actual payment, verifying loan ownership."""
    repo = ActualPaymentRepository(session)
    payment = await repo.get(payment_id)
    if payment is None:
        return None

    loan_repo = LoanRepository(session)
    loan = await loan_repo.get(payment.loan_id)
    if loan is None or loan.user_id != user_id:
        return None

    before = audit_service.model_to_dict(payment)
    await session.delete(payment)
    await session.flush()
    await audit_service.record(
        session,
        entity_type="actual_payments",
        entity_id=payment.id,
        action=AuditAction.DELETE,
        before_state=before,
        changed_by=user_id,
    )
    return payment


# ------------------------------------------------------------------
# Payment type determination
# ------------------------------------------------------------------


def determine_payment_type(
    actual_amount: Decimal,
    planned_amount: Decimal | None,
    loan_balance: Decimal,
) -> ActualPaymentType:
    """Determine the payment type from the amounts.

    Architecture section 5.2, step 1:
    - amount == planned → regular
    - amount > planned → overpayment
    - amount < planned and amount > 0 → underpayment
    - amount == 0 → missed
    - amount >= loan_balance (no planned or early) → early_full
    - otherwise → early_partial
    """
    if actual_amount == Decimal("0"):
        return ActualPaymentType.MISSED

    if planned_amount is not None:
        if actual_amount == planned_amount:
            return ActualPaymentType.REGULAR
        if actual_amount > planned_amount:
            return ActualPaymentType.OVERPAYMENT
        # actual_amount < planned_amount
        return ActualPaymentType.UNDERPAYMENT

    # No planned payment — standalone payment
    if actual_amount >= loan_balance:
        return ActualPaymentType.EARLY_FULL
    return ActualPaymentType.EARLY_PARTIAL


# ------------------------------------------------------------------
# Core engine: register actual payment
# ------------------------------------------------------------------


async def register_payment(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    loan_id: uuid.UUID,
    amount: Decimal,
    payment_date: date,
    planned_payment_id: uuid.UUID | None = None,
    payment_type: ActualPaymentType | None = None,
    principal_part: Decimal | None = None,
    interest_part: Decimal | None = None,
    notes: str | None = None,
) -> ActualPayment:
    """Register a factual payment with the full financial chain.

    Steps (architecture section 5.2):
    1. Verify loan ownership
    2. Get latest balance & planned payment
    3. Determine payment type (or use explicit)
    4. Calculate interest/principal split if not provided
    5. Create actual_payment
    6. Create new balance snapshot
    7. If prepayment/overpayment — regenerate future schedule
    8. Update planned_payment status
    9. Audit log everything
    """
    # 1. Verify loan
    loan_repo = LoanRepository(session)
    loan = await loan_repo.get(loan_id)
    if loan is None or loan.user_id != user_id:
        msg = f"Кредит {loan_id} не найден"
        raise ValueError(msg)

    # 2. Get latest balance
    latest_balance = await balance_service.get_latest(session, loan_id)
    current_principal = (
        latest_balance.principal_balance if latest_balance else Decimal("0.00")
    )
    current_accrued = (
        latest_balance.accrued_interest if latest_balance else Decimal("0.00")
    )

    # 2b. Get planned payment if referenced
    planned: PlannedPayment | None = None
    planned_amount: Decimal | None = None
    if planned_payment_id is not None:
        planned_repo = PlannedPaymentRepository(session)
        planned = await planned_repo.get(planned_payment_id)
        if planned is not None:
            planned_amount = planned.amount

    # 3. Determine payment type
    if payment_type is None:
        current_balance_total = current_principal + current_accrued
        payment_type = determine_payment_type(
            amount, planned_amount, current_balance_total
        )

    # 4. Calculate interest/principal split
    if interest_part is None:
        if payment_type == ActualPaymentType.MISSED:
            interest_part = Decimal("0.00")
        elif planned is not None and planned.interest_part is not None:
            interest_part = planned.interest_part
        else:
            # Use accrued interest as the interest portion
            interest_part = min(current_accrued, amount)

    if principal_part is None:
        principal_part = max(amount - interest_part, Decimal("0.00"))

    # 5. Create actual_payment
    actual_repo = ActualPaymentRepository(session)
    actual = await actual_repo.create(
        loan_id=loan_id,
        planned_payment_id=planned_payment_id,
        amount=amount,
        principal_part=principal_part,
        interest_part=interest_part,
        payment_date=payment_date,
        payment_type=payment_type,
        notes=notes,
    )
    await audit_service.record(
        session,
        entity_type="actual_payments",
        entity_id=actual.id,
        action=AuditAction.CREATE,
        after_state=audit_service.model_to_dict(actual),
        changed_by=user_id,
    )

    # 6. Create new balance snapshot
    new_principal = balance_service.calculate_new_principal(
        current_principal, amount, interest_part
    )
    if payment_type == ActualPaymentType.EARLY_FULL:
        new_principal = Decimal("0.00")

    await balance_service.create_snapshot(
        session,
        loan_id=loan_id,
        snapshot_date=payment_date,
        principal_balance=new_principal,
        accrued_interest=Decimal("0.00"),  # reset after payment
        source=BalanceSource.CALCULATED,
        notes=f"After {payment_type.value} payment",
        changed_by=user_id,
    )

    # 7. Regenerate future schedule if needed
    needs_regeneration = payment_type in (
        ActualPaymentType.EARLY_PARTIAL,
        ActualPaymentType.EARLY_FULL,
        ActualPaymentType.OVERPAYMENT,
    )

    if needs_regeneration and new_principal > Decimal("0.00"):
        await _regenerate_future_schedule(
            session,
            loan=loan,
            new_principal=new_principal,
            from_date=payment_date,
            user_id=user_id,
            old_annuity=planned_amount,
        )
    elif payment_type == ActualPaymentType.EARLY_FULL:
        # Cancel all future planned payments
        await _cancel_future_planned(session, loan_id, payment_date, user_id)
        # Mark loan as paid off
        before_loan = audit_service.model_to_dict(loan)
        await loan_repo.update(loan_id, status="paid_off")
        after_loan = audit_service.model_to_dict(loan)
        await audit_service.record(
            session,
            entity_type="loans",
            entity_id=loan.id,
            action=AuditAction.UPDATE,
            before_state=before_loan,
            after_state=after_loan,
            changed_by=user_id,
        )


    # 8. Update planned_payment status
    if planned is not None:
        planned_repo = PlannedPaymentRepository(session)
        before_planned = audit_service.model_to_dict(planned)

        if payment_type == ActualPaymentType.UNDERPAYMENT:
            new_status = PaymentStatus.PARTIAL
            underpaid = planned_amount - amount if planned_amount else Decimal("0.00")
            await planned_repo.update(
                planned.id,
                status=new_status,
                notes=f"Недоплачено: {underpaid} ₽",
            )
        elif payment_type == ActualPaymentType.MISSED:
            await planned_repo.update(planned.id, status=PaymentStatus.SKIPPED)
        else:
            await planned_repo.update(planned.id, status=PaymentStatus.PAID)

        after_planned = audit_service.model_to_dict(planned)
        await audit_service.record(
            session,
            entity_type="planned_payments",
            entity_id=planned.id,
            action=AuditAction.UPDATE,
            before_state=before_planned,
            after_state=after_planned,
            changed_by=user_id,
        )

    return actual


# ------------------------------------------------------------------
# Internal: schedule regeneration
# ------------------------------------------------------------------


async def _regenerate_future_schedule(
    session: AsyncSession,
    *,
    loan: Loan,
    new_principal: Decimal,
    from_date: date,
    user_id: uuid.UUID,
    old_annuity: Decimal | None = None,
) -> None:
    """Cancel future planned payments and generate a new schedule.

    Architecture section 5.2, step 4.
    """
    # Cancel existing future planned payments
    await _cancel_future_planned(session, loan.id, from_date, user_id)

    # Generate new schedule
    months = loan.months_remaining
    if months is None or months <= 0:
        return

    payment_day = loan.payment_day or from_date.day
    annual_rate = loan.interest_rate

    strategy = loan.prepayment_strategy.value if loan.prepayment_strategy else "reduce_payment"

    new_entries = schedule_service.recalculate_after_prepayment(
        new_principal=new_principal,
        annual_rate=annual_rate,
        months_remaining=months,
        prepayment_date=from_date,
        payment_day=payment_day,
        strategy=strategy,
        current_annuity=old_annuity,
    )

    # Create new planned payments
    planned_repo = PlannedPaymentRepository(session)
    for entry in new_entries:
        new_pp = await planned_repo.create(
            user_id=user_id,
            loan_id=loan.id,
            due_date=entry.due_date,
            amount=entry.amount,
            principal_part=entry.principal_part,
            interest_part=entry.interest_part,
            status=PaymentStatus.PENDING,
            accuracy=PaymentAccuracy.CALCULATED_ANNUITY,
            can_pay_early=True,
        )
        await audit_service.record(
            session,
            entity_type="planned_payments",
            entity_id=new_pp.id,
            action=AuditAction.CREATE,
            after_state=audit_service.model_to_dict(new_pp),
            changed_by=user_id,
        )


async def _cancel_future_planned(
    session: AsyncSession,
    loan_id: uuid.UUID,
    from_date: date,
    user_id: uuid.UUID,
) -> None:
    """Cancel all future pending planned payments for a loan."""
    stmt = (
        select(PlannedPayment)
        .where(
            PlannedPayment.loan_id == loan_id,
            PlannedPayment.due_date > from_date,
            PlannedPayment.status == PaymentStatus.PENDING,
            PlannedPayment.is_deleted == False,  # noqa: E712
        )
    )
    result = await session.execute(stmt)
    future_payments = list(result.scalars().all())

    planned_repo = PlannedPaymentRepository(session)
    for pp in future_payments:
        before = audit_service.model_to_dict(pp)
        await planned_repo.update(
            pp.id,
            status=PaymentStatus.CANCELLED,
            notes="Заменён после досрочного погашения",
        )
        after = audit_service.model_to_dict(pp)
        await audit_service.record(
            session,
            entity_type="planned_payments",
            entity_id=pp.id,
            action=AuditAction.UPDATE,
            before_state=before,
            after_state=after,
            changed_by=user_id,
        )


# ------------------------------------------------------------------
# Legacy: simple create_actual for backward-compat with stage-4 router
# ------------------------------------------------------------------


async def create_actual(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    loan_id: uuid.UUID,
    planned_payment_id: uuid.UUID | None = None,
    amount: Decimal,
    principal_part: Decimal | None = None,
    interest_part: Decimal | None = None,
    payment_date,
    payment_type,
    notes: str | None = None,
) -> ActualPayment | None:
    """Create an actual payment (simple CRUD, no financial chain).

    Kept for backward compatibility with existing router/tests.
    For full financial processing, use register_payment().
    """
    loan_repo = LoanRepository(session)
    loan = await loan_repo.get(loan_id)
    if loan is None or loan.user_id != user_id:
        return None

    repo = ActualPaymentRepository(session)
    payment = await repo.create(
        loan_id=loan_id,
        planned_payment_id=planned_payment_id,
        amount=amount,
        principal_part=principal_part,
        interest_part=interest_part,
        payment_date=payment_date,
        payment_type=payment_type,
        notes=notes,
    )
    await audit_service.record(
        session,
        entity_type="actual_payments",
        entity_id=payment.id,
        action=AuditAction.CREATE,
        after_state=audit_service.model_to_dict(payment),
        changed_by=user_id,
    )
    return payment
