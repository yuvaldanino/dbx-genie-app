# Lakebase Migration Guide

## Overview
Migrating app state tables from Delta (SQL Statements API, 1-2s/query) to Lakebase Postgres (psycopg2, ~5-50ms/query). Delta tables are NOT deleted — kept as rollback safety net.

## Status Tracker

| Phase | Description | Status | Notes |
|-------|-------------|--------|-------|
| 0 | Connection Pool Module | [x] | Create pg.py, init on startup |
| 1 | Create Postgres Tables | [x] | 6 tables + indexes in public schema (created via SQL editor) |
| 2 | Migrate Data | [x] | 29 users, 18 spaces, 26 convos, 75 msgs, 3 feedback migrated |
| 3a | Test Queries | [x] | All 7 tests pass — Postgres matches Delta |
| 3b | Rewrite db.py | [x] | All functions swapped to Postgres, app working |
| 4 | Clean Up Routes | [ ] | Move raw SQL into db.py functions |
| 5 | Optimize | [ ] | UPSERT, RETURNING, token refresh |

## Testing Strategy
ALL phases tested via `/api/admin/lakebase-test` endpoint before touching live app code. Each phase adds test steps to that endpoint. Real `db.py` only modified in Phase 3b after all tests pass.

---

## What Moves to Postgres
- users, spaces, conversations, messages, images, feedback

## What Stays on Delta
- sessions (pipeline-created, written by Spark notebooks)
- Generated company tables (analytics data Genie queries)
- Genie SQL re-execution (`_reexecute_sql` in genie_client.py)
- Dashboard panel SQL execution (analytics queries in dashboard_designer.py)

---

## Phase 0: Connection Pool Module

**Create:** `src/genieapp/backend/pg.py`
```python
# Key functions:
init_pool(ws)           # Read PG env vars, get OAuth token, create ThreadedConnectionPool
get_conn()              # Context manager — get/return connections from pool
execute_query(sql, params) → list[dict]  # SELECT via RealDictCursor
execute_write(sql, params) → None        # INSERT/UPDATE with commit
close_pool()            # Shutdown
```

**Modify:** `src/genieapp/backend/app.py` — add `init_pool(ws)` to startup

**Test:** Add step to lakebase-test: init pool → `execute_query("SELECT 1")` → verify `[(1,)]`

**Deploy + hit test endpoint → verify → move to Phase 1**

---

## Phase 1: Create Postgres Tables

**6 tables created via lakebase-test endpoint:**

```sql
-- users
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY, email TEXT, username TEXT,
    default_template TEXT DEFAULT 'simple', preferences_json TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- spaces
CREATE TABLE IF NOT EXISTS spaces (
    space_id TEXT PRIMARY KEY, owner_user_id TEXT, company_name TEXT,
    description TEXT, schema_name TEXT, space_type TEXT DEFAULT 'generated',
    template_id TEXT DEFAULT 'simple', logo_volume_path TEXT,
    primary_color TEXT DEFAULT '#1a73e8', secondary_color TEXT DEFAULT '#ea4335',
    accent_color TEXT, chart_colors_json TEXT, tables_json TEXT,
    sample_questions_json TEXT, warehouse_id TEXT, dashboard_json TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- conversations
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY, space_id TEXT, user_id TEXT,
    title TEXT, message_count INTEGER DEFAULT 0, is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- messages
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY, conversation_id TEXT, user_id TEXT,
    question TEXT, status TEXT, sql_text TEXT, description TEXT,
    is_clarification BOOLEAN DEFAULT false, feedback_rating TEXT,
    is_starred BOOLEAN DEFAULT false, starred_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- images
CREATE TABLE IF NOT EXISTS images (
    image_id TEXT PRIMARY KEY, user_id TEXT, space_id TEXT,
    filename TEXT, content_type TEXT, volume_path TEXT, size_bytes BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- feedback
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id TEXT PRIMARY KEY, user_id TEXT, email TEXT,
    message TEXT, created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes:**
```sql
CREATE INDEX IF NOT EXISTS idx_spaces_owner ON spaces(owner_user_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_spaces_type ON spaces(space_type) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id) WHERE is_archived = false;
CREATE INDEX IF NOT EXISTS idx_conversations_space ON conversations(space_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_starred ON messages(starred_by) WHERE is_starred = true;
```

**Verify:** Query `information_schema.tables` — 6 tables, all 0 rows.

**Deploy + hit test endpoint → verify → move to Phase 2**

---

## Phase 2: Migrate Data (Delta → Postgres)

**Per table:**
1. Read all rows from Delta via `run_sql(ws, "SELECT * FROM {delta_table}")`
2. Parse with `parse_sql_rows()`
3. Insert into Postgres: `INSERT INTO {table} (...) VALUES (%s, ...) ON CONFLICT (pk) DO NOTHING`
4. Report row counts

**Order:** users → spaces → conversations → messages → images → feedback

**Type conversions:**
- Booleans: `"true"/"false"` → Python `True/False`
- Integers: `str` → `int()`
- Timestamps: ISO strings pass through (Postgres parses them)
- NULLs: already `None`

**Verify:** Row counts match Delta vs Postgres for each table.

**Migration is idempotent** — `ON CONFLICT DO NOTHING` = safe to re-run.

**Deploy + hit test endpoint → verify → move to Phase 3a**

---

## Phase 3a: Test Postgres Queries

**Test queries added to lakebase-test (compare results with Delta):**
1. `SELECT * FROM users WHERE user_id = %s`
2. `SELECT * FROM spaces WHERE owner_user_id = %s AND is_active = true`
3. `SELECT * FROM spaces WHERE space_type = 'shared' AND is_active = true`
4. `SELECT * FROM conversations WHERE user_id = %s AND is_archived = false`
5. `SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at`
6. `INSERT ... ON CONFLICT DO UPDATE ... RETURNING *` (upsert)
7. Admin stats: `SELECT COUNT(*) FROM users`, messages with `NOW() - INTERVAL '7 days'`

**Each query: run on Postgres AND Delta, compare row counts + sample values.**

**Deploy + hit test endpoint → verify all match → move to Phase 3b**

---

## Phase 3b: Rewrite db.py

**Swap ~25 functions from Delta to Postgres. Function signatures stay identical.**

Key transforms:
```python
# Before (Delta):
safe_id = _escape(user_id)
result = run_sql(ws, f"SELECT * FROM {_USERS_TABLE} WHERE user_id = '{safe_id}'")
rows = parse_sql_rows(result)

# After (Postgres):
from .pg import execute_query
rows = execute_query("SELECT * FROM users WHERE user_id = %s", (user_id,))
```

**SQL dialect changes:**
| Delta | Postgres |
|---|---|
| `STRING` | `TEXT` |
| `DATEADD(DAY, -N, CURRENT_TIMESTAMP())` | `NOW() - INTERVAL 'N days'` |
| `first_value(col)` | `MIN(col)` |
| `'{_escape(val)}'` | `%s` parameterized |

**What stays on Delta (still uses `run_sql`):**
- `get_dashboard_data()` sessions table fallback
- All `_SESSIONS_TABLE` reads in spaces.py
- `_reexecute_sql()` in genie_client.py
- `_execute_panel_sql()` in dashboard_designer.py

**`ws` param stays in all signatures** (callers don't change) but unused for Postgres paths.

**Deploy + test full app (spaces, chat, conversations, admin, etc.) → Phase 4**

---

## Phase 4: Clean Up Route-Level Raw SQL

Move remaining raw SQL from route files into db.py functions:

- `upload.py` → new `db.save_image_metadata()`, `db.get_image_metadata()`
- `spaces.py` → new `db.get_session_by_space_id()` for sessions reads
- `dashboard_designer.py` → new `db.update_space_dashboard_json()` (Postgres) + keep Delta for sessions

**Deploy + test full app → Phase 5**

---

## Phase 5: Optimize

- `RETURNING *` on INSERT/UPDATE (no read-after-write)
- Postgres UPSERT for `get_or_create_user` (single statement)
- Single-query admin stats with JOINs (no N+1)
- Token refresh: catch `OperationalError`, rebuild pool, retry

---

## Connection Details
- Host: `ep-flat-haze-d2mzy9ui.database.us-east-1.cloud.databricks.com`
- Database: `databricks_postgres`
- User: Service principal client ID (from `PGUSER` env var)
- Auth: OAuth JWT token via `ws.config.authenticate()`
- Port: 5432, SSL: require

## Deploy Command
```bash
./deploy.sh
```
Handles: frontend build → bundle deploy → restore Lakebase resource → UC grants → app deploy

## Test Endpoint
```
GET https://genieapp-dev-7474655921234161.aws.databricksapps.com/api/admin/lakebase-test
```

## Rollback
```bash
git checkout -- src/genieapp/backend/db.py
```
Delta tables still have all data. App immediately reverts to SQL Statements API path.

## Files Changed Summary

| File | Phase | Change |
|---|---|---|
| `src/genieapp/backend/pg.py` | 0 | NEW — connection pool |
| `src/genieapp/backend/app.py` | 0 | Add pool init to startup |
| `src/genieapp/backend/routes/admin.py` | 0-3a | Test steps for each phase |
| `src/genieapp/backend/db.py` | 3b | Rewrite ~25 functions |
| `src/genieapp/backend/routes/upload.py` | 4 | Replace raw SQL with db functions |
| `src/genieapp/backend/routes/spaces.py` | 4 | Replace sessions raw SQL with db functions |
| `src/genieapp/backend/pipeline/dashboard_designer.py` | 4 | Dual-write spaces (PG) + sessions (Delta) |
| Frontend | — | ZERO changes |
| Routes (chat, users, export) | — | ZERO changes |
| genie_client.py | — | ZERO changes |
