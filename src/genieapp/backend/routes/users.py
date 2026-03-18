"""User profile and preferences endpoints."""

from __future__ import annotations

import json
from typing import Any

from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, Request

from ..core import Dependencies, logger
from ..db import get_or_create_user, update_user_preferences
from ..models import UserOut, UserPreferencesIn

router = APIRouter()

_ANONYMOUS_USER = UserOut(
    user_id="anonymous",
    email="anonymous@local",
    username="Anonymous",
    default_template="simple",
    preferences={},
)


def _get_ws_or_none(request: Request) -> WorkspaceClient | None:
    """Get WorkspaceClient if available, None otherwise (local dev)."""
    try:
        return request.app.state.workspace_client
    except AttributeError:
        return None


@router.get("/users/me", response_model=UserOut, operation_id="getCurrentUser")
def get_current_user(
    headers: Dependencies.Headers,
    request: Request,
) -> UserOut:
    """Get or create the current user from Databricks Apps headers."""
    if not headers.user_id:
        return _ANONYMOUS_USER

    ws = _get_ws_or_none(request)
    if not ws:
        return _ANONYMOUS_USER

    user = get_or_create_user(
        ws=ws,
        user_id=headers.user_id,
        email=headers.user_email,
        username=headers.user_name,
    )
    return _user_dict_to_out(user)


@router.patch("/users/me/preferences", response_model=UserOut, operation_id="updateUserPreferences")
def update_preferences(
    prefs: UserPreferencesIn,
    headers: Dependencies.Headers,
    request: Request,
) -> UserOut:
    """Update the current user's preferences."""
    if not headers.user_id:
        return _ANONYMOUS_USER

    ws = _get_ws_or_none(request)
    if not ws:
        return _ANONYMOUS_USER

    user = update_user_preferences(
        ws=ws,
        user_id=headers.user_id,
        default_template=prefs.default_template,
        preferences=prefs.preferences,
    )
    return _user_dict_to_out(user)


def _user_dict_to_out(user: dict[str, Any]) -> UserOut:
    """Convert a DB user dict to UserOut model."""
    prefs = {}
    if user.get("preferences_json"):
        try:
            prefs = json.loads(user["preferences_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    return UserOut(
        user_id=user.get("user_id", ""),
        email=user.get("email", ""),
        username=user.get("username", ""),
        default_template=user.get("default_template", "simple"),
        preferences=prefs,
    )
