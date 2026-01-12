"""
Long-term memory for the AI system.

This module provides:
- Historical data storage
- Semantic search over past insights
- Context retrieval
- Time-aware relevance scoring
"""

from .memory_service import MemoryService

__all__ = [
    "MemoryService",
]
