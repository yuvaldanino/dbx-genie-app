"""API routes for GenieApp."""

from __future__ import annotations

import csv
import io
import json

from fastapi.responses import StreamingResponse

from .app_config import get_state
from .chart_suggest import suggest_chart
from .core import Dependencies, create_router, logger
from .genie_client import (
    ask_genie,
    get_genie_result,
    get_table_detail,
    poll_genie_status,
    send_genie_feedback,
    start_genie_async,
)
from .models import (
    AppConfigOut,
    BrandingOut,
    ChatMessageIn,
    ChatMessageOut,
    ChatStartOut,
    ChatStatusOut,
    ChartSuggestion,
    ColumnInfo,
    ConversationOut,
    ExportRequest,
    FeedbackIn,
    TableDetailOut,
    TableInfoOut,
    VersionOut,
)

router = create_router()

# In-memory conversation store (per-process)
_conversations: dict[str, list[dict]] = {}


def _result_to_response(result: dict, question: str | None = None) -> ChatMessageOut:
    """Convert a genie_client result dict to a ChatMessageOut."""
    chart = suggest_chart(result["columns"], result["data"])

    # Store in conversation history
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


@router.get("/version", response_model=VersionOut, operation_id="version")
async def version() -> VersionOut:
    """Get application version."""
    return VersionOut.from_metadata()


@router.get("/config", response_model=AppConfigOut, operation_id="getAppConfig")
async def get_app_config() -> AppConfigOut:
    """Get app configuration and branding for frontend."""
    state = get_state()
    return AppConfigOut(
        space_id=state.space_id,
        display_name=state.display_name,
        sample_questions=state.sample_questions,
        branding=BrandingOut(
            company_name=state.branding.company_name,
            description=state.branding.description,
            logo_path=state.branding.logo_path,
            primary_color=state.branding.primary_color,
            secondary_color=state.branding.secondary_color,
        ),
    )


# --- Chat (sync) ---

@router.post("/chat", response_model=ChatMessageOut, operation_id="sendChatMessage")
def send_chat_message(
    msg: ChatMessageIn,
    ws: Dependencies.Client,
) -> ChatMessageOut:
    """Send a question to Genie and return results with chart suggestion."""
    state = get_state()
    result = ask_genie(
        ws=ws,
        space_id=state.space_id,
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
    state = get_state()
    result = start_genie_async(
        ws=ws,
        space_id=state.space_id,
        question=msg.question,
        conversation_id=msg.conversation_id,
    )
    # Store the question for later retrieval
    conv_id = result["conversation_id"]
    if conv_id:
        if conv_id not in _conversations:
            _conversations[conv_id] = []
        _conversations[conv_id].append({
            "question": msg.question,
            "message_id": result["message_id"],
            "result": None,  # Filled when result is fetched
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
) -> ChatStatusOut:
    """Poll message processing status."""
    state = get_state()
    result = poll_genie_status(
        ws=ws,
        space_id=state.space_id,
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
) -> ChatMessageOut:
    """Fetch full result for a completed message."""
    state = get_state()
    result = get_genie_result(
        ws=ws,
        space_id=state.space_id,
        conversation_id=conv_id,
        message_id=msg_id,
    )

    # Find and update stored question
    question = None
    if conv_id in _conversations:
        for entry in _conversations[conv_id]:
            if entry.get("message_id") == msg_id:
                question = entry.get("question")
                entry["result"] = result
                break

    return _result_to_response(result, question=question)


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


# --- Tables ---

@router.get("/tables", response_model=list[TableInfoOut], operation_id="listTables")
async def list_tables() -> list[TableInfoOut]:
    """List all tables in the Genie Space."""
    state = get_state()
    return [
        TableInfoOut(
            full_name=t.full_name,
            table_name=t.table_name,
            comment=t.comment,
        )
        for t in state.tables
    ]


@router.get("/tables/{name}", response_model=TableDetailOut, operation_id="getTableDetail")
def get_table(name: str, ws: Dependencies.Client) -> TableDetailOut:
    """Get detailed table schema information."""
    state = get_state()

    # Find matching table
    full_name = None
    for t in state.tables:
        if t.table_name == name or t.full_name == name:
            full_name = t.full_name
            break

    if not full_name:
        full_name = f"{state.catalog}.{state.schema_name}.{name}"

    detail = get_table_detail(ws, full_name)
    return TableDetailOut(
        full_name=detail["full_name"],
        table_name=detail["table_name"],
        comment=detail.get("comment", ""),
        columns=[ColumnInfo(**c) for c in detail.get("columns", [])],
        row_count=detail.get("row_count", 0),
    )


# --- Conversations ---

@router.get(
    "/conversations",
    response_model=list[ConversationOut],
    operation_id="listConversations",
)
async def list_conversations() -> list[ConversationOut]:
    """List conversation history."""
    return [
        ConversationOut(
            conversation_id=conv_id,
            first_question=messages[0]["question"] if messages else "",
            message_count=len(messages),
        )
        for conv_id, messages in _conversations.items()
    ]


# --- Export ---

@router.post("/export", operation_id="exportConversation")
async def export_conversation(req: ExportRequest) -> StreamingResponse:
    """Export conversation data as JSON or CSV."""
    messages = _conversations.get(req.conversation_id, [])

    if req.format == "json":
        content = json.dumps(messages, indent=2, default=str)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=conversation_{req.conversation_id}.json"},
        )

    # CSV format — flatten all result data
    output = io.StringIO()
    writer = None
    for msg in messages:
        result = msg.get("result", {})
        if not result:
            continue
        columns = result.get("columns", [])
        data = result.get("data", [])
        if columns and data:
            if writer is None:
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
            for row in data:
                writer.writerow(row)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=conversation_{req.conversation_id}.csv"},
    )
