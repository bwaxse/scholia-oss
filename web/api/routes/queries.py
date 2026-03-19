"""
FastAPI routes for querying papers with Claude.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Body, Depends

from .auth import require_active
from ..models import (
    QueryRequest,
    QueryResponse,
    FlagResponse,
    Highlight,
    HighlightList,
    MessageEvaluationRequest,
    MessageEvaluationResponse,
)
from ...services import get_query_service
from ...core.database import get_db_manager


router = APIRouter(prefix="/sessions", tags=["queries"])


@router.post("/{session_id}/query", response_model=QueryResponse)
async def query_paper(
    session_id: str,
    request: QueryRequest,
    user: Dict[str, Any] = Depends(require_active),
):
    """
    Ask a question about the paper.

    **Process:**
    - Checks user has credits for the model
    - Retrieves full paper text and conversation history
    - Sends question to Claude with context
    - Stores both question and answer in conversation history
    - Deducts credits on success
    - Returns Claude's response with usage stats

    **Args:**
    - session_id: Session identifier
    - request: Query request with question and optional context
    - user: Authenticated user (via require_active)

    **Returns:**
    - QueryResponse with exchange_id, response text, model used, and usage stats

    **Raises:**
    - 402: If insufficient credits for model
    - 403: If model restricted by tier
    - 404: If session not found
    - 500: If query processing fails

    **Example:**
    ```json
    {
      "query": "What is the main contribution of this paper?",
      "model": "sonnet"
    }
    ```
    """
    try:
        service = get_query_service()
        response = await service.query_paper(session_id, request)
        response_dict = response.dict()
        response_dict["credits_used"] = 0
        response_dict["remaining_balance"] = None
        return response_dict
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process query: {str(e)}")


@router.post("/{session_id}/exchanges/{exchange_id}/flag", response_model=FlagResponse)
async def flag_exchange(
    session_id: str,
    exchange_id: int,
    note: Optional[str] = Body(None, embed=True)
):
    """
    Flag an exchange for later review.

    **Purpose:**
    - Mark important or interesting exchanges
    - Add optional note explaining why flagged
    - Use for building insights, export, or review

    **Args:**
    - session_id: Session identifier
    - exchange_id: Exchange ID to flag
    - note: Optional note about why this exchange is important

    **Returns:**
    - FlagResponse with success status and flag_id

    **Raises:**
    - 404: If session or exchange not found

    **Example:**
    ```json
    {
      "note": "Key insight about methodology"
    }
    ```
    """
    try:
        service = get_query_service()
        response = await service.flag_exchange(session_id, exchange_id, note)
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to flag exchange: {str(e)}"
        )


@router.delete("/{session_id}/exchanges/{exchange_id}/flag", response_model=FlagResponse)
async def unflag_exchange(
    session_id: str,
    exchange_id: int
):
    """
    Remove flag from an exchange.

    **Args:**
    - session_id: Session identifier
    - exchange_id: Exchange ID to unflag

    **Returns:**
    - FlagResponse with success status

    **Note:**
    - Returns success=false if exchange was not flagged
    """
    try:
        service = get_query_service()
        response = await service.unflag_exchange(session_id, exchange_id)
        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unflag exchange: {str(e)}"
        )


@router.post("/{session_id}/exchanges/{exchange_id}/evaluate", response_model=MessageEvaluationResponse)
async def evaluate_message(
    session_id: str,
    exchange_id: int,
    request: MessageEvaluationRequest
):
    """
    Evaluate an assistant message with thumbs up/down feedback.

    **Purpose:**
    - Collect user feedback on AI response quality
    - Track model performance for analytics
    - Identify problematic responses for improvement

    **Args:**
    - session_id: Session identifier
    - exchange_id: Exchange ID to evaluate
    - request: Evaluation details (rating, reasons, optional feedback text)

    **Returns:**
    - MessageEvaluationResponse with success status and evaluation_id

    **Raises:**
    - 404: If exchange not found
    - 500: If evaluation save fails

    **Note:**
    - Users can update their evaluation (UPSERT pattern)
    - Reason flags are primarily for negative ratings
    """
    try:
        service = get_query_service()
        response = await service.evaluate_message(
            session_id=session_id,
            exchange_id=exchange_id,
            rating=request.rating,
            reason_inaccurate=request.reason_inaccurate,
            reason_unhelpful=request.reason_unhelpful,
            reason_off_topic=request.reason_off_topic,
            reason_other=request.reason_other,
            feedback_text=request.feedback_text
        )
        return MessageEvaluationResponse(**response)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save evaluation: {str(e)}"
        )


@router.get("/{session_id}/exchanges/{exchange_id}/evaluation")
async def get_message_evaluation(
    session_id: str,
    exchange_id: int
):
    """
    Get existing evaluation for a message.

    **Purpose:**
    - Retrieve user's previous feedback on a response
    - Display evaluation state in UI

    **Args:**
    - session_id: Session identifier
    - exchange_id: Exchange ID

    **Returns:**
    - Evaluation object if exists, empty dict otherwise

    **Raises:**
    - 500: If retrieval fails
    """
    try:
        service = get_query_service()
        evaluation = await service.get_message_evaluation(session_id, exchange_id)
        return evaluation or {}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation: {str(e)}"
        )


@router.delete("/{session_id}/exchanges/{exchange_id}/evaluation", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message_evaluation(
    session_id: str,
    exchange_id: int
):
    """
    Delete a message evaluation (toggle off rating).

    **Purpose:**
    - Allow users to remove their thumbs up/down rating
    - Called when user clicks the same rating button again

    **Args:**
    - session_id: Session identifier
    - exchange_id: Exchange ID

    **Returns:**
    - 204 No Content on success
    - 404 if evaluation not found

    **Raises:**
    - 500: If deletion fails
    """
    try:
        service = get_query_service()
        deleted = await service.delete_message_evaluation(session_id, exchange_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evaluation not found for exchange {exchange_id}"
            )

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete evaluation: {str(e)}"
        )


@router.delete("/{session_id}/exchanges/{exchange_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exchange(
    session_id: str,
    exchange_id: int
):
    """
    Delete a Q&A exchange from the conversation.

    **Purpose:**
    - Remove unwanted exchanges from conversation history
    - Clean up conversation before exporting insights
    - Delete exchanges with errors or irrelevant content

    **Args:**
    - session_id: Session identifier
    - exchange_id: Exchange ID to delete

    **Returns:**
    - 204 No Content on success

    **Raises:**
    - 404: If session or exchange not found

    **Note:**
    - Deletes both user question and assistant response
    - Also removes any associated flags
    """
    try:
        service = get_query_service()
        deleted = await service.delete_exchange(session_id, exchange_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exchange {exchange_id} not found in session {session_id}"
            )

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete exchange: {str(e)}"
        )


@router.get("/{session_id}/highlights", response_model=HighlightList)
async def get_highlights(session_id: str):
    """
    Get all highlights for a session.

    **Returns:**
    - HighlightList with all highlights, sorted by creation time (newest first)

    **Use case:**
    - Review important passages
    - Build insights from highlighted text
    - Export annotations
    """
    try:
        service = get_query_service()
        highlights = await service.get_highlights(session_id)
        return highlights

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get highlights: {str(e)}"
        )


@router.post("/{session_id}/highlights", response_model=Highlight, status_code=status.HTTP_201_CREATED)
async def add_highlight(
    session_id: str,
    text: str = Body(..., min_length=1, max_length=5000, embed=True),
    page_number: Optional[int] = Body(None, embed=True),
    exchange_id: Optional[int] = Body(None, embed=True)
):
    """
    Add a text highlight to the session.

    **Purpose:**
    - Mark important passages for later reference
    - Optionally associate with a specific page or exchange
    - Build collection of key quotes

    **Args:**
    - session_id: Session identifier
    - text: The highlighted text (required)
    - page_number: Optional page number where text appears
    - exchange_id: Optional exchange ID if highlight relates to a Q&A

    **Returns:**
    - Highlight with ID and timestamp

    **Raises:**
    - 404: If session not found
    - 400: If text is empty or too long

    **Example:**
    ```json
    {
      "text": "Our method achieves state-of-the-art results on benchmark X",
      "page_number": 5,
      "exchange_id": 3
    }
    ```
    """
    try:
        service = get_query_service()
        highlight = await service.add_highlight(
            session_id=session_id,
            text=text,
            page_number=page_number,
            exchange_id=exchange_id
        )
        return highlight

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add highlight: {str(e)}"
        )


@router.delete("/{session_id}/highlights/{highlight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_highlight(
    session_id: str,
    highlight_id: int
):
    """
    Delete a highlight.

    **Args:**
    - session_id: Session identifier
    - highlight_id: Highlight ID to delete

    **Returns:**
    - 204 No Content on success

    **Raises:**
    - 404: If highlight not found
    """
    try:
        service = get_query_service()
        deleted = await service.delete_highlight(session_id, highlight_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Highlight {highlight_id} not found in session {session_id}"
            )

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete highlight: {str(e)}"
        )
