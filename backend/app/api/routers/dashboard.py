"""Dashboard and forecast API router.

Endpoints:
    GET /api/dashboard              → aggregated dashboard response
    GET /api/forecast/balance-by-day → daily balance projection
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.domain.models.user import User
from app.domain.schemas.dashboard import DashboardResponse, ForecastResponse
from app.services import dashboard_service, forecast_service

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    """Return the aggregated dashboard for the main view."""
    return await dashboard_service.get_dashboard(session, current_user.id)


@router.get("/forecast/balance-by-day", response_model=ForecastResponse)
async def get_balance_by_day(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    starting_balance: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ForecastResponse:
    """Return daily balance projection over the given date range."""
    try:
        balance = Decimal(starting_balance)
    except (InvalidOperation, ValueError):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail="starting_balance must be a valid decimal number",
        ) from None

    points = await forecast_service.forecast_balance_by_day(
        session=session,
        user_id=current_user.id,
        starting_balance=balance,
        from_date=from_date,
        to_date=to_date,
    )

    return ForecastResponse(
        from_date=from_date,
        to_date=to_date,
        starting_balance=starting_balance,
        points=points,
    )
