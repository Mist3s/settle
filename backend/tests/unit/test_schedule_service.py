"""Unit tests for schedule_service — critical financial engine tests.

Tests cover section 14.3 of architecture.md:
  - Schedule convergence invariant
  - Partial prepayment with reduce_payment strategy
  - Partial prepayment with shorten_term strategy
  - Zero-rate schedule (installments/split)
  - Edge cases (payment_day, last day of month)
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.schedule_service import (
    ScheduleEntry,
    generate_schedule,
    recalculate_after_prepayment,
    solve_for_n,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sum_principal(entries: list[ScheduleEntry]) -> Decimal:
    return sum(e.principal_part for e in entries)


def _sum_interest(entries: list[ScheduleEntry]) -> Decimal:
    return sum(e.interest_part for e in entries)


# ---------------------------------------------------------------------------
# generate_schedule basics
# ---------------------------------------------------------------------------


class TestGenerateSchedule:
    """Core schedule generation tests."""

    def test_convergence_invariant(self):
        """sum(principal_part) == original_amount (±1 kopeck)."""
        principal = Decimal("500000.00")
        schedule = generate_schedule(
            principal=principal,
            annual_rate=Decimal("12.0"),
            months_remaining=60,
            start_date=date(2026, 1, 15),
            payment_day=15,
        )
        assert len(schedule) == 60
        total_principal = _sum_principal(schedule)
        assert abs(total_principal - principal) <= Decimal("0.01")
        assert schedule[-1].balance_after == Decimal("0.00")

    def test_convergence_large_rate(self):
        """Convergence with high interest rate."""
        principal = Decimal("1000000.00")
        schedule = generate_schedule(
            principal=principal,
            annual_rate=Decimal("24.0"),
            months_remaining=120,
            start_date=date(2026, 3, 1),
            payment_day=10,
        )
        assert len(schedule) == 120
        total_principal = _sum_principal(schedule)
        assert abs(total_principal - principal) <= Decimal("0.01")
        assert schedule[-1].balance_after == Decimal("0.00")

    def test_convergence_small_amount(self):
        """Convergence for a small loan."""
        principal = Decimal("10000.00")
        schedule = generate_schedule(
            principal=principal,
            annual_rate=Decimal("9.9"),
            months_remaining=12,
            start_date=date(2026, 5, 1),
            payment_day=5,
        )
        assert len(schedule) == 12
        total_principal = _sum_principal(schedule)
        assert abs(total_principal - principal) <= Decimal("0.01")
        assert schedule[-1].balance_after == Decimal("0.00")

    def test_zero_rate_schedule(self):
        """Zero interest rate: equal payments, no interest."""
        principal = Decimal("30000.00")
        schedule = generate_schedule(
            principal=principal,
            annual_rate=Decimal("0"),
            months_remaining=6,
            start_date=date(2026, 1, 1),
            payment_day=15,
        )
        assert len(schedule) == 6
        for entry in schedule:
            assert entry.interest_part == Decimal("0.00")
        total = _sum_principal(schedule)
        assert total == principal
        assert schedule[-1].balance_after == Decimal("0.00")

    def test_single_payment(self):
        """Schedule with just one payment."""
        principal = Decimal("5000.00")
        schedule = generate_schedule(
            principal=principal,
            annual_rate=Decimal("12.0"),
            months_remaining=1,
            start_date=date(2026, 6, 1),
            payment_day=1,
        )
        assert len(schedule) == 1
        assert schedule[0].balance_after == Decimal("0.00")
        assert schedule[0].principal_part == principal

    def test_empty_on_zero_months(self):
        assert generate_schedule(
            Decimal("1000"), Decimal("12"), 0, date(2026, 1, 1), 15
        ) == []

    def test_empty_on_zero_principal(self):
        assert generate_schedule(
            Decimal("0"), Decimal("12"), 12, date(2026, 1, 1), 15
        ) == []

    def test_annuity_constant(self):
        """All payments except the last should be equal (annuity property)."""
        schedule = generate_schedule(
            principal=Decimal("100000.00"),
            annual_rate=Decimal("10.0"),
            months_remaining=24,
            start_date=date(2026, 1, 1),
            payment_day=20,
        )
        amounts = [e.amount for e in schedule[:-1]]
        assert len(set(amounts)) == 1, "Non-final payments should all be equal"

    def test_principal_part_grows(self):
        """In an annuity schedule, principal_part should generally increase."""
        schedule = generate_schedule(
            principal=Decimal("200000.00"),
            annual_rate=Decimal("15.0"),
            months_remaining=36,
            start_date=date(2026, 1, 1),
            payment_day=10,
        )
        # Check first vs middle vs second-to-last
        assert schedule[0].principal_part < schedule[17].principal_part
        assert schedule[17].principal_part < schedule[-2].principal_part


# ---------------------------------------------------------------------------
# Payment day edge cases
# ---------------------------------------------------------------------------


class TestPaymentDayEdgeCases:
    """Verify correct date handling for payment_day."""

    def test_payment_day_31_february(self):
        """payment_day=31 should clamp to Feb 28/29."""
        schedule = generate_schedule(
            principal=Decimal("6000.00"),
            annual_rate=Decimal("0"),
            months_remaining=3,
            start_date=date(2026, 1, 1),
            payment_day=31,
        )
        # Feb 2026 has 28 days, Mar has 31, Apr has 30
        assert schedule[0].due_date == date(2026, 2, 28)
        assert schedule[1].due_date == date(2026, 3, 31)
        assert schedule[2].due_date == date(2026, 4, 30)

    def test_payment_day_normal(self):
        """Normal payment_day=15 across months."""
        schedule = generate_schedule(
            principal=Decimal("3000.00"),
            annual_rate=Decimal("0"),
            months_remaining=3,
            start_date=date(2026, 6, 1),
            payment_day=15,
        )
        assert schedule[0].due_date == date(2026, 7, 15)
        assert schedule[1].due_date == date(2026, 8, 15)
        assert schedule[2].due_date == date(2026, 9, 15)

    def test_year_boundary(self):
        """Payment across year boundary."""
        schedule = generate_schedule(
            principal=Decimal("2000.00"),
            annual_rate=Decimal("0"),
            months_remaining=2,
            start_date=date(2026, 11, 1),
            payment_day=10,
        )
        assert schedule[0].due_date == date(2026, 12, 10)
        assert schedule[1].due_date == date(2027, 1, 10)


# ---------------------------------------------------------------------------
# Prepayment strategies
# ---------------------------------------------------------------------------


class TestPrepaymentReducePayment:
    """Partial prepayment with reduce_payment strategy.

    Section 14.3: number of remaining payments unchanged, new annuity < old.
    """

    def test_reduce_payment_keeps_months(self):
        original = generate_schedule(
            principal=Decimal("300000.00"),
            annual_rate=Decimal("12.0"),
            months_remaining=36,
            start_date=date(2026, 1, 15),
            payment_day=15,
        )
        old_annuity = original[0].amount

        # After 6 months, pay extra 50k
        new_principal = Decimal("250000.00")
        remaining = 30  # 36 - 6 already paid
        new_schedule = recalculate_after_prepayment(
            new_principal=new_principal,
            annual_rate=Decimal("12.0"),
            months_remaining=remaining,
            prepayment_date=date(2026, 7, 15),
            payment_day=15,
            strategy="reduce_payment",
        )

        assert len(new_schedule) == remaining  # months unchanged
        assert new_schedule[0].amount < old_annuity  # annuity decreased
        # Convergence still holds
        total_principal = _sum_principal(new_schedule)
        assert abs(total_principal - new_principal) <= Decimal("0.01")
        assert new_schedule[-1].balance_after == Decimal("0.00")


class TestPrepaymentShortenTerm:
    """Partial prepayment with shorten_term strategy.

    Section 14.3: annuity unchanged, number of payments decreased.
    """

    def test_shorten_term_keeps_annuity(self):
        original = generate_schedule(
            principal=Decimal("300000.00"),
            annual_rate=Decimal("12.0"),
            months_remaining=36,
            start_date=date(2026, 1, 15),
            payment_day=15,
        )
        old_annuity = original[0].amount

        # Aggressive prepayment: 300k → 150k
        new_principal = Decimal("150000.00")
        remaining = 30
        new_schedule = recalculate_after_prepayment(
            new_principal=new_principal,
            annual_rate=Decimal("12.0"),
            months_remaining=remaining,
            prepayment_date=date(2026, 7, 15),
            payment_day=15,
            strategy="shorten_term",
            current_annuity=old_annuity,
        )

        # Months should be less than remaining 30
        assert len(new_schedule) < remaining
        # The payments should still converge
        total_principal = _sum_principal(new_schedule)
        assert abs(total_principal - new_principal) <= Decimal("0.01")
        assert new_schedule[-1].balance_after == Decimal("0.00")

    def test_shorten_term_requires_annuity(self):
        with pytest.raises(ValueError, match="current_annuity"):
            recalculate_after_prepayment(
                new_principal=Decimal("100000"),
                annual_rate=Decimal("12.0"),
                months_remaining=12,
                prepayment_date=date(2026, 1, 1),
                payment_day=15,
                strategy="shorten_term",
                current_annuity=None,
            )


# ---------------------------------------------------------------------------
# solve_for_n
# ---------------------------------------------------------------------------


class TestSolveForN:
    def test_basic(self):
        n = solve_for_n(
            annuity_payment=Decimal("9963.00"),
            principal=Decimal("250000.00"),
            annual_rate=Decimal("12.0"),
        )
        assert isinstance(n, int)
        assert n > 0
        assert n < 36  # should be less than original 36

    def test_zero_rate(self):
        n = solve_for_n(
            annuity_payment=Decimal("5000.00"),
            principal=Decimal("15000.00"),
            annual_rate=Decimal("0"),
        )
        assert n == 3

    def test_zero_inputs(self):
        assert solve_for_n(Decimal("0"), Decimal("1000"), Decimal("12")) == 0
        assert solve_for_n(Decimal("1000"), Decimal("0"), Decimal("12")) == 0
