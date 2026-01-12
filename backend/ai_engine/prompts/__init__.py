"""
Prompt templates and prompt management.

This module provides centralized prompt templates for:
- Topic extraction
- Summarization
- Insight generation
- System instructions
"""

from .prompt_manager import PromptManager
from .templates import (
    TOPIC_EXTRACTION_PROMPT,
    SUMMARIZATION_PROMPT,
    INSIGHT_GENERATION_PROMPT,
    EXECUTIVE_SUMMARY_PROMPT,
)

__all__ = [
    "PromptManager",
    "TOPIC_EXTRACTION_PROMPT",
    "SUMMARIZATION_PROMPT",
    "INSIGHT_GENERATION_PROMPT",
    "EXECUTIVE_SUMMARY_PROMPT",
]
