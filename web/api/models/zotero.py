"""
Pydantic models for Zotero integration.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ZoteroCreator(BaseModel):
    """Model for Zotero item creator (author/editor)."""
    creatorType: str = Field(description="Type of creator (author, editor, etc.)")
    firstName: Optional[str] = Field(default=None, description="First name")
    lastName: Optional[str] = Field(default=None, description="Last name")
    name: Optional[str] = Field(default=None, description="Full name (for organizations)")


class ZoteroTag(BaseModel):
    """Model for Zotero tag."""
    tag: str = Field(description="Tag text")
    type: Optional[int] = Field(default=None, description="Tag type (0=user, 1=automatic)")


class ZoteroItemData(BaseModel):
    """Model for Zotero item data."""
    key: str = Field(description="Zotero item key")
    version: int = Field(description="Item version")
    itemType: str = Field(description="Type of item (journalArticle, book, etc.)")
    title: Optional[str] = Field(default=None, description="Item title")
    creators: List[ZoteroCreator] = Field(default_factory=list, description="Item creators")
    abstractNote: Optional[str] = Field(default=None, description="Abstract")
    publicationTitle: Optional[str] = Field(default=None, description="Journal/publication name")
    journalAbbreviation: Optional[str] = Field(default=None, description="Journal abbreviation")
    volume: Optional[str] = Field(default=None, description="Volume number")
    issue: Optional[str] = Field(default=None, description="Issue number")
    pages: Optional[str] = Field(default=None, description="Page range")
    date: Optional[str] = Field(default=None, description="Publication date")
    DOI: Optional[str] = Field(default=None, description="Digital Object Identifier")
    url: Optional[str] = Field(default=None, description="URL")
    accessDate: Optional[str] = Field(default=None, description="Access date")
    tags: List[ZoteroTag] = Field(default_factory=list, description="Tags")

    model_config = ConfigDict(extra="allow")  # Allow additional Zotero fields


class ZoteroItem(BaseModel):
    """Model for complete Zotero item."""
    key: str = Field(description="Zotero item key")
    version: int = Field(description="Item version")
    library: Dict[str, Any] = Field(description="Library information")
    data: ZoteroItemData = Field(description="Item data")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "ABC123XY",
                "version": 123,
                "library": {"type": "user", "id": 12345},
                "data": {
                    "key": "ABC123XY",
                    "version": 123,
                    "itemType": "journalArticle",
                    "title": "Attention Is All You Need",
                    "creators": [
                        {"creatorType": "author", "firstName": "Ashish", "lastName": "Vaswani"}
                    ],
                    "publicationTitle": "arXiv",
                    "date": "2017-06",
                    "DOI": "10.48550/arXiv.1706.03762",
                    "tags": [{"tag": "transformer"}, {"tag": "attention"}]
                }
            }
        }
    )


class ZoteroItemSummary(BaseModel):
    """Lightweight Zotero item summary for list views."""
    key: str = Field(description="Zotero item key")
    title: str = Field(description="Item title")
    authors: str = Field(description="Formatted author string")
    year: Optional[str] = Field(default=None, description="Publication year")
    publication: Optional[str] = Field(default=None, description="Publication/journal name")
    item_type: str = Field(description="Item type")
    has_pdf: bool = Field(default=False, description="Whether item has a PDF attachment")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "ABC123XY",
                "title": "Attention Is All You Need",
                "authors": "Vaswani et al.",
                "year": "2017",
                "publication": "arXiv",
                "item_type": "journalArticle",
                "has_pdf": True
            }
        }
    )


class ZoteroSearchRequest(BaseModel):
    """Request model for Zotero search."""
    query: str = Field(min_length=1, description="Search query (title, DOI, etc.)")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results to return")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "attention is all you need",
                "limit": 10
            }
        }
    )


class ZoteroSearchResponse(BaseModel):
    """Response model for Zotero search."""
    items: List[ZoteroItemSummary] = Field(description="Matching items")
    total: int = Field(description="Total number of matches")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "key": "ABC123",
                        "title": "Attention Is All You Need",
                        "authors": "Vaswani et al.",
                        "year": "2017",
                        "publication": "arXiv",
                        "item_type": "journalArticle"
                    }
                ],
                "total": 1
            }
        }
    )


class ZoteroNoteRequest(BaseModel):
    """Request model for saving note to Zotero."""
    session_id: str = Field(description="Session ID to extract insights from")
    parent_item_key: str = Field(description="Zotero item key to attach note to")
    tags: List[str] = Field(default_factory=list, description="Additional tags for the note")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "abc123def456",
                "parent_item_key": "ABC123XY",
                "tags": ["claude-analyzed", "critical-appraisal"]
            }
        }
    )


class ZoteroNoteResponse(BaseModel):
    """Response model for note save operation."""
    success: bool = Field(description="Whether note was saved successfully")
    message: str = Field(description="Status message")
    note_key: Optional[str] = Field(default=None, description="Key of created note")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Note saved successfully to Zotero",
                "note_key": "NOTE123"
            }
        }
    )
