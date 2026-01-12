"""
Pydantic schemas for document operations.

This module defines request/response schemas for document creation,
updating, and retrieval operations.
"""

from datetime import datetime
from typing import Dict, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class DocumentBase(BaseModel):
    """Base document schema with common fields."""

    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    content: str = Field(..., description="Document content")
    source_type: str = Field(..., description="Type of document source (api, upload, scraper, manual)")


class DocumentCreate(DocumentBase):
    """Schema for creating new documents."""

    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class DocumentUpdate(BaseModel):
    """Schema for updating existing documents."""

    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Document title")
    content: Optional[str] = Field(None, description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    processed: Optional[bool] = Field(None, description="Whether document has been processed")


class DocumentInDBBase(DocumentBase):
    """Base schema for document data from database."""

    id: UUID = Field(..., description="Document unique identifier")
    source_id: Optional[str] = Field(None, description="Data source identifier")
    external_id: Optional[str] = Field(None, description="External system identifier")
    source_url: Optional[str] = Field(None, description="Source URL")
    processed: bool = Field(False, description="Whether document has been processed")
    processing_attempts: int = Field(0, description="Number of processing attempts")
    word_count: Optional[int] = Field(None, description="Word count")
    language: Optional[str] = Field(None, description="Document language")
    summary: Optional[str] = Field(None, description="Document summary")
    content_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Content quality score")
    duplicate_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Duplicate detection score")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class Document(DocumentInDBBase):
    """Schema for complete document information."""

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")


class DocumentPublic(DocumentInDBBase):
    """Schema for public document information (excludes sensitive data)."""

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")


class DocumentSummary(BaseModel):
    """Schema for document summary information."""

    id: UUID = Field(..., description="Document unique identifier")
    title: str = Field(..., description="Document title")
    source_type: str = Field(..., description="Type of document source")
    processed: bool = Field(..., description="Whether document has been processed")
    created_at: datetime = Field(..., description="Creation timestamp")
    word_count: Optional[int] = Field(None, description="Word count")


class DocumentSearch(BaseModel):
    """Schema for document search parameters."""

    query: Optional[str] = Field(None, description="Search query")
    source_type: Optional[str] = Field(None, description="Filter by source type")
    processed: Optional[bool] = Field(None, description="Filter by processing status")
    date_from: Optional[datetime] = Field(None, description="Filter documents from this date")
    date_to: Optional[datetime] = Field(None, description="Filter documents until this date")
    limit: int = Field(50, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class DocumentIngestionRequest(BaseModel):
    """Schema for document ingestion requests."""

    source_type: str = Field(..., description="Type of data source")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Ingestion parameters")


class NewsIngestionRequest(DocumentIngestionRequest):
    """Schema for news API ingestion requests."""

    source_type: str = Field("news_api", description="Data source type")
    query: str = Field(..., description="Search query for news articles")
    max_articles: Optional[int] = Field(50, ge=1, le=100, description="Maximum articles to fetch")


class FinancialIngestionRequest(DocumentIngestionRequest):
    """Schema for financial data ingestion requests."""

    source_type: str = Field("alpha_vantage", description="Data source type")
    symbol: str = Field(..., description="Stock symbol")
    function: str = Field("TIME_SERIES_DAILY", description="Alpha Vantage function")
    interval: Optional[str] = Field("1min", description="Data interval")


class IngestionResponse(BaseModel):
    """Schema for ingestion operation responses."""

    operation_id: str = Field(..., description="Unique operation identifier")
    status: str = Field(..., description="Ingestion status")
    message: str = Field(..., description="Status message")
    records_processed: int = Field(0, description="Number of records processed")
    records_successful: int = Field(0, description="Number of successful records")
    records_failed: int = Field(0, description="Number of failed records")
    duration_seconds: Optional[float] = Field(None, description="Operation duration")


class DocumentProcessingRequest(BaseModel):
    """Schema for document processing requests."""

    document_ids: list[UUID] = Field(..., description="List of document IDs to process")
    force_reprocess: bool = Field(False, description="Whether to reprocess already processed documents")
