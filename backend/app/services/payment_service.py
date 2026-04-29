"""Payment service — business logic for planned and actual payments."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction
from app.domain.models.payment import ActualPayment, PlannedPayment
from app.repositories.loan_repo import LoanRepository
from app.repositories.payment_repo import (
    ActualPaymentRepository,
    PlannedPaymentRepository,
)
from app.services import audit_service

# ------------------------------------------------------------------
# Planned Payments
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
# Actual Payments
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
    """Create an actual payment, verifying loan ownership."""
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
