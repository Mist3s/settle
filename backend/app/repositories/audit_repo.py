"""AuditLog repository — read-only queries for audit trail."""

import uuid

from sqlalchemy import select

from app.domain.models.audit import AuditLog
from app.repositories.base import Repository


class AuditLogRepository(Repository[AuditLog]):
    model = AuditLog

    async def list_by_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Return audit entries for a specific entity, newest first."""
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.changed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
