"""Local logic test for pg.py — mocks psycopg2 + WorkspaceClient.

Verifies:
  1. Token is fetched on first connection.
  2. Token is REUSED within TOKEN_TTL_SEC.
  3. Token is REFRESHED after TOKEN_TTL_SEC.
  4. Connections older than CONN_TTL_SEC are evicted on checkout.
  5. Dead connections are detected and replaced.
  6. Concurrent checkout/return doesn't deadlock.

Run from repo root:  python scripts/test_pg_pool_logic.py
"""

from __future__ import annotations

import os
import sys
import threading
import time
import types
from unittest.mock import MagicMock

# --- Mock psycopg2 BEFORE importing pg.py -----------------------------------

_connect_calls: list[dict] = []  # passwords passed to psycopg2.connect


class _FakeCursor:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, params=None):
        if self._conn._dead:
            raise Exception("connection closed by server")

    def fetchone(self):
        return (1,)

    def fetchall(self):
        return []

    @property
    def description(self):
        return None

    def close(self):
        pass


class _FakeConn:
    def __init__(self, password: str):
        self.password = password
        self.closed = False
        self._dead = False

    def cursor(self, cursor_factory=None):
        return _FakeCursor(self)

    def rollback(self):
        if self._dead:
            raise Exception("connection lost")

    def commit(self):
        pass

    def close(self):
        self.closed = True


def _fake_connect(**kwargs):
    _connect_calls.append({"password": kwargs.get("password", "")})
    return _FakeConn(password=kwargs["password"])


fake_psycopg2 = types.ModuleType("psycopg2")
fake_psycopg2.connect = _fake_connect  # type: ignore
fake_extras = types.ModuleType("psycopg2.extras")
fake_extras.RealDictCursor = object  # type: ignore
fake_psycopg2.extras = fake_extras  # type: ignore
sys.modules["psycopg2"] = fake_psycopg2
sys.modules["psycopg2.extras"] = fake_extras

# Mock databricks.sdk
fake_sdk = types.ModuleType("databricks")
fake_sdk_sdk = types.ModuleType("databricks.sdk")
_token_counter = {"n": 0}


class _FakeWS:
    @property
    def config(self):
        return self

    def authenticate(self):
        _token_counter["n"] += 1
        return {"Authorization": f"Bearer token_v{_token_counter['n']}"}


fake_sdk_sdk.WorkspaceClient = _FakeWS  # type: ignore
sys.modules["databricks"] = fake_sdk
sys.modules["databricks.sdk"] = fake_sdk_sdk

# Set short TTLs BEFORE importing pg.py
os.environ["PG_TOKEN_TTL_SEC"] = "2"
os.environ["PG_CONN_TTL_SEC"] = "3"
os.environ["PG_MAX_IDLE"] = "10"
os.environ["PG_MIN_WARM"] = "0"  # disable warmup; tests count connect calls precisely
os.environ["PG_VALIDATE_AFTER_IDLE_SEC"] = "1"  # short so dead-conn test fires
os.environ["PGHOST"] = "fakehost"
os.environ["PGUSER"] = "fakeuser"
os.environ["PGPORT"] = "5432"

# Now import pg
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from genieapp.backend import pg  # noqa: E402


def _reset():
    _connect_calls.clear()
    _token_counter["n"] = 0
    pg.close_pool()


def test_first_connection_fetches_token():
    _reset()
    pg.init_pool(_FakeWS())
    with pg.get_conn() as conn:
        assert conn.password == "token_v1", f"expected token_v1, got {conn.password}"
    assert len(_connect_calls) == 1
    print("PASS  test_first_connection_fetches_token")


def test_token_reused_within_ttl():
    _reset()
    pg.init_pool(_FakeWS())
    # Open and close 3 connections rapidly — no time elapses, token shouldn't change
    for _ in range(3):
        with pg.get_conn() as conn:
            pass
    # Only one auth call should have happened (token is cached)
    assert _token_counter["n"] == 1, f"token fetched {_token_counter['n']}x, expected 1"
    print(f"PASS  test_token_reused_within_ttl ({_token_counter['n']} fetch)")


def test_token_refreshes_after_ttl():
    _reset()
    pg.init_pool(_FakeWS())
    with pg.get_conn():
        pass
    # Force pool eviction so next checkout opens a fresh connection.
    pg._pool.closeall()
    time.sleep(2.5)  # exceed TOKEN_TTL_SEC=2
    with pg.get_conn() as conn:
        assert conn.password == "token_v2", f"expected token_v2, got {conn.password}"
    assert _token_counter["n"] == 2, f"expected 2 token fetches, got {_token_counter['n']}"
    print("PASS  test_token_refreshes_after_ttl")


def test_aged_connection_evicted():
    _reset()
    pg.init_pool(_FakeWS())
    with pg.get_conn() as c1:
        old_id = id(c1)
    # Connection is now in pool. Wait past CONN_TTL_SEC=3.
    time.sleep(3.5)
    # Token cache also expired (TTL=2 < 3.5), so we should see token_v2.
    with pg.get_conn() as c2:
        assert id(c2) != old_id, "expected fresh connection, got same one"
        assert c2.password == "token_v2", f"expected token_v2, got {c2.password}"
    print("PASS  test_aged_connection_evicted")


def test_dead_connection_replaced():
    _reset()
    pg.init_pool(_FakeWS())
    with pg.get_conn() as c1:
        c1._dead = True  # simulate server-side termination
    # Wait past PG_VALIDATE_AFTER_IDLE_SEC so checkout actually runs SELECT 1.
    time.sleep(1.5)
    with pg.get_conn() as c2:
        assert c2 is not c1, "expected new connection"
        assert not c2._dead
    print("PASS  test_dead_connection_replaced")


def test_recent_connection_skips_validation():
    """Hot-path: returned-and-checked-out within seconds skips network validation."""
    _reset()
    pg.init_pool(_FakeWS())
    with pg.get_conn():
        pass
    with pg.get_conn():
        pass
    # 1 underlying connect call: pool reused the connection without re-running SELECT 1
    # over the network (we can't directly assert no SELECT 1 with this mock, but we
    # can confirm the same physical connection was reused — only 1 _fake_connect call).
    assert len(_connect_calls) == 1, f"expected 1 connect call, got {len(_connect_calls)}"
    print("PASS  test_recent_connection_skips_validation")


def test_warmup_creates_min_connections():
    """init_pool with MIN_WARM>0 pre-creates connections."""
    _reset()
    os.environ["PG_MIN_WARM"] = "3"
    # Reload pg's module-level constants
    pg.MIN_WARM = 3
    pg.init_pool(_FakeWS())
    assert len(_connect_calls) == 3, f"expected 3 warmups, got {len(_connect_calls)}"
    assert len(pg._pool._idle) == 3, f"expected 3 idle, got {len(pg._pool._idle)}"
    # Restore
    pg.MIN_WARM = 0
    print("PASS  test_warmup_creates_min_connections")


def test_concurrent_checkouts():
    _reset()
    pg.init_pool(_FakeWS())
    errors: list[Exception] = []

    def worker():
        try:
            for _ in range(10):
                with pg.get_conn() as conn:
                    pass
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not errors, f"errors during concurrency: {errors}"
    # At most MAX_IDLE=10 connections were retained; total opens >= 1 but unbounded
    print(f"PASS  test_concurrent_checkouts (opens={len(_connect_calls)}, errors=0)")


def test_execute_query_path():
    _reset()
    pg.init_pool(_FakeWS())
    rows = pg.execute_query("SELECT 1")
    assert rows == []  # FakeCursor returns no rows
    print("PASS  test_execute_query_path")


if __name__ == "__main__":
    print("Running pg.py logic tests with TOKEN_TTL=2s, CONN_TTL=3s\n")
    tests = [
        test_first_connection_fetches_token,
        test_token_reused_within_ttl,
        test_token_refreshes_after_ttl,
        test_aged_connection_evicted,
        test_dead_connection_replaced,
        test_recent_connection_skips_validation,
        test_warmup_creates_min_connections,
        test_concurrent_checkouts,
        test_execute_query_path,
    ]
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
            sys.exit(1)
    print(f"\n  All {len(tests)} tests passed.")
