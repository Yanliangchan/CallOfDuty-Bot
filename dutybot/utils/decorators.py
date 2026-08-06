"""Reusable decorators for Telegram command handlers."""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from config import settings

logger = logging.getLogger(__name__)

HandlerFunc = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, object]]


def admin_only(func: HandlerFunc) -> HandlerFunc:
    """Reject the update unless it comes from a configured admin user."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> object:
        user = update.effective_user
        if user is None or not settings.is_admin(user.id):
            message = update.effective_message
            if message is not None:
                await message.reply_text("This command is restricted to administrators.")
            logger.warning(
                "Unauthorized access attempt by user_id=%s to %s",
                user.id if user else "unknown",
                func.__name__,
            )
            return None
        return await func(update, context)

    return wrapper


def log_errors(func: HandlerFunc) -> HandlerFunc:
    """Log unhandled exceptions raised by a handler without crashing the bot."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> object:
        try:
            return await func(update, context)
        except Exception:
            logger.exception("Unhandled error in handler %s", func.__name__)
            message = update.effective_message
            if message is not None:
                await message.reply_text(
                    "Something went wrong while processing that command. The error has been logged."
                )
            return None

    return wrapper
