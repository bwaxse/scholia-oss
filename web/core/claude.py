"""
Claude API integration for Paper Companion Web Backend.
Handles all Claude API interactions with retry logic, rate limiting, and cost tracking.
"""

import asyncio
import base64
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
from anthropic.types import Message

from .config import get_settings
from .prompts import (
    QUERY_SYSTEM_PROMPT,
    QUERY_PROMPT,
    INITIAL_ANALYSIS_SYSTEM_PROMPT,
    INITIAL_ANALYSIS_PROMPT,
    EXTRACTION_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


# Model configurations
MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

# Development mode - set to True to use haiku for all queries (cost savings)
USE_DEV_MODE = False


class TokenUsage:
    """Track token usage and costs for monitoring."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_creation_tokens = 0
        self.cache_read_tokens = 0
        self.thinking_tokens = 0

    def add_usage(self, usage: Any) -> None:
        """
        Add usage from API response.

        Args:
            usage: Usage object from Anthropic API response
        """
        self.input_tokens += getattr(usage, "input_tokens", 0)
        self.output_tokens += getattr(usage, "output_tokens", 0)
        self.cache_creation_tokens += getattr(usage, "cache_creation_input_tokens", 0)
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0)
        # Extended thinking tokens (Claude Sonnet with thinking enabled)
        self.thinking_tokens += getattr(usage, "thinking_tokens", 0)


    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "thinking_tokens": self.thinking_tokens,
            "total_tokens": self.input_tokens + self.output_tokens + self.thinking_tokens,
        }


class ClaudeClient:
    """
    Wrapper for Claude API with enterprise features.

    Features:
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Token usage tracking and cost monitoring
    - Support for both Haiku and Sonnet models
    - PDF document analysis with prompt caching
    - Conversational query handling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
    ):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key (uses settings if not provided)
            max_retries: Maximum number of retry attempts
            initial_retry_delay: Initial delay in seconds for exponential backoff
        """
        if api_key:
            self.api_key = api_key
        else:
            settings = get_settings()
            self.api_key = settings.anthropic_api_key
        self.client = Anthropic(api_key=self.api_key)
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.token_usage = TokenUsage()

    @staticmethod
    def _encode_pdf(pdf_path: str) -> str:
        """
        Encode PDF file to base64 for API upload.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Base64 encoded PDF string

        Raises:
            FileNotFoundError: If PDF doesn't exist
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        with open(pdf_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")

    async def _retry_with_backoff(
        self,
        func,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                # Run in thread pool since anthropic client is sync
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
                return result

            except RateLimitError as e:
                last_exception = e
                # Rate limit - use longer backoff
                delay = self.initial_retry_delay * (3 ** attempt)
                logger.warning(f"Rate limit hit, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)

            except APIConnectionError as e:
                last_exception = e
                # Network error - retry with exponential backoff
                delay = self.initial_retry_delay * (2 ** attempt)
                logger.warning(f"Connection error, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)

            except APIError as e:
                # Other API errors - check if retryable
                if e.status_code and 500 <= e.status_code < 600:
                    # Server error - retry
                    last_exception = e
                    delay = self.initial_retry_delay * (2 ** attempt)
                    logger.warning(f"Server error {e.status_code}, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                else:
                    # Client error - don't retry
                    raise

            except Exception as e:
                # Unexpected error - don't retry
                logger.error(f"Unexpected error in Claude API call: {e}")
                raise

        # All retries exhausted
        logger.error(f"All {self.max_retries} retries exhausted")
        raise last_exception

    async def initial_analysis(
        self,
        pdf_path: str,
        max_tokens: int = 800,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Get initial analysis of paper using Claude Sonnet with full PDF document.

        This method uses Sonnet for high-quality initial analysis.
        Sends the entire PDF file (including figures, tables, formatting) to Claude.

        Args:
            pdf_path: Path to PDF file
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (analysis_text, usage_dict)
            The analysis_text starts with "TITLE: <paper title>" on the first line
        """
        logger.info(f"Starting initial analysis with Sonnet using PDF: {pdf_path}")

        # Encode PDF to base64
        pdf_data = self._encode_pdf(pdf_path)

        # Build prompt with PDF document
        # Claude processes the full PDF including figures, tables, and formatting
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_data
                        },
                        "cache_control": {"type": "ephemeral"}
                    },
                    {
                        "type": "text",
                        "text": INITIAL_ANALYSIS_PROMPT
                    }
                ]
            }
        ]

        # Make API call with retry logic
        response = await self._retry_with_backoff(
            self.client.messages.create,
            model=MODELS["sonnet"],
            max_tokens=max_tokens,
            system=INITIAL_ANALYSIS_SYSTEM_PROMPT,
            messages=messages,
        )

        # Track token usage
        self.token_usage.add_usage(response.usage)

        # Extract response text
        response_text = response.content[0].text if response.content else ""

        # Build usage stats including cache info
        cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0)
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0)

        usage_stats = {
            "model": MODELS["sonnet"],
            "use_thinking": False,  # Thinking not supported for initial analysis
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "thinking_tokens": 0,
            "cache_creation_tokens": cache_creation,
            "cache_read_tokens": cache_read,
        }

        logger.info(
            f"Initial analysis complete. Tokens: {response.usage.input_tokens} in, "
            f"{response.usage.output_tokens} out, cache_create: {cache_creation}, cache_read: {cache_read}"
        )

        return response_text, usage_stats

    async def query(
        self,
        user_query: str,
        pdf_path: str,
        conversation_history: List[Dict[str, str]],
        use_sonnet: bool = True,
        use_thinking: bool = False,
        max_tokens: int = 2000,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Handle conversational query about the paper using full PDF document.

        Uses prompt caching for the PDF - cached for 5 minutes,
        so follow-up queries within that window are significantly cheaper.

        Args:
            user_query: User's question
            pdf_path: Path to PDF file
            conversation_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
            use_sonnet: Use Sonnet (True) or Haiku (False) - ignored if USE_DEV_MODE is True
            use_thinking: Enable extended thinking (only works with Sonnet)
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (response_text, usage_dict)
        """
        # In dev mode, always use haiku for cost savings
        if USE_DEV_MODE:
            model = MODELS["haiku"]
            use_thinking = False  # Thinking only available with Sonnet
        else:
            model = MODELS["sonnet"] if use_sonnet else MODELS["haiku"]
            # Thinking only works with Sonnet
            if not use_sonnet:
                use_thinking = False

        logger.info(f"Processing query with {model} (query length: {len(user_query)} chars, thinking: {use_thinking})")

        # Encode PDF to base64
        pdf_data = self._encode_pdf(pdf_path)

        # Build messages with cache_control for PDF document
        # The PDF and system prompt are marked for caching (ephemeral = 5 min TTL)
        messages = []

        # First message contains paper PDF (cached) and task instructions
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data
                    },
                    "cache_control": {"type": "ephemeral"}
                },
                {
                    "type": "text",
                    "text": QUERY_PROMPT
                }
            ]
        })

        # Add a placeholder assistant response to maintain turn structure
        # This is needed because we're using content blocks in the first user message
        messages.append({
            "role": "assistant",
            "content": "I've read the paper and am ready to discuss it with you."
        })

        # Add conversation history (recent messages only)
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add current query
        messages.append({
            "role": "user",
            "content": user_query
        })

        # Build API call kwargs
        api_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": QUERY_SYSTEM_PROMPT,
            "messages": messages,
        }

        # Add thinking configuration if enabled (Sonnet only)
        if use_thinking:
            api_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": 10000  # Allow up to 10k tokens for thinking
            }
            # Increase max_tokens for thinking responses (must be > budget_tokens)
            api_kwargs["max_tokens"] = max(max_tokens, 12000)
            # Temperature must be 1 when thinking is enabled
        else:
            api_kwargs["temperature"] = 0.6

        # Make API call with retry logic
        response = await self._retry_with_backoff(
            self.client.messages.create,
            **api_kwargs,
        )

        # Track token usage
        self.token_usage.add_usage(response.usage)

        # Extract response text (skip thinking blocks, get text blocks)
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text += block.text

        # Check if response was truncated due to max_tokens
        if response.stop_reason == "max_tokens":
            response_text += "\n\n---\n*[Response truncated due to length. Reply with \"continue\" to see more]*"
            logger.warning(f"Response truncated at max_tokens limit")

        # Build usage stats including cache info and thinking tokens
        cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0)
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0)
        thinking_tokens = getattr(response.usage, "thinking_tokens", 0)

        usage_stats = {
            "model": model,
            "use_thinking": use_thinking,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "thinking_tokens": thinking_tokens,
            "cache_creation_tokens": cache_creation,
            "cache_read_tokens": cache_read,
        }

        logger.info(
            f"Query complete. Tokens: {response.usage.input_tokens} in, "
            f"{response.usage.output_tokens} out, thinking: {thinking_tokens}, "
            f"cache_create: {cache_creation}, cache_read: {cache_read}"
        )

        return response_text, usage_stats

    async def extract_structured(
        self,
        extraction_prompt: str,
        pdf_path: str = "",
        conversation_context: str = "",
        max_tokens: int = 4000,
        use_thinking: bool = False,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Extract structured data (JSON) from paper and conversation.

        Unlike query(), this method:
        - Uses higher token limits for complete JSON responses
        - Does not include brevity constraints
        - Is optimized for data extraction tasks
        - Uses prompt caching for PDF document

        Args:
            extraction_prompt: Prompt describing what to extract
            pdf_path: Path to PDF file (optional, if not provided, only uses conversation context)
            conversation_context: Formatted conversation history for context
            max_tokens: Maximum tokens in response (default 4000 for JSON)
            use_thinking: Enable extended thinking (uses Sonnet instead of Haiku)

        Returns:
            Tuple of (response_text, usage_dict)
        """
        # Use Sonnet if thinking is enabled, otherwise Haiku for cost-effective extraction
        if use_thinking:
            model = MODELS["sonnet"]
        else:
            model = MODELS["haiku"]

        logger.info(f"Extracting structured data with {model} (thinking: {use_thinking})")

        # Build messages with cache_control for PDF content
        messages = []

        # Build content blocks for the first message
        content_blocks = []

        # Add paper PDF with caching if provided
        if pdf_path:
            pdf_data = self._encode_pdf(pdf_path)
            content_blocks.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_data
                },
                "cache_control": {"type": "ephemeral"}
            })

        # Add extraction task instructions
        # Note: conversation_context is deprecated and included in extraction_prompt
        # for the new XML-based extraction format
        task_prompt = extraction_prompt
        if conversation_context:
            task_prompt = f"Conversation context:\n{conversation_context}\n\n{extraction_prompt}"

        content_blocks.append({
            "type": "text",
            "text": task_prompt
        })

        messages.append({
            "role": "user",
            "content": content_blocks
        })

        # Build API call kwargs
        api_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": EXTRACTION_SYSTEM_PROMPT,
            "messages": messages,
        }

        # Add thinking configuration if enabled (Sonnet only)
        if use_thinking:
            api_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": 10000  # Allow up to 10k tokens for thinking
            }
            # Increase max_tokens for thinking responses (must be > budget_tokens)
            api_kwargs["max_tokens"] = max(max_tokens, 16000)
            # Temperature must be 1 when thinking is enabled
        else:
            api_kwargs["temperature"] = 0.3  # Lower temperature for structured output

        # Make API call with retry logic
        response = await self._retry_with_backoff(
            self.client.messages.create,
            **api_kwargs,
        )

        # Track token usage
        self.token_usage.add_usage(response.usage)

        # Extract response text (skip thinking blocks, get text blocks)
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text += block.text

        # Build usage stats including cache info and thinking tokens
        cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0)
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0)
        thinking_tokens = getattr(response.usage, "thinking_tokens", 0)

        usage_stats = {
            "model": model,
            "use_thinking": use_thinking,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "thinking_tokens": thinking_tokens,
            "cache_creation_tokens": cache_creation,
            "cache_read_tokens": cache_read,
        }

        logger.info(
            f"Extraction complete. Tokens: {response.usage.input_tokens} in, "
            f"{response.usage.output_tokens} out, thinking: {thinking_tokens}, "
            f"cache_create: {cache_creation}, cache_read: {cache_read}"
        )

        return response_text, usage_stats

    def get_total_usage(self) -> Dict[str, Any]:
        """
        Get total token usage for this client instance.

        Returns:
            Dictionary with usage stats
        """
        return self.token_usage.to_dict()

    def reset_usage(self) -> None:
        """Reset token usage tracking."""
        self.token_usage = TokenUsage()


# Convenience functions for dependency injection
_claude_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """
    Get global Claude client instance (singleton pattern).

    Returns:
        ClaudeClient: Configured Claude client
    """
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
