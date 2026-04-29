"""Pydantic schemas for schedule-related responses."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class ScheduleEntryResponse(BaseModel):
    """One row of an annuity schedule (API response)."""

    model_config = ConfigDict(from_attributes=True)

    due_date: date
    amount: str  # Decimal as string
    principal_part: str
    interest_part: str
    balance_after: str
