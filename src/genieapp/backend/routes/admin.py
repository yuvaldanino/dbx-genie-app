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

    # Step 1: Check for PG* env vars (injected by Databricks App resource binding)
    pg_env = {}
    for key in ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGSSLMODE", "PGPASSWORD"]:
        val = os.environ.get(key)
        if val:
            pg_env[key] = val if key != "PGPASSWORD" else val[:20] + "..."
    # Also check for any DB_ or DATABASE_ env vars
    db_env = {k: v[:50] for k, v in os.environ.items() if any(kw in k.upper() for kw in ["PG", "POSTGRES", "DATABASE", "LAKEBASE"])}
    results["steps"].append({
        "step": "env_vars",
        "status": "ok" if pg_env else "missing",
        "pg_vars": pg_env if pg_env else "none",
        "all_db_vars": db_env if db_env else "none",
    })

    # Step 2: Check available Postgres libraries
    pg_libs = []
    for lib in ["psycopg2", "psycopg", "pg8000", "asyncpg", "sqlalchemy"]:
        try:
            mod = __import__(lib)
            ver = getattr(mod, "__version__", getattr(mod, "version", "unknown"))
            pg_libs.append(f"{lib}=={ver}")
        except ImportError:
            pass
    results["steps"].append({"step": "pg_libs", "status": "ok" if pg_libs else "none", "available": pg_libs if pg_libs else "none"})

    # Step 3: Try connecting with env vars + any available library
    if pg_env.get("PGHOST"):
        host = os.environ.get("PGHOST")
        port = os.environ.get("PGPORT", "5432")
        dbname = os.environ.get("PGDATABASE", "databricks_postgres")
        user = os.environ.get("PGUSER", "")
        sslmode = os.environ.get("PGSSLMODE", "require")

        # Get OAuth token for password
        try:
            auth_header = ws.config.authenticate()
            token = auth_header.get("Authorization", "").replace("Bearer ", "")
            results["steps"].append({"step": "auth_token", "status": "ok", "type": "OAuth/JWT" if token.startswith("eyJ") else "PAT"})
        except Exception as e:
            token = ""
            results["steps"].append({"step": "auth_token", "status": "error", "error": str(e)[:200]})

        # Try psycopg (v3)
        try:
            import psycopg
            conn = psycopg.connect(
                host=host, port=int(port), dbname=dbname,
                user=user, password=token, sslmode=sslmode,
                connect_timeout=10,
            )
            cur = conn.execute("SELECT 1 as test")
            row = cur.fetchone()
            cur.close()
            conn.close()
            results["steps"].append({"step": "psycopg3_connect", "status": "ok", "result": str(row)})
            results["success"] = True
        except ImportError:
            results["steps"].append({"step": "psycopg3_connect", "status": "skip", "message": "not installed"})
        except Exception as e:
            results["steps"].append({"step": "psycopg3_connect", "status": "error", "error": str(e)[:300]})

        # Try psycopg2
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=host, port=port, dbname=dbname,
                user=user, password=token, sslmode=sslmode,
                connect_timeout=10,
            )
            cur = conn.cursor()
            cur.execute("SELECT 1 as test")
            row = cur.fetchone()
            cur.close()
            conn.close()
            results["steps"].append({"step": "psycopg2_connect", "status": "ok", "result": str(row)})
            results["success"] = True
        except ImportError:
            results["steps"].append({"step": "psycopg2_connect", "status": "skip", "message": "not installed"})
        except Exception as e:
            results["steps"].append({"step": "psycopg2_connect", "status": "error", "error": str(e)[:300]})

        # Try pg8000 (pure Python)
        try:
            import pg8000
            conn = pg8000.connect(
                host=host, port=int(port), database=dbname,
                user=user, password=token, ssl_context=True,
            )
            cur = conn.cursor()
            cur.execute("SELECT 1 as test")
            row = cur.fetchone()
            cur.close()
            conn.close()
            results["steps"].append({"step": "pg8000_connect", "status": "ok", "result": str(row)})
            results["success"] = True
        except ImportError:
            results["steps"].append({"step": "pg8000_connect", "status": "skip", "message": "not installed"})
        except Exception as e:
            results["steps"].append({"step": "pg8000_connect", "status": "error", "error": str(e)[:300]})

    else:
        results["steps"].append({"step": "connect", "status": "skip", "message": "No PGHOST env var — redeploy the app after adding the Database resource"})

    return results
