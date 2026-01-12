"""
Data source model for tracking ingestion sources.

This module defines the DataSource model to track different types of
data sources (API, file upload, etc.) and their configuration.
"""

from enum import Enum
from typing import Dict, Optional

from sqlalchemy import Column, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, relationship

from .base import Base


class DataSourceType(str, Enum):
    """Enumeration of supported data source types."""

    NEWS_API = "news_api"
    ALPHA_VANTAGE = "alpha_vantage"
    FILE_UPLOAD = "file_upload"
    WEB_SCRAPER = "web_scraper"
    MANUAL_ENTRY = "manual_entry"


class DataSourceStatus(str, Enum):
    """Enumeration of data source statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DataSource(Base):
    """
    Data source model for tracking ingestion sources.

    Tracks configuration and status of various data ingestion sources.
    """

    __tablename__ = "data_sources"

    # Basic information
    name: Mapped[str] = Column(String(255), nullable=False, index=True)
    type: Mapped[DataSourceType] = Column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = Column(Text)

    # Status and configuration
    status: Mapped[DataSourceStatus] = Column(
        String(20),
        default=DataSourceStatus.ACTIVE,
        nullable=False
    )

    # Configuration as JSON (API keys, endpoints, parameters, etc.)
    config: Mapped[Dict] = Column(JSON, default=dict, nullable=False)

    # Metadata
    source_url: Mapped[Optional[str]] = Column(String(500))
    api_version: Mapped[Optional[str]] = Column(String(20))
    rate_limit: Mapped[Optional[int]] = Column(Integer)  # requests per hour

    # Usage tracking
    total_ingestions: Mapped[int] = Column(Integer, default=0, nullable=False)
    successful_ingestions: Mapped[int] = Column(Integer, default=0, nullable=False)
    failed_ingestions: Mapped[int] = Column(Integer, default=0, nullable=False)

    # Error tracking
    last_error: Mapped[Optional[str]] = Column(Text)
    last_successful_ingestion: Mapped[Optional[str]] = Column(String(255))

    @property
    def success_rate(self) -> float:
        """Calculate success rate of ingestions."""
        total = self.total_ingestions
        if total == 0:
            return 0.0
        return (self.successful_ingestions / total) * 100

    @property
    def error_rate(self) -> float:
        """Calculate error rate of ingestions."""
        total = self.total_ingestions
        if total == 0:
            return 0.0
        return (self.failed_ingestions / total) * 100

    def record_ingestion_success(self) -> None:
        """Record a successful ingestion."""
        self.total_ingestions += 1
        self.successful_ingestions += 1

    def record_ingestion_failure(self, error_message: str) -> None:
        """Record a failed ingestion."""
        self.total_ingestions += 1
        self.failed_ingestions += 1
        self.last_error = error_message

    def update_config(self, new_config: Dict) -> None:
        """Update data source configuration."""
        self.config.update(new_config)

    # Relationships
    documents = relationship("RawDocument", back_populates="data_source")

    def __str__(self) -> str:
        """String representation of the data source."""
        return f"DataSource(name={self.name}, type={self.type}, status={self.status})"
