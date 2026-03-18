"""Centralized data access layer for UC Delta tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from cachetools import TTLCache
from databricks.sdk import WorkspaceClient

from .core import logger

# --- Constants ---
CATALOG = "yd_launchpad_final_classic_catalog"
SCHEMA = "genie_app"
WAREHOUSE_ID = "551addcb4415adb7"

_USERS_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`users`"
_SPACES_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`spaces`"
_CONVERSATIONS_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`conversations`"
_MESSAGES_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`messages`"
_IMAGES_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`images`"
_SESSIONS_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`sessions`"

# Server-side TTL caches
_user_cache: TTLCache = TTLCache(maxsize=256, ttl=300)  # 5 min
_space_list_cache: TTLCache = TTLCache(maxsize=256, ttl=30)  # 30s


def run_sql(ws: WorkspaceClient, sql: str) -> dict:
    """Execute SQL via the Databricks SQL Statements API."""
    return ws.api_client.do(
        "POST",
        "/api/2.0/sql/statements",
        body={"statement": sql, "warehouse_id": WAREHOUSE_ID, "wait_timeout": "50s"},
    )


def parse_sql_rows(result: dict) -> list[dict]:
    """Parse SQL statement API response into a list of row dicts."""
    if result.get("status", {}).get("state") != "SUCCEEDED":
        return []
    manifest = result.get("manifest", {})
    cols = [c["name"] for c in manifest.get("schema", {}).get("columns", [])]
    data_array = result.get("result", {}).get("data_array", [])
    return [dict(zip(cols, row)) for row in data_array]


def _escape(value: str) -> str:
    """Escape a string value for SQL single-quote literals."""
    return value.replace("\\", "\\\\").replace("'", "''")


def _now_iso() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------

def ensure_tables(ws: WorkspaceClient) -> None:
    """Create all application tables if they don't exist."""
    ddl_statements = [
        f"""
        CREATE TABLE IF NOT EXISTS {_USERS_TABLE} (
            user_id STRING,
            email STRING,
            username STRING,
            default_template STRING,
            preferences_json STRING,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {_SPACES_TABLE} (
            space_id STRING,
            owner_user_id STRING,
            company_name STRING,
            description STRING,
            schema_name STRING,
            space_type STRING,
            template_id STRING,
            logo_volume_path STRING,
            primary_color STRING,
            secondary_color STRING,
            accent_color STRING,
            chart_colors_json STRING,
            tables_json STRING,
            sample_questions_json STRING,
            warehouse_id STRING,
            is_active BOOLEAN,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {_CONVERSATIONS_TABLE} (
            conversation_id STRING,
            space_id STRING,
            user_id STRING,
            title STRING,
            message_count INT,
            is_archived BOOLEAN,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {_MESSAGES_TABLE} (
            message_id STRING,
            conversation_id STRING,
            user_id STRING,
            question STRING,
            status STRING,
            sql_text STRING,
            description STRING,
            is_clarification BOOLEAN,
            feedback_rating STRING,
            created_at TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {_IMAGES_TABLE} (
            image_id STRING,
            user_id STRING,
            space_id STRING,
            filename STRING,
            content_type STRING,
            volume_path STRING,
            size_bytes BIGINT,
            created_at TIMESTAMP
        )
        """,
    ]
    for ddl in ddl_statements:
        try:
            run_sql(ws, ddl)
        except Exception as e:
            logger.error("Failed to create table: %s", e)
            raise


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def get_or_create_user(
    ws: WorkspaceClient,
    user_id: str,
    email: str | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    """Get user by ID, creating if not found. Uses TTL cache."""
    cached = _user_cache.get(user_id)
    if cached:
        return cached

    safe_id = _escape(user_id)
    result = run_sql(ws, f"SELECT * FROM {_USERS_TABLE} WHERE user_id = '{safe_id}' LIMIT 1")
    rows = parse_sql_rows(result)

    if rows:
        user = rows[0]
        # Update email/username if changed
        updates = []
        if email and user.get("email") != email:
            updates.append(f"email = '{_escape(email)}'")
        if username and user.get("username") != username:
            updates.append(f"username = '{_escape(username)}'")
        if updates:
            now = _now_iso()
            updates.append(f"updated_at = '{now}'")
            run_sql(
                ws,
                f"UPDATE {_USERS_TABLE} SET {', '.join(updates)} WHERE user_id = '{safe_id}'",
            )
            user["email"] = email or user.get("email")
            user["username"] = username or user.get("username")
            user["updated_at"] = now
    else:
        now = _now_iso()
        safe_email = _escape(email or "")
        safe_username = _escape(username or "")
        run_sql(
            ws,
            f"""INSERT INTO {_USERS_TABLE}
                (user_id, email, username, default_template, preferences_json, created_at, updated_at)
                VALUES ('{safe_id}', '{safe_email}', '{safe_username}', 'simple', '{{}}'
                , '{now}', '{now}')""",
        )
        user = {
            "user_id": user_id,
            "email": email or "",
            "username": username or "",
            "default_template": "simple",
            "preferences_json": "{}",
            "created_at": now,
            "updated_at": now,
        }

    _user_cache[user_id] = user
    return user


def update_user_preferences(
    ws: WorkspaceClient,
    user_id: str,
    default_template: str | None = None,
    preferences: dict | None = None,
) -> dict[str, Any]:
    """Update user preferences. Returns updated user dict."""
    safe_id = _escape(user_id)
    updates = []
    now = _now_iso()

    if default_template is not None:
        updates.append(f"default_template = '{_escape(default_template)}'")
    if preferences is not None:
        updates.append(f"preferences_json = '{_escape(json.dumps(preferences))}'")

    if not updates:
        return get_or_create_user(ws, user_id)

    updates.append(f"updated_at = '{now}'")
    run_sql(
        ws,
        f"UPDATE {_USERS_TABLE} SET {', '.join(updates)} WHERE user_id = '{safe_id}'",
    )

    # Invalidate cache
    _user_cache.pop(user_id, None)
    return get_or_create_user(ws, user_id)
