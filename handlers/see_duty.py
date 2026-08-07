"""Handler for /see_duty: shows the current and next week's roster."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from database.unit_of_work import UnitOfWork
from services.duty_service import DutyService
from utils.decorators import log_errors
from utils.message_utils import schedule_auto_delete

_duty_service = DutyService()


@log_errors
async def see_duty_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the current week's duty, and next week's if already generated."""
    message = update.effective_message
    if message is None:
        return

    async with UnitOfWork() as uow:
        latest_published = await uow.weeks.get_latest_published()
        latest_any = await uow.weeks.get_latest()

        texts: list[str] = []
        if latest_published is not None:
            text = await _duty_service.render_week(uow, latest_published.week_number)
            if text:
                texts.append(text)
        else:
            texts.append("No published duty roster yet.")

        if (
            latest_any is not None
            and (latest_published is None or latest_any.week_number > latest_published.week_number)
        ):
            next_text = await _duty_service.render_week(uow, latest_any.week_number)
            if next_text:
                texts.append(next_text)

    reply = await message.reply_text("\n\n---\n\n".join(texts))
    schedule_auto_delete(context, reply)
    schedule_auto_delete(context, message)
