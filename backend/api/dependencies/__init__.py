"""
API dependencies for dependency injection.

This module provides reusable dependencies for FastAPI routes,
including authentication, database sessions, and validation.
"""

from core.security import get_current_admin_user, get_current_stakeholder_user, get_current_user
from db import get_db

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_admin_user",
    "get_current_stakeholder_user",
]
