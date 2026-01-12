"""
NewsAPI integration service.

This module provides functionality to fetch news articles from NewsAPI
and normalize them into the internal document format for ingestion.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.config import settings
from models import DataSource, IngestionLog, IngestionStatus, IngestionType, RawDocument, DocumentSourceType
from schemas.documents import DocumentCreate
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class NewsAPIService:
    """
    Service for fetching and processing news articles from NewsAPI.

    Provides methods to fetch latest articles by keyword, handle rate limiting,
    and normalize responses into internal document format.
    """

    def __init__(self):
        """Initialize NewsAPI service with configuration."""
        self.base_url = settings.news_api_base_url
        self.api_key = settings.news_api_key
        self.rate_limiter = RateLimiter(requests_per_hour=settings.news_api_rate_limit)

        # HTTP client configuration
        self.client_config = {
            "timeout": httpx.Timeout(30.0, connect=10.0),
            "headers": {
                "User-Agent": "Aionix-Agent-Backend/1.0",
                "Accept": "application/json",
            }
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def fetch_articles(
        self,
        query: str,
        page_size: int = 20,
        language: str = "en",
        sort_by: str = "publishedAt"
    ) -> Dict[str, Any]:
        """
        Fetch articles from NewsAPI.

        Args:
            query: Search query for articles
            page_size: Number of articles to fetch (max 100)
            language: Article language code
            sort_by: Sort order (publishedAt, relevancy, popularity)

        Returns:
            Dict: NewsAPI response

        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If API key is not configured
        """
        if not self.api_key:
            raise ValueError("NewsAPI key not configured")

        # Check rate limit
        await self.rate_limiter.wait_if_needed()

        params = {
            "q": query,
            "apiKey": self.api_key,
            "pageSize": min(page_size, 100),  # API limit
            "language": language,
            "sortBy": sort_by,
        }

        async with httpx.AsyncClient(**self.client_config) as client:
            response = await client.get(f"{self.base_url}/everything", params=params)
            response.raise_for_status()

            data = response.json()

            # Validate response structure
            if "articles" not in data:
                raise ValueError("Invalid NewsAPI response format")

            return data

    async def fetch_latest_headlines(
        self,
        country: str = "us",
        category: Optional[str] = None,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Fetch latest headlines from NewsAPI.

        Args:
            country: Country code (us, gb, etc.)
            category: News category (business, entertainment, etc.)
            page_size: Number of headlines to fetch

        Returns:
            Dict: NewsAPI response
        """
        if not self.api_key:
            raise ValueError("NewsAPI key not configured")

        # Check rate limit
        await self.rate_limiter.wait_if_needed()

        params = {
            "apiKey": self.api_key,
            "country": country,
            "pageSize": min(page_size, 100),
        }

        if category:
            params["category"] = category

        async with httpx.AsyncClient(**self.client_config) as client:
            response = await client.get(f"{self.base_url}/top-headlines", params=params)
            response.raise_for_status()

            data = response.json()

            if "articles" not in data:
                raise ValueError("Invalid NewsAPI response format")

            return data

    def normalize_article(self, article: Dict[str, Any]) -> DocumentCreate:
        """
        Normalize NewsAPI article to internal document format.

        Args:
            article: NewsAPI article data

        Returns:
            DocumentCreate: Normalized document data
        """
        # Extract content from description and content fields
        description = article.get("description", "")
        content = article.get("content", "")

        # Combine description and content, preferring content if available
        full_content = content or description
        if content and description and content.startswith(description[:50]):
            # Avoid duplication if content starts with description
            full_content = content
        elif content and description:
            full_content = f"{description}\n\n{content}"

        # Create title
        title = article.get("title", "Untitled Article")
        if not title or title == "[Removed]":
            title = f"News Article - {article.get('source', {}).get('name', 'Unknown Source')}"

        # Extract metadata
        metadata = {
            "source": "news_api",
            "api_source": article.get("source", {}).get("name", "Unknown"),
            "author": article.get("author"),
            "published_at": article.get("publishedAt"),
            "url": article.get("url"),
            "url_to_image": article.get("urlToImage"),
            "fetched_at": datetime.utcnow().isoformat(),
            "language": "en",  # NewsAPI returns English by default
        }

        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return DocumentCreate(
            title=title,
            content=full_content,
            source_type=DocumentSourceType.API,
            metadata=metadata,
        )

    async def ingest_articles(
        self,
        query: str,
        data_source: DataSource,
        db_session,
        batch_size: int = 20,
        max_articles: Optional[int] = None
    ) -> IngestionLog:
        """
        Ingest articles from NewsAPI and store in database.

        Args:
            query: Search query
            data_source: Data source configuration
            db_session: Database session
            batch_size: Articles to fetch per request
            max_articles: Maximum articles to ingest

        Returns:
            IngestionLog: Ingestion operation log
        """
        operation_id = str(uuid4())
        start_time = datetime.utcnow()

        log_entry = IngestionLog(
            operation_id=operation_id,
            ingestion_type=IngestionType.NEWS_FETCH,
            status=IngestionStatus.PENDING,
            started_at=start_time,
            data_source_id=data_source.id,
            parameters={
                "query": query,
                "batch_size": batch_size,
                "max_articles": max_articles,
            }
        )

        db_session.add(log_entry)
        await db_session.commit()

        try:
            logger.info(f"Starting NewsAPI ingestion for query: {query}")

            # Fetch articles
            response = await self.fetch_articles(
                query=query,
                page_size=min(batch_size, max_articles or batch_size)
            )

            articles = response.get("articles", [])
            total_articles = len(articles)

            if max_articles:
                articles = articles[:max_articles]

            logger.info(f"Fetched {len(articles)} articles from NewsAPI")

            # Process and store articles
            successful_count = 0
            failed_count = 0

            for article in articles:
                try:
                    # Normalize article
                    doc_data = self.normalize_article(article)

                    # Create document
                    document = RawDocument(
                        title=doc_data.title,
                        content=doc_data.content,
                        source_type=doc_data.source_type,
                        source_id=data_source.id,
                        external_id=article.get("url"),  # Use URL as external ID
                        metadata=doc_data.metadata,
                    )

                    db_session.add(document)
                    successful_count += 1

                except Exception as e:
                    logger.error(f"Failed to process article: {e}")
                    failed_count += 1
                    continue

            # Update data source statistics
            data_source.record_ingestion_success()
            await db_session.commit()

            # Complete the log entry
            log_entry.mark_completed(IngestionStatus.SUCCESS)
            log_entry.update_metrics(
                processed=len(articles),
                successful=successful_count,
                failed=failed_count
            )

            await db_session.commit()

            logger.info(f"NewsAPI ingestion completed: {successful_count} successful, {failed_count} failed")

        except Exception as e:
            logger.error(f"NewsAPI ingestion failed: {e}")

            # Record failure
            log_entry.record_error(str(e))
            data_source.record_ingestion_failure(str(e))

            await db_session.commit()

        return log_entry

    async def health_check(self) -> bool:
        """
        Check NewsAPI service health.

        Returns:
            bool: True if service is healthy
        """
        try:
            # Try a simple query to test API connectivity
            await self.fetch_articles("test", page_size=1)
            return True
        except Exception:
            return False
