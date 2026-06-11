"""Lakebase Postgres connection pool with per-connection OAuth token refresh.

The Databricks OAuth token used as the Postgres password expires (~1 hour).
A pool that captures the token once at startup will eventually fail when
connections drop and need to reopen with a stale credential.

This pool:
  - Mints a fresh token before every NEW connection (with a short TTL cache
    to avoid hammering the auth endpoint on bursty traffic).
  - Validates pooled connections on checkout (`SELECT 1`).
  - Evicts pooled connections older than CONN_TTL_SEC, ensuring no
    connection is reused with a token that may have expired.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Optional

import psycopg2
import psycopg2.extras
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)

# Pooled connections older than this are discarded on checkout.
# Set well under the 1-hour OAuth token TTL.
CONN_TTL_SEC = int(os.environ.get("PG_CONN_TTL_SEC", str(50 * 60)))

# Cached token is reused for at most this long before re-fetching.
TOKEN_TTL_SEC = int(os.environ.get("PG_TOKEN_TTL_SEC", str(30 * 60)))

# Max idle connections retained in the pool.
MAX_IDLE = int(os.environ.get("PG_MAX_IDLE", "10"))

# Connections idle longer than this are validated with SELECT 1 on checkout.
# Recently-used connections skip the network validation for latency.
VALIDATE_AFTER_IDLE_SEC = int(os.environ.get("PG_VALIDATE_AFTER_IDLE_SEC", "30"))

# Pool is pre-warmed to this many connections at init.
MIN_WARM = int(os.environ.get("PG_MIN_WARM", "2"))


class _TokenAwarePool:
    """Postgres pool that re-fetches the OAuth token for every new connection."""

    def __init__(
        self,
        ws: WorkspaceClient,
        host: str,
        port: int,
        dbname: str,
        user: str,
        sslmode: str,
        max_idle: int = MAX_IDLE,
    ):
        self._ws = ws
        self._host = host
        self._port = port
        self._dbname = dbname
        self._user = user
        self._sslmode = sslmode
        self._max_idle = max_idle
        self._lock = threading.Lock()
        # Each idle entry: (conn, last_used_at). created_at lives on conn._pg_created_at.
        self._idle: list[tuple[Any, float]] = []
        self._cached_token: Optional[str] = None
        self._token_minted_at: float = 0.0

    def _get_token(self) -> str:
        """Return a fresh-enough OAuth token, fetching a new one if expired."""
        now = time.time()
        if not self._cached_token or (now - self._token_minted_at) > TOKEN_TTL_SEC:
            auth_header = self._ws.config.authenticate()
            token = auth_header.get("Authorization", "").replace("Bearer ", "")
            if not token:
                raise RuntimeError("Failed to fetch Databricks OAuth token for Postgres")
            self._cached_token = token
            self._token_minted_at = now
            logger.info(
                "Postgres token refreshed (sha8=%s, ttl=%ds)",
                token[:8],
                TOKEN_TTL_SEC,
            )
        return self._cached_token

    def _connect(self) -> Any:
        """Open a brand-new psycopg2 connection with a fresh token."""
        token = self._get_token()
        conn = psycopg2.connect(
            host=self._host,
            port=self._port,
            dbname=self._dbname,
            user=self._user,
            password=token,
            sslmode=self._sslmode,
            connect_timeout=10,
        )
        # Stamp creation time on the connection so the TTL survives put/get cycles.
        try:
            setattr(conn, "_pg_created_at", time.time())
        except Exception:
            pass
        logger.debug("Postgres connection opened (token sha8=%s)", token[:8])
        return conn

    def _is_alive(self, conn: Any) -> bool:
        """Quick health check — returns False if the connection cannot serve queries."""
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return True
        except Exception:
            return False

    def getconn(self) -> Any:
        """Hand out a healthy connection. Discards stale or dead ones first."""
        now = time.time()
        with self._lock:
            while self._idle:
                conn, last_used_at = self._idle.pop()
                created_at = getattr(conn, "_pg_created_at", now)
                age = now - created_at
                idle_for = now - last_used_at
                if age > CONN_TTL_SEC:
                    logger.debug("Discarding aged Postgres connection (age=%.0fs)", age)
                    self._safe_close(conn)
                    continue
                # Cheap local check first — psycopg2 marks closed when client side disconnects.
                if conn.closed:
                    self._safe_close(conn)
                    continue
                # Only run a network round-trip if the connection has been idle a while.
                # Hot-path checkouts (returned-and-reused within seconds) skip validation.
                if idle_for > VALIDATE_AFTER_IDLE_SEC and not self._is_alive(conn):
                    logger.warning("Discarding dead pooled Postgres connection (idle=%.0fs)", idle_for)
                    self._safe_close(conn)
                    continue
                return conn
        # Pool empty or all evicted — open a fresh one with a fresh token.
        return self._connect()

    def putconn(self, conn: Any) -> None:
        """Return a connection to the pool, or close it if no slot/dead."""
        if conn is None:
            return
        if conn.closed:
            return
        # Roll back any open transaction so we don't poison the next user.
        try:
            conn.rollback()
        except Exception:
            self._safe_close(conn)
            return
        now = time.time()
        with self._lock:
            if len(self._idle) >= self._max_idle:
                self._safe_close(conn)
            else:
                # last_used_at is "now"; created_at is preserved on conn._pg_created_at.
                self._idle.append((conn, now))

    def closeall(self) -> None:
        """Close every idle connection (in-flight ones close on their own putconn)."""
        with self._lock:
            for conn, _ in self._idle:
                self._safe_close(conn)
            self._idle.clear()

    @staticmethod
    def _safe_close(conn: Any) -> None:
        try:
            conn.close()
        except Exception:
            pass


_pool: Optional[_TokenAwarePool] = None
_init_lock = threading.Lock()


def init_pool(ws: WorkspaceClient) -> None:
    """Initialize the global Postgres pool.

    Reads PGHOST, PGPORT, PGDATABASE, PGUSER, PGSSLMODE from the environment.
    The pool itself does not hold long-lived credentials — each new
    connection mints a fresh token via `ws.config.authenticate()`.
    """
    global _pool

    host = os.environ.get("PGHOST")
    port = int(os.environ.get("PGPORT", "5432"))
    dbname = os.environ.get("PGDATABASE", "databricks_postgres")
    user = os.environ.get("PGUSER", "")
    sslmode = os.environ.get("PGSSLMODE", "require")

    if not host:
        raise RuntimeError(
            "PGHOST env var not set — Lakebase database resource not configured"
        )

    with _init_lock:
        if _pool is not None:
            _pool.closeall()
        _pool = _TokenAwarePool(
            ws=ws,
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            sslmode=sslmode,
        )
        # Pre-warm so the first few requests don't all pay handshake cost.
        warmed = 0
        for _ in range(MIN_WARM):
            try:
                conn = _pool._connect()
                _pool.putconn(conn)
                warmed += 1
            except Exception as e:
                logger.warning("Pre-warm connection failed: %s", e)
                break
    logger.info(
        "Postgres pool initialized (%s:%s/%s) — token_ttl=%ds, conn_ttl=%ds, warmed=%d",
        host,
        port,
        dbname,
        TOKEN_TTL_SEC,
        CONN_TTL_SEC,
        warmed,
    )


def _ensure_pool() -> None:
    """Lazy-init the pool on first use if it wasn't initialized at startup."""
    global _pool
    if _pool is None:
        try:
            init_pool(WorkspaceClient())
        except Exception as e:
            raise RuntimeError(f"Postgres pool auto-init failed: {e}")


@contextmanager
def get_conn():
    """Yield a healthy Postgres connection from the pool.

    The connection is validated and refreshed if needed. Returns to the pool on exit.
    """
    _ensure_pool()
    assert _pool is not None
    conn = _pool.getconn()
    try:
        yield conn
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _pool.putconn(conn)


def execute_query(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """Execute a SELECT and return rows as list of dicts."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]


def execute_write(sql: str, params: tuple | None = None) -> list[dict[str, Any]] | None:
    """Execute INSERT/UPDATE/DELETE. Returns rows if RETURNING, else None."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            conn.commit()
            if cur.description:
                return [dict(row) for row in cur.fetchall()]
            return None


def close_pool() -> None:
    """Close all idle connections and drop the pool."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("Postgres pool closed")
