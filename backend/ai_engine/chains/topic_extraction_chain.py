"""
Topic Extraction Chain using LangChain.

Extracts topics, entities, and relationships from documents using LLMs.
"""

import json
import logging
from typing import Dict, List, Optional

from ai_engine.llm_client import LLMClient, create_llm_client
from ai_engine.prompts.prompt_manager import prompt_manager
from ai_engine.schemas import TopicExtractionResult

logger = logging.getLogger(__name__)


class TopicExtractionChain:
    """
    Chain for extracting topics, entities, and relationships from documents.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize topic extraction chain.

        Args:
            llm_client: LLM client instance (optional)
            model: Model identifier (optional)
        """
        self.llm_client = llm_client or create_llm_client(model=model)
        self.prompt_template = prompt_manager.get_template("topic_extraction")

    async def extract_topics(
        self,
        document: str,
        chunk_analyses: Optional[List[Dict]] = None,
    ) -> TopicExtractionResult:
        """
        Extract topics from a document.

        Args:
            document: Document content
            chunk_analyses: Optional pre-analyzed chunks for aggregation

        Returns:
            TopicExtractionResult: Extracted topics and entities
        """
        try:
            # Format prompt
            prompt = prompt_manager.format_prompt(
                "topic_extraction",
                document=document[:10000]  # Limit document size
            )

            # Define expected schema
            schema = {
                "type": "object",
                "properties": {
                    "topics": {"type": "array", "items": {"type": "string"}},
                    "entities": {
                        "type": "object",
                        "properties": {
                            "people": {"type": "array", "items": {"type": "string"}},
                            "organizations": {"type": "array", "items": {"type": "string"}},
                            "locations": {"type": "array", "items": {"type": "string"}},
                            "concepts": {"type": "array", "items": {"type": "string"}},
                        }
                    },
                    "key_dates": {"type": "array", "items": {"type": "string"}},
                    "themes": {"type": "array", "items": {"type": "string"}},
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                                "relationship": {"type": "string"}
                            }
                        }
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["topics", "entities", "confidence"]
            }

            # Generate structured output
            result = await self.llm_client.generate_structured(
                prompt=prompt,
                schema=schema,
                system_prompt="You are an expert information extraction system. Extract topics, entities, and relationships accurately."
            )

            # Convert to TopicExtractionResult
            return TopicExtractionResult(**result)

        except Exception as e:
            logger.error(f"Topic extraction failed: {e}", exc_info=True)
            # Return empty result on error
            return TopicExtractionResult(
                topics=[],
                entities={},
                confidence=0.0,
                processing_metadata={"error": str(e)}
            )

    async def extract_from_chunks(
        self,
        chunks: List[str],
    ) -> TopicExtractionResult:
        """
        Extract topics from multiple chunks and aggregate results.

        Args:
            chunks: List of document chunks

        Returns:
            TopicExtractionResult: Aggregated topics and entities
        """
        # Extract topics from each chunk
        chunk_results = []
        for chunk in chunks:
            result = await self.extract_topics(chunk)
            chunk_results.append(result)

        # Aggregate results
        all_topics = set()
        all_entities = {
            "people": set(),
            "organizations": set(),
            "locations": set(),
            "concepts": set(),
        }
        all_dates = set()
        all_themes = set()
        all_relationships = []

        for result in chunk_results:
            all_topics.update(result.topics)
            for entity_type, entities in result.entities.items():
                if entity_type in all_entities:
                    all_entities[entity_type].update(entities)
            all_dates.update(result.key_dates)
            all_themes.update(result.themes)
            all_relationships.extend(result.relationships)

        # Calculate average confidence
        avg_confidence = (
            sum(r.confidence for r in chunk_results) / len(chunk_results)
            if chunk_results else 0.0
        )

        return TopicExtractionResult(
            topics=list(all_topics),
            entities={k: list(v) for k, v in all_entities.items()},
            key_dates=list(all_dates),
            themes=list(all_themes),
            relationships=all_relationships,
            confidence=avg_confidence,
        )
