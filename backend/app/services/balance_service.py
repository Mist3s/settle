"""BalanceService — loan balance snapshot management.

Centralises balance operations:
  - creating snapshots (manual, calculated, imported)
  - retrieving the latest snapshot
  - calculating updated balance after a payment
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction, BalanceSource
from app.domain.models.balance import LoanBalance
from app.repositories.balance_repo import BalanceRepository
from app.services import audit_service


async def get_latest(
    session: AsyncSession,
    loan_id: uuid.UUID,
) -> LoanBalance | None:
    """Return the most recent balance snapshot for a loan."""
    repo = BalanceRepository(session)
    return await repo.get_latest(loan_id)


async def create_snapshot(
    session: AsyncSession,
    *,
    loan_id: uuid.UUID,
    snapshot_date: date,
    principal_balance: Decimal,
    accrued_interest: Decimal = Decimal("0.00"),
    source: BalanceSource = BalanceSource.CALCULATED,
    notes: str | None = None,
    changed_by: uuid.UUID | None = None,
) -> LoanBalance:
    """Create a new balance snapshot and record audit entry.

    ``current_balance`` is always computed as ``principal_balance + accrued_interest``
    to enforce the invariant from architecture section 4.1.
    """
    current_balance = principal_balance + accrued_interest

    repo = BalanceRepository(session)
    balance = await repo.create(
        loan_id=loan_id,
        snapshot_date=snapshot_date,
        current_balance=current_balance,
        principal_balance=principal_balance,
        accrued_interest=accrued_interest,
        source=source,
        notes=notes,
    )

    if changed_by is not None:
        await audit_service.record(
            session,
            entity_type="loan_balances",
            entity_id=balance.id,
            action=AuditAction.CREATE,
            after_state=audit_service.model_to_dict(balance),
            changed_by=changed_by,
        )

    return balance


def calculate_new_principal(
    current_principal: Decimal,
    payment_amount: Decimal,
    interest_part: Decimal,
) -> Decimal:
    """Calculate new principal after a payment.

    ``principal_part = payment_amount - interest_part``
    ``new_principal = current_principal - principal_part``

    Pure function, no DB access.
    """
    principal_part = payment_amount - interest_part
    new_principal = current_principal - principal_part
    if new_principal < Decimal("0.00"):
        new_principal = Decimal("0.00")
    return new_principal
