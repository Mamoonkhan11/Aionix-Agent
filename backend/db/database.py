"""
Database connection and session management.

This module provides async SQLAlchemy engine and session management
for the PostgreSQL database with proper connection pooling and error handling.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import settings


class DatabaseManager:
    """
    Database connection manager for async SQLAlchemy operations.

    Provides centralized database connection management with proper
    connection pooling and session handling.
    """

    def __init__(self) -> None:
        """Initialize the database manager."""
        self._engine = None
        self._async_session_maker = None

    def create_engine(self) -> None:
        """Create the async SQLAlchemy engine."""
        self._engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            future=True,
            pool_pre_ping=True,  # Test connections before using them
            pool_size=10,  # Connection pool size
            max_overflow=20,  # Max overflow connections
            pool_timeout=30,  # Connection timeout
            pool_recycle=1800,  # Recycle connections after 30 minutes
        )

    def create_session_maker(self) -> None:
        """Create the async session maker."""
        if not self._engine:
            raise RuntimeError("Engine not created. Call create_engine() first.")

        self._async_session_maker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Don't auto-flush
            autocommit=False,  # Don't auto-commit
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session.

        Yields:
            AsyncSession: Database session for async operations

        Note:
            Automatically handles session cleanup and rollback on exceptions.
        """
        if not self._async_session_maker:
            raise RuntimeError("Session maker not initialized. Call create_session_maker() first.")

        async with self._async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Close the database engine and clean up connections."""
        if self._engine:
            await self._engine.dispose()

    async def health_check(self) -> bool:
        """
        Perform a database health check.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception:
            return False


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI to get database session.

    This function is used as a dependency in FastAPI routes to provide
    database sessions with automatic cleanup.

    Yields:
        AsyncSession: Database session
    """
    async with db_manager.get_session() as session:
        yield session


async def init_database() -> None:
    """Initialize the database connection."""
    db_manager.create_engine()
    db_manager.create_session_maker()

    # Import models to ensure they are registered with SQLAlchemy
    from models import Base  # noqa: F401


async def close_database() -> None:
    """Close database connections."""
    await db_manager.close()
