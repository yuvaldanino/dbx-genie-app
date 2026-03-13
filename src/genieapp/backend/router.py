"""API routes for GenieApp."""

from __future__ import annotations

import csv
import io
import json

from databricks.sdk import WorkspaceClient
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
    ConversationMessageOut,
    ConversationOut,
    CreateSpaceIn,
    CreateSpaceOut,
    ExportRequest,
    FeedbackIn,
    JobStatusOut,
    SpaceOut,
    TableInfoBrief,
    TableDetailOut,
    TableInfoOut,
    VersionOut,
)

router = create_router()

# In-memory conversation store (per-process)
# Key: conversation_id → list of message dicts
_conversations: dict[str, list[dict]] = {}
# Maps conversation_id → space_id
_conversation_spaces: dict[str, str] = {}

# --- Constants ---
_CATALOG = "yd_launchpad_final_classic_catalog"
_SCHEMA = "genie_app"
_WAREHOUSE_ID = "551addcb4415adb7"
_SESSIONS_TABLE = f"`{_CATALOG}`.`{_SCHEMA}`.`sessions`"


def _resolve_space_id(msg_space_id: str | None, ws: WorkspaceClient | None = None) -> str:
    """Resolve space_id from request or fall back to state.json."""
    if msg_space_id:
        return msg_space_id
    state = get_state()
    return state.space_id


def _run_sql(ws: WorkspaceClient, sql: str) -> dict:
    """Execute SQL via the Databricks SQL Statements API."""
    return ws.api_client.do(
        "POST",
        "/api/2.0/sql/statements",
        body={"statement": sql, "warehouse_id": _WAREHOUSE_ID, "wait_timeout": "50s"},
    )


def _parse_sql_rows(result: dict) -> list[dict]:
    """Parse SQL statement API response into a list of row dicts."""
    if result.get("status", {}).get("state") != "SUCCEEDED":
        return []
    manifest = result.get("manifest", {})
    cols = [c["name"] for c in manifest.get("schema", {}).get("columns", [])]
    data_array = result.get("result", {}).get("data_array", [])
    return [dict(zip(cols, row)) for row in data_array]


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
        tables=[
            TableInfoBrief(full_name=t.full_name, table_name=t.table_name, comment=t.comment)
            for t in state.tables
        ],
    )


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
    # Store the question for later retrieval
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

    # Update stored entry (already created by start_chat)
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


# --- Spaces ---

@router.get("/spaces/debug", operation_id="debugSpaces")
def debug_spaces(ws: Dependencies.Client) -> dict:
    """Debug endpoint — shows raw SQL result for sessions query."""
    sql = (
        f"SELECT space_id, company_name, description, logo_path, primary_color, "
        f"secondary_color, created_at FROM {_SESSIONS_TABLE} ORDER BY created_at DESC"
    )
    try:
        result = _run_sql(ws, sql)
        rows = _parse_sql_rows(result)
        return {
            "sql": sql,
            "raw_status": result.get("status"),
            "raw_keys": list(result.keys()),
            "parsed_row_count": len(rows),
            "rows": rows,
        }
    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__, "sql": sql}


@router.get("/spaces", response_model=list[SpaceOut], operation_id="listSpaces")
def list_spaces(ws: Dependencies.Client) -> list[SpaceOut]:
    """List all created Genie Spaces from the sessions table."""
    try:
        result = _run_sql(
            ws,
            f"SELECT space_id, company_name, description, logo_path, primary_color, "
            f"secondary_color, created_at FROM {_SESSIONS_TABLE} ORDER BY created_at DESC",
        )
        rows = _parse_sql_rows(result)
        logger.info("list_spaces: SQL returned %d rows, keys=%s", len(rows), list(result.keys()))
        if not rows:
            logger.info("list_spaces: no rows, falling back. status=%s", result.get("status"))
            return _fallback_spaces()

        return [
            SpaceOut(
                space_id=r.get("space_id", ""),
                company_name=r.get("company_name", ""),
                description=r.get("description", ""),
                logo_path=r.get("logo_path", ""),
                primary_color=r.get("primary_color", "#1a73e8"),
                secondary_color=r.get("secondary_color", "#ea4335"),
                created_at=str(r.get("created_at", "")),
            )
            for r in rows
        ]
    except Exception as e:
        logger.error("list_spaces exception: %s: %s", type(e).__name__, e)
        return _fallback_spaces()


def _fallback_spaces() -> list[SpaceOut]:
    """Fall back to state.json if sessions table is unavailable."""
    try:
        state = get_state()
        return [
            SpaceOut(
                space_id=state.space_id,
                company_name=state.branding.company_name,
                description=state.branding.description,
                logo_path=state.branding.logo_path,
                primary_color=state.branding.primary_color,
                secondary_color=state.branding.secondary_color,
            )
        ]
    except Exception:
        return []


@router.get(
    "/spaces/{space_id}/config",
    response_model=AppConfigOut,
    operation_id="getSpaceConfig",
)
def get_space_config(space_id: str, ws: Dependencies.Client) -> AppConfigOut:
    """Get config for a specific Genie Space from the sessions table."""
    safe_id = space_id.replace("'", "''")
    result = _run_sql(
        ws,
        f"SELECT * FROM {_SESSIONS_TABLE} WHERE space_id = '{safe_id}' LIMIT 1",
    )
    rows = _parse_sql_rows(result)

    if not rows:
        return get_app_config()

    row = rows[0]
    tables_info = json.loads(row.get("tables_json", "[]"))
    sample_questions = json.loads(row.get("sample_questions_json", "[]"))

    return AppConfigOut(
        space_id=space_id,
        display_name=f"{row.get('company_name', '')} Analytics",
        sample_questions=sample_questions,
        branding=BrandingOut(
            company_name=row.get("company_name", ""),
            description=row.get("description", ""),
            logo_path=row.get("logo_path", ""),
            primary_color=row.get("primary_color", "#1a73e8"),
            secondary_color=row.get("secondary_color", "#ea4335"),
        ),
        tables=[
            TableInfoBrief(
                full_name=t.get("full_name", ""),
                table_name=t.get("table_name", ""),
                comment=t.get("comment", ""),
            )
            for t in tables_info
        ],
    )


@router.post("/spaces", response_model=CreateSpaceOut, operation_id="createSpace")
def create_space(
    req: CreateSpaceIn,
    ws: Dependencies.Client,
) -> CreateSpaceOut:
    """Trigger the DABs pipeline to create a new Genie Space."""
    # Trigger the pipeline job (ID from DABs deployment)
    job_id = 381399907081683
    run = ws.jobs.run_now(
        job_id=job_id,
        notebook_params={
            "catalog": _CATALOG,
            "schema": _SCHEMA,
            "company_name": req.company_name,
            "company_description": req.description,
            "primary_color": "#1a73e8",
            "secondary_color": "#ea4335",
            "warehouse_id": _WAREHOUSE_ID,
            "databricks_host_id": "7474655921234161",
            "llm_model": "opendoor-claude-opus-46",
        },
    )

    return CreateSpaceOut(run_id=str(run.run_id))


@router.get(
    "/jobs/{run_id}",
    response_model=JobStatusOut,
    operation_id="getJobStatus",
)
def get_job_status(run_id: str, ws: Dependencies.Client) -> JobStatusOut:
    """Poll the status of a pipeline job run."""
    run = ws.jobs.get_run(int(run_id))
    state = run.state

    # Map Databricks run states to simple statuses
    life_cycle = state.life_cycle_state.value if state.life_cycle_state else "UNKNOWN"
    result_state = state.result_state.value if state.result_state else None

    if life_cycle in ("TERMINATED",):
        if result_state == "SUCCESS":
            status = "COMPLETED"
        else:
            status = "FAILED"
    elif life_cycle in ("INTERNAL_ERROR", "SKIPPED"):
        status = "FAILED"
    else:
        status = "RUNNING"

    # On completion, find the space_id by matching company_name from job params
    space_id = None
    error = None
    if status == "COMPLETED":
        try:
            company_name = ""
            if run.overriding_parameters and run.overriding_parameters.notebook_params:
                company_name = run.overriding_parameters.notebook_params.get("company_name", "")

            if company_name:
                safe_name = company_name.replace("'", "''")
                result = _run_sql(
                    ws,
                    f"SELECT space_id FROM {_SESSIONS_TABLE} "
                    f"WHERE company_name = '{safe_name}' ORDER BY created_at DESC LIMIT 1",
                )
            else:
                result = _run_sql(
                    ws,
                    f"SELECT space_id FROM {_SESSIONS_TABLE} ORDER BY created_at DESC LIMIT 1",
                )
            rows = _parse_sql_rows(result)
            if rows:
                space_id = rows[0].get("space_id")
        except Exception as e:
            logger.warning("Could not fetch space_id after job completion: %s", e)

    if status == "FAILED":
        error = state.state_message or "Pipeline failed"

    return JobStatusOut(
        run_id=run_id,
        status=status,
        space_id=space_id,
        error=error,
    )
