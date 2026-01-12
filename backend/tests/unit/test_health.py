"""
Unit tests for health check endpoints.

This module tests the health check router endpoints including
liveness, readiness, and detailed health checks.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestHealthEndpoints:
    """Test cases for health check endpoints."""

    @pytest.mark.asyncio
    async def test_liveness_check(self, client: AsyncClient):
        """Test liveness probe endpoint."""
        response = await client.get("/health/live")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "aionix-agent-backend"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_readiness_check_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test readiness probe endpoint with healthy database."""
        response = await client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data
        assert "version" in data
        assert "checks" in data

        # Check database health
        assert "database" in data["checks"]
        assert data["checks"]["database"]["status"] == "healthy"

        # Check application health
        assert "application" in data["checks"]
        assert data["checks"]["application"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_detailed_health_check(self, client: AsyncClient, db_session: AsyncSession):
        """Test detailed health check endpoint."""
        response = await client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert "checks" in data

        # Check that all expected components are present
        expected_checks = ["application", "database", "news_api", "alpha_vantage", "openai", "vector_db", "system"]
        for check_name in expected_checks:
            assert check_name in data["checks"]
            assert "status" in data["checks"][check_name]

    @pytest.mark.asyncio
    async def test_service_health_check(self, client: AsyncClient):
        """Test external services health check."""
        response = await client.get("/health/services")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "services" in data

        # Check that external services are included
        expected_services = ["news_api", "alpha_vantage", "openai", "vector_db"]
        for service_name in expected_services:
            assert service_name in data["services"]
            assert "status" in data["services"][service_name]
            assert "configured" in data["services"][service_name]

    @pytest.mark.asyncio
    async def test_health_metrics(self, client: AsyncClient, db_session: AsyncSession):
        """Test health metrics endpoint."""
        response = await client.get("/health/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "timestamp" in data
        assert "metrics" in data

        # Check that metrics include expected fields
        metrics = data["metrics"]
        assert "uptime_seconds" in metrics
        assert "environment" in metrics
        assert "version" in metrics

        # Database-dependent metrics might be missing in test environment
        # but should not cause errors
        for field in ["total_users", "total_documents", "total_ingestions"]:
            assert field in metrics  # Field should be present even if 0 or None
