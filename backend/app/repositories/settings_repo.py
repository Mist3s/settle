"""Settings repository."""

import uuid

from sqlalchemy import select

from app.domain.models.settings import Setting
from app.repositories.base import Repository


class SettingsRepository(Repository[Setting]):
    model = Setting

    async def get_by_key(
        self, user_id: uuid.UUID, key: str
    ) -> Setting | None:
        """Find a setting by user_id and key."""
        stmt = select(Setting).where(
            Setting.user_id == user_id,
            Setting.key == key,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Setting]:
        """Return all settings for a user."""
        stmt = (
            select(Setting)
            .where(Setting.user_id == user_id)
            .order_by(Setting.key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
