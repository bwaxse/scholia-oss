"""
Tests for insight extraction service.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from web.services.insight_extractor import InsightExtractor, get_insight_extractor


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
def mock_database():
    """Mock database with test data."""
    mock_db = MagicMock()

    # Mock session data
    session_row = {
        "session_id": "test-session-123",
        "filename": "test_paper.pdf",
        "initial_analysis": "This paper introduces a novel approach...",
        "created_at": datetime.now().isoformat(),
        "zotero_key": "ABC123"
    }

    # Mock exchanges (conversation)
    exchanges = [
        {"id": 1, "role": "user", "content": "What is the main contribution?", "model_used": "haiku", "created_at": "2025-01-15 10:00:00"},
        {"id": 2, "role": "assistant", "content": "The main contribution is a novel transformer architecture...", "model_used": "haiku", "created_at": "2025-01-15 10:00:05"},
        {"id": 3, "role": "user", "content": "What are the limitations?", "model_used": "haiku", "created_at": "2025-01-15 10:01:00"},
        {"id": 4, "role": "assistant", "content": "The main limitations include small dataset size and...", "model_used": "haiku", "created_at": "2025-01-15 10:01:05"},
    ]

    # Mock flagged exchanges
    flagged = [
        {"id": 2, "role": "assistant", "content": "The main contribution is...", "note": "Key insight", "flag_time": "2025-01-15 10:00:10"},
    ]

    # Mock highlights
    highlights = [
        {"text": "Important finding in section 3", "page_number": 5, "exchange_id": None, "created_at": "2025-01-15 10:05:00"},
        {"text": "Novel methodology described here", "page_number": 3, "exchange_id": 2, "created_at": "2025-01-15 10:06:00"},
    ]

    # Setup mock connection
    async def mock_execute(query, params=None):
        mock_result = MagicMock()

        if "SELECT * FROM sessions" in query:
            mock_result.fetchone = AsyncMock(return_value=session_row)
        elif "FROM exchanges" in query and "flags" not in query:
            mock_result.fetchall = AsyncMock(return_value=exchanges)
        elif "JOIN flags" in query:
            mock_result.fetchall = AsyncMock(return_value=flagged)
        elif "FROM highlights" in query:
            mock_result.fetchall = AsyncMock(return_value=highlights)

        return mock_result

    mock_conn = MagicMock()
    mock_conn.execute = mock_execute
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    mock_db.get_connection = MagicMock(return_value=mock_conn)

    return mock_db


@pytest.fixture
def mock_claude_client():
    """Mock Claude client."""
    mock_client = MagicMock()

    # Mock successful extraction response
    sample_insights_json = """{
        "bibliographic": {
            "title": "Attention Is All You Need",
            "authors": ["Vaswani et al."],
            "journal": "NeurIPS",
            "year": "2017",
            "doi": "10.1234/example"
        },
        "strengths": [
            "Novel transformer architecture",
            "Strong empirical results"
        ],
        "weaknesses": [
            "Limited dataset diversity",
            "High computational cost"
        ],
        "methodological_notes": [
            "Uses multi-head attention mechanism",
            "Self-attention allows parallel processing"
        ],
        "statistical_concerns": [],
        "theoretical_contributions": [
            "Eliminates recurrence in sequence modeling"
        ],
        "empirical_findings": [
            "Achieves state-of-the-art on WMT translation"
        ],
        "questions_raised": [
            "How does this scale to longer sequences?"
        ],
        "applications": [
            "Machine translation",
            "Text generation"
        ],
        "connections": [
            "Builds on attention mechanisms from Bahdanau et al."
        ],
        "critiques": [],
        "surprising_elements": [
            "No recurrence needed for strong performance"
        ],
        "key_quotes": [
            {
                "user": "What is the main contribution?",
                "assistant": "The main contribution is a novel transformer architecture...",
                "theme": "architecture",
                "note": "Key architectural innovation"
            }
        ],
        "custom_themes": {
            "efficiency": ["Parallel processing capability"]
        },
        "highlight_suggestions": {
            "critical_passages": ["Section 3.2 on multi-head attention"],
            "methodological_details": ["Positional encoding description"]
        }
    }"""

    mock_client.query = AsyncMock(return_value={
        "content": sample_insights_json
    })

    return mock_client


class TestInsightExtractor:
    """Test InsightExtractor class."""

    @pytest.mark.asyncio
    async def test_extract_insights_success(self, mock_database, mock_claude_client):
        """Test successful insight extraction."""
        extractor = InsightExtractor(
            claude_client=mock_claude_client,
            database=mock_database
        )

        insights = await extractor.extract_insights("test-session-123")

        # Verify insights structure
        assert "bibliographic" in insights
        assert "strengths" in insights
        assert "weaknesses" in insights
        assert "metadata" in insights

        # Verify bibliographic info
        assert insights["bibliographic"]["title"] == "Attention Is All You Need"
        assert insights["bibliographic"]["year"] == "2017"

        # Verify insights content
        assert len(insights["strengths"]) == 2
        assert "Novel transformer architecture" in insights["strengths"]

        # Verify metadata
        assert insights["metadata"]["session_id"] == "test-session-123"
        assert insights["metadata"]["filename"] == "test_paper.pdf"
        assert insights["metadata"]["total_exchanges"] == 2  # 4 messages / 2
        assert insights["metadata"]["flagged_count"] == 1
        assert insights["metadata"]["highlights_count"] == 2

    @pytest.mark.asyncio
    async def test_extract_insights_session_not_found(self, mock_database, mock_claude_client):
        """Test extraction with non-existent session."""
        # Mock no session found
        async def mock_execute_not_found(query, params=None):
            mock_result = MagicMock()
            mock_result.fetchone = AsyncMock(return_value=None)
            return mock_result

        mock_conn = MagicMock()
        mock_conn.execute = mock_execute_not_found
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_database.get_connection = MagicMock(return_value=mock_conn)

        extractor = InsightExtractor(
            claude_client=mock_claude_client,
            database=mock_database
        )

        with pytest.raises(ValueError, match="Session not found"):
            await extractor.extract_insights("invalid-session")

    @pytest.mark.asyncio
    async def test_extract_insights_with_malformed_json(self, mock_database):
        """Test extraction when Claude returns malformed JSON."""
        # Mock Claude client returning invalid JSON
        bad_claude = MagicMock()
        bad_claude.query = AsyncMock(return_value={
            "content": "This is not valid JSON"
        })

        extractor = InsightExtractor(
            claude_client=bad_claude,
            database=mock_database
        )

        insights = await extractor.extract_insights("test-session-123")

        # Should have fallback structure
        assert "extraction_error" in insights
        assert insights["extraction_error"] == "Failed to parse structured insights"
        assert "bibliographic" in insights
        assert "strengths" in insights

    @pytest.mark.asyncio
    async def test_format_conversation(self, mock_database, mock_claude_client):
        """Test conversation formatting."""
        extractor = InsightExtractor(
            claude_client=mock_claude_client,
            database=mock_database
        )

        exchanges = [
            {"id": 1, "role": "user", "content": "Question 1?"},
            {"id": 2, "role": "assistant", "content": "Answer 1"},
            {"id": 3, "role": "user", "content": "Question 2?"},
            {"id": 4, "role": "assistant", "content": "Answer 2"},
        ]

        formatted = extractor._format_conversation(exchanges)

        assert "User: Question 1?" in formatted
        assert "Assistant: Answer 1" in formatted
        assert "User: Question 2?" in formatted

    @pytest.mark.asyncio
    async def test_format_flagged_exchanges(self, mock_database, mock_claude_client):
        """Test flagged exchange formatting."""
        extractor = InsightExtractor(
            claude_client=mock_claude_client,
            database=mock_database
        )

        all_exchanges = [
            {"id": 1, "role": "user", "content": "What is X?"},
            {"id": 2, "role": "assistant", "content": "X is..."},
        ]

        flagged = [
            {"id": 2, "role": "assistant", "note": "Important", "flag_time": "2025-01-15"}
        ]

        formatted = extractor._format_flagged_exchanges(all_exchanges, flagged)

        assert "FLAGGED" in formatted
        assert "Important" in formatted
        assert "What is X?" in formatted

    @pytest.mark.asyncio
    async def test_format_highlights(self, mock_database, mock_claude_client):
        """Test highlight formatting."""
        extractor = InsightExtractor(
            claude_client=mock_claude_client,
            database=mock_database
        )

        highlights = [
            {"text": "Key finding", "page_number": 5, "created_at": "2025-01-15"},
            {"text": "Important quote", "page_number": None, "created_at": "2025-01-15"},
        ]

        formatted = extractor._format_highlights(highlights)

        assert "Key finding (page 5)" in formatted
        assert "Important quote" in formatted

    def test_format_highlights_empty(self, mock_claude_client):
        """Test formatting with no highlights."""
        extractor = InsightExtractor(claude_client=mock_claude_client)

        formatted = extractor._format_highlights([])

        assert formatted == "(No highlights)"


class TestFormatInsightsHTML:
    """Test HTML formatting."""

    def test_format_insights_html_complete(self):
        """Test HTML formatting with complete insights."""
        insights = {
            "bibliographic": {
                "title": "Test Paper",
                "authors": "Smith et al.",
                "journal": "Nature",
                "year": "2024",
                "doi": "10.1234/test"
            },
            "strengths": ["Strong methodology", "Novel approach"],
            "weaknesses": ["Small sample size"],
            "methodological_notes": ["Uses XYZ method"],
            "key_quotes": [
                {
                    "user": "What is X?",
                    "assistant": "X is...",
                    "theme": "methodology",
                    "note": "Key insight"
                }
            ],
            "highlight_suggestions": {
                "critical_passages": ["Section 3"],
                "methodological_details": ["Appendix A"]
            },
            "custom_themes": {
                "efficiency": ["Fast processing"]
            },
            "metadata": {
                "filename": "test.pdf",
                "total_exchanges": 5,
                "flagged_count": 2,
                "highlights_count": 3,
                "extracted_at": "2025-01-15T10:00:00"
            }
        }

        html = InsightExtractor.format_insights_html(insights)

        # Check structure
        assert "📚 Paper Insights" in html
        assert "📄 Paper Information" in html
        assert "Test Paper" in html
        assert "Smith et al." in html

        # Check themes
        assert "💪 Strengths" in html
        assert "Strong methodology" in html
        assert "⚠️ Weaknesses" in html
        assert "Small sample size" in html

        # Check quotes
        assert "💬 Key Exchanges" in html
        assert "What is X?" in html

        # Check highlights
        assert "📝 Suggested Highlights" in html
        assert "Section 3" in html

        # Check custom themes
        assert "🎨 Session-Specific Themes" in html
        assert "Efficiency" in html

        # Check metadata footer
        assert "test.pdf" in html
        assert "Total exchanges: 5" in html

    def test_format_insights_html_minimal(self):
        """Test HTML formatting with minimal insights."""
        insights = {
            "metadata": {
                "filename": "minimal.pdf",
                "total_exchanges": 1,
                "flagged_count": 0,
                "highlights_count": 0
            }
        }

        html = InsightExtractor.format_insights_html(insights)

        # Should still have basic structure
        assert "📚 Paper Insights" in html
        assert "minimal.pdf" in html
        assert "Total exchanges: 1" in html

    def test_format_insights_html_empty_sections(self):
        """Test that empty sections are not displayed."""
        insights = {
            "strengths": [],
            "weaknesses": [],
            "metadata": {"filename": "test.pdf"}
        }

        html = InsightExtractor.format_insights_html(insights)

        # Empty sections should not appear
        assert "💪 Strengths" not in html
        assert "⚠️ Weaknesses" not in html


class TestSingleton:
    """Test singleton pattern."""

    def test_get_insight_extractor_singleton(self):
        """Test that get_insight_extractor returns same instance."""
        extractor1 = get_insight_extractor()
        extractor2 = get_insight_extractor()

        assert extractor1 is extractor2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
