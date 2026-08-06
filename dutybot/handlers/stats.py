"""Handler for /stats: shows duty statistics for all personnel."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from database.unit_of_work import UnitOfWork
from services.stats_service import StatsService, render_all_stats
from utils.decorators import log_errors
from utils.message_utils import schedule_auto_delete

_stats_service = StatsService()


@log_errors
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show statistics for every person."""
    message = update.effective_message
    if message is None:
        return

    async with UnitOfWork() as uow:
        all_stats = await _stats_service.stats_for_all(uow)

    text = render_all_stats(all_stats)
    # Telegram messages are capped at 4096 characters; split if necessary.
    for chunk_start in range(0, len(text), 4000):
        reply = await message.reply_text(text[chunk_start : chunk_start + 4000])
        schedule_auto_delete(context, reply)
