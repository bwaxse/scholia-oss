"""
Notion export service for Scholia.
Generates relevance statements and formats content for Notion Literature Reviews.
"""

import json
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .notion_client import NotionClient, get_notion_client
from ..core.claude import get_claude_client
from ..core.database import get_db_manager
from .usage_tracker import get_usage_tracker

logger = logging.getLogger(__name__)


# Voice samples for relevance generation (from bjw-voice-modeling skill)
RELEVANCE_VOICE_GUIDE = """
VOICE CHARACTERISTICS TO MATCH:
- Technical precision with accessibility: Use domain terminology correctly but explain clearly
- Substantive without excess: Direct and concise, no unnecessary preamble
- Appropriately humble: Acknowledge limitations, offer alternatives vs overconfident claims
- Pedagogical: Explain WHY things matter, not just WHAT they are
- Collaborative tone: Points out considerations without being pedantic
- Natural imperfections: Occasional fragments or conversational constructions that feel authentic

USAGE GUIDELINES - When drafting relevance statements:
1. Lead with substance: Avoid long preambles. Get to the point quickly but naturally.
2. Use specifics: Concrete examples are better than abstract descriptions.
3. Acknowledge uncertainty: Use "though", "but", "however" when appropriate for caveats.
4. Explain implications: Don't just present findings - interpret what they mean for THIS project.
5. Stay collaborative: Frame connections constructively.
6. Allow natural imperfections: Conversational constructions feel authentic.

EXAMPLES OF BENNETT'S CONNECTING STYLE:
"This paper's phecode methodology aligns with our need for phenotype classification, though the reliance on billing codes means we'll need to validate against clinical notes."

"The autoencoder architecture here could work for our EHR embedding, but their batch size assumptions won't hold with our sparse data."

"Their approach to handling missing data is cleaner than what we've tried, though it assumes MCAR which we know isn't true in our dataset."
"""


class NotionExporter:
    """
    Exports session insights to Notion with project-specific relevance framing.

    Uses Claude to:
    - Generate relevance statements connecting papers to project goals (Haiku)
    - Format full export content for Notion Literature Reviews (Sonnet)
    """

    def __init__(
        self,
        notion_client: Optional[NotionClient] = None,
        claude_client=None,
        gemini_client=None
    ):
        """
        Initialize Notion exporter.

        Args:
            notion_client: Optional NotionClient instance
            claude_client: Optional ClaudeClient instance
            gemini_client: Optional GeminiClient instance
        """
        self.notion = notion_client or get_notion_client()
        self.claude = claude_client or get_claude_client()
        # Import here to avoid circular dependency
        from ..core.gemini import get_gemini_client
        self.gemini = gemini_client or get_gemini_client()

    async def get_project_context(
        self,
        page_id: str,
        user_id: str,
        force_refresh: bool = False
    ) -> Dict:
        """
        Fetch and parse project context. Uses database cache unless force_refresh.

        Args:
            page_id: Notion page ID
            user_id: User ID for per-user caching
            force_refresh: If True, bypass cache and re-fetch

        Returns:
            {
                "title": "EHR Autoencoder Project",
                "hypothesis": "Cross-modal embedding via autoencoders...",
                "themes": ["Autoencoder Use in Biology", "EHR GPT"],
                "raw_content": "..."
            }

        Raises:
            ValueError: If not authenticated with Notion
        """
        db = get_db_manager()

        # Check cache first (unless force_refresh)
        if not force_refresh:
            async with db.get_connection() as conn:
                row = await conn.fetchrow(
                    "SELECT title, hypothesis, themes, raw_content, fetched_at "
                    "FROM notion_project_cache WHERE user_id = $1 AND page_id = $2",
                    user_id,
                    page_id
                )

                if row:
                    # Check if cache is recent (less than 7 days old)
                    fetched_at = row['fetched_at']
                    if datetime.now(fetched_at.tzinfo) - fetched_at < timedelta(days=7):
                        logger.info(f"Using cached context for page {page_id} (user {user_id})")
                        return {
                            "title": row['title'],
                            "hypothesis": row['hypothesis'],
                            "themes": json.loads(row['themes']) if row['themes'] else [],
                            "raw_content": row['raw_content'],
                            "fetched_at": row['fetched_at'].isoformat()
                        }

        # Fetch fresh content from Notion
        logger.info(f"Fetching fresh context for page {page_id} (user {user_id})")
        raw_content = await self.notion.fetch_page_content(page_id)

        # Parse context using Claude
        context = await self._parse_project_context(page_id, raw_content, user_id)

        # Cache the result
        async with db.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO notion_project_cache (user_id, page_id, title, hypothesis, themes, raw_content, fetched_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT(user_id, page_id) DO UPDATE SET
                    title = excluded.title,
                    hypothesis = excluded.hypothesis,
                    themes = excluded.themes,
                    raw_content = excluded.raw_content,
                    fetched_at = NOW()
                """,
                user_id,
                page_id,
                context["title"],
                context["hypothesis"],
                json.dumps(context["themes"]),
                raw_content
            )

            # Get the fetched_at timestamp we just inserted
            fetched_at = await conn.fetchval(
                "SELECT fetched_at FROM notion_project_cache WHERE user_id = $1 AND page_id = $2",
                user_id,
                page_id
            )
            if fetched_at:
                context["fetched_at"] = fetched_at.isoformat()

        return context

    async def _parse_project_context(self, page_id: str, raw_content: str, user_id: str) -> Dict:
        """
        Parse project context from page content using Claude.

        Args:
            page_id: Notion page ID
            raw_content: Raw page content as text
            user_id: User ID for tracking

        Returns:
            Parsed context dict
        """
        # Get page title from Notion API
        page = await self.notion.notion.pages.retrieve(page_id=page_id)
        title = self.notion._extract_title(page) or "Untitled Project"

        # Extract hypothesis and themes from content
        prompt = f"""Analyze this Notion project page and extract key information.

PAGE CONTENT:
{raw_content[:4000]}  # Limit to first 4000 chars

TASK:
1. Find the project hypothesis or research question (look for "Hypothesis", "Research Question", "Goal" sections)
2. Find Literature Review themes (look under "Literature Review" heading for sub-headings or categories)

Return JSON:
{{
    "hypothesis": "The main research hypothesis or question (1-2 sentences)",
    "themes": ["Theme 1", "Theme 2", ...]  // Existing theme headings found
}}

If no hypothesis found, use empty string.
If no themes found, return empty array.
"""

        response_text, usage_stats = await self.claude.extract_structured(
            extraction_prompt=prompt,
            pdf_path="",
            conversation_context="",
            max_tokens=500
        )

        # Log usage tracking
        usage_tracker = get_usage_tracker()
        await usage_tracker.log_token_usage(
            operation_type='notion_parse_context',
            provider='claude',
            usage_stats=usage_stats,
            user_id=user_id
        )

        # Parse response
        try:
            import json
            match = re.search(r'\{[\s\S]*\}', response_text)
            if match:
                parsed = json.loads(match.group())
            else:
                parsed = json.loads(response_text)

            return {
                "title": title,
                "hypothesis": parsed.get("hypothesis", ""),
                "themes": parsed.get("themes", []),
                "raw_content": raw_content
            }
        except Exception as e:
            logger.error(f"Failed to parse project context: {e}")
            return {
                "title": title,
                "hypothesis": "",
                "themes": [],
                "raw_content": raw_content
            }

    async def generate_relevance(
        self,
        session_insights: Dict,
        project_context: Dict,
        user_id: str,
        model: str = "gemini-flash"
    ) -> Dict:
        """
        Generate proposed relevance statement + theme suggestion.

        Uses Claude or Gemini with Bennett's voice from bjw-voice-modeling skill.

        Args:
            session_insights: Session insights from extract_insights()
            project_context: Project context from get_project_context()
            user_id: User ID for tracking
            model: Model to use ("haiku", "sonnet", "gemini-flash", "gemini-pro")

        Returns:
            {
                "suggested_theme": "Existing Theme" or "NEW: Proposed Theme",
                "relevance_statement": "2-3 sentence relevance in Bennett's voice"
            }
        """
        # Extract key info from insights
        bibliographic = session_insights.get("bibliographic", {})
        paper_title = bibliographic.get("title", "Unknown paper")
        summary = session_insights.get("summary", "")
        learnings = session_insights.get("learnings", [])[:3]  # Top 3
        assessment = session_insights.get("assessment", {})

        prompt = f"""You are helping a researcher integrate a newly analyzed paper into their ongoing research project. Your task is to categorize the paper under an appropriate theme and explain its relevance to the project hypothesis.

Here is the project context:

<project_title>
{project_context['title']}
</project_title>

<project_hypothesis>
{project_context['hypothesis'] or 'Not specified'}
</project_hypothesis>

<existing_themes>
{', '.join(project_context['themes']) if project_context['themes'] else 'None yet'}
</existing_themes>

Here are the insights from the paper that was just analyzed:

<paper_title>
{paper_title}
</paper_title>

<paper_summary>
{summary}
</paper_summary>

<key_learnings>
{chr(10).join(f"- {l}" for l in learnings)}
</key_learnings>

Here is guidance on the voice and style to use when writing the relevance statement:

<voice_guide>
{RELEVANCE_VOICE_GUIDE}
</voice_guide>

Your task has two parts:

**Part 1: Theme Categorization**
Review the existing literature review themes in the project context. Determine whether this paper fits under one of the existing themes, or whether it represents a new thematic area. If suggesting a new theme, prefix it with "NEW: " followed by a concise, descriptive theme name (3-6 words).

**Part 2: Relevance Statement**
Write a 2-3 sentence statement explaining how this paper connects to the project hypothesis. The statement should:
- Focus on WHY this paper matters for the project, not just summarizing what the paper did
- Use technical precision while remaining accessible
- Be substantive and direct without preamble phrases like "This paper is relevant because..."
- Acknowledge limitations, caveats, or tensions where appropriate using words like "though," "but," "however"
- Sound like a researcher thinking aloud—thoughtful and analytical, not promotional
- Follow the voice guidance provided above

Before providing your final answer, use the scratchpad to think through:
1. How the paper's key learnings relate to the project hypothesis
2. Whether it fits existing themes or needs a new one
3. What makes this paper specifically valuable (or limited) for this project

<scratchpad>
[Think through the theme fit and relevance here]
</scratchpad>

Provide your response as valid JSON with exactly this structure:
{{
    "suggested_theme": "Existing Theme Name" or "NEW: Proposed Theme Name",
    "relevance_statement": "2-3 sentences in Bennett's voice"
}}
"""

        # Call appropriate model to generate relevance
        if model.startswith('gemini'):
            if not self.gemini:
                raise ValueError("Gemini is not configured. Please set GOOGLE_API_KEY.")
            provider = 'gemini'
            response_text, usage_stats = await self.gemini.extract_structured(
                extraction_prompt=prompt,
                pdf_path="",
                conversation_context="",
                max_tokens=500  # Increased for Gemini to complete JSON
            )
        else:
            provider = 'claude'
            response_text, usage_stats = await self.claude.extract_structured(
                extraction_prompt=prompt,
                pdf_path="",
                conversation_context="",
                max_tokens=300
            )

        # Log usage tracking
        usage_tracker = get_usage_tracker()
        await usage_tracker.log_token_usage(
            operation_type='notion_generate_relevance',
            provider=provider,
            usage_stats=usage_stats,
            user_id=user_id
        )
        await usage_tracker.log_user_event(
            event_type='notion_explored',
            metadata={'action': 'relevance'},
            user_id=user_id
        )

        # Parse response
        try:
            match = re.search(r'\{[\s\S]*\}', response_text)
            if match:
                result = json.loads(match.group())
            else:
                result = json.loads(response_text)

            return {
                "suggested_theme": result.get("suggested_theme", "NEW: Related Work"),
                "relevance_statement": result.get("relevance_statement", "")
            }
        except Exception as e:
            logger.error(f"Failed to parse relevance response: {e}")
            return {
                "suggested_theme": "NEW: Related Work",
                "relevance_statement": "This paper relates to the project goals.",
                "error": str(e)
            }

    async def generate_export_content(
        self,
        session_insights: Dict,
        project_context: Dict,
        confirmed_theme: str,
        confirmed_relevance: str,
        user_id: str,
        include_session_notes: bool = True,
        model: str = "gemini-flash"
    ) -> str:
        """
        Generate full formatted content for Notion export.

        Uses Claude Sonnet or Gemini Pro for quality.

        Args:
            session_insights: Session insights from extract_insights()
            project_context: Project context
            confirmed_theme: User-confirmed theme
            confirmed_relevance: User-confirmed relevance statement
            user_id: User ID for tracking
            include_session_notes: Whether to include collapsed session notes
            model: Model to use ("sonnet", "haiku", "gemini-pro", "gemini-flash")

        Returns:
            Formatted content as plain text (will be converted to Notion blocks)
        """
        bibliographic = session_insights.get("bibliographic", {})
        paper_title = bibliographic.get("title", "Unknown paper")
        authors = bibliographic.get("authors", "Unknown authors")
        year = bibliographic.get("year", "")

        # Extract last name for citation
        if authors and "," in authors:
            last_name = authors.split(",")[0].strip()
        elif authors:
            last_name = authors.split()[0].strip()
        else:
            last_name = "Unknown"

        prompt = f"""You are formatting a paper analysis for a researcher's Notion literature review. Your goal is to create an entry that frames the paper's findings specifically in terms of the researcher's project, not as a generic summary.

Here is the project context:
<project_title>
{project_context['title']}
</project_title>

<project_hypothesis>
{project_context['hypothesis'] or 'Not specified'}
</project_hypothesis>

Here is the confirmed framing for this paper:
<confirmed_framing>
Theme: {confirmed_theme}
Relevance: {confirmed_relevance}
</confirmed_framing>

Here is the paper information:
<paper_title>
{paper_title}
</paper_title>

<paper_authors>
{authors}
</paper_authors>

<paper_year>
{year}
</paper_year>

Here are the session insights collected about this paper:
<session_insights>
{json.dumps(session_insights, indent=2)}
</session_insights>

<voice_guide>
{RELEVANCE_VOICE_GUIDE}
</voice_guide>

Should session notes be included:
{{'**Session notes**:' if include_session_notes else ''}}
{{'[condensed learnings from session]' if include_session_notes else ''}}

Your task is to generate a literature review entry with the following components:

**Key insights** (2-4 bullet points): Frame the paper's findings in terms of how they specifically matter for THIS project and its hypothesis. Do not write generic paper summaries. Each insight should connect to the project's goals and explain implications.

**Open questions** (1-3 bullet points): Identify questions this paper raises specifically for THIS project's hypothesis. These should be substantive questions that advance the research agenda.

**Session notes** (only if INCLUDE_SESSION_NOTES is true): Condense what the reader learned and engaged with during the session. Focus on key takeaways and realizations, not a play-by-play.

Use the voice characteristics from the voice_guide above throughout your writing:
- Technical precision with accessibility
- Substantive without excess
- Explain implications ("so what"), not just facts
- Collaborative, engaged tone
- Direct and clear
- Allow natural imperfections for authenticity

Before writing your output, use a scratchpad to plan your approach:

<scratchpad>
- Review the project hypothesis and how this paper connects to it
- Identify 2-4 key findings from session insights that matter most for the project
- Frame each insight in terms of project implications
- Generate 1-3 open questions that advance the project's research agenda
- If including session notes, identify the core learnings to condense
- Ensure voice matches Bennett's characteristics
</scratchpad>

Now write your formatted output inside <output> tags. Use this exact structure:

### {last_name} et al., {year}
{paper_title}

**Relevance**: {confirmed_relevance}

**Key insights**:
- [First insight framed for this project]
- [Second insight framed for this project]
- [Additional insights as needed, 2-4 total]

**Open questions**:
- [First question for this project]
- [Additional questions as needed, 1-3 total]

[Only include the following section if INCLUDE_SESSION_NOTES is true:]
**Session notes**:
[Condensed learnings from the session]

Important formatting rules:
- Use plain text with markdown formatting only (**, -, ###)
- DO NOT include toggle syntax like ▶ or any Notion-specific formatting codes
- DO NOT include XML tags in your output
- Extract the last name of the first author from the paper info provided
- Keep bullets concise but substantive
- Ensure every insight and question connects back to the project context

Write your complete formatted entry now.
"""

        # Call appropriate model to generate export content
        if model.startswith('gemini'):
            if not self.gemini:
                raise ValueError("Gemini is not configured. Please set GOOGLE_API_KEY.")
            provider = 'gemini'
            response_text, usage_stats = await self.gemini.extract_structured(
                extraction_prompt=prompt,
                pdf_path="",
                conversation_context="",
                max_tokens=1000
            )
        else:
            provider = 'claude'
            response_text, usage_stats = await self.claude.extract_structured(
                extraction_prompt=prompt,
                pdf_path="",
                conversation_context="",
                max_tokens=1000
            )

        # Log usage tracking
        usage_tracker = get_usage_tracker()
        await usage_tracker.log_token_usage(
            operation_type='notion_generate_content',
            provider=provider,
            usage_stats=usage_stats,
            user_id=user_id
        )
        await usage_tracker.log_user_event(
            event_type='notion_explored',
            metadata={'action': 'export'},
            user_id=user_id
        )

        return response_text.strip()

    async def export_to_notion(
        self,
        page_id: str,
        theme: str,
        content: str,
        literature_review_heading: str = "Literature Review"
    ) -> str:
        """
        Write content to Notion under Literature Review > theme.

        Args:
            page_id: Notion page ID
            theme: Theme name (existing or "NEW: Theme Name")
            content: Formatted content from generate_export_content()
            literature_review_heading: Name of the Literature Review section

        Returns:
            URL of the updated page

        Raises:
            ValueError: If Literature Review heading not found
        """
        # Parse content into Notion blocks
        blocks = self._content_to_notion_blocks(content)

        # Find the Literature Review section
        page_blocks = await self.notion._get_all_blocks(page_id)

        # Log all top-level blocks for debugging
        logger.info(f"Found {len(page_blocks)} top-level blocks in page")
        for block in page_blocks[:10]:  # Log first 10 blocks
            block_type = block.get("type", "unknown")
            content = block.get(block_type, {})
            rich_text = content.get("rich_text", [])
            text = "".join(part.get("plain_text", "") for part in rich_text)[:50]
            logger.debug(f"Block: type={block_type}, text='{text}'")

        lit_review_block = self._find_heading_block(page_blocks, literature_review_heading)

        if not lit_review_block:
            raise ValueError(
                f"Could not find '{literature_review_heading}' heading in page. "
                "Please add this heading to your Notion page first."
            )

        # Ensure Literature Review is a toggle (toggle list or toggle heading)
        block_type = lit_review_block.get("type")
        content = lit_review_block.get(block_type, {})
        is_toggleable = content.get("is_toggleable", False)

        # Accept: toggle list OR toggle heading (heading_1/2/3 with is_toggleable=true)
        is_valid_toggle = (
            block_type == "toggle" or
            (block_type in ["heading_1", "heading_2", "heading_3"] and is_toggleable)
        )

        if not is_valid_toggle:
            rich_text = content.get("rich_text", [])
            found_text = "".join(part.get("plain_text", "") for part in rich_text)

            raise ValueError(
                f"Found '{found_text}' as a {block_type} (is_toggleable={is_toggleable}), but it must be a toggle block. "
                f"In Notion, right-click the '{literature_review_heading}' block and select 'Turn into toggle' or use a toggle heading."
            )

        # Handle new theme creation
        if theme.startswith("NEW:"):
            theme_name = theme[4:].strip()  # Remove "NEW: " prefix
            theme_block = await self._create_theme_heading(
                lit_review_block["id"],
                theme_name
            )
            target_block_id = theme_block["id"]
        else:
            # Find existing theme heading
            theme_block = self._find_heading_block(
                lit_review_block.get("children", []),
                theme
            )
            if not theme_block:
                # Theme doesn't exist, create it
                theme_block = await self._create_theme_heading(
                    lit_review_block["id"],
                    theme
                )
            target_block_id = theme_block["id"]

        # Append paper entry as children of the theme toggle
        url = await self.notion.append_to_page(
            page_id=page_id,
            blocks=blocks,
            after_block_id=target_block_id
        )

        return url

    async def _create_theme_heading(
        self,
        parent_block_id: str,
        theme_name: str
    ) -> Dict:
        """Create a new theme toggle block under Literature Review (styled as H2)."""
        toggle_block = {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": theme_name},
                    "annotations": {
                        "bold": True,
                        "color": "default"
                    }
                }],
                "color": "default",
                "children": []
            }
        }

        # Append toggle block
        response = await self.notion.notion.blocks.children.append(
            block_id=parent_block_id,
            children=[toggle_block]
        )

        return response["results"][0]

    def _find_heading_block(
        self,
        blocks: List[Dict],
        heading_text: str
    ) -> Optional[Dict]:
        """Find a heading or toggle block by text content."""
        for block in blocks:
            block_type = block.get("type", "")

            # Check headings and toggles
            if block_type in ["heading_1", "heading_2", "heading_3", "toggle"]:
                content = block.get(block_type, {})
                rich_text = content.get("rich_text", [])
                text = "".join(part.get("plain_text", "") for part in rich_text)

                if text.strip().lower() == heading_text.strip().lower():
                    return block

        return None

    def _content_to_notion_blocks(self, content: str) -> List[Dict]:
        """
        Convert plain text content to Notion blocks.

        Parses markdown-style formatting into Notion block structure.
        """
        blocks = []
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Heading (### Title)
            if line.startswith("###"):
                title_text = line[3:].strip()
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [{"type": "text", "text": {"content": title_text}}],
                        "children": []
                    }
                })

            # Bold label (**Label**:)
            elif line.startswith("**") and "**:" in line:
                # This is a label like "**Relevance**:" or "**Key insights**:"
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._parse_rich_text(line)
                    }
                })

            # Bullet point
            elif line.startswith("-"):
                bullet_text = line[1:].strip()
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": bullet_text}}]
                    }
                })

            # Regular paragraph
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    }
                })

            i += 1

        # Nest content under toggle (first block should be toggle)
        if blocks and blocks[0].get("type") == "toggle":
            toggle_block = blocks[0]
            toggle_block["toggle"]["children"] = blocks[1:]
            return [toggle_block]

        return blocks

    def _parse_rich_text(self, text: str) -> List[Dict]:
        """Parse markdown-style bold (**text**) into Notion rich text."""
        parts = []

        # Simple bold parsing
        pattern = r'\*\*(.*?)\*\*'
        last_end = 0

        for match in re.finditer(pattern, text):
            # Add text before bold
            if match.start() > last_end:
                parts.append({
                    "type": "text",
                    "text": {"content": text[last_end:match.start()]}
                })

            # Add bold text
            parts.append({
                "type": "text",
                "text": {"content": match.group(1)},
                "annotations": {"bold": True}
            })

            last_end = match.end()

        # Add remaining text
        if last_end < len(text):
            parts.append({
                "type": "text",
                "text": {"content": text[last_end:]}
            })

        return parts if parts else [{"type": "text", "text": {"content": text}}]


# Singleton instance
_notion_exporter: Optional[NotionExporter] = None


def get_notion_exporter(
    notion_client: Optional[NotionClient] = None,
    claude_client=None,
    gemini_client=None
) -> NotionExporter:
    """
    Get singleton NotionExporter instance.

    Args:
        notion_client: Optional NotionClient instance
        claude_client: Optional ClaudeClient instance
        gemini_client: Optional GeminiClient instance

    Returns:
        NotionExporter instance
    """
    global _notion_exporter

    if _notion_exporter is None:
        _notion_exporter = NotionExporter(
            notion_client=notion_client,
            claude_client=claude_client,
            gemini_client=gemini_client
        )

    return _notion_exporter
