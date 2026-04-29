"""Integration tests for services/import_/committer.py — commit_import().

Tests run against a real PostgreSQL instance (Docker Compose).
Each test gets its own transactional session that is rolled back.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.enums import (
    LoanType,
    PaymentAccuracy,
    PaymentMethod,
    PaymentStatus,
)
from app.domain.models.audit import AuditLog
from app.domain.models.loan import Loan
from app.domain.models.payment import PlannedPayment
from app.domain.models.user import User
from app.domain.schemas.import_dto import (
    ActualPaymentImportRow,
    BalanceImportRow,
    IncomeImportRow,
    LoanImportRow,
    ScheduleImportRow,
    SettingImportRow,
)
from app.services.import_.committer import commit_import
from app.services.import_.parser import ParsedData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_user(session: AsyncSession) -> User:
    user = User(email="commit@settle.local", password_hash=hash_password("pw"))
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


def _loan_row(
    code: str = "LOAN1", *, months: int | None = None,
) -> LoanImportRow:
    return LoanImportRow(
        code=code,
        creditor="Bank",
        name="Test loan",
        loan_type=LoanType.CREDIT,
        payment_method=PaymentMethod.ANNUITY,
        original_amount=Decimal("100000"),
        interest_rate=Decimal("12"),
        opening_date=date(2026, 1, 1),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_commit_creates_all_entities(db_session: AsyncSession) -> None:
    """Full commit with empty DB — all entities should be created."""
    user = await _create_user(db_session)

    parsed = ParsedData(
        settings=[SettingImportRow(key="usd_rub_rate", value="92.5")],
        loans=[_loan_row("L1")],
        balances=[
            BalanceImportRow(
                loan_code="L1",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("95000"),
            ),
        ],
        incomes=[
            IncomeImportRow(
                code="INC1",
                expected_date=date(2026, 2, 1),
                amount_rub=Decimal("50000"),
            ),
        ],
        schedule=[
            ScheduleImportRow(
                loan_code="L1",
                due_date=date(2026, 2, 15),
                amount=Decimal("5000"),
            ),
        ],
        actual_payments=[
            ActualPaymentImportRow(
                loan_code="L1",
                payment_date=date(2026, 2, 15),
                amount=Decimal("5000"),
                payment_type="regular",
            ),
        ],
    )

    result = await commit_import(db_session, user.id, parsed)

    assert result.settings_created == 1
    assert result.loans_created == 1
    assert result.balances_created == 1
    assert result.incomes_created == 1
    assert result.schedule_created == 1
    assert result.actual_payments_created == 1
    assert result.loans_updated == 0
    assert result.schedule_cancelled == 0


@pytest.mark.asyncio()
async def test_commit_updates_existing(db_session: AsyncSession) -> None:
    """Second import with same business keys should update, not duplicate."""
    user = await _create_user(db_session)

    parsed = ParsedData(
        loans=[_loan_row("L1")],
        balances=[
            BalanceImportRow(
                loan_code="L1",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("95000"),
            ),
        ],
    )
    r1 = await commit_import(db_session, user.id, parsed)
    assert r1.loans_created == 1
    assert r1.balances_created == 1

    # Second import — same business keys, different values.
    parsed2 = ParsedData(
        loans=[_loan_row("L1")],
        balances=[
            BalanceImportRow(
                loan_code="L1",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("90000"),
            ),
        ],
    )
    r2 = await commit_import(db_session, user.id, parsed2)

    assert r2.loans_updated == 1
    assert r2.loans_created == 0
    assert r2.balances_updated == 1
    assert r2.balances_created == 0


@pytest.mark.asyncio()
async def test_commit_audit_log_entries(db_session: AsyncSession) -> None:
    """Every mutation should produce an audit_log entry."""
    user = await _create_user(db_session)

    parsed = ParsedData(
        loans=[_loan_row("AUDIT_L")],
        balances=[
            BalanceImportRow(
                loan_code="AUDIT_L",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("80000"),
            ),
        ],
        incomes=[
            IncomeImportRow(
                code="AUDIT_INC",
                expected_date=date(2026, 3, 1),
                amount_rub=Decimal("30000"),
            ),
        ],
    )

    await commit_import(db_session, user.id, parsed)

    count = (
        await db_session.execute(select(func.count()).select_from(AuditLog))
    ).scalar_one()

    # 1 loan + 1 balance + 1 income = 3 audit records (all CREATEs).
    assert count == 3

    # Verify entity_type values.
    types_result = await db_session.execute(
        select(AuditLog.entity_type).order_by(AuditLog.changed_at),
    )
    entity_types = [r[0] for r in types_result.all()]
    assert "loan" in entity_types
    assert "loan_balance" in entity_types
    assert "income" in entity_types


@pytest.mark.asyncio()
async def test_cancel_pending_schedule(db_session: AsyncSession) -> None:
    """Importing schedule rows should cancel existing pending planned payments."""
    user = await _create_user(db_session)

    # First import: create loan + schedule.
    loan = Loan(
        user_id=user.id,
        code="CANCEL_LOAN",
        creditor="Bank",
        name="Cancel test",
        loan_type=LoanType.CREDIT,
        payment_method=PaymentMethod.ANNUITY,
    )
    db_session.add(loan)
    await db_session.flush()
    await db_session.refresh(loan)

    # Create 3 pending planned payments.
    for month in (3, 4, 5):
        pp = PlannedPayment(
            user_id=user.id,
            loan_id=loan.id,
            due_date=date(2026, month, 15),
            amount=Decimal("10000"),
            status=PaymentStatus.PENDING,
        )
        db_session.add(pp)

    # 1 paid — must NOT be cancelled.
    paid_pp = PlannedPayment(
        user_id=user.id,
        loan_id=loan.id,
        due_date=date(2026, 2, 15),
        amount=Decimal("10000"),
        status=PaymentStatus.PAID,
    )
    db_session.add(paid_pp)
    await db_session.flush()

    # Import new schedule for the same loan.
    parsed = ParsedData(
        schedule=[
            ScheduleImportRow(
                loan_code="CANCEL_LOAN",
                due_date=date(2026, 6, 15),
                amount=Decimal("10000"),
            ),
        ],
    )

    result = await commit_import(db_session, user.id, parsed)

    assert result.schedule_cancelled == 3  # 3 pending cancelled
    assert result.schedule_created == 1    # 1 new created

    # Verify paid payment is untouched.
    stmt = select(PlannedPayment).where(
        PlannedPayment.id == paid_pp.id,
    )
    paid_after = (await db_session.execute(stmt)).scalar_one()
    assert paid_after.status == PaymentStatus.PAID


@pytest.mark.asyncio()
async def test_auto_generate_schedule(db_session: AsyncSession) -> None:
    """Loans without explicit schedule should get auto-generated schedule."""
    user = await _create_user(db_session)

    # Import a loan with months_remaining (needed for auto-gen).
    # We need to set months_remaining on the Loan model directly since
    # LoanImportRow doesn't have months_remaining.
    parsed = ParsedData(
        loans=[_loan_row("AUTO_SCHED")],
        balances=[
            BalanceImportRow(
                loan_code="AUTO_SCHED",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("100000"),
            ),
        ],
        # No schedule rows — should trigger auto-generation.
    )

    result = await commit_import(db_session, user.id, parsed)
    assert result.loans_created == 1

    # Now set months_remaining on the loan (not available in import DTO).
    stmt = select(Loan).where(Loan.code == "AUTO_SCHED", Loan.user_id == user.id)
    loan = (await db_session.execute(stmt)).scalar_one()
    loan.months_remaining = 6
    loan.payment_day = 15
    await db_session.flush()

    # Second import — same loan, no schedule → should auto-generate.
    parsed2 = ParsedData(
        loans=[_loan_row("AUTO_SCHED")],
    )

    result2 = await commit_import(db_session, user.id, parsed2)

    assert result2.schedules_auto_generated == 1
    assert result2.schedule_created == 6  # 6 months

    # Verify planned payments exist.
    pp_count = (
        await db_session.execute(
            select(func.count())
            .select_from(PlannedPayment)
            .where(
                PlannedPayment.loan_id == loan.id,
                PlannedPayment.accuracy == PaymentAccuracy.CALCULATED_ANNUITY,
            ),
        )
    ).scalar_one()
    assert pp_count == 6
