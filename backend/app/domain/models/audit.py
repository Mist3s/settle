"""AuditLog ORM model — immutable append-only change log."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import AuditAction
from app.domain.models.base import Base
from app.domain.models.pg_enums import pg_audit_action


class AuditLog(Base):
    """Immutable audit trail — no PK mixin needed, has its own UUID PK.

    No timestamps mixin: only changed_at matters; no updated_at
    (records are never updated). No soft-delete (records are never deleted).
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index(
            "ix_audit_log_entity_type_entity_id_changed_at",
            "entity_type",
            "entity_id",
            "changed_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[AuditAction] = mapped_column(pg_audit_action, nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
