"""
Document Preprocessing Pipeline.

Handles text cleaning, chunking, and metadata preservation
for optimal AI processing.
"""

import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import tiktoken

logger = logging.getLogger(__name__)


class ChunkingStrategy(str, Enum):
    """Document chunking strategies."""

    FIXED_SIZE = "fixed_size"
    SENTENCE_AWARE = "sentence_aware"
    PARAGRAPH_AWARE = "paragraph_aware"
    TOKEN_AWARE = "token_aware"


class DocumentChunk:
    """Represents a processed document chunk."""

    def __init__(
        self,
        content: str,
        chunk_index: int,
        metadata: Optional[Dict] = None,
        token_count: Optional[int] = None,
    ):
        """
        Initialize document chunk.

        Args:
            content: Chunk text content
            chunk_index: Index of chunk in document
            metadata: Additional metadata
            token_count: Number of tokens in chunk
        """
        self.id = str(uuid4())
        self.content = content
        self.chunk_index = chunk_index
        self.metadata = metadata or {}
        self.token_count = token_count or 0

    def to_dict(self) -> Dict:
        """Convert chunk to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
            "token_count": self.token_count,
        }


class DocumentProcessor:
    """
    Document preprocessing pipeline.

    Handles text cleaning, chunking, and metadata preservation.
    """

    def __init__(
        self,
        max_chunk_size: int = 2000,
        chunk_overlap: int = 200,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.TOKEN_AWARE,
        encoding_name: str = "cl100k_base",  # GPT-4 tokenizer
    ):
        """
        Initialize document processor.

        Args:
            max_chunk_size: Maximum chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
            chunking_strategy: Chunking strategy to use
            encoding_name: Tokenizer encoding name
        """
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunking_strategy = chunking_strategy

        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            logger.warning(f"Failed to load encoding {encoding_name}, using fallback")
            self.encoding = None

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Raw text to clean

        Returns:
            str: Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but preserve punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\'\"]', '', text)

        # Normalize line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            int: Token count
        """
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Fallback: approximate token count (1 token ≈ 4 characters)
            return len(text) // 4

    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List[str]: List of sentences
        """
        # Simple sentence splitting (can be enhanced with NLTK/spaCy)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs.

        Args:
            text: Text to split

        Returns:
            List[str]: List of paragraphs
        """
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]

    def chunk_fixed_size(self, text: str, metadata: Optional[Dict] = None) -> List[DocumentChunk]:
        """
        Chunk text into fixed-size chunks.

        Args:
            text: Text to chunk
            metadata: Document metadata

        Returns:
            List[DocumentChunk]: List of document chunks
        """
        chunks = []
        chunk_size = self.max_chunk_size - self.chunk_overlap

        for i in range(0, len(text), chunk_size):
            start = max(0, i - self.chunk_overlap)
            end = min(len(text), i + chunk_size)
            chunk_text = text[start:end]

            token_count = self.count_tokens(chunk_text)
            chunk = DocumentChunk(
                content=chunk_text,
                chunk_index=len(chunks),
                metadata={**(metadata or {}), "strategy": "fixed_size"},
                token_count=token_count,
            )
            chunks.append(chunk)

        return chunks

    def chunk_sentence_aware(self, text: str, metadata: Optional[Dict] = None) -> List[DocumentChunk]:
        """
        Chunk text preserving sentence boundaries.

        Args:
            text: Text to chunk
            metadata: Document metadata

        Returns:
            List[DocumentChunk]: List of document chunks
        """
        sentences = self.split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            if current_tokens + sentence_tokens > self.max_chunk_size and current_chunk:
                # Create chunk from accumulated sentences
                chunk_text = ' '.join(current_chunk)
                token_count = self.count_tokens(chunk_text)
                chunk = DocumentChunk(
                    content=chunk_text,
                    chunk_index=len(chunks),
                    metadata={**(metadata or {}), "strategy": "sentence_aware"},
                    token_count=token_count,
                )
                chunks.append(chunk)

                # Keep overlap sentences
                overlap_tokens = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    s_tokens = self.count_tokens(s)
                    if overlap_tokens + s_tokens <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break

                current_chunk = overlap_sentences + [sentence]
                current_tokens = overlap_tokens + sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add remaining sentences as final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            token_count = self.count_tokens(chunk_text)
            chunk = DocumentChunk(
                content=chunk_text,
                chunk_index=len(chunks),
                metadata={**(metadata or {}), "strategy": "sentence_aware"},
                token_count=token_count,
            )
            chunks.append(chunk)

        return chunks

    def chunk_token_aware(self, text: str, metadata: Optional[Dict] = None) -> List[DocumentChunk]:
        """
        Chunk text with token-aware splitting.

        Args:
            text: Text to chunk
            metadata: Document metadata

        Returns:
            List[DocumentChunk]: List of document chunks
        """
        # Use sentence-aware chunking but with token limits
        return self.chunk_sentence_aware(text, metadata)

    def process_document(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        preserve_metadata: bool = True,
    ) -> List[DocumentChunk]:
        """
        Process a document through the full pipeline.

        Args:
            content: Document content
            metadata: Document metadata
            preserve_metadata: Whether to preserve metadata in chunks

        Returns:
            List[DocumentChunk]: Processed document chunks
        """
        # Clean text
        cleaned_content = self.clean_text(content)

        # Prepare chunk metadata
        chunk_metadata = {}
        if preserve_metadata and metadata:
            chunk_metadata = {
                "original_metadata": metadata,
                "document_id": metadata.get("document_id"),
                "source_type": metadata.get("source_type"),
                "title": metadata.get("title"),
            }

        # Chunk based on strategy
        if self.chunking_strategy == ChunkingStrategy.FIXED_SIZE:
            chunks = self.chunk_fixed_size(cleaned_content, chunk_metadata)
        elif self.chunking_strategy == ChunkingStrategy.SENTENCE_AWARE:
            chunks = self.chunk_sentence_aware(cleaned_content, chunk_metadata)
        elif self.chunking_strategy == ChunkingStrategy.PARAGRAPH_AWARE:
            # Use paragraph-aware chunking (similar to sentence-aware)
            chunks = self.chunk_sentence_aware(cleaned_content, chunk_metadata)
        elif self.chunking_strategy == ChunkingStrategy.TOKEN_AWARE:
            chunks = self.chunk_token_aware(cleaned_content, chunk_metadata)
        else:
            chunks = self.chunk_token_aware(cleaned_content, chunk_metadata)

        logger.info(
            f"Processed document into {len(chunks)} chunks",
            extra={
                "chunk_count": len(chunks),
                "strategy": self.chunking_strategy,
                "total_tokens": sum(c.token_count for c in chunks),
            }
        )

        return chunks
