"""Scenario service — business logic for scenarios and actions."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction
from app.domain.models.scenario import Scenario, ScenarioAction
from app.repositories.scenario_repo import (
    ScenarioActionRepository,
    ScenarioRepository,
)
from app.services import audit_service


async def list_scenarios(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: str | None = None,
) -> list[Scenario]:
    repo = ScenarioRepository(session)
    filters: dict = {"user_id": user_id}
    if status is not None:
        filters["status"] = status
    return await repo.list(filters=filters)


async def get_scenario(
    session: AsyncSession,
    user_id: uuid.UUID,
    scenario_id: uuid.UUID,
) -> Scenario | None:
    repo = ScenarioRepository(session)
    s = await repo.get(scenario_id)
    if s is None or s.user_id != user_id:
        return None
    return s


async def create_scenario(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    name: str,
    base_date,
) -> Scenario:
    repo = ScenarioRepository(session)
    scenario = await repo.create(
        user_id=user_id, name=name, base_date=base_date,
    )
    await audit_service.record(
        session,
        entity_type="scenarios",
        entity_id=scenario.id,
        action=AuditAction.CREATE,
        after_state=audit_service.model_to_dict(scenario),
        changed_by=user_id,
    )
    return scenario


async def update_scenario(
    session: AsyncSession,
    user_id: uuid.UUID,
    scenario_id: uuid.UUID,
    **kwargs,
) -> Scenario | None:
    repo = ScenarioRepository(session)
    s = await repo.get(scenario_id)
    if s is None or s.user_id != user_id:
        return None
    before = audit_service.model_to_dict(s)
    if kwargs:
        await repo.update(scenario_id, **kwargs)
    after = audit_service.model_to_dict(s)
    await audit_service.record(
        session,
        entity_type="scenarios",
        entity_id=s.id,
        action=AuditAction.UPDATE,
        before_state=before,
        after_state=after,
        changed_by=user_id,
    )
    return s


async def delete_scenario(
    session: AsyncSession,
    user_id: uuid.UUID,
    scenario_id: uuid.UUID,
) -> Scenario | None:
    repo = ScenarioRepository(session)
    s = await repo.get(scenario_id)
    if s is None or s.user_id != user_id:
        return None
    before = audit_service.model_to_dict(s)
    await repo.soft_delete(scenario_id)
    after = audit_service.model_to_dict(s)
    await audit_service.record(
        session,
        entity_type="scenarios",
        entity_id=s.id,
        action=AuditAction.DELETE,
        before_state=before,
        after_state=after,
        changed_by=user_id,
    )
    return s


# --- Actions ---


async def create_action(
    session: AsyncSession,
    user_id: uuid.UUID,
    scenario_id: uuid.UUID,
    **kwargs,
) -> ScenarioAction | None:
    s_repo = ScenarioRepository(session)
    s = await s_repo.get(scenario_id)
    if s is None or s.user_id != user_id:
        return None
    a_repo = ScenarioActionRepository(session)
    return await a_repo.create(scenario_id=scenario_id, **kwargs)


async def update_action(
    session: AsyncSession,
    user_id: uuid.UUID,
    scenario_id: uuid.UUID,
    action_id: uuid.UUID,
    **kwargs,
) -> ScenarioAction | None:
    s_repo = ScenarioRepository(session)
    s = await s_repo.get(scenario_id)
    if s is None or s.user_id != user_id:
        return None
    a_repo = ScenarioActionRepository(session)
    action = await a_repo.get(action_id)
    if action is None or action.scenario_id != scenario_id:
        return None
    if kwargs:
        await a_repo.update(action_id, **kwargs)
    return action


async def delete_action(
    session: AsyncSession,
    user_id: uuid.UUID,
    scenario_id: uuid.UUID,
    action_id: uuid.UUID,
) -> ScenarioAction | None:
    s_repo = ScenarioRepository(session)
    s = await s_repo.get(scenario_id)
    if s is None or s.user_id != user_id:
        return None
    a_repo = ScenarioActionRepository(session)
    action = await a_repo.get(action_id)
    if action is None or action.scenario_id != scenario_id:
        return None
    await session.delete(action)
    await session.flush()
    return action
