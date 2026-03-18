"""Chat endpoints — sync, async (start/poll/result), and feedback."""

from __future__ import annotations

from fastapi import APIRouter

from ..app_config import get_state
from ..chart_suggest import suggest_chart
from ..core import Dependencies, logger
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
    ChartSuggestion,
    FeedbackIn,
    VersionOut,
)

router = APIRouter()

# In-memory conversation store (per-process) — replaced by DB in Phase 2
_conversations: dict[str, list[dict]] = {}
_conversation_spaces: dict[str, str] = {}


def _resolve_space_id(msg_space_id: str | None) -> str:
    """Resolve space_id from request or fall back to state.json."""
    if msg_space_id:
        return msg_space_id
    state = get_state()
    return state.space_id


def _result_to_response(result: dict, question: str | None = None) -> ChatMessageOut:
    """Convert a genie_client result dict to a ChatMessageOut."""
    chart = suggest_chart(result["columns"], result["data"])

    conv_id = result["conversation_id"]
    if conv_id and question:
        if conv_id not in _conversations:
            _conversations[conv_id] = []
        _conversations[conv_id].append({
            "question": question,
            "message_id": result.get("message_id", ""),
            "result": result,
        })

    return ChatMessageOut(
        conversation_id=conv_id,
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


# --- Version ---

@router.get("/version", response_model=VersionOut, operation_id="version")
async def version() -> VersionOut:
    """Get application version."""
    return VersionOut.from_metadata()


# --- Chat (sync) ---

@router.post("/chat", response_model=ChatMessageOut, operation_id="sendChatMessage")
def send_chat_message(
    msg: ChatMessageIn,
    ws: Dependencies.Client,
) -> ChatMessageOut:
    """Send a question to Genie and return results with chart suggestion."""
    space_id = _resolve_space_id(msg.space_id)
    result = ask_genie(
        ws=ws,
        space_id=space_id,
        question=msg.question,
        conversation_id=msg.conversation_id,
    )
    return _result_to_response(result, question=msg.question)


# --- Chat (async: start + poll + result) ---

@router.post("/chat/start", response_model=ChatStartOut, operation_id="startChat")
def start_chat(
    msg: ChatMessageIn,
    ws: Dependencies.Client,
) -> ChatStartOut:
    """Start a Genie message without waiting for completion."""
    space_id = _resolve_space_id(msg.space_id)
    result = start_genie_async(
        ws=ws,
        space_id=space_id,
        question=msg.question,
        conversation_id=msg.conversation_id,
    )
    conv_id = result["conversation_id"]
    if conv_id:
        if conv_id not in _conversations:
            _conversations[conv_id] = []
        _conversation_spaces[conv_id] = space_id
        _conversations[conv_id].append({
            "question": msg.question,
            "message_id": result["message_id"],
            "result": None,
        })

    return ChatStartOut(
        conversation_id=result["conversation_id"],
        message_id=result["message_id"],
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

    if conv_id in _conversations:
        for entry in _conversations[conv_id]:
            if entry.get("message_id") == msg_id:
                entry["result"] = result
                break

    return _result_to_response(result, question=None)


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


# --- Conversations (in-memory, replaced by DB in Phase 2) ---

from ..models import ConversationMessageOut, ConversationOut


@router.get(
    "/conversations",
    response_model=list[ConversationOut],
    operation_id="listConversations",
)
async def list_conversations(space_id: str | None = None) -> list[ConversationOut]:
    """List conversation history, optionally filtered by space_id."""
    results = []
    for conv_id, messages in _conversations.items():
        if space_id and _conversation_spaces.get(conv_id) != space_id:
            continue
        results.append(ConversationOut(
            conversation_id=conv_id,
            first_question=messages[0]["question"] if messages else "",
            message_count=len(messages),
        ))
    return results


@router.get(
    "/conversations/{conv_id}",
    response_model=list[ConversationMessageOut],
    operation_id="getConversationMessages",
)
async def get_conversation_messages(conv_id: str) -> list[ConversationMessageOut]:
    """Get all messages in a conversation."""
    entries = _conversations.get(conv_id, [])
    messages = []
    for entry in entries:
        result = entry.get("result")
        response = None
        if result:
            chart = suggest_chart(result.get("columns", []), result.get("data", []))
            response = ChatMessageOut(
                conversation_id=result.get("conversation_id", conv_id),
                message_id=result.get("message_id", ""),
                status=result.get("status", "COMPLETED"),
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
        messages.append(ConversationMessageOut(
            question=entry.get("question", ""),
            response=response,
        ))
    return messages
