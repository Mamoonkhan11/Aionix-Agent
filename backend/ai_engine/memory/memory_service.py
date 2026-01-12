"""
Long-term Memory Service for the AI System.

Stores historical summaries, insights, and enables semantic search
over past data with time-aware relevance scoring.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ai_engine.embeddings import EmbeddingsService
from db import get_db
from models import RawDocument

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service for managing long-term memory of the AI system.
    """

    def __init__(
        self,
        embeddings_service: Optional[EmbeddingsService] = None,
    ):
        """
        Initialize memory service.

        Args:
            embeddings_service: Embeddings service for semantic search
        """
        self.embeddings_service = embeddings_service

    async def store_memory(
        self,
        db: AsyncSession,
        content: str,
        memory_type: str,
        metadata: Optional[Dict] = None,
        document_id: Optional[str] = None,
    ) -> str:
        """
        Store a memory entry.

        Args:
            db: Database session
            content: Memory content (summary, insight, etc.)
            memory_type: Type of memory (summary, insight, topic, etc.)
            metadata: Additional metadata
            document_id: Associated document ID

        Returns:
            str: Memory entry ID
        """
        memory_id = str(uuid4())

        # Create memory document
        memory_doc = RawDocument(
            title=f"Memory: {memory_type}",
            content=content,
            source_type="memory",
            external_id=memory_id,
            metadata={
                "memory_type": memory_type,
                "document_id": document_id,
                "stored_at": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
        )

        db.add(memory_doc)
        await db.commit()
        await db.refresh(memory_doc)

        # Generate and store embedding
        if self.embeddings_service:
            try:
                embedding = await self.embeddings_service.generate_embedding(content)
                await self.embeddings_service.store_embedding(
                    document_id=memory_id,
                    embedding=embedding,
                    metadata={
                        "memory_type": memory_type,
                        "document_id": document_id,
                        "stored_at": datetime.utcnow().isoformat(),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to store embedding for memory: {e}")

        logger.info(f"Stored memory entry: {memory_id} (type: {memory_type})")
        return memory_id

    async def search_memory(
        self,
        db: AsyncSession,
        query: str,
        memory_types: Optional[List[str]] = None,
        time_range_days: Optional[int] = None,
        top_k: int = 10,
    ) -> List[Dict]:
        """
        Search memory using semantic search.

        Args:
            db: Database session
            query: Search query
            memory_types: Filter by memory types
            time_range_days: Limit to recent memories (days)
            top_k: Number of results

        Returns:
            List[Dict]: Search results with relevance scores
        """
        if not self.embeddings_service:
            # Fallback to text search
            return await self._text_search_memory(db, query, memory_types, time_range_days, top_k)

        try:
            # Generate query embedding
            query_embedding = await self.embeddings_service.generate_embedding(query)

            # Build metadata filter
            filter_metadata = {}
            if memory_types:
                filter_metadata["memory_type"] = {"$in": memory_types}

            # Search vector database
            results = await self.embeddings_service.search_similar(
                query_embedding=query_embedding,
                top_k=top_k * 2,  # Get more results for time filtering
                filter_metadata=filter_metadata
            )

            # Fetch full memory documents
            memory_ids = [doc_id for doc_id, _, _ in results]
            stmt = select(RawDocument).where(
                RawDocument.external_id.in_(memory_ids),
                RawDocument.source_type == "memory"
            )

            if time_range_days:
                cutoff_date = datetime.utcnow() - timedelta(days=time_range_days)
                stmt = stmt.where(RawDocument.created_at >= cutoff_date)

            result = await db.execute(stmt)
            memory_docs = result.scalars().all()

            # Combine with scores and apply time-aware relevance
            memory_dict = {doc.external_id: doc for doc in memory_docs}
            scored_results = []

            for doc_id, score, _ in results:
                if doc_id in memory_dict:
                    doc = memory_dict[doc_id]
                    # Apply time decay
                    time_score = self._calculate_time_relevance(doc.created_at)
                    final_score = score * time_score

                    scored_results.append({
                        "memory_id": doc_id,
                        "content": doc.content,
                        "metadata": doc.metadata,
                        "relevance_score": final_score,
                        "semantic_score": score,
                        "time_score": time_score,
                        "created_at": doc.created_at.isoformat(),
                    })

            # Sort by final score and return top_k
            scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
            return scored_results[:top_k]

        except Exception as e:
            logger.error(f"Memory search failed: {e}", exc_info=True)
            return await self._text_search_memory(db, query, memory_types, time_range_days, top_k)

    async def _text_search_memory(
        self,
        db: AsyncSession,
        query: str,
        memory_types: Optional[List[str]],
        time_range_days: Optional[int],
        top_k: int,
    ) -> List[Dict]:
        """Fallback text-based memory search."""
        stmt = select(RawDocument).where(
            RawDocument.source_type == "memory",
            RawDocument.content.ilike(f"%{query}%")
        )

        if memory_types:
            # Filter by memory type in metadata
            for mem_type in memory_types:
                stmt = stmt.where(RawDocument.metadata.contains({"memory_type": mem_type}))

        if time_range_days:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range_days)
            stmt = stmt.where(RawDocument.created_at >= cutoff_date)

        stmt = stmt.order_by(RawDocument.created_at.desc()).limit(top_k)

        result = await db.execute(stmt)
        memory_docs = result.scalars().all()

        return [
            {
                "memory_id": doc.external_id,
                "content": doc.content,
                "metadata": doc.metadata,
                "relevance_score": 0.5,  # Default score for text search
                "created_at": doc.created_at.isoformat(),
            }
            for doc in memory_docs
        ]

    def _calculate_time_relevance(self, created_at: datetime) -> float:
        """
        Calculate time-based relevance score.

        More recent memories get higher scores.

        Args:
            created_at: Memory creation timestamp

        Returns:
            float: Time relevance score (0.0 to 1.0)
        """
        age_days = (datetime.utcnow() - created_at).days

        # Exponential decay: recent memories (0-7 days) get full score
        if age_days <= 7:
            return 1.0
        elif age_days <= 30:
            return 0.8
        elif age_days <= 90:
            return 0.6
        elif age_days <= 180:
            return 0.4
        else:
            return 0.2

    async def get_context_for_query(
        self,
        db: AsyncSession,
        query: str,
        max_context_items: int = 5,
    ) -> str:
        """
        Get relevant context from memory for a query.

        Args:
            db: Database session
            query: Query to get context for
            max_context_items: Maximum context items to retrieve

        Returns:
            str: Formatted context string
        """
        memories = await self.search_memory(
            db=db,
            query=query,
            top_k=max_context_items
        )

        if not memories:
            return ""

        context_parts = ["Relevant historical context:"]
        for i, memory in enumerate(memories, 1):
            context_parts.append(
                f"{i}. {memory['content'][:200]}... "
                f"(relevance: {memory['relevance_score']:.2f})"
            )

        return "\n".join(context_parts)

    async def clear_old_memories(
        self,
        db: AsyncSession,
        days_to_keep: int = 365,
    ) -> int:
        """
        Clear memories older than specified days.

        Args:
            db: Database session
            days_to_keep: Number of days to keep

        Returns:
            int: Number of memories deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        stmt = select(RawDocument).where(
            RawDocument.source_type == "memory",
            RawDocument.created_at < cutoff_date
        )

        result = await db.execute(stmt)
        old_memories = result.scalars().all()

        count = len(old_memories)
        for memory in old_memories:
            await db.delete(memory)

        await db.commit()

        logger.info(f"Cleared {count} old memories (older than {days_to_keep} days)")
        return count
