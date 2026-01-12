"""
Financial API router for fetching stock market data.

This module provides FastAPI routes for financial data ingestion
from Alpha Vantage API with proper error handling and rate limiting.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_stakeholder_user
from db import get_db
from models import DataSource, DataSourceType, User
from schemas.documents import DocumentPublic, FinancialIngestionRequest, IngestionResponse
from services.financial.financial_service import FinancialService

router = APIRouter(prefix="/financial", tags=["financial"])
financial_service = FinancialService()


@router.post("/stocks/fetch", response_model=IngestionResponse)
async def fetch_stock_data(
    request: FinancialIngestionRequest,
    current_user: User = Depends(get_current_stakeholder_user),
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Fetch and ingest stock market data from Alpha Vantage.

    Retrieves various types of financial data for the specified stock symbol
    and stores them in the database after normalization.

    Args:
        request: Financial data ingestion request parameters
        current_user: Current authenticated user
        db: Database session

    Returns:
        IngestionResponse: Ingestion operation result

    Raises:
        HTTPException: If Alpha Vantage API key is not configured or ingestion fails
    """
    try:
        # Get or create Alpha Vantage data source
        data_source = await _get_or_create_alpha_vantage_data_source(db)

        # Default functions if not specified
        functions = ["GLOBAL_QUOTE", "TIME_SERIES_DAILY"]
        if hasattr(request, 'function') and request.function:
            functions = [request.function]

        # Perform ingestion
        log_entry = await financial_service.ingest_stock_data(
            symbol=request.symbol,
            data_source=data_source,
            db_session=db,
            functions=functions,
        )

        return IngestionResponse(
            operation_id=log_entry.operation_id,
            status=log_entry.status,
            message=f"Successfully ingested financial data for {request.symbol}",
            records_processed=log_entry.records_processed,
            records_successful=log_entry.records_successful,
            records_failed=log_entry.records_failed,
            duration_seconds=log_entry.duration_seconds,
        )

    except ValueError as e:
        if "Alpha Vantage API key not configured" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Alpha Vantage service is not configured. Please set ALPHA_VANTAGE_API_KEY environment variable.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch financial data: {str(e)}",
        )


@router.get("/stocks/{symbol}", response_model=List[DocumentPublic])
async def get_stock_data(
    symbol: str,
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(get_current_stakeholder_user),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentPublic]:
    """
    Get ingested financial data for a specific stock symbol.

    Returns a paginated list of financial documents that have been ingested
    for the specified stock symbol from Alpha Vantage.

    Args:
        symbol: Stock symbol (e.g., AAPL, GOOGL)
        limit: Maximum number of records to return
        offset: Number of records to skip
        current_user: Current authenticated user
        db: Database session

    Returns:
        List[DocumentPublic]: List of financial data documents
    """
    from sqlalchemy import select
    from models import RawDocument, DocumentSourceType

    stmt = (
        select(RawDocument)
        .where(RawDocument.source_type == DocumentSourceType.API)
        .where(RawDocument.metadata.contains({"source": "alpha_vantage", "symbol": symbol.upper()}))
        .order_by(RawDocument.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)
    documents = result.scalars().all()

    return [DocumentPublic.model_validate(doc) for doc in documents]


@router.get("/stocks", response_model=List[str])
async def get_available_symbols(
    current_user: User = Depends(get_current_stakeholder_user),
    db: AsyncSession = Depends(get_db),
) -> List[str]:
    """
    Get list of stock symbols that have been ingested.

    Returns a list of unique stock symbols for which financial data
    has been stored in the database.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List[str]: List of stock symbols
    """
    from sqlalchemy import select, distinct
    from models import RawDocument

    # Extract symbols from metadata
    stmt = (
        select(distinct(RawDocument.metadata['symbol']))
        .where(RawDocument.metadata.contains({"source": "alpha_vantage"}))
        .where(RawDocument.metadata.has_key('symbol'))  # type: ignore
    )

    result = await db.execute(stmt)
    symbols = result.scalars().all()

    return [symbol for symbol in symbols if symbol]


@router.get("/health")
async def check_alpha_vantage_health(
    current_user: User = Depends(get_current_stakeholder_user),
) -> dict:
    """
    Check Alpha Vantage service health.

    Args:
        current_user: Current authenticated user

    Returns:
        Dict: Health check result
    """
    is_healthy = await financial_service.health_check()

    return {
        "service": "alpha_vantage",
        "healthy": is_healthy,
        "status": "healthy" if is_healthy else "unhealthy",
    }


async def _get_or_create_alpha_vantage_data_source(db: AsyncSession) -> DataSource:
    """
    Get or create the Alpha Vantage data source.

    Args:
        db: Database session

    Returns:
        DataSource: Alpha Vantage data source instance
    """
    from sqlalchemy import select

    stmt = select(DataSource).where(DataSource.type == DataSourceType.ALPHA_VANTAGE)
    result = await db.execute(stmt)
    data_source = result.scalar_one_or_none()

    if not data_source:
        # Create new data source for Alpha Vantage
        data_source = DataSource(
            name="Alpha Vantage",
            type=DataSourceType.ALPHA_VANTAGE,
            description="Alpha Vantage financial market data API",
            config={
                "base_url": "https://www.alphavantage.co/query",
                "rate_limit_per_day": 25,
                "supported_functions": [
                    "GLOBAL_QUOTE",
                    "TIME_SERIES_INTRADAY",
                    "TIME_SERIES_DAILY",
                    "TIME_SERIES_WEEKLY",
                    "TIME_SERIES_MONTHLY",
                    "OVERVIEW",
                    "INCOME_STATEMENT",
                    "BALANCE_SHEET",
                    "CASH_FLOW",
                ],
            },
            source_url="https://www.alphavantage.co",
            api_version="v1",
        )
        db.add(data_source)
        await db.commit()
        await db.refresh(data_source)

    return data_source
