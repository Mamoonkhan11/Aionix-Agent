"""
Data normalization service.

This module provides a centralized service for normalizing all ingested data
into a unified internal schema, regardless of the original source format.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from models import RawDocument

logger = logging.getLogger(__name__)


class DataNormalizationService:
    """
    Service for normalizing ingested data into unified internal schema.

    This service provides methods to standardize data from various sources
    (APIs, file uploads, etc.) into a consistent internal format.
    """

    def __init__(self):
        """Initialize the normalization service."""
        pass

    def normalize_document(
        self,
        source_type: str,
        raw_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """
        Normalize raw data into a standardized document format.

        Args:
            source_type: Type of data source (news_api, alpha_vantage, upload, etc.)
            raw_data: Raw data from the source
            metadata: Additional metadata

        Returns:
            RawDocument: Normalized document ready for storage
        """
        if source_type == "news_api":
            return self._normalize_news_api_data(raw_data, metadata)
        elif source_type == "alpha_vantage":
            return self._normalize_alpha_vantage_data(raw_data, metadata)
        elif source_type == "upload":
            return self._normalize_upload_data(raw_data, metadata)
        else:
            return self._normalize_generic_data(raw_data, metadata)

    def _normalize_news_api_data(
        self,
        raw_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """
        Normalize NewsAPI article data.

        Args:
            raw_data: NewsAPI article data
            metadata: Additional metadata

        Returns:
            RawDocument: Normalized document
        """
        # Extract core information
        title = raw_data.get("title", "Untitled News Article")
        description = raw_data.get("description", "")
        content = raw_data.get("content", "")

        # Combine content intelligently
        full_content = self._combine_text_content([description, content])

        # Build comprehensive metadata
        doc_metadata = {
            "source": "news_api",
            "source_type": "api",
            "external_id": raw_data.get("url"),
            "author": raw_data.get("author"),
            "published_at": raw_data.get("publishedAt"),
            "source_name": raw_data.get("source", {}).get("name"),
            "url": raw_data.get("url"),
            "url_to_image": raw_data.get("urlToImage"),
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "content_type": "news_article",
            "language": "en",  # NewsAPI primarily returns English
        }

        # Add any additional metadata
        if metadata:
            doc_metadata.update(metadata)

        return RawDocument(
            title=title,
            content=full_content,
            source_type="api",
            metadata=doc_metadata,
        )

    def _normalize_alpha_vantage_data(
        self,
        raw_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """
        Normalize Alpha Vantage financial data.

        Args:
            raw_data: Alpha Vantage API response
            metadata: Additional metadata

        Returns:
            RawDocument: Normalized document
        """
        # Determine data type from the response
        if "Global Quote" in raw_data:
            return self._normalize_stock_quote(raw_data, metadata)
        elif any(key.startswith("Time Series") for key in raw_data.keys()):
            return self._normalize_time_series(raw_data, metadata)
        else:
            return self._normalize_fundamental_data(raw_data, metadata)

    def _normalize_stock_quote(
        self,
        raw_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """Normalize stock quote data."""
        quote = raw_data.get("Global Quote", {})
        symbol = quote.get("01. symbol", "UNKNOWN")

        content_parts = [
            f"Stock Quote for {symbol}",
            "",
            f"Symbol: {quote.get('01. symbol', 'N/A')}",
            f"Open: {quote.get('02. open', 'N/A')}",
            f"High: {quote.get('03. high', 'N/A')}",
            f"Low: {quote.get('04. low', 'N/A')}",
            f"Price: {quote.get('05. price', 'N/A')}",
            f"Volume: {quote.get('06. volume', 'N/A')}",
            f"Latest Trading Day: {quote.get('07. latest trading day', 'N/A')}",
            f"Previous Close: {quote.get('08. previous close', 'N/A')}",
            f"Change: {quote.get('09. change', 'N/A')}",
            f"Change Percent: {quote.get('10. change percent', 'N/A')}",
        ]

        content = "\n".join(content_parts)

        doc_metadata = {
            "source": "alpha_vantage",
            "source_type": "api",
            "data_type": "stock_quote",
            "symbol": symbol,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "content_type": "financial_data",
        }

        if metadata:
            doc_metadata.update(metadata)

        return RawDocument(
            title=f"Stock Quote: {symbol}",
            content=content,
            source_type="api",
            metadata=doc_metadata,
        )

    def _normalize_time_series(
        self,
        raw_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """Normalize time series data."""
        # Find the time series key
        time_series_key = None
        for key in raw_data.keys():
            if "Time Series" in key:
                time_series_key = key
                break

        if not time_series_key:
            raise ValueError("No time series data found")

        time_series = raw_data[time_series_key]
        symbol = raw_data.get("Meta Data", {}).get("2. Symbol", "UNKNOWN")

        # Create readable content
        content_parts = [
            f"Financial Time Series Data for {symbol}",
            f"Data Type: {time_series_key}",
            "",
        ]

        # Add latest entries (limit to prevent huge documents)
        dates = list(time_series.keys())[:20]  # Latest 20 entries

        for date in dates:
            content_parts.append(f"Date: {date}")
            values = time_series[date]
            for key, value in values.items():
                content_parts.append(f"  {key}: {value}")
            content_parts.append("")

        content = "\n".join(content_parts)

        doc_metadata = {
            "source": "alpha_vantage",
            "source_type": "api",
            "data_type": "time_series",
            "symbol": symbol,
            "time_series_type": time_series_key,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "content_type": "financial_data",
            "data_points": len(time_series),
        }

        if metadata:
            doc_metadata.update(metadata)

        return RawDocument(
            title=f"Financial Data: {symbol} - {time_series_key.replace('Time Series ', '')}",
            content=content,
            source_type="api",
            metadata=doc_metadata,
        )

    def _normalize_fundamental_data(
        self,
        raw_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """Normalize fundamental financial data."""
        symbol = raw_data.get("Symbol", "UNKNOWN")

        # Create readable content from key-value pairs
        content_parts = [
            f"Fundamental Financial Data for {symbol}",
            "",
        ]

        for key, value in raw_data.items():
            if value and str(value).strip():
                content_parts.append(f"{key}: {value}")

        content = "\n".join(content_parts)

        doc_metadata = {
            "source": "alpha_vantage",
            "source_type": "api",
            "data_type": "fundamental",
            "symbol": symbol,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "content_type": "financial_data",
        }

        if metadata:
            doc_metadata.update(metadata)

        return RawDocument(
            title=f"Financial Fundamentals: {symbol}",
            content=content,
            source_type="api",
            metadata=doc_metadata,
        )

    def _normalize_upload_data(
        self,
        raw_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """
        Normalize uploaded file data.

        Args:
            raw_data: Upload data
            metadata: Additional metadata

        Returns:
            RawDocument: Normalized document
        """
        title = raw_data.get("title", "Uploaded Document")
        content = raw_data.get("content", "")

        doc_metadata = {
            "source": "upload",
            "source_type": "upload",
            "original_filename": raw_data.get("filename"),
            "content_type": raw_data.get("content_type"),
            "file_size": raw_data.get("file_size"),
            "uploaded_by": raw_data.get("uploaded_by"),
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "content_type": "document",
        }

        if metadata:
            doc_metadata.update(metadata)

        return RawDocument(
            title=title,
            content=content,
            source_type="upload",
            metadata=doc_metadata,
        )

    def _normalize_generic_data(
        self,
        raw_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """
        Normalize generic data into document format.

        Args:
            raw_data: Generic data
            metadata: Additional metadata

        Returns:
            RawDocument: Normalized document
        """
        # Try to extract title and content
        title = raw_data.get("title", raw_data.get("name", "Untitled Document"))
        content = raw_data.get("content", raw_data.get("description", ""))

        # If content is still empty, create content from all fields
        if not content:
            content_parts = []
            for key, value in raw_data.items():
                if isinstance(value, (str, int, float)) and value:
                    content_parts.append(f"{key}: {value}")
            content = "\n".join(content_parts)

        doc_metadata = {
            "source": "generic",
            "source_type": "unknown",
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "content_type": "generic",
        }

        if metadata:
            doc_metadata.update(metadata)

        return RawDocument(
            title=title,
            content=content,
            source_type="manual",
            metadata=doc_metadata,
        )

    def _combine_text_content(self, text_parts: list) -> str:
        """
        Intelligently combine multiple text parts.

        Args:
            text_parts: List of text parts to combine

        Returns:
            str: Combined text
        """
        combined = []
        seen_content = set()

        for part in text_parts:
            if part and part.strip():
                # Remove duplicate content
                part_clean = part.strip()
                if part_clean not in seen_content:
                    combined.append(part_clean)
                    seen_content.add(part_clean)

        return "\n\n".join(combined)

    def validate_normalized_document(self, document: RawDocument) -> bool:
        """
        Validate that a normalized document meets requirements.

        Args:
            document: Document to validate

        Returns:
            bool: True if valid
        """
        # Check required fields
        if not document.title or not document.title.strip():
            return False

        if not document.content or not document.content.strip():
            return False

        # Check minimum content length
        if len(document.content.strip()) < 10:
            return False

        # Check metadata structure
        if not document.metadata:
            return False

        required_metadata = ["source", "ingestion_timestamp"]
        for field in required_metadata:
            if field not in document.metadata:
                return False

        return True

    def enrich_document_metadata(self, document: RawDocument) -> None:
        """
        Enrich document with additional computed metadata.

        Args:
            document: Document to enrich
        """
        if not document.metadata:
            document.metadata = {}

        # Add content statistics
        content = document.content or ""
        document.metadata["word_count"] = len(content.split())
        document.metadata["character_count"] = len(content)

        # Add processing timestamp
        document.metadata["processed_at"] = datetime.utcnow().isoformat()

        # Add content quality indicators
        document.metadata["has_title"] = bool(document.title and document.title.strip())
        document.metadata["has_content"] = bool(content.strip())
        document.metadata["content_length_category"] = self._categorize_content_length(len(content))

    def _categorize_content_length(self, length: int) -> str:
        """
        Categorize content by length.

        Args:
            length: Content length in characters

        Returns:
            str: Length category
        """
        if length < 100:
            return "very_short"
        elif length < 500:
            return "short"
        elif length < 2000:
            return "medium"
        elif length < 10000:
            return "long"
        else:
            return "very_long"
