"""
Structured logging configuration.

Uses structlog with:
- ConsoleRenderer in dev (TTY detected)
- JSONRenderer in production (Docker, CI)
- Request ID binding for traceability
"""

import sys
import uuid

import structlog


def setup_logging() -> None:
    """Configure structlog processors. Call once at app startup."""
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if sys.stderr.isatty():
        processors = [*shared_processors, structlog.dev.ConsoleRenderer()]
    else:
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def generate_request_id() -> str:
    return str(uuid.uuid4())[:8]


def get_logger(**kwargs) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(**kwargs)
