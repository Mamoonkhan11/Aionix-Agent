"""
Database models for the Aionix Agent Backend.

This module contains all SQLAlchemy models used in the application,
providing the data layer for users, data sources, documents, and ingestion logs.
"""

from .base import Base
from .data_source import DataSource, DataSourceStatus, DataSourceType
from .ingestion_log import IngestionLog, IngestionStatus, IngestionType
from .raw_document import RawDocument, DocumentSourceType
from .user import User, UserRole

__all__ = [
    # Base model
    "Base",

    # User models
    "User",
    "UserRole",

    # Data source models
    "DataSource",
    "DataSourceType",
    "DataSourceStatus",

    # Document models
    "RawDocument",
    "DocumentSourceType",

    # Ingestion models
    "IngestionLog",
    "IngestionStatus",
    "IngestionType",
]
