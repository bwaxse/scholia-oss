"""
FastAPI route modules for Scholia API.
"""

from .sessions import router as sessions_router
from .queries import router as queries_router
from .zotero import router as zotero_router
from .notion import router as notion_router
from .metadata import router as metadata_router
from .auth import router as auth_router
from .settings import router as settings_router

__all__ = [
    "sessions_router",
    "queries_router",
    "zotero_router",
    "notion_router",
    "metadata_router",
    "auth_router",
    "settings_router",
]
