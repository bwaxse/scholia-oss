"""
Main FastAPI application for Paper Companion.
"""

import logging
import time
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException as StarletteHTTPException
from .routes import sessions, queries, zotero, notion, metadata, auth
from .routes import settings as settings_routes
from ..core.database import init_database
from ..core.gemini import is_gemini_available


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles:
    - Database initialization on startup
    - Cleanup on shutdown
    """
    # Startup
    logger.info("Starting Paper Companion API...")
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Paper Companion API...")


# Create FastAPI app
app = FastAPI(
    title="Paper Companion API",
    description="AI-powered academic paper analysis and conversation",
    version="0.1.0",
    lifespan=lifespan
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all requests with timing information.

    Logs:
    - HTTP method and path
    - Client IP
    - Response status code
    - Request duration
    """
    start_time = time.time()

    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    # Process request
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Request failed: {e}")
        raise

    # Log response
    duration = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} "
        f"for {request.method} {request.url.path} "
        f"({duration:.3f}s)"
    )

    return response


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions with consistent JSON response format.

    Returns:
        JSON response with error details
    """
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail} "
        f"for {request.method} {request.url.path}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors with detailed error messages.

    Returns:
        JSON response with validation error details
    """
    logger.warning(
        f"Validation error for {request.method} {request.url.path}: {exc.errors()}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "details": exc.errors(),
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions with generic error response.

    Returns:
        JSON response with generic error message
    """
    logger.error(
        f"Unhandled exception for {request.method} {request.url.path}: {exc}",
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "path": str(request.url.path)
            }
        }
    )


# Include routers BEFORE mounting static files
# This ensures /api/*, /docs, /redoc, /openapi.json take priority
app.include_router(sessions.router)
app.include_router(queries.router)
app.include_router(zotero.router)
app.include_router(notion.router)
app.include_router(metadata.router)
app.include_router(auth.router)
app.include_router(settings_routes.router)


@app.get("/health")
@app.head("/health")
async def health():
    """Health check endpoint for GET and HEAD requests."""
    return {"status": "healthy"}


@app.get("/api/config")
async def get_config():
    """Get application configuration for frontend."""
    return {
        "gemini_available": is_gemini_available(),
        # Note: Zotero/Notion availability is now per-user (check user settings)
    }


# Custom API docs endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """Swagger UI documentation."""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Paper Companion API - Swagger UI"
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """ReDoc documentation."""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="Paper Companion API - ReDoc"
    )


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    """OpenAPI schema endpoint."""
    return get_openapi(
        title="Paper Companion API",
        version="0.1.0",
        description="AI-powered academic paper analysis and conversation",
        routes=app.routes
    )


# Serve static frontend files with SPA fallback
# This MUST come last since it's a catch-all route
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    logger.info(f"Serving static frontend from {frontend_dist}")

    # Mount static assets (js, css, images, etc.)
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html for all non-API routes (SPA fallback)."""
        # Check if it's a static file that exists
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for client-side routing
        return FileResponse(frontend_dist / "index.html")
else:
    logger.warning(f"Frontend dist directory not found at {frontend_dist}")

    @app.get("/")
    async def root():
        """Root endpoint - API health check."""
        return {
            "status": "ok",
            "service": "Paper Companion API",
            "version": "0.1.0",
            "note": "Frontend not available - run 'npm run build' in frontend/"
        }
