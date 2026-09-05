"""
AgentOS — Structured JSON logging.
All services get a consistent logger with trace_id/span_id injection.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger


def add_service_name(
    logger: WrappedLogger, method: str, event_dict: EventDict
) -> EventDict:
    """Inject service name from settings."""
    try:
        from shared.config import settings
        event_dict["service"] = settings.service_name
        event_dict["environment"] = settings.environment
    except Exception:
        pass
    return event_dict


def add_trace_context(
    logger: WrappedLogger, method: str, event_dict: EventDict
) -> EventDict:
    """Inject OpenTelemetry trace/span IDs if available."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
    except Exception:
        pass
    return event_dict


def configure_logging(
    service_name: str = "agentos",
    log_level: str = "INFO",
    json_output: bool = True,
) -> None:
    """Configure structlog for the process. Call once at startup."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Standard library root logger
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    # Suppress noisy third-party loggers
    for noisy in ("uvicorn.access", "aio_pika", "aiormq", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_service_name,
        add_trace_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Return a bound structlog logger for the given module name."""
    return structlog.get_logger(name)
