"""The automatic weekly duty generation-and-publish job.

Runs every Sunday at 20:00 in the configured timezone: generates a fair
roster for the upcoming week, saves it, publishes it to the configured
Telegram group/topic, pins the message, and logs the outcome.
"""

from __future__ import annotations

import logging

from telegram import Bot

from database.unit_of_work import UnitOfWork
from services.duty_service import DutyService, DutyServiceError

logger = logging.getLogger(__name__)

_duty_service = DutyService()


async def run_weekly_publish_job(bot: Bot) -> None:
    """Generate and publish the next week's duty roster.

    Never raises: all errors are logged so a single failure cannot crash the
    scheduler or take down the bot process.
    """
    logger.info("Starting scheduled weekly duty generation and publish job")
    try:
        async with UnitOfWork() as uow:
            latest = await uow.weeks.get_latest()
            week_number = latest.week_number if latest is not None and not latest.published else None
            week = await _duty_service.generate_week(uow, week_number=week_number)
            logger.info("Weekly job generated draft for week %s", week.week_number)

        async with UnitOfWork() as uow:
            await _duty_service.publish_week(uow, week.week_number, bot)
        logger.info("Weekly job successfully published week %s", week.week_number)
    except DutyServiceError:
        logger.exception("Weekly duty job failed with a service error")
    except Exception:
        logger.exception("Weekly duty job failed with an unexpected error")
