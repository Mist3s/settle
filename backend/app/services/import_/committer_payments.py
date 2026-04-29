"""Commit incomes, schedule, and actual payments from import data.

Also handles side-effects:
- Cancel existing pending planned payments for loans with new schedule.
- Auto-generate schedule for imported loans that lack explicit schedule rows.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    ActualPaymentType,
    IncomeStatus,
    PaymentAccuracy,
    PaymentStatus,
)
from app.domain.models.balance import LoanBalance
from app.domain.models.income import Income
from app.domain.models.loan import Loan
from app.domain.models.payment import ActualPayment, PlannedPayment
from app.domain.schemas.import_report import ImportWarning
from app.services.import_.committer_core import (
    CommitResult,
    create_with_audit,
    update_with_audit,
)
from app.services.import_.diff import _resolve_income_amount
from app.services.import_.parser import ParsedData
from app.services.schedule_service import generate_schedule


async def commit_incomes(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
    usd_rub_rate: Decimal | None,
    income_codes: dict[str, uuid.UUID],
    result: CommitResult,
) -> None:
    """Upsert incomes by business key ``(user_id, code)``."""
    # Warnings were already collected at diff stage; discard here.
    sink: list[ImportWarning] = []

    for idx, row in enumerate(parsed.incomes, start=2):
        amount = _resolve_income_amount(row, usd_rub_rate, sink, idx)

        stmt = select(Income).where(
            Income.user_id == user_id,
            Income.code == row.code,
            Income.is_deleted.is_(False),
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()

        data = {
            "expected_date": row.expected_date,
            "amount": amount,
            "name": row.name,
            "status": row.status or IncomeStatus.EXPECTED,
            "notes": row.notes,
        }

        if existing is not None:
            await update_with_audit(session, existing, data, "income", user_id)
            result.incomes_updated += 1
        else:
            entity = Income(user_id=user_id, code=row.code, **data)
            await create_with_audit(session, entity, "income", user_id)
            income_codes[row.code] = entity.id
            result.incomes_created += 1


async def _cancel_pending_schedule(
    session: AsyncSession,
    user_id: uuid.UUID,
    affected_loan_ids: set[uuid.UUID],
    result: CommitResult,
) -> None:
    """Cancel all existing pending planned payments for affected loans."""
    if not affected_loan_ids:
        return

    stmt = select(PlannedPayment).where(
        PlannedPayment.loan_id.in_(affected_loan_ids),
        PlannedPayment.status == PaymentStatus.PENDING,
        PlannedPayment.is_deleted.is_(False),
    )
    rows = (await session.execute(stmt)).scalars().all()

    for pp in rows:
        await update_with_audit(
            session, pp,
            {"status": PaymentStatus.CANCELLED},
            "planned_payment", user_id,
        )
        result.schedule_cancelled += 1


async def commit_schedule(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
    loan_codes: dict[str, uuid.UUID],
    income_codes: dict[str, uuid.UUID],
    result: CommitResult,
) -> None:
    """Cancel pending planned and upsert schedule by ``(loan_id, due_date)``."""
    # Collect affected loan_ids and cancel pending first.
    affected: set[uuid.UUID] = set()
    for row in parsed.schedule:
        lid = loan_codes.get(row.loan_code)
        if lid is not None:
            affected.add(lid)

    await _cancel_pending_schedule(session, user_id, affected, result)

    # Upsert schedule rows.
    for row in parsed.schedule:
        loan_id = loan_codes[row.loan_code]
        income_id = income_codes.get(row.income_code) if row.income_code else None

        # Exclude PAID payments from upsert lookup to preserve payment history.
        stmt = select(PlannedPayment).where(
            PlannedPayment.loan_id == loan_id,
            PlannedPayment.due_date == row.due_date,
            PlannedPayment.is_deleted.is_(False),
            PlannedPayment.status != PaymentStatus.PAID,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()

        data = {
            "amount": row.amount,
            "principal_part": row.principal_part,
            "interest_part": row.interest_part,
            "accuracy": row.accuracy or PaymentAccuracy.ESTIMATE,
            "can_pay_early": (
                row.can_pay_early if row.can_pay_early is not None else True
            ),
            "income_id": income_id,
            "notes": row.notes,
            "status": PaymentStatus.PENDING,
        }

        if existing is not None:
            await update_with_audit(
                session, existing, data, "planned_payment", user_id,
            )
            result.schedule_updated += 1
        else:
            entity = PlannedPayment(
                user_id=user_id,
                loan_id=loan_id,
                due_date=row.due_date,
                **data,
            )
            await create_with_audit(session, entity, "planned_payment", user_id)
            result.schedule_created += 1


async def commit_actual_payments(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
    loan_codes: dict[str, uuid.UUID],
    result: CommitResult,
) -> None:
    """Upsert actual payments by ``(loan_id, payment_date, amount)``."""
    for row in parsed.actual_payments:
        loan_id = loan_codes[row.loan_code]

        # Resolve planned_payment_id if planned_due_date provided.
        planned_id: uuid.UUID | None = None
        if row.planned_due_date is not None:
            stmt = select(PlannedPayment.id).where(
                PlannedPayment.loan_id == loan_id,
                PlannedPayment.due_date == row.planned_due_date,
                PlannedPayment.is_deleted.is_(False),
            )
            planned_id = (await session.execute(stmt)).scalar_one_or_none()

        payment_type = row.payment_type or ActualPaymentType.REGULAR

        # Business key lookup.
        stmt = select(ActualPayment).where(
            ActualPayment.loan_id == loan_id,
            ActualPayment.payment_date == row.payment_date,
            ActualPayment.amount == row.amount,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()

        upd = {
            "principal_part": row.principal_part,
            "interest_part": row.interest_part,
            "payment_type": payment_type,
            "planned_payment_id": planned_id,
            "notes": row.notes,
        }

        if existing is not None:
            await update_with_audit(
                session, existing, upd, "actual_payment", user_id,
            )
            result.actual_payments_updated += 1
        else:
            entity = ActualPayment(
                loan_id=loan_id,
                payment_date=row.payment_date,
                amount=row.amount,
                **upd,
            )
            await create_with_audit(session, entity, "actual_payment", user_id)
            result.actual_payments_created += 1


async def auto_generate_schedules(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedData,
    loan_codes: dict[str, uuid.UUID],
    result: CommitResult,
) -> None:
    """Generate schedule for imported loans that lack explicit schedule rows."""
    loans_with_schedule = {r.loan_code for r in parsed.schedule}

    for row in parsed.loans:
        if row.code in loans_with_schedule:
            continue
        loan_id = loan_codes[row.code]

        stmt = select(Loan).where(Loan.id == loan_id)
        loan = (await session.execute(stmt)).scalar_one()

        if loan.months_remaining is None or loan.months_remaining <= 0:
            continue
        if loan.original_amount is None or loan.original_amount <= 0:
            continue

        # Use latest balance as principal, fallback to original_amount.
        bal_stmt = (
            select(LoanBalance.current_balance)
            .where(LoanBalance.loan_id == loan_id)
            .order_by(LoanBalance.snapshot_date.desc())
            .limit(1)
        )
        latest_bal = (await session.execute(bal_stmt)).scalar_one_or_none()
        principal = latest_bal if latest_bal is not None else loan.original_amount

        start = loan.opening_date or row.opening_date or date.today()
        entries = generate_schedule(
            principal=principal,
            annual_rate=loan.interest_rate,
            months_remaining=loan.months_remaining,
            start_date=start,
            payment_day=loan.payment_day or 15,
        )

        for entry in entries:
            pp = PlannedPayment(
                user_id=user_id,
                loan_id=loan_id,
                due_date=entry.due_date,
                amount=entry.amount,
                principal_part=entry.principal_part,
                interest_part=entry.interest_part,
                status=PaymentStatus.PENDING,
                accuracy=PaymentAccuracy.CALCULATED_ANNUITY,
            )
            await create_with_audit(session, pp, "planned_payment", user_id)
            result.schedule_created += 1

        result.schedules_auto_generated += 1
