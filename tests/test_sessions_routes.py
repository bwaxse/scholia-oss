"""
Tests for session management routes.
"""

import os
import pytest
from fastapi.testclient import TestClient
from io import BytesIO

# Set test environment
os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
os.environ["DATABASE_PATH"] = ":memory:"


@pytest.fixture
def client():
    """Create test client."""
    from fastapi import FastAPI
    from web.api.routes import sessions_router

    app = FastAPI()
    app.include_router(sessions_router)

    return TestClient(app)


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF file content."""
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
    return pdf_content


class TestSessionRoutes:
    """Test session management routes."""

    def test_create_session_no_input(self, client):
        """Test that creating session without file or zotero_key fails."""
        response = client.post("/sessions/new")

        assert response.status_code == 400
        assert "file" in response.json()["detail"] or "zotero_key" in response.json()["detail"]

    def test_create_session_both_inputs(self, client, sample_pdf_bytes):
        """Test that providing both file and zotero_key fails."""
        files = {"file": ("test.pdf", BytesIO(sample_pdf_bytes), "application/pdf")}
        data = {"zotero_key": "ABC123"}

        response = client.post("/sessions/new", files=files, data=data)

        assert response.status_code == 400
        assert "both" in response.json()["detail"].lower()

    def test_list_sessions_default(self, client):
        """Test listing sessions with default parameters."""
        response = client.get("/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert isinstance(data["sessions"], list)
        assert isinstance(data["total"], int)

    def test_list_sessions_with_pagination(self, client):
        """Test listing sessions with pagination."""
        response = client.get("/sessions?limit=10&offset=5")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data

    def test_list_sessions_invalid_limit(self, client):
        """Test that invalid limit is rejected."""
        response = client.get("/sessions?limit=200")  # Too high

        assert response.status_code == 400

    def test_list_sessions_invalid_offset(self, client):
        """Test that negative offset is rejected."""
        response = client.get("/sessions?offset=-1")

        assert response.status_code == 400

    def test_get_session_not_found(self, client):
        """Test getting non-existent session."""
        response = client.get("/sessions/nonexistent_id")

        assert response.status_code == 404

    def test_delete_session_not_found(self, client):
        """Test deleting non-existent session."""
        response = client.delete("/sessions/nonexistent_id")

        assert response.status_code == 404

    def test_export_session_not_found(self, client):
        """Test exporting non-existent session."""
        response = client.get("/sessions/nonexistent_id/export")

        assert response.status_code == 404


class TestSessionRoutesOpenAPI:
    """Test OpenAPI documentation."""

    def test_openapi_schema_generated(self, client):
        """Test that OpenAPI schema is generated."""
        from fastapi import FastAPI
        from web.api.routes import sessions_router

        app = FastAPI()
        app.include_router(sessions_router)

        schema = app.openapi()

        assert schema is not None
        assert "paths" in schema
        assert "/sessions/new" in schema["paths"]
        assert "/sessions" in schema["paths"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
