"""
Session management service for Paper Companion.
Handles session creation, retrieval, and lifecycle management.
"""

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import tempfile
import shutil


def parse_title_from_analysis(analysis: str) -> tuple[dict, str]:
    """
    Parse paper metadata from Claude's initial analysis response.

    The analysis starts with structured header lines followed by bullet points:
        TITLE: [paper title]
        AUTHORS: [semicolon-separated authors] or Unknown
        JOURNAL: [journal name] or Unknown
        YEAR: [4-digit year] or Unknown
        - [ASPECT]: sentence...

    Args:
        analysis: The full analysis text from Claude

    Returns:
        Tuple of (metadata_dict, analysis_body)
        metadata_dict keys: title (str|None), authors (list[str]), journal (str|None), year (str|None)
        Fields set to None/[] when Unknown or not found.
    """
    metadata: dict = {"title": None, "authors": [], "journal": None, "year": None}
    lines = analysis.split('\n')
    body_start = len(lines)  # default: no body (handles headers-only response)

    for i, line in enumerate(lines):
        stripped = line.strip()
        upper = stripped.upper()

        if not stripped:
            continue  # skip blank lines between header fields
        elif upper.startswith('TITLE:'):
            val = stripped[6:].strip()
            if val and val.lower() != 'unknown':
                metadata['title'] = val
        elif upper.startswith('AUTHORS:'):
            val = stripped[8:].strip()
            if val and val.lower() != 'unknown':
                metadata['authors'] = [a.strip() for a in val.split(';') if a.strip()]
        elif upper.startswith('JOURNAL:'):
            val = stripped[8:].strip()
            if val and val.lower() != 'unknown':
                metadata['journal'] = val
        elif upper.startswith('YEAR:'):
            val = stripped[5:].strip()
            if val and val.lower() != 'unknown' and re.match(r'^\d{4}$', val):
                metadata['year'] = val
        else:
            body_start = i
            break

    analysis_body = '\n'.join(lines[body_start:]).strip()
    return metadata, analysis_body

from fastapi import UploadFile

from ..core.database import get_db_manager
from ..core.pdf_processor import PDFProcessor
from ..core.claude import get_claude_client
from ..api.models import (
    SessionResponse,
    SessionListItem,
    SessionList,
    SessionDetail,
    ConversationMessage,
    SessionMetadata,
)
from .zotero_service import get_zotero_service_for_user
from .metadata_service import get_metadata_service
from .usage_tracker import get_usage_tracker


class PageLimitExceededError(ValueError):
    """Raised when an uploaded PDF exceeds the user's tier page limit."""


class SessionManager:
    """
    Manages paper analysis sessions.

    Handles:
    - Session creation from PDF uploads or Zotero
    - PDF text extraction and initial analysis
    - Session storage and retrieval
    - Conversation history management
    - Session deletion
    """

    MAX_FILE_SIZE_BYTES = 32 * 1024 * 1024  # 32 MB

    def __init__(self, db_manager=None, pdf_processor=None, claude_client=None):
        """
        Initialize session manager with database and services.

        Args:
            db_manager: Database manager (optional, uses default if not provided)
            pdf_processor: PDF processor (optional, uses default if not provided)
            claude_client: Claude client (optional, uses default if not provided)
        """
        self.db = db_manager or get_db_manager()
        self.pdf_processor = pdf_processor or PDFProcessor()
        self.claude = claude_client or get_claude_client()

    def _generate_session_id(self) -> str:
        """Generate unique session identifier."""
        return secrets.token_urlsafe(16)

    async def create_session_from_pdf(
        self,
        file: UploadFile,
        user_id: str,
        save_pdf: bool = True,
        doi: Optional[str] = None,
        pmid: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> SessionResponse:
        """
        Create a new session from PDF upload.

        Args:
            file: Uploaded PDF file
            user_id: ID of the user creating the session
            save_pdf: Whether to save PDF to disk (default: True)
            doi: Optional DOI for metadata lookup
            pmid: Optional PMID for metadata lookup

        Returns:
            SessionResponse with session info and initial analysis

        Raises:
            ValueError: If file is not a PDF or processing fails
        """
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise ValueError("File must be a PDF")

        # Generate session ID
        session_id = self._generate_session_id()

        # Save PDF temporarily for processing
        temp_pdf_path = None
        saved_pdf_path = None

        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                # Copy uploaded file to temp
                shutil.copyfileobj(file.file, temp_file)
                temp_pdf_path = temp_file.name

            # Get file size from the temp file
            file_size_bytes = Path(temp_pdf_path).stat().st_size

            if file_size_bytes > self.MAX_FILE_SIZE_BYTES:
                size_mb = file_size_bytes / (1024 * 1024)
                raise ValueError(
                    f"This PDF is {size_mb:.0f} MB, which exceeds the 32 MB size limit. "
                    "Try compressing the PDF or using a version with lower image resolution."
                )

            # Extract PDF metadata
            pdf_metadata = await self.pdf_processor.extract_metadata(temp_pdf_path)
            page_count = pdf_metadata.get('page_count', 0)

            if max_pages is not None and page_count > max_pages:
                if max_pages == 40:
                    hint = "Please reduce the PDF to 40 pages or fewer."
                else:
                    hint = "Upgrade to Max for a 40-page limit."
                raise PageLimitExceededError(
                    f"This PDF has {page_count} pages, which exceeds the {max_pages}-page limit "
                    f"for your plan. {hint}"
                )

            # Get enriched metadata from CrossRef/PubMed (manual DOI/PMID or extracted from PDF)
            metadata_service = get_metadata_service()
            enriched_metadata = await metadata_service.extract_metadata_hybrid(
                pdf_metadata=pdf_metadata,
                doi=doi,
                pmid=pmid
            )

            # Get initial analysis from Claude (Haiku) - sends full PDF
            initial_analysis, usage_stats = await self.claude.initial_analysis(
                pdf_path=temp_pdf_path
            )

            # Parse metadata from Claude's analysis
            claude_metadata, analysis_body = parse_title_from_analysis(initial_analysis)

            # Priority: CrossRef/PubMed > PDF metadata > Claude extraction
            final_title = (
                enriched_metadata.get('title') or
                pdf_metadata.get('title') or
                claude_metadata['title']
            )

            # Save PDF to permanent location (required for PDF-based queries)
            pdf_dir = Path("data/pdfs")
            pdf_dir.mkdir(parents=True, exist_ok=True)
            saved_pdf_path = str(pdf_dir / f"{session_id}.pdf")
            shutil.copy2(temp_pdf_path, saved_pdf_path)

            # Store session in database
            now = datetime.utcnow()
            async with self.db.transaction() as conn:
                # Insert session with page_count and file_size_bytes
                await conn.execute(
                    """
                    INSERT INTO sessions (id, user_id, filename, pdf_path, page_count, file_size_bytes, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    session_id, user_id, file.filename, saved_pdf_path, page_count, file_size_bytes, now, now
                )

                # Store initial analysis as first conversation message
                await conn.execute(
                    """
                    INSERT INTO conversations (session_id, exchange_id, role, content, model, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    session_id, 0, "assistant", initial_analysis, usage_stats['model'], now
                )

                # Store enriched metadata (from CrossRef/PubMed or PDF or Claude extraction)
                if final_title or enriched_metadata.get('authors') or claude_metadata['authors']:
                    # Authors: CrossRef/PubMed > PDF metadata > Claude extraction
                    if enriched_metadata.get('authors'):
                        authors_json = json.dumps(enriched_metadata['authors'])
                    elif claude_metadata['authors']:
                        authors_json = json.dumps(claude_metadata['authors'])
                    elif pdf_metadata.get('author'):
                        authors_json = pdf_metadata.get('author')
                    else:
                        authors_json = None

                    # Journal and publication_date: CrossRef/PubMed > Claude extraction
                    final_journal = enriched_metadata.get('journal') or claude_metadata['journal']
                    final_pub_date = enriched_metadata.get('publication_date') or claude_metadata['year']

                    await conn.execute(
                        """
                        INSERT INTO metadata (session_id, title, authors, doi, publication_date, journal, journal_abbr, abstract)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        session_id,
                        final_title,
                        authors_json,
                        enriched_metadata.get('doi'),
                        final_pub_date,
                        final_journal,
                        enriched_metadata.get('journal_abbr'),
                        enriched_metadata.get('abstract')
                    )

            # Log usage tracking
            usage_tracker = get_usage_tracker()
            await usage_tracker.log_token_usage(
                operation_type='initial_analysis',
                provider='claude',
                usage_stats=usage_stats,
                session_id=session_id,
                user_id=user_id
            )
            await usage_tracker.log_user_event(
                event_type='paper_upload',
                metadata={
                    'filename': file.filename,
                    'source': 'upload',
                    'page_count': page_count,
                    'file_size_bytes': file_size_bytes
                },
                session_id=session_id,
                user_id=user_id
            )

            # Return session response
            return SessionResponse(
                session_id=session_id,
                filename=file.filename,
                initial_analysis=initial_analysis,
                created_at=now,
                updated_at=now,
                page_count=page_count,
                file_size_bytes=file_size_bytes
            )

        finally:
            # Clean up temp file
            if temp_pdf_path and Path(temp_pdf_path).exists():
                Path(temp_pdf_path).unlink()

    async def create_session_from_zotero(
        self,
        zotero_key: str,
        user_id: str,
        label: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> SessionResponse:
        """
        Create a new session from Zotero library item.

        Args:
            zotero_key: Zotero item key
            user_id: ID of the user creating the session
            label: Optional label to distinguish multiple sessions for same paper

        Returns:
            SessionResponse with session info and initial analysis

        Raises:
            ValueError: If Zotero item not found or no PDF attached
        """
        # Get Zotero service for this user
        zotero = await get_zotero_service_for_user(user_id)

        if not zotero.is_configured():
            raise ValueError("Zotero is not configured. Please add your Zotero credentials in Settings.")

        # Get Zotero item
        item = await zotero.get_paper_by_key(zotero_key)
        if not item:
            raise ValueError(f"Zotero item not found: {zotero_key}")

        # Get PDF path
        pdf_path = await zotero.get_pdf_path(zotero_key)
        if not pdf_path:
            paper_title = item.data.title or "this item"
            raise ValueError(f"No PDF attachment found for '{paper_title}'. Please attach a PDF to this item in Zotero.")

        # Generate session ID
        session_id = self._generate_session_id()

        # Get file size from the PDF
        file_size_bytes = Path(pdf_path).stat().st_size if Path(pdf_path).exists() else None

        # Extract PDF metadata
        metadata = await self.pdf_processor.extract_metadata(pdf_path)
        page_count = metadata.get('page_count', 0)

        if max_pages is not None and page_count > max_pages:
            if max_pages == 40:
                hint = "Please reduce the PDF to 40 pages or fewer."
            else:
                hint = "Upgrade to Max for a 40-page limit."
            raise PageLimitExceededError(
                f"This PDF has {page_count} pages, which exceeds the {max_pages}-page limit "
                f"for your plan. {hint}"
            )

        # Get initial analysis from Claude (Haiku) - sends full PDF
        initial_analysis, usage_stats = await self.claude.initial_analysis(
            pdf_path=pdf_path
        )

        # Store session in database
        now = datetime.utcnow()
        async with self.db.transaction() as conn:
            # Insert session with page_count, file_size_bytes, and optional label
            await conn.execute(
                """
                INSERT INTO sessions (id, user_id, filename, zotero_key, pdf_path, page_count, file_size_bytes, label, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                session_id, user_id, item.data.title or "Untitled", zotero_key, pdf_path, page_count, file_size_bytes, label, now, now
            )

            # Store initial analysis
            await conn.execute(
                """
                INSERT INTO conversations (session_id, exchange_id, role, content, model, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                session_id, 0, "assistant", initial_analysis, usage_stats['model'], now
            )

            # Store Zotero metadata if available
            if item.data.title or item.data.DOI:
                # Format authors as JSON string
                authors_json = None
                if item.data.creators:
                    authors_list = [
                        f"{c.lastName}, {c.firstName}" if c.lastName and c.firstName
                        else c.name or c.lastName or c.firstName or "Unknown"
                        for c in item.data.creators
                    ]
                    authors_json = json.dumps(authors_list)

                await conn.execute(
                    """
                    INSERT INTO metadata (session_id, title, authors, doi, publication_date, journal, journal_abbr, abstract)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    session_id,
                    item.data.title,
                    authors_json,
                    item.data.DOI,
                    item.data.date,
                    item.data.publicationTitle,
                    item.data.journalAbbreviation,
                    item.data.abstractNote
                )

        # Log usage tracking
        usage_tracker = get_usage_tracker()
        await usage_tracker.log_token_usage(
            operation_type='initial_analysis',
            provider='claude',
            usage_stats=usage_stats,
            session_id=session_id,
            user_id=user_id
        )
        await usage_tracker.log_user_event(
            event_type='paper_upload',
            metadata={
                'filename': item.data.title or "Untitled",
                'source': 'zotero',
                'zotero_key': zotero_key,
                'page_count': page_count,
                'file_size_bytes': file_size_bytes
            },
            session_id=session_id,
            user_id=user_id
        )

        # Return session response
        return SessionResponse(
            session_id=session_id,
            filename=item.data.title or "Untitled",
            initial_analysis=initial_analysis,
            created_at=now,
            updated_at=now,
            zotero_key=zotero_key,
            page_count=page_count,
            file_size_bytes=file_size_bytes,
            label=label
        )

    async def get_sessions_by_zotero_key(
        self,
        zotero_key: str,
        user_id: str
    ) -> "DuplicateCheckResponse":
        """
        Check if sessions already exist for a Zotero item.

        Args:
            zotero_key: Zotero item key
            user_id: ID of the user

        Returns:
            DuplicateCheckResponse with existing session info
        """
        from ..api.models.session import DuplicateCheckResponse, ExistingSessionInfo

        async with self.db.get_connection() as conn:
            # Get all sessions for this zotero_key and user, with exchange counts (exclude soft-deleted)
            rows = await conn.fetch(
                """
                SELECT
                    s.id, s.label, s.created_at,
                    m.title,
                    (SELECT COUNT(*) FROM conversations c
                     WHERE c.session_id = s.id AND c.exchange_id > 0 AND c.role = 'user' AND c.deleted_at IS NULL) as exchange_count
                FROM sessions s
                LEFT JOIN metadata m ON s.id = m.session_id
                WHERE s.zotero_key = $1 AND s.user_id = $2 AND s.deleted_at IS NULL
                ORDER BY s.created_at DESC
                """,
                zotero_key, user_id
            )

            if not rows:
                return DuplicateCheckResponse(exists=False, count=0, sessions=[], paper_title=None)

            sessions = [
                ExistingSessionInfo(
                    session_id=row['id'],
                    created_at=row['created_at'],
                    label=row['label'],
                    exchange_count=row['exchange_count'] or 0
                )
                for row in rows
            ]

            # Get paper title from the first result
            paper_title = rows[0]['title'] if rows[0]['title'] else None

            return DuplicateCheckResponse(
                exists=True,
                count=len(sessions),
                sessions=sessions,
                paper_title=paper_title
            )

    async def get_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[SessionDetail]:
        """
        Get full session details including conversation history.

        Args:
            session_id: Session identifier
            user_id: If provided, verify session belongs to this user

        Returns:
            SessionDetail with full conversation, or None if not found (or not owned by user)
        """
        async with self.db.get_connection() as conn:
            # Get session info with metadata title, authors, publication_date, journal, journal_abbr, page_count, file_size_bytes, and label
            # Exclude soft-deleted sessions
            if user_id:
                session_row = await conn.fetchrow(
                    """
                    SELECT s.id, s.filename, s.zotero_key, s.pdf_path, s.page_count, s.file_size_bytes, s.label, s.created_at, s.updated_at, m.title, m.authors, m.publication_date, m.journal, m.journal_abbr
                    FROM sessions s
                    LEFT JOIN metadata m ON s.id = m.session_id
                    WHERE s.id = $1 AND s.user_id = $2 AND s.deleted_at IS NULL
                    """,
                    session_id, user_id
                )
            else:
                session_row = await conn.fetchrow(
                    """
                    SELECT s.id, s.filename, s.zotero_key, s.pdf_path, s.page_count, s.file_size_bytes, s.label, s.created_at, s.updated_at, m.title, m.authors, m.publication_date, m.journal, m.journal_abbr
                    FROM sessions s
                    LEFT JOIN metadata m ON s.id = m.session_id
                    WHERE s.id = $1 AND s.deleted_at IS NULL
                    """,
                    session_id
                )

            if not session_row:
                return None

            # Use title from metadata if available, otherwise use filename
            display_name = session_row['title'] if session_row['title'] else session_row['filename']

            # Get conversation history (excluding deleted messages)
            conversation_rows = await conn.fetch(
                """
                SELECT exchange_id, role, content, model, highlighted_text, page_number, timestamp
                FROM conversations
                WHERE session_id = $1 AND deleted_at IS NULL
                ORDER BY exchange_id, id
                """,
                session_id
            )

            # Build conversation messages
            conversation = []
            for row in conversation_rows:
                ts = row['timestamp']
                conversation.append(ConversationMessage(
                    exchange_id=row['exchange_id'],
                    role=row['role'],
                    content=row['content'],
                    model=row['model'],
                    highlighted_text=row['highlighted_text'],
                    page_number=row['page_number'],
                    timestamp=ts if ts else datetime.utcnow()
                ))

            # Extract initial analysis (exchange_id = 0)
            initial_analysis = ""
            if conversation and conversation[0].exchange_id == 0:
                initial_analysis = conversation[0].content
                conversation = conversation[1:]  # Remove initial analysis from conversation

            # Get page count and file size from stored values
            page_count = session_row.get('page_count')
            file_size_bytes = session_row.get('file_size_bytes')

            # Get flags for this session
            flag_rows = await conn.fetch(
                """
                SELECT DISTINCT exchange_id
                FROM flags
                WHERE session_id = $1
                ORDER BY exchange_id
                """,
                session_id
            )
            flags = [row['exchange_id'] for row in flag_rows]

            return SessionDetail(
                session_id=session_row['id'],
                filename=display_name,  # Use title from metadata if available
                initial_analysis=initial_analysis,
                created_at=session_row['created_at'] if session_row['created_at'] else datetime.utcnow(),
                updated_at=session_row['updated_at'] if session_row['updated_at'] else datetime.utcnow(),
                zotero_key=session_row['zotero_key'],
                page_count=page_count,
                file_size_bytes=file_size_bytes,
                label=session_row.get('label'),
                title=session_row['title'],
                authors=session_row['authors'],
                publication_date=session_row['publication_date'],
                journal=session_row['journal'],
                journal_abbr=session_row['journal_abbr'],
                conversation=conversation,
                flags=flags
            )

    async def list_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> SessionList:
        """
        List user's sessions with pagination.

        Args:
            user_id: ID of the user whose sessions to list
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            SessionList with sessions and total count
        """
        async with self.db.get_connection() as conn:
            # Get total count for user (exclude soft-deleted sessions)
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM sessions WHERE user_id = $1 AND deleted_at IS NULL",
                user_id
            )
            total = total or 0

            # Get sessions with metadata title, authors, publication_date, journal, journal_abbr, page_count, file_size_bytes, and label
            # Exclude soft-deleted sessions
            session_rows = await conn.fetch(
                """
                SELECT s.id, s.filename, s.zotero_key, s.page_count, s.file_size_bytes, s.label, s.created_at, s.updated_at, m.title, m.authors, m.publication_date, m.journal, m.journal_abbr
                FROM sessions s
                LEFT JOIN metadata m ON s.id = m.session_id
                WHERE s.user_id = $1 AND s.deleted_at IS NULL
                ORDER BY s.created_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id, limit, offset
            )

            # Build session list items
            sessions = []
            for row in session_rows:
                # Use title from metadata if available, otherwise use filename
                display_name = row['title'] if row['title'] else row['filename']
                sessions.append(SessionListItem(
                    session_id=row['id'],
                    filename=display_name,
                    created_at=row['created_at'] if row['created_at'] else datetime.utcnow(),
                    updated_at=row['updated_at'] if row['updated_at'] else datetime.utcnow(),
                    zotero_key=row['zotero_key'],
                    page_count=row.get('page_count'),
                    file_size_bytes=row.get('file_size_bytes'),
                    label=row.get('label'),
                    title=row['title'],
                    authors=row['authors'],
                    publication_date=row['publication_date'],
                    journal=row['journal'],
                    journal_abbr=row['journal_abbr']
                ))

            return SessionList(sessions=sessions, total=total)

    async def delete_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """
        Soft-delete a session (sets deleted_at timestamp).

        Preserves session and all associated data (conversations, insights, etc.) for token usage analytics.
        Deleted sessions are hidden from UI but remain queryable for analysis.

        Args:
            session_id: Session identifier
            user_id: If provided, verify session belongs to this user

        Returns:
            True if deleted, False if session not found (or not owned by user)
        """
        async with self.db.transaction() as conn:
            # Soft-delete session by setting deleted_at timestamp
            # Keep PDF files and all related data for analytics
            if user_id:
                result = await conn.execute(
                    "UPDATE sessions SET deleted_at = NOW() WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
                    session_id, user_id
                )
            else:
                result = await conn.execute(
                    "UPDATE sessions SET deleted_at = NOW() WHERE id = $1 AND deleted_at IS NULL",
                    session_id
                )

            # result is like "UPDATE 1" if successful, "UPDATE 0" if not found
            return result.split()[1] == "1"

    async def restore_session(self, session_id: str) -> Optional[SessionDetail]:
        """
        Restore full session for "pick up where you left off" functionality.

        This is an alias for get_session() that returns complete conversation history.

        Args:
            session_id: Session identifier

        Returns:
            SessionDetail with full conversation history, or None if not found
        """
        return await self.get_session(session_id)

    async def get_session_pdf_path(self, session_id: str) -> Optional[str]:
        """
        Get the PDF path for a session.

        Args:
            session_id: Session identifier

        Returns:
            PDF file path, or None if session not found
        """
        async with self.db.get_connection() as conn:
            return await conn.fetchval(
                "SELECT pdf_path FROM sessions WHERE id = $1",
                session_id
            )

    async def update_session_timestamp(self, session_id: str) -> None:
        """
        Update session's last activity timestamp.

        Args:
            session_id: Session identifier
        """
        async with self.db.transaction() as conn:
            await conn.execute(
                "UPDATE sessions SET updated_at = $1 WHERE id = $2",
                datetime.utcnow(), session_id
            )


# Global instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get global session manager instance (singleton pattern).

    Returns:
        SessionManager: Session manager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


# Convenience functions
async def create_session_from_pdf(file: UploadFile, user_id: str) -> SessionResponse:
    """Create session from PDF upload."""
    manager = get_session_manager()
    return await manager.create_session_from_pdf(file, user_id=user_id)


async def get_session(session_id: str, user_id: Optional[str] = None) -> Optional[SessionDetail]:
    """Get session details."""
    manager = get_session_manager()
    return await manager.get_session(session_id, user_id=user_id)


async def list_sessions(user_id: str, limit: int = 50, offset: int = 0) -> SessionList:
    """List user's sessions."""
    manager = get_session_manager()
    return await manager.list_sessions(user_id=user_id, limit=limit, offset=offset)


async def delete_session(session_id: str, user_id: Optional[str] = None) -> bool:
    """Delete session."""
    manager = get_session_manager()
    return await manager.delete_session(session_id, user_id=user_id)
