"""Job: accrue_interest — daily interest accrual for active loans.

Architecture §7.5: creates a balance snapshot with accumulated interest
for each active credit-type loan, giving an accurate balance on any day.

Runs daily at 03:00 MSK.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import structlog
from sqlalchemy import select

from app.core.database import async_session_factory
from app.domain.enums import BalanceSource, LoanStatus, LoanType
from app.domain.models.balance import LoanBalance
from app.domain.models.loan import Loan
from app.services import balance_service

log = structlog.get_logger()


async def run_accrue_interest() -> None:
    """For each active loan with interest_rate > 0, create today's balance snapshot.

    Daily interest = principal_balance x (annual_rate / 365).
    New accrued_interest = previous_accrued + daily_interest.
    """
    today = date.today()

    async with async_session_factory() as session, session.begin():
        # Fetch active loans with interest
        stmt = select(Loan).where(
            Loan.status == LoanStatus.ACTIVE,
            Loan.interest_rate > 0,
            Loan.is_deleted.is_(False),
            # Only credit/installment types accrue interest
            Loan.loan_type.in_([LoanType.CREDIT]),
        )
        result = await session.execute(stmt)
        loans = list(result.scalars().all())

        created = 0
        for loan in loans:
            # Get latest balance
            repo_stmt = (
                select(LoanBalance)
                .where(LoanBalance.loan_id == loan.id)
                .order_by(LoanBalance.snapshot_date.desc())
                .limit(1)
            )
            latest = (await session.execute(repo_stmt)).scalar_one_or_none()
            if latest is None:
                continue

            # Skip if already accrued today
            if latest.snapshot_date >= today:
                continue

            # Calculate daily interest
            daily_rate = loan.interest_rate / Decimal("36500")
            daily_interest = (latest.principal_balance * daily_rate).quantize(
                Decimal("0.01")
            )
            new_accrued = latest.accrued_interest + daily_interest

            await balance_service.create_snapshot(
                session,
                loan_id=loan.id,
                snapshot_date=today,
                principal_balance=latest.principal_balance,
                accrued_interest=new_accrued,
                source=BalanceSource.CALCULATED,
                notes="Daily interest accrual",
                changed_by=loan.user_id,
            )
            created += 1

        log.info(
            "accrue_interest_complete",
            date=str(today),
            loans_processed=len(loans),
            snapshots_created=created,
        )
