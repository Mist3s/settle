"""Integration tests for services/import_/diff.py — build_diff().

Tests run against a real PostgreSQL instance (Docker Compose).
Each test gets its own transactional session that is rolled back.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.enums import (
    LoanType,
    PaymentMethod,
    PaymentStatus,
)
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
from app.services.import_.diff import build_diff
from app.services.import_.parser import ParsedData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_user(session: AsyncSession) -> User:
    user = User(email="diff@settle.local", password_hash=hash_password("pw"))
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


def _loan_row(code: str = "LOAN1") -> LoanImportRow:
    return LoanImportRow(
        code=code,
        creditor="Bank",
        name="Test loan",
        loan_type=LoanType.CREDIT,
        payment_method=PaymentMethod.ANNUITY,
        original_amount=Decimal("100000"),
        interest_rate=Decimal("10"),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_diff_empty_db_all_creates(db_session: AsyncSession) -> None:
    """With an empty DB every imported row should be classified as 'create'."""
    user = await _create_user(db_session)

    parsed = ParsedData(
        loans=[_loan_row("L1"), _loan_row("L2")],
        balances=[
            BalanceImportRow(
                loan_code="L1",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("90000"),
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
                due_date=date(2026, 3, 1),
                amount=Decimal("5000"),
            ),
        ],
        actual_payments=[
            ActualPaymentImportRow(
                loan_code="L1",
                payment_date=date(2026, 3, 1),
                amount=Decimal("5000"),
                payment_type="regular",
            ),
        ],
    )

    report = await build_diff(db_session, user.id, parsed)

    assert report.summary.loans.to_create == 2
    assert report.summary.loans.to_update == 0
    assert report.summary.balances.to_create == 1
    assert report.summary.incomes.to_create == 1
    assert report.summary.schedule.to_create == 1
    assert report.summary.schedule.to_cancel_existing == 0
    assert report.summary.actual_payments.to_create == 1
    assert not report.has_errors


@pytest.mark.asyncio()
async def test_diff_with_existing_records(db_session: AsyncSession) -> None:
    """Existing records matched by business key → to_update."""
    user = await _create_user(db_session)

    # Pre-populate DB
    loan = Loan(
        user_id=user.id,
        code="EXIST",
        creditor="Bank",
        name="Existing",
        loan_type=LoanType.CREDIT,
        payment_method=PaymentMethod.ANNUITY,
    )
    db_session.add(loan)
    await db_session.flush()
    await db_session.refresh(loan)

    balance = LoanBalance(
        loan_id=loan.id,
        snapshot_date=date(2026, 1, 1),
        current_balance=Decimal("80000"),
        principal_balance=Decimal("80000"),
    )
    db_session.add(balance)

    income = Income(
        user_id=user.id,
        code="INC_EXIST",
        expected_date=date(2026, 2, 1),
        amount=Decimal("50000"),
    )
    db_session.add(income)

    actual = ActualPayment(
        loan_id=loan.id,
        payment_date=date(2026, 3, 1),
        amount=Decimal("5000"),
        payment_type="regular",
    )
    db_session.add(actual)
    await db_session.flush()

    # Import data matching the existing records + one new loan
    parsed = ParsedData(
        loans=[_loan_row("EXIST"), _loan_row("NEW1")],
        balances=[
            BalanceImportRow(
                loan_code="EXIST",
                snapshot_date=date(2026, 1, 1),
                current_balance=Decimal("78000"),
            ),
            BalanceImportRow(
                loan_code="NEW1",
                snapshot_date=date(2026, 1, 15),
                current_balance=Decimal("50000"),
            ),
        ],
        incomes=[
            IncomeImportRow(
                code="INC_EXIST",
                expected_date=date(2026, 2, 1),
                amount_rub=Decimal("60000"),
            ),
            IncomeImportRow(
                code="INC_NEW",
                expected_date=date(2026, 4, 1),
                amount_rub=Decimal("30000"),
            ),
        ],
        actual_payments=[
            ActualPaymentImportRow(
                loan_code="EXIST",
                payment_date=date(2026, 3, 1),
                amount=Decimal("5000"),
                payment_type="regular",
            ),
        ],
    )

    report = await build_diff(db_session, user.id, parsed)

    assert report.summary.loans.to_update == 1
    assert report.summary.loans.to_create == 1
    assert report.summary.balances.to_update == 1
    assert report.summary.balances.to_create == 1
    assert report.summary.incomes.to_update == 1
    assert report.summary.incomes.to_create == 1
    assert report.summary.actual_payments.to_update == 1


@pytest.mark.asyncio()
async def test_diff_usd_to_rub_conversion(db_session: AsyncSession) -> None:
    """Income with amount_usd should trigger USD→RUB warning/conversion."""
    user = await _create_user(db_session)

    parsed = ParsedData(
        settings=[
            SettingImportRow(key="usd_rub_rate", value="92.50"),
        ],
        incomes=[
            IncomeImportRow(
                code="USD_INC",
                expected_date=date(2026, 5, 1),
                amount_usd=Decimal("100"),
            ),
        ],
    )

    report = await build_diff(db_session, user.id, parsed)

    assert report.summary.incomes.to_create == 1
    # No warning — only amount_usd provided, rate found
    assert len(report.warnings) == 0


@pytest.mark.asyncio()
async def test_diff_usd_rub_both_amounts_warning(
    db_session: AsyncSession,
) -> None:
    """When both amount_rub and amount_usd are set, a warning is emitted."""
    user = await _create_user(db_session)

    parsed = ParsedData(
        incomes=[
            IncomeImportRow(
                code="BOTH",
                expected_date=date(2026, 5, 1),
                amount_rub=Decimal("9000"),
                amount_usd=Decimal("100"),
            ),
        ],
    )

    report = await build_diff(db_session, user.id, parsed)
    assert len(report.warnings) == 1
    assert "amount_rub" in report.warnings[0].message


@pytest.mark.asyncio()
async def test_diff_usd_rub_no_rate_warning(
    db_session: AsyncSession,
) -> None:
    """When only amount_usd is set but no usd_rub_rate exists, a warning fires."""
    user = await _create_user(db_session)

    parsed = ParsedData(
        incomes=[
            IncomeImportRow(
                code="NO_RATE",
                expected_date=date(2026, 5, 1),
                amount_usd=Decimal("100"),
            ),
        ],
    )

    report = await build_diff(db_session, user.id, parsed)
    assert len(report.warnings) == 1
    assert "usd_rub_rate" in report.warnings[0].message


@pytest.mark.asyncio()
async def test_diff_schedule_to_cancel_existing(
    db_session: AsyncSession,
) -> None:
    """Pending planned payments for loans with new schedule should be counted."""
    user = await _create_user(db_session)

    loan = Loan(
        user_id=user.id,
        code="SCHED_LOAN",
        creditor="Bank",
        name="Sched loan",
        loan_type=LoanType.CREDIT,
        payment_method=PaymentMethod.ANNUITY,
    )
    db_session.add(loan)
    await db_session.flush()
    await db_session.refresh(loan)

    # Create 3 pending planned payments in DB
    for month in (4, 5, 6):
        pp = PlannedPayment(
            user_id=user.id,
            loan_id=loan.id,
            due_date=date(2026, month, 15),
            amount=Decimal("10000"),
            status=PaymentStatus.PENDING,
        )
        db_session.add(pp)

    # One paid — should NOT be counted as to_cancel
    paid_pp = PlannedPayment(
        user_id=user.id,
        loan_id=loan.id,
        due_date=date(2026, 3, 15),
        amount=Decimal("10000"),
        status=PaymentStatus.PAID,
    )
    db_session.add(paid_pp)
    await db_session.flush()

    # Import schedule for this loan (one row matching existing, one new)
    parsed = ParsedData(
        schedule=[
            ScheduleImportRow(
                loan_code="SCHED_LOAN",
                due_date=date(2026, 4, 15),
                amount=Decimal("10000"),
            ),
            ScheduleImportRow(
                loan_code="SCHED_LOAN",
                due_date=date(2026, 7, 15),
                amount=Decimal("10000"),
            ),
        ],
    )

    report = await build_diff(db_session, user.id, parsed)

    assert report.summary.schedule.to_update == 1  # 2026-04-15 matches
    assert report.summary.schedule.to_create == 1  # 2026-07-15 new
    assert report.summary.schedule.to_cancel_existing == 3  # 3 pending


@pytest.mark.asyncio()
async def test_diff_usd_to_rub_via_db_setting(db_session: AsyncSession) -> None:
    """When Settings sheet has no usd_rub_rate, fall back to DB Setting."""
    user = await _create_user(db_session)

    # Store rate in the database, not in the spreadsheet
    setting = Setting(
        user_id=user.id,
        key="usd_rub_rate",
        value="95.00",
    )
    db_session.add(setting)
    await db_session.flush()

    parsed = ParsedData(
        settings=[],  # No usd_rub_rate in the sheet
        incomes=[
            IncomeImportRow(
                code="USD_DB",
                expected_date=date(2026, 6, 1),
                amount_usd=Decimal("200"),
            ),
        ],
    )

    report = await build_diff(db_session, user.id, parsed)

    # Rate found in DB → no warnings
    assert len(report.warnings) == 0
    assert report.summary.incomes.to_create == 1
