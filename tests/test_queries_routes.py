"""
Tests for query routes.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from web.api.main import app
from web.api.models import (
    QueryResponse,
    FlagResponse,
    Highlight,
    HighlightList,
)


# Set test environment variables
@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set test environment variables."""
    os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
    os.environ["DATABASE_PATH"] = ":memory:"
    yield
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("DATABASE_PATH", None)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_query_service():
    """Mock query service for testing."""
    with patch("web.api.routes.queries.get_query_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


class TestQueryPaper:
    """Test POST /sessions/{id}/query endpoint."""

    @pytest.mark.asyncio
    async def test_query_success(self, client, mock_query_service):
        """Test successful query."""
        # Mock service response
        mock_query_service.query_paper = AsyncMock(return_value=QueryResponse(
            exchange_id=1,
            response="This paper introduces a novel approach to...",
            model_used="claude-sonnet-4-6",
            usage={
                "model": "claude-sonnet-4-6",
                "input_tokens": 1000,
                "output_tokens": 200
            }
        ))

        # Make request
        response = client.post(
            "/sessions/test-session-123/query",
            json={
                "query": "What is the main contribution?",
                "use_sonnet": True
            }
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["exchange_id"] == 1
        assert "novel approach" in data["response"]
        assert data["model_used"] == "claude-sonnet-4-6"
        assert data["usage"]["input_tokens"] == 1000

        # Verify service called
        mock_query_service.query_paper.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_session_not_found(self, client, mock_query_service):
        """Test query with non-existent session."""
        mock_query_service.query_paper = AsyncMock(
            side_effect=ValueError("Session not found: invalid-id")
        )

        response = client.post(
            "/sessions/invalid-id/query",
            json={"query": "What is this about?"}
        )

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_query_with_highlighted_text(self, client, mock_query_service):
        """Test query with highlighted text context."""
        mock_query_service.query_paper = AsyncMock(return_value=QueryResponse(
            exchange_id=2,
            response="This passage describes...",
            model_used="claude-sonnet-4-6",
            usage={"model": "claude-sonnet-4-6"}
        ))

        response = client.post(
            "/sessions/test-session/query",
            json={
                "query": "Explain this passage",
                "highlighted_text": "We propose a new method...",
                "page_number": 5
            }
        )

        assert response.status_code == 200
        assert response.json()["exchange_id"] == 2

    @pytest.mark.asyncio
    async def test_query_validation_empty_query(self, client, mock_query_service):
        """Test query validation with empty query."""
        response = client.post(
            "/sessions/test-session/query",
            json={"query": "   "}  # Whitespace only
        )

        # Should fail validation
        assert response.status_code == 422


class TestFlagExchange:
    """Test POST /sessions/{id}/exchanges/{eid}/flag endpoint."""

    @pytest.mark.asyncio
    async def test_flag_exchange_success(self, client, mock_query_service):
        """Test successfully flagging an exchange."""
        mock_query_service.flag_exchange = AsyncMock(return_value=FlagResponse(
            success=True,
            message="Exchange flagged successfully",
            flag_id=1
        ))

        response = client.post(
            "/sessions/test-session/exchanges/1/flag",
            json={"note": "Important insight"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["flag_id"] == 1
        assert "successfully" in data["message"]

        # Verify service called with correct args
        mock_query_service.flag_exchange.assert_called_once()
        call_args = mock_query_service.flag_exchange.call_args
        assert call_args[0][0] == "test-session"
        assert call_args[0][1] == 1
        assert call_args[0][2] == "Important insight"

    @pytest.mark.asyncio
    async def test_flag_exchange_no_note(self, client, mock_query_service):
        """Test flagging without a note."""
        mock_query_service.flag_exchange = AsyncMock(return_value=FlagResponse(
            success=True,
            message="Exchange flagged successfully",
            flag_id=2
        ))

        response = client.post(
            "/sessions/test-session/exchanges/3/flag",
            json={}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_flag_exchange_already_flagged(self, client, mock_query_service):
        """Test flagging an already flagged exchange."""
        mock_query_service.flag_exchange = AsyncMock(return_value=FlagResponse(
            success=True,
            message="Exchange already flagged, note updated",
            flag_id=1
        ))

        response = client.post(
            "/sessions/test-session/exchanges/1/flag",
            json={"note": "Updated note"}
        )

        assert response.status_code == 200
        assert "already flagged" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_flag_exchange_not_found(self, client, mock_query_service):
        """Test flagging non-existent exchange."""
        mock_query_service.flag_exchange = AsyncMock(
            side_effect=ValueError("Exchange 999 not found")
        )

        response = client.post(
            "/sessions/test-session/exchanges/999/flag",
            json={}
        )

        assert response.status_code == 404


class TestUnflagExchange:
    """Test DELETE /sessions/{id}/exchanges/{eid}/flag endpoint."""

    @pytest.mark.asyncio
    async def test_unflag_exchange_success(self, client, mock_query_service):
        """Test successfully unflagging an exchange."""
        mock_query_service.unflag_exchange = AsyncMock(return_value=FlagResponse(
            success=True,
            message="Flag removed successfully",
            flag_id=None
        ))

        response = client.delete("/sessions/test-session/exchanges/1/flag")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["flag_id"] is None

    @pytest.mark.asyncio
    async def test_unflag_not_flagged(self, client, mock_query_service):
        """Test unflagging an exchange that wasn't flagged."""
        mock_query_service.unflag_exchange = AsyncMock(return_value=FlagResponse(
            success=False,
            message="Exchange was not flagged",
            flag_id=None
        ))

        response = client.delete("/sessions/test-session/exchanges/5/flag")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not flagged" in data["message"]


class TestHighlights:
    """Test highlight endpoints."""

    @pytest.mark.asyncio
    async def test_get_highlights_success(self, client, mock_query_service):
        """Test getting all highlights."""
        mock_query_service.get_highlights = AsyncMock(return_value=HighlightList(
            highlights=[
                Highlight(
                    id=1,
                    text="Important quote from paper",
                    page_number=5,
                    exchange_id=None,
                    created_at="2025-01-15T10:00:00"
                ),
                Highlight(
                    id=2,
                    text="Another key finding",
                    page_number=7,
                    exchange_id=3,
                    created_at="2025-01-15T11:00:00"
                )
            ],
            total=2
        ))

        response = client.get("/sessions/test-session/highlights")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["highlights"]) == 2
        assert data["highlights"][0]["text"] == "Important quote from paper"

    @pytest.mark.asyncio
    async def test_get_highlights_empty(self, client, mock_query_service):
        """Test getting highlights when none exist."""
        mock_query_service.get_highlights = AsyncMock(return_value=HighlightList(
            highlights=[],
            total=0
        ))

        response = client.get("/sessions/test-session/highlights")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["highlights"] == []

    @pytest.mark.asyncio
    async def test_add_highlight_success(self, client, mock_query_service):
        """Test adding a highlight."""
        mock_query_service.add_highlight = AsyncMock(return_value=Highlight(
            id=1,
            text="Key finding to remember",
            page_number=10,
            exchange_id=None,
            created_at="2025-01-15T12:00:00"
        ))

        response = client.post(
            "/sessions/test-session/highlights",
            json={
                "text": "Key finding to remember",
                "page_number": 10
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["text"] == "Key finding to remember"
        assert data["page_number"] == 10

    @pytest.mark.asyncio
    async def test_add_highlight_with_exchange(self, client, mock_query_service):
        """Test adding highlight associated with an exchange."""
        mock_query_service.add_highlight = AsyncMock(return_value=Highlight(
            id=2,
            text="Relevant to our discussion",
            page_number=None,
            exchange_id=5,
            created_at="2025-01-15T13:00:00"
        ))

        response = client.post(
            "/sessions/test-session/highlights",
            json={
                "text": "Relevant to our discussion",
                "exchange_id": 5
            }
        )

        assert response.status_code == 201
        assert response.json()["exchange_id"] == 5

    @pytest.mark.asyncio
    async def test_add_highlight_session_not_found(self, client, mock_query_service):
        """Test adding highlight to non-existent session."""
        mock_query_service.add_highlight = AsyncMock(
            side_effect=ValueError("Session not found: invalid-id")
        )

        response = client.post(
            "/sessions/invalid-id/highlights",
            json={"text": "Some text"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_highlight_success(self, client, mock_query_service):
        """Test deleting a highlight."""
        mock_query_service.delete_highlight = AsyncMock(return_value=True)

        response = client.delete("/sessions/test-session/highlights/1")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_highlight_not_found(self, client, mock_query_service):
        """Test deleting non-existent highlight."""
        mock_query_service.delete_highlight = AsyncMock(return_value=False)

        response = client.delete("/sessions/test-session/highlights/999")

        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
