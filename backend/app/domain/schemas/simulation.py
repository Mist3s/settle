"""Pydantic schemas for the overlay simulator (architecture §6).

Defines:
- Params validators for each ScenarioActionType (JSONB params field)
- ScenarioForecastResponse — as-is + to-be + diff in one response
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.schemas.dashboard import DailyBalance

# ---------------------------------------------------------------------------
# Action params validators — one per ScenarioActionType
# Architecture §6.2: params JSONB validated by type
# ---------------------------------------------------------------------------


class CloseEarlyFullParams(BaseModel):
    """close_early_full: no extra params (loan_id and date on parent)."""

    model_config = ConfigDict(extra="forbid")


class PrepaymentPartialParams(BaseModel):
    """prepayment_partial: amount to pay down."""

    model_config = ConfigDict(extra="forbid")

    amount: str = Field(..., description="Decimal amount as string")

    @model_validator(mode="after")
    def _validate_amount(self) -> PrepaymentPartialParams:
        val = Decimal(self.amount)
        if val <= 0:
            msg = "amount must be > 0"
            raise ValueError(msg)
        return self


class ReducePaymentParams(BaseModel):
    """reduce_payment: new payment amount."""

    model_config = ConfigDict(extra="forbid")

    new_amount: str = Field(..., description="New payment amount as string")

    @model_validator(mode="after")
    def _validate_amount(self) -> ReducePaymentParams:
        val = Decimal(self.new_amount)
        if val <= 0:
            msg = "new_amount must be > 0"
            raise ValueError(msg)
        return self


class SkipParams(BaseModel):
    """skip: no extra params (planned_payment_id on parent)."""

    model_config = ConfigDict(extra="forbid")


class AddIncomeParams(BaseModel):
    """add_income: new income event."""

    model_config = ConfigDict(extra="forbid")

    amount: str = Field(..., description="Income amount as string")
    name: str = Field(..., max_length=255, description="Income label")

    @model_validator(mode="after")
    def _validate_amount(self) -> AddIncomeParams:
        val = Decimal(self.amount)
        if val <= 0:
            msg = "amount must be > 0"
            raise ValueError(msg)
        return self


class ChangePaymentDateParams(BaseModel):
    """change_payment_date: new date for a planned payment."""

    model_config = ConfigDict(extra="forbid")

    new_date: date


# ---------------------------------------------------------------------------
# Lookup: action_type → params model
# ---------------------------------------------------------------------------

ACTION_PARAMS_MODELS: dict[str, type[BaseModel]] = {
    "close_early_full": CloseEarlyFullParams,
    "prepayment_partial": PrepaymentPartialParams,
    "reduce_payment": ReducePaymentParams,
    "skip": SkipParams,
    "add_income": AddIncomeParams,
    "change_payment_date": ChangePaymentDateParams,
}


def validate_action_params(action_type: str, params: dict[str, Any] | None) -> BaseModel:
    """Validate params JSONB against the expected model for action_type.

    Raises ValueError if validation fails.
    """
    model_cls = ACTION_PARAMS_MODELS.get(action_type)
    if model_cls is None:
        msg = f"Unknown action_type: {action_type}"
        raise ValueError(msg)
    return model_cls(**(params or {}))


# ---------------------------------------------------------------------------
# Forecast response schemas
# ---------------------------------------------------------------------------


class PaymentSummary(BaseModel):
    """A single payment in the forecast projection."""

    loan_id: str | None = None
    loan_name: str | None = None
    due_date: date
    amount: str
    status: str
    kind: str | None = None  # "synthetic" for overlay-generated


class ScenarioForecastDiff(BaseModel):
    """Numeric diff between as-is and to-be projections."""

    total_paid_difference: str  # Decimal as string
    total_interest_saved: str
    first_zero_balance_date_current: date | None = None
    first_zero_balance_date_scenario: date | None = None


class ProjectionData(BaseModel):
    """One side of the as-is / to-be comparison."""

    balance_by_day: list[DailyBalance]
    payments: list[PaymentSummary]


class ScenarioForecastResponse(BaseModel):
    """Response for GET /api/scenarios/{id}/forecast.

    Architecture §6.5: as-is + to-be + diff in one response.
    """

    current: ProjectionData
    scenario: ProjectionData
    diff: ScenarioForecastDiff
