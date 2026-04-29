"""Scenario and ScenarioAction ORM models."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ScenarioActionType, ScenarioStatus
from app.domain.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.domain.models.pg_enums import pg_scenario_action_type, pg_scenario_status


class Scenario(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "scenarios"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ScenarioStatus] = mapped_column(
        pg_scenario_status, nullable=False, server_default="draft"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="scenarios")  # noqa: F821
    actions: Mapped[list["ScenarioAction"]] = relationship(
        back_populates="scenario",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ScenarioAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Individual action within a scenario — cascade-deleted with parent scenario."""

    __tablename__ = "scenario_actions"

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[ScenarioActionType] = mapped_column(
        pg_scenario_action_type, nullable=False
    )
    loan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="RESTRICT"),
        nullable=True,
    )
    income_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incomes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    planned_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planned_payments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    scenario: Mapped["Scenario"] = relationship(back_populates="actions")
    loan: Mapped["Loan | None"] = relationship()  # noqa: F821
