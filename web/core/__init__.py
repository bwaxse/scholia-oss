"""
Core functionality: configuration, database, Claude client, and PDF processing.
"""

from .config import Settings, get_settings
from .database import DatabaseManager, get_db_manager, init_database, get_db
from .pdf_processor import (
    PDFProcessor,
    extract_text,
    extract_metadata,
    extract_outline,
    get_pdf_hash,
    process_pdf,
)

__all__ = [
    "Settings",
    "get_settings",
    "DatabaseManager",
    "get_db_manager",
    "init_database",
    "get_db",
    "PDFProcessor",
    "extract_text",
    "extract_metadata",
    "extract_outline",
    "get_pdf_hash",
    "process_pdf",
]
