"""
API routers module.

This module contains all FastAPI routers for the application,
providing endpoints for authentication, data ingestion, and health checks.
"""

from .agents import router as agents_router
from .auth import router as auth_router
from .collaboration import router as collaboration_router
from .financial import router as financial_router
from .health import router as health_router
from .news import router as news_router
from .scheduler import router as scheduler_router
from .upload import router as upload_router
from .voice import router as voice_router
from .web_search import router as web_search_router

__all__ = [
    "agents_router",
    "auth_router",
    "collaboration_router",
    "financial_router",
    "health_router",
    "news_router",
    "scheduler_router",
    "upload_router",
    "voice_router",
    "web_search_router",
]
