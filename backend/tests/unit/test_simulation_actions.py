"""Unit tests for simulation action handlers.

Tests are pure — no DB, no async. Each handler operates on a
ProjectedState constructed in-memory.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.services.simulation.actions import (
    apply_action,
    apply_add_income,
    apply_change_payment_date,
    apply_close_early_full,
    apply_prepayment_partial,
    apply_reduce_payment,
    apply_skip,
)
from app.services.simulation.projected_state import (
    ProjectedLoan,
    ProjectedPayment,
    ProjectedState,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LOAN_ID = uuid.uuid4()
PP_ID_1 = uuid.uuid4()
PP_ID_2 = uuid.uuid4()
PP_ID_3 = uuid.uuid4()


def _make_state(
    *,
    principal: Decimal = Decimal("100000.00"),
    accrued: Decimal = Decimal("500.00"),
    rate: Decimal = Decimal("12.0"),
    months: int = 12,
    payment_day: int = 15,
) -> ProjectedState:
    """Build a test ProjectedState with one loan and three pending payments."""
    state = ProjectedState()
    state.loans[LOAN_ID] = ProjectedLoan(
        id=LOAN_ID,
        name="Test Loan",
        creditor="Test Bank",
        principal_balance=principal,
        accrued_interest=accrued,
        interest_rate=rate,
        months_remaining=months,
        payment_day=payment_day,
        prepayment_strategy="reduce_payment",
        status="active",
    )
    state.payments = [
        ProjectedPayment(
            id=PP_ID_1,
            loan_id=LOAN_ID,
            loan_name="Test Loan",
            due_date=date(2026, 6, 15),
            amount=Decimal("10000.00"),
            principal_part=Decimal("9000.00"),
            interest_part=Decimal("1000.00"),
            status="pending",
        ),
        ProjectedPayment(
            id=PP_ID_2,
            loan_id=LOAN_ID,
            loan_name="Test Loan",
            due_date=date(2026, 7, 15),
            amount=Decimal("10000.00"),
            principal_part=Decimal("9100.00"),
            interest_part=Decimal("900.00"),
            status="pending",
        ),
        ProjectedPayment(
            id=PP_ID_3,
            loan_id=LOAN_ID,
            loan_name="Test Loan",
            due_date=date(2026, 8, 15),
            amount=Decimal("10000.00"),
            principal_part=Decimal("9200.00"),
            interest_part=Decimal("800.00"),
            status="pending",
        ),
    ]
    return state


# ---------------------------------------------------------------------------
# close_early_full
# ---------------------------------------------------------------------------


class TestCloseEarlyFull:
    def test_cancels_future_and_pays_off(self):
        state = _make_state()
        apply_close_early_full(
            state, loan_id=LOAN_ID, effective_date=date(2026, 6, 1)
        )

        loan = state.loans[LOAN_ID]
        assert loan.principal_balance == Decimal("0.00")
        assert loan.accrued_interest == Decimal("0.00")
        assert loan.status == "paid_off"

        # All original payments cancelled
        for p in state.payments:
            if p.kind == "real":
                assert p.status == "cancelled"

        # One synthetic payoff payment added
        synthetic = [p for p in state.payments if p.kind == "synthetic"]
        assert len(synthetic) == 1
        assert synthetic[0].amount == Decimal("100500.00")  # principal + accrued

    def test_nonexistent_loan_is_noop(self):
        state = _make_state()
        fake_id = uuid.uuid4()
        apply_close_early_full(
            state, loan_id=fake_id, effective_date=date(2026, 6, 1)
        )
        # Nothing changed
        assert state.loans[LOAN_ID].status == "active"

    def test_zero_balance_loan_is_noop(self):
        state = _make_state(principal=Decimal("0.00"), accrued=Decimal("0.00"))
        apply_close_early_full(
            state, loan_id=LOAN_ID, effective_date=date(2026, 6, 1)
        )
        assert state.loans[LOAN_ID].status == "active"  # unchanged


# ---------------------------------------------------------------------------
# prepayment_partial
# ---------------------------------------------------------------------------


class TestPrepaymentPartial:
    def test_reduces_balance_and_regenerates(self):
        state = _make_state(principal=Decimal("100000.00"), rate=Decimal("12.0"))
        apply_prepayment_partial(
            state,
            loan_id=LOAN_ID,
            effective_date=date(2026, 6, 1),
            amount=Decimal("20000.00"),
        )

        loan = state.loans[LOAN_ID]
        assert loan.principal_balance == Decimal("80000.00")
        assert loan.status == "active"

        # Original future payments cancelled
        cancelled = [p for p in state.payments if p.kind == "real" and p.status == "cancelled"]
        assert len(cancelled) == 3

        # Synthetic payments generated
        synthetic = [p for p in state.payments if p.kind == "synthetic"]
        assert len(synthetic) >= 1  # prepayment + new schedule

    def test_overpay_closes_loan(self):
        state = _make_state(principal=Decimal("5000.00"), accrued=Decimal("0.00"))
        apply_prepayment_partial(
            state,
            loan_id=LOAN_ID,
            effective_date=date(2026, 6, 1),
            amount=Decimal("10000.00"),
        )
        loan = state.loans[LOAN_ID]
        assert loan.principal_balance == Decimal("0.00")
        assert loan.status == "paid_off"


# ---------------------------------------------------------------------------
# reduce_payment
# ---------------------------------------------------------------------------


class TestReducePayment:
    def test_changes_amount(self):
        state = _make_state()
        apply_reduce_payment(
            state, planned_payment_id=PP_ID_1, new_amount=Decimal("5000.00")
        )
        target = [p for p in state.payments if p.id == PP_ID_1][0]
        assert target.amount == Decimal("5000.00")

    def test_nonexistent_payment_is_noop(self):
        state = _make_state()
        apply_reduce_payment(
            state, planned_payment_id=uuid.uuid4(), new_amount=Decimal("5000.00")
        )
        # All unchanged
        assert state.payments[0].amount == Decimal("10000.00")


# ---------------------------------------------------------------------------
# skip
# ---------------------------------------------------------------------------


class TestSkip:
    def test_marks_as_skipped(self):
        state = _make_state()
        apply_skip(state, planned_payment_id=PP_ID_2)
        target = [p for p in state.payments if p.id == PP_ID_2][0]
        assert target.status == "skipped"

    def test_nonexistent_payment_is_noop(self):
        state = _make_state()
        apply_skip(state, planned_payment_id=uuid.uuid4())
        # All still pending
        assert all(p.status == "pending" for p in state.payments)


# ---------------------------------------------------------------------------
# add_income
# ---------------------------------------------------------------------------


class TestAddIncome:
    def test_adds_synthetic_income(self):
        state = _make_state()
        apply_add_income(
            state,
            effective_date=date(2026, 6, 5),
            amount=Decimal("50000.00"),
            name="Премия",
        )
        assert len(state.incomes) == 1
        inc = state.incomes[0]
        assert inc.amount == Decimal("50000.00")
        assert inc.name == "Премия"
        assert inc.kind == "synthetic"


# ---------------------------------------------------------------------------
# change_payment_date
# ---------------------------------------------------------------------------


class TestChangePaymentDate:
    def test_moves_date(self):
        state = _make_state()
        new_dt = date(2026, 6, 20)
        apply_change_payment_date(
            state, planned_payment_id=PP_ID_1, new_date=new_dt
        )
        target = [p for p in state.payments if p.id == PP_ID_1][0]
        assert target.due_date == new_dt


# ---------------------------------------------------------------------------
# apply_action dispatcher
# ---------------------------------------------------------------------------


class TestApplyActionDispatcher:
    def test_dispatches_close_early_full(self):
        state = _make_state()
        apply_action(
            state,
            action_type="close_early_full",
            loan_id=LOAN_ID,
            planned_payment_id=None,
            effective_date=date(2026, 6, 1),
            params=None,
        )
        assert state.loans[LOAN_ID].status == "paid_off"

    def test_dispatches_skip(self):
        state = _make_state()
        apply_action(
            state,
            action_type="skip",
            loan_id=None,
            planned_payment_id=PP_ID_1,
            effective_date=date(2026, 6, 15),
            params=None,
        )
        assert state.payments[0].status == "skipped"

    def test_dispatches_add_income(self):
        state = _make_state()
        apply_action(
            state,
            action_type="add_income",
            loan_id=None,
            planned_payment_id=None,
            effective_date=date(2026, 7, 1),
            params={"amount": "25000", "name": "Бонус"},
        )
        assert len(state.incomes) == 1

    def test_missing_loan_id_is_noop(self):
        state = _make_state()
        apply_action(
            state,
            action_type="close_early_full",
            loan_id=None,
            planned_payment_id=None,
            effective_date=date(2026, 6, 1),
            params=None,
        )
        assert state.loans[LOAN_ID].status == "active"


# ---------------------------------------------------------------------------
# ProjectedState.copy isolation
# ---------------------------------------------------------------------------


class TestProjectedStateCopy:
    def test_copy_is_independent(self):
        state = _make_state()
        copied = state.copy()

        apply_close_early_full(
            copied, loan_id=LOAN_ID, effective_date=date(2026, 6, 1)
        )

        # Original unchanged
        assert state.loans[LOAN_ID].status == "active"
        assert state.loans[LOAN_ID].principal_balance == Decimal("100000.00")

        # Copy changed
        assert copied.loans[LOAN_ID].status == "paid_off"
        assert copied.loans[LOAN_ID].principal_balance == Decimal("0.00")
