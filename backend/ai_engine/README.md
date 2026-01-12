# AI Engine Module

The AI Engine module provides a comprehensive, production-ready AI processing system for the Aionix Agent backend. It follows clean architecture principles with clear separation of concerns.

## Architecture Overview

```
ai_engine/
├── chains/           # LangChain processing chains
├── prompts/          # Prompt templates and management
├── embeddings/       # Vector embedding generation and storage
├── memory/           # Long-term memory and semantic search
├── processors/       # Document preprocessing and transformation
└── orchestration/   # Workflow orchestration and task management
```

## Module Responsibilities

### `chains/`
Contains LangChain-based processing chains for:
- Topic extraction chains
- Multi-level summarization chains
- Insight generation chains
- Document analysis chains

**Purpose**: Reusable, composable processing pipelines that can be combined to create complex AI workflows.

### `prompts/`
Manages all prompt templates and prompt engineering:
- Topic extraction prompts
- Summarization prompts
- Insight generation prompts
- System prompts and instructions

**Purpose**: Centralized prompt management for consistency, versioning, and easy updates.

### `embeddings/`
Handles vector embedding operations:
- Embedding generation (OpenAI, Hugging Face)
- Vector database integration (Pinecone, Weaviate)
- Batch embedding operations
- Similarity search

**Purpose**: Enable semantic search and document similarity matching.

### `memory/`
Implements long-term memory for the AI system:
- Historical data storage
- Semantic search over past insights
- Context retrieval for improved responses
- Time-aware relevance scoring

**Purpose**: Enable the AI to learn from past interactions and maintain context over time.

### `processors/`
Document preprocessing and transformation:
- Text cleaning and normalization
- Document chunking
- Metadata preservation
- Token-aware splitting

**Purpose**: Prepare raw documents for AI processing with optimal chunk sizes and clean data.

### `orchestration/`
Workflow orchestration and task management:
- Autonomous AI workflows
- Background task processing
- Task status tracking
- Failure recovery and retry logic

**Purpose**: Coordinate complex multi-step AI processes and manage async execution.

## Key Features

- **Unified LLM Client**: Single abstraction supporting OpenAI and Hugging Face
- **Async Processing**: Full async/await support for high performance
- **Enterprise-Ready**: Audit logging, explainability, compliance features
- **Extensible**: Easy to add new models, chains, and processors
- **Production-Grade**: Error handling, retries, monitoring

## Usage Example

```python
from ai_engine.orchestration.workflow import DocumentProcessingWorkflow
from ai_engine.llm_client import LLMClient

# Initialize workflow
workflow = DocumentProcessingWorkflow()

# Process a document
result = await workflow.process_document(
    document_id="doc-123",
    include_insights=True
)
```

## Dependencies

- `langchain`: Chain orchestration
- `openai`: OpenAI API client
- `transformers`: Hugging Face models
- `pinecone-client` or `weaviate-client`: Vector databases
- `celery`: Background task processing (optional)

## Configuration

All AI Engine settings are configured via environment variables in `backend/.env`:

```bash
# LLM Configuration
OPENAI_API_KEY=your_key
HUGGINGFACE_API_KEY=your_key
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4

# Vector Database
VECTOR_DB_PROVIDER=pinecone
PINECONE_API_KEY=your_key
WEAVIATE_URL=your_url

# Processing Settings
MAX_CHUNK_SIZE=2000
CHUNK_OVERLAP=200
ENABLE_MEMORY=true
```

## Testing

Run AI Engine tests:
```bash
cd backend
pytest tests/unit/test_ai_engine.py
pytest tests/integration/test_ai_workflows.py
```
