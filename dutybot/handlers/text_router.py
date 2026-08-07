"""Routes free-text messages: main-menu button taps and admin workflow input.

Two kinds of plain-text messages need routing here rather than through a
dedicated :class:`~telegram.ext.CommandHandler`:

* Taps on the persistent main-menu reply keyboard (see
  :func:`handlers.common.build_main_menu`), which Telegram delivers as an
  ordinary text message matching the button's label.
* Free-text replies for admin conversations (personnel add/rename/remarks,
  /add_duty paste) that are awaiting input, tracked via a
  ``chat_data["awaiting"]`` marker set by the initiating command/callback.

Telegram's handler model only lets one :class:`~telegram.ext.MessageHandler`
claim a given text update, so this module centralises the dispatch.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes

from config import settings
from handlers.add_duty import add_duty_command, handle_pasted_duty
from handlers.common import MAIN_MENU_LABELS
from handlers.generate import generate_command, publish_command
from handlers.personnel import personnel_command, personnel_text_input
from handlers.see_duty import see_duty_command
from handlers.see_past import see_past_command
from handlers.start import help_command
from handlers.stats import stats_command
from utils.decorators import log_errors

_PERSONNEL_STATES = {"add_name", "rename", "remarks"}
_ADD_DUTY_STATES = {"add_duty_paste"}

MenuHandler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[object]]

_MENU_HANDLERS: dict[str, MenuHandler] = {
    MAIN_MENU_LABELS["see_duty"]: see_duty_command,
    MAIN_MENU_LABELS["see_past"]: see_past_command,
    MAIN_MENU_LABELS["stats"]: stats_command,
    MAIN_MENU_LABELS["help"]: help_command,
    MAIN_MENU_LABELS["personnel"]: personnel_command,
    MAIN_MENU_LABELS["generate"]: generate_command,
    MAIN_MENU_LABELS["publish"]: publish_command,
    MAIN_MENU_LABELS["add_duty"]: add_duty_command,
}


@log_errors
async def route_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatch a text message to a main-menu button or an awaited admin reply."""
    message = update.effective_message
    if message is None or message.text is None:
        return

    menu_handler = _MENU_HANDLERS.get(message.text.strip())
    if menu_handler is not None:
        if context.chat_data is not None:
            context.chat_data.pop("awaiting", None)
            context.chat_data.pop("edit_person_id", None)
        await menu_handler(update, context)
        return

    user = update.effective_user
    if user is None or not settings.is_admin(user.id) or context.chat_data is None:
        return

    awaiting = context.chat_data.get("awaiting")
    if awaiting in _PERSONNEL_STATES:
        await personnel_text_input(update, context)
    elif awaiting in _ADD_DUTY_STATES:
        await handle_pasted_duty(update, context)
