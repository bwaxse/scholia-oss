"""
FastAPI routes for Notion integration.
"""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status, Depends
from fastapi.responses import RedirectResponse

from ..models.notion import (
    NotionAuthResponse,
    NotionProjectList,
    NotionProjectContext,
    NotionRelevanceResponse,
    NotionContentResponse,
    NotionExportRequest,
    NotionExportResponse,
)
from ...services import (
    get_notion_client,
    get_notion_client_for_user,
    get_notion_exporter,
    get_session_manager,
)
from ...core.database import get_db_manager
from .auth import require_active

router = APIRouter(prefix="/api/notion", tags=["notion"])


@router.get("/auth-url")
async def get_notion_auth_url(state: Optional[str] = Query(None)):
    """
    Get Notion OAuth authorization URL.

    **Args:**
    - state: Optional CSRF state parameter

    **Returns:**
    - Authorization URL to redirect user to

    **Raises:**
    - 500: If Notion OAuth not configured

    **Example:**
    ```
    GET /notion/auth-url
    ```
    """
    try:
        client = get_notion_client()

        if not client.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Notion OAuth not configured. Set NOTION_CLIENT_ID, NOTION_CLIENT_SECRET, and NOTION_REDIRECT_URI in .env"
            )

        auth_url = client.get_authorization_url(state=state)

        return {"auth_url": auth_url}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate authorization URL: {str(e)}"
        )


@router.get("/callback")
async def notion_oauth_callback(
    code: str = Query(..., description="Authorization code from Notion"),
    state: Optional[str] = Query(None, description="CSRF state parameter"),
    user: dict = Depends(require_active)
):
    """
    Handle Notion OAuth callback.

    **Args:**
    - code: Authorization code from Notion
    - state: Optional CSRF state parameter

    **Returns:**
    - Redirects to frontend with success/error

    **Process:**
    - Exchanges code for access token
    - Stores token in user_notion_credentials table
    - Returns success message

    **Example:**
    ```
    GET /notion/callback?code=abc123&state=xyz
    ```
    """
    try:
        client = get_notion_client()
        token_data = await client.exchange_code_for_token(code)

        # Save token to database for this user
        db = get_db_manager()
        async with db.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO user_notion_credentials
                (user_id, access_token, bot_id, workspace_id, workspace_name, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET access_token = $2, bot_id = $3, workspace_id = $4,
                    workspace_name = $5, updated_at = NOW()
                """,
                user["id"],
                token_data["access_token"],
                token_data.get("bot_id"),
                token_data.get("workspace_id"),
                token_data.get("workspace_name")
            )

        # Redirect to settings page with success
        return RedirectResponse(
            url="/settings?notion=connected",
            status_code=status.HTTP_302_FOUND
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.get("/projects", response_model=NotionProjectList)
async def list_notion_projects(
    query: Optional[str] = Query(None, description="Optional search query"),
    user: dict = Depends(require_active)
):
    """
    List user's Notion pages (potential research projects).

    **Args:**
    - query: Optional search query

    **Returns:**
    - List of Notion pages with {id, title, url}

    **Raises:**
    - 401: If not authenticated with Notion
    - 500: If fetch fails

    **Example:**
    ```
    GET /notion/projects
    GET /notion/projects?query=research
    ```
    """
    try:
        client = await get_notion_client_for_user(user["id"])

        if not client or not client.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Notion. Please configure Notion in Settings first."
            )

        projects = await client.search_projects(query=query)

        return NotionProjectList(projects=projects, total=len(projects))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get("/project/{page_id}/context", response_model=NotionProjectContext)
async def get_project_context(
    page_id: str,
    force_refresh: bool = Query(False, description="Force refresh cached context"),
    user: dict = Depends(require_active)
):
    """
    Get project context (hypothesis, themes, etc.).

    **Args:**
    - page_id: Notion page ID
    - force_refresh: If True, bypass cache and re-fetch

    **Returns:**
    - Project context with title, hypothesis, themes, raw_content

    **Raises:**
    - 401: If not authenticated
    - 404: If page not found
    - 500: If fetch fails

    **Caching:**
    - Contexts are cached for 24 hours
    - Use force_refresh=true to clear cache

    **Example:**
    ```
    GET /notion/project/abc123/context
    GET /notion/project/abc123/context?force_refresh=true
    ```
    """
    try:
        client = await get_notion_client_for_user(user["id"])

        if not client or not client.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Notion. Please configure Notion in Settings first."
            )

        exporter = get_notion_exporter(notion_client=client)
        context = await exporter.get_project_context(
            page_id=page_id,
            user_id=user["id"],
            force_refresh=force_refresh
        )

        return NotionProjectContext(**context)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project context: {str(e)}"
        )


@router.post("/generate-relevance", response_model=NotionRelevanceResponse)
async def generate_relevance(
    session_id: str = Query(..., description="Session ID"),
    page_id: str = Query(..., description="Notion page ID"),
    model: str = Query("gemini-flash", description="Model to use"),
    user: dict = Depends(require_active)
):
    """
    Generate proposed relevance statement and theme suggestion.

    **Args:**
    - session_id: Session ID with insights
    - page_id: Notion page ID
    - model: Model to use ("haiku", "sonnet", "gemini-flash", "gemini-pro")

    **Returns:**
    - Suggested theme and relevance statement

    **Requirements:**
    - Session must have extracted insights
    - Project context must be fetchable

    **Uses:**
    - Claude or Gemini (based on model parameter)
    - Bennett's voice from bjw-voice-modeling skill

    **Example:**
    ```
    POST /notion/generate-relevance?session_id=abc123&page_id=xyz789&model=sonnet
    ```
    """
    try:
        # Check authentication
        client = await get_notion_client_for_user(user["id"])
        if not client or not client.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Notion. Please configure Notion in Settings first."
            )

        # Get session insights
        db = get_db_manager()
        async with db.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT insights_json FROM insights WHERE session_id = $1",
                session_id
            )

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No insights found for session. Please extract insights first."
                )

            insights = json.loads(row['insights_json'])

        # Get project context
        exporter = get_notion_exporter(notion_client=client)
        project_context = await exporter.get_project_context(
            page_id=page_id,
            user_id=user["id"]
        )

        # Generate relevance
        relevance_data = await exporter.generate_relevance(
            session_insights=insights,
            project_context=project_context,
            user_id=user["id"],
            model=model
        )

        return NotionRelevanceResponse(**relevance_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate relevance: {str(e)}"
        )


@router.post("/generate-content", response_model=NotionContentResponse)
async def generate_export_content(
    session_id: str = Query(..., description="Session ID"),
    page_id: str = Query(..., description="Notion page ID"),
    theme: str = Query(..., description="Theme name"),
    relevance: str = Query(..., description="Relevance statement"),
    include_session_notes: bool = Query(True, description="Include session notes"),
    model: str = Query("gemini-flash", description="Model to use"),
    user: dict = Depends(require_active)
):
    """
    Generate full export content for Notion.

    **Args:**
    - session_id: Session ID with insights
    - page_id: Notion project page ID
    - theme: Confirmed theme (can be "NEW: Theme Name")
    - relevance: Confirmed relevance statement
    - include_session_notes: Whether to include collapsed session notes
    - model: Model to use ("sonnet", "haiku", "gemini-pro", "gemini-flash")

    **Returns:**
    - Formatted content ready for export

    **Uses:**
    - Claude or Gemini (based on model parameter)
    - Bennett's voice characteristics

    **Example:**
    ```
    POST /notion/generate-content?session_id=abc&page_id=xyz&theme=Autoencoders&relevance=...&model=sonnet
    ```
    """
    try:
        # Check authentication
        client = await get_notion_client_for_user(user["id"])
        if not client or not client.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Notion. Please configure Notion in Settings first."
            )

        # Get session insights and metadata
        db = get_db_manager()
        async with db.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT insights_json FROM insights WHERE session_id = $1",
                session_id
            )

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No insights found for session"
                )

            insights = json.loads(row['insights_json'])

            # Get metadata from database (more reliable than Claude extraction)
            metadata_row = await conn.fetchrow(
                "SELECT title, authors, publication_date FROM metadata WHERE session_id = $1",
                session_id
            )

            # Merge database metadata with insights (prefer database)
            if metadata_row and metadata_row['title']:
                if "bibliographic" not in insights:
                    insights["bibliographic"] = {}
                insights["bibliographic"]["title"] = metadata_row['title']
                if metadata_row['authors']:
                    insights["bibliographic"]["authors"] = metadata_row['authors']
                if metadata_row['publication_date']:
                    # Extract year from publication_date
                    pub_date = metadata_row['publication_date']
                    # Try to extract year (might be "2023", "2023-01-01", etc.)
                    import re
                    year_match = re.search(r'\d{4}', pub_date)
                    if year_match:
                        insights["bibliographic"]["year"] = year_match.group(0)

        # Get project context
        exporter = get_notion_exporter(notion_client=client)
        project_context = await exporter.get_project_context(
            page_id=page_id,
            user_id=user["id"]
        )

        # Generate content
        content = await exporter.generate_export_content(
            session_insights=insights,
            project_context=project_context,
            confirmed_theme=theme,
            confirmed_relevance=relevance,
            user_id=user["id"],
            include_session_notes=include_session_notes,
            model=model
        )

        return NotionContentResponse(content=content)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate content: {str(e)}"
        )


@router.post("/export", response_model=NotionExportResponse)
async def export_to_notion(
    request: NotionExportRequest,
    user: dict = Depends(require_active)
):
    """
    Export content to Notion page.

    **Args:**
    - request: NotionExportRequest with session_id, page_id, theme, content, literature_review_heading

    **Returns:**
    - Success status and Notion page URL

    **Raises:**
    - 401: If not authenticated
    - 404: If Literature Review heading not found
    - 500: If export fails

    **Example:**
    ```
    POST /notion/export
    {
      "session_id": "abc",
      "page_id": "xyz",
      "theme": "Autoencoders",
      "content": "...",
      "literature_review_heading": "Literature Review"
    }
    ```
    """
    try:
        # Check authentication
        client = await get_notion_client_for_user(user["id"])
        if not client or not client.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Notion. Please configure Notion in Settings first."
            )

        # Export to Notion
        exporter = get_notion_exporter(notion_client=client)
        url = await exporter.export_to_notion(
            page_id=request.page_id,
            theme=request.theme,
            content=request.content,
            literature_review_heading=request.literature_review_heading
        )

        return NotionExportResponse(
            success=True,
            page_url=url,
            message="Successfully exported to Notion"
        )

    except ValueError as e:
        # Validation error (e.g., Literature Review not a toggle, or not found)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export to Notion: {str(e)}"
        )
