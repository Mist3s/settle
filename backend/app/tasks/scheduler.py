"""APScheduler configuration — background task scheduler.

Runs within the FastAPI process via lifespan.
Architecture §7.5: APScheduler in the same process, acceptable for single user.
"""

from __future__ import annotations

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.tasks.jobs.accrue_interest import run_accrue_interest
from app.tasks.jobs.refresh_status import run_refresh_planned_status

log = structlog.get_logger()

# Singleton scheduler instance
_scheduler: AsyncIOScheduler | None = None


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler with all jobs."""
    scheduler = AsyncIOScheduler()

    # accrue_interest — daily at 03:00 MSK (UTC+3 → 00:00 UTC)
    scheduler.add_job(
        run_accrue_interest,
        CronTrigger(hour=0, minute=0, timezone="Europe/Moscow"),
        id="accrue_interest",
        name="Daily interest accrual",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # refresh_planned_status — daily at 00:30 MSK
    scheduler.add_job(
        run_refresh_planned_status,
        CronTrigger(hour=0, minute=30, timezone="Europe/Moscow"),
        id="refresh_planned_status",
        name="Refresh overdue planned payments",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    return scheduler


async def start_scheduler() -> None:
    """Start the background scheduler."""
    global _scheduler
    _scheduler = create_scheduler()
    _scheduler.start()
    log.info("scheduler_started", jobs=len(_scheduler.get_jobs()))


async def stop_scheduler() -> None:
    """Gracefully stop the scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")
        _scheduler = None
