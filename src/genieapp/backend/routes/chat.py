"""Chat endpoints — sync, async (start/poll/result), and feedback."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Request

from ..app_config import get_state
from ..chart_suggest import suggest_chart
from ..core import Dependencies, logger
from ..db import (
    add_message,
    create_conversation,
    get_conversation,
    get_conversation_messages,
    get_message,
    get_starred_messages,
    increment_conversation_message_count,
    list_conversations,
    toggle_star_message,
    update_message_result,
)
from ..genie_client import (
    _error_result,
    ask_genie,
    get_genie_result,
    poll_genie_status,
    recompute_from_sql,
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
    StarIn,
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
        follow_up_text=result.get("follow_up_text", ""),
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
    except Exception:
        logger.exception("Failed to persist message start")


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
    except Exception:
        logger.exception("Failed to persist message result")


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
    if conv_id and not msg.ephemeral:
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
    try:
        result = start_genie_async(
            ws=ws,
            space_id=space_id,
            question=msg.question,
            conversation_id=msg.conversation_id,
        )
    except Exception:
        if not msg.conversation_id:
            raise
        # Stale/cross-space conversation_id (e.g. old URL param) — fall back to
        # a fresh conversation instead of 500ing mid-demo.
        logger.warning("start_chat: conversation %s invalid for space %s — starting fresh",
                       msg.conversation_id, space_id)
        result = start_genie_async(ws=ws, space_id=space_id, question=msg.question, conversation_id=None)
    conv_id = result["conversation_id"]
    msg_id = result["message_id"]
    if conv_id and not msg.ephemeral:
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
    ephemeral: bool = False,
) -> ChatMessageOut:
    """Fetch full result for a completed message."""
    sid = _resolve_space_id(space_id)
    try:
        result = get_genie_result(
            ws=ws,
            space_id=sid,
            conversation_id=conv_id,
            message_id=msg_id,
        )
    except Exception as e:
        logger.exception("get_chat_result failed for %s/%s", conv_id, msg_id)
        return _result_to_response(_error_result(conv_id, e))
    if not ephemeral:
        _persist_message_result(ws, conv_id, msg_id, result)
    return _result_to_response(result)


# --- Recompute (re-run persisted SQL, no Genie round-trip) ---

@router.post(
    "/chat/{conv_id}/{msg_id}/recompute",
    response_model=ChatMessageOut,
    operation_id="recomputeMessage",
)
def recompute_message(
    conv_id: str,
    msg_id: str,
    ws: Dependencies.Client,
    request: Request,
) -> ChatMessageOut:
    """Re-execute a message's saved SQL to refresh expired result data."""
    user_id = _get_user_id(request)
    conv = get_conversation(ws, conv_id)
    if conv and conv.get("user_id") and conv["user_id"] != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

    row = get_message(ws, conv_id, msg_id)
    sql_text = (row or {}).get("sql_text") or ""
    if not sql_text:
        result = _error_result(conv_id, RuntimeError("No SQL saved for this message — ask the question again"))
        result["message_id"] = msg_id
        return _result_to_response(result)

    try:
        result = recompute_from_sql(
            ws,
            conversation_id=conv_id,
            message_id=msg_id,
            sql=sql_text,
            description=(row or {}).get("description", ""),
        )
    except Exception as e:
        logger.exception("Recompute failed for %s/%s", conv_id, msg_id)
        result = _error_result(conv_id, e)
        result["message_id"] = msg_id
        result["sql"] = sql_text
    return _result_to_response(result)


# --- Feedback ---

@router.post("/chat/feedback", operation_id="sendFeedback")
def send_feedback(
    feedback: FeedbackIn,
    ws: Dependencies.Client,
) -> dict[str, bool]:
    """Send thumbs up/down feedback for a Genie response.

    Space resolution: request body → conversation record → state.json. The old
    state.json-only path silently failed for every non-default space.
    """
    space_id = feedback.space_id or ""
    if not space_id:
        conv = get_conversation(ws, feedback.conversation_id)
        space_id = (conv or {}).get("space_id") or ""
    if not space_id:
        space_id = get_state().space_id
    success = send_genie_feedback(
        ws=ws,
        space_id=space_id,
        conversation_id=feedback.conversation_id,
        message_id=feedback.message_id,
        rating=feedback.rating,
    )
    return {"success": success}


# --- Warehouse wake (fire-and-forget warm-up) ---

@router.post("/warehouse/wake", operation_id="wakeWarehouse")
def wake_warehouse(ws: Dependencies.Client) -> dict[str, bool]:
    """Kick the SQL warehouse awake in the background (cold start is 1-3 min).

    Called on app load so the warehouse is warming before the first question.
    """
    def _ping() -> None:
        try:
            from ..db import run_sql
            run_sql(ws, "SELECT 1", raise_on_error=False)
        except Exception:
            logger.debug("warehouse wake ping failed (non-fatal)")

    import threading
    threading.Thread(target=_ping, daemon=True, name="warehouse-wake").start()
    return {"ok": True}


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
    request: Request,
    space_id: str | None = None,
) -> list[ConversationMessageOut]:
    """Get all messages in a conversation, re-fetching data from Genie API."""
    # Verify conversation belongs to the requesting user
    user_id = _get_user_id(request)
    conv = get_conversation(ws, conv_id)
    if conv and conv.get("user_id") and conv["user_id"] != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
    rows = get_conversation_messages(ws, conv_id)

    # Resolve space_id from conversation record if not provided
    if not space_id and conv:
        space_id = conv.get("space_id")

    if not rows:
        return []

    # Rebuild message data in PARALLEL — serial re-fetch (Genie + SQL re-execution
    # per message) made long conversations take 10-40s to open. Order is preserved
    # by pool.map; workers bounded to keep warehouse fan-out sane. User isolation
    # is unaffected: the ownership check above runs before any fetching.
    with ThreadPoolExecutor(max_workers=min(6, len(rows))) as pool:
        return list(pool.map(
            lambda row: _build_conversation_message(ws, conv_id, space_id, row),
            rows,
        ))


def _build_conversation_message(
    ws,
    conv_id: str,
    space_id: str | None,
    row: dict,
) -> ConversationMessageOut:
    """Build one history message, re-fetching Genie data. Runs in a worker thread.

    Hard rule: genie.* calls MUST use the SP client — OBO tokens lack the
    `genie` scope (403) and silently degraded history to metadata-only.
    """
    response = None
    is_starred = row.get("is_starred") in (True, "true", "1")
    msg_id = row.get("message_id", "")

    if row.get("status") in ("COMPLETED", "FAILED", "NO_RESULT"):
        # Try re-fetching full data from Genie API
        if row.get("status") == "COMPLETED" and msg_id and space_id:
            try:
                result = get_genie_result(ws, space_id, conv_id, msg_id)
                response = _result_to_response(result)
                response.is_starred = is_starred
            except Exception:
                logger.warning("Could not re-fetch Genie data for %s/%s — falling back to metadata", conv_id, msg_id)
                response = None

        # Fallback to metadata-only response
        if response is None:
            response = ChatMessageOut(
                conversation_id=conv_id,
                message_id=msg_id,
                status=row.get("status", "COMPLETED"),
                description=row.get("description", ""),
                sql=row.get("sql_text", ""),
                columns=[],
                data=[],
                row_count=0,
                is_clarification=row.get("is_clarification") in (True, "true", "1"),
                is_starred=is_starred,
            )

    return ConversationMessageOut(
        question=row.get("question", ""),
        response=response,
        is_starred=is_starred,
    )


# --- Starred Queries ---

@router.get(
    "/chat/starred",
    response_model=list[ConversationMessageOut],
    operation_id="getStarredMessages",
)
def get_starred_messages_endpoint(
    ws: Dependencies.Client,
    request: Request,
    space_id: str | None = None,
) -> list[ConversationMessageOut]:
    """Get starred messages for the current user in a space."""
    user_id = _get_user_id(request)
    if not space_id:
        return []
    rows = get_starred_messages(ws, user_id, space_id)
    messages = []
    for row in rows:
        response = None
        msg_id = row.get("message_id", "")
        conv_id = row.get("conversation_id", "")
        if row.get("status") == "COMPLETED" and msg_id and space_id:
            try:
                result = get_genie_result(ws, space_id, conv_id, msg_id)
                response = _result_to_response(result)
                response.is_starred = True
            except Exception:
                response = ChatMessageOut(
                    conversation_id=conv_id,
                    message_id=msg_id,
                    status=row.get("status", "COMPLETED"),
                    description=row.get("description", ""),
                    sql=row.get("sql_text", ""),
                    columns=[],
                    data=[],
                    row_count=0,
                    is_starred=True,
                )
        messages.append(ConversationMessageOut(
            question=row.get("question", ""),
            response=response,
            is_starred=True,
        ))
    return messages


@router.patch(
    "/chat/{conv_id}/{msg_id}/star",
    operation_id="toggleStar",
)
def toggle_star_endpoint(
    conv_id: str,
    msg_id: str,
    body: StarIn,
    ws: Dependencies.Client,
    request: Request,
) -> dict[str, bool]:
    """Toggle star status for a message."""
    user_id = _get_user_id(request)
    toggle_star_message(ws, msg_id, conv_id, user_id, body.starred)
    return {"starred": body.starred}
