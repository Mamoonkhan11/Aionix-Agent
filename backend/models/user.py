"""
User model for authentication and authorization.

This module defines the User model with fields for authentication,
role-based access control, and user management.
"""

from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import Mapped

from .base import Base


class UserRole(str, Enum):
    """User role enumeration for role-based access control."""

    ADMIN = "admin"
    STAKEHOLDER = "stakeholder"
    USER = "user"


class User(Base):
    """
    User model for the application.

    Handles user authentication, authorization, and profile information.
    """

    __tablename__ = "users"

    # Authentication fields
    email: Mapped[str] = Column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = Column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = Column(String(255), nullable=False)

    # Profile fields
    first_name: Mapped[Optional[str]] = Column(String(100))
    last_name: Mapped[Optional[str]] = Column(String(100))
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = Column(Boolean, default=False, nullable=False)

    # Authorization
    role: Mapped[UserRole] = Column(
        String(20),
        default=UserRole.USER,
        nullable=False
    )

    # Additional metadata
    last_login: Mapped[Optional[str]] = Column(String(255))
    login_attempts: Mapped[str] = Column(String(10), default="0", nullable=False)

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN

    @property
    def is_stakeholder(self) -> bool:
        """Check if user has stakeholder role."""
        return self.role in [UserRole.ADMIN, UserRole.STAKEHOLDER]

    def increment_login_attempts(self) -> None:
        """Increment login attempts counter."""
        try:
            current_attempts = int(self.login_attempts or "0")
            self.login_attempts = str(current_attempts + 1)
        except (ValueError, TypeError):
            self.login_attempts = "1"

    def reset_login_attempts(self) -> None:
        """Reset login attempts counter."""
        self.login_attempts = "0"

    def __str__(self) -> str:
        """String representation of the user."""
        return f"User(email={self.email}, role={self.role})"
