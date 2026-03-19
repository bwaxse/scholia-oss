"""
Pydantic models for Notion API endpoints.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class NotionAuthResponse(BaseModel):
    """Response from Notion OAuth callback."""
    success: bool
    access_token: str
    workspace_name: Optional[str] = None
    message: str


class NotionProject(BaseModel):
    """Summary of a Notion page (potential project)."""
    id: str
    title: str
    url: str
    parent: Optional[Dict] = None


class NotionProjectList(BaseModel):
    """List of Notion projects."""
    projects: List[NotionProject]
    total: int


class NotionProjectContext(BaseModel):
    """Project context extracted from Notion page."""
    title: str
    hypothesis: str = ""
    themes: List[str] = Field(default_factory=list)
    raw_content: str
    fetched_at: Optional[str] = None


class NotionRelevanceResponse(BaseModel):
    """Generated relevance statement and theme suggestion."""
    suggested_theme: str = Field(
        ...,
        description="Suggested theme name, or 'NEW: Theme Name' for new theme"
    )
    relevance_statement: str = Field(
        ...,
        description="2-3 sentence relevance statement in Bennett's voice"
    )
    error: Optional[str] = None


class NotionContentResponse(BaseModel):
    """Generated export content."""
    content: str = Field(
        ...,
        description="Formatted content ready for Notion export"
    )


class NotionExportRequest(BaseModel):
    """Request body for Notion export."""
    session_id: str
    page_id: str
    theme: str
    content: str
    literature_review_heading: str = "Literature Review"


class NotionExportResponse(BaseModel):
    """Response from Notion export."""
    success: bool
    page_url: str
    message: str
