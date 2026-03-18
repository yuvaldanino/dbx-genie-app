"""Conversation export endpoints."""

from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..models import ExportRequest
from .chat import _conversations

router = APIRouter()


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
