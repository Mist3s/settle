"""Public entry-point for committing parsed import data.

Orchestrates the per-entity commit modules in strict order:
Settings → Loans → Balances → Incomes → Schedule → ActualPayments → auto-schedule.

Everything runs inside the caller's transaction (no internal commit).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.income import Income
from app.domain.models.loan import Loan
from app.domain.models.settings import Setting
from app.services.import_.committer_core import CommitResult
from app.services.import_.committer_loans import (
    commit_balances,
    commit_loans,
    commit_settings,
)
from app.services.import_.committer_payments import (
    auto_generate_schedules,
    commit_actual_payments,
    commit_incomes,
    commit_schedule,
)
from app.services.import_.parser import ParsedData


async def _build_loan_map(
    session: AsyncSession, user_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """Return ``{code: loan_id}`` for all active loans of the user."""
    stmt = select(Loan.code, Loan.id).where(
        Loan.user_id == user_id, Loan.is_deleted.is_(False),
    )
    return {r[0]: r[1] for r in (await session.execute(stmt)).all()}


async def _build_income_map(
    session: AsyncSession, user_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """Return ``{code: income_id}`` for all active incomes of the user."""
    stmt = select(Income.code, Income.id).where(
        Income.user_id == user_id, Income.is_deleted.is_(False),
    )
    return {r[0]: r[1] for r in (await session.execute(stmt)).all()}


async def _resolve_usd_rub_rate(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
) -> Decimal | None:
    """Resolve ``usd_rub_rate``: first from parsed Settings, then from DB."""
    for s in parsed.settings:
        if s.key == "usd_rub_rate":
            return Decimal(s.value)

    stmt = select(Setting.value).where(
        Setting.user_id == user_id, Setting.key == "usd_rub_rate",
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return Decimal(row) if row is not None else None


async def commit_import(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
) -> CommitResult:
    """Commit *parsed* import data into the database.

    Everything runs in the caller's transaction.  Order:
    Settings → Loans → Balances → Incomes → Schedule → ActualPayments
    → auto-schedule.
    """
    result = CommitResult()

    loan_codes = await _build_loan_map(session, user_id)
    income_codes = await _build_income_map(session, user_id)
    usd_rub_rate = await _resolve_usd_rub_rate(session, user_id, parsed)

    await commit_settings(session, user_id, parsed, result)
    await commit_loans(session, user_id, parsed, loan_codes, result)
    await commit_balances(session, user_id, parsed, loan_codes, result)
    await commit_incomes(
        session, user_id, parsed, usd_rub_rate, income_codes, result,
    )
    await commit_schedule(
        session, user_id, parsed, loan_codes, income_codes, result,
    )
    await commit_actual_payments(session, user_id, parsed, loan_codes, result)
    await auto_generate_schedules(session, user_id, parsed, loan_codes, result)

    return result
