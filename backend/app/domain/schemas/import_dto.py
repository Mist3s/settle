"""Pydantic DTOs for XLSX import — one per template sheet.

These are separate from REST API schemas: they mirror the Excel column
layout exactly and handle coercion (comma→dot in decimals, lenient
booleans, date serial numbers).
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import (
    ActualPaymentType,
    BalanceSource,
    IncomeStatus,
    LoanStatus,
    LoanType,
    PaymentAccuracy,
    PaymentMethod,
    PrepaymentStrategy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_decimal(v: Any) -> Decimal | None:
    """Parse a decimal value from various Excel formats."""
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    if isinstance(v, Decimal):
        return v
    s = str(v).replace(",", ".").replace("\u00a0", "").replace(" ", "")
    try:
        return Decimal(s)
    except InvalidOperation as e:
        msg = f"Невозможно преобразовать в число: {v!r}"
        raise ValueError(msg) from e


def _parse_bool(v: Any) -> bool | None:
    """Parse boolean from various Excel representations."""
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "да"):
        return True
    if s in ("false", "0", "no", "нет"):
        return False
    msg = f"Невозможно преобразовать в boolean: {v!r}"
    raise ValueError(msg)


def _parse_date(v: Any) -> date | None:
    """Parse date from string or Excel serial number."""
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)):
        # Excel serial number (days since 1899-12-30)
        from datetime import timedelta
        epoch = date(1899, 12, 30)
        return epoch + timedelta(days=int(v))
    s = str(v).strip()
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        msg = f"Невозможно преобразовать в дату (ожидается YYYY-MM-DD): {v!r}"
        raise ValueError(msg) from e


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

class SettingImportRow(BaseModel):
    """One row from the 'Settings' sheet."""
    model_config = ConfigDict(extra="forbid")

    key: str
    value: str
    description: str | None = None


class LoanImportRow(BaseModel):
    """One row from the 'Loans' sheet."""
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., max_length=32)
    creditor: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    loan_type: LoanType
    payment_method: PaymentMethod
    original_amount: Decimal | None = None
    interest_rate: Decimal | None = None
    opening_date: date | None = None
    closing_date: date | None = None
    prepayment_strategy: PrepaymentStrategy | None = None
    priority: int | None = None
    status: LoanStatus | None = None
    contract_number: str | None = None
    notes: str | None = None

    @field_validator("original_amount", "interest_rate", mode="before")
    @classmethod
    def coerce_decimal(cls, v: Any) -> Decimal | None:
        return _parse_decimal(v)

    @field_validator("opening_date", "closing_date", mode="before")
    @classmethod
    def coerce_date(cls, v: Any) -> date | None:
        return _parse_date(v)


class BalanceImportRow(BaseModel):
    """One row from the 'Balances' sheet."""
    model_config = ConfigDict(extra="forbid")

    loan_code: str
    snapshot_date: date
    current_balance: Decimal
    principal_balance: Decimal | None = None
    accrued_interest: Decimal | None = None
    source: BalanceSource | None = None
    notes: str | None = None

    @field_validator(
        "current_balance", "principal_balance", "accrued_interest", mode="before"
    )
    @classmethod
    def coerce_decimal(cls, v: Any) -> Decimal | None:
        return _parse_decimal(v)

    @field_validator("snapshot_date", mode="before")
    @classmethod
    def coerce_date(cls, v: Any) -> date | None:
        return _parse_date(v)


class ScheduleImportRow(BaseModel):
    """One row from the 'Schedule' sheet."""
    model_config = ConfigDict(extra="forbid")

    loan_code: str
    due_date: date
    amount: Decimal
    principal_part: Decimal | None = None
    interest_part: Decimal | None = None
    accuracy: PaymentAccuracy | None = None
    can_pay_early: bool | None = None
    income_code: str | None = None
    notes: str | None = None

    @field_validator("amount", "principal_part", "interest_part", mode="before")
    @classmethod
    def coerce_decimal(cls, v: Any) -> Decimal | None:
        return _parse_decimal(v)

    @field_validator("due_date", mode="before")
    @classmethod
    def coerce_date(cls, v: Any) -> date | None:
        return _parse_date(v)

    @field_validator("can_pay_early", mode="before")
    @classmethod
    def coerce_bool(cls, v: Any) -> bool | None:
        return _parse_bool(v)


class IncomeImportRow(BaseModel):
    """One row from the 'Incomes' sheet."""
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., max_length=64)
    expected_date: date
    amount_rub: Decimal | None = None
    amount_usd: Decimal | None = None
    name: str | None = None
    status: IncomeStatus | None = None
    notes: str | None = None

    @field_validator("amount_rub", "amount_usd", mode="before")
    @classmethod
    def coerce_decimal(cls, v: Any) -> Decimal | None:
        return _parse_decimal(v)

    @field_validator("expected_date", mode="before")
    @classmethod
    def coerce_date(cls, v: Any) -> date | None:
        return _parse_date(v)


class ActualPaymentImportRow(BaseModel):
    """One row from the 'ActualPayments' sheet."""
    model_config = ConfigDict(extra="forbid")

    loan_code: str
    payment_date: date
    amount: Decimal
    principal_part: Decimal | None = None
    interest_part: Decimal | None = None
    payment_type: ActualPaymentType | None = None
    planned_due_date: date | None = None
    notes: str | None = None

    @field_validator("amount", "principal_part", "interest_part", mode="before")
    @classmethod
    def coerce_decimal(cls, v: Any) -> Decimal | None:
        return _parse_decimal(v)

    @field_validator("payment_date", "planned_due_date", mode="before")
    @classmethod
    def coerce_date(cls, v: Any) -> date | None:
        return _parse_date(v)
