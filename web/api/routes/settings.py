"""
User settings routes.

Endpoints:
- GET /api/settings/zotero - Get user's Zotero configuration status
- PUT /api/settings/zotero - Save user's Zotero credentials
- DELETE /api/settings/zotero - Remove user's Zotero credentials
- GET /api/settings/notion - Get user's Notion configuration status
- PUT /api/settings/notion - Save user's Notion credentials
- DELETE /api/settings/notion - Remove user's Notion credentials
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import logging

from .auth import require_active
from ...core.database import get_db_manager

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger(__name__)


class ZoteroConfigRequest(BaseModel):
    """Request model for saving Zotero credentials."""
    api_key: str
    library_id: str
    library_type: str = "user"  # 'user' or 'group'


class ZoteroConfigResponse(BaseModel):
    """Response model for Zotero configuration status."""
    configured: bool
    library_id: Optional[str] = None
    library_type: Optional[str] = None
    # Note: api_key is never returned for security


@router.get("/zotero", response_model=ZoteroConfigResponse)
async def get_zotero_config(user: dict = Depends(require_active)):
    """
    Get user's Zotero configuration status.

    Returns whether Zotero is configured (but not the API key).
    """
    db = get_db_manager()

    async with db.get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT library_id, library_type
            FROM user_zotero_credentials
            WHERE user_id = $1
            """,
            user["id"]
        )

    if row:
        return ZoteroConfigResponse(
            configured=True,
            library_id=row["library_id"],
            library_type=row["library_type"]
        )
    else:
        return ZoteroConfigResponse(configured=False)


@router.put("/zotero", response_model=ZoteroConfigResponse)
async def save_zotero_config(
    config: ZoteroConfigRequest,
    user: dict = Depends(require_active)
):
    """
    Save user's Zotero credentials.

    Stores API key, library ID, and library type for per-user Zotero access.
    """
    db = get_db_manager()

    async with db.get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO user_zotero_credentials (user_id, api_key, library_id, library_type, updated_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (user_id) DO UPDATE
            SET api_key = $2, library_id = $3, library_type = $4, updated_at = NOW()
            """,
            user["id"], config.api_key, config.library_id, config.library_type
        )

    logger.info(f"User {user['email']} saved Zotero config for library {config.library_id}")

    return ZoteroConfigResponse(
        configured=True,
        library_id=config.library_id,
        library_type=config.library_type
    )


@router.delete("/zotero")
async def delete_zotero_config(user: dict = Depends(require_active)):
    """
    Remove user's Zotero credentials.
    """
    db = get_db_manager()

    async with db.get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM user_zotero_credentials WHERE user_id = $1",
            user["id"]
        )

    logger.info(f"User {user['email']} removed Zotero config")

    return {"success": True, "message": "Zotero credentials removed"}


# ============================================================================
# Notion Settings Endpoints
# ============================================================================

class NotionConfigRequest(BaseModel):
    """Request model for saving Notion credentials."""
    access_token: str
    bot_id: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None


class NotionConfigResponse(BaseModel):
    """Response model for Notion configuration status."""
    configured: bool
    workspace_name: Optional[str] = None
    workspace_id: Optional[str] = None
    # Note: access_token is never returned for security


@router.get("/notion", response_model=NotionConfigResponse)
async def get_notion_config(user: dict = Depends(require_active)):
    """
    Get user's Notion configuration status.

    Returns whether Notion is configured (but not the access token).
    """
    db = get_db_manager()

    async with db.get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT workspace_id, workspace_name
            FROM user_notion_credentials
            WHERE user_id = $1
            """,
            user["id"]
        )

    if row:
        return NotionConfigResponse(
            configured=True,
            workspace_id=row["workspace_id"],
            workspace_name=row["workspace_name"]
        )
    else:
        return NotionConfigResponse(configured=False)


@router.put("/notion", response_model=NotionConfigResponse)
async def save_notion_config(
    config: NotionConfigRequest,
    user: dict = Depends(require_active)
):
    """
    Save user's Notion credentials.

    Stores OAuth access token and workspace info for per-user Notion access.
    """
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
            user["id"], config.access_token, config.bot_id,
            config.workspace_id, config.workspace_name
        )

    logger.info(f"User {user['email']} saved Notion config for workspace {config.workspace_name}")

    return NotionConfigResponse(
        configured=True,
        workspace_id=config.workspace_id,
        workspace_name=config.workspace_name
    )


@router.delete("/notion")
async def delete_notion_config(user: dict = Depends(require_active)):
    """
    Remove user's Notion credentials.
    """
    db = get_db_manager()

    async with db.get_connection() as conn:
        # Delete credentials
        await conn.execute(
            "DELETE FROM user_notion_credentials WHERE user_id = $1",
            user["id"]
        )
        # Also clear the cache for this user
        await conn.execute(
            "DELETE FROM notion_project_cache WHERE user_id = $1",
            user["id"]
        )

    logger.info(f"User {user['email']} removed Notion config")

    return {"success": True, "message": "Notion credentials removed"}
