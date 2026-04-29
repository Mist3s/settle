"""Pydantic schemas for LoanBalance entity."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import BalanceSource


class BalanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: str = Field(..., description="current_balance as Decimal string")
    principal_balance: str | None = None
    snapshot_date: date
    source: BalanceSource = BalanceSource.MANUAL
    notes: str | None = None


class BalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    loan_id: UUID
    snapshot_date: date
    current_balance: str
    principal_balance: str
    accrued_interest: str
    source: BalanceSource
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, obj: object) -> "BalanceResponse":
        data: dict = {}
        for field_name in cls.model_fields:
            value = getattr(obj, field_name, None)
            if isinstance(value, Decimal):
                value = str(value)
            data[field_name] = value
        return cls(**data)
