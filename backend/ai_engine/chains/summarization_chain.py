"""
Multi-level Summarization Chain using LangChain.

Provides chunk-level, document-level, and executive summaries.
"""

import logging
from typing import List, Optional

from ai_engine.llm_client import LLMClient, create_llm_client
from ai_engine.prompts.prompt_manager import prompt_manager
from ai_engine.schemas import ExecutiveSummaryResult, SummaryResult

logger = logging.getLogger(__name__)


class SummarizationChain:
    """
    Chain for generating multi-level summaries.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize summarization chain.

        Args:
            llm_client: LLM client instance (optional)
            model: Model identifier (optional)
        """
        self.llm_client = llm_client or create_llm_client(model=model)

    async def summarize(
        self,
        content: str,
        target_length: int = 200,
    ) -> SummaryResult:
        """
        Generate a summary of the content.

        Args:
            content: Content to summarize
            target_length: Target word count

        Returns:
            SummaryResult: Generated summary
        """
        try:
            prompt = prompt_manager.format_prompt(
                "summarization",
                document=content[:8000],  # Limit content size
                target_length=target_length
            )

            summary_text = await self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are an expert summarizer. Create clear, concise, and comprehensive summaries."
            )

            # Extract key points (simple extraction, can be enhanced)
            sentences = summary_text.split('. ')
            key_points = [s.strip() for s in sentences[:5] if s.strip()]

            word_count = len(summary_text.split())

            return SummaryResult(
                summary=summary_text,
                word_count=word_count,
                key_points=key_points,
                confidence=0.9,  # Can be calculated based on model confidence
            )

        except Exception as e:
            logger.error(f"Summarization failed: {e}", exc_info=True)
            raise

    async def summarize_chunks(
        self,
        chunks: List[str],
    ) -> List[SummaryResult]:
        """
        Summarize multiple chunks.

        Args:
            chunks: List of content chunks

        Returns:
            List[SummaryResult]: Summaries for each chunk
        """
        summaries = []
        for chunk in chunks:
            summary = await self.summarize(chunk, target_length=100)
            summaries.append(summary)

        return summaries

    async def create_executive_summary(
        self,
        content: str,
    ) -> ExecutiveSummaryResult:
        """
        Create an executive summary.

        Args:
            content: Content to summarize

        Returns:
            ExecutiveSummaryResult: Executive summary
        """
        try:
            prompt = prompt_manager.format_prompt(
                "executive_summary",
                document=content[:10000]
            )

            summary_text = await self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are an executive assistant. Create concise, actionable executive summaries."
            )

            # Extract bullet points
            lines = summary_text.split('\n')
            bullet_points = [
                line.strip().lstrip('- ').lstrip('• ')
                for line in lines
                if line.strip() and (line.strip().startswith('-') or line.strip().startswith('•'))
            ]

            # If no bullet points found, split by sentences
            if not bullet_points:
                bullet_points = [s.strip() for s in summary_text.split('. ') if s.strip()][:10]

            return ExecutiveSummaryResult(
                summary=summary_text,
                bullet_points=bullet_points[:10],
                key_decisions=[],
                action_items=[],
                confidence=0.9,
            )

        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}", exc_info=True)
            raise

    async def create_global_summary(
        self,
        chunk_summaries: List[SummaryResult],
    ) -> SummaryResult:
        """
        Create a global summary from chunk summaries.

        Args:
            chunk_summaries: List of chunk summaries

        Returns:
            SummaryResult: Global summary
        """
        # Combine chunk summaries
        combined_text = "\n\n".join([s.summary for s in chunk_summaries])

        # Create summary of summaries
        return await self.summarize(combined_text, target_length=300)
