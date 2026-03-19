"""
Business logic services for Scholia.
"""

from .session_manager import (
    SessionManager,
    get_session_manager,
    create_session_from_pdf,
    get_session,
    list_sessions,
    delete_session,
)

from .zotero_service import (
    ZoteroService,
    get_zotero_service_for_user,
)

from .query_service import (
    QueryService,
    get_query_service,
)

from .insight_extractor import (
    InsightExtractor,
    get_insight_extractor,
)

from .notion_client import (
    NotionClient,
    get_notion_client,
    get_notion_client_for_user,
)

from .notion_exporter import (
    NotionExporter,
    get_notion_exporter,
)

from .usage_tracker import (
    UsageTracker,
    get_usage_tracker,
)

__all__ = [
    # Session management
    "SessionManager",
    "get_session_manager",
    "create_session_from_pdf",
    "get_session",
    "list_sessions",
    "delete_session",
    # Zotero integration
    "ZoteroService",
    "get_zotero_service_for_user",
    # Query service
    "QueryService",
    "get_query_service",
    # Insight extraction
    "InsightExtractor",
    "get_insight_extractor",
    # Notion integration
    "NotionClient",
    "get_notion_client",
    "get_notion_client_for_user",
    "NotionExporter",
    "get_notion_exporter",
    # Usage tracking
    "UsageTracker",
    "get_usage_tracker",
]
