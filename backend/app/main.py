"""
Main FastAPI application for the Aionix Agent Backend.

This module creates and configures the FastAPI application with all
routers, middleware, and documentation settings.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import agents_router, auth_router, collaboration_router, financial_router, health_router, news_router, scheduler_router, upload_router, voice_router, web_search_router
from core.config import settings
from core.logging_config import get_logger
from core.middleware import (
    ErrorHandlingMiddleware,
    RateLimitingMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    create_cors_middleware,
)
from db import close_database, init_database

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting Aionix Agent Backend")

    try:
        # Initialize database connection
        await init_database()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Aionix Agent Backend")

    try:
        await close_database()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    # Create FastAPI app with metadata
    app = FastAPI(
        title=settings.app_name,
        description="""
        # Aionix Agent Backend API

        A production-ready FastAPI backend for an Autonomous AI Knowledge Worker system.

        ## Features

        - **Data Ingestion**: Collect data from NewsAPI, Alpha Vantage, and file uploads
        - **Authentication**: JWT-based authentication with role-based access control
        - **Document Processing**: Text extraction from PDFs, DOCX, and TXT files
        - **Health Monitoring**: Comprehensive health checks and metrics
        - **Structured Logging**: JSON logging with request tracing
        - **Database**: PostgreSQL with async SQLAlchemy ORM

        ## Authentication

        Most endpoints require authentication. Include the JWT token in the Authorization header:

        ```
        Authorization: Bearer <your-jwt-token>
        ```

        Get a token by logging in at `/auth/login` or registering at `/auth/register`.

        ## Rate Limiting

        API endpoints are rate-limited. Check the response headers for rate limit information.

        ## Support

        For issues or questions, please refer to the application logs or contact the development team.
        """,
        version=settings.app_version,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        contact={
            "name": "Aionix Team",
            "email": "team@aionix.ai",
        },
        license_info={
            "name": "MIT",
        },
        # OpenAPI tags for better organization
        openapi_tags=[
            {
                "name": "authentication",
                "description": "User authentication and authorization endpoints",
                "externalDocs": {
                    "description": "Authentication Guide",
                    "url": "https://docs.aionix.ai/auth",
                },
            },
            {
                "name": "news",
                "description": "News article ingestion from NewsAPI",
                "externalDocs": {
                    "description": "NewsAPI Documentation",
                    "url": "https://newsapi.org/docs",
                },
            },
            {
                "name": "financial",
                "description": "Financial data ingestion from Alpha Vantage",
                "externalDocs": {
                    "description": "Alpha Vantage Documentation",
                    "url": "https://www.alphavantage.co/documentation/",
                },
            },
            {
                "name": "upload",
                "description": "File upload and document processing",
                "externalDocs": {
                    "description": "File Upload Guide",
                    "url": "https://docs.aionix.ai/upload",
                },
            },
            {
                "name": "health",
                "description": "Health checks and monitoring endpoints",
                "externalDocs": {
                    "description": "Health Checks",
                    "url": "https://docs.aionix.ai/health",
                },
            },
        ],
    )

    # Add middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # Add CORS middleware
    cors_settings = create_cors_middleware()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_settings["allow_origins"],
        allow_credentials=cors_settings["allow_credentials"],
        allow_methods=cors_settings["allow_methods"],
        allow_headers=cors_settings["allow_headers"],
        expose_headers=cors_settings["expose_headers"],
        max_age=cors_settings["max_age"],
    )

    # Add rate limiting (only if not in development)
    if not settings.is_development:
        app.add_middleware(RateLimitingMiddleware, requests_per_minute=60)

    # Include routers
    app.include_router(auth_router)
    app.include_router(news_router)
    app.include_router(financial_router)
    app.include_router(upload_router)
    app.include_router(health_router)
    app.include_router(scheduler_router)
    app.include_router(web_search_router)
    app.include_router(agents_router)
    app.include_router(collaboration_router)
    app.include_router(voice_router)

    # Add root endpoint
    @app.get(
        "/",
        summary="API Root",
        description="Welcome endpoint providing basic API information",
        tags=["general"],
    )
    async def root():
        """Get basic API information."""
        return {
            "message": "Welcome to Aionix Agent Backend API",
            "version": settings.app_version,
            "environment": settings.environment,
            "docs": "/docs",
            "health": "/health/ready",
        }

    # Add global exception handler for unhandled exceptions
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled exceptions."""
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "user_agent": request.headers.get("user-agent"),
            },
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": getattr(request.state, "request_id", "unknown"),
                }
            },
        )

    return app


# Create the FastAPI application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn

    # Run the application with uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
    )
