"""
Tests for Zotero routes.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from web.api.main import app
from web.api.models import (
    ZoteroItemSummary,
    ZoteroItem,
    ZoteroItemData,
    ZoteroCreator,
    SessionResponse,
)


# Set test environment variables
@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set test environment variables."""
    os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
    os.environ["DATABASE_PATH"] = ":memory:"
    os.environ["ZOTERO_API_KEY"] = "test-zotero-key"
    os.environ["ZOTERO_LIBRARY_ID"] = "12345"
    yield
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("DATABASE_PATH", None)
    os.environ.pop("ZOTERO_API_KEY", None)
    os.environ.pop("ZOTERO_LIBRARY_ID", None)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_zotero_service():
    """Mock Zotero service for testing."""
    with patch("web.api.routes.zotero.get_zotero_service") as mock:
        service = MagicMock()
        service.is_configured.return_value = True
        mock.return_value = service
        yield service


@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing."""
    with patch("web.api.routes.zotero.get_session_manager") as mock:
        manager = MagicMock()
        mock.return_value = manager
        yield manager


@pytest.fixture
def sample_zotero_items():
    """Sample Zotero items for testing."""
    return [
        ZoteroItemSummary(
            key="ABC123",
            title="Attention Is All You Need",
            authors="Vaswani et al.",
            year="2017",
            publication="arXiv",
            item_type="journalArticle"
        ),
        ZoteroItemSummary(
            key="DEF456",
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            authors="Devlin et al.",
            year="2018",
            publication="arXiv",
            item_type="journalArticle"
        )
    ]


@pytest.fixture
def sample_zotero_item():
    """Sample complete Zotero item for testing."""
    return ZoteroItem(
        key="ABC123",
        version=123,
        library={"type": "user", "id": 12345},
        data=ZoteroItemData(
            key="ABC123",
            version=123,
            itemType="journalArticle",
            title="Attention Is All You Need",
            creators=[
                ZoteroCreator(
                    creatorType="author",
                    firstName="Ashish",
                    lastName="Vaswani"
                )
            ],
            abstractNote="The dominant sequence transduction models...",
            publicationTitle="arXiv",
            date="2017-06",
            DOI="10.48550/arXiv.1706.03762",
            tags=[]
        )
    )


class TestSearchZotero:
    """Test GET /zotero/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_success(self, client, mock_zotero_service, sample_zotero_items):
        """Test successful search."""
        mock_zotero_service.search_papers = AsyncMock(return_value=sample_zotero_items)

        response = client.get("/zotero/search?query=transformer&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["title"] == "Attention Is All You Need"
        assert data["items"][0]["key"] == "ABC123"

        # Verify service called correctly
        mock_zotero_service.search_papers.assert_called_once_with(query="transformer", limit=10)

    @pytest.mark.asyncio
    async def test_search_no_results(self, client, mock_zotero_service):
        """Test search with no results."""
        mock_zotero_service.search_papers = AsyncMock(return_value=[])

        response = client.get("/zotero/search?query=nonexistent&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_search_not_configured(self, client, mock_zotero_service):
        """Test search when Zotero not configured."""
        mock_zotero_service.is_configured.return_value = False

        response = client.get("/zotero/search?query=test")

        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_search_missing_query(self, client, mock_zotero_service):
        """Test search without query parameter."""
        response = client.get("/zotero/search")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_custom_limit(self, client, mock_zotero_service, sample_zotero_items):
        """Test search with custom limit."""
        mock_zotero_service.search_papers = AsyncMock(return_value=sample_zotero_items[:1])

        response = client.get("/zotero/search?query=attention&limit=1")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        mock_zotero_service.search_papers.assert_called_once_with(query="attention", limit=1)


class TestListRecentPapers:
    """Test GET /zotero/recent endpoint."""

    @pytest.mark.asyncio
    async def test_list_recent_success(self, client, mock_zotero_service, sample_zotero_items):
        """Test successfully listing recent papers."""
        mock_zotero_service.list_recent = AsyncMock(return_value=sample_zotero_items)

        response = client.get("/zotero/recent")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Attention Is All You Need"

        # Verify default limit used
        mock_zotero_service.list_recent.assert_called_once_with(limit=20)

    @pytest.mark.asyncio
    async def test_list_recent_custom_limit(self, client, mock_zotero_service, sample_zotero_items):
        """Test listing recent papers with custom limit."""
        mock_zotero_service.list_recent = AsyncMock(return_value=sample_zotero_items[:1])

        response = client.get("/zotero/recent?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        mock_zotero_service.list_recent.assert_called_once_with(limit=5)

    @pytest.mark.asyncio
    async def test_list_recent_not_configured(self, client, mock_zotero_service):
        """Test listing when Zotero not configured."""
        mock_zotero_service.is_configured.return_value = False

        response = client.get("/zotero/recent")

        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_recent_empty(self, client, mock_zotero_service):
        """Test listing when library is empty."""
        mock_zotero_service.list_recent = AsyncMock(return_value=[])

        response = client.get("/zotero/recent")

        assert response.status_code == 200
        assert response.json() == []


class TestGetPaperDetails:
    """Test GET /zotero/paper/{key} endpoint."""

    @pytest.mark.asyncio
    async def test_get_paper_success(self, client, mock_zotero_service, sample_zotero_item):
        """Test successfully getting paper details."""
        mock_zotero_service.get_paper_by_key = AsyncMock(return_value=sample_zotero_item)

        response = client.get("/zotero/paper/ABC123")

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "ABC123"
        assert data["data"]["title"] == "Attention Is All You Need"
        assert data["data"]["DOI"] == "10.48550/arXiv.1706.03762"

        mock_zotero_service.get_paper_by_key.assert_called_once_with("ABC123")

    @pytest.mark.asyncio
    async def test_get_paper_not_found(self, client, mock_zotero_service):
        """Test getting non-existent paper."""
        mock_zotero_service.get_paper_by_key = AsyncMock(return_value=None)

        response = client.get("/zotero/paper/INVALID")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_paper_not_configured(self, client, mock_zotero_service):
        """Test getting paper when Zotero not configured."""
        mock_zotero_service.is_configured.return_value = False

        response = client.get("/zotero/paper/ABC123")

        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]


class TestSaveInsights:
    """Test POST /zotero/save-insights endpoint."""

    @pytest.mark.asyncio
    async def test_save_insights_success(self, client, mock_zotero_service, mock_session_manager):
        """Test successfully saving insights."""
        # Mock session data
        mock_session_manager.get_session = AsyncMock(return_value=SessionResponse(
            session_id="test-session-123",
            filename="test.pdf",
            initial_analysis="This paper introduces a novel approach...",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            page_count=10
        ))

        # Mock Zotero save
        mock_zotero_service.save_insights_to_note = AsyncMock(return_value=True)

        response = client.post(
            "/zotero/save-insights",
            json={
                "session_id": "test-session-123",
                "parent_item_key": "ABC123",
                "tags": ["claude-analyzed"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully" in data["message"]

        # Verify service called
        mock_zotero_service.save_insights_to_note.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_insights_session_not_found(self, client, mock_zotero_service, mock_session_manager):
        """Test saving insights for non-existent session."""
        mock_session_manager.get_session = AsyncMock(return_value=None)

        response = client.post(
            "/zotero/save-insights",
            json={
                "session_id": "invalid-session",
                "parent_item_key": "ABC123",
                "tags": []
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_save_insights_zotero_failure(self, client, mock_zotero_service, mock_session_manager):
        """Test when Zotero save fails."""
        # Mock session data
        mock_session_manager.get_session = AsyncMock(return_value=SessionResponse(
            session_id="test-session-123",
            filename="test.pdf",
            initial_analysis="Analysis...",
            created_at=datetime.now(),
            updated_at=datetime.now()
        ))

        # Mock Zotero save failure
        mock_zotero_service.save_insights_to_note = AsyncMock(return_value=False)

        response = client.post(
            "/zotero/save-insights",
            json={
                "session_id": "test-session-123",
                "parent_item_key": "ABC123",
                "tags": []
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Failed" in data["message"]

    @pytest.mark.asyncio
    async def test_save_insights_not_configured(self, client, mock_zotero_service, mock_session_manager):
        """Test saving insights when Zotero not configured."""
        mock_zotero_service.is_configured.return_value = False

        response = client.post(
            "/zotero/save-insights",
            json={
                "session_id": "test-session",
                "parent_item_key": "ABC123",
                "tags": []
            }
        )

        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]


class TestGetRelatedPapers:
    """Test GET /zotero/related endpoint."""

    @pytest.mark.asyncio
    async def test_get_related_success(self, client, mock_zotero_service, sample_zotero_items):
        """Test successfully finding related papers."""
        mock_zotero_service.get_related_papers = AsyncMock(return_value=sample_zotero_items)

        response = client.get("/zotero/related?tags=transformer,attention&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["key"] == "ABC123"

        # Verify tags parsed correctly
        mock_zotero_service.get_related_papers.assert_called_once()
        call_args = mock_zotero_service.get_related_papers.call_args
        assert call_args[1]["tags"] == ["transformer", "attention"]
        assert call_args[1]["limit"] == 5

    @pytest.mark.asyncio
    async def test_get_related_single_tag(self, client, mock_zotero_service, sample_zotero_items):
        """Test finding related papers with single tag."""
        mock_zotero_service.get_related_papers = AsyncMock(return_value=sample_zotero_items[:1])

        response = client.get("/zotero/related?tags=nlp")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        call_args = mock_zotero_service.get_related_papers.call_args
        assert call_args[1]["tags"] == ["nlp"]

    @pytest.mark.asyncio
    async def test_get_related_empty_tags(self, client, mock_zotero_service):
        """Test with empty tag string."""
        response = client.get("/zotero/related?tags=")

        assert response.status_code == 400
        assert "required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_related_missing_tags(self, client, mock_zotero_service):
        """Test without tags parameter."""
        response = client.get("/zotero/related")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_related_not_configured(self, client, mock_zotero_service):
        """Test finding related papers when Zotero not configured."""
        mock_zotero_service.is_configured.return_value = False

        response = client.get("/zotero/related?tags=test")

        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_related_no_results(self, client, mock_zotero_service):
        """Test when no related papers found."""
        mock_zotero_service.get_related_papers = AsyncMock(return_value=[])

        response = client.get("/zotero/related?tags=nonexistent")

        assert response.status_code == 200
        assert response.json() == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
