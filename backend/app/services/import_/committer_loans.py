"""Commit settings, loans, and balances from import data."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import BalanceSource, LoanStatus, PrepaymentStrategy
from app.domain.models.balance import LoanBalance
from app.domain.models.loan import Loan
from app.domain.models.settings import Setting
from app.services.import_.committer_core import (
    CommitResult,
    create_with_audit,
    update_with_audit,
)
from app.services.import_.parser import ParsedData


async def commit_settings(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
    result: CommitResult,
) -> None:
    """Upsert settings by business key ``(user_id, key)``."""
    for row in parsed.settings:
        stmt = select(Setting).where(
            Setting.user_id == user_id,
            Setting.key == row.key,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing is not None:
            updates: dict[str, Any] = {"value": row.value}
            if row.description is not None:
                updates["description"] = row.description
            await update_with_audit(session, existing, updates, "setting", user_id)
            result.settings_updated += 1
        else:
            entity = Setting(
                user_id=user_id,
                key=row.key,
                value=row.value,
                description=row.description,
            )
            await create_with_audit(session, entity, "setting", user_id)
            result.settings_created += 1


async def commit_loans(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
    loan_codes: dict[str, uuid.UUID],
    result: CommitResult,
) -> None:
    """Upsert loans by business key ``(user_id, code)``."""
    for row in parsed.loans:
        data = {
            "code": row.code,
            "creditor": row.creditor,
            "name": row.name,
            "loan_type": row.loan_type,
            "payment_method": row.payment_method,
            "original_amount": row.original_amount,
            "interest_rate": row.interest_rate or Decimal(0),
            "opening_date": row.opening_date,
            "closing_date": row.closing_date,
            "prepayment_strategy": (
                row.prepayment_strategy or PrepaymentStrategy.REDUCE_PAYMENT
            ),
            "priority": row.priority,
            "status": row.status or LoanStatus.ACTIVE,
            "contract_number": row.contract_number,
            "notes": row.notes,
        }

        existing_id = loan_codes.get(row.code)
        if existing_id is not None:
            stmt = select(Loan).where(Loan.id == existing_id)
            loan = (await session.execute(stmt)).scalar_one()
            await update_with_audit(session, loan, data, "loan", user_id)
            result.loans_updated += 1
        else:
            loan = Loan(user_id=user_id, **data)
            await create_with_audit(session, loan, "loan", user_id)
            loan_codes[row.code] = loan.id
            result.loans_created += 1


async def commit_balances(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
    loan_codes: dict[str, uuid.UUID],
    result: CommitResult,
) -> None:
    """Upsert balances by business key ``(loan_id, snapshot_date)``."""
    for row in parsed.balances:
        loan_id = loan_codes[row.loan_code]
        principal = (
            row.principal_balance
            if row.principal_balance is not None
            else row.current_balance
        )
        accrued = (
            row.accrued_interest
            if row.accrued_interest is not None
            else Decimal(0)
        )

        stmt = select(LoanBalance).where(
            LoanBalance.loan_id == loan_id,
            LoanBalance.snapshot_date == row.snapshot_date,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()

        bal_data = {
            "current_balance": row.current_balance,
            "principal_balance": principal,
            "accrued_interest": accrued,
            "source": row.source or BalanceSource.IMPORTED,
            "notes": row.notes,
        }

        if existing is not None:
            await update_with_audit(
                session, existing, bal_data, "loan_balance", user_id,
            )
            result.balances_updated += 1
        else:
            entity = LoanBalance(
                loan_id=loan_id,
                snapshot_date=row.snapshot_date,
                **bal_data,
            )
            await create_with_audit(session, entity, "loan_balance", user_id)
            result.balances_created += 1
