"""
Logging configuration for the application.

This module provides centralized logging configuration using structlog
for structured logging with JSON output and proper formatting.
"""

import logging
import sys
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

from core.config import settings


def configure_logging() -> None:
    """
    Configure application logging with structured output.

    Sets up logging with JSON formatting for production and
    human-readable formatting for development.
    """
    # Remove existing handlers to avoid duplication
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Create formatter based on environment
    if settings.log_format == "json" or settings.is_production:
        formatter = _create_json_formatter()
    else:
        formatter = _create_human_formatter()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Add handler to root logger
    root_logger.addHandler(console_handler)

    # Configure structlog if available
    if STRUCTLOG_AVAILABLE:
        _configure_structlog()

    # Set levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Log configuration completion
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": settings.log_level,
            "log_format": settings.log_format,
            "environment": settings.environment,
        }
    )


def _create_json_formatter() -> jsonlogger.JsonFormatter:
    """Create JSON formatter for structured logging."""
    return jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _create_human_formatter() -> logging.Formatter:
    """Create human-readable formatter for development."""
    return logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _configure_structlog() -> None:
    """Configure structlog for structured logging."""
    import structlog

    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_request_id,
        structlog.processors.JSONRenderer(),
    ]

    if not settings.is_production:
        # Add human-readable output for development
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            _add_request_id,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(log_level_from_string(settings.log_level)),
        cache_logger_on_first_use=True,
    )


def _add_request_id(logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add request ID to log events if available.

    This processor adds the request ID from context variables to log entries.
    """
    try:
        import contextvars
        request_id_var = contextvars.ContextVar("request_id")
        request_id = request_id_var.get(None)
        if request_id:
            event_dict["request_id"] = request_id
    except (LookupError, ImportError):
        pass

    return event_dict


def log_level_from_string(level_str: str) -> int:
    """
    Convert log level string to numeric value.

    Args:
        level_str: Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        int: Numeric log level
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "FATAL": logging.CRITICAL,
    }
    return level_map.get(level_str.upper(), logging.INFO)


class RequestLogger:
    """
    Context manager for logging request-specific information.

    Provides a way to add request-specific context to all log messages
    within a request scope.
    """

    def __init__(self, request_id: str, user_id: str = None, **extra_context):
        """
        Initialize request logger.

        Args:
            request_id: Unique request identifier
            user_id: User ID if authenticated
            extra_context: Additional context to include in logs
        """
        self.request_id = request_id
        self.user_id = user_id
        self.extra_context = extra_context
        self.context_vars = {}

    def __enter__(self):
        """Set up logging context for the request."""
        try:
            import contextvars

            # Create context variables
            request_id_var = contextvars.ContextVar("request_id")
            user_id_var = contextvars.ContextVar("user_id")

            # Set context
            self.context_vars["request_id"] = request_id_var.set(self.request_id)
            if self.user_id:
                self.context_vars["user_id"] = user_id_var.set(self.user_id)

            # Set additional context
            for key, value in self.extra_context.items():
                var = contextvars.ContextVar(key)
                self.context_vars[key] = var.set(value)

        except ImportError:
            # Fallback for environments without contextvars
            pass

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up logging context."""
        try:
            import contextvars

            # Reset context variables
            for var_token in self.context_vars.values():
                var_token.var.reset(var_token)

        except ImportError:
            pass


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger: Configured logger instance
    """
    if STRUCTLOG_AVAILABLE:
        import structlog
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


# Initialize logging on import
configure_logging()
