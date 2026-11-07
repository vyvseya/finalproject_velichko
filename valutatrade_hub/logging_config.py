import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def configure_logging() -> logging.Logger:
    """Настраивает логирование операций платформы"""
    logger = logging.getLogger("valutatrade_hub.actions")

    if logger.handlers:
        return logger

    settings = SettingsLoader()

    log_path = Path(settings.get("log_file", "logs/actions.log"))

    if not log_path.is_absolute():
        log_path = Path(__file__).resolve().parents[1] / log_path

    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        fmt="%(levelname)s %(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    formatter.converter = time.gmtime

    handler.setFormatter(formatter)

    log_level = settings.get("log_level", "INFO")
    logger.setLevel(getattr(logging, str(log_level).upper(), logging.INFO))

    logger.addHandler(handler)
    logger.propagate = False

    return logger
