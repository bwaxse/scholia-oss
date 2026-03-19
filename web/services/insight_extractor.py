"""
Insight extraction service for Scholia web backend.
Ports critical appraisal extraction from CLI to web service.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

from ..core.claude import get_claude_client
from ..core.database import get_db_manager
from ..core.prompts import EXTRACTION_PROMPT_TEMPLATE
from .usage_tracker import get_usage_tracker

logger = logging.getLogger(__name__)


class InsightExtractor:
    """
    Extracts and organizes insights from paper analysis sessions.

    Analyzes conversation history, flagged exchanges, and highlights to:
    - Identify strengths and weaknesses
    - Extract methodological insights
    - Organize findings thematically
    - Generate structured output for Zotero notes
    """

    def __init__(
        self,
        claude_client=None,
        gemini_client=None,
        database=None
    ):
        """
        Initialize insight extractor.

        Args:
            claude_client: Optional ClaudeClient instance
            gemini_client: Optional GeminiClient instance
            database: Optional Database instance
        """
        self.claude = claude_client or get_claude_client()
        # Import here to avoid circular dependency
        from ..core.gemini import get_gemini_client
        self.gemini = gemini_client or get_gemini_client()
        self.db = database or get_db_manager()

    def _format_initial_analysis_xml(self, initial_analysis: str) -> str:
        """Format initial analysis for XML block."""
        return initial_analysis.strip()

    def _format_conversation_history_xml(self, exchanges: List) -> str:
        """Format conversation for XML block (truncate to 10000 chars)."""
        conversation = []

        # Group exchanges by pairs (user, assistant)
        for i in range(0, len(exchanges) - 1, 2):
            if i + 1 < len(exchanges):
                user_msg = dict(exchanges[i])
                assistant_msg = dict(exchanges[i + 1])

                if user_msg["role"] == "user" and assistant_msg["role"] == "assistant":
                    conversation.append(
                        f"User: {user_msg['content']}\n"
                        f"Assistant: {assistant_msg['content'][:500]}..."
                    )

        full_conv = "\n\n".join(conversation)
        return full_conv[:10000]

    def _format_starred_exchanges_xml(self, all_exchanges: List, flagged: List) -> str:
        """Format flagged exchanges for XML block."""
        return self._format_flagged_exchanges(all_exchanges, flagged)

    def _format_highlights_xml(self, highlights: List) -> str:
        """Format highlights for XML block."""
        return self._format_highlights(highlights)

    async def extract_insights(
        self,
        session_id: str,
        model: str = "gemini-flash",
        use_thinking: bool = False
    ) -> Dict:
        """
        Extract and thematically organize insights from a session.

        Args:
            session_id: Session ID to extract insights from
            model: Model to use for extraction
            use_thinking: Enable thinking mode (works with sonnet/gemini models, not haiku)

        Returns:
            Dict containing:
            - summary: Bottom-line takeaway from the paper discussion
            - learnings: What the reader actually engaged with and learned
            - assessment: Strengths and limitations of the paper
            - open_questions: Unresolved questions to revisit

        Raises:
            ValueError: If session not found
        """
        # Get session data
        async with self.db.get_connection() as conn:
            # Get session
            session_row = await conn.fetchrow(
                "SELECT * FROM sessions WHERE id = $1",
                session_id
            )

            if not session_row:
                raise ValueError(f"Session not found: {session_id}")

            # Get all exchanges (conversation history) excluding initial analysis and deleted
            exchanges_data = await conn.fetch(
                """
                SELECT id, role, content, model, timestamp as created_at
                FROM conversations
                WHERE session_id = $1 AND exchange_id > 0 AND deleted_at IS NULL
                ORDER BY timestamp ASC
                """,
                session_id
            )

            # Get flagged exchanges (excluding deleted conversations)
            flagged_data = await conn.fetch(
                """
                SELECT c.id, c.role, c.content, f.note, f.created_at as flag_time
                FROM conversations c
                JOIN flags f ON c.exchange_id = f.exchange_id AND c.session_id = f.session_id
                WHERE c.session_id = $1 AND c.deleted_at IS NULL
                ORDER BY f.created_at ASC
                """,
                session_id
            )

            # Get highlights
            highlights_data = await conn.fetch(
                """
                SELECT text, page_number, exchange_id, created_at
                FROM highlights
                WHERE session_id = $1
                ORDER BY created_at DESC
                """,
                session_id
            )

            # Get initial analysis from conversations (exchange_id = 0, role = 'assistant')
            initial_analysis = await conn.fetchval(
                """
                SELECT content FROM conversations
                WHERE session_id = $1 AND exchange_id = 0 AND role = 'assistant' AND deleted_at IS NULL
                LIMIT 1
                """,
                session_id
            )
            initial_analysis = initial_analysis or ""

        # Format data sections for XML tags
        initial_analysis_xml = self._format_initial_analysis_xml(initial_analysis)
        conversation_xml = self._format_conversation_history_xml(exchanges_data)
        starred_xml = self._format_starred_exchanges_xml(exchanges_data, flagged_data)
        highlights_xml = self._format_highlights_xml(highlights_data)

        # Build extraction prompt from template
        # This ensures insights reflect what was actually discussed, not a fresh analysis
        extraction_prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            initial_analysis=initial_analysis_xml,
            conversation_history=conversation_xml,
            starred_exchanges=starred_xml,
            highlights=highlights_xml
        )

        # Call appropriate model to extract insights
        # Uses summary + conversation only (not full PDF) to ensure insights
        # reflect what was actually discussed in the session

        # Thinking only works with frontier models (sonnet, gemini-flash, gemini-pro) - not haiku
        actual_use_thinking = use_thinking
        if use_thinking and model not in ('sonnet', 'gemini-flash', 'gemini-pro'):
            actual_use_thinking = False
            logger.info(f"Thinking disabled for insights: only available with sonnet/gemini models, not {model}")

        if model.startswith('gemini'):
            if not self.gemini:
                raise ValueError("Gemini is not configured. Please set GOOGLE_API_KEY.")
            provider = 'gemini'
            response_text, usage = await self.gemini.extract_structured(
                extraction_prompt=extraction_prompt,
                pdf_path="",  # Don't send full PDF - use initial_analysis in prompt instead
                conversation_context="",  # Already included in extraction_prompt
                max_tokens=4000,  # Sufficient for complete JSON response
                use_thinking=actual_use_thinking
            )
        else:
            provider = 'claude'
            response_text, usage = await self.claude.extract_structured(
                extraction_prompt=extraction_prompt,
                pdf_path="",  # Don't send full PDF - use initial_analysis in prompt instead
                conversation_context="",  # Already included in extraction_prompt
                max_tokens=4000,  # Sufficient for complete JSON response
                use_thinking=actual_use_thinking
            )

        # Log usage tracking
        usage_tracker = get_usage_tracker()
        await usage_tracker.log_token_usage(
            operation_type='extract_insights',
            provider=provider,
            usage_stats=usage,
            session_id=session_id
        )

        # Parse JSON from response
        insights = self._parse_insights_json(response_text)

        # Add metadata
        insights["metadata"] = {
            "session_id": session_id,
            "filename": dict(session_row)["filename"],
            "extracted_at": datetime.now().isoformat(),
            "total_exchanges": len(exchanges_data) // 2,
            "flagged_count": len(flagged_data) // 2,  # Divide by 2 since each exchange has user + assistant messages
            "highlights_count": len(highlights_data),
            "model_used": model,
            "use_thinking": actual_use_thinking
        }

        # Add Zotero key if available
        if dict(session_row).get("zotero_key"):
            insights["metadata"]["zotero_key"] = dict(session_row)["zotero_key"]

        # Log user event
        await usage_tracker.log_user_event(
            event_type='insights_extracted',
            metadata={
                'total_exchanges': len(exchanges_data) // 2,
                'use_thinking': actual_use_thinking
            },
            session_id=session_id
        )

        return insights

    def _format_conversation(self, exchanges: List, initial_analysis: str = "") -> str:
        """Format exchanges as conversation summary.

        Note: initial_analysis parameter is kept for backwards compatibility
        but is no longer included here since it's already in INITIAL PAPER SUMMARY.
        """
        conversation = []

        # Group exchanges by pairs (user, assistant)
        # Only include actual user Q&A, not the initial analysis
        for i in range(0, len(exchanges) - 1, 2):
            if i + 1 < len(exchanges):
                user_msg = dict(exchanges[i])
                assistant_msg = dict(exchanges[i + 1])

                if user_msg["role"] == "user" and assistant_msg["role"] == "assistant":
                    conversation.append(
                        f"User: {user_msg['content']}\n"
                        f"Assistant: {assistant_msg['content'][:500]}..."  # Truncate long responses
                    )

        return "\n\n".join(conversation)

    def _format_flagged_exchanges(self, all_exchanges: List, flagged: List) -> str:
        """Format flagged exchanges with context."""
        if not flagged:
            return "(No flagged exchanges)"

        # Create exchange lookup by ID
        exchange_map = {dict(ex)["id"]: dict(ex) for ex in all_exchanges}

        flagged_text = []
        for flag in flagged:
            flag_dict = dict(flag)

            # Find the user question and assistant answer
            exchange_id = flag_dict["id"]

            # Find user and assistant messages around this exchange
            user_content = None
            assistant_content = None

            for i, ex in enumerate(all_exchanges):
                ex_dict = dict(ex)
                if ex_dict["id"] == exchange_id:
                    if ex_dict["role"] == "user":
                        user_content = ex_dict["content"]
                        # Get next message (assistant response)
                        if i + 1 < len(all_exchanges):
                            assistant_content = dict(all_exchanges[i + 1])["content"]
                    elif ex_dict["role"] == "assistant":
                        assistant_content = ex_dict["content"]
                        # Get previous message (user question)
                        if i > 0:
                            user_content = dict(all_exchanges[i - 1])["content"]

            note = f"\nNote: {flag_dict['note']}" if flag_dict.get("note") else ""
            flagged_text.append(
                f"[FLAGGED at {flag_dict['flag_time']}]{note}\n"
                f"User: {user_content or 'N/A'}\n"
                f"Assistant: {assistant_content or 'N/A'}"
            )

        return "\n\n".join(flagged_text)

    def _format_highlights(self, highlights: List) -> str:
        """Format highlights summary."""
        if not highlights:
            return "(No highlights)"

        highlight_texts = []
        for h in highlights[:20]:  # Limit to 20 most recent
            h_dict = dict(h)
            page = f" (page {h_dict['page_number']})" if h_dict.get("page_number") else ""
            highlight_texts.append(f"- {h_dict['text']}{page}")

        return "\n".join(highlight_texts)

    def _parse_insights_json(self, response_text: str) -> Dict:
        """Parse JSON from Claude's response."""
        try:
            # Look for JSON block in response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                insights = json.loads(json_match.group())
            else:
                insights = json.loads(response_text)

            return insights
        except (json.JSONDecodeError, AttributeError):
            # Fallback structure matching new lean format
            return {
                "extraction_error": "Failed to parse structured insights",
                "raw_response": response_text[:500],
                "summary": "",
                "learnings": [],
                "assessment": {"strengths": [], "limitations": []},
                "open_questions": []
            }

    @staticmethod
    def format_insights_html(insights: Dict) -> str:
        """Format session insights as HTML for both UI and Zotero."""
        metadata = insights.get("metadata", {})
        summary = insights.get("summary", "")
        learnings = insights.get("learnings", [])
        assessment = insights.get("assessment", {})
        open_questions = insights.get("open_questions", [])

        # Title line
        title = metadata.get("filename", "Unknown")
        html = f"<h2>Scholia Insights - {datetime.now().strftime('%Y-%m-%d')}</h2>\n"
        html += f"<p><strong>{title}</strong></p>\n"

        # Summary
        if summary:
            html += f"<h3>Summary</h3>\n<p>{summary}</p>\n"

        # What I Learned (only if there are learnings)
        if learnings and len(learnings) > 0:
            html += "<h3>What I Learned</h3>\n<ul>\n"
            for item in learnings:
                html += f"<li>{item}</li>\n"
            html += "</ul>\n"

        # Paper Assessment (strengths & limitations)
        has_assessment = (assessment.get("strengths") or assessment.get("limitations"))
        if has_assessment:
            html += "<h3>Paper Assessment</h3>\n"

            if assessment.get("strengths"):
                html += "<p><strong>Strengths:</strong></p>\n<ul>\n"
                for item in assessment["strengths"]:
                    html += f"<li>{item}</li>\n"
                html += "</ul>\n"

            if assessment.get("limitations"):
                html += "<p><strong>Limitations:</strong></p>\n<ul>\n"
                for item in assessment["limitations"]:
                    html += f"<li>{item}</li>\n"
                html += "</ul>\n"

        # Open Questions
        if open_questions and len(open_questions) > 0:
            html += "<h3>Open Questions</h3>\n<ul>\n"
            for item in open_questions:
                html += f"<li>{item}</li>\n"
            html += "</ul>\n"

        # Minimal footer
        html += f"<hr>\n<p><small>{metadata.get('total_exchanges', 0)} exchanges"
        if metadata.get('flagged_count', 0) > 0:
            html += f" | {metadata['flagged_count']} flagged"
        html += f" | {metadata.get('extracted_at', '')[:10]}</small></p>\n"

        return html

# Singleton instance
_insight_extractor: Optional[InsightExtractor] = None


def get_insight_extractor(
    claude_client=None,
    gemini_client=None,
    database=None
) -> InsightExtractor:
    """
    Get singleton InsightExtractor instance.

    Args:
        claude_client: Optional ClaudeClient instance
        gemini_client: Optional GeminiClient instance
        database: Optional Database instance

    Returns:
        InsightExtractor instance
    """
    global _insight_extractor

    if _insight_extractor is None:
        _insight_extractor = InsightExtractor(
            claude_client=claude_client,
            gemini_client=gemini_client,
            database=database
        )

    return _insight_extractor
