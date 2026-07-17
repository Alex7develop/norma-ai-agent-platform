"""Application logging configuration."""

import logging
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    """Configure consistent process-wide logs for local and container runs."""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"handlers": ["default"], "level": level.upper()},
        }
    )
    logging.captureWarnings(True)
