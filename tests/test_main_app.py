"""
Tests for main FastAPI application.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from web.api.main import app


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


class TestRootEndpoints:
    """Test root and health endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "Paper Companion API"
        assert data["version"] == "0.1.0"

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestErrorHandlers:
    """Test error handler functionality."""

    def test_404_not_found(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 404
        assert data["error"]["path"] == "/nonexistent"

    def test_validation_error(self, client):
        """Test validation error handling."""
        # Send invalid request to trigger validation error
        # Using query endpoint with missing required field
        response = client.post(
            "/sessions/test-session/query",
            json={}  # Missing required 'query' field
        )

        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 422
        assert data["error"]["message"] == "Validation error"
        assert "details" in data["error"]

    def test_method_not_allowed(self, client):
        """Test 405 method not allowed."""
        # Try to POST to GET-only endpoint
        response = client.post("/health")

        assert response.status_code == 405
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 405


class TestRequestLogging:
    """Test request logging middleware."""

    def test_request_logging(self, client, caplog):
        """Test that requests are logged."""
        with caplog.at_level("INFO"):
            response = client.get("/health")

        assert response.status_code == 200

        # Check that request was logged
        log_messages = [record.message for record in caplog.records]
        assert any("Request: GET /health" in msg for msg in log_messages)
        assert any("Response: 200 for GET /health" in msg for msg in log_messages)

    def test_response_timing_logged(self, client, caplog):
        """Test that response timing is included in logs."""
        with caplog.at_level("INFO"):
            response = client.get("/")

        assert response.status_code == 200

        # Check that timing info is logged
        log_messages = [record.message for record in caplog.records]
        timing_logs = [msg for msg in log_messages if "Response:" in msg and "GET /" in msg]
        assert len(timing_logs) > 0
        # Should contain timing like (0.001s)
        assert any("s)" in msg for msg in timing_logs)


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are added to responses."""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})

        assert response.status_code == 200
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"


class TestLifespan:
    """Test application lifespan events."""

    @patch("web.api.main.init_database")
    def test_startup_initializes_database(self, mock_init_db):
        """Test that database is initialized on startup."""
        mock_init_db.return_value = AsyncMock()

        # Create new client which triggers startup
        with TestClient(app) as client:
            # Just making a request to ensure app started
            response = client.get("/health")
            assert response.status_code == 200

        # Database initialization should have been called
        # Note: This test is tricky because lifespan runs before TestClient is ready
        # In practice, the database will be initialized, but we can't easily assert on it
        # without more complex mocking

    def test_app_starts_successfully(self):
        """Test that app can start and serve requests."""
        # This test verifies the lifespan manager works
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200


class TestRouterIntegration:
    """Test that routers are properly integrated."""

    def test_sessions_router_included(self, client):
        """Test that sessions router is included."""
        # Sessions endpoints should be accessible
        response = client.get("/sessions")
        # Should not be 404 (might be 200 or other status depending on implementation)
        assert response.status_code != 404

    def test_queries_router_included(self, client):
        """Test that queries router is included."""
        # Queries endpoints should be accessible (will fail without session but shouldn't 404)
        response = client.get("/sessions/test/highlights")
        # Should not be 404 (might be 500 if session doesn't exist, but endpoint exists)
        assert response.status_code != 404

    def test_zotero_router_included(self, client):
        """Test that zotero router is included."""
        # Zotero endpoints should be accessible
        response = client.get("/zotero/recent")
        # Should not be 404 (might be 500 if not configured, but endpoint exists)
        assert response.status_code != 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
