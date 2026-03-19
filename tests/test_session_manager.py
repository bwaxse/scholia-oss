"""
Tests for session management service.
"""

import os
import tempfile
from pathlib import Path
from io import BytesIO
import pytest
import pytest_asyncio
from fastapi import UploadFile

from web.services.session_manager import SessionManager, get_session_manager
from web.core.database import DatabaseManager


# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


# Set required environment variables for tests
@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set test environment variables."""
    os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
    os.environ["DATABASE_PATH"] = ":memory:"
    yield
    # Clean up
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("DATABASE_PATH", None)


@pytest_asyncio.fixture
async def test_db():
    """Create test database in memory."""
    db = DatabaseManager(":memory:")
    await db.initialize()
    yield db


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing."""
    # Create a minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
409
%%EOF
"""

    # Create UploadFile from bytes
    file = BytesIO(pdf_content)
    upload_file = UploadFile(
        filename="test_paper.pdf",
        file=file
    )
    return upload_file


class TestSessionManagerBasics:
    """Test basic session manager functionality."""

    async def test_generate_session_id(self, test_db):
        """Test session ID generation."""
        session_manager = SessionManager(db_manager=test_db)
        session_id1 = session_manager._generate_session_id()
        session_id2 = session_manager._generate_session_id()

        # IDs should be non-empty strings
        assert isinstance(session_id1, str)
        assert len(session_id1) > 0

        # IDs should be unique
        assert session_id1 != session_id2

    async def test_create_session_invalid_file(self, test_db):
        """Test that non-PDF files are rejected."""
        session_manager = SessionManager(db_manager=test_db)

        # Create non-PDF file
        file = BytesIO(b"Not a PDF")
        upload_file = UploadFile(filename="test.txt", file=file)

        with pytest.raises(ValueError, match="File must be a PDF"):
            await session_manager.create_session_from_pdf(upload_file)

    async def test_create_session_from_zotero_not_implemented(self, test_db):
        """Test that Zotero integration raises NotImplementedError."""
        session_manager = SessionManager(db_manager=test_db)

        with pytest.raises(NotImplementedError):
            await session_manager.create_session_from_zotero("ABC123XY")

    async def test_get_session_not_found(self, test_db):
        """Test getting non-existent session."""
        session_manager = SessionManager(db_manager=test_db)
        result = await session_manager.get_session("nonexistent_id")
        assert result is None

    async def test_list_sessions_empty(self, test_db):
        """Test listing sessions when database is empty."""
        session_manager = SessionManager(db_manager=test_db)
        result = await session_manager.list_sessions()

        assert result.total == 0
        assert len(result.sessions) == 0

    async def test_list_sessions_with_pagination(self, test_db):
        """Test session listing with pagination parameters."""
        session_manager = SessionManager(db_manager=test_db)
        result = await session_manager.list_sessions(limit=10, offset=0)

        assert isinstance(result.total, int)
        assert isinstance(result.sessions, list)

    async def test_delete_session_not_found(self, test_db):
        """Test deleting non-existent session."""
        session_manager = SessionManager(db_manager=test_db)
        result = await session_manager.delete_session("nonexistent_id")
        assert result is False

    async def test_restore_session(self, test_db):
        """Test session restoration."""
        session_manager = SessionManager(db_manager=test_db)
        # Restore is an alias for get_session
        result = await session_manager.restore_session("nonexistent_id")
        assert result is None

    async def test_get_session_text_not_found(self, test_db):
        """Test getting text for non-existent session."""
        session_manager = SessionManager(db_manager=test_db)
        result = await session_manager.get_session_text("nonexistent_id")
        assert result is None

    async def test_update_session_timestamp(self, test_db):
        """Test updating session timestamp."""
        session_manager = SessionManager(db_manager=test_db)
        # Should not raise error even if session doesn't exist
        await session_manager.update_session_timestamp("nonexistent_id")


class TestSessionManagerSingleton:
    """Test session manager singleton pattern."""

    def test_get_session_manager_singleton(self):
        """Test that get_session_manager returns same instance."""
        manager1 = get_session_manager()
        manager2 = get_session_manager()

        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
