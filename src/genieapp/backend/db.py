"""Centralized data access layer — Lakebase Postgres for app state, Delta for pipeline/sessions."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from cachetools import TTLCache
from databricks.sdk import WorkspaceClient

from .core import logger
from .pg import execute_query, execute_write

# --- Constants (kept for Delta operations: sessions, pipeline, genie re-execution) ---
CATALOG = "yd_launchpad_final_classic_catalog"
SCHEMA = "genie_app"
WAREHOUSE_ID = "fc62b388f737b2d3"

_USERS_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`users`"
_SPACES_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`spaces`"
_CONVERSATIONS_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`conversations`"
_MESSAGES_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`messages`"
_IMAGES_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`images`"
_SESSIONS_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`sessions`"
_FEEDBACK_TABLE = f"`{CATALOG}`.`{SCHEMA}`.`feedback`"

# Server-side TTL caches (kept but less critical with Postgres speed)
_user_cache: TTLCache = TTLCache(maxsize=256, ttl=300)
_space_list_cache: TTLCache = TTLCache(maxsize=256, ttl=30)


# ---------------------------------------------------------------------------
# Delta helpers (kept for sessions table, pipeline, genie re-execution)
# ---------------------------------------------------------------------------

def run_sql(ws: WorkspaceClient, sql: str, *, raise_on_error: bool = True) -> dict:
    """Execute SQL via the Databricks SQL Statements API (Delta tables only)."""
    import time
    max_retries = 2
    for attempt in range(max_retries + 1):
        result = ws.api_client.do(
            "POST",
            "/api/2.0/sql/statements",
            body={"statement": sql, "warehouse_id": WAREHOUSE_ID, "wait_timeout": "50s"},
        )
        state = result.get("status", {}).get("state", "")
        if state in ("SUCCEEDED", "RUNNING", "PENDING"):
            return result
        if attempt < max_retries:
            logger.warning("SQL attempt %d failed (%s) — retrying", attempt + 1, state)
            time.sleep(2)
            continue
        if raise_on_error:
            error_msg = result.get("status", {}).get("error", {}).get("message", "Unknown error")
            logger.error("SQL failed after %d attempts: %s", max_retries + 1, error_msg)
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
    """Escape a string value for SQL single-quote literals (Delta only)."""
    return value.replace("\\", "\\\\").replace("'", "''")


def _now_iso() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Table creation (Delta — kept for backward compat, Postgres tables created manually)
# ---------------------------------------------------------------------------

def ensure_tables(ws: WorkspaceClient) -> None:
    """Create Delta application tables if they don't exist (backward compat)."""
    ddl_statements = [
        f"CREATE TABLE IF NOT EXISTS {_USERS_TABLE} (user_id STRING, email STRING, username STRING, default_template STRING, preferences_json STRING, created_at TIMESTAMP, updated_at TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS {_SPACES_TABLE} (space_id STRING, owner_user_id STRING, company_name STRING, description STRING, schema_name STRING, space_type STRING, template_id STRING, logo_volume_path STRING, primary_color STRING, secondary_color STRING, accent_color STRING, chart_colors_json STRING, tables_json STRING, sample_questions_json STRING, warehouse_id STRING, is_active BOOLEAN, created_at TIMESTAMP, updated_at TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS {_CONVERSATIONS_TABLE} (conversation_id STRING, space_id STRING, user_id STRING, title STRING, message_count INT, is_archived BOOLEAN, created_at TIMESTAMP, updated_at TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS {_MESSAGES_TABLE} (message_id STRING, conversation_id STRING, user_id STRING, question STRING, status STRING, sql_text STRING, description STRING, is_clarification BOOLEAN, feedback_rating STRING, created_at TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS {_IMAGES_TABLE} (image_id STRING, user_id STRING, space_id STRING, filename STRING, content_type STRING, volume_path STRING, size_bytes BIGINT, created_at TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS {_FEEDBACK_TABLE} (feedback_id STRING, user_id STRING, email STRING, message STRING, created_at TIMESTAMP)",
    ]
    for ddl in ddl_statements:
        try:
            run_sql(ws, ddl)
        except Exception as e:
            logger.error("Failed to create table: %s", e)
            raise

    # Migrations
    for col_name, col_type in [("is_starred", "BOOLEAN"), ("starred_by", "STRING")]:
        try:
            run_sql(ws, f"ALTER TABLE {_MESSAGES_TABLE} ADD COLUMN {col_name} {col_type}")
        except (RuntimeError, Exception):
            pass
    for table in [_SESSIONS_TABLE, _SPACES_TABLE]:
        try:
            run_sql(ws, f"ALTER TABLE {table} ADD COLUMN dashboard_json STRING")
        except (RuntimeError, Exception):
            pass


# ---------------------------------------------------------------------------
# Users (Postgres)
# ---------------------------------------------------------------------------

def get_or_create_user(
    ws: WorkspaceClient,
    user_id: str,
    email: str | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    """Get user by ID, creating if not found."""
    cached = _user_cache.get(user_id)
    if cached:
        return cached

    rows = execute_query("SELECT * FROM users WHERE user_id = %s LIMIT 1", (user_id,))
    if rows:
        user = dict(rows[0])
        updates = []
        params = []
        if email and user.get("email") != email:
            updates.append("email = %s")
            params.append(email)
        if username and user.get("username") != username:
            updates.append("username = %s")
            params.append(username)
        if updates:
            updates.append("updated_at = NOW()")
            params.append(user_id)
            execute_write(f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s", tuple(params))
            user["email"] = email or user.get("email")
            user["username"] = username or user.get("username")
    else:
        execute_write(
            "INSERT INTO users (user_id, email, username, default_template, preferences_json, created_at, updated_at) VALUES (%s, %s, %s, 'simple', '{}', NOW(), NOW()) ON CONFLICT (user_id) DO NOTHING",
            (user_id, email or "", username or ""),
        )
        user = {"user_id": user_id, "email": email or "", "username": username or "", "default_template": "simple", "preferences_json": "{}"}

    _user_cache[user_id] = user
    return user


def update_user_preferences(
    ws: WorkspaceClient,
    user_id: str,
    default_template: str | None = None,
    preferences: dict | None = None,
) -> dict[str, Any]:
    """Update user preferences."""
    updates = []
    params = []
    if default_template is not None:
        updates.append("default_template = %s")
        params.append(default_template)
    if preferences is not None:
        updates.append("preferences_json = %s")
        params.append(json.dumps(preferences))
    if not updates:
        return get_or_create_user(ws, user_id)

    updates.append("updated_at = NOW()")
    params.append(user_id)
    execute_write(f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s", tuple(params))
    _user_cache.pop(user_id, None)
    return get_or_create_user(ws, user_id)


# ---------------------------------------------------------------------------
# Conversations (Postgres)
# ---------------------------------------------------------------------------

def create_conversation(
    ws: WorkspaceClient,
    conversation_id: str,
    space_id: str,
    user_id: str,
    title: str,
) -> dict[str, Any]:
    """Insert a new conversation record."""
    execute_write(
        "INSERT INTO conversations (conversation_id, space_id, user_id, title, message_count, is_archived, created_at, updated_at) VALUES (%s, %s, %s, %s, 0, false, NOW(), NOW()) ON CONFLICT (conversation_id) DO NOTHING",
        (conversation_id, space_id, user_id, title[:200]),
    )
    return {"conversation_id": conversation_id, "space_id": space_id, "user_id": user_id, "title": title[:200], "message_count": 0, "is_archived": False}


def get_conversation(
    ws: WorkspaceClient,
    conversation_id: str,
) -> dict[str, Any] | None:
    """Get a single conversation by ID."""
    rows = execute_query("SELECT * FROM conversations WHERE conversation_id = %s LIMIT 1", (conversation_id,))
    return dict(rows[0]) if rows else None


def list_conversations(
    ws: WorkspaceClient,
    user_id: str,
    space_id: str | None = None,
) -> list[dict[str, Any]]:
    """List conversations for a user, optionally filtered by space_id."""
    if space_id:
        return execute_query(
            "SELECT * FROM conversations WHERE user_id = %s AND is_archived = false AND space_id = %s ORDER BY updated_at DESC LIMIT 100",
            (user_id, space_id),
        )
    return execute_query(
        "SELECT * FROM conversations WHERE user_id = %s AND is_archived = false ORDER BY updated_at DESC LIMIT 100",
        (user_id,),
    )


def increment_conversation_message_count(
    ws: WorkspaceClient,
    conversation_id: str,
) -> None:
    """Increment the message count and update timestamp."""
    execute_write(
        "UPDATE conversations SET message_count = message_count + 1, updated_at = NOW() WHERE conversation_id = %s",
        (conversation_id,),
    )


# ---------------------------------------------------------------------------
# Messages (Postgres)
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
    execute_write(
        "INSERT INTO messages (message_id, conversation_id, user_id, question, status, sql_text, description, is_clarification, feedback_rating, created_at) VALUES (%s, %s, %s, %s, %s, '', '', false, '', NOW()) ON CONFLICT (message_id) DO NOTHING",
        (message_id, conversation_id, user_id, question, status),
    )
    return {"message_id": message_id, "conversation_id": conversation_id, "user_id": user_id, "question": question, "status": status}


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
    execute_write(
        "UPDATE messages SET status = %s, sql_text = %s, description = %s, is_clarification = %s WHERE message_id = %s AND conversation_id = %s",
        (status, sql_text, description, is_clarification, message_id, conversation_id),
    )


def get_conversation_messages(
    ws: WorkspaceClient,
    conversation_id: str,
) -> list[dict[str, Any]]:
    """Get all messages for a conversation, ordered by creation time."""
    return execute_query(
        "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
        (conversation_id,),
    )


def get_message(
    ws: WorkspaceClient,
    conversation_id: str,
    message_id: str,
) -> dict[str, Any] | None:
    """Get a single message by conversation + message ID."""
    rows = execute_query(
        "SELECT * FROM messages WHERE conversation_id = %s AND message_id = %s LIMIT 1",
        (conversation_id, message_id),
    )
    return dict(rows[0]) if rows else None


def toggle_star_message(
    ws: WorkspaceClient,
    message_id: str,
    conversation_id: str,
    user_id: str,
    starred: bool,
) -> None:
    """Toggle the starred status of a message."""
    execute_write(
        "UPDATE messages SET is_starred = %s, starred_by = %s WHERE message_id = %s AND conversation_id = %s",
        (starred, user_id, message_id, conversation_id),
    )


def get_starred_messages(
    ws: WorkspaceClient,
    user_id: str,
    space_id: str,
) -> list[dict[str, Any]]:
    """Get starred messages for a user in a specific space."""
    return execute_query(
        """SELECT m.* FROM messages m
           JOIN conversations c ON m.conversation_id = c.conversation_id
           WHERE m.starred_by = %s AND m.is_starred = true AND c.space_id = %s
           ORDER BY m.created_at DESC LIMIT 50""",
        (user_id, space_id),
    )


# ---------------------------------------------------------------------------
# Spaces (Postgres)
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
    """Insert a new space record."""
    chart_colors_str = json.dumps(chart_colors or [])
    now = _now_iso()
    execute_write(
        """INSERT INTO spaces (space_id, owner_user_id, company_name, description, schema_name, space_type,
           template_id, logo_volume_path, primary_color, secondary_color, accent_color,
           chart_colors_json, tables_json, sample_questions_json, warehouse_id,
           is_active, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, NOW(), NOW())
           ON CONFLICT (space_id) DO NOTHING""",
        (space_id, owner_user_id, company_name, description, schema_name or "", space_type,
         template_id, logo_volume_path, primary_color, secondary_color, accent_color,
         chart_colors_str, tables_json, sample_questions_json, warehouse_id),
    )
    _space_list_cache.clear()
    return {
        "space_id": space_id, "owner_user_id": owner_user_id, "company_name": company_name,
        "description": description, "space_type": space_type, "template_id": template_id,
        "primary_color": primary_color, "secondary_color": secondary_color,
        "accent_color": accent_color, "chart_colors_json": chart_colors_str,
        "is_active": True, "created_at": now,
    }


def list_user_spaces(
    ws: WorkspaceClient,
    user_id: str,
) -> list[dict[str, Any]]:
    """List active spaces owned by a user (excludes shared)."""
    cache_key = f"spaces:{user_id}"
    cached = _space_list_cache.get(cache_key)
    if cached is not None:
        return cached
    rows = execute_query(
        "SELECT * FROM spaces WHERE owner_user_id = %s AND is_active = true AND (space_type IS NULL OR space_type != 'shared') ORDER BY created_at DESC",
        (user_id,),
    )
    _space_list_cache[cache_key] = rows
    return rows


def list_shared_spaces(
    ws: WorkspaceClient,
) -> list[dict[str, Any]]:
    """List all shared spaces."""
    cache_key = "spaces:shared"
    cached = _space_list_cache.get(cache_key)
    if cached is not None:
        return cached
    rows = execute_query("SELECT * FROM spaces WHERE space_type = 'shared' AND is_active = true ORDER BY created_at DESC")
    _space_list_cache[cache_key] = rows
    return rows


def get_space(
    ws: WorkspaceClient,
    space_id: str,
) -> dict[str, Any] | None:
    """Get a single space by ID."""
    rows = execute_query("SELECT * FROM spaces WHERE space_id = %s AND is_active = true LIMIT 1", (space_id,))
    return dict(rows[0]) if rows else None


def update_space_template(
    ws: WorkspaceClient,
    space_id: str,
    template_id: str,
) -> None:
    """Update the template_id for a space."""
    execute_write("UPDATE spaces SET template_id = %s, updated_at = NOW() WHERE space_id = %s", (template_id, space_id))
    _space_list_cache.clear()


def soft_delete_space(
    ws: WorkspaceClient,
    space_id: str,
) -> None:
    """Soft-delete a space."""
    execute_write("UPDATE spaces SET is_active = false, updated_at = NOW() WHERE space_id = %s", (space_id,))
    _space_list_cache.clear()


# ---------------------------------------------------------------------------
# Dashboard (Hybrid: Postgres spaces + Delta sessions fallback)
# ---------------------------------------------------------------------------

def get_dashboard_data(
    ws: WorkspaceClient,
    space_id: str,
) -> dict | None:
    """Get dashboard JSON. Checks Postgres spaces first, then Delta sessions."""
    # Try Postgres spaces table
    rows = execute_query("SELECT dashboard_json FROM spaces WHERE space_id = %s AND is_active = true LIMIT 1", (space_id,))
    if rows and rows[0].get("dashboard_json"):
        try:
            return json.loads(rows[0]["dashboard_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback to Delta sessions table
    try:
        result = run_sql(ws, f"SELECT dashboard_json FROM {_SESSIONS_TABLE} WHERE space_id = '{_escape(space_id)}' LIMIT 1", raise_on_error=False)
        delta_rows = parse_sql_rows(result)
        if delta_rows and delta_rows[0].get("dashboard_json"):
            return json.loads(delta_rows[0]["dashboard_json"])
    except (json.JSONDecodeError, TypeError, Exception):
        pass

    return None


# ---------------------------------------------------------------------------
# Admin queries (Postgres)
# ---------------------------------------------------------------------------

ADMIN_USER_IDS = {"76554809512980@7474655921234161"}


def is_admin(user_id: str) -> bool:
    """Check if user is an admin."""
    return user_id in ADMIN_USER_IDS


def get_admin_stats(ws: WorkspaceClient) -> dict[str, Any]:
    """Get aggregate KPI stats."""
    stats: dict[str, Any] = {}
    queries = [
        ("total_users", "SELECT COUNT(DISTINCT email) as cnt FROM users WHERE email IS NOT NULL AND email != ''"),
        ("total_spaces", "SELECT COUNT(*) as cnt FROM spaces WHERE is_active = true"),
        ("total_conversations", "SELECT COUNT(*) as cnt FROM conversations"),
        ("total_messages", "SELECT COUNT(*) as cnt FROM messages"),
        ("messages_this_week", "SELECT COUNT(*) as cnt FROM messages WHERE created_at >= NOW() - INTERVAL '7 days'"),
        ("active_users_this_week", "SELECT COUNT(DISTINCT user_id) as cnt FROM messages WHERE created_at >= NOW() - INTERVAL '7 days'"),
    ]
    for key, sql in queries:
        try:
            rows = execute_query(sql)
            stats[key] = int(rows[0]["cnt"]) if rows else 0
        except Exception:
            stats[key] = 0
    return stats


def get_usage_trend(ws: WorkspaceClient, days: int = 30) -> list[dict[str, Any]]:
    """Get messages per day for the last N days."""
    try:
        return execute_query(
            "SELECT DATE(created_at) as day, COUNT(*) as count FROM messages WHERE created_at >= NOW() - INTERVAL '%s days' GROUP BY DATE(created_at) ORDER BY day",
            (days,),
        )
    except Exception:
        return []


def get_all_users_with_activity(ws: WorkspaceClient) -> list[dict[str, Any]]:
    """Get all users with activity metrics, deduped by email."""
    try:
        users = execute_query("""
            SELECT
                MIN(u.user_id) as user_id,
                u.email,
                MIN(u.username) as username,
                MIN(u.created_at) as joined,
                MAX(u.updated_at) as last_active
            FROM users u
            WHERE u.email IS NOT NULL AND u.email != ''
            GROUP BY u.email
            ORDER BY last_active DESC
        """)
    except Exception:
        return []

    for u in users:
        try:
            r = execute_query(
                "SELECT COUNT(*) as cnt FROM spaces WHERE owner_user_id IN (SELECT user_id FROM users WHERE email = %s) AND is_active = true",
                (u.get("email", ""),),
            )
            u["spaces_created"] = int(r[0]["cnt"]) if r else 0
        except Exception:
            u["spaces_created"] = 0

    return users


def get_all_spaces_with_stats(ws: WorkspaceClient) -> list[dict[str, Any]]:
    """Get all spaces with owner info and message counts."""
    try:
        return execute_query("""
            SELECT
                sp.space_id, sp.company_name, sp.owner_user_id, sp.space_type,
                sp.template_id, sp.created_at,
                COALESCE((SELECT u.email FROM users u WHERE u.user_id = sp.owner_user_id LIMIT 1), sp.owner_user_id) as owner_email,
                (SELECT COUNT(*) FROM messages m WHERE m.conversation_id IN (
                    SELECT c.conversation_id FROM conversations c WHERE c.space_id = sp.space_id
                )) as message_count
            FROM spaces sp
            WHERE sp.is_active = true
            ORDER BY sp.created_at DESC
        """)
    except Exception:
        return []


def set_space_shared(ws: WorkspaceClient, space_id: str, shared: bool) -> None:
    """Toggle a space's shared status."""
    new_type = "shared" if shared else "generated"
    execute_write("UPDATE spaces SET space_type = %s, updated_at = NOW() WHERE space_id = %s", (new_type, space_id))
    _space_list_cache.clear()


# ---------------------------------------------------------------------------
# Feedback (Postgres)
# ---------------------------------------------------------------------------

def submit_feedback(
    ws: WorkspaceClient,
    user_id: str,
    email: str,
    message: str,
) -> str:
    """Store user feedback."""
    feedback_id = uuid.uuid4().hex
    execute_write(
        "INSERT INTO feedback (feedback_id, user_id, email, message, created_at) VALUES (%s, %s, %s, %s, NOW())",
        (feedback_id, user_id, email, message),
    )
    return feedback_id
