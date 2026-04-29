"""Pydantic schemas for dashboard and forecast API responses.

Matches the API contract from architecture §8.2 (Dashboard section).
All monetary amounts serialised as strings to preserve precision.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------


class DailyBalance(BaseModel):
    """Single data-point in the balance-by-day forecast curve."""

    date: date
    balance: str  # Decimal as string

    @classmethod
    def from_values(cls, d: date, b: Decimal) -> "DailyBalance":
        return cls(date=d, balance=str(b))


class ForecastResponse(BaseModel):
    """Response for GET /api/forecast/balance-by-day."""

    from_date: date
    to_date: date
    starting_balance: str
    points: list[DailyBalance]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class NextPayment(BaseModel):
    """Upcoming payment summary for dashboard widget."""

    model_config = ConfigDict(from_attributes=True)

    loan_id: str
    loan_name: str
    creditor: str
    due_date: date
    amount: str
    status: str
    can_pay_early: bool


class CurrentPeriod(BaseModel):
    """Financial summary for current period (between two incomes)."""

    from_date: date
    to_date: date
    income: str
    planned_payments_total: str
    remaining_for_living: str
    status: str  # "comfortable" | "tight" | "deficit"


class DashboardTotals(BaseModel):
    """Aggregate debt totals."""

    total_debt: str
    active_loans: int
    month_to_month_change: str


class DashboardWarning(BaseModel):
    """Warning item for dashboard alerts."""

    type: str
    message: str


class DashboardResponse(BaseModel):
    """Unified dashboard response — single object for the frontend.

    Matches architecture §8.2 Dashboard contract.
    """

    next_payments: list[NextPayment]
    current_period: CurrentPeriod
    next_period: CurrentPeriod | None = None
    totals: DashboardTotals
    warnings: list[DashboardWarning]
