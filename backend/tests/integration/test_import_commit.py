"""Integration tests for services/import_/committer.py — commit_import().

Tests run against a real PostgreSQL instance (Docker Compose).
Each test gets its own transactional session that is rolled back.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.enums import (
    AuditAction,
    BalanceSource,
    IncomeStatus,
    LoanType,
    PaymentAccuracy,
    PaymentMethod,
    PaymentStatus,
)
from app.domain.models.audit import AuditLog
from app.domain.models.balance import LoanBalance
from app.domain.models.income import Income
from app.domain.models.loan import Loan
from app.domain.models.payment import ActualPayment, PlannedPayment
from app.domain.models.settings import Setting
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

    # --- Verify actual DB state (not just counters) ---

    # Setting persisted with correct value.
    setting = (
        await db_session.execute(
            select(Setting).where(
                Setting.user_id == user.id, Setting.key == "usd_rub_rate",
            ),
        )
    ).scalar_one()
    assert setting.value == "92.5"

    # Loan persisted with correct fields.
    loan = (
        await db_session.execute(
            select(Loan).where(Loan.user_id == user.id, Loan.code == "L1"),
        )
    ).scalar_one()
    assert loan.creditor == "Bank"
    assert loan.original_amount == Decimal("100000")
    assert loan.interest_rate == Decimal("12")
    assert loan.opening_date == date(2026, 1, 1)

    # Balance persisted and linked to the loan.
    balance = (
        await db_session.execute(
            select(LoanBalance).where(
                LoanBalance.loan_id == loan.id,
                LoanBalance.snapshot_date == date(2026, 1, 1),
            ),
        )
    ).scalar_one()
    assert balance.current_balance == Decimal("95000")
    assert balance.principal_balance == Decimal("95000")  # default = current
    assert balance.accrued_interest == Decimal("0")
    assert balance.source == BalanceSource.IMPORTED

    # Income persisted.
    income = (
        await db_session.execute(
            select(Income).where(
                Income.user_id == user.id, Income.code == "INC1",
            ),
        )
    ).scalar_one()
    assert income.amount == Decimal("50000")
    assert income.expected_date == date(2026, 2, 1)
    assert income.status == IncomeStatus.EXPECTED

    # PlannedPayment (schedule) persisted.
    pp = (
        await db_session.execute(
            select(PlannedPayment).where(
                PlannedPayment.loan_id == loan.id,
                PlannedPayment.due_date == date(2026, 2, 15),
            ),
        )
    ).scalar_one()
    assert pp.amount == Decimal("5000")
    assert pp.status == PaymentStatus.PENDING

    # ActualPayment persisted.
    ap = (
        await db_session.execute(
            select(ActualPayment).where(
                ActualPayment.loan_id == loan.id,
                ActualPayment.payment_date == date(2026, 2, 15),
            ),
        )
    ).scalar_one()
    assert ap.amount == Decimal("5000")


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
        await db_session.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.changed_by == user.id,
            )
        )
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
async def test_audit_log_update_has_before_and_after(
    db_session: AsyncSession,
) -> None:
    """UPDATE audit records must contain before_state and after_state."""
    user = await _create_user(db_session)

    # First import — create.
    parsed1 = ParsedData(
        loans=[_loan_row("UPD_L")],
        balances=[
            BalanceImportRow(
                loan_code="UPD_L",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("80000"),
            ),
        ],
    )
    await commit_import(db_session, user.id, parsed1)

    # Second import — update balance value.
    parsed2 = ParsedData(
        loans=[_loan_row("UPD_L")],
        balances=[
            BalanceImportRow(
                loan_code="UPD_L",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("70000"),
            ),
        ],
    )
    await commit_import(db_session, user.id, parsed2)

    # Find UPDATE audit records.
    update_audits = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == AuditAction.UPDATE),
        )
    ).scalars().all()

    assert len(update_audits) >= 1

    # Check loan_balance UPDATE specifically.
    bal_update = next(
        (a for a in update_audits if a.entity_type == "loan_balance"), None,
    )
    assert bal_update is not None
    assert bal_update.before_state is not None
    assert bal_update.after_state is not None
    # Before had 80000, after has 70000.
    assert Decimal(str(bal_update.before_state["current_balance"])) == Decimal("80000")
    assert Decimal(str(bal_update.after_state["current_balance"])) == Decimal("70000")


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

    # Verify cancelled payments have CANCELLED status in DB.
    cancelled = (
        await db_session.execute(
            select(PlannedPayment).where(
                PlannedPayment.loan_id == loan.id,
                PlannedPayment.status == PaymentStatus.CANCELLED,
            ),
        )
    ).scalars().all()
    assert len(cancelled) == 3


@pytest.mark.asyncio()
async def test_cancel_pending_schedule_audit(db_session: AsyncSession) -> None:
    """Each cancelled pending payment must produce an audit UPDATE record."""
    user = await _create_user(db_session)

    loan = Loan(
        user_id=user.id,
        code="AUDIT_CANCEL",
        creditor="Bank",
        name="Audit cancel",
        loan_type=LoanType.CREDIT,
        payment_method=PaymentMethod.ANNUITY,
    )
    db_session.add(loan)
    await db_session.flush()
    await db_session.refresh(loan)

    # Create 2 pending payments.
    for month in (3, 4):
        pp = PlannedPayment(
            user_id=user.id,
            loan_id=loan.id,
            due_date=date(2026, month, 15),
            amount=Decimal("5000"),
            status=PaymentStatus.PENDING,
        )
        db_session.add(pp)
    await db_session.flush()

    parsed = ParsedData(
        schedule=[
            ScheduleImportRow(
                loan_code="AUDIT_CANCEL",
                due_date=date(2026, 6, 15),
                amount=Decimal("5000"),
            ),
        ],
    )
    await commit_import(db_session, user.id, parsed)

    # 2 cancellation UPDATEs + 1 new CREATE = 3 planned_payment audits.
    pp_audits = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "planned_payment",
                AuditLog.changed_by == user.id,
            ),
        )
    ).scalars().all()
    assert len(pp_audits) == 3

    cancel_audits = [a for a in pp_audits if a.action == AuditAction.UPDATE]
    assert len(cancel_audits) == 2

    # Each cancel audit should show status change pending → cancelled.
    for audit in cancel_audits:
        assert audit.before_state["status"] == PaymentStatus.PENDING
        assert audit.after_state["status"] == PaymentStatus.CANCELLED


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


@pytest.mark.asyncio()
async def test_auto_generate_schedule_uses_latest_balance(
    db_session: AsyncSession,
) -> None:
    """Auto-generated schedule should use the latest balance, not original_amount."""
    user = await _create_user(db_session)

    parsed = ParsedData(
        loans=[_loan_row("AUTOB")],
        balances=[
            BalanceImportRow(
                loan_code="AUTOB",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("50000"),  # less than original 100000
            ),
        ],
    )
    await commit_import(db_session, user.id, parsed)

    loan = (
        await db_session.execute(
            select(Loan).where(Loan.code == "AUTOB", Loan.user_id == user.id),
        )
    ).scalar_one()
    loan.months_remaining = 3
    loan.payment_day = 15
    await db_session.flush()

    # Second import triggers auto-gen.
    parsed2 = ParsedData(loans=[_loan_row("AUTOB")])
    result = await commit_import(db_session, user.id, parsed2)

    assert result.schedules_auto_generated == 1

    # All generated payments should be based on 50000, not 100000.
    payments = (
        await db_session.execute(
            select(PlannedPayment.amount)
            .where(
                PlannedPayment.loan_id == loan.id,
                PlannedPayment.accuracy == PaymentAccuracy.CALCULATED_ANNUITY,
            )
            .order_by(PlannedPayment.due_date),
        )
    ).scalars().all()

    # Sum should equal ~50000 (within rounding).
    total = sum(payments)
    assert Decimal("49000") < total < Decimal("51500")


@pytest.mark.asyncio()
async def test_commit_transactional_rollback(db_session: AsyncSession) -> None:
    """If actual_payments commit fails, loans and balances must also roll back.

    We patch commit_actual_payments to raise after loans and balances
    have been flushed, then verify nothing was persisted.
    """
    user = await _create_user(db_session)

    parsed = ParsedData(
        loans=[_loan_row("TX_LOAN")],
        balances=[
            BalanceImportRow(
                loan_code="TX_LOAN",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("90000"),
            ),
        ],
        incomes=[
            IncomeImportRow(
                code="TX_INC",
                expected_date=date(2026, 3, 1),
                amount_rub=Decimal("20000"),
            ),
        ],
        actual_payments=[
            ActualPaymentImportRow(
                loan_code="TX_LOAN",
                payment_date=date(2026, 2, 15),
                amount=Decimal("5000"),
                payment_type="regular",
            ),
        ],
    )

    # Use a nested savepoint so we can rollback within the test session.
    nested = await db_session.begin_nested()

    with (
        patch(
            "app.services.import_.committer.commit_actual_payments",
            side_effect=RuntimeError("simulated failure in actual_payments"),
        ),
        pytest.raises(RuntimeError, match="simulated failure"),
    ):
        await commit_import(db_session, user.id, parsed)

    await nested.rollback()

    # After rollback: no loan, no balance, no income should exist.
    loan_count = (
        await db_session.execute(
            select(func.count()).select_from(Loan).where(
                Loan.user_id == user.id, Loan.code == "TX_LOAN",
            ),
        )
    ).scalar_one()
    assert loan_count == 0

    # Filter by user's loans to avoid stale data from previous runs.
    from sqlalchemy.orm import aliased
    lb_alias = aliased(LoanBalance)
    bal_count = (
        await db_session.execute(
            select(func.count()).select_from(lb_alias).join(
                Loan, lb_alias.loan_id == Loan.id,
            ).where(
                Loan.user_id == user.id, Loan.code == "TX_LOAN",
            ),
        )
    ).scalar_one()
    assert bal_count == 0

    income_count = (
        await db_session.execute(
            select(func.count()).select_from(Income).where(
                Income.user_id == user.id, Income.code == "TX_INC",
            ),
        )
    ).scalar_one()
    assert income_count == 0

    # Audit log should also be empty for this user after rollback.
    audit_count = (
        await db_session.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.changed_by == user.id,
            ),
        )
    ).scalar_one()
    assert audit_count == 0
