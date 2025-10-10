from __future__ import annotations

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db import SessionLocal
from app.services.dunning_service import generate_renewal_invoices
from app.settings import get_settings

log = structlog.get_logger(__name__)
_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler:
        return _scheduler

    settings = get_settings()
    sched = AsyncIOScheduler()
    every = settings.renewal_check_interval_seconds
    days_before = settings.renewal_days_before
    sched.add_job(
        lambda: _run_generate(days_before),
        trigger=IntervalTrigger(seconds=every),
        id="renewals",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    sched.start()
    _scheduler = sched
    log.info("scheduler_started", every_seconds=every, days_before=days_before)
    return sched


def _run_generate(days_before: int) -> None:
    with SessionLocal() as db:
        created = generate_renewal_invoices(db, days_before=days_before)
        if created:
            log.info("renewal_invoices_created", count=created)
