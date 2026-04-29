"""Validate XLSX sheet headers and required sheet presence.

Compares actual column names against the specification (architecture.md §11.2)
and reports missing / unexpected columns.
"""

from app.domain.constants.import_export import (
    REQUIRED_SHEETS,
    SHEET_COLUMN_SETS,
)
from app.domain.schemas.import_report import ImportError

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
    expected = SHEET_COLUMN_SETS.get(sheet_name)
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
