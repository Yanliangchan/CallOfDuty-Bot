"""DutyBot entrypoint: builds and runs the Telegram application."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes

from config import settings
from database.session import dispose_engine, init_engine
from handlers import register_handlers
from scheduler import build_scheduler
from utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


async def _on_startup(application: Application) -> None:
    """Start the background scheduler once the application is running."""
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

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
