"""Handlers for /see_past: browse historical duty rosters via inline buttons."""

from __future__ import annotations

from telegram import Message, Update
from telegram.ext import ContextTypes

from database.unit_of_work import UnitOfWork
from handlers.common import build_week_picker
from services.duty_service import DutyService
from utils.decorators import log_errors
from utils.message_utils import schedule_auto_delete

_duty_service = DutyService()
_CALLBACK_PREFIX = "seepast"


@log_errors
async def see_past_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show an inline keyboard listing every recorded week."""
    message = update.effective_message
    if message is None:
        return

    async with UnitOfWork() as uow:
        weeks = await uow.weeks.list_all()

    if not weeks:
        reply = await message.reply_text("No past duty records found.")
        schedule_auto_delete(context, reply)
        return

    keyboard = build_week_picker([w.week_number for w in weeks], prefix=_CALLBACK_PREFIX)
    reply = await message.reply_text("Select a week to view:", reply_markup=keyboard)
    schedule_auto_delete(context, reply)


@log_errors
async def see_past_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render the roster for the week selected from the /see_past keyboard."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()

    week_number = int(query.data.split(":")[1])
    async with UnitOfWork() as uow:
        text = await _duty_service.render_week(uow, week_number)

    if text is None:
        await query.edit_message_text("That week could no longer be found.")
        return

    result = await query.edit_message_text(text)
    if isinstance(result, Message):
        schedule_auto_delete(context, result)
