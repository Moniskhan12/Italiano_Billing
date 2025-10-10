from __future__ import annotations

import logging
import sys
from typing import Any, Dict, cast

import structlog
from structlog.stdlib import BoundLogger


def configurate_logging() -> None:
    """JSON логирование."""

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            timestamper,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=logging.INFO)
    for noisy in ("unicorn", "uvicorn.error", "unicorn.access", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.INFO)


def get_logger(name: str) -> BoundLogger:
    return cast(BoundLogger, structlog.get_logger(name))


def log_event(
    logger: "structlog.BoundLogger", event: str, **kwargs: Dict[str, Any]
) -> None:
    logger.info(event, **kwargs)
