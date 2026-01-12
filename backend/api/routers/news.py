"""
News API router for fetching and ingesting news articles.

This module provides FastAPI routes for news article ingestion
from NewsAPI with proper error handling and rate limiting.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_stakeholder_user
from db import get_db
from models import DataSource, DataSourceType, User
from schemas.documents import DocumentPublic, IngestionResponse, NewsIngestionRequest
from services.news.news_service import NewsAPIService

router = APIRouter(prefix="/news", tags=["news"])
news_service = NewsAPIService()


@router.post("/fetch", response_model=IngestionResponse)
async def fetch_news_articles(
    request: NewsIngestionRequest,
    current_user: User = Depends(get_current_stakeholder_user),
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Fetch and ingest news articles from NewsAPI.

    Searches for articles matching the provided query and stores them
    in the database after normalization.

    Args:
        request: News ingestion request parameters
        current_user: Current authenticated user
        db: Database session

    Returns:
        IngestionResponse: Ingestion operation result

    Raises:
        HTTPException: If NewsAPI key is not configured or ingestion fails
    """
    try:
        # Get or create news API data source
        data_source = await _get_or_create_news_data_source(db)

        # Perform ingestion
        log_entry = await news_service.ingest_articles(
            query=request.query,
            data_source=data_source,
            db_session=db,
            max_articles=request.max_articles,
        )

        return IngestionResponse(
            operation_id=log_entry.operation_id,
            status=log_entry.status,
            message=f"Successfully ingested {log_entry.records_successful} articles",
            records_processed=log_entry.records_processed,
            records_successful=log_entry.records_successful,
            records_failed=log_entry.records_failed,
            duration_seconds=log_entry.duration_seconds,
        )

    except ValueError as e:
        if "NewsAPI key not configured" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="NewsAPI service is not configured. Please set NEWS_API_KEY environment variable.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch news articles: {str(e)}",
        )


@router.get("/articles", response_model=List[DocumentPublic])
async def get_news_articles(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of articles to return"),
    offset: int = Query(0, ge=0, description="Number of articles to skip"),
    current_user: User = Depends(get_current_stakeholder_user),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentPublic]:
    """
    Get ingested news articles.

    Returns a paginated list of news articles that have been ingested
    from NewsAPI.

    Args:
        limit: Maximum number of articles to return
        offset: Number of articles to skip
        current_user: Current authenticated user
        db: Database session

    Returns:
        List[DocumentPublic]: List of news articles
    """
    from sqlalchemy import select
    from models import RawDocument, DocumentSourceType

    stmt = (
        select(RawDocument)
        .where(RawDocument.source_type == DocumentSourceType.API)
        .where(RawDocument.metadata.contains({"source": "news_api"}))
        .order_by(RawDocument.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)
    articles = result.scalars().all()

    return [DocumentPublic.model_validate(article) for article in articles]


@router.get("/sources")
async def get_news_sources(
    current_user: User = Depends(get_current_stakeholder_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get available news sources from NewsAPI.

    Note: This endpoint fetches sources from NewsAPI and returns them
    without storing in database.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict: NewsAPI sources information
    """
    try:
        async with news_service.client_config as client:
            response = await client.get(
                f"{news_service.base_url}/sources",
                params={"apiKey": news_service.api_key}
            )
            response.raise_for_status()
            return response.json()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch news sources: {str(e)}",
        )


@router.get("/health")
async def check_news_api_health(
    current_user: User = Depends(get_current_stakeholder_user),
) -> dict:
    """
    Check NewsAPI service health.

    Args:
        current_user: Current authenticated user

    Returns:
        Dict: Health check result
    """
    is_healthy = await news_service.health_check()

    return {
        "service": "news_api",
        "healthy": is_healthy,
        "status": "healthy" if is_healthy else "unhealthy",
    }


async def _get_or_create_news_data_source(db: AsyncSession) -> DataSource:
    """
    Get or create the NewsAPI data source.

    Args:
        db: Database session

    Returns:
        DataSource: NewsAPI data source instance
    """
    from sqlalchemy import select

    stmt = select(DataSource).where(DataSource.type == DataSourceType.NEWS_API)
    result = await db.execute(stmt)
    data_source = result.scalar_one_or_none()

    if not data_source:
        # Create new data source for NewsAPI
        data_source = DataSource(
            name="NewsAPI",
            type=DataSourceType.NEWS_API,
            description="NewsAPI.org news article service",
            config={
                "base_url": "https://newsapi.org/v2",
                "rate_limit_per_day": 100,
                "supported_languages": ["en", "es", "fr", "de", "it", "pt", "ru", "ar", "he", "zh"],
            },
            source_url="https://newsapi.org",
            api_version="v2",
        )
        db.add(data_source)
        await db.commit()
        await db.refresh(data_source)

    return data_source
