"""
Raw document model for storing ingested content.

This module defines the RawDocument model to store all ingested data
in a normalized format, regardless of the original source.
"""

from enum import Enum
from typing import Dict, Optional

from sqlalchemy import Boolean, Column, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func

from .base import Base


class DocumentSourceType(str, Enum):
    """Enumeration of document source types."""

    API = "api"
    UPLOAD = "upload"
    SCRAPER = "scraper"
    MANUAL = "manual"


class RawDocument(Base):
    """
    Raw document model for storing ingested content.

    Stores all ingested data in a normalized internal schema,
    maintaining source information and metadata.
    """

    __tablename__ = "raw_documents"

    # Core document fields
    title: Mapped[str] = Column(String(500), nullable=False, index=True)
    content: Mapped[str] = Column(Text, nullable=False)
    source_type: Mapped[DocumentSourceType] = Column(String(20), nullable=False, index=True)

    # Source information
    source_id: Mapped[Optional[str]] = Column(String(255), index=True)  # Foreign key to data_sources
    external_id: Mapped[Optional[str]] = Column(String(255), index=True)  # ID from external source
    source_url: Mapped[Optional[str]] = Column(String(500))

    # Metadata as JSON (flexible schema for different document types)
    document_metadata: Mapped[Dict] = Column(JSON, default=dict, nullable=False)

    # Processing status
    processed: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    processing_attempts: Mapped[int] = Column(Integer, default=0, nullable=False)

    # Relationships
    data_source = relationship("DataSource", back_populates="documents")

    # Content analysis (populated during processing)
    word_count: Mapped[Optional[int]] = Column(Integer)
    language: Mapped[Optional[str]] = Column(String(10))
    summary: Mapped[Optional[str]] = Column(Text)

    # Quality metrics
    content_quality_score: Mapped[Optional[float]] = Column(Float)  # 0.0 to 1.0
    duplicate_score: Mapped[Optional[float]] = Column(Float)  # 0.0 to 1.0

    @property
    def is_api_source(self) -> bool:
        """Check if document came from an API."""
        return self.source_type == DocumentSourceType.API

    @property
    def is_upload_source(self) -> bool:
        """Check if document came from file upload."""
        return self.source_type == DocumentSourceType.UPLOAD

    @property
    def content_length(self) -> int:
        """Get the length of the content."""
        return len(self.content) if self.content else 0

    @property
    def has_metadata(self) -> bool:
        """Check if document has metadata."""
        return bool(self.document_metadata and len(self.document_metadata) > 0)

    def mark_as_processed(self) -> None:
        """Mark document as successfully processed."""
        self.processed = True

    def increment_processing_attempts(self) -> None:
        """Increment processing attempts counter."""
        self.processing_attempts += 1

    def update_metadata(self, new_metadata: Dict) -> None:
        """Update document metadata."""
        if not self.document_metadata:
            self.document_metadata = {}
        self.document_metadata.update(new_metadata)

    def get_metadata_value(self, key: str, default=None):
        """Get a specific metadata value."""
        return self.document_metadata.get(key, default) if self.document_metadata else default

    def __str__(self) -> str:
        """String representation of the document."""
        return f"RawDocument(title='{self.title[:50]}...', source_type={self.source_type}, processed={self.processed})"
