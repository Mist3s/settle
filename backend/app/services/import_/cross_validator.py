"""Cross-validate parsed import data across sheets.

Checks referential integrity and business invariants that cannot be
expressed within a single Pydantic model (single-sheet scope).  Enum
validation is handled by Pydantic at parse time and is NOT duplicated
here (rule 6 from the spec).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.schemas.import_report import ImportError as ImportErr
from app.services.import_.parser import ParsedData

# Tolerance for the balance equation check (rule 4).
_BALANCE_TOLERANCE = Decimal("0.01")


def cross_validate(parsed: ParsedData) -> list[ImportErr]:
    """Return a list of cross-validation errors for *parsed* data.

    Rules implemented
    -----------------
    1. Every ``loan_code`` in Balances / Schedule / ActualPayments must
       reference an existing code in Loans.
    2. Every ``income_code`` in Schedule must reference an existing code
       in Incomes (when both sheets are populated).
    3. Every Loan must have at least one Balance row.
    4. ``principal_balance + accrued_interest == current_balance`` within
       ±0.01 ₽ (when all three fields are present).
    5. ``Balances.snapshot_date`` must not be in the future.
    """
    errors: list[ImportErr] = []

    loan_codes: set[str] = {loan.code for loan in parsed.loans}
    income_codes: set[str] = {inc.code for inc in parsed.incomes}

    # --- Rule 1: loan_code references ---
    _check_loan_refs(parsed, loan_codes, errors)

    # --- Rule 2: income_code references ---
    _check_income_refs(parsed, income_codes, errors)

    # --- Rule 3: every loan has ≥1 balance ---
    _check_loan_has_balance(parsed, errors)

    # --- Rule 4: balance equation ---
    _check_balance_equation(parsed, errors)

    # --- Rule 5: snapshot_date not in the future ---
    _check_snapshot_not_future(parsed, errors)

    return errors


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_loan_refs(
    parsed: ParsedData,
    loan_codes: set[str],
    errors: list[ImportErr],
) -> None:
    """Rule 1: loan_code in Balances/Schedule/ActualPayments → Loans."""
    for idx, row in enumerate(parsed.balances, start=2):
        if row.loan_code not in loan_codes:
            errors.append(
                ImportErr(
                    sheet="Balances",
                    row=idx,
                    column="loan_code",
                    message=f"Кредит «{row.loan_code}» не найден на листе Loans",
                ),
            )

    for idx, row in enumerate(parsed.schedule, start=2):
        if row.loan_code not in loan_codes:
            errors.append(
                ImportErr(
                    sheet="Schedule",
                    row=idx,
                    column="loan_code",
                    message=f"Кредит «{row.loan_code}» не найден на листе Loans",
                ),
            )

    for idx, row in enumerate(parsed.actual_payments, start=2):
        if row.loan_code not in loan_codes:
            errors.append(
                ImportErr(
                    sheet="ActualPayments",
                    row=idx,
                    column="loan_code",
                    message=f"Кредит «{row.loan_code}» не найден на листе Loans",
                ),
            )


def _check_income_refs(
    parsed: ParsedData,
    income_codes: set[str],
    errors: list[ImportErr],
) -> None:
    """Rule 2: income_code in Schedule → Incomes (both populated)."""
    if not parsed.incomes:
        return
    for idx, row in enumerate(parsed.schedule, start=2):
        if row.income_code and row.income_code not in income_codes:
            errors.append(
                ImportErr(
                    sheet="Schedule",
                    row=idx,
                    column="income_code",
                    message=(
                        f"Доход «{row.income_code}» не найден на листе Incomes"
                    ),
                ),
            )


def _check_loan_has_balance(
    parsed: ParsedData,
    errors: list[ImportErr],
) -> None:
    """Rule 3: every Loan → at least one Balance row."""
    codes_with_balance: set[str] = {b.loan_code for b in parsed.balances}
    for idx, loan in enumerate(parsed.loans, start=2):
        if loan.code not in codes_with_balance:
            errors.append(
                ImportErr(
                    sheet="Loans",
                    row=idx,
                    column="code",
                    message=(
                        f"Кредит «{loan.code}» не имеет ни одной записи "
                        f"на листе Balances"
                    ),
                ),
            )


def _check_balance_equation(
    parsed: ParsedData,
    errors: list[ImportErr],
) -> None:
    """Rule 4: principal + accrued == current (tolerance 0.01)."""
    for idx, row in enumerate(parsed.balances, start=2):
        if (
            row.principal_balance is not None
            and row.accrued_interest is not None
        ):
            expected = row.principal_balance + row.accrued_interest
            diff = abs(expected - row.current_balance)
            if diff > _BALANCE_TOLERANCE:
                errors.append(
                    ImportErr(
                        sheet="Balances",
                        row=idx,
                        column="current_balance",
                        message=(
                            f"principal_balance ({row.principal_balance}) + "
                            f"accrued_interest ({row.accrued_interest}) = "
                            f"{expected}, но current_balance = "
                            f"{row.current_balance} "
                            f"(разница {diff} > {_BALANCE_TOLERANCE})"
                        ),
                    ),
                )


def _check_snapshot_not_future(
    parsed: ParsedData,
    errors: list[ImportErr],
) -> None:
    """Rule 5: snapshot_date must not be in the future."""
    today = date.today()
    for idx, row in enumerate(parsed.balances, start=2):
        if row.snapshot_date > today:
            errors.append(
                ImportErr(
                    sheet="Balances",
                    row=idx,
                    column="snapshot_date",
                    message=(
                        f"Дата баланса {row.snapshot_date} в будущем "
                        f"(сегодня {today})"
                    ),
                ),
            )
