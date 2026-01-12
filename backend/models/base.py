"""
Base SQLAlchemy model with common fields and functionality.

This module provides the foundation for all database models in the application,
including UUID primary keys, timestamps, and common query methods.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped


class Base(DeclarativeBase):
    """
    Base class for all database models.

    Provides common fields and methods for all models.
    """

    id: Mapped[str]
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower()

    # Common fields
    id: Mapped[str] = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        """String representation of the model instance."""
        return f"<{self.__class__.__name__}(id={self.id})>"
