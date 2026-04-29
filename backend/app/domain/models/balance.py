"""LoanBalance ORM model — point-in-time balance snapshots."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import BalanceSource
from app.domain.models.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.domain.models.pg_enums import pg_balance_source


class LoanBalance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Snapshot of a loan balance on a specific date.

    No soft-delete: balance history is append-only.
    Corrections go through audit_log (old snapshot updated, previous state recorded).
    """

    __tablename__ = "loan_balances"
    __table_args__ = (
        UniqueConstraint(
            "loan_id", "snapshot_date", name="uq_loan_balances_loan_id_snapshot_date"
        ),
        CheckConstraint("principal_balance >= 0", name="non_negative_principal"),
        CheckConstraint("accrued_interest >= 0", name="non_negative_interest"),
    )

    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    principal_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    accrued_interest: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    source: Mapped[BalanceSource] = mapped_column(
        pg_balance_source, nullable=False, server_default="imported"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    loan: Mapped["Loan"] = relationship(back_populates="balances")  # noqa: F821
