"""ProjectedState — in-memory snapshot of financial state for overlay.

Architecture §6.3: base projection loaded from DB once, then actions
mutate the copy in memory. No DB writes from this module.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class ProjectedPayment:
    """In-memory representation of a planned payment."""

    id: uuid.UUID | None  # None for synthetic (overlay-generated)
    loan_id: uuid.UUID
    loan_name: str
    due_date: date
    amount: Decimal
    principal_part: Decimal
    interest_part: Decimal
    status: str  # "pending", "skipped", "cancelled", etc.
    kind: str = "real"  # "real" or "synthetic"


@dataclass
class ProjectedIncome:
    """In-memory representation of an income event."""

    id: uuid.UUID | None
    expected_date: date
    amount: Decimal
    name: str
    kind: str = "real"


@dataclass
class ProjectedLoan:
    """In-memory loan with current balance for overlay calculations."""

    id: uuid.UUID
    name: str
    creditor: str
    principal_balance: Decimal
    accrued_interest: Decimal
    interest_rate: Decimal  # annual rate as percentage
    months_remaining: int | None
    payment_day: int | None
    prepayment_strategy: str  # "reduce_payment" | "shorten_term"
    status: str  # "active", "paid_off", etc.


@dataclass
class ProjectedState:
    """Full in-memory snapshot for overlay simulation.

    Created from DB data, then mutated by action handlers.
    Must be deepcopy-safe.
    """

    payments: list[ProjectedPayment] = field(default_factory=list)
    incomes: list[ProjectedIncome] = field(default_factory=list)
    loans: dict[uuid.UUID, ProjectedLoan] = field(default_factory=dict)

    def copy(self) -> ProjectedState:
        """Deep-copy for side-by-side comparison."""
        return deepcopy(self)

    def pending_payments(
        self,
        *,
        loan_id: uuid.UUID | None = None,
        after: date | None = None,
    ) -> list[ProjectedPayment]:
        """Filter payments that are still pending."""
        result = []
        for p in self.payments:
            if p.status != "pending":
                continue
            if loan_id is not None and p.loan_id != loan_id:
                continue
            if after is not None and p.due_date <= after:
                continue
            result.append(p)
        return result

    def add_synthetic_payment(
        self,
        *,
        loan_id: uuid.UUID,
        loan_name: str,
        due_date: date,
        amount: Decimal,
        principal_part: Decimal | None = None,
        interest_part: Decimal | None = None,
    ) -> None:
        """Add an overlay-generated payment to the projection."""
        self.payments.append(
            ProjectedPayment(
                id=None,
                loan_id=loan_id,
                loan_name=loan_name,
                due_date=due_date,
                amount=amount,
                principal_part=principal_part or amount,
                interest_part=interest_part or Decimal("0.00"),
                status="pending",
                kind="synthetic",
            )
        )

    def add_synthetic_income(
        self,
        *,
        expected_date: date,
        amount: Decimal,
        name: str,
    ) -> None:
        """Add an overlay-generated income to the projection."""
        self.incomes.append(
            ProjectedIncome(
                id=None,
                expected_date=expected_date,
                amount=amount,
                name=name,
                kind="synthetic",
            )
        )
