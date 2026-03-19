"""
Pydantic models for metadata operations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class MetadataLookupRequest(BaseModel):
    """Request to lookup metadata by DOI or PMID."""
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    pmid: Optional[str] = Field(None, description="PubMed ID")


class MetadataResponse(BaseModel):
    """Response with paper metadata."""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    arxiv_id: Optional[str] = None
    abstract: Optional[str] = None
    publication_date: Optional[str] = None
    year: Optional[str] = None
    journal: Optional[str] = None
    journal_abbr: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    source: Optional[str] = Field(None, description="Metadata source: crossref, pubmed, pdf_metadata, ai_pending")


class MetadataUpdateRequest(BaseModel):
    """Request to update session metadata."""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    arxiv_id: Optional[str] = None
    abstract: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    journal_abbr: Optional[str] = None
    label: Optional[str] = Field(None, description="Session label to distinguish multiple sessions for same paper")


class MetadataUpdateResponse(BaseModel):
    """Response after updating metadata."""
    success: bool
    message: str
    metadata: Optional[MetadataResponse] = None
