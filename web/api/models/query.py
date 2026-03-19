"""
Pydantic models for query/conversation handling.
"""

from typing import Optional, Dict, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryRequest(BaseModel):
    """
    Request model for querying a paper.
    User asks questions about the paper in a session.
    """
    query: str = Field(
        min_length=1,
        max_length=2000,
        description="User's question or query about the paper"
    )
    highlighted_text: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Optional text highlighted by user for context"
    )
    page_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional page number reference"
    )
    model: Optional[Literal['sonnet', 'haiku', 'gemini-flash', 'gemini-pro']] = Field(
        default='sonnet',
        description="Model to use: 'sonnet'/'haiku' (Claude), 'gemini-flash'/'gemini-pro' (Google)"
    )
    use_thinking: bool = Field(
        default=False,
        description="Enable extended thinking mode (only works with 'sonnet' or 'gemini-pro')"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and clean query text."""
        query = v.strip()
        if not query:
            raise ValueError("Query cannot be empty")
        return query

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What is the time complexity of multi-head attention?",
                "highlighted_text": "Multi-head attention allows the model to jointly attend...",
                "page_number": 5,
                "model": "sonnet",
                "use_thinking": False
            }
        }
    )


class QueryResponse(BaseModel):
    """
    Response model for query results.
    Contains Claude's response and metadata.
    """
    exchange_id: int = Field(description="Exchange ID for this Q&A pair")
    response: str = Field(description="Claude's response to the query")
    model_used: str = Field(description="Model used for response")
    use_thinking: bool = Field(
        default=False,
        description="Whether thinking mode was used"
    )
    usage: Dict[str, Any] = Field(
        description="Token usage statistics",
        default_factory=dict
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exchange_id": 3,
                "response": "The time complexity of multi-head attention is O(n²d)...",
                "model_used": "claude-sonnet-4-6",
                "use_thinking": False,
                "usage": {
                    "input_tokens": 1234,
                    "output_tokens": 156,
                    "thinking_tokens": 0
                }
            }
        }
    )


class FlagRequest(BaseModel):
    """
    Request model for flagging an exchange.
    Users can flag important exchanges for later review.
    """
    exchange_id: int = Field(ge=1, description="Exchange ID to flag")
    note: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional note about why this was flagged"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exchange_id": 3,
                "note": "Important insight about attention mechanism"
            }
        }
    )


class FlagResponse(BaseModel):
    """
    Response model for flag operations.
    """
    success: bool = Field(description="Whether flag operation succeeded")
    message: str = Field(description="Status message")
    flag_id: Optional[int] = Field(default=None, description="Flag ID if created")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Exchange flagged successfully",
                "flag_id": 42
            }
        }
    )


class Highlight(BaseModel):
    """
    Model for a text highlight.
    """
    id: int = Field(description="Highlight ID")
    text: str = Field(description="Highlighted text")
    page_number: Optional[int] = Field(default=None, description="Page number")
    exchange_id: Optional[int] = Field(default=None, description="Associated exchange")
    created_at: str = Field(description="Creation timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 5,
                "text": "The Transformer uses multi-head attention...",
                "page_number": 3,
                "exchange_id": 2,
                "created_at": "2025-11-17T10:35:00Z"
            }
        }
    )


class HighlightList(BaseModel):
    """
    Response model for listing highlights.
    """
    highlights: list[Highlight] = Field(description="List of highlights")
    total: int = Field(description="Total number of highlights")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "highlights": [
                    {
                        "id": 1,
                        "text": "Key finding...",
                        "page_number": 5,
                        "created_at": "2025-11-17T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }
    )


class MessageEvaluationRequest(BaseModel):
    """
    Request model for evaluating a message (thumbs up/down).
    Users can provide feedback on AI responses.
    """
    rating: Literal['positive', 'negative'] = Field(
        description="User rating: 'positive' (thumbs up) or 'negative' (thumbs down)"
    )
    # Reason flags (only for negative ratings)
    reason_inaccurate: bool = Field(
        default=False,
        description="Response was inaccurate"
    )
    reason_unhelpful: bool = Field(
        default=False,
        description="Response was unhelpful"
    )
    reason_off_topic: bool = Field(
        default=False,
        description="Response was off-topic"
    )
    reason_other: bool = Field(
        default=False,
        description="Other issue"
    )
    feedback_text: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional detailed feedback text"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating": "negative",
                "reason_inaccurate": True,
                "reason_unhelpful": False,
                "reason_off_topic": False,
                "reason_other": False,
                "feedback_text": "The response cited a paper that doesn't exist"
            }
        }
    )


class MessageEvaluationResponse(BaseModel):
    """
    Response model for evaluation operations.
    """
    success: bool = Field(description="Whether evaluation was saved successfully")
    message: str = Field(description="Status message")
    evaluation_id: Optional[int] = Field(
        default=None,
        description="Evaluation ID if created/updated"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Evaluation saved",
                "evaluation_id": 15
            }
        }
    )
