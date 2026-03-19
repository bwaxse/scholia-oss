"""
Usage tracking service for token consumption and user events.
Logs AI API calls and user activities to database for credit/billing purposes.
"""

import json
import logging
from typing import Any, Dict, Optional

from ..core.database import get_db_manager

logger = logging.getLogger(__name__)


class UsageTracker:
    """
    Tracks AI token usage and user events for billing/analytics.

    Supports two types of tracking:
    - token_usage: Per-API-call token consumption with model details
    - user_events: User activities like paper uploads, questions asked
    """

    def __init__(self, db_manager=None):
        """
        Initialize usage tracker.

        Args:
            db_manager: Database manager (optional, uses global if not provided)
        """
        self.db = db_manager or get_db_manager()

    async def _resolve_user_id(self, session_id: Optional[str], user_id: Optional[str]) -> Optional[str]:
        """
        Resolve user_id from session_id or return provided user_id.

        Args:
            session_id: Session ID to look up user from
            user_id: Direct user ID (takes precedence if provided)

        Returns:
            User ID or None if not resolvable
        """
        if user_id:
            return user_id

        if not session_id:
            logger.warning("Cannot resolve user_id: neither session_id nor user_id provided")
            return None

        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT user_id FROM sessions WHERE id = $1",
                session_id
            )
            if row:
                return row['user_id']

            logger.warning(f"Could not find user_id for session: {session_id}")
            return None

    def _detect_provider(self, model: str) -> str:
        """
        Detect provider from model name.

        Args:
            model: Model name string

        Returns:
            'claude' or 'gemini'
        """
        if 'gemini' in model.lower():
            return 'gemini'
        return 'claude'

    async def log_token_usage(
        self,
        operation_type: str,
        provider: str,
        usage_stats: Dict[str, Any],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        exchange_id: Optional[int] = None,
    ) -> Optional[int]:
        """
        Log AI API token usage to database.

        Args:
            operation_type: Type of operation ('initial_analysis', 'query', 'extract_insights',
                           'notion_parse_context', 'notion_generate_relevance', 'notion_generate_content')
            provider: AI provider ('claude' or 'gemini')
            usage_stats: Dict with token counts from AI client
            session_id: Session ID (used to look up user_id if user_id not provided)
            user_id: User ID (takes precedence over session_id lookup)
            exchange_id: Exchange ID (for queries only)

        Returns:
            ID of inserted record, or None if failed
        """
        resolved_user_id = await self._resolve_user_id(session_id, user_id)
        if not resolved_user_id:
            logger.error(f"Cannot log token usage: no user_id resolvable for operation {operation_type}")
            return None

        # Extract fields from usage_stats (handle both Claude and Gemini formats)
        model = usage_stats.get('model', 'unknown')
        use_thinking = usage_stats.get('use_thinking', False)
        input_tokens = usage_stats.get('input_tokens', 0)
        output_tokens = usage_stats.get('output_tokens', 0)
        thinking_tokens = usage_stats.get('thinking_tokens', 0)
        cache_creation_tokens = usage_stats.get('cache_creation_tokens', 0)
        cache_read_tokens = usage_stats.get('cache_read_tokens', 0)
        cached_tokens = usage_stats.get('cached_tokens', 0)  # Gemini

        try:
            async with self.db.get_connection() as conn:
                result = await conn.fetchrow(
                    """
                    INSERT INTO token_usage (
                        user_id, session_id, exchange_id, operation_type, provider, model,
                        use_thinking, input_tokens, output_tokens, thinking_tokens,
                        cache_creation_tokens, cache_read_tokens, cached_tokens
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    RETURNING id
                    """,
                    resolved_user_id, session_id, exchange_id, operation_type, provider, model,
                    use_thinking, input_tokens, output_tokens, thinking_tokens,
                    cache_creation_tokens, cache_read_tokens, cached_tokens
                )

                logger.debug(
                    f"Logged token usage: {operation_type} by user {resolved_user_id}, "
                    f"in={input_tokens}, out={output_tokens}, thinking={thinking_tokens}"
                )
                return result['id'] if result else None

        except Exception as e:
            logger.error(f"Failed to log token usage: {e}")
            return None

    async def log_user_event(
        self,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[int]:
        """
        Log user event to database.

        Args:
            event_type: Type of event ('paper_upload', 'question_asked',
                       'insights_extracted', 'notion_explored')
            metadata: Additional event data (stored as JSONB)
            session_id: Session ID (used to look up user_id if user_id not provided)
            user_id: User ID (takes precedence over session_id lookup)

        Returns:
            ID of inserted record, or None if failed
        """
        resolved_user_id = await self._resolve_user_id(session_id, user_id)
        if not resolved_user_id:
            logger.error(f"Cannot log user event: no user_id resolvable for event {event_type}")
            return None

        # Convert metadata to JSON string for JSONB column
        metadata_json = json.dumps(metadata) if metadata else None

        try:
            async with self.db.get_connection() as conn:
                result = await conn.fetchrow(
                    """
                    INSERT INTO user_events (user_id, session_id, event_type, metadata)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    """,
                    resolved_user_id, session_id, event_type, metadata_json
                )

                logger.debug(f"Logged user event: {event_type} by user {resolved_user_id}")
                return result['id'] if result else None

        except Exception as e:
            logger.error(f"Failed to log user event: {e}")
            return None


# Singleton instance
_usage_tracker: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """
    Get global UsageTracker instance (singleton pattern).

    Returns:
        UsageTracker instance
    """
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker
