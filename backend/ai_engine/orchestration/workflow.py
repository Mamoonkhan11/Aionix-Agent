"""
Autonomous AI Workflow Orchestration.

Coordinates the complete document processing pipeline:
- Fetch unprocessed documents
- Preprocess
- Topic extraction
- Summarization
- Insight generation
- Store results & embeddings
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ai_engine.chains import InsightGenerationChain, SummarizationChain, TopicExtractionChain
from ai_engine.embeddings import EmbeddingsService
from ai_engine.memory import MemoryService
from ai_engine.processors import DocumentProcessor
from ai_engine.schemas import DocumentProcessingResult, ProcessingError, ProcessingMetadata
from db import get_db
from models import RawDocument

logger = logging.getLogger(__name__)


class DocumentProcessingWorkflow:
    """
    Orchestrates the complete document processing workflow.
    """

    def __init__(
        self,
        llm_client=None,
        embeddings_service: Optional[EmbeddingsService] = None,
        memory_service: Optional[MemoryService] = None,
    ):
        """
        Initialize workflow.

        Args:
            llm_client: LLM client instance
            embeddings_service: Embeddings service
            memory_service: Memory service
        """
        self.topic_chain = TopicExtractionChain(llm_client=llm_client)
        self.summarization_chain = SummarizationChain(llm_client=llm_client)
        self.insight_chain = InsightGenerationChain(llm_client=llm_client)
        self.document_processor = DocumentProcessor()
        self.embeddings_service = embeddings_service
        self.memory_service = memory_service

    async def process_document(
        self,
        document_id: str,
        db: AsyncSession,
        include_insights: bool = True,
        include_topics: bool = True,
        include_summary: bool = True,
    ) -> DocumentProcessingResult:
        """
        Process a single document through the complete pipeline.

        Args:
            document_id: Document ID to process
            db: Database session
            include_insights: Whether to generate insights
            include_topics: Whether to extract topics
            include_summary: Whether to generate summary

        Returns:
            DocumentProcessingResult: Complete processing result
        """
        start_time = time.time()
        errors = []
        operation_id = str(uuid4())

        try:
            # Fetch document
            document = await db.get(RawDocument, document_id)
            if not document:
                raise ValueError(f"Document not found: {document_id}")

            logger.info(f"Starting processing for document: {document_id}")

            # Step 1: Preprocess document
            chunks = self.document_processor.process_document(
                content=document.content,
                metadata={
                    "document_id": str(document.id),
                    "source_type": document.source_type,
                    "title": document.title,
                }
            )

            # Step 2: Extract topics
            topics_result = None
            if include_topics:
                try:
                    if len(chunks) > 1:
                        chunk_texts = [chunk.content for chunk in chunks]
                        topics_result = await self.topic_chain.extract_from_chunks(chunk_texts)
                    else:
                        topics_result = await self.topic_chain.extract_topics(document.content)

                    logger.info(f"Extracted {len(topics_result.topics)} topics")
                except Exception as e:
                    logger.error(f"Topic extraction failed: {e}", exc_info=True)
                    errors.append(ProcessingError(
                        error_type="TopicExtractionError",
                        message=str(e),
                        step="topic_extraction",
                        document_id=document.id,
                    ))

            # Step 3: Generate summaries
            summary_result = None
            executive_summary = None
            if include_summary:
                try:
                    if len(chunks) > 1:
                        chunk_summaries = await self.summarization_chain.summarize_chunks(
                            [chunk.content for chunk in chunks]
                        )
                        summary_result = await self.summarization_chain.create_global_summary(
                            chunk_summaries
                        )
                    else:
                        summary_result = await self.summarization_chain.summarize(document.content)

                    executive_summary = await self.summarization_chain.create_executive_summary(
                        document.content
                    )

                    logger.info("Generated summaries")
                except Exception as e:
                    logger.error(f"Summarization failed: {e}", exc_info=True)
                    errors.append(ProcessingError(
                        error_type="SummarizationError",
                        message=str(e),
                        step="summarization",
                        document_id=document.id,
                    ))

            # Step 4: Generate insights
            insights_result = None
            if include_insights:
                try:
                    # Get context from memory if available
                    context = None
                    if self.memory_service:
                        context_text = await self.memory_service.get_context_for_query(
                            db=db,
                            query=document.title or document.content[:200],
                            max_context_items=3
                        )
                        if context_text:
                            context = {"historical_context": context_text}

                    document_texts = [chunk.content for chunk in chunks[:5]]  # Limit chunks
                    insights_result = await self.insight_chain.generate_insights(
                        documents=document_texts,
                        context=context
                    )

                    logger.info(f"Generated {len(insights_result.recommendations)} recommendations")
                except Exception as e:
                    logger.error(f"Insight generation failed: {e}", exc_info=True)
                    errors.append(ProcessingError(
                        error_type="InsightGenerationError",
                        message=str(e),
                        step="insight_generation",
                        document_id=document.id,
                    ))

            # Step 5: Generate and store embeddings
            if self.embeddings_service:
                try:
                    # Generate embedding for document
                    embedding = await self.embeddings_service.generate_embedding(document.content)
                    await self.embeddings_service.store_embedding(
                        document_id=str(document.id),
                        embedding=embedding,
                        metadata={
                            "title": document.title,
                            "source_type": document.source_type,
                            "processed_at": datetime.utcnow().isoformat(),
                        }
                    )
                    logger.info("Stored document embedding")
                except Exception as e:
                    logger.warning(f"Failed to store embedding: {e}")

            # Step 6: Store results in memory
            if self.memory_service:
                try:
                    if summary_result:
                        await self.memory_service.store_memory(
                            db=db,
                            content=summary_result.summary,
                            memory_type="summary",
                            document_id=str(document.id),
                            metadata={"title": document.title}
                        )

                    if insights_result:
                        insights_text = f"Trends: {len(insights_result.trends)}, "
                        insights_text += f"Risks: {len(insights_result.risks)}, "
                        insights_text += f"Opportunities: {len(insights_result.opportunities)}"
                        await self.memory_service.store_memory(
                            db=db,
                            content=insights_text,
                            memory_type="insight",
                            document_id=str(document.id),
                        )
                except Exception as e:
                    logger.warning(f"Failed to store in memory: {e}")

            # Step 7: Mark document as processed
            document.processed = True
            await db.commit()

            # Create processing metadata
            processing_time = time.time() - start_time
            metadata = ProcessingMetadata(
                model_used=self.topic_chain.llm_client.model,
                tokens_used=None,  # Can be extracted from LLM response if available
                processing_time=processing_time,
                input_sources=[str(document.id)],
                confidence_scores={
                    "topics": topics_result.confidence if topics_result else 0.0,
                    "summary": summary_result.confidence if summary_result else 0.0,
                    "insights": insights_result.confidence if insights_result else 0.0,
                }
            )

            # Determine status
            status = "success"
            if errors:
                status = "partial" if (topics_result or summary_result or insights_result) else "failed"

            result = DocumentProcessingResult(
                document_id=document.id,
                topics=topics_result,
                summary=summary_result,
                executive_summary=executive_summary,
                insights=insights_result,
                metadata=metadata,
                errors=errors,
                status=status,
            )

            logger.info(
                f"Completed processing for document: {document_id} "
                f"(status: {status}, time: {processing_time:.2f}s)"
            )

            return result

        except Exception as e:
            logger.error(f"Document processing failed: {e}", exc_info=True)
            errors.append(ProcessingError(
                error_type=type(e).__name__,
                message=str(e),
                step="workflow",
                document_id=document_id,
            ))

            # Return failed result
            return DocumentProcessingResult(
                document_id=document_id,
                metadata=ProcessingMetadata(
                    model_used="unknown",
                    processing_time=time.time() - start_time,
                    input_sources=[document_id],
                ),
                errors=errors,
                status="failed",
            )

    async def process_unprocessed_documents(
        self,
        db: AsyncSession,
        limit: int = 10,
        **kwargs
    ) -> List[DocumentProcessingResult]:
        """
        Process all unprocessed documents.

        Args:
            db: Database session
            limit: Maximum number of documents to process
            **kwargs: Additional processing options

        Returns:
            List[DocumentProcessingResult]: Processing results
        """
        # Fetch unprocessed documents
        stmt = select(RawDocument).where(
            RawDocument.processed == False
        ).limit(limit)

        result = await db.execute(stmt)
        documents = result.scalars().all()

        logger.info(f"Found {len(documents)} unprocessed documents")

        # Process each document
        results = []
        for document in documents:
            try:
                result = await self.process_document(
                    document_id=str(document.id),
                    db=db,
                    **kwargs
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process document {document.id}: {e}")

        return results
