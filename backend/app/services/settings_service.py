"""Settings service — business logic for user settings."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction
from app.domain.models.settings import Setting
from app.repositories.settings_repo import SettingsRepository
from app.services import audit_service


async def list_settings(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[Setting]:
    repo = SettingsRepository(session)
    return await repo.list_by_user(user_id)


async def upsert_settings(
    session: AsyncSession,
    user_id: uuid.UUID,
    items: list[dict],
) -> list[Setting]:
    """Batch upsert settings.

    Each item is ``{"key": ..., "value": ..., "description": ...}``.
    """
    repo = SettingsRepository(session)
    for item in items:
        existing = await repo.get_by_key(user_id, item["key"])
        if existing is not None:
            before = audit_service.model_to_dict(existing)
            existing.value = item["value"]
            if item.get("description") is not None:
                existing.description = item["description"]
            await session.flush()
            await session.refresh(existing)
            after = audit_service.model_to_dict(existing)
            await audit_service.record(
                session,
                entity_type="settings",
                entity_id=existing.id,
                action=AuditAction.UPDATE,
                before_state=before,
                after_state=after,
                changed_by=user_id,
            )
        else:
            setting = await repo.create(
                user_id=user_id,
                key=item["key"],
                value=item["value"],
                description=item.get("description"),
            )
            await audit_service.record(
                session,
                entity_type="settings",
                entity_id=setting.id,
                action=AuditAction.CREATE,
                after_state=audit_service.model_to_dict(setting),
                changed_by=user_id,
            )
    return await repo.list_by_user(user_id)
