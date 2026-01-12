"""
Pytest configuration and fixtures for the Aionix Agent Backend tests.

This module provides test fixtures and configuration for the test suite.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from core.config import settings
from db.database import DatabaseManager
from models import Base


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_manager():
    """Create a test database manager."""
    # Create test database engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session maker
    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    yield session_maker

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_db_manager) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_db_manager() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def test_settings():
    """Override settings for testing."""
    # Could override settings here if needed
    return settings
