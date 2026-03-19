"""
Pydantic models for session management.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SessionCreate(BaseModel):
    """
    Request model for creating a new session.

    Supports two modes:
    1. PDF upload: Provide file via multipart/form-data
    2. Zotero: Provide zotero_key
    """
    zotero_key: Optional[str] = Field(
        default=None,
        description="Zotero item key to load paper from library"
    )

    # Note: PDF upload is handled separately via UploadFile in FastAPI route
    # This model is used when creating from Zotero

    @field_validator("zotero_key")
    @classmethod
    def validate_zotero_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate Zotero key format if provided."""
        if v is not None and v.strip():
            # Zotero keys are typically 8-character alphanumeric
            key = v.strip()
            if len(key) < 6:
                raise ValueError("Zotero key must be at least 6 characters")
            return key
        return None


class SessionResponse(BaseModel):
    """
    Response model for session information.
    Returned after creating or retrieving a session.
    """
    session_id: str = Field(description="Unique session identifier")
    filename: str = Field(description="Original PDF filename")
    initial_analysis: str = Field(description="Claude's initial analysis of the paper")
    created_at: datetime = Field(description="Session creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    zotero_key: Optional[str] = Field(default=None, description="Zotero item key if loaded from Zotero")
    page_count: Optional[int] = Field(default=None, description="Number of pages in PDF")
    file_size_bytes: Optional[int] = Field(default=None, description="PDF file size in bytes")
    label: Optional[str] = Field(default=None, description="User label to distinguish multiple sessions for same paper")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "abc123def456",
                "filename": "attention_is_all_you_need.pdf",
                "initial_analysis": "**Core Innovation**: Transformer architecture...",
                "created_at": "2025-11-17T10:30:00Z",
                "updated_at": "2025-11-17T10:30:00Z",
                "zotero_key": "ABC123XY",
                "page_count": 15,
                "file_size_bytes": 2456789
            }
        }
    )


class SessionListItem(BaseModel):
    """
    Lightweight session info for list views.
    Excludes large fields like initial_analysis.
    """
    session_id: str
    filename: str
    created_at: datetime
    updated_at: datetime
    zotero_key: Optional[str] = None
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None
    label: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    journal_abbr: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "abc123def456",
                "filename": "attention_is_all_you_need.pdf",
                "created_at": "2025-11-17T10:30:00Z",
                "updated_at": "2025-11-17T10:30:00Z",
                "zotero_key": "ABC123XY",
                "page_count": 15,
                "file_size_bytes": 2456789
            }
        }
    )


class SessionList(BaseModel):
    """
    Response model for listing sessions.
    """
    sessions: List[SessionListItem] = Field(description="List of sessions")
    total: int = Field(description="Total number of sessions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sessions": [
                    {
                        "session_id": "abc123",
                        "filename": "paper1.pdf",
                        "created_at": "2025-11-17T10:30:00Z",
                        "updated_at": "2025-11-17T10:30:00Z",
                        "page_count": 15
                    }
                ],
                "total": 1
            }
        }
    )


class ExistingSessionInfo(BaseModel):
    """Info about an existing session for duplicate detection."""
    session_id: str
    created_at: datetime
    label: Optional[str] = None
    exchange_count: int = Field(default=0, description="Number of Q&A exchanges")


class DuplicateCheckResponse(BaseModel):
    """
    Response for checking if sessions already exist for a Zotero item.
    """
    exists: bool = Field(description="Whether sessions exist for this Zotero item")
    count: int = Field(description="Number of existing sessions")
    sessions: List[ExistingSessionInfo] = Field(
        default_factory=list,
        description="List of existing sessions"
    )
    paper_title: Optional[str] = Field(default=None, description="Paper title from metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exists": True,
                "count": 2,
                "sessions": [
                    {"session_id": "abc123", "created_at": "2025-01-01T10:00:00Z", "label": "Initial read", "exchange_count": 5},
                    {"session_id": "def456", "created_at": "2025-01-02T14:00:00Z", "label": None, "exchange_count": 3}
                ],
                "paper_title": "Attention Is All You Need"
            }
        }
    )


class ConversationMessage(BaseModel):
    """
    Model for a single conversation message.
    """
    exchange_id: int = Field(description="Exchange number in conversation")
    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")
    model: Optional[str] = Field(default=None, description="Claude model used (for assistant messages)")
    highlighted_text: Optional[str] = Field(default=None, description="Text highlighted by user")
    page_number: Optional[int] = Field(default=None, description="Page reference")
    timestamp: datetime = Field(description="Message timestamp")


class SessionDetail(BaseModel):
    """
    Detailed session information including full conversation history.
    Used for session restoration and full session views.
    """
    session_id: str
    filename: str
    initial_analysis: str
    created_at: datetime
    updated_at: datetime
    zotero_key: Optional[str] = None
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None
    label: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    journal_abbr: Optional[str] = None
    conversation: List[ConversationMessage] = Field(
        default_factory=list,
        description="Full conversation history"
    )
    flags: List[int] = Field(
        default_factory=list,
        description="List of flagged exchange IDs"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "abc123",
                "filename": "paper.pdf",
                "initial_analysis": "**Core Innovation**: ...",
                "created_at": "2025-11-17T10:30:00Z",
                "updated_at": "2025-11-17T10:35:00Z",
                "page_count": 15,
                "file_size_bytes": 2456789,
                "conversation": [
                    {
                        "exchange_id": 1,
                        "role": "user",
                        "content": "What is the main contribution?",
                        "timestamp": "2025-11-17T10:31:00Z"
                    },
                    {
                        "exchange_id": 1,
                        "role": "assistant",
                        "content": "The main contribution is...",
                        "model": "claude-sonnet-4-6",
                        "timestamp": "2025-11-17T10:31:05Z"
                    }
                ]
            }
        }
    )


class SessionMetadata(BaseModel):
    """
    Paper metadata extracted from PDF or Zotero.
    """
    title: Optional[str] = None
    authors: Optional[str] = None  # JSON string of author list
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Attention Is All You Need",
                "authors": '["Vaswani, Ashish", "Shazeer, Noam", "Parmar, Niki"]',
                "doi": "10.48550/arXiv.1706.03762",
                "arxiv_id": "1706.03762",
                "publication_date": "2017-06",
                "journal": "arXiv",
                "abstract": "The dominant sequence transduction models..."
            }
        }
    )


class LinkedInPostEndings(BaseModel):
    """
    Alternative ending options for LinkedIn post.
    """
    question: str = Field(description="Question/call to action ending")
    declarative: str = Field(description="Clean declarative ending")
    forward_looking: str = Field(description="Forward-looking ending")


class LinkedInPostResponse(BaseModel):
    """
    Response model for LinkedIn post generation.
    """
    hook: str = Field(description="First 1-2 sentences for LinkedIn preview")
    body: str = Field(description="Full post body with [PAPER LINK] placeholder")
    endings: LinkedInPostEndings = Field(description="Three alternative ending options")
    full_post_options: List[str] = Field(description="Complete post variations (body + each ending + sign-off)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hook": "I've been thinking about how we measure model performance.",
                "body": "The recent paper on transformer architectures got me reconsidering...",
                "endings": {
                    "question": "How do you think about this tradeoff in your work?",
                    "declarative": "These insights are changing how I approach the problem.",
                    "forward_looking": "I'm curious to explore how this applies to other domains."
                },
                "full_post_options": [
                    "The recent paper... How do you think about this tradeoff?",
                    "The recent paper... These insights are changing my approach.",
                    "The recent paper... I'm curious to explore applications."
                ]
            }
        }
    )
