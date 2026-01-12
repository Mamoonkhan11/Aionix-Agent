"""
Vector Embeddings Service.

Generates embeddings using OpenAI or Hugging Face and stores them
in vector databases (Pinecone or Weaviate).
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple

from core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""

    OPENAI = "openai"
    HUGGINGFACE = "huggingface"


class VectorDBProvider(str, Enum):
    """Supported vector database providers."""

    PINECONE = "pinecone"
    WEAVIATE = "weaviate"


class EmbeddingsService:
    """
    Service for generating and storing vector embeddings.
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_db_provider: Optional[VectorDBProvider] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize embeddings service.

        Args:
            embedding_provider: Provider for embeddings (openai, huggingface)
            vector_db_provider: Vector database provider (pinecone, weaviate)
            model: Embedding model identifier
        """
        self.embedding_provider = embedding_provider or EmbeddingProvider.OPENAI
        self.vector_db_provider = vector_db_provider or VectorDBProvider.PINECONE

        if self.embedding_provider == EmbeddingProvider.OPENAI:
            self._init_openai(model)
        elif self.embedding_provider == EmbeddingProvider.HUGGINGFACE:
            self._init_huggingface(model)

        if self.vector_db_provider == VectorDBProvider.PINECONE:
            self._init_pinecone()
        elif self.vector_db_provider == VectorDBProvider.WEAVIATE:
            self._init_weaviate()

    def _init_openai(self, model: Optional[str] = None):
        """Initialize OpenAI embeddings."""
        try:
            import openai

            self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            self.embedding_model = model or "text-embedding-3-small"
            logger.info(f"Initialized OpenAI embeddings with model: {self.embedding_model}")
        except ImportError:
            raise ImportError("openai package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embeddings: {e}")
            raise

    def _init_huggingface(self, model: Optional[str] = None):
        """Initialize Hugging Face embeddings."""
        try:
            from sentence_transformers import SentenceTransformer

            self.embedding_model = model or "all-MiniLM-L6-v2"
            self.hf_model = SentenceTransformer(self.embedding_model)
            logger.info(f"Initialized Hugging Face embeddings with model: {self.embedding_model}")
        except ImportError:
            raise ImportError("sentence-transformers package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Hugging Face embeddings: {e}")
            raise

    def _init_pinecone(self):
        """Initialize Pinecone vector database."""
        try:
            import pinecone

            api_key = getattr(settings, "pinecone_api_key", None)
            if not api_key:
                raise ValueError("Pinecone API key not configured")

            self.pinecone_client = pinecone.Pinecone(api_key=api_key)
            self.index_name = getattr(settings, "pinecone_index_name", "aionix-documents")
            logger.info(f"Initialized Pinecone with index: {self.index_name}")
        except ImportError:
            raise ImportError("pinecone-client package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise

    def _init_weaviate(self):
        """Initialize Weaviate vector database."""
        try:
            import weaviate

            url = getattr(settings, "weaviate_url", "http://localhost:8080")
            self.weaviate_client = weaviate.Client(url=url)
            self.class_name = getattr(settings, "weaviate_class_name", "Document")
            logger.info(f"Initialized Weaviate with class: {self.class_name}")
        except ImportError:
            raise ImportError("weaviate-client package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {e}")
            raise

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List[float]: Embedding vector
        """
        if self.embedding_provider == EmbeddingProvider.OPENAI:
            return await self._generate_openai_embedding(text)
        elif self.embedding_provider == EmbeddingProvider.HUGGINGFACE:
            return await self._generate_huggingface_embedding(text)

    async def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise

    async def _generate_huggingface_embedding(self, text: str) -> List[float]:
        """Generate embedding using Hugging Face."""
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.hf_model.encode(text, convert_to_numpy=True)
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Hugging Face embedding generation failed: {e}")
            raise

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            List[List[float]]: List of embedding vectors
        """
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            if self.embedding_provider == EmbeddingProvider.OPENAI:
                batch_embeddings = await self._generate_openai_embeddings_batch(batch)
            else:
                batch_embeddings = await self._generate_huggingface_embeddings_batch(batch)
            embeddings.extend(batch_embeddings)
        return embeddings

    async def _generate_openai_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings batch using OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI batch embedding generation failed: {e}")
            raise

    async def _generate_huggingface_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings batch using Hugging Face."""
        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.hf_model.encode(texts, convert_to_numpy=True)
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Hugging Face batch embedding generation failed: {e}")
            raise

    async def store_embedding(
        self,
        document_id: str,
        embedding: List[float],
        metadata: Optional[Dict] = None,
    ):
        """
        Store embedding in vector database.

        Args:
            document_id: Document identifier
            embedding: Embedding vector
            metadata: Additional metadata
        """
        if self.vector_db_provider == VectorDBProvider.PINECONE:
            await self._store_pinecone(document_id, embedding, metadata)
        elif self.vector_db_provider == VectorDBProvider.WEAVIATE:
            await self._store_weaviate(document_id, embedding, metadata)

    async def _store_pinecone(
        self,
        document_id: str,
        embedding: List[float],
        metadata: Optional[Dict] = None,
    ):
        """Store embedding in Pinecone."""
        try:
            index = self.pinecone_client.Index(self.index_name)
            await index.upsert(
                vectors=[{
                    "id": document_id,
                    "values": embedding,
                    "metadata": metadata or {}
                }]
            )
            logger.info(f"Stored embedding in Pinecone for document: {document_id}")
        except Exception as e:
            logger.error(f"Failed to store embedding in Pinecone: {e}")
            raise

    async def _store_weaviate(
        self,
        document_id: str,
        embedding: List[float],
        metadata: Optional[Dict] = None,
    ):
        """Store embedding in Weaviate."""
        try:
            data_object = {
                "document_id": document_id,
                **(metadata or {})
            }
            self.weaviate_client.data_object.create(
                data_object=data_object,
                class_name=self.class_name,
                vector=embedding
            )
            logger.info(f"Stored embedding in Weaviate for document: {document_id}")
        except Exception as e:
            logger.error(f"Failed to store embedding in Weaviate: {e}")
            raise

    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar documents.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List[Tuple[str, float, Dict]]: List of (document_id, score, metadata) tuples
        """
        if self.vector_db_provider == VectorDBProvider.PINECONE:
            return await self._search_pinecone(query_embedding, top_k, filter_metadata)
        elif self.vector_db_provider == VectorDBProvider.WEAVIATE:
            return await self._search_weaviate(query_embedding, top_k, filter_metadata)

    async def _search_pinecone(
        self,
        query_embedding: List[float],
        top_k: int,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Tuple[str, float, Dict]]:
        """Search Pinecone for similar documents."""
        try:
            index = self.pinecone_client.Index(self.index_name)
            results = await index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_metadata
            )
            return [
                (match.id, match.score, match.metadata or {})
                for match in results.matches
            ]
        except Exception as e:
            logger.error(f"Pinecone search failed: {e}")
            raise

    async def _search_weaviate(
        self,
        query_embedding: List[float],
        top_k: int,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Tuple[str, float, Dict]]:
        """Search Weaviate for similar documents."""
        try:
            query = self.weaviate_client.query.get(
                self.class_name,
                ["document_id", "_additional {id}"]
            ).with_near_vector({
                "vector": query_embedding
            }).with_limit(top_k)

            if filter_metadata:
                # Add filters (Weaviate filter syntax)
                pass  # Implement filtering as needed

            results = query.do()
            return [
                (
                    item.get("document_id", ""),
                    item.get("_additional", {}).get("certainty", 0.0),
                    item
                )
                for item in results.get("data", {}).get("Get", {}).get(self.class_name, [])
            ]
        except Exception as e:
            logger.error(f"Weaviate search failed: {e}")
            raise
