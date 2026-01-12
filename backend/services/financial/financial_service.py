"""
Alpha Vantage integration service for financial data.

This module provides functionality to fetch financial market data from Alpha Vantage API
and normalize it into the internal document format for ingestion.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.config import settings
from models import DataSource, IngestionLog, IngestionStatus, IngestionType, RawDocument, DocumentSourceType
from schemas.documents import DocumentCreate
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class FinancialService:
    """
    Service for fetching financial data from Alpha Vantage API.

    Provides methods to fetch stock market data, handle rate limiting,
    and normalize responses into internal document format.
    """

    def __init__(self):
        """Initialize Alpha Vantage service with configuration."""
        self.base_url = settings.alpha_vantage_base_url
        self.api_key = settings.alpha_vantage_api_key
        self.rate_limiter = RateLimiter(requests_per_hour=settings.alpha_vantage_rate_limit)

        # HTTP client configuration
        self.client_config = {
            "timeout": httpx.Timeout(30.0, connect=10.0),
            "headers": {
                "User-Agent": "Aionix-Agent-Backend/1.0",
                "Accept": "application/json",
            }
        }

    async def process(self, data):
        """
        Process financial data.

        Args:
            data: Input data to process

        Returns:
            Processed data
        """
        return data

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def fetch_time_series(
        self,
        symbol: str,
        function: str = "TIME_SERIES_DAILY",
        interval: Optional[str] = None,
        outputsize: str = "compact"
    ) -> Dict[str, Any]:
        """
        Fetch time series data from Alpha Vantage.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
            function: Time series function
            interval: Interval for intraday data (1min, 5min, etc.)
            outputsize: 'compact' (latest 100) or 'full' (all available)

        Returns:
            Dict: Alpha Vantage API response

        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If API key is not configured
        """
        if not self.api_key:
            raise ValueError("Alpha Vantage API key not configured")

        # Check rate limit
        await self.rate_limiter.wait_if_needed()

        params = {
            "function": function,
            "symbol": symbol.upper(),
            "apikey": self.api_key,
            "outputsize": outputsize,
        }

        if interval and function == "TIME_SERIES_INTRADAY":
            params["interval"] = interval

        async with httpx.AsyncClient(**self.client_config) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if "Error Message" in data:
                raise ValueError(f"Alpha Vantage API Error: {data['Error Message']}")

            if "Note" in data and "rate limit" in data["Note"].lower():
                raise ValueError("Alpha Vantage API rate limit exceeded")

            return data

    async def fetch_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current stock quote.

        Args:
            symbol: Stock symbol

        Returns:
            Dict: Stock quote data
        """
        return await self.fetch_time_series(symbol, "GLOBAL_QUOTE")

    async def fetch_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch company overview information.

        Args:
            symbol: Stock symbol

        Returns:
            Dict: Company overview data
        """
        return await self.fetch_time_series(symbol, "OVERVIEW")

    async def fetch_income_statement(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch company income statement.

        Args:
            symbol: Stock symbol

        Returns:
            Dict: Income statement data
        """
        return await self.fetch_time_series(symbol, "INCOME_STATEMENT")

    async def fetch_balance_sheet(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch company balance sheet.

        Args:
            symbol: Stock symbol

        Returns:
            Dict: Balance sheet data
        """
        return await self.fetch_time_series(symbol, "BALANCE_SHEET")

    async def fetch_cash_flow(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch company cash flow statement.

        Args:
            symbol: Stock symbol

        Returns:
            Dict: Cash flow data
        """
        return await self.fetch_time_series(symbol, "CASH_FLOW")

    def normalize_time_series_data(self, data: Dict[str, Any], symbol: str) -> DocumentCreate:
        """
        Normalize Alpha Vantage time series data to internal document format.

        Args:
            data: Alpha Vantage time series response
            symbol: Stock symbol

        Returns:
            DocumentCreate: Normalized document data
        """
        # Extract metadata
        metadata = {
            "source": "alpha_vantage",
            "symbol": symbol,
            "data_type": "time_series",
            "fetched_at": datetime.utcnow().isoformat(),
            "api_response": data,  # Store full response for reference
        }

        # Find the time series key
        time_series_key = None
        for key in data.keys():
            if "Time Series" in key:
                time_series_key = key
                break

        if not time_series_key:
            raise ValueError("No time series data found in response")

        time_series = data[time_series_key]
        dates = list(time_series.keys())[:10]  # Get latest 10 entries

        # Create readable content
        content_parts = [
            f"Financial data for {symbol} from Alpha Vantage API.",
            f"Latest available data as of {dates[0] if dates else 'N/A'}:",
            ""
        ]

        for date in dates:
            values = time_series[date]
            content_parts.append(f"Date: {date}")
            for key, value in values.items():
                content_parts.append(f"  {key}: {value}")
            content_parts.append("")

        content = "\n".join(content_parts)

        # Extract title
        title = f"Stock Data: {symbol} - {time_series_key.replace('Time Series', '').strip()}"

        return DocumentCreate(
            title=title,
            content=content,
            source_type=DocumentSourceType.API,
            metadata=metadata,
        )

    def normalize_quote_data(self, data: Dict[str, Any], symbol: str) -> DocumentCreate:
        """
        Normalize stock quote data to internal document format.

        Args:
            data: Alpha Vantage quote response
            symbol: Stock symbol

        Returns:
            DocumentCreate: Normalized document data
        """
        quote = data.get("Global Quote", {})

        if not quote:
            raise ValueError("No quote data found in response")

        # Create readable content
        content = f"""
Stock Quote for {symbol}:

Symbol: {quote.get('01. symbol', symbol)}
Open: {quote.get('02. open', 'N/A')}
High: {quote.get('03. high', 'N/A')}
Low: {quote.get('04. low', 'N/A')}
Price: {quote.get('05. price', 'N/A')}
Volume: {quote.get('06. volume', 'N/A')}
Latest Trading Day: {quote.get('07. latest trading day', 'N/A')}
Previous Close: {quote.get('08. previous close', 'N/A')}
Change: {quote.get('09. change', 'N/A')}
Change Percent: {quote.get('10. change percent', 'N/A')}

Data fetched from Alpha Vantage API on {datetime.utcnow().isoformat()}
"""

        metadata = {
            "source": "alpha_vantage",
            "symbol": symbol,
            "data_type": "quote",
            "fetched_at": datetime.utcnow().isoformat(),
            "api_response": data,
        }

        title = f"Stock Quote: {symbol}"

        return DocumentCreate(
            title=title,
            content=content.strip(),
            source_type=DocumentSourceType.API,
            metadata=metadata,
        )

    def normalize_fundamental_data(self, data: Dict[str, Any], symbol: str, data_type: str) -> DocumentCreate:
        """
        Normalize fundamental data (overview, financials) to internal document format.

        Args:
            data: Alpha Vantage fundamental data response
            symbol: Stock symbol
            data_type: Type of fundamental data

        Returns:
            DocumentCreate: Normalized document data
        """
        # Create readable content from key-value pairs
        content_parts = [
            f"{data_type.replace('_', ' ').title()} for {symbol}:",
            ""
        ]

        for key, value in data.items():
            if value and str(value).strip():  # Skip empty values
                content_parts.append(f"{key}: {value}")

        content = "\n".join(content_parts)

        metadata = {
            "source": "alpha_vantage",
            "symbol": symbol,
            "data_type": data_type,
            "fetched_at": datetime.utcnow().isoformat(),
            "api_response": data,
        }

        title = f"{data_type.replace('_', ' ').title()}: {symbol}"

        return DocumentCreate(
            title=title,
            content=content,
            source_type=DocumentSourceType.API,
            metadata=metadata,
        )

    async def ingest_stock_data(
        self,
        symbol: str,
        data_source: DataSource,
        db_session,
        functions: Optional[List[str]] = None
    ) -> IngestionLog:
        """
        Ingest stock data from Alpha Vantage and store in database.

        Args:
            symbol: Stock symbol to fetch
            data_source: Data source configuration
            db_session: Database session
            functions: List of Alpha Vantage functions to call

        Returns:
            IngestionLog: Ingestion operation log
        """
        if functions is None:
            functions = ["GLOBAL_QUOTE", "TIME_SERIES_DAILY"]

        operation_id = str(uuid4())
        start_time = datetime.utcnow()

        log_entry = IngestionLog(
            operation_id=operation_id,
            ingestion_type=IngestionType.STOCK_DATA,
            status=IngestionStatus.PENDING,
            started_at=start_time,
            data_source_id=data_source.id,
            parameters={
                "symbol": symbol,
                "functions": functions,
            }
        )

        db_session.add(log_entry)
        await db_session.commit()

        try:
            logger.info(f"Starting Alpha Vantage ingestion for symbol: {symbol}")

            successful_count = 0
            failed_count = 0

            # Fetch different types of data
            for function in functions:
                try:
                    if function == "GLOBAL_QUOTE":
                        data = await self.fetch_stock_quote(symbol)
                        doc_data = self.normalize_quote_data(data, symbol)

                    elif function.startswith("TIME_SERIES"):
                        data = await self.fetch_time_series(symbol, function)
                        doc_data = self.normalize_time_series_data(data, symbol)

                    elif function == "OVERVIEW":
                        data = await self.fetch_company_overview(symbol)
                        doc_data = self.normalize_fundamental_data(data, symbol, "company_overview")

                    elif function == "INCOME_STATEMENT":
                        data = await self.fetch_income_statement(symbol)
                        doc_data = self.normalize_fundamental_data(data, symbol, "income_statement")

                    elif function == "BALANCE_SHEET":
                        data = await self.fetch_balance_sheet(symbol)
                        doc_data = self.normalize_fundamental_data(data, symbol, "balance_sheet")

                    elif function == "CASH_FLOW":
                        data = await self.fetch_cash_flow(symbol)
                        doc_data = self.normalize_fundamental_data(data, symbol, "cash_flow")

                    else:
                        logger.warning(f"Unsupported function: {function}")
                        continue

                    # Create document
                    document = RawDocument(
                        title=doc_data.title,
                        content=doc_data.content,
                        source_type=doc_data.source_type,
                        source_id=data_source.id,
                        external_id=f"{symbol}_{function}_{datetime.utcnow().date()}",
                        metadata=doc_data.metadata,
                    )

                    db_session.add(document)
                    successful_count += 1

                except Exception as e:
                    logger.error(f"Failed to fetch {function} for {symbol}: {e}")
                    failed_count += 1
                    continue

            # Update data source statistics
            data_source.record_ingestion_success()
            await db_session.commit()

            # Complete the log entry
            log_entry.mark_completed(IngestionStatus.SUCCESS)
            log_entry.update_metrics(
                processed=len(functions),
                successful=successful_count,
                failed=failed_count
            )

            await db_session.commit()

            logger.info(f"Alpha Vantage ingestion completed: {successful_count} successful, {failed_count} failed")

        except Exception as e:
            logger.error(f"Alpha Vantage ingestion failed: {e}")

            # Record failure
            log_entry.record_error(str(e))
            data_source.record_ingestion_failure(str(e))

            await db_session.commit()

        return log_entry

    async def health_check(self) -> bool:
        """
        Check Alpha Vantage service health.

        Returns:
            bool: True if service is healthy
        """
        try:
            # Try to fetch a simple quote to test API connectivity
            await self.fetch_stock_quote("AAPL")
            return True
        except Exception:
            return False
