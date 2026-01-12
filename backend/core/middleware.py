"""
Middleware for error handling, logging, and request processing.

This module provides FastAPI middleware for centralized error handling,
request logging, CORS, and other cross-cutting concerns.
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from core.config import settings
from core.exceptions import AppException

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    Logs request details, response status, and timing information
    for monitoring and debugging purposes.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request start
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.url.query),
                "user_agent": request.headers.get("user-agent", ""),
                "client_ip": self._get_client_ip(request),
            }
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log successful response
            logger.info(
                f"Request completed: {request.method} {request.url.path} -> {response.status_code}",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.4f}s",
                    "response_size": response.headers.get("content-length", "0"),
                }
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate processing time for failed requests
            process_time = time.time() - start_time

            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path} -> {type(e).__name__}",
                extra={
                    "request_id": request_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "process_time": f"{process_time:.4f}s",
                },
                exc_info=True
            )

            # Re-raise to let error handler middleware catch it
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (common in proxy setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        return request.client.host if request.client else "unknown"


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized error handling.

    Catches exceptions and converts them to appropriate HTTP responses
    with consistent error formatting.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)

        except AppException as e:
            # Handle custom application exceptions
            return self._handle_app_exception(request, e)

        except Exception as e:
            # Handle unexpected exceptions
            return self._handle_unexpected_exception(request, e)

    def _handle_app_exception(self, request: Request, exc: AppException) -> JSONResponse:
        """Handle custom application exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")

        # Log the error
        logger.warning(
            f"Application error: {exc.error_code} - {exc.message}",
            extra={
                "request_id": request_id,
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
            }
        )

        # Return structured error response
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                }
            }
        )

    def _handle_unexpected_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")

        # Log the error with full traceback
        logger.error(
            f"Unexpected error: {type(exc).__name__} - {str(exc)}",
            extra={
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True
        )

        # DEBUG: Print error to stdout for immediate visibility
        print(f"DEBUG ERROR: {type(exc).__name__}: {str(exc)}")
        import traceback
        traceback.print_exc()

        # Return generic error response (don't expose internal details)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                }
            }
        )


def create_cors_middleware():
    """
    Get CORS middleware settings.

    Returns:
        dict: CORS middleware configuration
    """
    return {
        "allow_origins": settings.cors_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            "Accept",
            "Origin",
            "User-Agent",
            "X-Request-ID",
        ],
        "expose_headers": ["X-Request-ID"],
        "max_age": 86400,  # 24 hours
    }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to responses.

    Adds various security headers to help protect against common web vulnerabilities.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Add HSTS header for HTTPS (only in production)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Basic rate limiting middleware.

    Provides simple IP-based rate limiting for API endpoints.
    In production, consider using more sophisticated solutions like Redis.
    """

    def __init__(self, app: Callable, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # Simple in-memory storage (not suitable for production)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean old entries (simple cleanup)
        cutoff_time = current_time - 60
        self.requests = {
            ip: times for ip, times in self.requests.items()
            if any(t > cutoff_time for t in times)
        }

        # Check rate limit
        if client_ip in self.requests:
            # Remove old requests
            self.requests[client_ip] = [
                t for t in self.requests[client_ip] if t > cutoff_time
            ]

            if len(self.requests[client_ip]) >= self.requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests",
                            "retry_after": 60,
                        }
                    },
                    headers={"Retry-After": "60"}
                )

            self.requests[client_ip].append(current_time)
        else:
            self.requests[client_ip] = [current_time]

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"
