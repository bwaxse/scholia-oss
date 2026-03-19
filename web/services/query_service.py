"""
Query service for handling conversations with LLM providers.
Manages question/answer exchanges, flags, and highlights.
Supports both Claude (Anthropic) and Gemini (Google) models.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from ..core.database import get_db_manager
from ..core.claude import get_claude_client
from ..core.gemini import get_gemini_client, is_gemini_available
from ..api.models import (
    QueryRequest,
    QueryResponse,
    FlagResponse,
    Highlight,
    HighlightList,
)
from .usage_tracker import get_usage_tracker

logger = logging.getLogger(__name__)


class QueryService:
    """
    Manages conversational queries with LLM providers.

    Handles:
    - Sending queries to Claude or Gemini with paper context
    - Routing to appropriate provider based on model selection
    - Storing conversation exchanges
    - Flagging important exchanges
    - Managing text highlights
    """

    def __init__(self, db_manager=None, claude_client=None, gemini_client=None):
        """
        Initialize query service.

        Args:
            db_manager: Database manager (optional)
            claude_client: Claude client (optional)
            gemini_client: Gemini client (optional)
        """
        self.db = db_manager or get_db_manager()
        self.claude = claude_client or get_claude_client()
        self.gemini = gemini_client or get_gemini_client()  # May be None if not configured

    async def query_paper(
        self,
        session_id: str,
        request: QueryRequest
    ) -> QueryResponse:
        """
        Ask a question about the paper.

        Args:
            session_id: Session identifier
            request: Query request with question and optional context

        Returns:
            QueryResponse with Claude's answer

        Raises:
            ValueError: If session not found
        """
        # Get session PDF path and conversation history
        async with self.db.get_connection() as conn:
            # Verify session exists and get PDF path (and zotero_key, user_id for re-download)
            row = await conn.fetchrow(
                "SELECT pdf_path, zotero_key, user_id FROM sessions WHERE id = $1",
                session_id
            )

            if not row:
                raise ValueError(f"Session not found: {session_id}")

            pdf_path = row['pdf_path']
            zotero_key = row['zotero_key']
            user_id = row['user_id']

            # Check if PDF exists - if not and this is a Zotero session, re-download
            if not Path(pdf_path).exists():
                if zotero_key and user_id:
                    logger.info(f"PDF missing at {pdf_path}, re-downloading from Zotero for key {zotero_key}")
                    from .zotero_service import get_zotero_service_for_user
                    zotero = await get_zotero_service_for_user(user_id)
                    if zotero.is_configured():
                        new_pdf_path = await zotero.get_pdf_path(zotero_key)
                        if new_pdf_path:
                            pdf_path = new_pdf_path
                            # Update the stored path in case it changed
                            await conn.execute(
                                "UPDATE sessions SET pdf_path = $1 WHERE id = $2",
                                pdf_path, session_id
                            )
                            logger.info(f"Re-downloaded PDF to {pdf_path}")
                        else:
                            raise ValueError(f"Could not re-download PDF from Zotero for session {session_id}")
                    else:
                        raise ValueError(f"Zotero not configured for user. Please check your Zotero settings.")
                else:
                    raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            # Get conversation history (excluding deleted messages)
            history_rows = await conn.fetch(
                """
                SELECT role, content FROM conversations
                WHERE session_id = $1 AND exchange_id > 0 AND deleted_at IS NULL
                ORDER BY exchange_id, id
                """,
                session_id
            )

        # Build conversation context
        conversation_history = []
        for row in history_rows:
            conversation_history.append({
                "role": row['role'],
                "content": row['content']
            })

        # Build current query
        query_content = request.query
        if request.highlighted_text:
            query_content = f"{request.query}\n\nHighlighted text: {request.highlighted_text}"
        if request.page_number:
            query_content += f"\n(Page {request.page_number})"

        # Route to appropriate provider based on model selection
        model = request.model or 'sonnet'
        use_thinking = request.use_thinking

        # Thinking only works with frontier models (sonnet, gemini-flash, gemini-pro) - not haiku
        if use_thinking and model not in ('sonnet', 'gemini-flash', 'gemini-pro'):
            use_thinking = False
            logger.info(f"Thinking disabled: only available with sonnet/gemini models, not {model}")

        if model.startswith('gemini'):
            # Use Gemini with full PDF document
            if not self.gemini:
                raise ValueError("Gemini is not configured. Please set GOOGLE_API_KEY.")

            use_pro = (model == 'gemini-pro')
            provider = 'gemini'
            logger.info(f"Routing query to Gemini ({model}) with PDF (thinking: {use_thinking})")
            response_text, usage_stats = await self.gemini.query(
                user_query=query_content,
                pdf_path=pdf_path,
                conversation_history=conversation_history,
                use_pro=use_pro,
                use_thinking=use_thinking,
                session_id=session_id
            )
        else:
            # Use Claude with full PDF document
            use_sonnet = (model == 'sonnet')
            provider = 'claude'
            logger.info(f"Routing query to Claude ({model}) with PDF (thinking: {use_thinking})")
            response_text, usage_stats = await self.claude.query(
                user_query=query_content,
                pdf_path=pdf_path,
                conversation_history=conversation_history,
                use_sonnet=use_sonnet,
                use_thinking=use_thinking
            )

        # Get next exchange ID
        async with self.db.transaction() as conn:
            row = await conn.fetchrow(
                "SELECT MAX(exchange_id) FROM conversations WHERE session_id = $1",
                session_id
            )
            next_exchange_id = (row[0] or 0) + 1

            # Store user query
            await conn.execute(
                """
                INSERT INTO conversations
                (session_id, exchange_id, role, content, highlighted_text, page_number, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                session_id,
                next_exchange_id,
                "user",
                request.query,
                request.highlighted_text,
                request.page_number,
                datetime.utcnow()
            )

            # Store assistant response
            await conn.execute(
                """
                INSERT INTO conversations
                (session_id, exchange_id, role, content, model, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                session_id,
                next_exchange_id,
                "assistant",
                response_text,
                usage_stats['model'],
                datetime.utcnow()
            )

            # Update session timestamp
            await conn.execute(
                "UPDATE sessions SET updated_at = $1 WHERE id = $2",
                datetime.utcnow(), session_id
            )

        # Log usage tracking
        usage_tracker = get_usage_tracker()
        await usage_tracker.log_token_usage(
            operation_type='query',
            provider=provider,
            usage_stats=usage_stats,
            session_id=session_id,
            exchange_id=next_exchange_id
        )
        await usage_tracker.log_user_event(
            event_type='question_asked',
            metadata={'exchange_id': next_exchange_id, 'use_thinking': use_thinking},
            session_id=session_id
        )

        return QueryResponse(
            exchange_id=next_exchange_id,
            response=response_text,
            model_used=usage_stats['model'],
            use_thinking=usage_stats.get('use_thinking', False),
            usage=usage_stats
        )

    async def flag_exchange(
        self,
        session_id: str,
        exchange_id: int,
        note: Optional[str] = None
    ) -> FlagResponse:
        """
        Flag an exchange for later review.

        Args:
            session_id: Session identifier
            exchange_id: Exchange ID to flag
            note: Optional note about why flagged

        Returns:
            FlagResponse with success status

        Raises:
            ValueError: If session or exchange not found
        """
        async with self.db.transaction() as conn:
            # Verify exchange exists (and is not deleted)
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM conversations
                WHERE session_id = $1 AND exchange_id = $2 AND deleted_at IS NULL
                """,
                session_id, exchange_id
            )

            if count == 0:
                raise ValueError(f"Exchange {exchange_id} not found in session {session_id}")

            # Check if already flagged
            existing = await conn.fetchrow(
                """
                SELECT id FROM flags
                WHERE session_id = $1 AND exchange_id = $2
                """,
                session_id, exchange_id
            )

            if existing:
                # Already flagged, update note if provided
                if note is not None:
                    await conn.execute(
                        "UPDATE flags SET note = $1 WHERE id = $2",
                        note, existing['id']
                    )
                return FlagResponse(
                    success=True,
                    message="Exchange already flagged, note updated",
                    flag_id=existing['id']
                )

            # Create new flag
            flag_id = await conn.fetchval(
                """
                INSERT INTO flags (session_id, exchange_id, note, created_at)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                session_id, exchange_id, note, datetime.utcnow()
            )

        return FlagResponse(
            success=True,
            message="Exchange flagged successfully",
            flag_id=flag_id
        )

    async def unflag_exchange(
        self,
        session_id: str,
        exchange_id: int
    ) -> FlagResponse:
        """
        Remove flag from an exchange.

        Args:
            session_id: Session identifier
            exchange_id: Exchange ID to unflag

        Returns:
            FlagResponse with success status
        """
        async with self.db.transaction() as conn:
            # Delete flag and get status
            status = await conn.execute(
                """
                DELETE FROM flags
                WHERE session_id = $1 AND exchange_id = $2
                """,
                session_id, exchange_id
            )

            # Parse status string "DELETE N" to get row count
            rowcount = int(status.split()[-1]) if status else 0

            if rowcount == 0:
                return FlagResponse(
                    success=False,
                    message="Exchange was not flagged",
                    flag_id=None
                )

        return FlagResponse(
            success=True,
            message="Flag removed successfully",
            flag_id=None
        )

    async def add_highlight(
        self,
        session_id: str,
        text: str,
        page_number: Optional[int] = None,
        exchange_id: Optional[int] = None
    ) -> Highlight:
        """
        Add a text highlight.

        Args:
            session_id: Session identifier
            text: Highlighted text
            page_number: Optional page number
            exchange_id: Optional associated exchange

        Returns:
            Highlight with ID and timestamp

        Raises:
            ValueError: If session not found
        """
        async with self.db.transaction() as conn:
            # Verify session exists
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM sessions WHERE id = $1",
                session_id
            )
            if count == 0:
                raise ValueError(f"Session not found: {session_id}")

            # Insert highlight
            now = datetime.utcnow()
            highlight_id = await conn.fetchval(
                """
                INSERT INTO highlights (session_id, text, page_number, exchange_id, created_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                session_id, text, page_number, exchange_id, now
            )

        return Highlight(
            id=highlight_id,
            text=text,
            page_number=page_number,
            exchange_id=exchange_id,
            created_at=now.isoformat()
        )

    async def get_highlights(
        self,
        session_id: str
    ) -> HighlightList:
        """
        Get all highlights for a session.

        Args:
            session_id: Session identifier

        Returns:
            HighlightList with all highlights
        """
        async with self.db.get_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, text, page_number, exchange_id, created_at
                FROM highlights
                WHERE session_id = $1
                ORDER BY created_at DESC
                """,
                session_id
            )

            highlights = []
            for row in rows:
                highlights.append(Highlight(
                    id=row['id'],
                    text=row['text'],
                    page_number=row['page_number'],
                    exchange_id=row['exchange_id'],
                    created_at=row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat()
                ))

            return HighlightList(
                highlights=highlights,
                total=len(highlights)
            )

    async def delete_highlight(
        self,
        session_id: str,
        highlight_id: int
    ) -> bool:
        """
        Delete a highlight.

        Args:
            session_id: Session identifier
            highlight_id: Highlight ID

        Returns:
            True if deleted, False if not found
        """
        async with self.db.transaction() as conn:
            status = await conn.execute(
                """
                DELETE FROM highlights
                WHERE id = $1 AND session_id = $2
                """,
                highlight_id, session_id
            )

            # Parse status string "DELETE N" to get row count
            rowcount = int(status.split()[-1]) if status else 0
            return rowcount > 0

    async def delete_exchange(
        self,
        session_id: str,
        exchange_id: int
    ) -> bool:
        """
        Delete a Q&A exchange from the conversation.

        Args:
            session_id: Session identifier
            exchange_id: Exchange ID to delete

        Returns:
            True if deleted, False if not found
        """
        async with self.db.transaction() as conn:
            # Soft-delete the exchange (set deleted_at timestamp)
            # This preserves token_usage metrics while hiding from UI
            status = await conn.execute(
                """
                UPDATE conversations
                SET deleted_at = NOW()
                WHERE session_id = $1 AND exchange_id = $2 AND deleted_at IS NULL
                """,
                session_id, exchange_id
            )

            # Also delete any associated flags (these don't need soft-delete)
            await conn.execute(
                """
                DELETE FROM flags
                WHERE session_id = $1 AND exchange_id = $2
                """,
                session_id, exchange_id
            )

            # Parse status string "UPDATE N" to get row count
            rowcount = int(status.split()[-1]) if status else 0
            return rowcount > 0

    async def evaluate_message(
        self,
        session_id: str,
        exchange_id: int,
        rating: str,
        reason_inaccurate: bool = False,
        reason_unhelpful: bool = False,
        reason_off_topic: bool = False,
        reason_other: bool = False,
        feedback_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save or update a message evaluation (UPSERT pattern).

        Args:
            session_id: Session identifier
            exchange_id: Exchange ID to evaluate
            rating: 'positive' or 'negative'
            reason_inaccurate: Response was inaccurate (negative only)
            reason_unhelpful: Response was unhelpful (negative only)
            reason_off_topic: Response was off-topic (negative only)
            reason_other: Other issue (negative only)
            feedback_text: Optional detailed feedback

        Returns:
            Dict with success status, message, and evaluation_id

        Raises:
            ValueError: If exchange doesn't exist
        """
        async with self.db.transaction() as conn:
            # Verify exchange exists (not deleted)
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM conversations
                WHERE session_id = $1 AND exchange_id = $2 AND deleted_at IS NULL
                """,
                session_id, exchange_id
            )

            if count == 0:
                raise ValueError(f"Exchange {exchange_id} not found")

            # Upsert evaluation (insert or update if exists)
            evaluation_id = await conn.fetchval(
                """
                INSERT INTO message_evaluations (
                    session_id, exchange_id, rating,
                    reason_inaccurate, reason_unhelpful, reason_off_topic, reason_other,
                    feedback_text, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                ON CONFLICT (session_id, exchange_id)
                DO UPDATE SET
                    rating = EXCLUDED.rating,
                    reason_inaccurate = EXCLUDED.reason_inaccurate,
                    reason_unhelpful = EXCLUDED.reason_unhelpful,
                    reason_off_topic = EXCLUDED.reason_off_topic,
                    reason_other = EXCLUDED.reason_other,
                    feedback_text = EXCLUDED.feedback_text,
                    updated_at = NOW()
                RETURNING id
                """,
                session_id, exchange_id, rating,
                reason_inaccurate, reason_unhelpful, reason_off_topic, reason_other,
                feedback_text
            )

        return {
            "success": True,
            "message": "Evaluation saved",
            "evaluation_id": evaluation_id
        }

    async def get_message_evaluation(
        self, session_id: str, exchange_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing evaluation for a message.

        Args:
            session_id: Session identifier
            exchange_id: Exchange ID

        Returns:
            Dict with evaluation data if found, None otherwise
        """
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT rating, reason_inaccurate, reason_unhelpful,
                       reason_off_topic, reason_other, feedback_text
                FROM message_evaluations
                WHERE session_id = $1 AND exchange_id = $2
                """,
                session_id, exchange_id
            )

            return dict(row) if row else None

    async def delete_message_evaluation(
        self, session_id: str, exchange_id: int
    ) -> bool:
        """
        Delete a message evaluation (when user toggles off their rating).

        Args:
            session_id: Session identifier
            exchange_id: Exchange ID

        Returns:
            True if evaluation was deleted, False if not found
        """
        async with self.db.transaction() as conn:
            status = await conn.execute(
                """
                DELETE FROM message_evaluations
                WHERE session_id = $1 AND exchange_id = $2
                """,
                session_id, exchange_id
            )

            # Parse status string "DELETE N" to get row count
            rowcount = int(status.split()[-1]) if status else 0
            return rowcount > 0


# Global instance
_query_service: Optional[QueryService] = None


def get_query_service() -> QueryService:
    """Get global query service instance (singleton)."""
    global _query_service
    if _query_service is None:
        _query_service = QueryService()
    return _query_service
