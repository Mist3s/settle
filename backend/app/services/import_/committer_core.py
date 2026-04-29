"""Shared types and helpers for the import committer package."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction
from app.services import audit_service


@dataclass
class CommitResult:
    """Counters of committed entities per type."""

    loans_created: int = 0
    loans_updated: int = 0
    balances_created: int = 0
    balances_updated: int = 0
    incomes_created: int = 0
    incomes_updated: int = 0
    schedule_created: int = 0
    schedule_updated: int = 0
    schedule_cancelled: int = 0
    actual_payments_created: int = 0
    actual_payments_updated: int = 0
    schedules_auto_generated: int = 0
    settings_created: int = 0
    settings_updated: int = 0


async def create_with_audit(
    session: AsyncSession,
    entity: Any,
    entity_type: str,
    user_id: uuid.UUID,
) -> None:
    """Add *entity* to session, flush, refresh, and record audit CREATE."""
    session.add(entity)
    await session.flush()
    await session.refresh(entity)
    await audit_service.record(
        session,
        entity_type=entity_type,
        entity_id=entity.id,
        action=AuditAction.CREATE,
        after_state=audit_service.model_to_dict(entity),
        changed_by=user_id,
    )


async def update_with_audit(
    session: AsyncSession,
    entity: Any,
    updates: dict[str, Any],
    entity_type: str,
    user_id: uuid.UUID,
) -> None:
    """Apply *updates* to *entity*, flush, refresh, and record audit UPDATE."""
    before = audit_service.model_to_dict(entity)
    for k, v in updates.items():
        setattr(entity, k, v)
    await session.flush()
    await session.refresh(entity)
    await audit_service.record(
        session,
        entity_type=entity_type,
        entity_id=entity.id,
        action=AuditAction.UPDATE,
        before_state=before,
        after_state=audit_service.model_to_dict(entity),
        changed_by=user_id,
    )
