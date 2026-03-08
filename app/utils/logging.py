"""
app/utils/logging.py
─────────────────────
Structured JSON logging using structlog.
Every log entry includes: timestamp, level, service, request_id (when available).
In production: JSON output for log aggregators (Datadog, CloudWatch).
In development: pretty-printed colored output.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.config import settings


def add_service_context(
    logger: Any, method: str, event_dict: EventDict
) -> EventDict:
    """Inject static service metadata into every log entry."""
    event_dict["service"] = "crypto-ops-platform"
    event_dict["env"] = settings.app_env
    return event_dict


def drop_color_message_key(
    logger: Any, method: str, event_dict: EventDict
) -> EventDict:
    """Remove uvicorn's color_message to keep logs clean."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for the application.
    Call once at application startup.
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_service_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        drop_color_message_key,
    ]

    if settings.is_production:
        # JSON output for log aggregation
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty colored output for local dev
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(settings.log_level),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a bound logger with a component name."""
    return structlog.get_logger(name)
