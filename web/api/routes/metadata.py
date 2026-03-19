"""
Metadata API routes for Paper Companion.
Handles metadata lookup and updates.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import json

from ..models import (
    MetadataLookupRequest,
    MetadataResponse,
    MetadataUpdateRequest,
    MetadataUpdateResponse,
)
from ...services.metadata_service import get_metadata_service
from ...core.database import get_db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.post("/lookup", response_model=MetadataResponse)
async def lookup_metadata(request: MetadataLookupRequest):
    """
    Look up paper metadata by DOI or PMID.

    This endpoint queries CrossRef (for DOI) or PubMed (for PMID)
    to retrieve rich metadata about a paper.

    Args:
        request: DOI or PMID to look up

    Returns:
        Metadata including title, authors, journal, etc.

    Raises:
        400: If neither DOI nor PMID provided
        404: If paper not found
    """
    if not request.doi and not request.pmid:
        raise HTTPException(
            status_code=400,
            detail="Either DOI or PMID must be provided"
        )

    metadata_service = get_metadata_service()

    try:
        # Try DOI first via CrossRef
        if request.doi:
            logger.info(f"Looking up metadata for DOI: {request.doi}")
            metadata = await metadata_service.get_metadata_from_crossref(request.doi)
            if metadata:
                return MetadataResponse(**metadata)

        # Try PMID via PubMed
        if request.pmid:
            logger.info(f"Looking up metadata for PMID: {request.pmid}")
            metadata = await metadata_service.get_metadata_from_pubmed(request.pmid, is_pmid=True)
            if metadata:
                return MetadataResponse(**metadata)

        # Not found
        raise HTTPException(
            status_code=404,
            detail="Paper not found in CrossRef or PubMed"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up metadata: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to lookup metadata: {str(e)}"
        )


@router.put("/{session_id}", response_model=MetadataUpdateResponse)
async def update_session_metadata(
    session_id: str,
    request: MetadataUpdateRequest
):
    """
    Update metadata for a session.

    This endpoint allows manual editing of paper metadata.
    If DOI or PMID is provided, it will attempt to fetch
    enriched metadata from APIs.

    Args:
        session_id: Session identifier
        request: Metadata fields to update

    Returns:
        Update confirmation with new metadata

    Raises:
        404: If session not found
    """
    db = get_db_manager()

    try:
        # Check if session exists
        async with db.get_connection() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM sessions WHERE id = $1)",
                session_id
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Session not found")

        # If DOI or PMID provided, try to enrich metadata from APIs
        enriched_metadata = None
        if request.doi or request.pmid:
            metadata_service = get_metadata_service()
            enriched_metadata = await metadata_service.extract_metadata_hybrid(
                doi=request.doi,
                pmid=request.pmid
            )

        # Merge manual entries with API data (manual takes priority)
        final_metadata = {}
        if enriched_metadata:
            final_metadata.update(enriched_metadata)

        # Override with manual entries
        if request.title:
            final_metadata['title'] = request.title
        if request.authors:
            final_metadata['authors'] = request.authors
        if request.doi:
            final_metadata['doi'] = request.doi
        if request.pmid:
            final_metadata['pmid'] = request.pmid
        if request.arxiv_id:
            final_metadata['arxiv_id'] = request.arxiv_id
        if request.abstract:
            final_metadata['abstract'] = request.abstract
        if request.publication_date:
            final_metadata['publication_date'] = request.publication_date
        if request.journal:
            final_metadata['journal'] = request.journal
        if request.journal_abbr:
            final_metadata['journal_abbr'] = request.journal_abbr

        # Format authors as JSON
        authors_json = None
        if final_metadata.get('authors'):
            authors_json = json.dumps(final_metadata['authors'])

        # Update or insert metadata
        async with db.transaction() as conn:
            # Update session label if provided
            if request.label is not None:
                await conn.execute(
                    "UPDATE sessions SET label = $1 WHERE id = $2",
                    request.label if request.label else None,  # Empty string → NULL
                    session_id
                )

            # Check if metadata exists
            existing = await conn.fetchrow(
                "SELECT session_id FROM metadata WHERE session_id = $1",
                session_id
            )

            if existing:
                # Update existing metadata
                await conn.execute(
                    """
                    UPDATE metadata
                    SET title = COALESCE($2, title),
                        authors = COALESCE($3, authors),
                        doi = COALESCE($4, doi),
                        arxiv_id = COALESCE($5, arxiv_id),
                        publication_date = COALESCE($6, publication_date),
                        journal = COALESCE($7, journal),
                        journal_abbr = COALESCE($8, journal_abbr),
                        abstract = COALESCE($9, abstract)
                    WHERE session_id = $1
                    """,
                    session_id,
                    final_metadata.get('title'),
                    authors_json,
                    final_metadata.get('doi'),
                    final_metadata.get('arxiv_id'),
                    final_metadata.get('publication_date'),
                    final_metadata.get('journal'),
                    final_metadata.get('journal_abbr'),
                    final_metadata.get('abstract')
                )
            else:
                # Insert new metadata
                await conn.execute(
                    """
                    INSERT INTO metadata (session_id, title, authors, doi, arxiv_id, publication_date, journal, journal_abbr, abstract)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    session_id,
                    final_metadata.get('title'),
                    authors_json,
                    final_metadata.get('doi'),
                    final_metadata.get('arxiv_id'),
                    final_metadata.get('publication_date'),
                    final_metadata.get('journal'),
                    final_metadata.get('journal_abbr'),
                    final_metadata.get('abstract')
                )

        logger.info(f"Updated metadata for session {session_id}")

        return MetadataUpdateResponse(
            success=True,
            message="Metadata updated successfully",
            metadata=MetadataResponse(**final_metadata) if final_metadata else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating metadata: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update metadata: {str(e)}"
        )


@router.get("/{session_id}", response_model=MetadataResponse)
async def get_session_metadata(session_id: str):
    """
    Get metadata for a session.

    Args:
        session_id: Session identifier

    Returns:
        Session metadata

    Raises:
        404: If session or metadata not found
    """
    db = get_db_manager()

    try:
        async with db.get_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT title, authors, doi, arxiv_id, publication_date, journal, journal_abbr, abstract
                FROM metadata
                WHERE session_id = $1
                """,
                session_id
            )

            if not row:
                raise HTTPException(status_code=404, detail="Metadata not found")

            # Parse authors JSON
            authors = None
            if row['authors']:
                try:
                    authors = json.loads(row['authors'])
                except:
                    authors = [row['authors']]  # Fallback to single author

            # Extract year from publication_date
            year = None
            if row['publication_date']:
                year = row['publication_date'].split('-')[0]

            return MetadataResponse(
                title=row['title'],
                authors=authors,
                doi=row['doi'],
                arxiv_id=row['arxiv_id'],
                publication_date=row['publication_date'],
                year=year,
                journal=row['journal'],
                journal_abbr=row['journal_abbr'],
                abstract=row['abstract'],
                source="database"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving metadata: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metadata: {str(e)}"
        )
