"""
Prompt Manager for template management and versioning.

Provides centralized prompt management with versioning and customization.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages prompt templates with versioning and customization.
    """

    def __init__(self):
        """Initialize prompt manager."""
        self.templates: Dict[str, str] = {}
        self.versions: Dict[str, str] = {}

    def register_template(
        self,
        name: str,
        template: str,
        version: str = "1.0"
    ):
        """
        Register a prompt template.

        Args:
            name: Template name
            template: Template string
            version: Template version
        """
        self.templates[name] = template
        self.versions[name] = version
        logger.info(f"Registered prompt template: {name} v{version}")

    def get_template(self, name: str) -> Optional[str]:
        """
        Get a prompt template.

        Args:
            name: Template name

        Returns:
            str: Template string or None if not found
        """
        return self.templates.get(name)

    def format_prompt(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """
        Format a prompt template with variables.

        Args:
            template_name: Name of template
            **kwargs: Variables to substitute

        Returns:
            str: Formatted prompt
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")

    def get_version(self, template_name: str) -> Optional[str]:
        """
        Get template version.

        Args:
            template_name: Template name

        Returns:
            str: Version string or None
        """
        return self.versions.get(template_name)


# Global prompt manager instance
prompt_manager = PromptManager()

# Register default templates
from .templates import (
    TOPIC_EXTRACTION_PROMPT,
    SUMMARIZATION_PROMPT,
    EXECUTIVE_SUMMARY_PROMPT,
    INSIGHT_GENERATION_PROMPT,
)

prompt_manager.register_template("topic_extraction", TOPIC_EXTRACTION_PROMPT)
prompt_manager.register_template("summarization", SUMMARIZATION_PROMPT)
prompt_manager.register_template("executive_summary", EXECUTIVE_SUMMARY_PROMPT)
prompt_manager.register_template("insight_generation", INSIGHT_GENERATION_PROMPT)
