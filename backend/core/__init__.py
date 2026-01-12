"""
Core module for the Aionix Agent Backend.

This module provides core functionality including configuration,
security, middleware, logging, and exception handling.
"""

from .config import settings
from .exceptions import (
    AppException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
    ExternalAPIException,
)
from .logging_config import RequestLogger, configure_logging, get_logger
from .middleware import (
    ErrorHandlingMiddleware,
    RateLimitingMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    create_cors_middleware,
)
from .security import authenticate_user, create_access_token, get_current_user, get_password_hash, verify_password

__all__ = [
    # Configuration
    "settings",

    # Exceptions
    "AppException",
    "NotFoundException",
    "PermissionDeniedException",
    "ValidationException",
    "ExternalAPIException",

    # Logging
    "RequestLogger",
    "configure_logging",
    "get_logger",

    # Middleware
    "ErrorHandlingMiddleware",
    "RateLimitingMiddleware",
    "RequestLoggingMiddleware",
    "SecurityHeadersMiddleware",
    "create_cors_middleware",

    # Security
    "authenticate_user",
    "create_access_token",
    "get_current_user",
    "get_password_hash",
    "verify_password",
]
