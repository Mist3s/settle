"""LoanBalance repository."""

import uuid

from sqlalchemy import select

from app.domain.models.balance import LoanBalance
from app.repositories.base import Repository


class BalanceRepository(Repository[LoanBalance]):
    model = LoanBalance

    async def get_latest(self, loan_id: uuid.UUID) -> LoanBalance | None:
        """Get the most recent balance snapshot for a loan."""
        stmt = (
            select(LoanBalance)
            .where(LoanBalance.loan_id == loan_id)
            .order_by(LoanBalance.snapshot_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
