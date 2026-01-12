"""
Configuration module for the Aionix Agent Backend.

This module provides centralized configuration management using pydantic-settings,
supporting different environments with secure handling of secrets.
"""

from .settings import settings

__all__ = ["settings"]
