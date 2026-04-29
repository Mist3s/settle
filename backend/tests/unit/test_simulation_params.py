"""Unit tests for simulation params validators."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.schemas.simulation import (
    AddIncomeParams,
    ChangePaymentDateParams,
    CloseEarlyFullParams,
    PrepaymentPartialParams,
    ReducePaymentParams,
    SkipParams,
    validate_action_params,
)


class TestCloseEarlyFullParams:
    def test_empty_is_valid(self):
        p = CloseEarlyFullParams()
        assert p is not None

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            CloseEarlyFullParams(foo="bar")


class TestPrepaymentPartialParams:
    def test_valid(self):
        p = PrepaymentPartialParams(amount="10000.00")
        assert Decimal(p.amount) == Decimal("10000.00")

    def test_zero_amount_rejected(self):
        with pytest.raises(ValueError):
            PrepaymentPartialParams(amount="0")

    def test_negative_amount_rejected(self):
        with pytest.raises(ValueError):
            PrepaymentPartialParams(amount="-100")


class TestReducePaymentParams:
    def test_valid(self):
        p = ReducePaymentParams(new_amount="5000.00")
        assert Decimal(p.new_amount) == Decimal("5000.00")

    def test_zero_rejected(self):
        with pytest.raises(ValueError):
            ReducePaymentParams(new_amount="0")


class TestSkipParams:
    def test_empty_is_valid(self):
        p = SkipParams()
        assert p is not None


class TestAddIncomeParams:
    def test_valid(self):
        p = AddIncomeParams(amount="50000", name="Бонус")
        assert p.name == "Бонус"

    def test_zero_amount_rejected(self):
        with pytest.raises(ValueError):
            AddIncomeParams(amount="0", name="x")


class TestChangePaymentDateParams:
    def test_valid(self):
        p = ChangePaymentDateParams(new_date=date(2026, 7, 1))
        assert p.new_date == date(2026, 7, 1)


class TestValidateActionParams:
    def test_dispatches_correctly(self):
        result = validate_action_params("close_early_full", {})
        assert isinstance(result, CloseEarlyFullParams)

    def test_prepayment_partial(self):
        result = validate_action_params(
            "prepayment_partial", {"amount": "10000"}
        )
        assert isinstance(result, PrepaymentPartialParams)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown action_type"):
            validate_action_params("nonexistent", {})

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            validate_action_params("prepayment_partial", {})
