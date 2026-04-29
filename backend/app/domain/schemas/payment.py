"""Pydantic schemas for PlannedPayment and ActualPayment entities."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ActualPaymentType,
    PaymentAccuracy,
    PaymentStatus,
)

# ---------------------------------------------------------------------------
# PlannedPayment
# ---------------------------------------------------------------------------


class PlannedPaymentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    due_date: date | None = None
    amount: str | None = None
    principal_part: str | None = None
    interest_part: str | None = None
    status: PaymentStatus | None = None
    accuracy: PaymentAccuracy | None = None
    income_id: UUID | None = None
    can_pay_early: bool | None = None
    notes: str | None = None


class PlannedPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    loan_id: UUID
    income_id: UUID | None = None
    due_date: date
    amount: str
    principal_part: str | None = None
    interest_part: str | None = None
    status: PaymentStatus
    accuracy: PaymentAccuracy
    can_pay_early: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, obj: object) -> "PlannedPaymentResponse":
        data: dict = {}
        for field_name in cls.model_fields:
            value = getattr(obj, field_name, None)
            if isinstance(value, Decimal):
                value = str(value)
            data[field_name] = value
        return cls(**data)


# ---------------------------------------------------------------------------
# ActualPayment
# ---------------------------------------------------------------------------


class ActualPaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loan_id: UUID
    planned_payment_id: UUID | None = None
    amount: str = Field(..., description="Decimal as string")
    principal_part: str | None = None
    interest_part: str | None = None
    payment_date: date
    payment_type: ActualPaymentType
    notes: str | None = None


class ActualPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    loan_id: UUID
    planned_payment_id: UUID | None = None
    amount: str
    principal_part: str | None = None
    interest_part: str | None = None
    payment_date: date
    payment_type: ActualPaymentType
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, obj: object) -> "ActualPaymentResponse":
        data: dict = {}
        for field_name in cls.model_fields:
            value = getattr(obj, field_name, None)
            if isinstance(value, Decimal):
                value = str(value)
            data[field_name] = value
        return cls(**data)
