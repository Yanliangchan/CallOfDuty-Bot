"""Application-wide logging configuration.

Call :func:`configure_logging` once at startup. All modules should then use
``logging.getLogger(__name__)`` as usual.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler


def configure_logging(*, level: str = "INFO", log_file: str = "dutybot.log") -> None:
    """Configure console and rotating file handlers for the root logger."""
    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    # Quiet noisy third-party loggers.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
