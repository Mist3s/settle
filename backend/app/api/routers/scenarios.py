"""Scenarios REST router -- thin HTTP layer delegating to scenario_service.

Includes overlay simulator endpoints (architecture 6.4-6.5):
- GET  /{id}/forecast  -- as-is + to-be + diff
- POST /{id}/apply     -- materialize scenario
- POST /{id}/archive   -- archive scenario
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.domain.enums import ScenarioStatus
from app.domain.models.user import User
from app.domain.schemas.scenario import (
    ScenarioActionCreate,
    ScenarioActionResponse,
    ScenarioActionUpdate,
    ScenarioCreate,
    ScenarioResponse,
    ScenarioUpdate,
)
from app.domain.schemas.simulation import (
    ScenarioForecastResponse,
)
from app.services import scenario_service
from app.services.simulation.engine import build_forecast
from app.services.simulation.materializer import (
    apply_scenario,
    archive_scenario,
)

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioResponse])
async def list_scenarios(
    scenario_status: ScenarioStatus | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ScenarioResponse]:
    return await scenario_service.list_scenarios(
        session, current_user.id, status=scenario_status,
    )


@router.post("", response_model=ScenarioResponse, status_code=201)
async def create_scenario(
    body: ScenarioCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScenarioResponse:
    scenario = await scenario_service.create_scenario(
        session, current_user.id,
        name=body.name, base_date=body.base_date,
    )
    await session.commit()
    return scenario


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScenarioResponse:
    s = await scenario_service.get_scenario(
        session, current_user.id, scenario_id,
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Сценарий не найден")
    return s


@router.patch("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: UUID,
    body: ScenarioUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScenarioResponse:
    data = body.model_dump(exclude_unset=True)
    s = await scenario_service.update_scenario(
        session, current_user.id, scenario_id, **data,
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Сценарий не найден")
    await session.commit()
    return s


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    s = await scenario_service.delete_scenario(
        session, current_user.id, scenario_id,
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Сценарий не найден")
    await session.commit()


# --- Actions ---

@router.get(
    "/{scenario_id}/actions",
    response_model=list[ScenarioActionResponse],
)
async def list_actions(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ScenarioActionResponse]:
    return await scenario_service.list_actions(
        session, current_user.id, scenario_id,
    )


@router.post(
    "/{scenario_id}/actions",
    response_model=ScenarioActionResponse,
    status_code=201,
)
async def create_action(
    scenario_id: UUID,
    body: ScenarioActionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScenarioActionResponse:
    action = await scenario_service.create_action(
        session, current_user.id, scenario_id,
        action_type=body.action_type,
        loan_id=body.loan_id,
        income_id=body.income_id,
        planned_payment_id=body.planned_payment_id,
        effective_date=body.effective_date,
        params=body.params,
    )
    if action is None:
        raise HTTPException(status_code=404, detail="Сценарий не найден")
    await session.commit()
    return action


@router.patch(
    "/{scenario_id}/actions/{action_id}",
    response_model=ScenarioActionResponse,
)
async def update_action(
    scenario_id: UUID,
    action_id: UUID,
    body: ScenarioActionUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScenarioActionResponse:
    data = body.model_dump(exclude_unset=True)
    action = await scenario_service.update_action(
        session, current_user.id, scenario_id, action_id, **data,
    )
    if action is None:
        raise HTTPException(status_code=404, detail="Действие не найдено")
    await session.commit()
    return action


@router.delete(
    "/{scenario_id}/actions/{action_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_action(
    scenario_id: UUID,
    action_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    action = await scenario_service.delete_action(
        session, current_user.id, scenario_id, action_id,
    )
    if action is None:
        raise HTTPException(status_code=404, detail="Действие не найдено")
    await session.commit()


# --- Simulation overlay endpoints ---


@router.get(
    "/{scenario_id}/forecast",
    response_model=ScenarioForecastResponse,
)
async def scenario_forecast(
    scenario_id: UUID,
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    starting_balance: str = Query("0"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScenarioForecastResponse:
    """Build as-is + to-be forecast for a scenario.

    Architecture §6.5: returns both projections in one response.
    """
    s = await scenario_service.get_scenario(
        session, current_user.id, scenario_id,
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Сценарий не найден")

    return await build_forecast(
        session,
        user_id=current_user.id,
        scenario=s,
        from_date=from_date,
        to_date=to_date,
        starting_balance=Decimal(starting_balance),
    )


@router.post("/{scenario_id}/apply")
async def apply_scenario_endpoint(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Materialize a draft scenario into real DB records.

    Architecture §6.4: one transaction per apply.
    """
    s = await scenario_service.get_scenario(
        session, current_user.id, scenario_id,
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Сценарий не найден")

    try:
        result = await apply_scenario(session, current_user.id, s)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await session.commit()
    return result


@router.post(
    "/{scenario_id}/archive",
    response_model=ScenarioResponse,
)
async def archive_scenario_endpoint(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScenarioResponse:
    """Archive a scenario (any status → archived)."""
    s = await scenario_service.get_scenario(
        session, current_user.id, scenario_id,
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Сценарий не найден")

    result = await archive_scenario(session, current_user.id, s)
    await session.commit()
    return result
