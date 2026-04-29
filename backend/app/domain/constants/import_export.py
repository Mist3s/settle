"""Shared constants for import / export / template XLSX operations.

Single source of truth for sheet names and column sets (architecture.md §11.2).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Sheet names (order matters for template / export generation)
# ---------------------------------------------------------------------------

SHEET_SETTINGS = "Settings"
SHEET_LOANS = "Loans"
SHEET_BALANCES = "Balances"
SHEET_SCHEDULE = "Schedule"
SHEET_INCOMES = "Incomes"
SHEET_ACTUAL_PAYMENTS = "ActualPayments"

ALL_SHEETS: list[str] = [
    SHEET_SETTINGS,
    SHEET_LOANS,
    SHEET_BALANCES,
    SHEET_SCHEDULE,
    SHEET_INCOMES,
    SHEET_ACTUAL_PAYMENTS,
]

REQUIRED_SHEETS: frozenset[str] = frozenset({
    SHEET_SETTINGS,
    SHEET_LOANS,
    SHEET_BALANCES,
})

# ---------------------------------------------------------------------------
# Column lists per sheet (ordered — order used in export and template)
# ---------------------------------------------------------------------------

SETTINGS_COLUMNS: list[str] = ["key", "value", "description"]

LOANS_COLUMNS: list[str] = [
    "code", "creditor", "name", "loan_type", "payment_method",
    "original_amount", "interest_rate", "opening_date", "closing_date",
    "prepayment_strategy", "priority", "status", "contract_number", "notes",
]

BALANCES_COLUMNS: list[str] = [
    "loan_code", "snapshot_date", "current_balance",
    "principal_balance", "accrued_interest", "source", "notes",
]

SCHEDULE_COLUMNS: list[str] = [
    "loan_code", "due_date", "amount", "principal_part",
    "interest_part", "accuracy", "can_pay_early", "income_code", "notes",
]

INCOMES_COLUMNS: list[str] = [
    "code", "expected_date", "amount_rub", "amount_usd",
    "name", "status", "notes",
]

ACTUAL_PAYMENTS_COLUMNS: list[str] = [
    "loan_code", "payment_date", "amount", "principal_part",
    "interest_part", "payment_type", "planned_due_date", "notes",
]

# Mapping: sheet_name → ordered column list
SHEET_COLUMNS: dict[str, list[str]] = {
    SHEET_SETTINGS: SETTINGS_COLUMNS,
    SHEET_LOANS: LOANS_COLUMNS,
    SHEET_BALANCES: BALANCES_COLUMNS,
    SHEET_SCHEDULE: SCHEDULE_COLUMNS,
    SHEET_INCOMES: INCOMES_COLUMNS,
    SHEET_ACTUAL_PAYMENTS: ACTUAL_PAYMENTS_COLUMNS,
}

# For validation: set-based (order-insensitive)
SHEET_COLUMN_SETS: dict[str, set[str]] = {
    name: set(cols) for name, cols in SHEET_COLUMNS.items()
}

# Marker text in the first cell of example rows (architecture.md §11.6).
EXAMPLE_ROW_MARKER = "[delete this row before import]"
