# Genie-rator Architecture & Current State

## Last Updated: April 28, 2026

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

## Database: Lakebase Postgres
- **Host**: ep-flat-haze-d2mzy9ui.database.us-east-1.cloud.databricks.com
- **Database**: databricks_postgres
- **Schema**: public
- **Tables**: users, spaces, conversations, messages, images, feedback
- **Auth**: Service principal OAuth JWT via `ws.config.authenticate()`
- **Connection**: psycopg2 pool in `pg.py`, auto-init on first use
- **Deploy quirk**: `databricks bundle deploy` strips the Database resource → deploy.sh re-adds it via API PATCH → need to run `GRANT app_rw TO "677d1641-521c-4df6-91f4-dacea8be74e7"` after each deploy

## Database: Delta Tables (UC)
- **Catalog**: yd_launchpad_final_classic_catalog
- **Schema**: genie_app
- **Tables**: sessions (legacy pipeline metadata), generated company tables (per-space analytics data)
- **Warehouse**: fc62b388f737b2d3 (yd-sql-warehouse)
- **Used for**: Pipeline data generation, Genie SQL re-execution, session fallback

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
- [x] SQL re-execution fallback for expired Genie results
- [x] Markdown rendering for Genie responses
- [x] Robust JSON serialization (Decimal, date, datetime, numpy)

## Known Issues / Future Work
- [ ] Deploy strips Lakebase DB resource → need manual GRANT after each deploy (bundle CLI doesn't support postgres resource type yet)
- [ ] Email column in generated data sometimes gets numeric values instead of strings (spec issue)
- [ ] Formula-derived columns occasionally produce 0 when eval fails (fallback kicks in)
- [ ] Old conversations with expired Genie results use SQL re-execution fallback (slightly different data)
- [ ] Pipeline notebooks duplicate logic from Python modules (space_creator.py vs notebook cells)
- [ ] Error toasts in frontend not fully implemented (some errors still show blank screens)
- [ ] Phase 4+5 of Lakebase migration not done (cleanup route-level SQL, RETURNING optimization)

## Git / Deployment
- **Branch**: v1-release (main working branch)
- **Derek's repo**: github.com/dbderek/databricks-genie-app (v4 = latest push)
- **App URL**: https://genieapp-dev-7474655921234161.aws.databricksapps.com
- **Workspace**: fevm-yd-launchpad-final-classic
