"""DutyBot entrypoint: builds and runs the Telegram application."""

from __future__ import annotations

import logging

from telegram import BotCommand, Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes

from config import settings
from database.session import dispose_engine, init_engine
from handlers import register_handlers
from scheduler import build_scheduler
from utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


async def _on_startup(application: Application) -> None:
    """Prepare Telegram state and start background services."""
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Welcome message and command list"),
            BotCommand("help", "Show command usage"),
            BotCommand("see_duty", "Show current and next week's duty"),
            BotCommand("see_past", "Browse past duty rosters"),
            BotCommand("stats", "Show duty statistics"),
            BotCommand("personnel", "Manage personnel (admin)"),
            BotCommand("generate", "Generate next week's roster (admin)"),
            BotCommand("publish", "Publish the generated roster (admin)"),
            BotCommand("add_duty", "Import a historical duty roster (admin)"),
        ]
    )
    bot_user = await application.bot.get_me()
    logger.info("Connected to Telegram as @%s (id=%s)", bot_user.username, bot_user.id)

    init_engine(settings.database_url)
    scheduler = build_scheduler(application.bot, settings.timezone)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("DutyBot startup complete")


async def _on_shutdown(application: Application) -> None:
    """Cleanly stop the scheduler and dispose of database connections."""
    scheduler = application.bot_data.get("scheduler")
    if scheduler is not None:
        scheduler.shutdown(wait=False)
    await dispose_engine()
    logger.info("DutyBot shutdown complete")


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler: log and never let the bot crash."""
    logger.error("Unhandled exception while processing update: %s", update, exc_info=context.error)


def main() -> None:
    """Build and run the DutyBot application until interrupted."""
    configure_logging(level=settings.log_level, log_file=settings.log_file)
    logger.info("Starting DutyBot")

    application = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .post_init(_on_startup)
        .post_shutdown(_on_shutdown)
        .build()
    )

    register_handlers(application)
    application.add_error_handler(_on_error)

    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
