"""
Vector embedding generation and storage.

This module handles:
- Embedding generation (OpenAI, Hugging Face)
- Vector database integration
- Batch operations
- Similarity search
"""

from .embeddings_service import EmbeddingsService, EmbeddingProvider

__all__ = [
    "EmbeddingsService",
    "EmbeddingProvider",
]
