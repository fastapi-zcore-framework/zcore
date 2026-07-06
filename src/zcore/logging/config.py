"""ZCore Structured Logging Configuration.

This module initializes the application's logging pipeline. It integrates standard 
Python `logging` with `structlog` to provide structured, context-aware diagnostics. 
It dynamically formats output as developer-friendly, colorized text on interactive terminals 
or serialized JSON records on production stream targets.
"""

import logging
import sys
import structlog

LOG_LEVEL = "INFO"

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(message)s",
    stream=sys.stderr,
)

# Shared structlog processors executing transformation steps sequentially
shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.format_exc_info,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.stdlib.PositionalArgumentsFormatter(),
]

# Render interactive ANSI terminal streams locally, or serialized JSON in production
renderer = (
    structlog.dev.ConsoleRenderer()
    if sys.stderr.isatty()
    else structlog.processors.JSONRenderer()
)


def setup_logging() -> None:
    """Configure the global structlog logging engine.

    Applies the shared processor chain, hooks standard library logging factories 
    for consistency across external packages, resolves the appropriate rendering format 
    based on the terminal environment context, and caches loggers to reduce downstream 
    reflection overhead.
    """
    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, LOG_LEVEL)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )