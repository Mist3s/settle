"""Loan ORM model."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import LoanStatus, LoanType, PaymentMethod, PrepaymentStrategy
from app.domain.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.domain.models.pg_enums import (
    pg_loan_status,
    pg_loan_type,
    pg_payment_method,
    pg_prepayment_strategy,
)


class Loan(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "loans"
    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_loans_user_id_code"),
        Index("ix_loans_user_id_status", "user_id", "status"),
        CheckConstraint("interest_rate >= 0", name="positive_interest_rate"),
        CheckConstraint(
            "closing_date >= opening_date OR closing_date IS NULL OR opening_date IS NULL",
            name="closing_after_opening",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    creditor: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    loan_type: Mapped[LoanType] = mapped_column(pg_loan_type, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(pg_payment_method, nullable=False)
    original_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), nullable=False, server_default="0"
    )
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    prepayment_strategy: Mapped[PrepaymentStrategy] = mapped_column(
        pg_prepayment_strategy,
        nullable=False,
        server_default="reduce_payment",
    )
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[LoanStatus] = mapped_column(
        pg_loan_status, nullable=False, server_default="active"
    )
    contract_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ADR-003: late_fee_rate nullable, placeholder for future penalty calculation
    late_fee_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    # months_remaining for schedule generation
    months_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # payment_day: day of month for scheduled payments
    payment_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="loans")  # noqa: F821
    balances: Mapped[list["LoanBalance"]] = relationship(  # noqa: F821
        back_populates="loan", lazy="selectin"
    )
    planned_payments: Mapped[list["PlannedPayment"]] = relationship(  # noqa: F821
        back_populates="loan", lazy="selectin"
    )
    actual_payments: Mapped[list["ActualPayment"]] = relationship(  # noqa: F821
        back_populates="loan", lazy="selectin"
    )
