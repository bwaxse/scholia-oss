"""
Notion API client for Scholia.
Handles OAuth authentication and Notion API interactions.
"""

import os
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urlencode
import logging

from notion_client import AsyncClient
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


class NotionClient:
    """
    Notion API client with OAuth support.

    For single-user setup, access token is stored in environment variables.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        access_token: Optional[str] = None
    ):
        """
        Initialize Notion client.

        Args:
            client_id: Notion OAuth client ID (from env if not provided)
            client_secret: Notion OAuth client secret (from env if not provided)
            redirect_uri: OAuth redirect URI (from env if not provided)
            access_token: Notion access token (from env if not provided)
        """
        self.client_id = client_id or os.getenv("NOTION_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NOTION_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("NOTION_REDIRECT_URI")
        self.access_token = access_token or os.getenv("NOTION_ACCESS_TOKEN")

        # Initialize Notion API client if we have an access token
        self.notion: Optional[AsyncClient] = None
        if self.access_token:
            self.notion = AsyncClient(auth=self.access_token)

    def is_configured(self) -> bool:
        """Check if OAuth credentials are configured."""
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def is_authenticated(self) -> bool:
        """Check if we have a valid access token."""
        return bool(self.access_token and self.notion)

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to

        Raises:
            ValueError: If OAuth credentials not configured
        """
        if not self.is_configured():
            raise ValueError(
                "Notion OAuth not configured. Set NOTION_CLIENT_ID, "
                "NOTION_CLIENT_SECRET, and NOTION_REDIRECT_URI in .env"
            )

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "owner": "user",
            "redirect_uri": self.redirect_uri,
        }

        if state:
            params["state"] = state

        base_url = "https://api.notion.com/v1/oauth/authorize"
        return f"{base_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict:
        """
        Exchange OAuth authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dict with access_token, workspace_id, workspace_name, etc.

        Raises:
            ValueError: If OAuth credentials not configured
            Exception: If token exchange fails
        """
        if not self.is_configured():
            raise ValueError("Notion OAuth not configured")

        import aiohttp
        import base64

        # Encode credentials for Basic Auth
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        url = "https://api.notion.com/v1/oauth/token"
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Token exchange failed: {error_text}")

                result = await response.json()

                # Initialize Notion client with new token
                self.access_token = result.get("access_token")
                self.notion = AsyncClient(auth=self.access_token)

                return {
                    "access_token": result.get("access_token"),
                    "workspace_id": result.get("workspace_id"),
                    "workspace_name": result.get("workspace_name"),
                    "bot_id": result.get("bot_id"),
                    "owner": result.get("owner")
                }

    async def search_projects(
        self,
        query: Optional[str] = None,
        filter_type: str = "page"
    ) -> List[Dict]:
        """
        Search for pages in the Notion workspace.

        Prioritizes pages containing 'Literature Review' or 'Hypothesis' sections,
        but returns all pages as fallback.

        Args:
            query: Optional search query
            filter_type: Type of object to search for (default: "page")

        Returns:
            List of dicts with {id, title, url}

        Raises:
            ValueError: If not authenticated
        """
        if not self.is_authenticated():
            raise ValueError("Not authenticated with Notion")

        try:
            # Search for pages
            search_params = {
                "filter": {"property": "object", "value": filter_type}
            }

            if query:
                search_params["query"] = query

            results = await self.notion.search(**search_params)

            pages = []
            for page in results.get("results", []):
                if page.get("object") != "page":
                    continue

                # Extract title from properties
                title = self._extract_title(page)

                pages.append({
                    "id": page["id"],
                    "title": title or "Untitled",
                    "url": page.get("url", ""),
                    "parent": page.get("parent", {})
                })

            # Sort by title for consistent ordering
            pages.sort(key=lambda p: p["title"].lower())

            return pages

        except APIResponseError as e:
            logger.error(f"Notion API error in search_projects: {e}")
            raise

    async def fetch_page_content(self, page_id: str) -> str:
        """
        Fetch full page content as markdown-like text.

        Args:
            page_id: Notion page ID

        Returns:
            Page content as text

        Raises:
            ValueError: If not authenticated
        """
        if not self.is_authenticated():
            raise ValueError("Not authenticated with Notion")

        try:
            # Get page blocks
            blocks = await self._get_all_blocks(page_id)

            # Convert blocks to text
            content_parts = []
            for block in blocks:
                text = self._block_to_text(block)
                if text:
                    content_parts.append(text)

            return "\n\n".join(content_parts)

        except APIResponseError as e:
            logger.error(f"Notion API error in fetch_page_content: {e}")
            raise

    async def append_to_page(
        self,
        page_id: str,
        blocks: List[Dict],
        after_block_id: Optional[str] = None
    ) -> str:
        """
        Append blocks to a Notion page.

        Args:
            page_id: Notion page ID
            blocks: List of Notion block objects to append
            after_block_id: Optional block ID to insert after

        Returns:
            URL of the updated page

        Raises:
            ValueError: If not authenticated
        """
        if not self.is_authenticated():
            raise ValueError("Not authenticated with Notion")

        try:
            # If after_block_id specified, append to that block
            if after_block_id:
                await self.notion.blocks.children.append(
                    block_id=after_block_id,
                    children=blocks
                )
            else:
                # Append to page
                await self.notion.blocks.children.append(
                    block_id=page_id,
                    children=blocks
                )

            # Get page URL
            page = await self.notion.pages.retrieve(page_id=page_id)
            return page.get("url", "")

        except APIResponseError as e:
            logger.error(f"Notion API error in append_to_page: {e}")
            raise

    async def _get_all_blocks(self, block_id: str) -> List[Dict]:
        """Recursively get all blocks and their children."""
        blocks = []
        has_more = True
        start_cursor = None

        while has_more:
            response = await self.notion.blocks.children.list(
                block_id=block_id,
                start_cursor=start_cursor,
                page_size=100
            )

            for block in response.get("results", []):
                blocks.append(block)

                # Recursively get children if block has them
                if block.get("has_children"):
                    children = await self._get_all_blocks(block["id"])
                    block["children"] = children

            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

        return blocks

    def _extract_title(self, page: Dict) -> Optional[str]:
        """Extract title from page properties."""
        properties = page.get("properties", {})

        # Look for title property
        for prop_name, prop_value in properties.items():
            if prop_value.get("type") == "title":
                title_parts = prop_value.get("title", [])
                if title_parts:
                    return "".join(part.get("plain_text", "") for part in title_parts)

        return None

    def _block_to_text(self, block: Dict, indent: int = 0) -> str:
        """Convert a Notion block to text representation."""
        block_type = block.get("type")
        content = block.get(block_type, {})

        # Extract rich text
        rich_text = content.get("rich_text", [])
        text = "".join(part.get("plain_text", "") for part in rich_text)

        # Add indentation
        prefix = "  " * indent

        # Format based on block type
        if block_type == "heading_1":
            result = f"{prefix}# {text}"
        elif block_type == "heading_2":
            result = f"{prefix}## {text}"
        elif block_type == "heading_3":
            result = f"{prefix}### {text}"
        elif block_type == "bulleted_list_item":
            result = f"{prefix}- {text}"
        elif block_type == "numbered_list_item":
            result = f"{prefix}1. {text}"
        elif block_type == "toggle":
            result = f"{prefix}▶ {text}"
        else:
            result = f"{prefix}{text}" if text else ""

        # Add children
        children = block.get("children", [])
        if children:
            child_texts = [self._block_to_text(child, indent + 1) for child in children]
            child_text = "\n".join(t for t in child_texts if t)
            if child_text:
                result = f"{result}\n{child_text}"

        return result


# Singleton instance (deprecated - use get_notion_client_for_user instead)
_notion_client: Optional[NotionClient] = None


def get_notion_client() -> NotionClient:
    """
    Get singleton NotionClient instance.

    DEPRECATED: This uses global environment variables.
    Use get_notion_client_for_user() for per-user credentials instead.

    Returns:
        NotionClient instance
    """
    global _notion_client

    if _notion_client is None:
        _notion_client = NotionClient()

    return _notion_client


async def get_notion_client_for_user(user_id: str) -> Optional[NotionClient]:
    """
    Get NotionClient instance with user-specific credentials.

    Args:
        user_id: User ID to fetch credentials for

    Returns:
        NotionClient instance if user has configured Notion, None otherwise
    """
    from ..core.database import get_db_manager

    db = get_db_manager()

    async with db.get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT access_token, bot_id, workspace_id, workspace_name
            FROM user_notion_credentials
            WHERE user_id = $1
            """,
            user_id
        )

    if not row:
        return None

    # Create NotionClient with user's access token
    # OAuth credentials still come from environment (they're app-wide, not per-user)
    return NotionClient(
        client_id=os.getenv("NOTION_CLIENT_ID"),
        client_secret=os.getenv("NOTION_CLIENT_SECRET"),
        redirect_uri=os.getenv("NOTION_REDIRECT_URI"),
        access_token=row["access_token"]
    )
