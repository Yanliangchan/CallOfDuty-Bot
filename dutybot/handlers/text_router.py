"""Routes free-text messages to whichever admin workflow is awaiting input.

Several admin conversations (personnel add/rename/remarks, /add_duty paste)
need a plain text reply rather than a button press. Telegram's handler
model only lets one :class:`~telegram.ext.MessageHandler` claim a given
text update, so this module centralises the dispatch based on a
``chat_data["awaiting"]`` marker set by the initiating command/callback.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from config import settings
from handlers.add_duty import handle_pasted_duty
from handlers.personnel import personnel_text_input
from utils.decorators import log_errors

_PERSONNEL_STATES = {"add_name", "rename", "remarks"}
_ADD_DUTY_STATES = {"add_duty_paste"}


@log_errors
async def route_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatch a text message to the handler matching the current admin workflow."""
    user = update.effective_user
    if user is None or not settings.is_admin(user.id) or context.chat_data is None:
        return

    awaiting = context.chat_data.get("awaiting")
    if awaiting in _PERSONNEL_STATES:
        await personnel_text_input(update, context)
    elif awaiting in _ADD_DUTY_STATES:
        await handle_pasted_duty(update, context)
