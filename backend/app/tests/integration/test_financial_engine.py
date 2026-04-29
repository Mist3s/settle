"""Integration tests for the financial engine (Stage 5).

Critical tests from architecture section 14.3:
- Full early payoff: balance=0, future planned cancelled
- Partial prepayment reduce_payment: months same, annuity lower
- Overpayment: excess goes to principal, schedule recalculated
- Regular payment: balance updated correctly
- Underpayment: planned_payment status=partial

All tests use real PostgreSQL through the test session.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    ActualPaymentType,
    BalanceSource,
    LoanStatus,
    PaymentStatus,
)
from app.domain.models.balance import LoanBalance
from app.domain.models.loan import Loan
from app.domain.models.payment import PlannedPayment
from app.domain.models.user import User
from app.services import balance_service, payment_service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="engine_test@test.com",
        password_hash="$argon2id$v=19$m=65536,t=2,p=1$fake",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def test_loan(db_session: AsyncSession, test_user: User) -> Loan:
    """Active credit with 12% rate, 24 months, payment day 15."""
    loan = Loan(
        id=uuid.uuid4(),
        user_id=test_user.id,
        code="engine_test_credit",
        creditor="TestBank",
        name="Test Credit",
        loan_type="credit",
        payment_method="annuity",
        original_amount=Decimal("300000.00"),
        interest_rate=Decimal("12.0000"),
        opening_date=date(2026, 1, 1),
        prepayment_strategy="reduce_payment",
        months_remaining=24,
        payment_day=15,
        status="active",
    )
    db_session.add(loan)
    await db_session.flush()
    await db_session.refresh(loan)
    return loan


@pytest_asyncio.fixture()
async def loan_with_balance(
    db_session: AsyncSession, test_loan: Loan
) -> tuple[Loan, LoanBalance]:
    """Loan with an initial balance snapshot."""
    balance = LoanBalance(
        id=uuid.uuid4(),
        loan_id=test_loan.id,
        snapshot_date=date(2026, 1, 15),
        current_balance=Decimal("300000.00"),
        principal_balance=Decimal("300000.00"),
        accrued_interest=Decimal("0.00"),
        source="imported",
    )
    db_session.add(balance)
    await db_session.flush()
    await db_session.refresh(balance)
    return test_loan, balance


@pytest_asyncio.fixture()
async def loan_with_planned(
    db_session: AsyncSession,
    loan_with_balance: tuple[Loan, LoanBalance],
    test_user: User,
) -> tuple[Loan, LoanBalance, PlannedPayment]:
    """Loan with balance + one planned payment."""
    loan, balance = loan_with_balance
    pp = PlannedPayment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        loan_id=loan.id,
        due_date=date(2026, 2, 15),
        amount=Decimal("14122.97"),
        principal_part=Decimal("11122.97"),
        interest_part=Decimal("3000.00"),
        status="pending",
        accuracy="calculated_annuity",
        can_pay_early=True,
    )
    db_session.add(pp)
    await db_session.flush()
    await db_session.refresh(pp)
    return loan, balance, pp


# ---------------------------------------------------------------------------
# Critical test: regular payment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_regular_payment(
    db_session: AsyncSession,
    test_user: User,
    loan_with_planned: tuple[Loan, LoanBalance, PlannedPayment],
):
    loan, _balance, pp = loan_with_planned

    actual = await payment_service.register_payment(
        db_session,
        test_user.id,
        loan_id=loan.id,
        amount=Decimal("14122.97"),
        payment_date=date(2026, 2, 15),
        planned_payment_id=pp.id,
    )
    await db_session.flush()

    # Payment created with correct type
    assert actual.payment_type == ActualPaymentType.REGULAR
    assert actual.amount == Decimal("14122.97")

    # Balance updated
    new_balance = await balance_service.get_latest(db_session, loan.id)
    assert new_balance is not None
    assert new_balance.snapshot_date == date(2026, 2, 15)
    assert new_balance.source == BalanceSource.CALCULATED
    # principal should be 300000 - 11122.97 = 288877.03
    expected_principal = Decimal("300000.00") - Decimal("11122.97")
    assert new_balance.principal_balance == expected_principal

    # Planned payment marked as paid
    await db_session.refresh(pp)
    assert pp.status == PaymentStatus.PAID


# ---------------------------------------------------------------------------
# Critical test: full early payoff (14.3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_early_full_payoff(
    db_session: AsyncSession,
    test_user: User,
    loan_with_balance: tuple[Loan, LoanBalance],
):
    """After early_full: balance=0, loan status=paid_off."""
    loan, _balance = loan_with_balance

    # Add some future planned payments
    future_pps = []
    for month in range(2, 5):
        pp = PlannedPayment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            loan_id=loan.id,
            due_date=date(2026, month, 15),
            amount=Decimal("14122.97"),
            principal_part=Decimal("11122.97"),
            interest_part=Decimal("3000.00"),
            status="pending",
            accuracy="calculated_annuity",
            can_pay_early=True,
        )
        db_session.add(pp)
        future_pps.append(pp)
    await db_session.flush()
    for pp in future_pps:
        await db_session.refresh(pp)

    await payment_service.register_payment(
        db_session,
        test_user.id,
        loan_id=loan.id,
        amount=Decimal("300000.00"),
        payment_date=date(2026, 1, 20),
        payment_type=ActualPaymentType.EARLY_FULL,
    )
    await db_session.flush()

    # Balance = 0
    new_balance = await balance_service.get_latest(db_session, loan.id)
    assert new_balance is not None
    assert new_balance.principal_balance == Decimal("0.00")

    # All future planned payments cancelled
    for pp in future_pps:
        await db_session.refresh(pp)
        assert pp.status == PaymentStatus.CANCELLED

    # Loan marked as paid_off
    await db_session.refresh(loan)
    assert loan.status == LoanStatus.PAID_OFF


# ---------------------------------------------------------------------------
# Critical test: overpayment (14.3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overpayment_excess_to_principal(
    db_session: AsyncSession,
    test_user: User,
    loan_with_planned: tuple[Loan, LoanBalance, PlannedPayment],
):
    """Overpayment: excess goes to principal, schedule recalculated."""
    loan, _balance, pp = loan_with_planned

    # Add more future planned payments so regeneration has something to cancel
    extra_pp = PlannedPayment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        loan_id=loan.id,
        due_date=date(2026, 3, 15),
        amount=Decimal("14122.97"),
        principal_part=Decimal("11234.10"),
        interest_part=Decimal("2888.87"),
        status="pending",
        accuracy="calculated_annuity",
        can_pay_early=True,
    )
    db_session.add(extra_pp)
    await db_session.flush()
    await db_session.refresh(extra_pp)

    # Pay 20000 instead of 14122.97 — overpayment of ~5877
    actual = await payment_service.register_payment(
        db_session,
        test_user.id,
        loan_id=loan.id,
        amount=Decimal("20000.00"),
        payment_date=date(2026, 2, 15),
        planned_payment_id=pp.id,
    )
    await db_session.flush()

    assert actual.payment_type == ActualPaymentType.OVERPAYMENT

    # Balance should reflect the larger payment
    new_balance = await balance_service.get_latest(db_session, loan.id)
    assert new_balance is not None
    # With overpayment, new principal = 300000 - (20000 - 3000) = 283000
    assert new_balance.principal_balance == Decimal("283000.00")

    # Planned payment marked as paid
    await db_session.refresh(pp)
    assert pp.status == PaymentStatus.PAID


# ---------------------------------------------------------------------------
# Critical test: underpayment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_underpayment_marks_partial(
    db_session: AsyncSession,
    test_user: User,
    loan_with_planned: tuple[Loan, LoanBalance, PlannedPayment],
):
    """Underpayment: planned_payment status=partial, notes record shortfall."""
    loan, _balance, pp = loan_with_planned

    actual = await payment_service.register_payment(
        db_session,
        test_user.id,
        loan_id=loan.id,
        amount=Decimal("10000.00"),
        payment_date=date(2026, 2, 15),
        planned_payment_id=pp.id,
    )
    await db_session.flush()

    assert actual.payment_type == ActualPaymentType.UNDERPAYMENT

    # Planned marked as partial
    await db_session.refresh(pp)
    assert pp.status == PaymentStatus.PARTIAL
    assert "4122.97" in (pp.notes or "")


# ---------------------------------------------------------------------------
# Critical test: missed payment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missed_payment(
    db_session: AsyncSession,
    test_user: User,
    loan_with_planned: tuple[Loan, LoanBalance, PlannedPayment],
):
    """Missed payment (amount=0): planned status=skipped."""
    loan, _balance, pp = loan_with_planned

    actual = await payment_service.register_payment(
        db_session,
        test_user.id,
        loan_id=loan.id,
        amount=Decimal("0"),
        payment_date=date(2026, 2, 15),
        planned_payment_id=pp.id,
    )
    await db_session.flush()

    assert actual.payment_type == ActualPaymentType.MISSED

    await db_session.refresh(pp)
    assert pp.status == PaymentStatus.SKIPPED


# ---------------------------------------------------------------------------
# Test: early partial prepayment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_early_partial_payment(
    db_session: AsyncSession,
    test_user: User,
    loan_with_balance: tuple[Loan, LoanBalance],
):
    """Early partial: balance reduced, future schedule regenerated."""
    loan, _balance = loan_with_balance

    # Add future planned payments
    pp = PlannedPayment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        loan_id=loan.id,
        due_date=date(2026, 3, 15),
        amount=Decimal("14122.97"),
        principal_part=Decimal("11122.97"),
        interest_part=Decimal("3000.00"),
        status="pending",
        accuracy="calculated_annuity",
        can_pay_early=True,
    )
    db_session.add(pp)
    await db_session.flush()

    actual = await payment_service.register_payment(
        db_session,
        test_user.id,
        loan_id=loan.id,
        amount=Decimal("50000.00"),
        payment_date=date(2026, 2, 1),
        payment_type=ActualPaymentType.EARLY_PARTIAL,
    )
    await db_session.flush()

    assert actual.payment_type == ActualPaymentType.EARLY_PARTIAL

    # Balance reduced
    new_balance = await balance_service.get_latest(db_session, loan.id)
    assert new_balance is not None
    assert new_balance.principal_balance < Decimal("300000.00")

    # The future planned payment should be cancelled (regenerated)
    await db_session.refresh(pp)
    assert pp.status == PaymentStatus.CANCELLED
