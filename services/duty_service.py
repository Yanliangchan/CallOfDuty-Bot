"""Orchestrates duty roster generation, publishing, and retrieval."""

from __future__ import annotations

import logging
from datetime import date

from telegram import Bot
from telegram.error import TelegramError

from config import settings
from database.unit_of_work import UnitOfWorkProtocol
from models.duty_assignment import DutyAssignment
from models.week import Week
from services.scheduling_service import SchedulingService
from utils.formatting import render_week_roster

logger = logging.getLogger(__name__)


class DutyServiceError(Exception):
    """Raised for user-facing duty-service failures."""


class DutyService:
    """Business logic for generating, publishing, and viewing weekly duties."""

    def __init__(self, scheduler: SchedulingService | None = None) -> None:
        self._scheduler = scheduler or SchedulingService()

    async def generate_week(self, uow: UnitOfWorkProtocol, *, week_number: int | None = None) -> Week:
        """Generate (or regenerate) a draft roster for the given/next week.

        If a draft (unpublished) week with this number already exists, its
        assignments are cleared and regenerated. Published weeks are never
        overwritten.
        """
        if week_number is None:
            week_number = await uow.weeks.next_week_number()

        existing = await uow.weeks.get_by_number(week_number)
        if existing is not None and existing.published:
            raise DutyServiceError(f"Week {week_number} has already been published and cannot be regenerated.")

        people = await uow.personnel.list_all(active_only=True)
        if not people:
            raise DutyServiceError("No active personnel available to generate a schedule.")

        contexts = await self._scheduler.build_contexts(uow, people)
        roster = self._scheduler.generate_assignments(contexts, week_number)

        if existing is not None:
            await uow.assignments.delete_for_week(existing.id)
            week = existing
        else:
            week = await uow.weeks.add(week_number, date.today(), published=False)

        assignments = [
            DutyAssignment(week_id=week.id, category=category, meal=category.meal, person_id=person.id)
            for category, people_list in roster.items()
            for person in people_list
        ]
        await uow.assignments.bulk_add(assignments)
        logger.info("Generated draft schedule for week %s (%d assignments)", week_number, len(assignments))
        return week

    async def cancel_draft(self, uow: UnitOfWorkProtocol, week_number: int) -> None:
        """Delete a draft (unpublished) week entirely."""
        week = await uow.weeks.get_by_number(week_number)
        if week is None:
            raise DutyServiceError(f"Week {week_number} does not exist.")
        if week.published:
            raise DutyServiceError(f"Week {week_number} is already published and cannot be cancelled.")
        await uow.weeks.delete(week)
        logger.info("Cancelled draft schedule for week %s", week_number)

    async def render_week(self, uow: UnitOfWorkProtocol, week_number: int) -> str | None:
        """Render the roster text for a given week number, or ``None`` if absent."""
        week = await uow.weeks.get_by_number(week_number, with_assignments=True)
        if week is None:
            return None
        return render_week_roster(week.week_number, week.assignments)

    async def render_week_by_id(self, uow: UnitOfWorkProtocol, week_id: int) -> str | None:
        """Render the roster text for a given week id, or ``None`` if absent."""
        week = await uow.weeks.get_by_id(week_id, with_assignments=True)
        if week is None:
            return None
        return render_week_roster(week.week_number, week.assignments)

    async def publish_week(self, uow: UnitOfWorkProtocol, week_number: int, bot: Bot) -> str:
        """Publish a draft week's roster to the configured group/topic.

        Returns the rendered text that was sent. Marks the week as published
        only after the Telegram send succeeds.
        """
        week = await uow.weeks.get_by_number(week_number, with_assignments=True)
        if week is None:
            raise DutyServiceError(f"Week {week_number} does not exist. Generate it first.")
        if week.published:
            raise DutyServiceError(f"Week {week_number} has already been published.")

        text = render_week_roster(week.week_number, week.assignments)
        try:
            message = await bot.send_message(
                chat_id=settings.group_chat_id,
                message_thread_id=settings.group_topic_id,
                text=text,
            )
        except TelegramError:
            logger.exception("Failed to publish week %s to Telegram", week_number)
            raise DutyServiceError("Failed to send the roster to Telegram. See logs for details.") from None

        await uow.weeks.mark_published(week)
        logger.info("Published week %s to chat=%s topic=%s", week_number, settings.group_chat_id, settings.group_topic_id)

        try:
            await message.pin(disable_notification=True)
        except TelegramError as exc:
            logger.warning("Could not pin published message for week %s: %s", week_number, exc)

        return text
