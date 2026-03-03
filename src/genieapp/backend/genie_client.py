"""Databricks Genie API client wrapper."""

from __future__ import annotations

from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import (
    GenieFeedbackRating,
    GenieMessage,
    MessageStatus,
)

from .core import logger


# --- Completed statuses ---
_TERMINAL_STATUSES = {
    MessageStatus.COMPLETED,
    MessageStatus.FAILED,
    MessageStatus.CANCELLED,
    MessageStatus.QUERY_RESULT_EXPIRED,
}


def ask_genie(
    ws: WorkspaceClient,
    space_id: str,
    question: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Send a question to Genie and poll until complete.

    Returns:
        Dict with conversation_id, message_id, status, description, sql,
        columns, data, row_count, suggested_questions, query_description,
        is_truncated, is_clarification, error, error_type.
    """
    try:
        if conversation_id:
            resp = ws.genie.create_message_and_wait(
                space_id=space_id,
                conversation_id=conversation_id,
                content=question,
            )
        else:
            resp = ws.genie.start_conversation_and_wait(
                space_id=space_id,
                content=question,
            )

        return _parse_genie_response(ws, space_id, resp)

    except Exception as e:
        logger.error(f"Genie API error: {e}")
        return _error_result(conversation_id or "", e)


def start_genie_async(
    ws: WorkspaceClient,
    space_id: str,
    question: str,
    conversation_id: str | None = None,
) -> dict[str, str]:
    """Start a Genie message without waiting for completion.

    Returns:
        Dict with conversation_id and message_id.
    """
    if conversation_id:
        op = ws.genie.create_message(
            space_id=space_id,
            conversation_id=conversation_id,
            content=question,
        )
    else:
        op = ws.genie.start_conversation(
            space_id=space_id,
            content=question,
        )

    return {
        "conversation_id": op.conversation_id or "",
        "message_id": op.message_id or "",
    }


def poll_genie_status(
    ws: WorkspaceClient,
    space_id: str,
    conversation_id: str,
    message_id: str,
) -> dict[str, Any]:
    """Check message processing status.

    Returns:
        Dict with status string and is_complete boolean.
    """
    msg = ws.genie.get_message(
        space_id=space_id,
        conversation_id=conversation_id,
        message_id=message_id,
    )
    status = msg.status
    status_str = status.value if status else "SUBMITTED"
    is_complete = status in _TERMINAL_STATUSES if status else False

    return {"status": status_str, "is_complete": is_complete}


def get_genie_result(
    ws: WorkspaceClient,
    space_id: str,
    conversation_id: str,
    message_id: str,
) -> dict[str, Any]:
    """Fetch full result for a completed message."""
    msg = ws.genie.get_message(
        space_id=space_id,
        conversation_id=conversation_id,
        message_id=message_id,
    )
    return _parse_genie_response(ws, space_id, msg)


def send_genie_feedback(
    ws: WorkspaceClient,
    space_id: str,
    conversation_id: str,
    message_id: str,
    rating: str,
) -> bool:
    """Send thumbs up/down feedback for a message.

    Args:
        rating: "POSITIVE" or "NEGATIVE".

    Returns:
        True on success.
    """
    try:
        genie_rating = (
            GenieFeedbackRating.POSITIVE
            if rating.upper() == "POSITIVE"
            else GenieFeedbackRating.NEGATIVE
        )
        ws.genie.send_message_feedback(
            space_id=space_id,
            conversation_id=conversation_id,
            message_id=message_id,
            rating=genie_rating,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send feedback: {e}")
        return False


def _parse_genie_response(
    ws: WorkspaceClient,
    space_id: str,
    resp: GenieMessage,
) -> dict[str, Any]:
    """Parse a Genie response into a structured dict."""
    conversation_id = resp.conversation_id or ""
    message_id = resp.message_id or resp.id or ""
    status = "COMPLETED"
    description = ""
    sql = ""
    query_description = ""
    columns: list[str] = []
    data: list[dict] = []
    suggested_questions: list[str] = []
    is_truncated = False
    is_clarification = False
    error = None

    if resp.attachments:
        for attachment in resp.attachments:
            # Text attachment
            if attachment.text:
                description = attachment.text.content or ""
                # Clarification detection
                if attachment.text.purpose:
                    purpose_str = str(attachment.text.purpose.value) if hasattr(attachment.text.purpose, 'value') else str(attachment.text.purpose)
                    if purpose_str == "FOLLOW_UP_QUESTION":
                        is_clarification = True

            # Query attachment
            if attachment.query:
                sql = attachment.query.query or ""
                query_description = attachment.query.description or ""

                # Truncation check
                if attachment.query.query_result_metadata:
                    is_truncated = attachment.query.query_result_metadata.is_truncated or False

                if sql:
                    try:
                        result = ws.genie.get_message_query_result(
                            space_id=space_id,
                            conversation_id=conversation_id,
                            message_id=message_id,
                        )

                        raw = result.as_dict() if hasattr(result, 'as_dict') else {}
                        sr = raw.get('statement_response', {})

                        # Extract columns from manifest
                        manifest = sr.get('manifest', {})
                        schema = manifest.get('schema', {})
                        raw_cols = schema.get('columns', [])
                        if raw_cols:
                            columns = [c.get('name', '') for c in raw_cols if c.get('name')]

                        # Check if data_array is inline
                        raw_result = sr.get('result', {})
                        data_array = raw_result.get('data_array')

                        if data_array and columns:
                            for row in data_array:
                                data.append(dict(zip(columns, row)))
                        elif columns and sr.get('statement_id'):
                            # Data not inline — fetch via statement execution API
                            stmt_id = sr['statement_id']
                            stmt_resp = ws.statement_execution.get_statement(stmt_id)
                            if stmt_resp.result and stmt_resp.result.data_array:
                                for row in stmt_resp.result.data_array:
                                    if row:
                                        data.append(dict(zip(columns, row)))

                    except Exception as e:
                        logger.warning(f"Failed to fetch query result: {e}")

            # Suggested questions
            if attachment.suggested_questions and attachment.suggested_questions.questions:
                suggested_questions = [
                    q for q in attachment.suggested_questions.questions if q
                ]

    # Error from message
    if resp.error:
        error = resp.error.error or "Unknown error"
        status = "FAILED"

    if not error and not description and not sql and not data:
        status = "NO_RESULT"

    return {
        "conversation_id": conversation_id,
        "message_id": message_id,
        "status": status,
        "description": description,
        "sql": sql,
        "query_description": query_description,
        "columns": columns,
        "data": data,
        "row_count": len(data),
        "suggested_questions": suggested_questions,
        "is_truncated": is_truncated,
        "is_clarification": is_clarification,
        "error": error,
        "error_type": "",
    }


def _classify_error(error: Exception) -> str:
    """Classify an error into a user-friendly category."""
    msg = str(error).lower()
    if "permission" in msg or "unauthorized" in msg or "access" in msg:
        return "PERMISSION_DENIED"
    if "not found" in msg:
        return "NOT_FOUND"
    if "timeout" in msg or "timed out" in msg:
        return "TIMEOUT"
    if "rate" in msg or "throttl" in msg:
        return "RATE_LIMITED"
    return "UNKNOWN"


def _error_result(conversation_id: str, error: Exception) -> dict[str, Any]:
    """Build a standardized error result dict."""
    return {
        "conversation_id": conversation_id,
        "message_id": "",
        "status": "FAILED",
        "description": "",
        "sql": "",
        "query_description": "",
        "columns": [],
        "data": [],
        "row_count": 0,
        "suggested_questions": [],
        "is_truncated": False,
        "is_clarification": False,
        "error": str(error),
        "error_type": _classify_error(error),
    }


def get_table_detail(
    ws: WorkspaceClient,
    full_name: str,
) -> dict[str, Any]:
    """Get table schema details via Unity Catalog."""
    try:
        table_info = ws.tables.get(full_name)
        columns = []
        if table_info.columns:
            for col in table_info.columns:
                columns.append({
                    "name": col.name or "",
                    "type": col.type_text or str(col.type_name or ""),
                    "comment": col.comment or "",
                })

        return {
            "full_name": full_name,
            "table_name": table_info.name or full_name.split(".")[-1],
            "comment": table_info.comment or "",
            "columns": columns,
            "row_count": 0,
        }
    except Exception as e:
        logger.error(f"Failed to get table detail for {full_name}: {e}")
        return {
            "full_name": full_name,
            "table_name": full_name.split(".")[-1],
            "comment": "",
            "columns": [],
            "row_count": 0,
        }
