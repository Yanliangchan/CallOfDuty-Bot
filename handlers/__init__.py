"""Registers all Telegram handlers on the application."""

from __future__ import annotations

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from handlers.add_duty import add_duty_command, import_callback
from handlers.generate import generate_callback, generate_command, publish_command
from handlers.personnel import personnel_command, personnel_menu_callback
from handlers.see_duty import see_duty_command
from handlers.see_past import see_past_callback, see_past_command
from handlers.start import help_command, start_command
from handlers.stats import stats_command
from handlers.text_router import route_text_input


def register_handlers(application: Application) -> None:
    """Attach every command, callback, and message handler to ``application``."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("see_duty", see_duty_command))
    application.add_handler(CommandHandler("see_past", see_past_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("personnel", personnel_command))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CommandHandler("publish", publish_command))
    application.add_handler(CommandHandler("add_duty", add_duty_command))

    application.add_handler(CallbackQueryHandler(see_past_callback, pattern=r"^seepast:"))
    application.add_handler(CallbackQueryHandler(generate_callback, pattern=r"^gen:"))
    application.add_handler(CallbackQueryHandler(personnel_menu_callback, pattern=r"^pers:"))
    application.add_handler(CallbackQueryHandler(import_callback, pattern=r"^import:"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text_input))
