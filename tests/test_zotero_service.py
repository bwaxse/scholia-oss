"""
Tests for Zotero integration service.
"""

import os
import pytest

from web.services.zotero_service import ZoteroService


# Set test environment variables
@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set test environment variables."""
    os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
    os.environ["DATABASE_PATH"] = ":memory:"
    yield
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("DATABASE_PATH", None)


class TestZoteroService:
    """Test Zotero service basic functionality."""

    def test_not_configured_by_default(self):
        """Test that service is not configured without credentials."""
        service = ZoteroService()
        assert service.is_configured() is False

    def test_configured_with_credentials(self):
        """Test that service is configured when credentials provided."""
        service = ZoteroService(api_key="test_key", library_id="12345")
        assert service.is_configured() is True

    @pytest.mark.asyncio
    async def test_search_papers_not_configured(self):
        """Test that search raises error when not configured."""
        service = ZoteroService()

        with pytest.raises(ValueError, match="Zotero is not configured"):
            await service.search_papers("test query")

    @pytest.mark.asyncio
    async def test_get_paper_by_key_not_configured(self):
        """Test that get_paper raises error when not configured."""
        service = ZoteroService()

        with pytest.raises(ValueError, match="Zotero is not configured"):
            await service.get_paper_by_key("ABC123")

    @pytest.mark.asyncio
    async def test_get_pdf_path_not_configured(self):
        """Test that get_pdf_path raises error when not configured."""
        service = ZoteroService()

        with pytest.raises(ValueError, match="Zotero is not configured"):
            await service.get_pdf_path("ABC123")

    @pytest.mark.asyncio
    async def test_list_recent_not_configured(self):
        """Test that list_recent raises error when not configured."""
        service = ZoteroService()

        with pytest.raises(ValueError, match="Zotero is not configured"):
            await service.list_recent()

    @pytest.mark.asyncio
    async def test_save_insights_not_configured(self):
        """Test that save_insights raises error when not configured."""
        service = ZoteroService()

        with pytest.raises(ValueError, match="Zotero is not configured"):
            await service.save_insights_to_note("ABC123", "<p>Test note</p>")

    @pytest.mark.asyncio
    async def test_get_related_papers_not_configured(self):
        """Test that get_related_papers raises error when not configured."""
        service = ZoteroService()

        with pytest.raises(ValueError, match="Zotero is not configured"):
            await service.get_related_papers(["tag1", "tag2"])

    def test_item_to_summary(self):
        """Test conversion of Zotero item to summary."""
        service = ZoteroService(api_key="test", library_id="123")

        # Create mock Zotero item
        item = {
            "key": "ABC123",
            "data": {
                "title": "Test Paper",
                "creators": [
                    {"lastName": "Doe", "firstName": "John"},
                    {"lastName": "Smith", "firstName": "Jane"}
                ],
                "date": "2023-01-15",
                "publicationTitle": "Test Journal",
                "itemType": "journalArticle"
            }
        }

        summary = service._item_to_summary(item)

        assert summary is not None
        assert summary.key == "ABC123"
        assert summary.title == "Test Paper"
        assert summary.authors == "Doe et al."
        assert summary.year == "2023"
        assert summary.publication == "Test Journal"
        assert summary.item_type == "journalArticle"

    def test_item_to_summary_single_author(self):
        """Test summary with single author."""
        service = ZoteroService(api_key="test", library_id="123")

        item = {
            "key": "ABC123",
            "data": {
                "title": "Test Paper",
                "creators": [{"lastName": "Doe", "firstName": "John"}],
                "date": "2023",
                "itemType": "journalArticle"
            }
        }

        summary = service._item_to_summary(item)

        assert summary is not None
        assert summary.authors == "Doe"

    def test_item_to_summary_organization(self):
        """Test summary with organization as creator."""
        service = ZoteroService(api_key="test", library_id="123")

        item = {
            "key": "ABC123",
            "data": {
                "title": "Test Paper",
                "creators": [{"name": "Test Organization"}],
                "date": "2023",
                "itemType": "report"
            }
        }

        summary = service._item_to_summary(item)

        assert summary is not None
        assert summary.authors == "Test Organization"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
