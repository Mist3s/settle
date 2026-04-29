"""Tests for the financial engine: payment type determination, balance calculations.

Also includes the float-scanner test (architecture section 14.3, 10.2).
"""

import subprocess
from decimal import Decimal

from app.domain.enums import ActualPaymentType
from app.services.balance_service import calculate_new_principal
from app.services.payment_service import determine_payment_type

# ---------------------------------------------------------------------------
# determine_payment_type
# ---------------------------------------------------------------------------


class TestDeterminePaymentType:
    """Section 5.2: payment type from amount comparison."""

    def test_regular(self):
        assert (
            determine_payment_type(
                Decimal("10000"), Decimal("10000"), Decimal("500000")
            )
            == ActualPaymentType.REGULAR
        )

    def test_overpayment(self):
        assert (
            determine_payment_type(
                Decimal("15000"), Decimal("10000"), Decimal("500000")
            )
            == ActualPaymentType.OVERPAYMENT
        )

    def test_underpayment(self):
        assert (
            determine_payment_type(
                Decimal("8000"), Decimal("10000"), Decimal("500000")
            )
            == ActualPaymentType.UNDERPAYMENT
        )

    def test_missed(self):
        assert (
            determine_payment_type(
                Decimal("0"), Decimal("10000"), Decimal("500000")
            )
            == ActualPaymentType.MISSED
        )

    def test_early_full_no_planned(self):
        assert (
            determine_payment_type(
                Decimal("500000"), None, Decimal("500000")
            )
            == ActualPaymentType.EARLY_FULL
        )

    def test_early_full_exceeds_balance(self):
        assert (
            determine_payment_type(
                Decimal("600000"), None, Decimal("500000")
            )
            == ActualPaymentType.EARLY_FULL
        )

    def test_early_partial_no_planned(self):
        assert (
            determine_payment_type(
                Decimal("100000"), None, Decimal("500000")
            )
            == ActualPaymentType.EARLY_PARTIAL
        )


# ---------------------------------------------------------------------------
# calculate_new_principal
# ---------------------------------------------------------------------------


class TestCalculateNewPrincipal:
    def test_normal_payment(self):
        result = calculate_new_principal(
            current_principal=Decimal("500000.00"),
            payment_amount=Decimal("10000.00"),
            interest_part=Decimal("4000.00"),
        )
        assert result == Decimal("494000.00")

    def test_full_payment_zeros_out(self):
        result = calculate_new_principal(
            current_principal=Decimal("10000.00"),
            payment_amount=Decimal("10500.00"),
            interest_part=Decimal("500.00"),
        )
        assert result == Decimal("0.00")

    def test_overpayment_floors_to_zero(self):
        result = calculate_new_principal(
            current_principal=Decimal("5000.00"),
            payment_amount=Decimal("10000.00"),
            interest_part=Decimal("200.00"),
        )
        assert result == Decimal("0.00")


# ---------------------------------------------------------------------------
# Float scanner: architecture 10.2, 14.3
# ---------------------------------------------------------------------------


class TestFloatScanner:
    """Ensure no float() usage in financial code paths."""

    def test_no_float_in_services(self):
        """grep for float( in services/, domain/, repositories/.

        Exception: math.log in solve_for_n (documented — result is month count,
        not monetary value).
        """
        result = subprocess.run(
            [
                "grep", "-rnI", r"float(", "--include=*.py",
                "app/services/", "app/domain/", "app/repositories/",
            ],
            capture_output=True,
            text=True,
            cwd="/app",
        )
        lines = result.stdout.strip().splitlines() if result.stdout.strip() else []

        # Filter out the known exception in schedule_service.solve_for_n
        violations = [
            line
            for line in lines
            if "schedule_service.py" not in line or "solve_for_n" not in line
        ]

        # Also filter out the actual float() calls in solve_for_n which are
        # for math.log arguments (month count, not money)
        violations = [
            line
            for line in violations
            if not (
                "schedule_service.py" in line
                and ("math.log" in line or "si_over_p" in line or "monthly_rate" in line)
            )
        ]

        assert violations == [], (
            "float() found in financial code paths:\n"
            + "\n".join(violations)
        )
