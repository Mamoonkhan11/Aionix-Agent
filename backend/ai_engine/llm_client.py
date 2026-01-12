"""
Unified LLM Client Abstraction.

Provides a single interface for interacting with different LLM providers
(OpenAI, Hugging Face) with async support, retry logic, and easy extension.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    ANTHROPIC = "anthropic"  # Future support


class LLMClient(ABC):
    """
    Abstract base class for LLM clients.

    Provides a unified interface for all LLM providers with async support,
    retry logic, and error handling.
    """

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        """
        Initialize LLM client.

        Args:
            model: Model identifier
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.request_id: Optional[str] = None

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific parameters

        Returns:
            str: Generated text
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """
        Generate streaming text completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific parameters

        Yields:
            str: Text chunks
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output.

        Args:
            prompt: User prompt
            schema: JSON schema for output structure
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            Dict: Structured output matching schema
        """
        pass

    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracking."""
        self.request_id = str(uuid4())
        return self.request_id


class OpenAIClient(LLMClient):
    """OpenAI API client implementation."""

    def __init__(self, model: str = "gpt-4", **kwargs):
        """Initialize OpenAI client."""
        super().__init__(model, **kwargs)
        self.api_key = settings.openai_api_key

        if not self.api_key:
            raise ValueError("OpenAI API key not configured")

        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=self.api_key, timeout=self.timeout)
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,)),
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text using OpenAI API."""
        self._generate_request_id()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )

            result = response.choices[0].message.content
            logger.info(
                f"OpenAI completion successful",
                extra={
                    "request_id": self.request_id,
                    "model": self.model,
                    "tokens_used": response.usage.total_tokens if response.usage else None,
                }
            )
            return result

        except Exception as e:
            logger.error(
                f"OpenAI API error: {e}",
                extra={"request_id": self.request_id, "model": self.model},
                exc_info=True
            )
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Generate streaming text using OpenAI API."""
        self._generate_request_id()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(
                f"OpenAI streaming error: {e}",
                extra={"request_id": self.request_id, "model": self.model},
                exc_info=True
            )
            raise

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON output using OpenAI function calling."""
        self._generate_request_id()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
                **kwargs
            )

            import json
            result = json.loads(response.choices[0].message.content)
            logger.info(
                f"OpenAI structured completion successful",
                extra={"request_id": self.request_id, "model": self.model}
            )
            return result

        except Exception as e:
            logger.error(
                f"OpenAI structured generation error: {e}",
                extra={"request_id": self.request_id, "model": self.model},
                exc_info=True
            )
            raise


class HuggingFaceClient(LLMClient):
    """Hugging Face client implementation."""

    def __init__(self, model: str = "meta-llama/Llama-2-7b-chat-hf", **kwargs):
        """Initialize Hugging Face client."""
        super().__init__(model, **kwargs)
        self.api_key = getattr(settings, "huggingface_api_key", None)

        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
            import torch

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading Hugging Face model {model} on {self.device}")

            self.tokenizer = AutoTokenizer.from_pretrained(model)
            self.model_obj = AutoModelForCausalLM.from_pretrained(
                model,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
            )

            self.pipeline = pipeline(
                "text-generation",
                model=self.model_obj,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
            )

        except ImportError:
            raise ImportError(
                "transformers and torch packages not installed. "
                "Install with: pip install transformers torch"
            )
        except Exception as e:
            logger.error(f"Failed to load Hugging Face model: {e}")
            raise

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text using Hugging Face model."""
        self._generate_request_id()

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.pipeline(
                    full_prompt,
                    max_length=self.max_tokens or 512,
                    temperature=self.temperature,
                    do_sample=True,
                    num_return_sequences=1,
                    **kwargs
                )
            )

            generated_text = result[0]["generated_text"][len(full_prompt):].strip()
            logger.info(
                f"Hugging Face completion successful",
                extra={"request_id": self.request_id, "model": self.model}
            )
            return generated_text

        except Exception as e:
            logger.error(
                f"Hugging Face generation error: {e}",
                extra={"request_id": self.request_id, "model": self.model},
                exc_info=True
            )
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Generate streaming text using Hugging Face (simulated)."""
        # Hugging Face doesn't natively support streaming, so we simulate it
        result = await self.generate(prompt, system_prompt, **kwargs)
        words = result.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.01)  # Small delay to simulate streaming

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON output using Hugging Face."""
        # Add JSON format instruction to prompt
        json_prompt = f"{prompt}\n\nRespond in valid JSON format matching this schema: {schema}"

        result = await self.generate(json_prompt, system_prompt, **kwargs)

        try:
            import json
            # Try to extract JSON from response
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = result[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            logger.error(f"Failed to parse JSON from Hugging Face response: {e}")
            raise ValueError(f"Invalid JSON response: {result}")


def create_llm_client(
    provider: Optional[Union[str, LLMProvider]] = None,
    model: Optional[str] = None,
    **kwargs
) -> LLMClient:
    """
    Factory function to create LLM client.

    Args:
        provider: LLM provider (openai, huggingface)
        model: Model identifier
        **kwargs: Additional client parameters

    Returns:
        LLMClient: Configured LLM client instance

    Example:
        >>> client = create_llm_client("openai", "gpt-4")
        >>> result = await client.generate("Hello, world!")
    """
    if provider is None:
        provider = getattr(settings, "default_llm_provider", "openai")

    if isinstance(provider, str):
        provider = LLMProvider(provider.lower())

    # Default models
    if model is None:
        if provider == LLMProvider.OPENAI:
            model = getattr(settings, "default_openai_model", "gpt-4")
        elif provider == LLMProvider.HUGGINGFACE:
            model = getattr(settings, "default_huggingface_model", "meta-llama/Llama-2-7b-chat-hf")
        else:
            model = "gpt-4"

    if provider == LLMProvider.OPENAI:
        return OpenAIClient(model=model, **kwargs)
    elif provider == LLMProvider.HUGGINGFACE:
        return HuggingFaceClient(model=model, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
