"""Loan service — business logic for loan management."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction, BalanceSource
from app.domain.models.balance import LoanBalance
from app.domain.models.loan import Loan
from app.repositories.balance_repo import BalanceRepository
from app.repositories.loan_repo import LoanRepository
from app.services import audit_service


async def list_loans(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: str | None = None,
    loan_type: str | None = None,
) -> list[Loan]:
    repo = LoanRepository(session)
    filters: dict = {"user_id": user_id}
    if status is not None:
        filters["status"] = status
    if loan_type is not None:
        filters["loan_type"] = loan_type
    return await repo.list(filters=filters)


async def get_loan(
    session: AsyncSession,
    user_id: uuid.UUID,
    loan_id: uuid.UUID,
) -> Loan | None:
    repo = LoanRepository(session)
    loan = await repo.get(loan_id)
    if loan is None or loan.user_id != user_id:
        return None
    return loan


async def create_loan(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    code: str,
    creditor: str,
    name: str,
    loan_type: str,
    payment_method: str,
    original_amount: Decimal | None = None,
    interest_rate: Decimal = Decimal(0),
    opening_date=None,
    closing_date=None,
    prepayment_strategy: str = "reduce_payment",
    priority: int | None = None,
    status: str = "active",
    contract_number: str | None = None,
    notes: str | None = None,
    late_fee_rate: Decimal | None = None,
    months_remaining: int | None = None,
    payment_day: int | None = None,
) -> Loan:
    repo = LoanRepository(session)
    loan = await repo.create(
        user_id=user_id,
        code=code,
        creditor=creditor,
        name=name,
        loan_type=loan_type,
        payment_method=payment_method,
        original_amount=original_amount,
        interest_rate=interest_rate,
        opening_date=opening_date,
        closing_date=closing_date,
        prepayment_strategy=prepayment_strategy,
        priority=priority,
        status=status,
        contract_number=contract_number,
        notes=notes,
        late_fee_rate=late_fee_rate,
        months_remaining=months_remaining,
        payment_day=payment_day,
    )
    await audit_service.record(
        session,
        entity_type="loans",
        entity_id=loan.id,
        action=AuditAction.CREATE,
        after_state=audit_service.model_to_dict(loan),
        changed_by=user_id,
    )
    return loan


async def update_loan(
    session: AsyncSession,
    user_id: uuid.UUID,
    loan_id: uuid.UUID,
    **kwargs,
) -> Loan | None:
    repo = LoanRepository(session)
    loan = await repo.get(loan_id)
    if loan is None or loan.user_id != user_id:
        return None

    before = audit_service.model_to_dict(loan)
    if kwargs:
        await repo.update(loan_id, **kwargs)
    after = audit_service.model_to_dict(loan)

    await audit_service.record(
        session,
        entity_type="loans",
        entity_id=loan.id,
        action=AuditAction.UPDATE,
        before_state=before,
        after_state=after,
        changed_by=user_id,
    )
    return loan


async def delete_loan(
    session: AsyncSession,
    user_id: uuid.UUID,
    loan_id: uuid.UUID,
) -> Loan | None:
    repo = LoanRepository(session)
    loan = await repo.get(loan_id)
    if loan is None or loan.user_id != user_id:
        return None

    before = audit_service.model_to_dict(loan)
    await repo.soft_delete(loan_id)
    after = audit_service.model_to_dict(loan)

    await audit_service.record(
        session,
        entity_type="loans",
        entity_id=loan.id,
        action=AuditAction.DELETE,
        before_state=before,
        after_state=after,
        changed_by=user_id,
    )
    return loan


async def create_balance(
    session: AsyncSession,
    user_id: uuid.UUID,
    loan_id: uuid.UUID,
    *,
    amount: Decimal,
    principal_balance: Decimal | None = None,
    snapshot_date,
    source: BalanceSource = BalanceSource.MANUAL,
    notes: str | None = None,
) -> LoanBalance | None:
    """Create a manual balance correction for a loan."""
    loan_repo = LoanRepository(session)
    loan = await loan_repo.get(loan_id)
    if loan is None or loan.user_id != user_id:
        return None

    principal = principal_balance if principal_balance is not None else amount
    accrued = amount - principal
    if accrued < 0:
        accrued = Decimal(0)

    balance_repo = BalanceRepository(session)
    balance = await balance_repo.create(
        loan_id=loan_id,
        snapshot_date=snapshot_date,
        current_balance=amount,
        principal_balance=principal,
        accrued_interest=accrued,
        source=source,
        notes=notes,
    )

    await audit_service.record(
        session,
        entity_type="loan_balances",
        entity_id=balance.id,
        action=AuditAction.CREATE,
        after_state=audit_service.model_to_dict(balance),
        changed_by=user_id,
    )
    return balance
