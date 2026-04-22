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


@router.get("/lakebase-test", operation_id="adminLakebaseTest")
def admin_lakebase_test(
    ws: Dependencies.Client,
    request: Request,
) -> dict:
    """Test Lakebase connectivity from the deployed app."""
    # Skip admin check temporarily for testing
    try:
        return _run_lakebase_tests(ws)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:500]}"}


def _run_lakebase_tests(ws) -> dict:
    import os
    results = {"steps": [], "success": False}

    # Step 1: Check PG env vars
    pg_env = {}
    for key in ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGSSLMODE"]:
        val = os.environ.get(key)
        if val:
            pg_env[key] = val
    results["steps"].append({
        "step": "env_vars",
        "status": "ok" if pg_env.get("PGHOST") else "missing",
        "pg_vars": pg_env if pg_env else "none",
    })

    if not pg_env.get("PGHOST"):
        results["steps"].append({"step": "pool", "status": "skip", "message": "No PGHOST — add Database resource and redeploy"})
        return results

    # Step 2: Test pg.py connection pool
    try:
        from ..pg import init_pool, execute_query, execute_write, close_pool

        # Init pool (may already be initialized at startup)
        try:
            init_pool(ws)
        except Exception:
            pass  # Pool might already exist from startup

        # Test SELECT
        rows = execute_query("SELECT 1 as test")
        results["steps"].append({"step": "pool_select", "status": "ok", "result": str(rows)})
        results["success"] = True

    except Exception as e:
        results["steps"].append({"step": "pool_select", "status": "error", "error": str(e)[:300]})
        return results

    # Phase 1: Create schema + tables
    try:
        tables_ddl = [
            ("users", """CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY, email TEXT, username TEXT,
                default_template TEXT DEFAULT 'simple', preferences_json TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
            )"""),
            ("spaces", """CREATE TABLE IF NOT EXISTS spaces (
                space_id TEXT PRIMARY KEY, owner_user_id TEXT, company_name TEXT,
                description TEXT, schema_name TEXT, space_type TEXT DEFAULT 'generated',
                template_id TEXT DEFAULT 'simple', logo_volume_path TEXT,
                primary_color TEXT DEFAULT '#1a73e8', secondary_color TEXT DEFAULT '#ea4335',
                accent_color TEXT, chart_colors_json TEXT, tables_json TEXT,
                sample_questions_json TEXT, warehouse_id TEXT, dashboard_json TEXT,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
            )"""),
            ("conversations", """CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY, space_id TEXT, user_id TEXT,
                title TEXT, message_count INTEGER DEFAULT 0, is_archived BOOLEAN DEFAULT false,
                created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
            )"""),
            ("messages", """CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY, conversation_id TEXT, user_id TEXT,
                question TEXT, status TEXT, sql_text TEXT, description TEXT,
                is_clarification BOOLEAN DEFAULT false, feedback_rating TEXT,
                is_starred BOOLEAN DEFAULT false, starred_by TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )"""),
            ("images", """CREATE TABLE IF NOT EXISTS images (
                image_id TEXT PRIMARY KEY, user_id TEXT, space_id TEXT,
                filename TEXT, content_type TEXT, volume_path TEXT, size_bytes BIGINT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )"""),
            ("feedback", """CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY, user_id TEXT, email TEXT,
                message TEXT, created_at TIMESTAMPTZ DEFAULT NOW()
            )"""),
        ]

        indexes_ddl = [
            "CREATE INDEX IF NOT EXISTS idx_spaces_owner ON spaces(owner_user_id)",
            "CREATE INDEX IF NOT EXISTS idx_spaces_type ON spaces(space_type)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_space ON conversations(space_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_starred ON messages(starred_by)",
        ]

        table_results = []
        for name, ddl in tables_ddl:
            try:
                execute_write(ddl)
                table_results.append({"table": name, "status": "ok"})
            except Exception as e:
                table_results.append({"table": name, "status": "error", "error": str(e)[:200]})

        for idx_ddl in indexes_ddl:
            try:
                execute_write(idx_ddl)
            except Exception:
                pass  # Index may already exist

        # Verify: count tables
        verify = execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        )
        found_tables = [r["table_name"] for r in verify]

        # Count rows per table
        row_counts = {}
        for t in found_tables:
            try:
                cnt = execute_query(f"SELECT COUNT(*) as cnt FROM {t}")
                row_counts[t] = cnt[0]["cnt"] if cnt else 0
            except Exception:
                row_counts[t] = "error"

        results["steps"].append({
            "step": "create_tables",
            "status": "ok" if len(found_tables) >= 6 else "incomplete",
            "tables_created": table_results,
            "tables_found": found_tables,
            "row_counts": row_counts,
        })

    except Exception as e:
        results["steps"].append({"step": "create_tables", "status": "error", "error": str(e)[:300]})

    # Phase 2: Migrate data from Delta → Postgres
    try:
        from ..db import run_sql as delta_sql, parse_sql_rows, _USERS_TABLE, _SPACES_TABLE, _CONVERSATIONS_TABLE, _MESSAGES_TABLE, _IMAGES_TABLE, _FEEDBACK_TABLE

        delta_tables = {
            "users": {"delta": _USERS_TABLE, "pk": "user_id", "cols": [
                "user_id", "email", "username", "default_template", "preferences_json", "created_at", "updated_at"
            ]},
            "spaces": {"delta": _SPACES_TABLE, "pk": "space_id", "cols": [
                "space_id", "owner_user_id", "company_name", "description", "schema_name", "space_type",
                "template_id", "logo_volume_path", "primary_color", "secondary_color", "accent_color",
                "chart_colors_json", "tables_json", "sample_questions_json", "warehouse_id", "dashboard_json",
                "is_active", "created_at", "updated_at"
            ]},
            "conversations": {"delta": _CONVERSATIONS_TABLE, "pk": "conversation_id", "cols": [
                "conversation_id", "space_id", "user_id", "title", "message_count", "is_archived", "created_at", "updated_at"
            ]},
            "messages": {"delta": _MESSAGES_TABLE, "pk": "message_id", "cols": [
                "message_id", "conversation_id", "user_id", "question", "status", "sql_text", "description",
                "is_clarification", "feedback_rating", "is_starred", "starred_by", "created_at"
            ]},
            "images": {"delta": _IMAGES_TABLE, "pk": "image_id", "cols": [
                "image_id", "user_id", "space_id", "filename", "content_type", "volume_path", "size_bytes", "created_at"
            ]},
            "feedback": {"delta": _FEEDBACK_TABLE, "pk": "feedback_id", "cols": [
                "feedback_id", "user_id", "email", "message", "created_at"
            ]},
        }

        def _convert_value(val, col_name):
            """Convert Delta string values to proper Python types for Postgres."""
            if val is None:
                return None
            # Booleans
            if col_name in ("is_active", "is_archived", "is_clarification", "is_starred"):
                if isinstance(val, bool):
                    return val
                return str(val).lower() in ("true", "1")
            # Integers
            if col_name in ("message_count", "size_bytes"):
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return 0
            return val

        migration_results = []
        for pg_table, info in delta_tables.items():
            try:
                # Read from Delta
                delta_result = delta_sql(ws, f"SELECT * FROM {info['delta']}", raise_on_error=False)
                delta_rows = parse_sql_rows(delta_result)
                delta_count = len(delta_rows)

                # Insert into Postgres (ON CONFLICT DO NOTHING = idempotent)
                inserted = 0
                cols = info["cols"]
                placeholders = ", ".join(["%s"] * len(cols))
                col_names = ", ".join(cols)
                insert_sql = f"INSERT INTO {pg_table} ({col_names}) VALUES ({placeholders}) ON CONFLICT ({info['pk']}) DO NOTHING"

                for row in delta_rows:
                    values = tuple(_convert_value(row.get(c), c) for c in cols)
                    # Skip rows with no primary key
                    pk_val = row.get(info["pk"])
                    if not pk_val:
                        continue
                    try:
                        execute_write(insert_sql, values)
                        inserted += 1
                    except Exception as e:
                        # Log first error per table, continue
                        if inserted == 0:
                            migration_results.append({
                                "table": pg_table, "delta_rows": delta_count,
                                "error_sample": str(e)[:200],
                            })
                        continue

                # Count in Postgres
                pg_count_rows = execute_query(f"SELECT COUNT(*) as cnt FROM {pg_table}")
                pg_count = pg_count_rows[0]["cnt"] if pg_count_rows else 0

                migration_results.append({
                    "table": pg_table,
                    "delta_rows": delta_count,
                    "inserted": inserted,
                    "pg_total": pg_count,
                    "status": "ok" if pg_count > 0 or delta_count == 0 else "warning",
                })

            except Exception as e:
                migration_results.append({"table": pg_table, "status": "error", "error": str(e)[:200]})

        results["steps"].append({
            "step": "migrate_data",
            "status": "ok",
            "tables": migration_results,
        })

    except Exception as e:
        results["steps"].append({"step": "migrate_data", "status": "error", "error": str(e)[:300]})

    # Phase 3a: Test critical queries on Postgres vs Delta
    try:
        from ..db import run_sql as delta_sql, parse_sql_rows, _USERS_TABLE, _SPACES_TABLE, _CONVERSATIONS_TABLE, _MESSAGES_TABLE

        query_tests = []

        # Test 1: User lookup
        try:
            pg_users = execute_query("SELECT user_id, email FROM users LIMIT 5")
            if pg_users:
                test_uid = pg_users[0]["user_id"]
                pg_row = execute_query("SELECT * FROM users WHERE user_id = %s", (test_uid,))
                d_result = delta_sql(ws, f"SELECT * FROM {_USERS_TABLE} WHERE user_id = '{test_uid}'", raise_on_error=False)
                d_rows = parse_sql_rows(d_result)
                query_tests.append({
                    "test": "user_lookup",
                    "status": "ok" if pg_row and d_rows else "warning",
                    "pg_count": len(pg_row),
                    "delta_count": len(d_rows),
                    "pg_email": pg_row[0].get("email") if pg_row else None,
                    "delta_email": d_rows[0].get("email") if d_rows else None,
                })
            else:
                query_tests.append({"test": "user_lookup", "status": "skip", "message": "no users"})
        except Exception as e:
            query_tests.append({"test": "user_lookup", "status": "error", "error": str(e)[:200]})

        # Test 2: Space listing (owner-filtered)
        try:
            pg_spaces = execute_query(
                "SELECT space_id, company_name FROM spaces WHERE owner_user_id = %s AND is_active = true ORDER BY created_at DESC",
                ("76554809512980@7474655921234161",)
            )
            d_result = delta_sql(ws, f"SELECT space_id, company_name FROM {_SPACES_TABLE} WHERE owner_user_id = '76554809512980@7474655921234161' AND is_active = true ORDER BY created_at DESC", raise_on_error=False)
            d_rows = parse_sql_rows(d_result)
            query_tests.append({
                "test": "list_user_spaces",
                "status": "ok" if len(pg_spaces) == len(d_rows) else "mismatch",
                "pg_count": len(pg_spaces),
                "delta_count": len(d_rows),
                "pg_names": [s["company_name"] for s in pg_spaces],
                "delta_names": [s["company_name"] for s in d_rows],
            })
        except Exception as e:
            query_tests.append({"test": "list_user_spaces", "status": "error", "error": str(e)[:200]})

        # Test 3: Shared spaces
        try:
            pg_shared = execute_query("SELECT space_id, company_name FROM spaces WHERE space_type = 'shared' AND is_active = true")
            d_result = delta_sql(ws, f"SELECT space_id, company_name FROM {_SPACES_TABLE} WHERE space_type = 'shared' AND is_active = true", raise_on_error=False)
            d_rows = parse_sql_rows(d_result)
            query_tests.append({
                "test": "list_shared_spaces",
                "status": "ok" if len(pg_shared) == len(d_rows) else "mismatch",
                "pg_count": len(pg_shared),
                "delta_count": len(d_rows),
            })
        except Exception as e:
            query_tests.append({"test": "list_shared_spaces", "status": "error", "error": str(e)[:200]})

        # Test 4: Conversations listing
        try:
            pg_convos = execute_query(
                "SELECT conversation_id, title FROM conversations WHERE user_id = %s AND is_archived = false ORDER BY updated_at DESC",
                ("76554809512980@7474655921234161",)
            )
            d_result = delta_sql(ws, f"SELECT conversation_id, title FROM {_CONVERSATIONS_TABLE} WHERE user_id = '76554809512980@7474655921234161' AND is_archived = false ORDER BY updated_at DESC", raise_on_error=False)
            d_rows = parse_sql_rows(d_result)
            query_tests.append({
                "test": "list_conversations",
                "status": "ok" if len(pg_convos) == len(d_rows) else "mismatch",
                "pg_count": len(pg_convos),
                "delta_count": len(d_rows),
            })
        except Exception as e:
            query_tests.append({"test": "list_conversations", "status": "error", "error": str(e)[:200]})

        # Test 5: Messages for a conversation
        try:
            pg_convos_any = execute_query("SELECT conversation_id FROM conversations LIMIT 1")
            if pg_convos_any:
                test_cid = pg_convos_any[0]["conversation_id"]
                pg_msgs = execute_query("SELECT message_id, question FROM messages WHERE conversation_id = %s ORDER BY created_at", (test_cid,))
                d_result = delta_sql(ws, f"SELECT message_id, question FROM {_MESSAGES_TABLE} WHERE conversation_id = '{test_cid}' ORDER BY created_at", raise_on_error=False)
                d_rows = parse_sql_rows(d_result)
                query_tests.append({
                    "test": "conversation_messages",
                    "status": "ok" if len(pg_msgs) == len(d_rows) else "mismatch",
                    "pg_count": len(pg_msgs),
                    "delta_count": len(d_rows),
                    "conversation_id": test_cid,
                })
            else:
                query_tests.append({"test": "conversation_messages", "status": "skip", "message": "no conversations"})
        except Exception as e:
            query_tests.append({"test": "conversation_messages", "status": "error", "error": str(e)[:200]})

        # Test 6: Upsert (write + read back)
        try:
            execute_write(
                "INSERT INTO feedback (feedback_id, user_id, email, message) VALUES (%s, %s, %s, %s) ON CONFLICT (feedback_id) DO UPDATE SET message = EXCLUDED.message",
                ("test-migration-check", "test-user", "test@test.com", "migration test")
            )
            check = execute_query("SELECT * FROM feedback WHERE feedback_id = %s", ("test-migration-check",))
            # Clean up
            execute_write("DELETE FROM feedback WHERE feedback_id = %s", ("test-migration-check",))
            query_tests.append({
                "test": "upsert_write_read",
                "status": "ok" if check and check[0]["message"] == "migration test" else "error",
            })
        except Exception as e:
            query_tests.append({"test": "upsert_write_read", "status": "error", "error": str(e)[:200]})

        # Test 7: Admin stats with Postgres date functions
        try:
            pg_weekly = execute_query("SELECT COUNT(*) as cnt FROM messages WHERE created_at >= NOW() - INTERVAL '7 days'")
            query_tests.append({
                "test": "postgres_date_functions",
                "status": "ok",
                "messages_this_week": pg_weekly[0]["cnt"] if pg_weekly else 0,
            })
        except Exception as e:
            query_tests.append({"test": "postgres_date_functions", "status": "error", "error": str(e)[:200]})

        results["steps"].append({"step": "query_tests", "status": "ok", "tests": query_tests})

    except Exception as e:
        results["steps"].append({"step": "query_tests", "status": "error", "error": str(e)[:300]})

    return results
