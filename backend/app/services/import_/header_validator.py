"""Validate XLSX sheet headers and required sheet presence.

Compares actual column names against the specification (architecture.md §11.2)
and reports missing / unexpected columns.
"""

from app.domain.schemas.import_report import ImportError

# ---------------------------------------------------------------------------
# Reference column sets per sheet (architecture.md §11.2)
# ---------------------------------------------------------------------------

SHEET_COLUMNS: dict[str, set[str]] = {
    "Settings": {"key", "value", "description"},
    "Loans": {
        "code", "creditor", "name", "loan_type", "payment_method",
        "original_amount", "interest_rate", "opening_date", "closing_date",
        "prepayment_strategy", "priority", "status", "contract_number", "notes",
    },
    "Balances": {
        "loan_code", "snapshot_date", "current_balance",
        "principal_balance", "accrued_interest", "source", "notes",
    },
    "Schedule": {
        "loan_code", "due_date", "amount", "principal_part", "interest_part",
        "accuracy", "can_pay_early", "income_code", "notes",
    },
    "Incomes": {
        "code", "expected_date", "amount_rub", "amount_usd",
        "name", "status", "notes",
    },
    "ActualPayments": {
        "loan_code", "payment_date", "amount", "principal_part",
        "interest_part", "payment_type", "planned_due_date", "notes",
    },
}

REQUIRED_SHEETS: set[str] = {"Settings", "Loans", "Balances"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_headers(
    sheet_name: str,
    actual_cols: list[str],
) -> list[ImportError]:
    """Check *actual_cols* against the reference set for *sheet_name*.

    Returns a list of ``ImportError`` for:
    - unknown sheet name (not in spec)
    - missing columns
    - extra (unexpected) columns
    """
    expected = SHEET_COLUMNS.get(sheet_name)
    if expected is None:
        return [
            ImportError(
                sheet=sheet_name,
                message=f"Неизвестный лист: {sheet_name}",
            ),
        ]

    actual = set(actual_cols)
    errors: list[ImportError] = []

    missing = expected - actual
    if missing:
        errors.append(
            ImportError(
                sheet=sheet_name,
                message=(
                    f"Отсутствуют колонки: {', '.join(sorted(missing))}"
                ),
            ),
        )

    extra = actual - expected
    if extra:
        errors.append(
            ImportError(
                sheet=sheet_name,
                message=(
                    f"Лишние колонки: {', '.join(sorted(extra))}"
                ),
            ),
        )

    return errors


def validate_required_sheets(sheet_names: list[str]) -> list[ImportError]:
    """Ensure all required sheets are present in *sheet_names*.

    Missing *optional* sheets are silently ignored.
    """
    present = set(sheet_names)
    missing = REQUIRED_SHEETS - present
    return [
        ImportError(
            sheet=name,
            message=f"Обязательный лист отсутствует: {name}",
        )
        for name in sorted(missing)
    ]
