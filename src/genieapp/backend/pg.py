"""Lakebase Postgres connection pool for fast app state queries."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras
import psycopg2.pool
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def init_pool(ws: WorkspaceClient) -> None:
    """Initialize the Postgres connection pool using PG env vars and OAuth token.

    Args:
        ws: WorkspaceClient used to obtain the OAuth JWT for authentication.
    """
    global _pool

    host = os.environ.get("PGHOST")
    port = os.environ.get("PGPORT", "5432")
    dbname = os.environ.get("PGDATABASE", "databricks_postgres")
    user = os.environ.get("PGUSER", "")
    sslmode = os.environ.get("PGSSLMODE", "require")

    if not host:
        raise RuntimeError("PGHOST env var not set — Lakebase database resource not configured")

    # OAuth JWT token as password
    auth_header = ws.config.authenticate()
    token = auth_header.get("Authorization", "").replace("Bearer ", "")

    _pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        host=host,
        port=int(port),
        dbname=dbname,
        user=user,
        password=token,
        sslmode=sslmode,
        connect_timeout=10,
    )
    logger.info("Postgres pool initialized (%s:%s/%s)", host, port, dbname)


@contextmanager
def get_conn():
    """Get a connection from the pool. Auto-returns on exit, rolls back on error."""
    if _pool is None:
        raise RuntimeError("Postgres pool not initialized — call init_pool() first")
    conn = _pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def execute_query(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """Execute a SELECT query and return rows as list of dicts.

    Args:
        sql: SQL query with %s placeholders.
        params: Parameter tuple for query placeholders.

    Returns:
        List of row dicts.
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]


def execute_write(sql: str, params: tuple | None = None) -> list[dict[str, Any]] | None:
    """Execute an INSERT/UPDATE/DELETE and commit. Optionally returns rows (for RETURNING).

    Args:
        sql: SQL statement with %s placeholders.
        params: Parameter tuple for placeholders.

    Returns:
        List of row dicts if the query has RETURNING, otherwise None.
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            conn.commit()
            if cur.description:
                return [dict(row) for row in cur.fetchall()]
            return None


def close_pool() -> None:
    """Close all connections in the pool."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Postgres pool closed")
