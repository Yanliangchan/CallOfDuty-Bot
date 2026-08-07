"""Handlers for /generate and /publish: creating and publishing draft rosters."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database.unit_of_work import UnitOfWork
from services.duty_service import DutyService, DutyServiceError
from utils.decorators import admin_only, log_errors

_duty_service = DutyService()


def _preview_keyboard(week_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Publish", callback_data=f"gen:publish:{week_number}"),
                InlineKeyboardButton("Regenerate", callback_data=f"gen:regenerate:{week_number}"),
            ],
            [InlineKeyboardButton("Cancel", callback_data=f"gen:cancel:{week_number}")],
        ]
    )


@log_errors
@admin_only
async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a draft roster for the next week and show a preview."""
    message = update.effective_message
    if message is None:
        return

    async with UnitOfWork() as uow:
        latest = await uow.weeks.get_latest()
        target_week_number = latest.week_number if latest is not None and not latest.published else None
        try:
            week = await _duty_service.generate_week(uow, week_number=target_week_number)
        except DutyServiceError as exc:
            await message.reply_text(str(exc))
            return
        text = await _duty_service.render_week(uow, week.week_number)

    await message.reply_text(
        text or "Generated, but rendering failed.", reply_markup=_preview_keyboard(week.week_number)
    )


@log_errors
@admin_only
async def publish_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Publish the most recently generated draft week immediately."""
    message = update.effective_message
    if message is None:
        return

    async with UnitOfWork() as uow:
        week = await uow.weeks.get_latest()
        if week is None:
            await message.reply_text("No draft roster exists. Use /generate first.")
            return
        try:
            await _duty_service.publish_week(uow, week.week_number, context.bot)
        except DutyServiceError as exc:
            await message.reply_text(str(exc))
            return

    await message.reply_text(f"Week {week.week_number} published to the group.")


@log_errors
@admin_only
async def generate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Publish/Regenerate/Cancel button presses from /generate previews."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()

    _, action, week_number_raw = query.data.split(":")
    week_number = int(week_number_raw)

    async with UnitOfWork() as uow:
        if action == "publish":
            try:
                await _duty_service.publish_week(uow, week_number, context.bot)
            except DutyServiceError as exc:
                await query.edit_message_text(str(exc))
                return
            await query.edit_message_text(f"Week {week_number} published to the group.")
        elif action == "regenerate":
            try:
                week = await _duty_service.generate_week(uow, week_number=week_number)
                text = await _duty_service.render_week(uow, week.week_number)
            except DutyServiceError as exc:
                await query.edit_message_text(str(exc))
                return
            await query.edit_message_text(
                text or "Regenerated, but rendering failed.", reply_markup=_preview_keyboard(week_number)
            )
        elif action == "cancel":
            try:
                await _duty_service.cancel_draft(uow, week_number)
            except DutyServiceError as exc:
                await query.edit_message_text(str(exc))
                return
            await query.edit_message_text(f"Draft for week {week_number} cancelled.")
