"""APScheduler wiring for DutyBot's recurring jobs."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from jobs.weekly_publish import run_weekly_publish_job

logger = logging.getLogger(__name__)


def build_scheduler(bot: Bot, timezone: str) -> AsyncIOScheduler:
    """Build an :class:`AsyncIOScheduler` with the weekly publish job registered.

    The job fires every Sunday at 20:00 in ``timezone``. The scheduler is
    returned unstarted; call ``.start()`` once the bot's event loop is
    running.
    """
    scheduler = AsyncIOScheduler(timezone=timezone)
    scheduler.add_job(
        run_weekly_publish_job,
        trigger=CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=timezone),
        args=[bot],
        id="weekly_duty_publish",
        name="Weekly duty generation and publish",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Scheduled weekly duty publish job for Sundays 20:00 %s", timezone)
    return scheduler
