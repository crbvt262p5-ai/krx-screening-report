from __future__ import annotations

import logging
from datetime import datetime

from .config import Settings


def setup_logging(settings: Settings) -> logging.Logger:
    settings.ensure_directories()
    logger = logging.getLogger("krx_screening")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )

    date_str = datetime.now(settings.timezone).strftime("%Y-%m-%d")
    log_path = settings.logs_dir / f"krx_screening_{date_str}.log"

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
