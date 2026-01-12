"""
Custom exception classes for the application.

This module defines custom exceptions for different types of errors
that can occur in the application, providing better error handling
and user-friendly error messages.
"""


class AppException(Exception):
    """
    Base exception class for all application-specific errors.
    """

    def __init__(self, message: str = "An error occurred"):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
        """
        super().__init__(message)
        self.message = message


class NotFoundException(AppException):
    """Exception raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)


class PermissionDeniedException(AppException):
    """Exception raised for authorization-related errors."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message)


class ValidationException(AppException):
    """Exception raised for input validation errors."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message)


class ExternalAPIException(AppException):
    """Exception raised when external API calls fail."""

    def __init__(self, message: str = "External API error"):
        super().__init__(message)
