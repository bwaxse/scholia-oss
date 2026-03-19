"""
FastAPI routes for Zotero integration.

All routes require authentication and use per-user Zotero credentials.
"""

import asyncio
import json
from typing import List, Optional
from pathlib import Path
import tempfile
from fastapi import APIRouter, HTTPException, Query, status, UploadFile, File, Form, Depends

from ..models.zotero import (
    ZoteroSearchResponse,
    ZoteroItemSummary,
    ZoteroItem,
    ZoteroNoteRequest,
    ZoteroNoteResponse,
)
from ...services import get_zotero_service_for_user, get_session_manager, get_insight_extractor
from ...core.database import get_db_manager
from .auth import require_active


router = APIRouter(prefix="/zotero", tags=["zotero"])


@router.get("/search", response_model=ZoteroSearchResponse)
async def search_zotero(
    user: dict = Depends(require_active),
    query: str = Query(..., min_length=1, description="Search query (title, DOI, keywords)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return")
):
    """
    Search Zotero library for papers.

    **Capabilities:**
    - Search by title, author, DOI, or keywords
    - Returns summaries optimized for list display
    - Supports pagination with limit parameter

    **Args:**
    - query: Search query string (required)
    - limit: Maximum results (1-50, default 10)

    **Returns:**
    - ZoteroSearchResponse with matching items and total count

    **Raises:**
    - 401: If not authenticated
    - 500: If Zotero not configured or search fails

    **Example:**
    ```
    GET /zotero/search?query=attention+is+all+you+need&limit=5
    ```
    """
    try:
        service = await get_zotero_service_for_user(user["id"])

        if not service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zotero is not configured. Please add your Zotero credentials in Settings."
            )

        items = await service.search_papers(query=query, limit=limit)

        return ZoteroSearchResponse(
            items=items,
            total=len(items)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search Zotero: {str(e)}"
        )


@router.get("/recent", response_model=List[ZoteroItemSummary])
async def list_recent_papers(
    user: dict = Depends(require_active),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return")
):
    """
    List recent papers from Zotero library.

    **Purpose:**
    - Browse recently added papers
    - Quick access to latest research
    - Sorted by date added (newest first)

    **Args:**
    - limit: Maximum results (1-100, default 20)

    **Returns:**
    - List of ZoteroItemSummary objects

    **Raises:**
    - 401: If not authenticated
    - 400: If Zotero not configured

    **Example:**
    ```
    GET /zotero/recent?limit=10
    ```
    """
    try:
        service = await get_zotero_service_for_user(user["id"])

        if not service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zotero is not configured. Please add your Zotero credentials in Settings."
            )

        items = await service.list_recent(limit=limit)
        return items

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recent papers: {str(e)}"
        )


@router.get("/paper/{key}", response_model=ZoteroItem)
async def get_paper_details(key: str, user: dict = Depends(require_active)):
    """
    Get full details for a specific Zotero paper.

    **Purpose:**
    - Retrieve complete metadata for a paper
    - Get abstract, tags, publication info
    - Use before creating session or for display

    **Args:**
    - key: Zotero item key (from search results)

    **Returns:**
    - ZoteroItem with complete metadata

    **Raises:**
    - 401: If not authenticated
    - 404: If paper not found
    - 400: If Zotero not configured

    **Example:**
    ```
    GET /zotero/paper/ABC123XY
    ```
    """
    try:
        service = await get_zotero_service_for_user(user["id"])

        if not service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zotero is not configured. Please add your Zotero credentials in Settings."
            )

        item = await service.get_paper_by_key(key)

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paper with key '{key}' not found in Zotero library"
            )

        return item

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get paper details: {str(e)}"
        )


@router.post("/save-insights", response_model=ZoteroNoteResponse)
async def save_insights_to_zotero(request: ZoteroNoteRequest, user: dict = Depends(require_active)):
    """
    Save session insights as a note attached to Zotero paper.

    **Workflow:**
    1. Retrieves session data (exchanges, flags, highlights)
    2. Formats insights as HTML note
    3. Attaches note to specified Zotero item
    4. Adds tags for organization

    **Args:**
    - request: Contains session_id, parent_item_key, and optional tags

    **Returns:**
    - ZoteroNoteResponse with success status and note_key

    **Raises:**
    - 401: If not authenticated
    - 404: If session not found
    - 400: If Zotero not configured

    **Example:**
    ```json
    {
      "session_id": "abc123def456",
      "parent_item_key": "ABC123XY",
      "tags": ["claude-analyzed", "critical-appraisal"]
    }
    ```

    **Note Format:**
    - Initial analysis summary
    - Flagged exchanges (Q&A marked as important)
    - Highlights with page numbers
    - Metadata (session date, model used)
    """
    try:
        # Get services
        zotero_service = await get_zotero_service_for_user(user["id"])
        session_manager = get_session_manager()
        db = get_db_manager()

        if not zotero_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zotero is not configured. Please add your Zotero credentials in Settings."
            )

        # Get session data
        session = await session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{request.session_id}' not found"
            )

        # Get cached insights from database (no re-extraction)
        async with db.get_connection() as conn:
            cached_row = await conn.fetchrow(
                "SELECT insights_json FROM insights WHERE session_id = $1",
                request.session_id
            )

        if not cached_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No insights found for this session. Please extract insights first in the Insights tab."
            )

        insights = json.loads(cached_row['insights_json'])

        # Format cached insights as HTML for Zotero (no inference needed)
        from ...services.insight_extractor import InsightExtractor
        note_html = InsightExtractor.format_insights_html(insights)

        # Save note to Zotero
        success = await zotero_service.save_insights_to_note(
            parent_item_key=request.parent_item_key,
            note_html=note_html,
            tags=request.tags
        )

        if success:
            return ZoteroNoteResponse(
                success=True,
                message="Insights saved successfully to Zotero",
                note_key=None  # pyzotero doesn't return the created note key easily
            )
        else:
            return ZoteroNoteResponse(
                success=False,
                message="Failed to save note to Zotero. Check API key and item key.",
                note_key=None
            )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save insights: {str(e)}"
        )


@router.get("/attachments/{key}", response_model=List[ZoteroItemSummary])
async def get_paper_attachments(key: str, user: dict = Depends(require_active)):
    """
    Get all attachment files linked to a Zotero paper.

    **Purpose:**
    - Show supplemental PDFs/files for a paper
    - User can select one to load as supplement

    **Args:**
    - key: Zotero item key of the parent paper

    **Returns:**
    - List of ZoteroItemSummary objects (attachment items only)

    **Raises:**
    - 401: If not authenticated
    - 404: If paper not found
    - 400: If Zotero not configured

    **Example:**
    ```
    GET /zotero/attachments/ABC123XY
    ```
    """
    try:
        service = await get_zotero_service_for_user(user["id"])

        if not service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zotero is not configured. Please add your Zotero credentials in Settings."
            )

        # Get the parent item to verify it exists
        parent = await service.get_paper_by_key(key)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paper '{key}' not found in Zotero"
            )

        # Get attachments for this paper (excluding the main PDF)
        # pyzotero returns children items which include attachments
        try:
            attachments = []
            # Access the zotero client directly to get children
            zot = service.zot
            if zot:
                children = await asyncio.to_thread(zot.children, key)

                # Filter for PDF attachments only
                pdf_attachments = [
                    child for child in children
                    if child.get('data', {}).get('contentType') == 'application/pdf'
                ]

                # Identify the main PDF (same logic as get_pdf_path)
                # Main PDF is either titled "Full Text PDF" or the first PDF
                main_pdf_key = None
                if pdf_attachments:
                    main_pdf = next(
                        (att for att in pdf_attachments if att['data'].get('title') == 'Full Text PDF'),
                        pdf_attachments[0]
                    )
                    main_pdf_key = main_pdf.get('key')

                # Return only supplemental PDFs (exclude the main PDF)
                for child in pdf_attachments:
                    if child.get('key') != main_pdf_key:
                        summary = service._item_to_summary(child)
                        if summary:
                            attachments.append(summary)

            return attachments
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get attachments: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get attachments: {str(e)}"
        )


@router.post("/load-supplement", response_model=dict)
async def load_supplement(
    user: dict = Depends(require_active),
    session_id: str = Query(..., description="Session ID to load supplement into"),
    zotero_key: str = Query(..., description="Zotero key of supplement paper")
):
    """
    Load a supplement paper's text into a session for Claude reference.

    **Purpose:**
    - User can add related papers during conversation
    - Text gets added to conversation history
    - Claude can reference supplement without displaying it

    **Args:**
    - session_id: Session ID to add supplement to
    - zotero_key: Zotero item key of the supplement

    **Returns:**
    - dict with supplement_text and metadata

    **Raises:**
    - 401: If not authenticated
    - 404: If session or paper not found
    - 400: If Zotero not configured

    **Example:**
    ```
    POST /zotero/load-supplement?session_id=abc123&zotero_key=XYZ789
    ```
    """
    try:
        zotero_service = await get_zotero_service_for_user(user["id"])

        if not zotero_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zotero is not configured. Please add your Zotero credentials in Settings."
            )

        # Get the supplement paper
        supplement = await zotero_service.get_paper_by_key(zotero_key)
        if not supplement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Supplement paper '{zotero_key}' not found"
            )

        # Get PDF text if available
        pdf_path = await zotero_service.get_pdf_path(zotero_key)
        supplement_text = ""

        if pdf_path:
            try:
                from ...core.pdf_processor import PDFProcessor
                processor = PDFProcessor()
                supplement_text = await processor.extract_text(pdf_path)
            except Exception as e:
                supplement_text = f"(Could not extract PDF text: {str(e)})"

        return {
            "success": True,
            "title": supplement.title,
            "authors": supplement.authors,
            "year": supplement.year,
            "supplement_text": supplement_text,
            "has_pdf": bool(pdf_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load supplement: {str(e)}"
        )


@router.get("/related", response_model=List[ZoteroItemSummary])
async def get_related_papers(
    user: dict = Depends(require_active),
    tags: str = Query(..., description="Comma-separated list of tags to search for"),
    limit: int = Query(5, ge=1, le=20, description="Maximum results per tag")
):
    """
    Find related papers in Zotero library based on tags.

    **Use Case:**
    - Discover papers with similar topics
    - Find related research after analyzing a paper
    - Build reading lists around themes

    **Args:**
    - tags: Comma-separated tag list (e.g., "machine-learning,nlp")
    - limit: Maximum results per tag (1-20, default 5)

    **Returns:**
    - List of ZoteroItemSummary objects with matching tags

    **Raises:**
    - 401: If not authenticated
    - 400: If Zotero not configured

    **Example:**
    ```
    GET /zotero/related?tags=transformer,attention&limit=5
    ```

    **Note:**
    - Results may contain duplicates if papers match multiple tags
    - Papers are returned in no specific order
    """
    try:
        service = await get_zotero_service_for_user(user["id"])

        if not service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zotero is not configured. Please add your Zotero credentials in Settings."
            )

        # Parse tags from comma-separated string
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        if not tag_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one tag is required"
            )

        items = await service.get_related_papers(tags=tag_list, limit=limit)
        return items

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find related papers: {str(e)}"
        )


@router.post("/upload-supplement")
async def upload_supplement(
    user: dict = Depends(require_active),
    session_id: str = Form(...),
    zotero_key: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload a supplemental PDF and attach it to a Zotero item.

    **Purpose:**
    - Allow users to add supplemental PDFs to papers in their Zotero library
    - Files are uploaded to Zotero as child attachments
    - Makes supplements available for future sessions

    **Args:**
    - session_id: Current session ID (for validation)
    - zotero_key: Zotero item key to attach supplement to
    - file: PDF file to upload

    **Returns:**
    - dict with success status and attachment details

    **Raises:**
    - 401: If not authenticated
    - 400: If file is not a PDF or Zotero not configured
    - 404: If Zotero item not found
    - 500: If upload fails

    **Example:**
    ```
    POST /zotero/upload-supplement
    Content-Type: multipart/form-data
    ```
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a PDF"
            )

        service = await get_zotero_service_for_user(user["id"])

        if not service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zotero is not configured. Please add your Zotero credentials in Settings."
            )

        # Verify parent item exists
        parent = await service.get_paper_by_key(zotero_key)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zotero item '{zotero_key}' not found"
            )

        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            # Upload to Zotero as child attachment
            loop = asyncio.get_event_loop()
            zot = service.zot

            # Create attachment using pyzotero
            attachment = await loop.run_in_executor(
                None,
                lambda: zot.attachment_simple([temp_path], zotero_key)
            )

            # Update the title to match the filename
            if attachment and len(attachment) > 0:
                attachment_key = attachment[0]
                await loop.run_in_executor(
                    None,
                    lambda: zot.update_item({
                        'key': attachment_key,
                        'data': {
                            'title': file.filename,
                            'contentType': 'application/pdf'
                        }
                    })
                )

            return {
                "status": "success",
                "message": f"Supplement '{file.filename}' uploaded to Zotero",
                "attachment_key": attachment[0] if attachment else None,
                "parent_key": zotero_key
            }

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload supplement: {str(e)}"
        )
