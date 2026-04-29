"""Pydantic schemas for Loan entity."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    LoanStatus,
    LoanType,
    PaymentMethod,
    PrepaymentStrategy,
)


class LoanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., max_length=32)
    creditor: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    loan_type: LoanType
    payment_method: PaymentMethod
    original_amount: str | None = None  # Decimal as string in JSON
    interest_rate: str = "0"  # Decimal as string
    opening_date: date | None = None
    closing_date: date | None = None
    prepayment_strategy: PrepaymentStrategy = PrepaymentStrategy.REDUCE_PAYMENT
    priority: int | None = None
    status: LoanStatus = LoanStatus.ACTIVE
    contract_number: str | None = Field(None, max_length=100)
    notes: str | None = None
    late_fee_rate: str | None = None
    months_remaining: int | None = None
    payment_day: int | None = None


class LoanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(None, max_length=32)
    creditor: str | None = Field(None, max_length=255)
    name: str | None = Field(None, max_length=255)
    loan_type: LoanType | None = None
    payment_method: PaymentMethod | None = None
    original_amount: str | None = None
    interest_rate: str | None = None
    opening_date: date | None = None
    closing_date: date | None = None
    prepayment_strategy: PrepaymentStrategy | None = None
    priority: int | None = None
    status: LoanStatus | None = None
    contract_number: str | None = Field(None, max_length=100)
    notes: str | None = None
    late_fee_rate: str | None = None
    months_remaining: int | None = None
    payment_day: int | None = None


class LoanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    code: str
    creditor: str
    name: str
    loan_type: LoanType
    payment_method: PaymentMethod
    original_amount: str | None = None
    interest_rate: str
    opening_date: date | None = None
    closing_date: date | None = None
    prepayment_strategy: PrepaymentStrategy
    priority: int | None = None
    status: LoanStatus
    contract_number: str | None = None
    notes: str | None = None
    late_fee_rate: str | None = None
    months_remaining: int | None = None
    payment_day: int | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, obj: object) -> "LoanResponse":
        """Build response from ORM model, converting Decimals to strings."""
        data: dict = {}
        for field_name in cls.model_fields:
            value = getattr(obj, field_name, None)
            if isinstance(value, Decimal):
                value = str(value)
            data[field_name] = value
        return cls(**data)
