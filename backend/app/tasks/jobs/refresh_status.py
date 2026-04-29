"""Job: refresh_planned_status — mark overdue planned payments.

Architecture §7.5: transfers planned_payments with due_date < today
and status == 'pending' to 'overdue'.

Runs daily at 00:30 MSK.
"""

from __future__ import annotations

from datetime import date

import structlog
from sqlalchemy import update

from app.core.database import async_session_factory
from app.domain.enums import PaymentStatus
from app.domain.models.payment import PlannedPayment

log = structlog.get_logger()


async def run_refresh_planned_status() -> None:
    """Move pending payments with past due dates to overdue status."""
    today = date.today()

    async with async_session_factory() as session, session.begin():
        # Find and update in one statement
        stmt = (
            update(PlannedPayment)
            .where(
                PlannedPayment.due_date < today,
                PlannedPayment.status == PaymentStatus.PENDING,
                PlannedPayment.is_deleted.is_(False),
            )
            .values(status=PaymentStatus.OVERDUE)
            .returning(PlannedPayment.id)
        )
        result = await session.execute(stmt)
        updated_ids = list(result.scalars().all())

        log.info(
            "refresh_planned_status_complete",
            date=str(today),
            updated_count=len(updated_ids),
        )
