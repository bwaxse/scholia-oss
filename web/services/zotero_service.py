"""
Zotero integration service for Scholia.
Handles all Zotero API operations for the web backend.
"""

import re
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio
from functools import partial

try:
    from pyzotero import zotero
    PYZOTERO_AVAILABLE = True
except ImportError:
    PYZOTERO_AVAILABLE = False
    zotero = None

from ..api.models.zotero import (
    ZoteroItem,
    ZoteroItemSummary,
    ZoteroItemData,
    ZoteroCreator,
    ZoteroTag,
)


class ZoteroService:
    """
    Manages Zotero API operations.

    Handles:
    - Paper search in Zotero library
    - Item retrieval by key
    - PDF download and path resolution
    - Note creation with insights
    - Related paper discovery
    """

    def __init__(self, api_key: Optional[str] = None, library_id: Optional[str] = None, library_type: str = "user"):
        """
        Initialize Zotero service.

        Args:
            api_key: Zotero API key
            library_id: Zotero library ID
            library_type: Library type ('user' or 'group'), defaults to 'user'
        """
        self.api_key = api_key
        self.library_id = library_id
        self.library_type = library_type

        # Initialize Zotero client if credentials available and pyzotero installed
        if PYZOTERO_AVAILABLE and self.api_key and self.library_id:
            self.zot = zotero.Zotero(self.library_id, self.library_type, self.api_key)
            self._configured = True
        else:
            self.zot = None
            self._configured = False

    def is_configured(self) -> bool:
        """Check if Zotero is properly configured."""
        return self._configured

    async def search_papers(self, query: str, limit: int = 10) -> List[ZoteroItemSummary]:
        """
        Search Zotero library for papers.

        Args:
            query: Search query (title, DOI, keywords, etc.)
            limit: Maximum number of results to return

        Returns:
            List of matching items as summaries

        Raises:
            ValueError: If Zotero not configured
        """
        if not self._configured:
            raise ValueError("Zotero is not configured. Please provide API key and library ID.")

        # Run blocking Zotero API call in thread pool
        loop = asyncio.get_event_loop()

        # Search top-level items only (excludes attachments, notes)
        # Check if query looks like a DOI
        if re.match(r'10\.\d+/.*', query):
            items = await loop.run_in_executor(None, partial(self.zot.top, q=query, limit=limit))
        else:
            # General search
            items = await loop.run_in_executor(None, partial(self.zot.top, q=query, limit=limit))

        # Convert to summaries
        summaries = []
        for item in items:
            summary = self._item_to_summary(item)
            if summary:
                summaries.append(summary)

        return summaries

    async def get_paper_by_key(self, key: str) -> Optional[ZoteroItem]:
        """
        Get a specific paper by its Zotero key.

        Args:
            key: Zotero item key

        Returns:
            ZoteroItem if found, None otherwise

        Raises:
            ValueError: If Zotero not configured
        """
        if not self._configured:
            raise ValueError("Zotero is not configured. Please provide API key and library ID.")

        try:
            loop = asyncio.get_event_loop()
            item = await loop.run_in_executor(None, self.zot.item, key)

            if item:
                return self._dict_to_zotero_item(item)
            return None

        except Exception as e:
            # Item not found or API error
            return None

    async def get_pdf_path(self, key: str) -> Optional[str]:
        """
        Get the file path to a PDF attachment for a Zotero item.

        Args:
            key: Zotero item key

        Returns:
            Path to PDF file, or None if not found

        Raises:
            ValueError: If Zotero not configured
        Note:
            This method downloads the PDF to a temp location.
            For production, consider caching or using Zotero storage paths.
        """
        if not self._configured:
            raise ValueError("Zotero is not configured. Please provide API key and library ID.")

        try:
            loop = asyncio.get_event_loop()

            # Get attachments for this item
            children = await loop.run_in_executor(None, self.zot.children, key)

            # Find PDF attachments
            pdf_attachments = [
                child for child in children
                if child['data'].get('contentType') == 'application/pdf'
            ]

            if not pdf_attachments:
                return None

            # Get the first PDF (or "Full Text PDF" if available)
            main_pdf = next(
                (att for att in pdf_attachments if att['data'].get('title') == 'Full Text PDF'),
                pdf_attachments[0]
            )

            # Download to temp directory
            temp_dir = Path(tempfile.gettempdir()) / "paper_companion_pdfs"
            temp_dir.mkdir(exist_ok=True)

            pdf_path = temp_dir / f"{key}_{main_pdf['key']}.pdf"

            # Download if not already cached
            if not pdf_path.exists():
                await loop.run_in_executor(
                    None,
                    partial(self.zot.dump, main_pdf['key'], filename=pdf_path.name, path=str(temp_dir))
                )

            return str(pdf_path)

        except Exception as e:
            return None

    async def list_recent(self, limit: int = 20) -> List[ZoteroItemSummary]:
        """
        List recent papers from Zotero library.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of recent items as summaries

        Raises:
            ValueError: If Zotero not configured
        """
        if not self._configured:
            raise ValueError("Zotero is not configured. Please provide API key and library ID.")

        loop = asyncio.get_event_loop()

        # Get recent top-level items sorted by date added
        # Using .top() instead of .items() to exclude child items (attachments, notes)
        items = await loop.run_in_executor(
            None,
            partial(self.zot.top, limit=limit, sort='dateAdded', direction='desc')
        )

        # Convert to summaries
        summaries = []
        for item in items:
            summary = self._item_to_summary(item)
            if summary:
                summaries.append(summary)

        return summaries

    async def save_insights_to_note(
        self,
        parent_item_key: str,
        note_html: str,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Save insights as a note attached to a Zotero item.

        Args:
            parent_item_key: Zotero item key to attach note to
            note_html: HTML content of the note
            tags: Optional list of tags to add to the note

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If Zotero not configured
        """
        if not self._configured:
            raise ValueError("Zotero is not configured. Please provide API key and library ID.")

        try:
            loop = asyncio.get_event_loop()

            # Create note template
            note_template = await loop.run_in_executor(None, self.zot.item_template, 'note')

            # Configure note
            note_template['note'] = note_html
            note_template['parentItem'] = parent_item_key

            # Add tags
            if tags:
                note_template['tags'] = [{"tag": tag} for tag in tags]

            # Create the note
            await loop.run_in_executor(None, self.zot.create_items, [note_template])

            return True

        except Exception as e:
            return False

    async def get_related_papers(self, tags: List[str], limit: int = 5) -> List[ZoteroItemSummary]:
        """
        Find papers in library with similar tags.

        Args:
            tags: List of tags to search for
            limit: Maximum number of results per tag

        Returns:
            List of related paper summaries

        Raises:
            ValueError: If Zotero not configured
        """
        if not self._configured:
            raise ValueError("Zotero is not configured. Please provide API key and library ID.")

        loop = asyncio.get_event_loop()

        related_items = []
        seen_keys = set()

        # Search for items with each tag
        for tag in tags[:3]:  # Limit to top 3 tags to avoid too many API calls
            try:
                items = await loop.run_in_executor(
                    None,
                    partial(self.zot.items, tag=tag, limit=limit)
                )

                for item in items:
                    key = item.get('key')
                    if key and key not in seen_keys:
                        seen_keys.add(key)
                        summary = self._item_to_summary(item)
                        if summary:
                            related_items.append(summary)

            except Exception:
                continue  # Skip failed tag searches

        return related_items[:limit]  # Return top N unique items

    def _item_to_summary(self, item: Dict[str, Any]) -> Optional[ZoteroItemSummary]:
        """
        Convert Zotero API item to summary model.

        Args:
            item: Raw Zotero item dict

        Returns:
            ZoteroItemSummary or None if conversion fails
        """
        try:
            data = item.get('data', {})

            # Extract title
            title = data.get('title', 'Untitled')

            # Format authors
            creators = data.get('creators', [])
            if creators:
                first_creator = creators[0]
                if 'lastName' in first_creator:
                    authors = f"{first_creator['lastName']} et al." if len(creators) > 1 else first_creator['lastName']
                else:
                    authors = first_creator.get('name', 'Unknown')
            else:
                authors = "Unknown"

            # Extract year from date
            date_str = data.get('date', '')
            year = date_str[:4] if date_str and len(date_str) >= 4 else None

            # Get publication
            publication = data.get('publicationTitle') or data.get('bookTitle')

            # Check if item has attachments (children)
            # Note: This is a heuristic - numChildren > 0 suggests attachments may exist
            # The actual check for PDF happens when loading the paper
            meta = item.get('meta', {})
            has_pdf = meta.get('numChildren', 0) > 0

            return ZoteroItemSummary(
                key=item.get('key', ''),
                title=title,
                authors=authors,
                year=year,
                publication=publication,
                item_type=data.get('itemType', 'unknown'),
                has_pdf=has_pdf
            )

        except Exception:
            return None

    def _dict_to_zotero_item(self, item_dict: Dict[str, Any]) -> ZoteroItem:
        """
        Convert raw Zotero API response to ZoteroItem model.

        Args:
            item_dict: Raw Zotero item dictionary

        Returns:
            ZoteroItem pydantic model
        """
        data = item_dict.get('data', {})

        # Convert creators
        creators = [
            ZoteroCreator(
                creatorType=c.get('creatorType', 'author'),
                firstName=c.get('firstName'),
                lastName=c.get('lastName'),
                name=c.get('name')
            )
            for c in data.get('creators', [])
        ]

        # Convert tags
        tags = [
            ZoteroTag(tag=t['tag'], type=t.get('type'))
            for t in data.get('tags', [])
        ]

        # Build item data
        item_data = ZoteroItemData(
            key=data.get('key', ''),
            version=data.get('version', 0),
            itemType=data.get('itemType', 'unknown'),
            title=data.get('title'),
            creators=creators,
            abstractNote=data.get('abstractNote'),
            publicationTitle=data.get('publicationTitle'),
            journalAbbreviation=data.get('journalAbbreviation'),
            volume=data.get('volume'),
            issue=data.get('issue'),
            pages=data.get('pages'),
            date=data.get('date'),
            DOI=data.get('DOI'),
            url=data.get('url'),
            accessDate=data.get('accessDate'),
            tags=tags
        )

        return ZoteroItem(
            key=item_dict.get('key', ''),
            version=item_dict.get('version', 0),
            library=item_dict.get('library', {}),
            data=item_data,
            meta=item_dict.get('meta')
        )


async def get_user_zotero_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Zotero credentials for a specific user from the database.

    Args:
        user_id: User's database ID

    Returns:
        Dict with api_key, library_id, library_type or None if not configured
    """
    from ..core.database import get_db_manager
    db = get_db_manager()

    async with db.get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT api_key, library_id, library_type
            FROM user_zotero_credentials
            WHERE user_id = $1
            """,
            user_id
        )

    if row:
        return {
            "api_key": row["api_key"],
            "library_id": row["library_id"],
            "library_type": row["library_type"]
        }
    return None


async def get_zotero_service_for_user(user_id: str) -> ZoteroService:
    """
    Get a ZoteroService instance configured for a specific user.

    Args:
        user_id: User's database ID

    Returns:
        ZoteroService: Configured for the user's credentials

    Note:
        Returns an unconfigured service if user has no Zotero credentials.
        Caller should check is_configured() before using.
    """
    credentials = await get_user_zotero_credentials(user_id)

    if credentials:
        return ZoteroService(
            api_key=credentials["api_key"],
            library_id=credentials["library_id"],
            library_type=credentials["library_type"]
        )
    else:
        # Return unconfigured service - caller should check is_configured()
        return ZoteroService(api_key=None, library_id=None)


