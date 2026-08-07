"""Handlers for /start and /help."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from config import settings
from handlers.common import build_main_menu
from utils.decorators import log_errors

_WELCOME = (
    "Welcome to DutyBot!\n\n"
    "I manage weekly military duty assignments: I keep historical records, "
    "generate fair rosters automatically, and publish them to the group every "
    "Sunday at 8:00 PM.\n\n"
    "You can message me here privately too — everything except publishing "
    "works the same in a DM. Use the menu below or /help to see commands."
)

_HELP_USER = (
    "Available commands:\n\n"
    "/see_duty - Show this week's and next week's duty roster\n"
    "/see_past - Browse past weeks' duty rosters\n"
    "/stats - Show duty statistics for everyone\n"
    "/help - Show this message"
)

_HELP_ADMIN_EXTRA = (
    "\n\nAdmin commands:\n\n"
    "/personnel - Manage personnel (add/edit/remove/phone/stats)\n"
    "/generate - Generate next week's draft roster\n"
    "/publish - Publish the latest generated draft\n"
    "/add_duty - Import a historical duty roster by pasting text"
)


@log_errors
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start: greet the user and show the persistent main menu."""
    message = update.effective_message
    user = update.effective_user
    if message is None:
        return
    is_admin = user is not None and settings.is_admin(user.id)
    await message.reply_text(_WELCOME, reply_markup=build_main_menu(is_admin=is_admin))


@log_errors
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    message = update.effective_message
    if message is None:
        return
    user = update.effective_user
    is_admin = user is not None and settings.is_admin(user.id)
    text = _HELP_USER
    if is_admin:
        text += _HELP_ADMIN_EXTRA
    await message.reply_text(text, reply_markup=build_main_menu(is_admin=is_admin))
