"""Conversation export endpoints."""

from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..core import Dependencies
from ..db import get_conversation, get_conversation_messages
from ..models import ExportRequest

router = APIRouter()


def _get_user_id(request: Request) -> str:
    """Extract user_id from Databricks headers, fallback to 'anonymous'."""
    return request.headers.get("X-Forwarded-User", "anonymous")


@router.post("/export", operation_id="exportConversation")
def export_conversation(
    req: ExportRequest,
    ws: Dependencies.Client,
    request: Request,
) -> StreamingResponse:
    """Export conversation data as JSON or CSV."""
    # Verify conversation belongs to the requesting user
    user_id = _get_user_id(request)
    conv = get_conversation(ws, req.conversation_id)
    if conv and conv.get("user_id") and conv["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to export this conversation")
    rows = get_conversation_messages(ws, req.conversation_id)

    if req.format == "json":
        content = json.dumps(rows, indent=2, default=str)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=conversation_{req.conversation_id}.json"},
        )

    # CSV format — export message metadata
    output = io.StringIO()
    if rows:
        fieldnames = ["question", "status", "description", "sql_text", "created_at"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=conversation_{req.conversation_id}.csv"},
    )
