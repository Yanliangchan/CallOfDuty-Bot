"""Helpers for sending self-deleting Telegram messages."""

from __future__ import annotations

import logging

from telegram import Message
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from config import settings

logger = logging.getLogger(__name__)


def schedule_auto_delete(
    context: ContextTypes.DEFAULT_TYPE,
    message: Message,
    *,
    delay_seconds: int | None = None,
) -> None:
    """Schedule ``message`` for deletion after ``delay_seconds``.

    Uses the bot's :class:`~telegram.ext.JobQueue` so the deletion survives
    independently of the handler's own lifecycle. Deletion failures (e.g. the
    message was already removed) are logged and swallowed.
    """
    delay = delay_seconds if delay_seconds is not None else settings.auto_delete_seconds
    job_queue = context.job_queue
    if job_queue is None:
        logger.warning("JobQueue unavailable; cannot schedule auto-delete for message %s", message.message_id)
        return
    job_queue.run_once(
        _delete_message_job,
        when=delay,
        data={"chat_id": message.chat_id, "message_id": message.message_id},
        name=f"auto_delete_{message.chat_id}_{message.message_id}",
    )


async def _delete_message_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    assert job is not None
    data = job.data
    assert isinstance(data, dict)
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
    except TelegramError as exc:
        logger.debug("Could not auto-delete message %s: %s", data["message_id"], exc)
