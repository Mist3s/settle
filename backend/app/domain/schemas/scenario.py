"""Pydantic schemas for Scenario and ScenarioAction entities."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ScenarioActionType, ScenarioStatus

# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------


class ScenarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., max_length=255)
    base_date: date


class ScenarioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, max_length=255)
    base_date: date | None = None
    status: ScenarioStatus | None = None


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    base_date: date
    status: ScenarioStatus
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# ScenarioAction
# ---------------------------------------------------------------------------


class ScenarioActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: ScenarioActionType
    loan_id: UUID | None = None
    income_id: UUID | None = None
    planned_payment_id: UUID | None = None
    effective_date: date
    params: dict[str, Any] | None = None


class ScenarioActionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: ScenarioActionType | None = None
    loan_id: UUID | None = None
    income_id: UUID | None = None
    planned_payment_id: UUID | None = None
    effective_date: date | None = None
    params: dict[str, Any] | None = None


class ScenarioActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scenario_id: UUID
    action_type: ScenarioActionType
    loan_id: UUID | None = None
    income_id: UUID | None = None
    planned_payment_id: UUID | None = None
    effective_date: date
    params: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
