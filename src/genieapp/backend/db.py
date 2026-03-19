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


def run_sql(ws: WorkspaceClient, sql: str, *, raise_on_error: bool = True) -> dict:
    """Execute SQL via the Databricks SQL Statements API.

    Args:
        ws: Databricks WorkspaceClient.
        sql: SQL statement to execute.
        raise_on_error: If True (default), raise RuntimeError on failed statements.

    Returns:
        Raw API response dict.

    Raises:
        RuntimeError: If the statement fails and raise_on_error is True.
    """
    result = ws.api_client.do(
        "POST",
        "/api/2.0/sql/statements",
        body={"statement": sql, "warehouse_id": WAREHOUSE_ID, "wait_timeout": "50s"},
    )
    state = result.get("status", {}).get("state", "")
    if raise_on_error and state not in ("SUCCEEDED", "RUNNING", "PENDING"):
        error_msg = result.get("status", {}).get("error", {}).get("message", "Unknown error")
        logger.error("SQL failed (%s): %s | SQL: %.200s", state, error_msg, sql)
        raise RuntimeError(f"SQL failed ({state}): {error_msg}")
    return result


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

    # Migrations — add starred columns to messages table (safe if already exists).
    # Delta tables don't support ADD COLUMN ... DEFAULT in one statement.
    migration_columns = [
        ("is_starred", "BOOLEAN"),
        ("starred_by", "STRING"),
    ]
    for col_name, col_type in migration_columns:
        try:
            run_sql(ws, f"ALTER TABLE {_MESSAGES_TABLE} ADD COLUMN {col_name} {col_type}")
        except (RuntimeError, Exception):
            pass  # Column already exists


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


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

def create_conversation(
    ws: WorkspaceClient,
    conversation_id: str,
    space_id: str,
    user_id: str,
    title: str,
) -> dict[str, Any]:
    """Insert a new conversation record."""
    now = _now_iso()
    safe_conv = _escape(conversation_id)
    safe_space = _escape(space_id)
    safe_user = _escape(user_id)
    safe_title = _escape(title[:200])
    run_sql(
        ws,
        f"""INSERT INTO {_CONVERSATIONS_TABLE}
            (conversation_id, space_id, user_id, title, message_count, is_archived, created_at, updated_at)
            VALUES ('{safe_conv}', '{safe_space}', '{safe_user}', '{safe_title}', 0, false, '{now}', '{now}')""",
    )
    return {
        "conversation_id": conversation_id,
        "space_id": space_id,
        "user_id": user_id,
        "title": title[:200],
        "message_count": 0,
        "is_archived": False,
        "created_at": now,
        "updated_at": now,
    }


def get_conversation(
    ws: WorkspaceClient,
    conversation_id: str,
) -> dict[str, Any] | None:
    """Get a single conversation by ID."""
    safe_conv = _escape(conversation_id)
    result = run_sql(
        ws,
        f"SELECT * FROM {_CONVERSATIONS_TABLE} WHERE conversation_id = '{safe_conv}' LIMIT 1",
    )
    rows = parse_sql_rows(result)
    return rows[0] if rows else None


def list_conversations(
    ws: WorkspaceClient,
    user_id: str,
    space_id: str | None = None,
) -> list[dict[str, Any]]:
    """List conversations for a user, optionally filtered by space_id."""
    safe_user = _escape(user_id)
    sql = f"SELECT * FROM {_CONVERSATIONS_TABLE} WHERE user_id = '{safe_user}' AND is_archived = false"
    if space_id:
        sql += f" AND space_id = '{_escape(space_id)}'"
    sql += " ORDER BY updated_at DESC LIMIT 100"
    result = run_sql(ws, sql)
    return parse_sql_rows(result)


def increment_conversation_message_count(
    ws: WorkspaceClient,
    conversation_id: str,
) -> None:
    """Increment the message count and update timestamp for a conversation."""
    safe_conv = _escape(conversation_id)
    now = _now_iso()
    run_sql(
        ws,
        f"""UPDATE {_CONVERSATIONS_TABLE}
            SET message_count = message_count + 1, updated_at = '{now}'
            WHERE conversation_id = '{safe_conv}'""",
    )


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def add_message(
    ws: WorkspaceClient,
    message_id: str,
    conversation_id: str,
    user_id: str,
    question: str,
    status: str = "SUBMITTED",
) -> dict[str, Any]:
    """Insert a new message record."""
    now = _now_iso()
    safe_msg = _escape(message_id)
    safe_conv = _escape(conversation_id)
    safe_user = _escape(user_id)
    safe_q = _escape(question)
    run_sql(
        ws,
        f"""INSERT INTO {_MESSAGES_TABLE}
            (message_id, conversation_id, user_id, question, status, sql_text, description, is_clarification, feedback_rating, created_at)
            VALUES ('{safe_msg}', '{safe_conv}', '{safe_user}', '{safe_q}', '{_escape(status)}', '', '', false, '', '{now}')""",
    )
    return {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "question": question,
        "status": status,
        "sql_text": "",
        "description": "",
        "is_clarification": False,
        "feedback_rating": "",
        "created_at": now,
    }


def update_message_result(
    ws: WorkspaceClient,
    message_id: str,
    conversation_id: str,
    status: str,
    sql_text: str = "",
    description: str = "",
    is_clarification: bool = False,
) -> None:
    """Update a message with result metadata after Genie completes."""
    safe_msg = _escape(message_id)
    safe_conv = _escape(conversation_id)
    run_sql(
        ws,
        f"""UPDATE {_MESSAGES_TABLE}
            SET status = '{_escape(status)}',
                sql_text = '{_escape(sql_text)}',
                description = '{_escape(description)}',
                is_clarification = {str(is_clarification).lower()}
            WHERE message_id = '{safe_msg}' AND conversation_id = '{safe_conv}'""",
    )


def get_conversation_messages(
    ws: WorkspaceClient,
    conversation_id: str,
) -> list[dict[str, Any]]:
    """Get all messages for a conversation, ordered by creation time."""
    safe_conv = _escape(conversation_id)
    result = run_sql(
        ws,
        f"SELECT * FROM {_MESSAGES_TABLE} WHERE conversation_id = '{safe_conv}' ORDER BY created_at ASC",
    )
    return parse_sql_rows(result)


def toggle_star_message(
    ws: WorkspaceClient,
    message_id: str,
    conversation_id: str,
    user_id: str,
    starred: bool,
) -> None:
    """Toggle the starred status of a message."""
    safe_msg = _escape(message_id)
    safe_conv = _escape(conversation_id)
    safe_user = _escape(user_id)
    run_sql(
        ws,
        f"""UPDATE {_MESSAGES_TABLE}
            SET is_starred = {str(starred).lower()},
                starred_by = '{safe_user}'
            WHERE message_id = '{safe_msg}' AND conversation_id = '{safe_conv}'""",
    )


def get_starred_messages(
    ws: WorkspaceClient,
    user_id: str,
    space_id: str,
) -> list[dict[str, Any]]:
    """Get starred messages for a user in a specific space."""
    safe_user = _escape(user_id)
    safe_space = _escape(space_id)
    result = run_sql(
        ws,
        f"""SELECT m.* FROM {_MESSAGES_TABLE} m
            JOIN {_CONVERSATIONS_TABLE} c ON m.conversation_id = c.conversation_id
            WHERE m.starred_by = '{safe_user}'
              AND m.is_starred = true
              AND c.space_id = '{safe_space}'
            ORDER BY m.created_at DESC
            LIMIT 50""",
    )
    return parse_sql_rows(result)


# ---------------------------------------------------------------------------
# Spaces
# ---------------------------------------------------------------------------

def create_space(
    ws: WorkspaceClient,
    space_id: str,
    owner_user_id: str,
    company_name: str,
    description: str = "",
    schema_name: str | None = None,
    space_type: str = "generated",
    template_id: str = "simple",
    logo_volume_path: str = "",
    primary_color: str = "#1a73e8",
    secondary_color: str = "#ea4335",
    accent_color: str = "",
    chart_colors: list[str] | None = None,
    tables_json: str = "[]",
    sample_questions_json: str = "[]",
    warehouse_id: str = "",
) -> dict[str, Any]:
    """Insert a new space record in the spaces table."""
    now = _now_iso()
    chart_colors_str = json.dumps(chart_colors or [])
    run_sql(
        ws,
        f"""INSERT INTO {_SPACES_TABLE}
            (space_id, owner_user_id, company_name, description, schema_name, space_type,
             template_id, logo_volume_path, primary_color, secondary_color, accent_color,
             chart_colors_json, tables_json, sample_questions_json, warehouse_id,
             is_active, created_at, updated_at)
            VALUES ('{_escape(space_id)}', '{_escape(owner_user_id)}', '{_escape(company_name)}',
                    '{_escape(description)}', '{_escape(schema_name or "")}', '{_escape(space_type)}',
                    '{_escape(template_id)}', '{_escape(logo_volume_path)}',
                    '{_escape(primary_color)}', '{_escape(secondary_color)}', '{_escape(accent_color)}',
                    '{_escape(chart_colors_str)}', '{_escape(tables_json)}',
                    '{_escape(sample_questions_json)}', '{_escape(warehouse_id)}',
                    true, '{now}', '{now}')""",
    )
    _space_list_cache.clear()
    return {
        "space_id": space_id,
        "owner_user_id": owner_user_id,
        "company_name": company_name,
        "description": description,
        "space_type": space_type,
        "template_id": template_id,
        "primary_color": primary_color,
        "secondary_color": secondary_color,
        "accent_color": accent_color,
        "chart_colors_json": chart_colors_str,
        "is_active": True,
        "created_at": now,
    }


def list_user_spaces(
    ws: WorkspaceClient,
    user_id: str,
) -> list[dict[str, Any]]:
    """List active spaces owned by a user."""
    cache_key = f"spaces:{user_id}"
    cached = _space_list_cache.get(cache_key)
    if cached is not None:
        return cached

    safe_user = _escape(user_id)
    result = run_sql(
        ws,
        f"SELECT * FROM {_SPACES_TABLE} WHERE owner_user_id = '{safe_user}' AND is_active = true ORDER BY created_at DESC",
    )
    rows = parse_sql_rows(result)
    _space_list_cache[cache_key] = rows
    return rows


def get_space(
    ws: WorkspaceClient,
    space_id: str,
) -> dict[str, Any] | None:
    """Get a single space by ID."""
    safe_id = _escape(space_id)
    result = run_sql(
        ws,
        f"SELECT * FROM {_SPACES_TABLE} WHERE space_id = '{safe_id}' AND is_active = true LIMIT 1",
    )
    rows = parse_sql_rows(result)
    return rows[0] if rows else None


def update_space_template(
    ws: WorkspaceClient,
    space_id: str,
    template_id: str,
) -> None:
    """Update the template_id for a space."""
    now = _now_iso()
    run_sql(
        ws,
        f"""UPDATE {_SPACES_TABLE}
            SET template_id = '{_escape(template_id)}', updated_at = '{now}'
            WHERE space_id = '{_escape(space_id)}'""",
    )
    _space_list_cache.clear()


def soft_delete_space(
    ws: WorkspaceClient,
    space_id: str,
) -> None:
    """Soft-delete a space by setting is_active = false."""
    now = _now_iso()
    run_sql(
        ws,
        f"""UPDATE {_SPACES_TABLE}
            SET is_active = false, updated_at = '{now}'
            WHERE space_id = '{_escape(space_id)}'""",
    )
    _space_list_cache.clear()
