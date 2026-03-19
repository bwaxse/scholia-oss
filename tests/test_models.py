"""
Tests for Pydantic models.
"""

from datetime import datetime
import pytest
from pydantic import ValidationError

from web.api.models import (
    SessionCreate,
    SessionResponse,
    SessionList,
    SessionListItem,
    SessionDetail,
    ConversationMessage,
    SessionMetadata,
    QueryRequest,
    QueryResponse,
    FlagRequest,
    FlagResponse,
    Highlight,
    HighlightList,
)


class TestSessionModels:
    """Test session-related models."""

    def test_session_create_with_zotero_key(self):
        """Test creating session from Zotero key."""
        session = SessionCreate(zotero_key="ABC123XY")
        assert session.zotero_key == "ABC123XY"

    def test_session_create_invalid_zotero_key(self):
        """Test validation of short Zotero key."""
        with pytest.raises(ValidationError):
            SessionCreate(zotero_key="ABC")  # Too short

    def test_session_response(self):
        """Test session response model."""
        response = SessionResponse(
            session_id="test123",
            filename="paper.pdf",
            initial_analysis="Analysis text",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert response.session_id == "test123"
        assert response.filename == "paper.pdf"

    def test_session_list(self):
        """Test session list model."""
        item = SessionListItem(
            session_id="test123",
            filename="paper.pdf",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session_list = SessionList(sessions=[item], total=1)
        assert len(session_list.sessions) == 1
        assert session_list.total == 1

    def test_session_detail(self):
        """Test detailed session model with conversation."""
        message = ConversationMessage(
            exchange_id=1,
            role="user",
            content="What is the main finding?",
            timestamp=datetime.now(),
        )
        detail = SessionDetail(
            session_id="test123",
            filename="paper.pdf",
            initial_analysis="Analysis",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            conversation=[message],
        )
        assert len(detail.conversation) == 1
        assert detail.conversation[0].role == "user"

    def test_session_metadata(self):
        """Test session metadata model."""
        metadata = SessionMetadata(
            title="Test Paper",
            authors='["Author One", "Author Two"]',
            doi="10.1234/test",
        )
        assert metadata.title == "Test Paper"
        assert metadata.doi == "10.1234/test"


class TestQueryModels:
    """Test query-related models."""

    def test_query_request_valid(self):
        """Test valid query request."""
        request = QueryRequest(query="What is the time complexity?")
        assert request.query == "What is the time complexity?"
        assert request.use_sonnet is True

    def test_query_request_with_highlight(self):
        """Test query with highlighted text."""
        request = QueryRequest(
            query="Explain this",
            highlighted_text="Multi-head attention allows...",
            page_number=5,
        )
        assert request.highlighted_text == "Multi-head attention allows..."
        assert request.page_number == 5

    def test_query_request_empty_validation(self):
        """Test that empty queries are rejected."""
        with pytest.raises(ValidationError):
            QueryRequest(query="")

        with pytest.raises(ValidationError):
            QueryRequest(query="   ")  # Whitespace only

    def test_query_request_too_long(self):
        """Test query length validation."""
        with pytest.raises(ValidationError):
            QueryRequest(query="x" * 2001)  # Exceeds max_length

    def test_query_response(self):
        """Test query response model."""
        response = QueryResponse(
            exchange_id=1,
            response="The time complexity is O(n²d)...",
            model_used="claude-sonnet-4-6",
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        assert response.exchange_id == 1
        assert response.model_used == "claude-sonnet-4-6"

    def test_flag_request(self):
        """Test flag request model."""
        request = FlagRequest(exchange_id=3, note="Important insight")
        assert request.exchange_id == 3
        assert request.note == "Important insight"

    def test_flag_request_no_note(self):
        """Test flag request without note."""
        request = FlagRequest(exchange_id=3)
        assert request.exchange_id == 3
        assert request.note is None

    def test_flag_request_invalid_exchange_id(self):
        """Test that exchange_id must be positive."""
        with pytest.raises(ValidationError):
            FlagRequest(exchange_id=0)

        with pytest.raises(ValidationError):
            FlagRequest(exchange_id=-1)

    def test_flag_response(self):
        """Test flag response model."""
        response = FlagResponse(
            success=True,
            message="Flagged successfully",
            flag_id=42,
        )
        assert response.success is True
        assert response.flag_id == 42

    def test_highlight(self):
        """Test highlight model."""
        highlight = Highlight(
            id=1,
            text="Key passage from paper",
            page_number=5,
            exchange_id=2,
            created_at="2025-11-17T10:30:00Z",
        )
        assert highlight.id == 1
        assert highlight.page_number == 5

    def test_highlight_list(self):
        """Test highlight list model."""
        highlight = Highlight(
            id=1,
            text="Text",
            created_at="2025-11-17T10:30:00Z",
        )
        highlight_list = HighlightList(highlights=[highlight], total=1)
        assert len(highlight_list.highlights) == 1
        assert highlight_list.total == 1


class TestModelSerialization:
    """Test model serialization to JSON."""

    def test_session_response_json(self):
        """Test SessionResponse can be serialized to JSON."""
        response = SessionResponse(
            session_id="test123",
            filename="paper.pdf",
            initial_analysis="Analysis",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        json_data = response.model_dump()
        assert json_data["session_id"] == "test123"

    def test_query_request_json(self):
        """Test QueryRequest can be serialized to JSON."""
        request = QueryRequest(query="Test query")
        json_data = request.model_dump()
        assert json_data["query"] == "Test query"
        assert json_data["use_sonnet"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
