"""Unit tests for services/import_/header_validator.py."""

from app.domain.schemas.import_report import ImportError
from app.services.import_.header_validator import (
    REQUIRED_SHEETS,
    SHEET_COLUMNS,
    validate_headers,
    validate_required_sheets,
)


# ---------------------------------------------------------------------------
# validate_headers
# ---------------------------------------------------------------------------

class TestValidateHeaders:
    """Tests for validate_headers()."""

    def test_correct_headers_no_errors(self) -> None:
        for sheet, cols in SHEET_COLUMNS.items():
            errors = validate_headers(sheet, list(cols))
            assert errors == [], f"Unexpected errors for {sheet}: {errors}"

    def test_missing_columns(self) -> None:
        errors = validate_headers("Settings", ["key"])
        assert len(errors) == 1
        assert "Отсутствуют колонки" in errors[0].message
        assert "value" in errors[0].message
        assert errors[0].sheet == "Settings"

    def test_extra_columns(self) -> None:
        cols = list(SHEET_COLUMNS["Settings"]) + ["foo", "bar"]
        errors = validate_headers("Settings", cols)
        assert len(errors) == 1
        assert "Лишние колонки" in errors[0].message
        assert "bar" in errors[0].message
        assert "foo" in errors[0].message

    def test_missing_and_extra_columns(self) -> None:
        # Remove 'value', add 'extra_col'
        cols = ["key", "description", "extra_col"]
        errors = validate_headers("Settings", cols)
        assert len(errors) == 2
        messages = {e.message for e in errors}
        assert any("Отсутствуют" in m for m in messages)
        assert any("Лишние" in m for m in messages)

    def test_unknown_sheet(self) -> None:
        errors = validate_headers("NonExistent", ["a", "b"])
        assert len(errors) == 1
        assert "Неизвестный лист" in errors[0].message
        assert errors[0].sheet == "NonExistent"

    def test_all_sheets_present_in_spec(self) -> None:
        expected_sheets = {
            "Settings", "Loans", "Balances",
            "Schedule", "Incomes", "ActualPayments",
        }
        assert set(SHEET_COLUMNS.keys()) == expected_sheets

    def test_returns_import_error_type(self) -> None:
        errors = validate_headers("Settings", ["key"])
        assert all(isinstance(e, ImportError) for e in errors)


# ---------------------------------------------------------------------------
# validate_required_sheets
# ---------------------------------------------------------------------------

class TestValidateRequiredSheets:
    """Tests for validate_required_sheets()."""

    def test_all_required_present(self) -> None:
        errors = validate_required_sheets(
            ["Settings", "Loans", "Balances", "Schedule"],
        )
        assert errors == []

    def test_missing_required_sheet(self) -> None:
        errors = validate_required_sheets(["Settings", "Loans"])
        assert len(errors) == 1
        assert errors[0].sheet == "Balances"
        assert "Обязательный лист отсутствует" in errors[0].message

    def test_missing_all_required(self) -> None:
        errors = validate_required_sheets(["Schedule", "Incomes"])
        assert len(errors) == 3
        sheets = {e.sheet for e in errors}
        assert sheets == REQUIRED_SHEETS

    def test_optional_sheet_missing_is_fine(self) -> None:
        # Only required sheets present — no errors
        errors = validate_required_sheets(["Settings", "Loans", "Balances"])
        assert errors == []

    def test_empty_list(self) -> None:
        errors = validate_required_sheets([])
        assert len(errors) == 3
