"""Application configuration loaded from environment variables.

All runtime configuration is centralised here so the rest of the codebase
never touches ``os.environ`` directly. Import :data:`settings` to access
validated configuration values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _parse_admin_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.add(int(chunk))
        except ValueError as exc:
            raise ConfigError(f"Invalid admin id in ADMIN_IDS: {chunk!r}") from exc
    return frozenset(ids)


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable, validated application settings."""

    bot_token: str
    database_url: str
    admin_ids: frozenset[int]
    group_chat_id: int
    group_topic_id: int | None
    timezone: str = "Asia/Singapore"
    auto_delete_seconds: int = 300
    log_level: str = "INFO"
    log_file: str = "dutybot.log"

    def is_admin(self, user_id: int) -> bool:
        """Return ``True`` if ``user_id`` is a configured administrator."""
        return user_id in self.admin_ids

    @staticmethod
    def load() -> "Settings":
        """Build settings from the current process environment."""
        bot_token = _require("BOT_TOKEN")
        database_url = _require("DATABASE_URL")
        admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
        group_chat_id = int(_require("GROUP_CHAT_ID"))
        topic_raw = os.getenv("GROUP_TOPIC_ID", "").strip()
        group_topic_id = int(topic_raw) if topic_raw else None
        timezone = os.getenv("TIMEZONE", "Asia/Singapore")
        auto_delete_seconds = int(os.getenv("AUTO_DELETE_SECONDS", "300"))
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_file = os.getenv("LOG_FILE", "dutybot.log")
        return Settings(
            bot_token=bot_token,
            database_url=database_url,
            admin_ids=admin_ids,
            group_chat_id=group_chat_id,
            group_topic_id=group_topic_id,
            timezone=timezone,
            auto_delete_seconds=auto_delete_seconds,
            log_level=log_level,
            log_file=log_file,
        )


settings: Settings = Settings.load()
