"""Chat endpoints — sync, async (start/poll/result), and feedback."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..app_config import get_state
from ..chart_suggest import suggest_chart
from ..core import Dependencies, logger
from ..db import (
    add_message,
    create_conversation,
    get_conversation,
    get_conversation_messages,
    increment_conversation_message_count,
    list_conversations,
    update_message_result,
)
from ..genie_client import (
    ask_genie,
    get_genie_result,
    poll_genie_status,
    send_genie_feedback,
    start_genie_async,
)
from ..models import (
    ChatMessageIn,
    ChatMessageOut,
    ChatStartOut,
    ChatStatusOut,
    ConversationMessageOut,
    ConversationOut,
    FeedbackIn,
    VersionOut,
)

router = APIRouter()


def _resolve_space_id(msg_space_id: str | None) -> str:
    """Resolve space_id from request or fall back to state.json."""
    if msg_space_id:
        return msg_space_id
    state = get_state()
    return state.space_id


def _get_user_id(request: Request) -> str:
    """Extract user_id from Databricks headers, fallback to 'anonymous'."""
    return request.headers.get("X-Forwarded-User", "anonymous")


def _result_to_response(result: dict) -> ChatMessageOut:
    """Convert a genie_client result dict to a ChatMessageOut."""
    chart = suggest_chart(result["columns"], result["data"])

    return ChatMessageOut(
        conversation_id=result["conversation_id"],
        message_id=result.get("message_id", ""),
        status=result["status"],
        description=result.get("description", ""),
        sql=result.get("sql", ""),
        columns=result.get("columns", []),
        data=result.get("data", []),
        row_count=result.get("row_count", 0),
        chart_suggestion=chart,
        error=result.get("error"),
        suggested_questions=result.get("suggested_questions", []),
        query_description=result.get("query_description", ""),
        is_truncated=result.get("is_truncated", False),
        is_clarification=result.get("is_clarification", False),
        error_type=result.get("error_type", ""),
    )


def _persist_message_start(
    ws,
    conversation_id: str,
    message_id: str,
    space_id: str,
    user_id: str,
    question: str,
) -> None:
    """Persist a new conversation/message to the DB. Best-effort — does not block chat."""
    try:
        existing = get_conversation(ws, conversation_id)
        if not existing:
            create_conversation(ws, conversation_id, space_id, user_id, question)
        add_message(ws, message_id, conversation_id, user_id, question)
        increment_conversation_message_count(ws, conversation_id)
    except Exception as e:
        logger.warning("Failed to persist message start: %s", e)


def _persist_message_result(ws, conversation_id: str, message_id: str, result: dict) -> None:
    """Update a message row with result metadata. Best-effort."""
    try:
        update_message_result(
            ws,
            message_id=message_id,
            conversation_id=conversation_id,
            status=result.get("status", "COMPLETED"),
            sql_text=result.get("sql", ""),
            description=result.get("description", ""),
            is_clarification=result.get("is_clarification", False),
        )
    except Exception as e:
        logger.warning("Failed to persist message result: %s", e)


# --- Version ---

@router.get("/version", response_model=VersionOut, operation_id="version")
async def version() -> VersionOut:
    """Get application version."""
    return VersionOut.from_metadata()


@router.get("/health", operation_id="healthCheck")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


# --- Chat (sync) ---

@router.post("/chat", response_model=ChatMessageOut, operation_id="sendChatMessage")
def send_chat_message(
    msg: ChatMessageIn,
    ws: Dependencies.Client,
    request: Request,
) -> ChatMessageOut:
    """Send a question to Genie and return results with chart suggestion."""
    space_id = _resolve_space_id(msg.space_id)
    user_id = _get_user_id(request)
    result = ask_genie(
        ws=ws,
        space_id=space_id,
        question=msg.question,
        conversation_id=msg.conversation_id,
    )
    conv_id = result["conversation_id"]
    msg_id = result.get("message_id", "")
    if conv_id:
        _persist_message_start(ws, conv_id, msg_id, space_id, user_id, msg.question)
        _persist_message_result(ws, conv_id, msg_id, result)

    return _result_to_response(result)


# --- Chat (async: start + poll + result) ---

@router.post("/chat/start", response_model=ChatStartOut, operation_id="startChat")
def start_chat(
    msg: ChatMessageIn,
    ws: Dependencies.Client,
    request: Request,
) -> ChatStartOut:
    """Start a Genie message without waiting for completion."""
    space_id = _resolve_space_id(msg.space_id)
    user_id = _get_user_id(request)
    result = start_genie_async(
        ws=ws,
        space_id=space_id,
        question=msg.question,
        conversation_id=msg.conversation_id,
    )
    conv_id = result["conversation_id"]
    msg_id = result["message_id"]
    if conv_id:
        _persist_message_start(ws, conv_id, msg_id, space_id, user_id, msg.question)

    return ChatStartOut(
        conversation_id=conv_id,
        message_id=msg_id,
    )


@router.get(
    "/chat/{conv_id}/{msg_id}/status",
    response_model=ChatStatusOut,
    operation_id="getChatStatus",
)
def get_chat_status(
    conv_id: str,
    msg_id: str,
    ws: Dependencies.Client,
    space_id: str | None = None,
) -> ChatStatusOut:
    """Poll message processing status."""
    sid = _resolve_space_id(space_id)
    result = poll_genie_status(
        ws=ws,
        space_id=sid,
        conversation_id=conv_id,
        message_id=msg_id,
    )
    return ChatStatusOut(
        status=result["status"],
        is_complete=result["is_complete"],
    )


@router.get(
    "/chat/{conv_id}/{msg_id}/result",
    response_model=ChatMessageOut,
    operation_id="getChatResult",
)
def get_chat_result(
    conv_id: str,
    msg_id: str,
    ws: Dependencies.Client,
    space_id: str | None = None,
) -> ChatMessageOut:
    """Fetch full result for a completed message."""
    sid = _resolve_space_id(space_id)
    result = get_genie_result(
        ws=ws,
        space_id=sid,
        conversation_id=conv_id,
        message_id=msg_id,
    )
    _persist_message_result(ws, conv_id, msg_id, result)
    return _result_to_response(result)


# --- Feedback ---

@router.post("/chat/feedback", operation_id="sendFeedback")
def send_feedback(
    feedback: FeedbackIn,
    ws: Dependencies.Client,
) -> dict[str, bool]:
    """Send thumbs up/down feedback for a Genie response."""
    state = get_state()
    success = send_genie_feedback(
        ws=ws,
        space_id=state.space_id,
        conversation_id=feedback.conversation_id,
        message_id=feedback.message_id,
        rating=feedback.rating,
    )
    return {"success": success}


# --- Conversations (DB-backed) ---

@router.get(
    "/conversations",
    response_model=list[ConversationOut],
    operation_id="listConversations",
)
def list_conversations_endpoint(
    ws: Dependencies.Client,
    request: Request,
    space_id: str | None = None,
) -> list[ConversationOut]:
    """List conversation history for the current user."""
    user_id = _get_user_id(request)
    rows = list_conversations(ws, user_id, space_id)
    return [
        ConversationOut(
            conversation_id=r.get("conversation_id", ""),
            first_question=r.get("title", ""),
            message_count=int(r.get("message_count", 0) or 0),
        )
        for r in rows
    ]


@router.get(
    "/conversations/{conv_id}",
    response_model=list[ConversationMessageOut],
    operation_id="getConversationMessages",
)
def get_conversation_messages_endpoint(
    conv_id: str,
    ws: Dependencies.Client,
) -> list[ConversationMessageOut]:
    """Get all messages in a conversation from DB."""
    rows = get_conversation_messages(ws, conv_id)
    messages = []
    for row in rows:
        response = None
        if row.get("status") in ("COMPLETED", "FAILED", "NO_RESULT"):
            response = ChatMessageOut(
                conversation_id=conv_id,
                message_id=row.get("message_id", ""),
                status=row.get("status", "COMPLETED"),
                description=row.get("description", ""),
                sql=row.get("sql_text", ""),
                columns=[],
                data=[],
                row_count=0,
                is_clarification=row.get("is_clarification") in (True, "true", "1"),
            )
        messages.append(ConversationMessageOut(
            question=row.get("question", ""),
            response=response,
        ))
    return messages
