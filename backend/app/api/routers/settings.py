"""Settings REST router — thin HTTP layer delegating to settings_service."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.domain.models.user import User
from app.domain.schemas.settings import SettingResponse, SettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=list[SettingResponse])
async def get_settings(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[SettingResponse]:
    return await settings_service.list_settings(session, current_user.id)


@router.patch("", response_model=list[SettingResponse])
async def update_settings(
    body: SettingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[SettingResponse]:
    items = [item.model_dump() for item in body.items]
    result = await settings_service.upsert_settings(
        session, current_user.id, items,
    )
    await session.commit()
    return result
