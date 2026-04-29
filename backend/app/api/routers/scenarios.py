"""Scenarios REST router — thin HTTP layer delegating to scenario_service."""

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
from app.services import scenario_service

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
