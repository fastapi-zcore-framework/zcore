import logging
import sys
import structlog

LOG_LEVEL = "INFO"

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(message)s",
    stream=sys.stderr,
)

shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.format_exc_info,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.stdlib.PositionalArgumentsFormatter(),
]

renderer = (
    structlog.dev.ConsoleRenderer()
    if sys.stderr.isatty()
    else structlog.processors.JSONRenderer()
)

def setup_logging():
    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, LOG_LEVEL)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
