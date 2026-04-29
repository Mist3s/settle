"""Unit tests for services/import_/cross_validator.py.

Covers happy path and each of the 5 cross-validation rules individually.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.domain.schemas.import_dto import (
    ActualPaymentImportRow,
    BalanceImportRow,
    IncomeImportRow,
    LoanImportRow,
    ScheduleImportRow,
)
from app.services.import_.cross_validator import cross_validate
from app.services.import_.parser import ParsedData

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _loan(code: str = "LOAN1") -> LoanImportRow:
    return LoanImportRow(
        code=code,
        creditor="Bank",
        name="Test loan",
        loan_type="credit",
        payment_method="annuity",
    )


def _balance(
    loan_code: str = "LOAN1",
    snapshot_date: date | None = None,
    current_balance: Decimal = Decimal("100000"),
    principal_balance: Decimal | None = None,
    accrued_interest: Decimal | None = None,
) -> BalanceImportRow:
    return BalanceImportRow(
        loan_code=loan_code,
        snapshot_date=snapshot_date or date(2025, 1, 1),
        current_balance=current_balance,
        principal_balance=principal_balance,
        accrued_interest=accrued_interest,
    )


def _schedule(
    loan_code: str = "LOAN1",
    income_code: str | None = None,
) -> ScheduleImportRow:
    return ScheduleImportRow(
        loan_code=loan_code,
        due_date=date(2025, 2, 1),
        amount=Decimal("5000"),
        income_code=income_code,
    )


def _income(code: str = "INC1") -> IncomeImportRow:
    return IncomeImportRow(
        code=code,
        expected_date=date(2025, 1, 25),
        amount_rub=Decimal("50000"),
    )


def _actual(loan_code: str = "LOAN1") -> ActualPaymentImportRow:
    return ActualPaymentImportRow(
        loan_code=loan_code,
        payment_date=date(2025, 2, 1),
        amount=Decimal("5000"),
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:
    def test_no_errors_when_all_valid(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[_balance("LOAN1")],
            schedule=[_schedule("LOAN1", income_code="INC1")],
            incomes=[_income("INC1")],
            actual_payments=[_actual("LOAN1")],
        )
        errors = cross_validate(parsed)
        assert errors == []

    def test_empty_data(self) -> None:
        parsed = ParsedData()
        errors = cross_validate(parsed)
        assert errors == []


# ---------------------------------------------------------------------------
# Rule 1: loan_code references
# ---------------------------------------------------------------------------

class TestRule1LoanCodeRefs:
    def test_unknown_loan_code_in_balances(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[_balance("MISSING")],
        )
        errors = cross_validate(parsed)
        # rule 1 error + rule 3 error (LOAN1 has no balance)
        loan_ref_errors = [e for e in errors if e.sheet == "Balances" and e.column == "loan_code"]
        assert len(loan_ref_errors) == 1
        assert "MISSING" in loan_ref_errors[0].message

    def test_unknown_loan_code_in_schedule(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[_balance("LOAN1")],
            schedule=[_schedule("NOPE")],
        )
        errors = cross_validate(parsed)
        schedule_errors = [e for e in errors if e.sheet == "Schedule" and e.column == "loan_code"]
        assert len(schedule_errors) == 1
        assert "NOPE" in schedule_errors[0].message

    def test_unknown_loan_code_in_actual_payments(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[_balance("LOAN1")],
            actual_payments=[_actual("GHOST")],
        )
        errors = cross_validate(parsed)
        ap_errors = [e for e in errors if e.sheet == "ActualPayments" and e.column == "loan_code"]
        assert len(ap_errors) == 1
        assert "GHOST" in ap_errors[0].message


# ---------------------------------------------------------------------------
# Rule 2: income_code references
# ---------------------------------------------------------------------------

class TestRule2IncomeCodeRefs:
    def test_unknown_income_code_in_schedule(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[_balance("LOAN1")],
            schedule=[_schedule("LOAN1", income_code="BAD_INC")],
            incomes=[_income("INC1")],
        )
        errors = cross_validate(parsed)
        inc_errors = [e for e in errors if e.column == "income_code"]
        assert len(inc_errors) == 1
        assert "BAD_INC" in inc_errors[0].message

    def test_income_code_ignored_when_no_incomes_sheet(self) -> None:
        """When Incomes sheet is empty, income_code refs are not checked."""
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[_balance("LOAN1")],
            schedule=[_schedule("LOAN1", income_code="ANYTHING")],
            incomes=[],
        )
        errors = cross_validate(parsed)
        inc_errors = [e for e in errors if e.column == "income_code"]
        assert len(inc_errors) == 0

    def test_none_income_code_is_ok(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[_balance("LOAN1")],
            schedule=[_schedule("LOAN1", income_code=None)],
            incomes=[_income("INC1")],
        )
        errors = cross_validate(parsed)
        assert errors == []


# ---------------------------------------------------------------------------
# Rule 3: every Loan has ≥1 Balance
# ---------------------------------------------------------------------------

class TestRule3LoanHasBalance:
    def test_loan_without_balance(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1"), _loan("LOAN2")],
            balances=[_balance("LOAN1")],
        )
        errors = cross_validate(parsed)
        missing = [e for e in errors if e.sheet == "Loans" and e.column == "code"]
        assert len(missing) == 1
        assert "LOAN2" in missing[0].message


# ---------------------------------------------------------------------------
# Rule 4: balance equation
# ---------------------------------------------------------------------------

class TestRule4BalanceEquation:
    def test_correct_equation(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[
                _balance(
                    "LOAN1",
                    current_balance=Decimal("100000"),
                    principal_balance=Decimal("95000"),
                    accrued_interest=Decimal("5000"),
                ),
            ],
        )
        errors = cross_validate(parsed)
        assert errors == []

    def test_within_tolerance(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[
                _balance(
                    "LOAN1",
                    current_balance=Decimal("100000.00"),
                    principal_balance=Decimal("95000.005"),
                    accrued_interest=Decimal("4999.999"),
                ),
            ],
        )
        errors = cross_validate(parsed)
        # diff = 0.004 < 0.01 → OK
        assert errors == []

    def test_exceeds_tolerance(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[
                _balance(
                    "LOAN1",
                    current_balance=Decimal("100000"),
                    principal_balance=Decimal("90000"),
                    accrued_interest=Decimal("5000"),
                ),
            ],
        )
        errors = cross_validate(parsed)
        eq_errors = [e for e in errors if e.column == "current_balance"]
        assert len(eq_errors) == 1
        assert "principal_balance" in eq_errors[0].message

    def test_skipped_when_parts_not_set(self) -> None:
        """When principal_balance or accrued_interest is None, skip check."""
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[
                _balance(
                    "LOAN1",
                    current_balance=Decimal("100000"),
                    principal_balance=None,
                    accrued_interest=Decimal("5000"),
                ),
            ],
        )
        errors = cross_validate(parsed)
        assert errors == []


# ---------------------------------------------------------------------------
# Rule 5: snapshot_date not in the future
# ---------------------------------------------------------------------------

class TestRule5SnapshotNotFuture:
    def test_today_is_ok(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[_balance("LOAN1", snapshot_date=date.today())],
        )
        errors = cross_validate(parsed)
        assert errors == []

    def test_past_is_ok(self) -> None:
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[_balance("LOAN1", snapshot_date=date(2024, 6, 15))],
        )
        errors = cross_validate(parsed)
        assert errors == []

    def test_future_date_error(self) -> None:
        future = date.today() + timedelta(days=30)
        parsed = ParsedData(
            loans=[_loan("LOAN1")],
            balances=[_balance("LOAN1", snapshot_date=future)],
        )
        errors = cross_validate(parsed)
        future_errors = [e for e in errors if e.column == "snapshot_date"]
        assert len(future_errors) == 1
        assert "будущем" in future_errors[0].message
