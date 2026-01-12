"""
Ingestion log model for tracking data ingestion activities.

This module defines the IngestionLog model to track all ingestion
operations, including successes, failures, and performance metrics.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped

from .base import Base


class IngestionStatus(str, Enum):
    """Enumeration of ingestion operation statuses."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"
    CANCELLED = "cancelled"


class IngestionType(str, Enum):
    """Enumeration of ingestion operation types."""

    NEWS_FETCH = "news_fetch"
    STOCK_DATA = "stock_data"
    FILE_UPLOAD = "file_upload"
    WEB_SCRAPE = "web_scrape"
    MANUAL_ENTRY = "manual_entry"
    BATCH_PROCESS = "batch_process"


class IngestionLog(Base):
    """
    Ingestion log model for tracking data ingestion activities.

    Records all ingestion operations with detailed information about
    success/failure, performance metrics, and error details.
    """

    __tablename__ = "ingestion_logs"

    # Operation identification
    operation_id: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)
    ingestion_type: Mapped[IngestionType] = Column(String(20), nullable=False, index=True)

    # Status and timing
    status: Mapped[IngestionStatus] = Column(String(20), nullable=False, index=True)
    started_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))

    # Source information
    data_source_id: Mapped[Optional[str]] = Column(String(255), index=True)
    user_id: Mapped[Optional[str]] = Column(UUID(as_uuid=True), index=True)  # Who initiated the ingestion

    # Metrics
    records_processed: Mapped[int] = Column(Integer, default=0, nullable=False)
    records_successful: Mapped[int] = Column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = Column(Integer, default=0, nullable=False)

    # Performance metrics
    duration_seconds: Mapped[Optional[float]] = Column(Float)
    throughput_per_second: Mapped[Optional[float]] = Column(Float)

    # Error information
    error_message: Mapped[Optional[str]] = Column(Text)
    error_details: Mapped[Optional[Dict]] = Column(JSON)

    # Configuration and parameters used
    parameters: Mapped[Dict] = Column(JSON, default=dict, nullable=False)

    # Additional context
    notes: Mapped[Optional[str]] = Column(Text)

    @property
    def is_successful(self) -> bool:
        """Check if ingestion was successful."""
        return self.status == IngestionStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        """Check if ingestion failed."""
        return self.status == IngestionStatus.FAILURE

    @property
    def success_rate(self) -> float:
        """Calculate success rate of processed records."""
        total = self.records_processed
        if total == 0:
            return 0.0
        return (self.records_successful / total) * 100

    @property
    def duration(self) -> Optional[float]:
        """Get the duration of the ingestion operation."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def mark_completed(self, status: IngestionStatus = IngestionStatus.SUCCESS) -> None:
        """Mark the ingestion as completed."""
        self.status = status
        self.completed_at = datetime.utcnow()
        self.duration_seconds = self.duration

        if self.duration_seconds and self.duration_seconds > 0:
            self.throughput_per_second = self.records_processed / self.duration_seconds

    def record_error(self, message: str, details: Optional[Dict] = None) -> None:
        """Record an error during ingestion."""
        self.status = IngestionStatus.FAILURE
        self.error_message = message
        if details:
            self.error_details = details

    def update_metrics(self, processed: int = 0, successful: int = 0, failed: int = 0) -> None:
        """Update processing metrics."""
        self.records_processed += processed
        self.records_successful += successful
        self.records_failed += failed

    def __str__(self) -> str:
        """String representation of the ingestion log."""
        return f"IngestionLog(operation_id={self.operation_id}, type={self.ingestion_type}, status={self.status})"
