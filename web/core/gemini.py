"""
Google Gemini API integration for Scholia Web Backend.
Handles all Gemini API interactions with retry logic, caching, and cost tracking.
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

from google import genai
from google.genai import types, errors

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
    "gemini-flash": "gemini-3-flash-preview",
    "gemini-pro": "gemini-3-pro-preview",
}

# Safety settings - permissive for academic content
SAFETY_SETTINGS = [
    types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="BLOCK_NONE"
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="BLOCK_NONE"
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="BLOCK_NONE"
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="BLOCK_NONE"
    ),
]


class TokenUsage:
    """Track token usage for monitoring."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        self.thinking_tokens = 0

    def add_usage(self, prompt_tokens: int, completion_tokens: int, cached_tokens: int = 0, thinking_tokens: int = 0) -> None:
        """Add usage from API response."""
        self.input_tokens += prompt_tokens
        self.output_tokens += completion_tokens
        self.cached_tokens += cached_tokens
        self.thinking_tokens += thinking_tokens

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "thinking_tokens": self.thinking_tokens,
            "total_tokens": self.input_tokens + self.output_tokens + self.thinking_tokens,
        }


class GeminiClient:
    """
    Wrapper for Google Gemini API with enterprise features.

    Features:
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Token usage tracking
    - Support for both Flash and Pro models
    - Context caching for cost reduction
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
    ):
        """
        Initialize Gemini client.

        Args:
            api_key: Google API key (uses settings if not provided)
            max_retries: Maximum number of retry attempts
            initial_retry_delay: Initial delay in seconds for exponential backoff
        """
        if api_key:
            self.api_key = api_key
        else:
            settings = get_settings()
            self.api_key = settings.google_api_key

        if not self.api_key:
            raise ValueError("Google API key is required for Gemini client")

        self.client = genai.Client(api_key=self.api_key)
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.token_usage = TokenUsage()
        # Cache uploaded files by (session_id, pdf_path) tuple to avoid re-uploading
        # within a session while preventing cross-session context contamination
        self._uploaded_files: Dict[Tuple[str, str], Any] = {}

    def clear_file_cache(self, session_id: str = None, pdf_path: str = None) -> None:
        """
        Clear cached file uploads.

        Args:
            session_id: If provided with pdf_path, clear that specific cache entry.
            pdf_path: If provided with session_id, clear that specific cache entry.
                     If only pdf_path is provided, clears all entries for that path.
                     If neither provided, clears all.
        """
        if session_id and pdf_path:
            self._uploaded_files.pop((session_id, pdf_path), None)
        elif pdf_path:
            # Clear all entries for this pdf_path (any session)
            keys_to_remove = [k for k in self._uploaded_files if k[1] == pdf_path]
            for key in keys_to_remove:
                self._uploaded_files.pop(key, None)
        else:
            self._uploaded_files.clear()

    async def _upload_pdf(self, pdf_path: str, session_id: str) -> Any:
        """
        Upload PDF file to Gemini Files API.

        Files are cached by (session_id, pdf_path) tuple to avoid re-uploading
        within the same session while preventing cross-session context contamination.
        Gemini Files API keeps files for 48 hours.

        Args:
            pdf_path: Path to PDF file
            session_id: Session identifier for cache isolation

        Returns:
            File object from Gemini Files API

        Raises:
            FileNotFoundError: If PDF doesn't exist
        """
        cache_key = (session_id, pdf_path)

        # Check cache first
        if cache_key in self._uploaded_files:
            logger.info(f"Using cached file upload for session {session_id}: {pdf_path}")
            return self._uploaded_files[cache_key]

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Uploading PDF to Gemini Files API for session {session_id}: {pdf_path}")

        # Upload file to Gemini Files API
        loop = asyncio.get_event_loop()
        uploaded_file = await loop.run_in_executor(
            None,
            lambda: self.client.files.upload(file=pdf_path)
        )

        # Cache the uploaded file by (session_id, pdf_path)
        self._uploaded_files[cache_key] = uploaded_file
        logger.info(f"PDF uploaded successfully: {uploaded_file.name}")

        return uploaded_file

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
                # Run in thread pool since genai client operations may block
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
                return result

            except errors.ClientError as e:
                # Check if it's a rate limit error (429)
                if hasattr(e, 'status_code') and e.status_code == 429:
                    last_exception = e
                    # Rate limit - use longer backoff
                    delay = self.initial_retry_delay * (3 ** attempt)
                    logger.warning(f"Rate limit hit, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                else:
                    # Other client errors - don't retry
                    raise

            except errors.ServerError as e:
                last_exception = e
                # Server error - retry with exponential backoff
                delay = self.initial_retry_delay * (2 ** attempt)
                logger.warning(f"Service unavailable, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)

            except Exception as e:
                # Unexpected error - don't retry
                logger.error(f"Unexpected error in Gemini API call: {e}")
                raise

        # All retries exhausted
        logger.error(f"All {self.max_retries} retries exhausted")
        raise last_exception

    def _get_model_id(self, model_name: str) -> str:
        """Get Gemini model ID."""
        return MODELS.get(model_name, MODELS["gemini-flash"])

    async def initial_analysis(
        self,
        pdf_path: str,
        max_tokens: int = 800,
        session_id: str = "",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Get initial analysis of paper using Gemini with full PDF file.

        Args:
            pdf_path: Path to PDF file
            max_tokens: Maximum tokens in response
            session_id: Session identifier for cache isolation

        Returns:
            Tuple of (analysis_text, usage_dict)
        """
        logger.info(f"Starting initial analysis with Gemini Flash using PDF: {pdf_path}")

        model_id = self._get_model_id("gemini-flash")

        # Upload PDF to Gemini Files API (with session isolation)
        uploaded_file = await self._upload_pdf(pdf_path, session_id)

        # Data first, then instructions per Gemini 3 best practices
        # Reference the uploaded file
        prompt = INITIAL_ANALYSIS_PROMPT

        # Make API call with retry logic, including uploaded PDF file
        def _generate():
            return self.client.models.generate_content(
                model=model_id,
                contents=[
                    uploaded_file,  # Include the PDF file
                    prompt  # Then the task instructions
                ],
                config=types.GenerateContentConfig(
                    system_instruction=INITIAL_ANALYSIS_SYSTEM_PROMPT,
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                    safety_settings=SAFETY_SETTINGS,
                    # Enable context caching for the PDF
                    cached_content=None,  # Will use automatic caching
                ),
            )

        response = await self._retry_with_backoff(_generate)

        # Extract response text
        response_text = response.text if response.text else ""

        # Track token usage
        prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0 if response.usage_metadata else 0
        completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0 if response.usage_metadata else 0
        cached_tokens = getattr(response.usage_metadata, 'cached_content_token_count', 0) or 0 if response.usage_metadata else 0

        self.token_usage.add_usage(prompt_tokens, completion_tokens, cached_tokens)

        usage_stats = {
            "model": MODELS["gemini-flash"],
            "use_thinking": False,  # Thinking not supported for initial analysis
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "thinking_tokens": 0,
            "cached_tokens": cached_tokens,
        }

        logger.info(
            f"Initial analysis complete. Tokens: {prompt_tokens} in, "
            f"{completion_tokens} out, cached: {cached_tokens}"
        )

        return response_text, usage_stats

    async def query(
        self,
        user_query: str,
        pdf_path: str,
        conversation_history: List[Dict[str, str]],
        use_pro: bool = False,
        use_thinking: bool = False,
        max_tokens: int = 2000,
        session_id: str = "",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Handle conversational query about the paper using full PDF file.

        Args:
            user_query: User's question
            pdf_path: Path to PDF file
            conversation_history: List of previous messages
            use_pro: Use Pro (True) or Flash (False)
            use_thinking: Enable thinking mode (only works with Pro)
            max_tokens: Maximum tokens in response
            session_id: Session identifier for cache isolation

        Returns:
            Tuple of (response_text, usage_dict)
        """
        model_name = "gemini-pro" if use_pro else "gemini-flash"
        # Both Flash and Pro support thinking with Gemini 3

        logger.info(f"Processing query with {model_name} using PDF (query length: {len(user_query)} chars, thinking: {use_thinking})")

        model_id = self._get_model_id(model_name)

        # Upload PDF to Gemini Files API (with session isolation)
        uploaded_file = await self._upload_pdf(pdf_path, session_id)

        # Build conversation with context - instructions per Gemini 3 best practices
        # Build chat history for new SDK, including PDF file
        # Use types.Part.from_uri for file, dict format {"text": ...} for text
        file_part = types.Part.from_uri(file_uri=uploaded_file.uri, mime_type="application/pdf")

        history = [
            {
                "role": "user",
                "parts": [file_part, {"text": QUERY_PROMPT}]
            },
            {
                "role": "model",
                "parts": [{"text": "I've read the paper and am ready to discuss it with you."}]
            }
        ]

        # Add conversation history
        for msg in conversation_history[-10:]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Build config with optional thinking
        # Note: Gemini 3 models do implicit thinking even when not requested,
        # and thinking tokens count against max_output_tokens.
        #
        # Token allocation strategy:
        # - High thinking: 10000 tokens for extensive reasoning
        # - Low thinking: 2000 tokens (allows room for implicit thinking + output)
        if use_thinking:
            # High thinking mode: generous budget for reasoning
            allocated_tokens = max(max_tokens, 10000)
        else:
            # Low thinking mode: use default (2000)
            allocated_tokens = max_tokens

        config_kwargs = {
            "max_output_tokens": allocated_tokens,
            "system_instruction": QUERY_SYSTEM_PROMPT,
            "safety_settings": SAFETY_SETTINGS,
        }

        if use_thinking:
            # Enable thinking mode using thinking_level (Gemini 3 API)
            # Flash: "medium" for balanced reasoning, Pro: "high" for maximum depth
            thinking_level = "high" if use_pro else "medium"
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=thinking_level
            )
            # Temperature must be default (1.0) when thinking is enabled
        else:
            # Minimize thinking to prevent it from consuming output token budget
            # "low" works on both Flash and Pro, minimizes latency and cost
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level="low"
            )
            config_kwargs["temperature"] = 0.6

        # Create chat session and send message
        def _query():
            chat = self.client.chats.create(
                model=model_id,
                history=history,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            return chat.send_message(message=user_query)

        response = await self._retry_with_backoff(_query)

        # Extract response text and check finish reason
        response_text = response.text if response.text else ""

        # Log finish reason if response seems truncated
        if response.candidates:
            finish_reason = response.candidates[0].finish_reason
            if finish_reason and finish_reason.name != "STOP":
                logger.warning(f"Response finished with reason: {finish_reason.name}")
            elif len(response_text) < 50:
                logger.info(f"Short response ({len(response_text)} chars), finish_reason: {finish_reason.name if finish_reason else 'unknown'}")

        # Track token usage
        prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0 if response.usage_metadata else 0
        completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0 if response.usage_metadata else 0
        cached_tokens = getattr(response.usage_metadata, 'cached_content_token_count', 0) or 0 if response.usage_metadata else 0
        thinking_tokens = getattr(response.usage_metadata, 'thinking_token_count', 0) or 0 if response.usage_metadata else 0

        self.token_usage.add_usage(prompt_tokens, completion_tokens, cached_tokens, thinking_tokens)

        usage_stats = {
            "model": MODELS[model_name],
            "use_thinking": use_thinking,
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "thinking_tokens": thinking_tokens,
            "cached_tokens": cached_tokens,
        }

        logger.info(
            f"Query complete. Tokens: {prompt_tokens} in, "
            f"{completion_tokens} out, thinking: {thinking_tokens}, cached: {cached_tokens}"
        )

        return response_text, usage_stats

    async def extract_structured(
        self,
        extraction_prompt: str,
        pdf_path: str = "",
        conversation_context: str = "",
        max_tokens: int = 4000,
        use_thinking: bool = False,
        session_id: str = "",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Extract structured data (JSON) from paper and conversation using PDF file.

        Args:
            extraction_prompt: Prompt describing what to extract
            pdf_path: Path to PDF file (optional)
            conversation_context: Formatted conversation history for context
            max_tokens: Maximum tokens in response
            use_thinking: Enable thinking mode (uses Pro instead of Flash)
            session_id: Session identifier for cache isolation

        Returns:
            Tuple of (response_text, usage_dict)
        """
        # Use Flash for cost-effective extraction (Flash also supports thinking with Gemini 3)
        model_name = "gemini-flash"
        logger.info(f"Extracting structured data with {model_name} (thinking: {use_thinking})")

        model_id = self._get_model_id(model_name)

        # Build task prompt
        # Note: conversation_context is deprecated and included in extraction_prompt
        # for the new XML-based extraction format
        task_prompt = extraction_prompt
        if conversation_context:
            task_prompt = f"Conversation context:\n{conversation_context}\n\n{extraction_prompt}"

        # Upload PDF if provided (with session isolation)
        contents = []
        if pdf_path:
            uploaded_file = await self._upload_pdf(pdf_path, session_id)
            contents.append(uploaded_file)
        contents.append(task_prompt)

        # Build config with optional thinking
        config_kwargs = {
            "max_output_tokens": max_tokens if not use_thinking else max(max_tokens, 16000),
            "system_instruction": EXTRACTION_SYSTEM_PROMPT,
            "safety_settings": SAFETY_SETTINGS,
        }

        if use_thinking:
            # Enable thinking mode using thinking_level (Gemini 3 API)
            # Flash uses "medium" for balanced reasoning in extraction tasks
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level="medium"
            )
            # Temperature must be default (1.0) when thinking is enabled
        else:
            # Minimize thinking to prevent it from consuming output token budget
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level="low"
            )
            config_kwargs["temperature"] = 0.3  # Lower temperature for structured output

        def _extract():
            return self.client.models.generate_content(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs),
            )

        response = await self._retry_with_backoff(_extract)

        # Extract response text
        response_text = response.text if response.text else ""

        # Track token usage
        prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0 if response.usage_metadata else 0
        completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0 if response.usage_metadata else 0
        cached_tokens = getattr(response.usage_metadata, 'cached_content_token_count', 0) or 0 if response.usage_metadata else 0
        thinking_tokens = getattr(response.usage_metadata, 'thinking_token_count', 0) or 0 if response.usage_metadata else 0

        self.token_usage.add_usage(prompt_tokens, completion_tokens, cached_tokens, thinking_tokens)

        usage_stats = {
            "model": MODELS[model_name],
            "use_thinking": use_thinking,
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "thinking_tokens": thinking_tokens,
            "cached_tokens": cached_tokens,
        }

        logger.info(
            f"Extraction complete. Tokens: {prompt_tokens} in, "
            f"{completion_tokens} out, thinking: {thinking_tokens}, cached: {cached_tokens}"
        )

        return response_text, usage_stats

    def get_total_usage(self) -> Dict[str, Any]:
        """Get total token usage for this client instance."""
        return self.token_usage.to_dict()

    def reset_usage(self) -> None:
        """Reset token usage tracking."""
        self.token_usage = TokenUsage()


# Convenience functions for dependency injection
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> Optional[GeminiClient]:
    """
    Get global Gemini client instance (singleton pattern).

    Returns:
        GeminiClient if configured, None otherwise
    """
    global _gemini_client
    settings = get_settings()

    if not settings.has_gemini_config():
        return None

    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client


def is_gemini_available() -> bool:
    """Check if Gemini is available."""
    settings = get_settings()
    return settings.has_gemini_config()
