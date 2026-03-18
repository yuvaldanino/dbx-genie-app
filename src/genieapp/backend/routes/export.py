"""Conversation export endpoints."""

from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..core import Dependencies
from ..db import get_conversation_messages
from ..models import ExportRequest

router = APIRouter()


@router.post("/export", operation_id="exportConversation")
def export_conversation(
    req: ExportRequest,
    ws: Dependencies.Client,
) -> StreamingResponse:
    """Export conversation data as JSON or CSV."""
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
