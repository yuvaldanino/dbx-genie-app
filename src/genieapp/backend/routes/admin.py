"""Admin dashboard endpoints — usage metrics, user activity, space management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..core import Dependencies
from ..db import (
    get_admin_stats,
    get_all_spaces_with_stats,
    get_all_users_with_activity,
    get_usage_trend,
    is_admin,
    set_space_shared,
)

router = APIRouter(prefix="/admin")


def _require_admin(request: Request) -> str:
    """Check admin access, raise 403 if not admin."""
    user_id = request.headers.get("X-Forwarded-User", "anonymous")
    if not is_admin(user_id):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


@router.get("/check", operation_id="adminCheck")
def admin_check(request: Request) -> dict[str, bool]:
    """Check if the current user is an admin."""
    user_id = request.headers.get("X-Forwarded-User", "anonymous")
    return {"is_admin": is_admin(user_id)}


@router.get("/stats", operation_id="adminStats")
def admin_stats(ws: Dependencies.Client, request: Request) -> dict:
    """Get aggregate KPI stats."""
    _require_admin(request)
    return get_admin_stats(ws)


@router.get("/usage-trend", operation_id="adminUsageTrend")
def admin_usage_trend(
    ws: Dependencies.Client,
    request: Request,
    days: int = 30,
) -> list[dict]:
    """Get messages per day for the last N days."""
    _require_admin(request)
    return get_usage_trend(ws, days)


@router.get("/users", operation_id="adminUsers")
def admin_users(ws: Dependencies.Client, request: Request) -> list[dict]:
    """Get all users with activity metrics."""
    _require_admin(request)
    return get_all_users_with_activity(ws)


@router.get("/spaces", operation_id="adminSpaces")
def admin_spaces(ws: Dependencies.Client, request: Request) -> list[dict]:
    """Get all spaces with stats."""
    _require_admin(request)
    return get_all_spaces_with_stats(ws)


class ToggleSharedIn(BaseModel):
    """Toggle shared status."""
    shared: bool


@router.patch("/spaces/{space_id}/shared", operation_id="adminToggleShared")
def admin_toggle_shared(
    space_id: str,
    body: ToggleSharedIn,
    ws: Dependencies.Client,
    request: Request,
) -> dict[str, bool]:
    """Toggle a space's shared/private status."""
    _require_admin(request)
    set_space_shared(ws, space_id, body.shared)
    return {"shared": body.shared}
