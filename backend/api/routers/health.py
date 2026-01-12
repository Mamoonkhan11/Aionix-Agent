"""
Health check API router.

This module provides health check endpoints for monitoring application
status, database connectivity, and external service availability.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db import get_db
from models import IngestionStatus
from services.financial.financial_service import FinancialService
from services.news.news_service import NewsAPIService

router = APIRouter(prefix="/health", tags=["health"])

# Global variables to track application startup time and health status
_app_start_time = time.time()
_last_health_check = 0
_health_cache_duration = 30  # Cache health checks for 30 seconds


@router.get("/live")
async def liveness_check() -> Dict:
    """
    Liveness probe endpoint.

    Used by Kubernetes/orchestrators to determine if the application is running.
    This endpoint should always return 200 if the application is running.

    Returns:
        Dict: Basic liveness information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "aionix-agent-backend",
        "version": settings.app_version,
    }


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Readiness probe endpoint.

    Used by orchestrators to determine if the application is ready to serve traffic.
    Checks database connectivity and basic application health.

    Args:
        db: Database session for connectivity check

    Returns:
        Dict: Readiness status with component checks
    """
    checks = {}

    # Check database connectivity
    try:
        await db.execute("SELECT 1")
        checks["database"] = {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "message": f"Database error: {str(e)}"}

    # Check application uptime
    uptime_seconds = time.time() - _app_start_time
    checks["application"] = {
        "status": "healthy",
        "message": f"Application running for {uptime_seconds:.1f} seconds"
    }

    # Overall status
    overall_status = "healthy" if all(check["status"] == "healthy" for check in checks.values()) else "unhealthy"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "aionix-agent-backend",
        "version": settings.app_version,
        "checks": checks,
    }


@router.get("/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Detailed health check endpoint.

    Provides comprehensive health information including external services,
    performance metrics, and system status.

    Args:
        db: Database session

    Returns:
        Dict: Detailed health information
    """
    # Check cache to avoid excessive external API calls
    global _last_health_check
    current_time = time.time()

    if current_time - _last_health_check < _health_cache_duration:
        # Return cached result if within cache duration
        pass  # We'll still perform checks but could optimize this

    _last_health_check = current_time

    checks = {}

    # Basic application checks
    uptime_seconds = time.time() - _app_start_time
    checks["application"] = {
        "status": "healthy",
        "uptime_seconds": uptime_seconds,
        "version": settings.app_version,
        "environment": settings.environment,
    }

    # Database check
    try:
        start_time = time.time()
        await db.execute("SELECT COUNT(*) FROM users")
        db_check_time = time.time() - start_time
        checks["database"] = {
            "status": "healthy",
            "response_time": f"{db_check_time:.3f}s",
            "message": "Database connection and query OK"
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}"
        }

    # External service checks (run in parallel)
    external_checks = await _check_external_services()
    checks.update(external_checks)

    # System metrics
    checks["system"] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "memory_usage": "N/A",  # Could add psutil for detailed metrics
        "cpu_usage": "N/A",
    }

    # Overall status
    overall_status = "healthy"
    for check_name, check_data in checks.items():
        if isinstance(check_data, dict) and check_data.get("status") == "unhealthy":
            overall_status = "unhealthy"
            break

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "aionix-agent-backend",
        "checks": checks,
    }


@router.get("/services")
async def service_health_check() -> Dict:
    """
    External services health check.

    Checks the health of external APIs and services that the application depends on.

    Returns:
        Dict: External service health status
    """
    services_status = await _check_external_services()

    overall_status = "healthy"
    for service, status_info in services_status.items():
        if status_info["status"] == "unhealthy":
            overall_status = "unhealthy"
            break

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": services_status,
    }


async def _check_external_services() -> Dict[str, Dict]:
    """
    Check health of external services.

    Returns:
        Dict: Health status of each external service
    """
    services = {}

    # Check NewsAPI
    try:
        news_service = NewsAPIService()
        news_healthy = await news_service.health_check()
        services["news_api"] = {
            "status": "healthy" if news_healthy else "unhealthy",
            "message": "NewsAPI is responding" if news_healthy else "NewsAPI is not responding",
            "configured": bool(settings.news_api_key),
        }
    except Exception as e:
        services["news_api"] = {
            "status": "unhealthy",
            "message": f"NewsAPI check failed: {str(e)}",
            "configured": bool(settings.news_api_key),
        }

    # Check Alpha Vantage
    try:
        financial_service = FinancialService()
        av_healthy = await financial_service.health_check()
        services["alpha_vantage"] = {
            "status": "healthy" if av_healthy else "unhealthy",
            "message": "Alpha Vantage is responding" if av_healthy else "Alpha Vantage is not responding",
            "configured": bool(settings.alpha_vantage_api_key),
        }
    except Exception as e:
        services["alpha_vantage"] = {
            "status": "unhealthy",
            "message": f"Alpha Vantage check failed: {str(e)}",
            "configured": bool(settings.alpha_vantage_api_key),
        }

    # Check OpenAI (placeholder - would need actual API call)
    services["openai"] = {
        "status": "unknown",
        "message": "OpenAI health check not implemented",
        "configured": bool(settings.openai_api_key),
    }

    # Check Vector DB (placeholder - would need actual API call)
    services["vector_db"] = {
        "status": "unknown",
        "message": "Vector DB health check not implemented",
        "configured": bool(settings.vector_db_api_key),
    }

    return services


@router.get("/metrics")
async def health_metrics(
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Application health metrics.

    Provides various metrics about application performance and usage.

    Args:
        db: Database session

    Returns:
        Dict: Application metrics
    """
    metrics = {}

    try:
        # User count
        from sqlalchemy import func, select
        from models import User, RawDocument, IngestionLog

        result = await db.execute(select(func.count()).select_from(User))
        metrics["total_users"] = result.scalar()

        # Document count
        result = await db.execute(select(func.count()).select_from(RawDocument))
        metrics["total_documents"] = result.scalar()

        # Ingestion log count
        result = await db.execute(select(func.count()).select_from(IngestionLog))
        metrics["total_ingestions"] = result.scalar()

        # Recent ingestion success rate (last 100 operations)
        result = await db.execute(
            select(IngestionLog.status)
            .order_by(IngestionLog.created_at.desc())
            .limit(100)
        )
        recent_logs = result.scalars().all()
        if recent_logs:
            successful = sum(1 for log in recent_logs if log == IngestionStatus.SUCCESS)
            metrics["recent_success_rate"] = f"{(successful / len(recent_logs)) * 100:.1f}%"

    except Exception as e:
        metrics["error"] = f"Failed to collect metrics: {str(e)}"

    # Application metrics
    metrics["uptime_seconds"] = time.time() - _app_start_time
    metrics["environment"] = settings.environment
    metrics["version"] = settings.app_version

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
    }
