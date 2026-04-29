"""PlannedPayment and ActualPayment ORM models."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ActualPaymentType, PaymentAccuracy, PaymentStatus
from app.domain.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.domain.models.pg_enums import (
    pg_actual_payment_type,
    pg_payment_accuracy,
    pg_payment_status,
)


class PlannedPayment(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "planned_payments"
    __table_args__ = (
        Index("ix_planned_payments_user_id_due_date", "user_id", "due_date"),
        Index("ix_planned_payments_loan_id_due_date", "loan_id", "due_date"),
        Index("ix_planned_payments_income_id", "income_id"),
        CheckConstraint("amount > 0", name="positive_amount"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    income_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incomes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    principal_part: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    interest_part: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        pg_payment_status, nullable=False, server_default="pending"
    )
    accuracy: Mapped[PaymentAccuracy] = mapped_column(
        pg_payment_accuracy, nullable=False, server_default="estimate"
    )
    can_pay_early: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    loan: Mapped["Loan"] = relationship(back_populates="planned_payments")  # noqa: F821
    income: Mapped["Income | None"] = relationship(back_populates="planned_payments")  # noqa: F821
    actual_payment: Mapped["ActualPayment | None"] = relationship(
        back_populates="planned_payment", uselist=False, lazy="selectin"
    )


class ActualPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Recorded actual payment — no soft-delete, cancellation creates a compensating entry."""

    __tablename__ = "actual_payments"
    __table_args__ = (
        Index("ix_actual_payments_loan_id_payment_date", "loan_id", "payment_date"),
    )

    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    planned_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planned_payments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    principal_part: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    interest_part: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_type: Mapped[ActualPaymentType] = mapped_column(
        pg_actual_payment_type, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    loan: Mapped["Loan"] = relationship(back_populates="actual_payments")  # noqa: F821
    planned_payment: Mapped["PlannedPayment | None"] = relationship(
        back_populates="actual_payment"
    )
