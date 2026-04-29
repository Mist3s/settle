"""Generic async repository with soft-delete support.

Provides standard CRUD operations for any SQLAlchemy model.
Models with SoftDeleteMixin are filtered automatically — deleted
records are invisible unless explicitly requested.
"""

import uuid
from datetime import UTC
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository[ModelT: Base]:
    """Generic repository for async SQLAlchemy models.

    Subclass and set ``model`` to the target ORM class.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _has_soft_delete(self) -> bool:
        """Return True if the model supports soft-delete."""
        return hasattr(self.model, "is_deleted")

    def _base_query(self, *, include_deleted: bool = False):
        """Build a SELECT filtering out soft-deleted rows by default."""
        stmt = select(self.model)
        if self._has_soft_delete() and not include_deleted:
            stmt = stmt.where(self.model.is_deleted.is_(False))  # type: ignore[attr-defined]
        return stmt

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get(
        self,
        entity_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> ModelT | None:
        """Get a single entity by primary key."""
        stmt = self._base_query(include_deleted=include_deleted).where(
            self.model.id == entity_id  # type: ignore[attr-defined]
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        include_deleted: bool = False,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ModelT]:
        """Return a list of entities with optional filtering and pagination."""
        stmt = self._base_query(include_deleted=include_deleted)

        if filters:
            for attr_name, value in filters.items():
                column = getattr(self.model, attr_name, None)
                if column is not None:
                    stmt = stmt.where(column == value)

        if order_by is not None:
            stmt = stmt.order_by(order_by)

        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, **kwargs: Any) -> ModelT:
        """Create and flush a new entity. Returns the instance with its PK."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(
        self,
        entity_id: uuid.UUID,
        **kwargs: Any,
    ) -> ModelT | None:
        """Update fields on an existing entity. Returns None if not found."""
        instance = await self.get(entity_id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def soft_delete(self, entity_id: uuid.UUID) -> ModelT | None:
        """Mark an entity as deleted (soft-delete). Returns None if not found."""
        instance = await self.get(entity_id)
        if instance is None:
            return None
        if not self._has_soft_delete():
            msg = f"{self.model.__name__} does not support soft-delete"
            raise TypeError(msg)
        from datetime import datetime

        instance.is_deleted = True  # type: ignore[attr-defined]
        instance.deleted_at = datetime.now(tz=UTC)  # type: ignore[attr-defined]
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def restore(self, entity_id: uuid.UUID) -> ModelT | None:
        """Restore a soft-deleted entity. Returns None if not found."""
        instance = await self.get(entity_id, include_deleted=True)
        if instance is None:
            return None
        if not self._has_soft_delete():
            msg = f"{self.model.__name__} does not support soft-delete"
            raise TypeError(msg)
        instance.is_deleted = False  # type: ignore[attr-defined]
        instance.deleted_at = None  # type: ignore[attr-defined]
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
