"""TemplateService — XLSX template generation (empty + with examples).

Generates a template file matching the import specification from
architecture.md §11.2. Two modes:
  - empty: headers only
  - with_examples: one example row per sheet, highlighted yellow,
    first cell prefixed with '[delete this row before import]'
"""

from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

# ---------------------------------------------------------------------------
# Sheet definitions: (sheet_name, columns, example_row)
# ---------------------------------------------------------------------------

_YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
_BOLD_FONT = Font(bold=True)

SHEET_DEFS: list[tuple[str, list[str], list[str]]] = [
    (
        "Settings",
        ["key", "value", "description"],
        ["[delete this row before import] usd_rub_rate", "92.50", "Курс USD/RUB"],  # noqa: RUF001
    ),
    (
        "Loans",
        [
            "code", "creditor", "name", "loan_type", "payment_method",
            "original_amount", "interest_rate", "opening_date", "closing_date",
            "prepayment_strategy", "priority", "status", "contract_number", "notes",
        ],
        [
            "[delete this row before import] example_loan", "Сбербанк",
            "Потребительский кредит", "credit", "annuity", "500000.00",
            "12.50", "2025-01-15", "2028-01-15", "reduce_payment", "1",
            "active", "1234-5678", "Пример строки",
        ],
    ),
    (
        "Balances",
        [
            "loan_code", "snapshot_date", "current_balance",
            "principal_balance", "accrued_interest", "source", "notes",
        ],
        [
            "[delete this row before import] example_loan", "2026-04-01",
            "450000.00", "445000.00", "5000.00", "imported", "",
        ],
    ),
    (
        "Schedule",
        [
            "loan_code", "due_date", "amount", "principal_part",
            "interest_part", "accuracy", "can_pay_early", "income_code", "notes",
        ],
        [
            "[delete this row before import] example_loan", "2026-05-15",
            "18602.00", "13900.00", "4702.00", "exact_contract", "true",
            "salary_2026_05_10", "",
        ],
    ),
    (
        "Incomes",
        [
            "code", "expected_date", "amount_rub", "amount_usd",
            "name", "status", "notes",
        ],
        [
            "[delete this row before import] salary_2026_05_10", "2026-05-10",
            "150000.00", "", "Зарплата 10 мая", "expected", "",
        ],
    ),
    (
        "ActualPayments",
        [
            "loan_code", "payment_date", "amount", "principal_part",
            "interest_part", "payment_type", "planned_due_date", "notes",
        ],
        [
            "[delete this row before import] example_loan", "2026-04-15",
            "18602.00", "13900.00", "4702.00", "regular", "2026-04-15", "",
        ],
    ),
]


def generate_template(*, with_examples: bool = False) -> bytes:
    """Generate an XLSX template.

    Returns raw bytes suitable for writing to file or HTTP response.
    """
    wb = Workbook()
    # Remove default sheet created by openpyxl
    wb.remove(wb.active)  # type: ignore[arg-type]

    for sheet_name, columns, example_row in SHEET_DEFS:
        ws = wb.create_sheet(title=sheet_name)

        # Header row
        for col_idx, col_name in enumerate(columns, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = _BOLD_FONT

        # Example row (optional)
        if with_examples:
            for col_idx, value in enumerate(example_row, start=1):
                cell = ws.cell(row=2, column=col_idx, value=value)
                cell.fill = _YELLOW_FILL

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
