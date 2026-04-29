"""Audit service — writes to audit_log via SQLAlchemy event listeners.

Provides both an explicit ``record()`` method for manual audit entries
and automatic event listeners that can be attached to the session.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction
from app.domain.models.audit import AuditLog


def _serialize_value(value: Any) -> Any:
    """Convert non-JSON-serializable values for JSONB storage."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        # enum values
        return value.value
    return value


def model_to_dict(instance: Any) -> dict[str, Any]:
    """Serialize an ORM model instance to a JSON-safe dict.

    Only includes columns (not relationships). Reads from the
    instance __dict__ to avoid triggering lazy loads in async context.
    """
    from sqlalchemy import inspect as sa_inspect

    mapper = sa_inspect(type(instance))
    column_keys = {col.key for col in mapper.columns}
    result: dict[str, Any] = {}
    for key in column_keys:
        # Use __dict__ to avoid triggering lazy-load on relationships
        value = instance.__dict__.get(key)
        result[key] = _serialize_value(value)
    return result


async def record(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: AuditAction,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    changed_by: uuid.UUID | None = None,
) -> AuditLog:
    """Write an audit log entry and flush.

    This is the primary API for recording audit events.
    """
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_state=before_state,
        after_state=after_state,
        changed_at=datetime.now(tz=UTC),
        changed_by=changed_by,
    )
    session.add(entry)
    await session.flush()
    return entry
