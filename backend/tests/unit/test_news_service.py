"""
Unit tests for NewsAPI service.

This module tests the NewsAPI service functionality including
article fetching, normalization, and error handling.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import settings
from models import DataSource, IngestionStatus
from schemas.documents import DocumentCreate
from services.news.news_service import NewsAPIService


class TestNewsAPIService:
    """Test cases for NewsAPI service."""

    @pytest.fixture
    def news_service(self):
        """Create a NewsAPI service instance for testing."""
        return NewsAPIService()

    @pytest.fixture
    def mock_data_source(self):
        """Create a mock data source."""
        return DataSource(
            id="test-ds-id",
            name="Test News Source",
            type="news_api",
            config={"api_key": "test_key"},
        )

    def test_initialization(self, news_service):
        """Test service initialization."""
        assert news_service.base_url == settings.news_api_base_url
        assert news_service.api_key == settings.news_api_key
        assert hasattr(news_service, 'rate_limiter')

    @pytest.mark.asyncio
    async def test_fetch_articles_success(self, news_service):
        """Test successful article fetching."""
        mock_response_data = {
            "status": "ok",
            "totalResults": 2,
            "articles": [
                {
                    "title": "Test Article 1",
                    "description": "Test description 1",
                    "content": "Test content 1",
                    "url": "https://example.com/1",
                    "publishedAt": "2024-01-01T12:00:00Z",
                    "source": {"name": "Test Source"}
                },
                {
                    "title": "Test Article 2",
                    "description": "Test description 2",
                    "content": "Test content 2",
                    "url": "https://example.com/2",
                    "publishedAt": "2024-01-02T12:00:00Z",
                    "source": {"name": "Test Source"}
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await news_service.fetch_articles("test query")

            assert result == mock_response_data
            assert len(result["articles"]) == 2

    @pytest.mark.asyncio
    async def test_fetch_articles_no_api_key(self, news_service):
        """Test article fetching without API key."""
        # Temporarily set api_key to empty
        original_key = news_service.api_key
        news_service.api_key = ""

        try:
            with pytest.raises(ValueError, match="NewsAPI key not configured"):
                await news_service.fetch_articles("test query")
        finally:
            news_service.api_key = original_key

    @pytest.mark.asyncio
    async def test_fetch_articles_api_error(self, news_service):
        """Test article fetching with API error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock(side_effect=Exception("API Error"))
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            with pytest.raises(Exception, match="API Error"):
                await news_service.fetch_articles("test query")

    def test_normalize_article_complete(self, news_service):
        """Test article normalization with complete data."""
        article = {
            "title": "Test Article",
            "description": "Test description",
            "content": "Test content",
            "url": "https://example.com/article",
            "publishedAt": "2024-01-01T12:00:00Z",
            "source": {"name": "Test Source"},
            "author": "Test Author",
            "urlToImage": "https://example.com/image.jpg"
        }

        result = news_service.normalize_article(article)

        assert isinstance(result, DocumentCreate)
        assert result.title == "Test Article"
        assert "Test description" in result.content
        assert "Test content" in result.content
        assert result.source_type == "api"
        assert result.metadata["source"] == "news_api"
        assert result.metadata["author"] == "Test Author"
        assert result.metadata["published_at"] == "2024-01-01T12:00:00Z"
        assert result.metadata["url"] == "https://example.com/article"

    def test_normalize_article_minimal(self, news_service):
        """Test article normalization with minimal data."""
        article = {
            "title": "Minimal Article",
            "url": "https://example.com/minimal"
        }

        result = news_service.normalize_article(article)

        assert result.title == "Minimal Article"
        assert result.content == ""  # No description or content
        assert result.source_type == "api"
        assert result.metadata["source"] == "news_api"
        assert result.metadata["url"] == "https://example.com/minimal"

    def test_normalize_article_missing_title(self, news_service):
        """Test article normalization with missing title."""
        article = {
            "description": "Article without title",
            "url": "https://example.com/no-title",
            "source": {"name": "Test Source"}
        }

        result = news_service.normalize_article(article)

        assert result.title == "News Article - Test Source"
        assert result.content == "Article without title"

    def test_normalize_article_removed_title(self, news_service):
        """Test article normalization with '[Removed]' title."""
        article = {
            "title": "[Removed]",
            "description": "Removed article",
            "source": {"name": "Test Source"}
        }

        result = news_service.normalize_article(article)

        assert result.title == "News Article - Test Source"

    @pytest.mark.asyncio
    async def test_ingest_articles_success(self, news_service, mock_data_source):
        """Test successful article ingestion."""
        mock_articles = [
            {
                "title": "Test Article 1",
                "description": "Description 1",
                "url": "https://example.com/1",
                "publishedAt": "2024-01-01T12:00:00Z",
                "source": {"name": "Test Source"}
            }
        ]

        with patch.object(news_service, 'fetch_articles', return_value={"articles": mock_articles}) as mock_fetch:
            # Mock database session
            mock_session = AsyncMock()
            mock_log_entry = MagicMock()
            mock_log_entry.operation_id = "test-op-id"
            mock_log_entry.status = IngestionStatus.SUCCESS

            # Mock the ingestion log creation and commit
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            # Mock data source recording
            mock_data_source.record_ingestion_success = MagicMock()

            log_entry = await news_service.ingest_articles(
                query="test query",
                data_source=mock_data_source,
                db_session=mock_session,
                max_articles=1
            )

            # Verify fetch_articles was called
            mock_fetch.assert_called_once_with(query="test query", page_size=1)

            # Verify database operations
            assert mock_session.add.call_count >= 2  # Log entry + document
            assert mock_session.commit.call_count >= 1
            assert mock_data_source.record_ingestion_success.called

    @pytest.mark.asyncio
    async def test_ingest_articles_fetch_failure(self, news_service, mock_data_source):
        """Test article ingestion with fetch failure."""
        with patch.object(news_service, 'fetch_articles', side_effect=Exception("Fetch failed")):
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()

            mock_data_source.record_ingestion_failure = MagicMock()

            log_entry = await news_service.ingest_articles(
                query="test query",
                data_source=mock_data_source,
                db_session=mock_session
            )

            # Verify error handling
            assert mock_data_source.record_ingestion_failure.called
            assert log_entry.status == IngestionStatus.FAILURE

    @pytest.mark.asyncio
    async def test_health_check_success(self, news_service):
        """Test successful health check."""
        with patch.object(news_service, 'fetch_articles', return_value={"articles": []}):
            result = await news_service.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, news_service):
        """Test failed health check."""
        with patch.object(news_service, 'fetch_articles', side_effect=Exception("API Error")):
            result = await news_service.health_check()
            assert result is False
