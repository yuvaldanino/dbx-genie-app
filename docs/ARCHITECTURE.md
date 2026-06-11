# Genie-rator Architecture & Current State

## Last Updated: June 11, 2026

> Doc map: [`PROJECT_STATE.md`](PROJECT_STATE.md) = state/bugs/roadmap · [`OPERATIONS.md`](OPERATIONS.md) = deploy/test/recovery · [`UI_UPDATES.md`](UI_UPDATES.md) = UI change log · `../CLAUDE.md` = hard rules + dev commands

## What This App Does
Multi-user Databricks App that generates branded Genie Spaces with custom data. Users describe a company → LLM designs schema → LLM generates data specs → Python generates rows → creates UC tables → creates Genie Space with embedded chat + dashboards.

## Tech Stack
- **Frontend**: React + Vite + TanStack Router + shadcn/ui + Recharts
- **Backend**: FastAPI (Python), served at `/api`
- **Database**: Lakebase Postgres (app state) + Delta tables (pipeline data, sessions)
- **Deployment**: Databricks Apps via Asset Bundles
- **LLM**: Claude Opus via Databricks AI Gateway (`opendoor-claude-opus-46`)
- **Auth**: Databricks Apps headers (X-Forwarded-User, X-Forwarded-Access-Token)

## Architecture Diagram
```
Frontend (React)  →  FastAPI Backend  →  Lakebase Postgres (users, spaces, conversations, messages, feedback)
                                      →  Delta Tables (sessions, generated company data)
                                      →  Genie API (chat, query results)
                                      →  AI Gateway / Claude (schema design, data gen specs, dashboards)
```

## Key Directories
```
src/genieapp/
  backend/
    app.py                    # FastAPI entry point, startup (Postgres pool init)
    db.py                     # Data access layer — Lakebase Postgres for app state, Delta for sessions
    pg.py                     # Postgres connection pool (psycopg2, OAuth JWT auth)
    chart_suggest.py          # Heuristic chart type/axis selection for query results
    genie_client.py           # Genie API wrapper + SQL re-execution fallback
    models.py                 # All Pydantic models (CreateSpaceIn, ChatMessageOut, etc.)
    core/                     # APX framework (config, deps, headers, static)
    routes/
      admin.py                # Admin dashboard + Lakebase test endpoint
      chat.py                 # Chat endpoints (sync/async), conversations, starred, feedback
      spaces.py               # Space CRUD, BYOG, pipeline trigger, config, dashboard
      users.py                # User profile, preferences, feedback submission
      upload.py               # Image upload/retrieval
      export.py               # Conversation export
    pipeline/
      run.py                  # Pipeline orchestrator (schema → data → tables → genie space)
      schema_designer.py      # LLM schema design (3-4 tables from company description)
      data_generator_llm.py   # Spec-based data gen (LLM specs → Python rows, parallel)
      data_generator.py       # Old Faker-based generator (unused, kept for reference)
      space_creator.py        # UC table creation, Genie Space creation, session saving
      dashboard_designer.py   # LLM dashboard panel design + SQL execution
      theme_generator.py      # LLM brand color palette generation
  ui/
    routes/
      index.tsx               # Landing page — create space form (name, desc, logo, must-answer questions)
      spaces.tsx              # Space listing (My Spaces + Shared Spaces + delete)
      admin.tsx               # Admin dashboard (KPIs, usage chart, user/space tables)
      _sidebar/
        route.tsx             # Sidebar layout with nav, tables, history
        chat.tsx              # Chat page (QueryWorkspace)
        dashboard.tsx         # Dashboard page (pre-computed panels + Genie drawer)
    components/apx/
      ChartRenderer.tsx       # Recharts wrapper with chart type/axis controls
      DashboardView.tsx       # Dashboard grid with KPI cards + charts + Genie drawer
      GenieDrawer.tsx         # Slide-out Genie chat on dashboard
      DataTable.tsx           # Tabular results display
      MessageBubble.tsx       # Chat message with markdown, SQL, charts
      HelpDialog.tsx          # Help guide + feedback form
    lib/
      api.ts                  # API client (axios + React Query hooks)
      useChatFlow.ts          # Reusable chat polling hook
scripts/pipeline/
  01_design_and_generate.ipynb  # Step 1: Schema design + spec-based data gen (with logging)
  02_create_tables.ipynb        # Step 2: Create UC Delta tables from parquet
  03_create_space.ipynb         # Step 3: Create Genie Space + save session
  04_create_dashboard.ipynb     # Step 4: LLM dashboard panel design + SQL execution
```

## Data Stores — the complete map

The app stores data in FIVE places. Know which is which:

### 1. Lakebase Postgres (PRIMARY app state)
- **Host**: ep-flat-haze-d2mzy9ui.database.us-east-1.cloud.databricks.com · db `databricks_postgres` · schema `public`
- **Tables**: `users`, `spaces`, `conversations`, `messages` (incl. `is_starred`/`starred_by`), `feedback`
- **Access**: ALL app-state reads/writes go through `pg.execute_query`/`pg.execute_write` (called from `db.py`)
- **Connection pool** (`pg.py`): mints a fresh OAuth token per NEW connection (30-min token cache), evicts connections >50 min old, validates with SELECT 1 only when idle >30s, pre-warms 2 at init. This design exists because of two production outages — see PROJECT_STATE.md incident history. **Do not regress to a startup-captured token.**
- **Deploy quirk**: bundle deploy strips the Database resource → deploy.sh re-adds via API PATCH → SP loses `app_rw` role → **manual GRANT required after every deploy** (see OPERATIONS.md)

### 2. UC Delta tables (legacy + pipeline data)
- **Catalog**: `yd_launchpad_final_classic_catalog`, schema `genie_app`
- **Tables**: `sessions` (legacy pipeline metadata, still read as a spaces fallback), per-space generated analytics tables (the actual demo data Genie queries)
- **⚠️ Shadow tables**: `ensure_tables()` (db.py:86) still creates Delta twins of `users`/`spaces`/`conversations`/`messages`/`images`/`feedback` at startup for backward compat. **These Delta twins are NOT used by app reads/writes** — Postgres is authoritative. Don't be confused by them; candidates for removal.
- **Access**: SQL Statements API via `run_sql()` (db.py:38)

### 3. UC Volumes (binary/file storage)
- `/Volumes/{catalog}/genie_app/images/` — uploaded logos (routes/upload.py); metadata in Delta `images` table
- `/Volumes/{catalog}/{schema}/raw_data/state.json` — pipeline writes per-space state; also data-gen logs

### 4. state.json (legacy single-space fallback)
- Loaded by `app_config.get_state()` from UC Volume (or `STATE_FILE_PATH` env)
- **Fallback chain for spaces**: Postgres `spaces` → Delta `sessions` → state.json (this is why a broken Postgres shows only "Acme Corporation")
- Also used by `_resolve_space_id()` in chat.py when no space_id is passed

### 5. In-memory caches (db.py:29-31)
- `_user_cache` TTL 300s, `_space_list_cache` TTL 30s — explains why changes can take ≤30s to appear in space lists
- Frontend: `localStorage` for theme preference only

## Warehouse IDs (there are several — don't mix them up)

| ID / source | Where | Used for |
|---|---|---|
| `fc62b388f737b2d3` | hardcoded `db.py:19` | App runtime SQL: sessions reads, Delta DDL, Genie SQL re-execution |
| lookup "Serverless Starter Warehouse" | `databricks.yml` | Bundle deploy resolves at deploy time; deploy.sh grants + app resource use this (`551addcb4415adb7` currently) |
| `warehouse_id` column | Postgres `spaces` rows | Per-space override, passed to pipeline |
| `551addcb4415adb7` | `router.py` (dead code) | Ignore |

## External Services & Auth Model

**Two client identities** (core/_defaults.py): `ws` = app service principal (SP); `user_ws` = per-request OBO from `X-Forwarded-Access-Token`.

| Service | Client | Where | Notes |
|---|---|---|---|
| Genie API (`ws.genie.*`) | **SP ONLY** | genie_client.py | OBO tokens lack the `genie` scope → 403. Hard rule. |
| SQL Statements API | SP | db.py, genie_client.py | warehouse `fc62b388f737b2d3` |
| Jobs API (`run_now`, `get_run`) | SP | routes/spaces.py | Triggers create_space_job; params must be ASCII (known bug) |
| Statement Execution API | SP | genie_client.py:249 | Fetch non-inline Genie result data |
| UC Tables API (`ws.tables.get`) | SP | genie_client.py | Table detail for sidebar |
| Files API (`ws.files.*`) | SP | app_config.py, upload.py | state.json + images |
| AI Gateway (OpenAI SDK) | PAT token | pipeline/*.py | `https://{host}.ai-gateway.cloud.databricks.com/mlflow/v1`, model `opendoor-claude-opus-46`. Pipeline-only, not runtime. |
| BYOG validation | OBO (intentional) | spaces.py:149 | Verifies USER can access the space; UI entry removed, path mostly dead |

## Data Generation Pipeline (Current: Spec-Based v3)
```
User Input (company name, description, optional must-answer questions)
  ↓
Step 1: LLM designs schema (3-4 tables, ~30s)
  ↓
Step 2: LLM generates data SPEC per table (distributions, fixtures) — parallel for independent tables (~60-80s)
  ↓
Step 3: Python generates rows from spec (instant, ~0.03s)
  - Two-pass formula evaluation (regular cols first, then formulas)
  - Post-generation sanity checks (balance <= principal, price > cost, etc.)
  ↓
Step 4: Write parquet → Create Delta tables → Create Genie Space → Create Dashboard
  ↓
Total: ~2-3 min for data gen, ~5-6 min total pipeline
```

## Deploy Workflow
```bash
./deploy.sh  # Builds frontend, deploys bundle, restores Lakebase resource, deploys app
# Then run in Lakebase SQL editor:
GRANT app_rw TO "677d1641-521c-4df6-91f4-dacea8be74e7";
```

## Admin
- **Admin user ID**: 76554809512980@7474655921234161
- **Admin endpoint**: GET /api/admin/stats, /admin/users, /admin/spaces, /admin/lakebase-test
- **Service principal**: app-5t6256 genieapp-dev (677d1641-521c-4df6-91f4-dacea8be74e7)

## Key Features Implemented
- [x] Multi-user session management (My Spaces vs Shared Spaces)
- [x] Ownership checks on mutations (delete, template change)
- [x] Conversation isolation (users can't see each other's conversations)
- [x] Chart suggestion engine (ID exclusion, KPI detection, axis selection)
- [x] Dashboard with embedded Genie chat drawer
- [x] Admin dashboard with KPIs, usage trends, user/space management
- [x] Help dialog with guide + feedback collection
- [x] AWS-style delete confirmation (type space name)
- [x] Lakebase Postgres migration (fast reads/writes)
- [x] Spec-based data generation (LLM specs → Python rows)
- [x] Must-answer questions (optional, shapes schema + data)
- [x] Data generation logging to UC Volume
- [x] Parallel table generation for independent tables
- [x] SQL re-execution fallback for expired Genie results (working since 2026-06-11 — UC grants were silently missing before)
- [x] Recompute expired results: `POST /api/chat/{conv}/{msg}/recompute` + per-message button + "Recompute all" (QueryWorkspace)
- [x] Markdown rendering for Genie responses
- [x] Robust JSON serialization (Decimal, date, datetime, numpy)

## Known Issues / Future Work
- [ ] Deploy strips Lakebase DB resource → GRANT required after each deploy (agent self-serves via psql since 2026-06-11, see OPERATIONS.md; bundle CLI doesn't support postgres resource type yet)
- [x] ~~History load rebuilds per-message data serially~~ — parallelized 2026-06-11 (ThreadPoolExecutor ≤6 workers in chat.py)
- [ ] `/chat/feedback` resolves space_id from legacy state.json → silently broken for all non-default spaces (quick win, see PROJECT_STATE.md)
- [ ] `build_genie_instructions` keys on old `faker` schema format → degraded instructions for all v3 spaces (P0 #1, fix + retune approved)
- [ ] `_parse_genie_response` keeps only the LAST text/query attachment; uses legacy non-attachment-scoped query-result endpoint (P0 #1)
- [ ] Email column in generated data sometimes gets numeric values instead of strings (spec issue)
- [ ] Formula-derived columns occasionally produce 0 when eval fails (fallback kicks in)
- [ ] Expired-result recompute re-derives data from saved SQL — regenerated data may differ slightly from the original Genie snapshot
- [ ] Pipeline notebooks duplicate logic from Python modules (space_creator.py vs notebook cells)
- [ ] Error toasts in frontend not fully implemented (some errors still show blank screens)
- [ ] Phase 4+5 of Lakebase migration not done (cleanup route-level SQL, RETURNING optimization)

## Git / Deployment
- **Branches**: `main` = stable (tag `v2-stable` = rollback point), `agent-overhaul` = active development
- **Repo**: github.com/yuvaldanino/dbx-genie-app (push requires `gh auth switch --user yuvaldanino`)
- **Derek's fork**: github.com/dbderek/databricks-genie-app (historical, remotes derek/v1-v4)
- **App URL**: https://genieapp-dev-7474655921234161.aws.databricksapps.com
- **Workspace**: fevm-yd-launchpad-final-classic (profile `vm`)
- Deploy procedure + required env: see [`OPERATIONS.md`](OPERATIONS.md)
