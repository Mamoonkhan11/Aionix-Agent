"""
Insight Generation Chain using LangChain.

Generates business insights including trends, risks, opportunities, and recommendations.
"""

import json
import logging
from typing import Dict, List, Optional

from ai_engine.llm_client import LLMClient, create_llm_client
from ai_engine.prompts.prompt_manager import prompt_manager
from ai_engine.schemas import InsightResult

logger = logging.getLogger(__name__)


class InsightGenerationChain:
    """
    Chain for generating business insights from documents.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize insight generation chain.

        Args:
            llm_client: LLM client instance (optional)
            model: Model identifier (optional)
        """
        self.llm_client = llm_client or create_llm_client(model=model)

    async def generate_insights(
        self,
        documents: List[str],
        context: Optional[Dict] = None,
    ) -> InsightResult:
        """
        Generate insights from documents.

        Args:
            documents: List of document contents
            context: Optional context information

        Returns:
            InsightResult: Generated insights
        """
        try:
            # Combine documents
            combined_docs = "\n\n---\n\n".join(documents[:5])  # Limit to 5 documents

            context_str = ""
            if context:
                context_str = f"Context: {json.dumps(context, indent=2)}"

            prompt = prompt_manager.format_prompt(
                "insight_generation",
                documents=combined_docs[:15000],  # Limit size
                context=context_str
            )

            # Define schema for structured output
            schema = {
                "type": "object",
                "properties": {
                    "trends": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "impact": {"type": "string"},
                                "evidence": {"type": "string"}
                            }
                        }
                    },
                    "risks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "severity": {"type": "string"},
                                "mitigation": {"type": "string"}
                            }
                        }
                    },
                    "opportunities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "potential_value": {"type": "string"},
                                "action_items": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    },
                    "recommendations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "priority": {"type": "string"},
                                "timeline": {"type": "string"}
                            }
                        }
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["trends", "risks", "opportunities", "recommendations", "confidence"]
            }

            result = await self.llm_client.generate_structured(
                prompt=prompt,
                schema=schema,
                system_prompt="You are an expert business analyst. Provide actionable, evidence-based insights."
            )

            return InsightResult(**result)

        except Exception as e:
            logger.error(f"Insight generation failed: {e}", exc_info=True)
            # Return empty insights on error
            return InsightResult(
                trends=[],
                risks=[],
                opportunities=[],
                recommendations=[],
                confidence=0.0,
                processing_metadata={"error": str(e)}
            )
