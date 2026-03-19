"""
Pydantic models for Paper Companion API.
"""

from .session import (
    SessionCreate,
    SessionResponse,
    SessionListItem,
    SessionList,
    SessionDetail,
    ConversationMessage,
    SessionMetadata,
    ExistingSessionInfo,
    DuplicateCheckResponse,
)

from .query import (
    QueryRequest,
    QueryResponse,
    FlagRequest,
    FlagResponse,
    Highlight,
    HighlightList,
    MessageEvaluationRequest,
    MessageEvaluationResponse,
)

from .zotero import (
    ZoteroItem,
    ZoteroItemSummary,
    ZoteroItemData,
    ZoteroCreator,
    ZoteroTag,
    ZoteroSearchRequest,
    ZoteroSearchResponse,
    ZoteroNoteRequest,
    ZoteroNoteResponse,
)

from .notion import (
    NotionAuthResponse,
    NotionProject,
    NotionProjectList,
    NotionProjectContext,
    NotionRelevanceResponse,
    NotionContentResponse,
    NotionExportResponse,
)

from .metadata import (
    MetadataLookupRequest,
    MetadataResponse,
    MetadataUpdateRequest,
    MetadataUpdateResponse,
)

__all__ = [
    # Session models
    "SessionCreate",
    "SessionResponse",
    "SessionListItem",
    "SessionList",
    "SessionDetail",
    "ConversationMessage",
    "SessionMetadata",
    "ExistingSessionInfo",
    "DuplicateCheckResponse",
    # Query models
    "QueryRequest",
    "QueryResponse",
    "FlagRequest",
    "FlagResponse",
    "Highlight",
    "HighlightList",
    "MessageEvaluationRequest",
    "MessageEvaluationResponse",
    # Zotero models
    "ZoteroItem",
    "ZoteroItemSummary",
    "ZoteroItemData",
    "ZoteroCreator",
    "ZoteroTag",
    "ZoteroSearchRequest",
    "ZoteroSearchResponse",
    "ZoteroNoteRequest",
    "ZoteroNoteResponse",
    # Notion models
    "NotionAuthResponse",
    "NotionProject",
    "NotionProjectList",
    "NotionProjectContext",
    "NotionRelevanceResponse",
    "NotionContentResponse",
    "NotionExportResponse",
    # Metadata models
    "MetadataLookupRequest",
    "MetadataResponse",
    "MetadataUpdateRequest",
    "MetadataUpdateResponse",
]
