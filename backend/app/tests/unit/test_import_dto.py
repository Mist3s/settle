"""Unit tests for domain/schemas/import_dto.py — helper parsers and DTO models."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.schemas.import_dto import (
    ActualPaymentImportRow,
    BalanceImportRow,
    IncomeImportRow,
    LoanImportRow,
    ScheduleImportRow,
    SettingImportRow,
    _parse_bool,
    _parse_date,
    _parse_decimal,
)

# ---------------------------------------------------------------------------
# _parse_decimal
# ---------------------------------------------------------------------------


class TestParseDecimal:
    def test_dot_separator(self) -> None:
        assert _parse_decimal("123.45") == Decimal("123.45")

    def test_comma_separator(self) -> None:
        assert _parse_decimal("123,45") == Decimal("123.45")

    def test_non_breaking_space(self) -> None:
        assert _parse_decimal("1\u00a0234,56") == Decimal("1234.56")

    def test_regular_space(self) -> None:
        assert _parse_decimal("1 234.56") == Decimal("1234.56")

    def test_empty_string(self) -> None:
        assert _parse_decimal("") is None

    def test_whitespace_only(self) -> None:
        assert _parse_decimal("   ") is None

    def test_none(self) -> None:
        assert _parse_decimal(None) is None

    def test_invalid_string(self) -> None:
        with pytest.raises(ValueError, match="Невозможно преобразовать в число"):
            _parse_decimal("abc")

    def test_passthrough_decimal(self) -> None:
        d = Decimal("99.99")
        assert _parse_decimal(d) is d

    def test_integer_input(self) -> None:
        assert _parse_decimal(42) == Decimal("42")

    def test_float_input(self) -> None:
        # float → str → Decimal (expected lossy repr, just verify no crash)
        result = _parse_decimal(3.14)
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# _parse_bool
# ---------------------------------------------------------------------------


class TestParseBool:
    @pytest.mark.parametrize("raw", ["true", "True", "TRUE", "1", "yes", "Yes", "да", "Да"])
    def test_truthy(self, raw: str) -> None:
        assert _parse_bool(raw) is True

    @pytest.mark.parametrize("raw", ["false", "False", "FALSE", "0", "no", "No", "нет", "Нет"])
    def test_falsy(self, raw: str) -> None:
        assert _parse_bool(raw) is False

    def test_bool_passthrough_true(self) -> None:
        assert _parse_bool(True) is True

    def test_bool_passthrough_false(self) -> None:
        assert _parse_bool(False) is False

    def test_none(self) -> None:
        assert _parse_bool(None) is None

    def test_empty_string(self) -> None:
        assert _parse_bool("") is None

    def test_garbage(self) -> None:
        with pytest.raises(ValueError, match="Невозможно преобразовать в boolean"):
            _parse_bool("maybe")


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_iso_format(self) -> None:
        assert _parse_date("2025-06-15") == date(2025, 6, 15)

    def test_date_passthrough(self) -> None:
        d = date(2025, 1, 1)
        assert _parse_date(d) is d

    def test_excel_serial_int(self) -> None:
        # 2025-01-01 = days since 1899-12-30 = 45658
        assert _parse_date(45658) == date(2025, 1, 1)

    def test_excel_serial_float(self) -> None:
        # float serial — truncated to int
        assert _parse_date(45658.75) == date(2025, 1, 1)

    def test_string_number_excel(self) -> None:
        # Excel sometimes gives serial as text — goes through str branch
        # "45658" is not ISO, so it will raise ValueError
        with pytest.raises(ValueError, match="Невозможно преобразовать в дату"):
            _parse_date("45658")

    def test_none(self) -> None:
        assert _parse_date(None) is None

    def test_empty_string(self) -> None:
        assert _parse_date("") is None

    def test_invalid_date_string(self) -> None:
        with pytest.raises(ValueError, match="Невозможно преобразовать в дату"):
            _parse_date("not-a-date")


# ---------------------------------------------------------------------------
# SettingImportRow
# ---------------------------------------------------------------------------


class TestSettingImportRow:
    def test_happy_path(self) -> None:
        row = SettingImportRow(key="lang", value="ru", description="Language")
        assert row.key == "lang"
        assert row.description == "Language"

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            SettingImportRow(key="k", value="v", unknown="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# LoanImportRow
# ---------------------------------------------------------------------------


class TestLoanImportRow:
    def _valid(self, **overrides: object) -> dict:
        defaults: dict = {
            "code": "LOAN01",
            "creditor": "Bank A",
            "name": "Mortgage",
            "loan_type": "credit",
            "payment_method": "annuity",
        }
        defaults.update(overrides)
        return defaults

    def test_happy_path_minimal(self) -> None:
        row = LoanImportRow(**self._valid())
        assert row.code == "LOAN01"
        assert row.original_amount is None

    def test_decimal_coercion(self) -> None:
        row = LoanImportRow(**self._valid(original_amount="1 000,50"))
        assert row.original_amount == Decimal("1000.50")

    def test_date_coercion(self) -> None:
        row = LoanImportRow(**self._valid(opening_date="2024-03-01"))
        assert row.opening_date == date(2024, 3, 1)

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            LoanImportRow(**self._valid(bogus="nope"))


# ---------------------------------------------------------------------------
# BalanceImportRow
# ---------------------------------------------------------------------------


class TestBalanceImportRow:
    def _valid(self, **overrides: object) -> dict:
        defaults: dict = {
            "loan_code": "L1",
            "snapshot_date": "2025-06-01",
            "current_balance": "500000",
        }
        defaults.update(overrides)
        return defaults

    def test_happy_path(self) -> None:
        row = BalanceImportRow(**self._valid())
        assert row.current_balance == Decimal("500000")
        assert row.principal_balance is None

    def test_decimal_coercion(self) -> None:
        row = BalanceImportRow(**self._valid(current_balance="1\u00a0000,99"))
        assert row.current_balance == Decimal("1000.99")

    def test_date_coercion_serial(self) -> None:
        row = BalanceImportRow(**self._valid(snapshot_date=45658))
        assert row.snapshot_date == date(2025, 1, 1)

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            BalanceImportRow(**self._valid(extra_col="x"))


# ---------------------------------------------------------------------------
# ScheduleImportRow
# ---------------------------------------------------------------------------


class TestScheduleImportRow:
    def _valid(self, **overrides: object) -> dict:
        defaults: dict = {
            "loan_code": "L1",
            "due_date": "2025-07-01",
            "amount": "15000",
        }
        defaults.update(overrides)
        return defaults

    def test_happy_path(self) -> None:
        row = ScheduleImportRow(**self._valid())
        assert row.amount == Decimal("15000")
        assert row.can_pay_early is None

    def test_bool_coercion(self) -> None:
        row = ScheduleImportRow(**self._valid(can_pay_early="да"))
        assert row.can_pay_early is True

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            ScheduleImportRow(**self._valid(phantom="y"))


# ---------------------------------------------------------------------------
# IncomeImportRow
# ---------------------------------------------------------------------------


class TestIncomeImportRow:
    def _valid(self, **overrides: object) -> dict:
        defaults: dict = {
            "code": "INC01",
            "expected_date": "2025-08-15",
        }
        defaults.update(overrides)
        return defaults

    def test_happy_path(self) -> None:
        row = IncomeImportRow(**self._valid())
        assert row.code == "INC01"

    def test_decimal_coercion(self) -> None:
        row = IncomeImportRow(**self._valid(amount_rub="50 000,00"))
        assert row.amount_rub == Decimal("50000.00")

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            IncomeImportRow(**self._valid(surprise="!"))


# ---------------------------------------------------------------------------
# ActualPaymentImportRow
# ---------------------------------------------------------------------------


class TestActualPaymentImportRow:
    def _valid(self, **overrides: object) -> dict:
        defaults: dict = {
            "loan_code": "L1",
            "payment_date": "2025-06-20",
            "amount": "15000",
        }
        defaults.update(overrides)
        return defaults

    def test_happy_path(self) -> None:
        row = ActualPaymentImportRow(**self._valid())
        assert row.amount == Decimal("15000")
        assert row.planned_due_date is None

    def test_dual_date_coercion(self) -> None:
        row = ActualPaymentImportRow(
            **self._valid(planned_due_date="2025-06-15")
        )
        assert row.planned_due_date == date(2025, 6, 15)

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            ActualPaymentImportRow(**self._valid(hack="z"))
