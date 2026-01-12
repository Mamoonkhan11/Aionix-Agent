"""
Example Usage of AI Engine Components.

This module demonstrates how to use various AI Engine components
for document processing, topic extraction, summarization, and insights.
"""

import asyncio
from ai_engine import create_llm_client
from ai_engine.chains import InsightGenerationChain, SummarizationChain, TopicExtractionChain
from ai_engine.embeddings import EmbeddingsService, EmbeddingProvider, VectorDBProvider
from ai_engine.memory import MemoryService
from ai_engine.orchestration import DocumentProcessingWorkflow, TaskRunner
from ai_engine.processors import DocumentProcessor, ChunkingStrategy
from ai_engine.schemas import DocumentProcessingResult


async def example_topic_extraction():
    """Example: Extract topics from a document."""
    # Create LLM client
    llm_client = create_llm_client("openai", "gpt-4")

    # Create topic extraction chain
    topic_chain = TopicExtractionChain(llm_client=llm_client)

    # Extract topics
    document = """
    Artificial Intelligence is transforming industries across the globe.
    Companies like OpenAI, Google, and Microsoft are leading the charge.
    The technology has applications in healthcare, finance, and education.
    """

    result = await topic_chain.extract_topics(document)

    print("Extracted Topics:")
    print(f"Topics: {result.topics}")
    print(f"Entities: {result.entities}")
    print(f"Confidence: {result.confidence}")


async def example_summarization():
    """Example: Generate summaries."""
    # Create summarization chain
    summarization_chain = SummarizationChain()

    document = """
    [Long document content here...]
    """

    # Generate summary
    summary = await summarization_chain.summarize(document, target_length=200)
    print(f"Summary: {summary.summary}")
    print(f"Word count: {summary.word_count}")

    # Generate executive summary
    exec_summary = await summarization_chain.create_executive_summary(document)
    print(f"Executive Summary: {exec_summary.summary}")
    print(f"Bullet Points: {exec_summary.bullet_points}")


async def example_insight_generation():
    """Example: Generate business insights."""
    # Create insight chain
    insight_chain = InsightGenerationChain()

    documents = [
        "Document 1 content...",
        "Document 2 content...",
    ]

    insights = await insight_chain.generate_insights(documents)

    print("Generated Insights:")
    print(f"Trends: {len(insights.trends)}")
    print(f"Risks: {len(insights.risks)}")
    print(f"Opportunities: {len(insights.opportunities)}")
    print(f"Recommendations: {len(insights.recommendations)}")


async def example_document_processing():
    """Example: Process a document through the complete pipeline."""
    from db import get_db

    # Create workflow
    workflow = DocumentProcessingWorkflow()

    # Get database session
    async for db in get_db():
        # Process document
        result = await workflow.process_document(
            document_id="your-document-id",
            db=db,
            include_insights=True,
            include_topics=True,
            include_summary=True,
        )

        print(f"Processing Status: {result.status}")
        print(f"Topics: {len(result.topics.topics) if result.topics else 0}")
        print(f"Summary: {result.summary.summary[:200] if result.summary else 'N/A'}")
        print(f"Insights: {len(result.insights.recommendations) if result.insights else 0}")

        break


async def example_embeddings():
    """Example: Generate and store embeddings."""
    # Create embeddings service
    embeddings_service = EmbeddingsService(
        embedding_provider=EmbeddingProvider.OPENAI,
        vector_db_provider=VectorDBProvider.PINECONE,
    )

    # Generate embedding
    text = "This is a sample document for embedding."
    embedding = await embeddings_service.generate_embedding(text)
    print(f"Embedding dimension: {len(embedding)}")

    # Store embedding
    await embeddings_service.store_embedding(
        document_id="doc-123",
        embedding=embedding,
        metadata={"title": "Sample Document"}
    )

    # Search for similar documents
    query_embedding = await embeddings_service.generate_embedding("similar document")
    results = await embeddings_service.search_similar(query_embedding, top_k=5)
    print(f"Found {len(results)} similar documents")


async def example_memory_service():
    """Example: Use memory service for context retrieval."""
    from db import get_db
    from ai_engine.embeddings import EmbeddingsService

    # Create memory service
    embeddings_service = EmbeddingsService()
    memory_service = MemoryService(embeddings_service=embeddings_service)

    async for db in get_db():
        # Store a memory
        memory_id = await memory_service.store_memory(
            db=db,
            content="Key insight: AI adoption is increasing rapidly.",
            memory_type="insight",
            metadata={"source": "report-2024"}
        )

        # Search memory
        results = await memory_service.search_memory(
            db=db,
            query="AI trends",
            top_k=5
        )

        print(f"Found {len(results)} relevant memories")

        # Get context for a query
        context = await memory_service.get_context_for_query(
            db=db,
            query="What are the latest AI trends?",
            max_context_items=3
        )
        print(f"Context: {context}")

        break


async def example_background_tasks():
    """Example: Run AI processing as background tasks."""
    from ai_engine.orchestration import TaskRunner

    task_runner = TaskRunner()

    async def process_document_task(document_id: str):
        """Background task to process a document."""
        # Your processing logic here
        await asyncio.sleep(5)  # Simulate processing
        return {"status": "completed", "document_id": document_id}

    # Submit task
    task_id = await task_runner.submit_task(
        func=process_document_task,
        args=("doc-123",),
        max_retries=3
    )

    print(f"Task submitted: {task_id}")

    # Check status
    status = task_runner.get_task_status(task_id)
    print(f"Task status: {status}")

    # Wait for completion
    await asyncio.sleep(6)

    # Get result
    result = task_runner.get_task_result(task_id)
    print(f"Task result: {result}")


async def example_document_preprocessing():
    """Example: Preprocess documents with chunking."""
    # Create processor
    processor = DocumentProcessor(
        max_chunk_size=2000,
        chunk_overlap=200,
        chunking_strategy=ChunkingStrategy.TOKEN_AWARE,
    )

    # Process document
    document_content = """
    [Long document content here...]
    """

    chunks = processor.process_document(
        content=document_content,
        metadata={
            "document_id": "doc-123",
            "title": "Sample Document",
        }
    )

    print(f"Document split into {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i}: {chunk.token_count} tokens")


if __name__ == "__main__":
    # Run examples
    asyncio.run(example_topic_extraction())
    # asyncio.run(example_summarization())
    # asyncio.run(example_insight_generation())
    # asyncio.run(example_embeddings())
    # asyncio.run(example_memory_service())
    # asyncio.run(example_background_tasks())
    # asyncio.run(example_document_preprocessing())
