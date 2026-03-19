"""
Tests for Claude API client.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from anthropic.types import Message, Usage
from anthropic.types.text_block import TextBlock

from web.core.claude import ClaudeClient, TokenUsage, MODELS


class TestTokenUsage:
    """Test token usage tracking."""

    def test_token_usage_tracking(self):
        """Test that token usage is tracked correctly."""
        usage = TokenUsage()

        # Mock usage object
        mock_usage = Mock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50
        mock_usage.cache_creation_input_tokens = 20
        mock_usage.cache_read_input_tokens = 30

        usage.add_usage(mock_usage)

        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cache_creation_tokens == 20
        assert usage.cache_read_tokens == 30

    def test_to_dict(self):
        """Test conversion to dictionary."""
        usage = TokenUsage()
        usage.input_tokens = 100
        usage.output_tokens = 50

        result = usage.to_dict()

        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["total_tokens"] == 150


class TestClaudeClient:
    """Test Claude client functionality."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create mock Anthropic client."""
        with patch("web.core.claude.Anthropic") as mock:
            yield mock

    @pytest.fixture
    def claude_client(self, mock_anthropic_client):
        """Create Claude client with mocked Anthropic."""
        return ClaudeClient(api_key="test-key")

    def test_client_initialization(self, claude_client):
        """Test client initializes correctly."""
        assert claude_client.api_key == "test-key"
        assert claude_client.max_retries == 3
        assert claude_client.initial_retry_delay == 1.0
        assert isinstance(claude_client.token_usage, TokenUsage)

    @pytest.mark.asyncio
    async def test_initial_analysis(self, claude_client):
        """Test initial analysis method."""
        # Create proper mock usage object with all required attributes
        mock_usage = Mock()
        mock_usage.input_tokens = 1000
        mock_usage.output_tokens = 500
        mock_usage.cache_creation_input_tokens = 0
        mock_usage.cache_read_input_tokens = 0

        # Mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Test analysis result")]
        mock_response.usage = mock_usage

        # Mock the client's messages.create method
        claude_client.client.messages.create = Mock(return_value=mock_response)

        # Call initial_analysis
        result, usage = await claude_client.initial_analysis(
            pdf_path="/test/paper.pdf"
        )

        # Verify result
        assert result == "Test analysis result"
        assert usage["model"] == MODELS["sonnet"]
        assert usage["input_tokens"] == 1000
        assert usage["output_tokens"] == 500

        # Verify token tracking
        assert claude_client.token_usage.input_tokens == 1000
        assert claude_client.token_usage.output_tokens == 500

    @pytest.mark.asyncio
    async def test_query(self, claude_client):
        """Test query method."""
        # Create proper mock usage object with all required attributes
        mock_usage = Mock()
        mock_usage.input_tokens = 2000
        mock_usage.output_tokens = 300
        mock_usage.cache_creation_input_tokens = 0
        mock_usage.cache_read_input_tokens = 0

        # Mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Test query response")]
        mock_response.usage = mock_usage

        # Mock the client's messages.create method
        claude_client.client.messages.create = Mock(return_value=mock_response)

        # Call query
        result, usage = await claude_client.query(
            user_query="What is the main finding?",
            pdf_path="/test/paper.pdf",
            conversation_history=[],
            use_sonnet=True,
        )

        # Verify result
        assert result == "Test query response"
        assert usage["model"] == MODELS["sonnet"]
        assert usage["input_tokens"] == 2000
        assert usage["output_tokens"] == 300

    @pytest.mark.asyncio
    async def test_retry_logic(self, claude_client):
        """Test retry logic with exponential backoff."""
        from anthropic import RateLimitError

        # Create proper mock usage object with all required attributes
        mock_usage = Mock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50
        mock_usage.cache_creation_input_tokens = 0
        mock_usage.cache_read_input_tokens = 0

        # Mock to fail twice, then succeed
        mock_response = Mock()
        mock_response.content = [Mock(text="Success after retries")]
        mock_response.usage = mock_usage

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Create a proper RateLimitError with required params
                mock_response_obj = Mock()
                mock_response_obj.status_code = 429
                mock_body = {"error": {"message": "Rate limit exceeded"}}
                raise RateLimitError("Rate limit exceeded", response=mock_response_obj, body=mock_body)
            return mock_response

        claude_client.client.messages.create = Mock(side_effect=side_effect)

        # Should succeed after 2 retries
        result, usage = await claude_client.initial_analysis(
            pdf_path="/test/paper.pdf"
        )

        assert result == "Success after retries"
        assert call_count == 3  # Failed twice, succeeded on third try

    def test_get_total_usage(self, claude_client):
        """Test getting total usage stats."""
        claude_client.token_usage.input_tokens = 5000
        claude_client.token_usage.output_tokens = 2000

        usage = claude_client.get_total_usage()

        assert usage["input_tokens"] == 5000
        assert usage["output_tokens"] == 2000
        assert usage["total_tokens"] == 7000

    def test_reset_usage(self, claude_client):
        """Test resetting usage tracking."""
        claude_client.token_usage.input_tokens = 5000
        claude_client.token_usage.output_tokens = 2000

        claude_client.reset_usage()

        assert claude_client.token_usage.input_tokens == 0
        assert claude_client.token_usage.output_tokens == 0


@pytest.mark.asyncio
async def test_convenience_functions():
    """Test convenience functions."""
    import os
    from web.core.claude import get_claude_client

    # Set required environment variable for settings
    os.environ["ANTHROPIC_API_KEY"] = "test-key-123"

    # Get singleton client
    client1 = get_claude_client()
    client2 = get_claude_client()

    # Should be same instance
    assert client1 is client2

    # Clean up
    del os.environ["ANTHROPIC_API_KEY"]
