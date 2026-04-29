"""Compare parsed import data against the database to build a dry-run report.

For each entity type the algorithm:
1. Looks up existing records by business key (§11.4).
2. Classifies each imported row as *create* or *update*.
3. For Schedule — counts pending planned payments to cancel.
4. For Income — converts USD→RUB when needed.
5. For ActualPayment — resolves ``planned_payment_id`` via (loan_id, due_date).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import PaymentStatus
from app.domain.models.balance import LoanBalance
from app.domain.models.income import Income
from app.domain.models.loan import Loan
from app.domain.models.payment import ActualPayment, PlannedPayment
from app.domain.models.settings import Setting
from app.domain.schemas.import_dto import IncomeImportRow
from app.domain.schemas.import_report import (
    DryRunReport,
    DryRunSummary,
    EntityDiff,
    ImportWarning,
    ScheduleDiff,
)
from app.services.import_.parser import ParsedData

# TTL for dry-run reports (30 min).
_DRY_RUN_TTL_SECONDS = 30 * 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _loan_map(
    session: AsyncSession, user_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """Return ``{code: loan_id}`` for all active loans of the user."""
    stmt = select(Loan.code, Loan.id).where(
        Loan.user_id == user_id,
        Loan.is_deleted.is_(False),
    )
    rows = (await session.execute(stmt)).all()
    return {r[0]: r[1] for r in rows}


async def _income_map(
    session: AsyncSession, user_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """Return ``{code: income_id}`` for all incomes of the user."""
    stmt = select(Income.code, Income.id).where(
        Income.user_id == user_id,
        Income.is_deleted.is_(False),
    )
    rows = (await session.execute(stmt)).all()
    return {r[0]: r[1] for r in rows}


async def _get_usd_rub_rate(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
) -> Decimal | None:
    """Resolve ``usd_rub_rate``: first from parsed Settings, then from DB."""
    # Check parsed settings first
    for s in parsed.settings:
        if s.key == "usd_rub_rate":
            return Decimal(s.value)

    # Fallback to DB
    stmt = select(Setting.value).where(
        Setting.user_id == user_id,
        Setting.key == "usd_rub_rate",
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return Decimal(row) if row is not None else None


def _resolve_income_amount(
    row: IncomeImportRow,
    usd_rub_rate: Decimal | None,
    warnings: list[ImportWarning],
    row_idx: int,
) -> Decimal:
    """Determine final RUB amount for an income row.

    Priority: amount_rub > amount_usd * rate.
    """
    if row.amount_rub is not None and row.amount_usd is not None:
        warnings.append(
            ImportWarning(
                sheet="Incomes",
                row=row_idx,
                message="Указаны оба amount_rub и amount_usd — используется amount_rub",  # noqa: RUF001
            ),
        )
        return row.amount_rub

    if row.amount_rub is not None:
        return row.amount_rub

    if row.amount_usd is not None:
        if usd_rub_rate is None:
            warnings.append(
                ImportWarning(
                    sheet="Incomes",
                    row=row_idx,
                    message="Не найден usd_rub_rate — используется amount_usd без конвертации",  # noqa: RUF001
                ),
            )
            return row.amount_usd
        return row.amount_usd * usd_rub_rate

    # Both None — fallback to zero
    return Decimal(0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def build_diff(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
) -> DryRunReport:
    """Compare *parsed* data against the database and produce a diff report."""
    warnings: list[ImportWarning] = []
    loan_code_to_id = await _loan_map(session, user_id)
    income_code_to_id = await _income_map(session, user_id)

    # --- Loans ---
    loans_diff = EntityDiff()
    for row in parsed.loans:
        if row.code in loan_code_to_id:
            loans_diff.to_update += 1
        else:
            loans_diff.to_create += 1

    # --- Balances ---
    balances_diff = EntityDiff()
    for row in parsed.balances:
        loan_id = loan_code_to_id.get(row.loan_code)
        if loan_id is not None:
            stmt = select(LoanBalance.id).where(
                LoanBalance.loan_id == loan_id,
                LoanBalance.snapshot_date == row.snapshot_date,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                balances_diff.to_update += 1
            else:
                balances_diff.to_create += 1
        else:
            # Loan will be created by this import → balance is new
            balances_diff.to_create += 1

    # --- Incomes (with USD→RUB) ---
    usd_rub_rate = await _get_usd_rub_rate(session, user_id, parsed)
    incomes_diff = EntityDiff()
    for idx, row in enumerate(parsed.incomes, start=2):
        # Resolve amount (side-effect: populates warnings)
        _resolve_income_amount(row, usd_rub_rate, warnings, idx)
        if row.code in income_code_to_id:
            incomes_diff.to_update += 1
        else:
            incomes_diff.to_create += 1

    # --- Schedule ---
    schedule_diff = ScheduleDiff()
    # Collect loan_ids for which new schedule rows arrive
    schedule_loan_ids: set[uuid.UUID] = set()
    for row in parsed.schedule:
        loan_id = loan_code_to_id.get(row.loan_code)
        if loan_id is not None:
            schedule_loan_ids.add(loan_id)
            stmt = select(PlannedPayment.id).where(
                PlannedPayment.loan_id == loan_id,
                PlannedPayment.due_date == row.due_date,
                PlannedPayment.is_deleted.is_(False),
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                schedule_diff.to_update += 1
            else:
                schedule_diff.to_create += 1
        else:
            schedule_diff.to_create += 1

    # Count pending planned payments to cancel for affected loans
    if schedule_loan_ids:
        stmt = (
            select(PlannedPayment.id)
            .where(
                PlannedPayment.loan_id.in_(schedule_loan_ids),
                PlannedPayment.status == PaymentStatus.PENDING,
                PlannedPayment.is_deleted.is_(False),
            )
        )
        existing_pending = (await session.execute(stmt)).scalars().all()
        schedule_diff.to_cancel_existing = len(existing_pending)

    # --- ActualPayments ---
    actual_diff = EntityDiff()
    for row in parsed.actual_payments:
        loan_id = loan_code_to_id.get(row.loan_code)
        if loan_id is not None:
            # Business key: (loan_id, payment_date, amount)
            stmt = select(ActualPayment.id).where(
                ActualPayment.loan_id == loan_id,
                ActualPayment.payment_date == row.payment_date,
                ActualPayment.amount == row.amount,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                actual_diff.to_update += 1
            else:
                actual_diff.to_create += 1
        else:
            actual_diff.to_create += 1

    now = datetime.now(tz=UTC)
    return DryRunReport(
        import_id=uuid.uuid4(),
        expires_at=now + timedelta(seconds=_DRY_RUN_TTL_SECONDS),
        summary=DryRunSummary(
            loans=loans_diff,
            balances=balances_diff,
            schedule=schedule_diff,
            incomes=incomes_diff,
            actual_payments=actual_diff,
        ),
        warnings=warnings,
    )
