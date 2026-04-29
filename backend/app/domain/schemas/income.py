"""Pydantic schemas for Income entity."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import IncomeStatus


class IncomeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., max_length=64)
    expected_date: date
    amount: str = Field(..., description="Decimal as string")
    name: str | None = Field(None, max_length=255)
    status: IncomeStatus = IncomeStatus.EXPECTED
    notes: str | None = None


class IncomeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(None, max_length=64)
    expected_date: date | None = None
    amount: str | None = None
    name: str | None = Field(None, max_length=255)
    status: IncomeStatus | None = None
    notes: str | None = None


class IncomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    code: str
    expected_date: date
    amount: str
    name: str | None = None
    status: IncomeStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, obj: object) -> "IncomeResponse":
        data: dict = {}
        for field_name in cls.model_fields:
            value = getattr(obj, field_name, None)
            if isinstance(value, Decimal):
                value = str(value)
            data[field_name] = value
        return cls(**data)
