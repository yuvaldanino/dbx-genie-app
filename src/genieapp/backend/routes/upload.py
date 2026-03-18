"""Image upload and retrieval endpoints."""

from __future__ import annotations

import io
import uuid

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from ..core import Dependencies, logger
from ..db import CATALOG, _escape, _now_iso, run_sql, _IMAGES_TABLE, parse_sql_rows

router = APIRouter()

_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/svg+xml"}
_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
_VOLUME_BASE = f"/Volumes/{CATALOG}/genie_app/images"


def _get_user_id(request: Request) -> str:
    """Extract user_id from Databricks headers."""
    return request.headers.get("X-Forwarded-User", "anonymous")


@router.post("/images/upload", operation_id="uploadImage")
async def upload_image(
    file: UploadFile,
    ws: Dependencies.Client,
    request: Request,
    space_id: str | None = None,
) -> dict:
    """Upload an image (PNG/JPG/SVG, max 5MB) to UC Volume."""
    user_id = _get_user_id(request)

    # Validate content type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Allowed: PNG, JPG, SVG.",
        )

    # Read and validate size
    data = await file.read()
    if len(data) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(data)} bytes). Maximum: {_MAX_SIZE_BYTES} bytes (5MB).",
        )

    # Generate ID and path
    image_id = str(uuid.uuid4())
    ext_map = {"image/png": "png", "image/jpeg": "jpg", "image/svg+xml": "svg"}
    ext = ext_map.get(content_type, "bin")
    volume_path = f"{_VOLUME_BASE}/{image_id}.{ext}"
    filename = file.filename or f"{image_id}.{ext}"

    # Upload to UC Volume
    try:
        ws.files.upload(volume_path, io.BytesIO(data), overwrite=True)
    except Exception as e:
        logger.error("Failed to upload image to UC Volume: %s", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    # Store metadata in DB
    now = _now_iso()
    safe_space = _escape(space_id or "")
    try:
        run_sql(
            ws,
            f"""INSERT INTO {_IMAGES_TABLE}
                (image_id, user_id, space_id, filename, content_type, volume_path, size_bytes, created_at)
                VALUES ('{_escape(image_id)}', '{_escape(user_id)}', '{safe_space}',
                        '{_escape(filename)}', '{_escape(content_type)}', '{_escape(volume_path)}',
                        {len(data)}, '{now}')""",
        )
    except Exception as e:
        logger.warning("Failed to save image metadata: %s", e)

    return {
        "image_id": image_id,
        "volume_path": volume_path,
        "filename": filename,
        "size_bytes": len(data),
    }


@router.get("/images/{image_id}", operation_id="getImage")
def get_image(
    image_id: str,
    ws: Dependencies.Client,
) -> StreamingResponse:
    """Stream an image from UC Volume."""
    safe_id = _escape(image_id)
    result = run_sql(
        ws,
        f"SELECT volume_path, content_type, filename FROM {_IMAGES_TABLE} WHERE image_id = '{safe_id}' LIMIT 1",
    )
    rows = parse_sql_rows(result)
    if not rows:
        raise HTTPException(status_code=404, detail="Image not found")

    row = rows[0]
    volume_path = row["volume_path"]
    content_type = row.get("content_type", "application/octet-stream")
    filename = row.get("filename", image_id)

    try:
        resp = ws.files.download(volume_path)
        data = resp.contents.read()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Image file not found: {e}")

    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
