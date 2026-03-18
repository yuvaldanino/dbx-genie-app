# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-user Databricks application for creating, connecting, and chatting with Genie Spaces. Users can:
- Create Genie Spaces via LLM pipeline (generates fake data + UC tables + Genie Space)
- Connect existing Genie Spaces (BYOG — Bring Your Own Genie)
- Choose from 5 UI templates per space
- Upload company logos (stored in UC Volumes)
- Chat with natural language, view results as charts/tables
- Persistent conversation history across restarts

## Architecture

- **Framework**: APX (FastAPI + React) — full-stack monorepo
- **Backend**: FastAPI (Python), served at `/api`, code in `src/genieapp/backend/`
- **Frontend**: React + Vite + TanStack Router (file-based routing) + shadcn/ui, code in `src/genieapp/ui/`
- **Backend serves frontend**: Static build from `src/genieapp/__dist__/` at `/`, API at `/api`
- **Deployment**: Databricks Apps via Databricks Asset Bundles (`databricks.yml`)
- **Database**: UC Delta tables via SQL Statements API (not Lakebase Postgres)
- **Auth**: Databricks Apps injects identity headers (`X-Forwarded-User`, `X-Forwarded-Email`, `X-Forwarded-Access-Token`)

### Backend Structure

```
backend/
├── app.py                  # Entry point — creates FastAPI app, runs ensure_tables on startup
├── app_config.py           # state.json loader (legacy single-space fallback)
├── db.py                   # Centralized data access layer (UC Delta tables)
├── chart_suggest.py        # Heuristic chart type suggestion
├── genie_client.py         # Databricks Genie API wrapper
├── models.py               # All Pydantic request/response models
├── core/                   # APX framework internals
│   ├── _base.py            # LifespanDependency ABC
│   ├── _config.py          # AppConfig, logger
│   ├── _defaults.py        # Config, WS client, user WS client dependencies
│   ├── _factory.py         # create_app(), create_router()
│   ├── _headers.py         # Databricks Apps header extraction
│   ├── _static.py          # Static file serving
│   └── dependencies.py     # Dependencies convenience class
├── routes/                 # API route modules
│   ├── __init__.py         # Aggregates all sub-routers
│   ├── chat.py             # Chat (sync/async), feedback, conversations, version, health
│   ├── spaces.py           # Space CRUD, BYOG, config, template selection, jobs
│   ├── tables.py           # Table browsing, app config
│   ├── users.py            # User profile, preferences
│   ├── upload.py           # Image upload/retrieval (UC Volumes)
│   └── export.py           # Conversation export
├── router.py               # Legacy monolithic router (dead code, kept for reference)
└── pipeline/               # Data generation pipeline
```

### Database Schema (UC Delta Tables)

Catalog: `yd_launchpad_final_classic_catalog`, Schema: `genie_app`

| Table | Purpose |
|-------|---------|
| `users` | User profiles and preferences (default_template, preferences_json) |
| `spaces` | Genie Space metadata — branding, tables, template, owner (evolves from `sessions`) |
| `conversations` | Conversation pointers (user-scoped, space-scoped) |
| `messages` | Message metadata — question, status, sql, description (NOT full data arrays) |
| `images` | Uploaded image metadata (binary stored in UC Volumes) |
| `sessions` | Legacy table from pipeline (still used as fallback) |

### Key Frontend Components

- `ui/lib/api.ts` — API client with axios + React Query hooks (user, spaces, chat, BYOG, upload)
- `ui/lib/useChatFlow.ts` — Reusable chat polling hook (extracted from chat.tsx)
- `ui/components/apx/AuthProvider.tsx` — User auth context (useCurrentUser → useAuth)
- `ui/components/apx/PreferencesPanel.tsx` — Theme + default template preferences
- `ui/components/apx/TemplateRenderer.tsx` — Lazy-loads correct template by templateId
- `ui/routes/_sidebar/chat.tsx` — Main chat page (uses useChatFlow)
- `ui/routes/_sidebar/templates.tsx` — Template picker (preview + apply to space)
- `ui/components/apx/template-testing/` — 5 demo templates with mock data

### Data Flow

1. **Setup pipeline** generates fake data, creates UC tables + Genie Space, writes to `sessions` table
2. **App startup** calls `ensure_tables()` to create DB tables, reads `state.json` as fallback
3. **User visit**: Frontend calls `GET /api/users/me` → auto-creates user in DB
4. **Space listing**: `GET /api/spaces` → user-owned spaces → sessions fallback → state.json fallback
5. **Chat flow**: `POST /api/chat/start` → poll `GET /status` → `GET /result` → persists to conversations + messages tables
6. **BYOG**: `POST /api/spaces/byog` → validates via OBO token → stores in spaces table

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/version` | App version |
| GET | `/api/config` | App config (legacy) |
| GET | `/api/users/me` | Current user profile |
| PATCH | `/api/users/me/preferences` | Update preferences |
| POST | `/api/chat` | Sync chat |
| POST | `/api/chat/start` | Async chat start |
| GET | `/api/chat/{conv}/{msg}/status` | Poll status |
| GET | `/api/chat/{conv}/{msg}/result` | Get result |
| POST | `/api/chat/feedback` | Send feedback |
| GET | `/api/tables` | List tables |
| GET | `/api/tables/{name}` | Table detail |
| GET | `/api/conversations` | List conversations (user-scoped) |
| GET | `/api/conversations/{conv_id}` | Conversation messages |
| POST | `/api/export` | Export conversation |
| GET | `/api/spaces` | List spaces (user-scoped) |
| POST | `/api/spaces` | Create space (pipeline) |
| POST | `/api/spaces/byog` | Connect existing space |
| GET | `/api/spaces/{id}/config` | Space config |
| PATCH | `/api/spaces/{id}/template` | Update template |
| DELETE | `/api/spaces/{id}` | Soft delete space |
| GET | `/api/jobs/{run_id}` | Job status |
| POST | `/api/images/upload` | Upload image |
| GET | `/api/images/{id}` | Get image |

## Development Commands

```bash
# Install Python deps
uv sync

# Install frontend deps
bun install

# Run backend (port 8000)
uv run uvicorn genieapp.backend.app:app --reload --host 0.0.0.0 --port 8000

# Run frontend dev server (port 5173, proxies /api → localhost:8000)
bun run --bun node_modules/.bin/vite dev

# Build frontend (outputs to src/genieapp/__dist__/)
bun run --bun node_modules/.bin/vite build

# Type check frontend
bun run --bun node_modules/.bin/tsc --noEmit

# Deploy to Databricks
./deploy.sh [target] [catalog] [schema]

# Deploy bundle only
databricks bundle deploy -t dev
```

## Package Managers

- **Python**: `uv` (not pip)
- **Frontend**: `bun`
- **Dev tooling**: `apx` toolkit

## Databricks Integration

- **Workspace profile**: `vm` (set in `databricks.yml`)
- **Key services**: Genie API (`ws.genie.*`), Unity Catalog tables, SQL Statements API, Jobs API
- **State file**: `state.json` — legacy single-space mode, read at startup via `app_config.get_state()`
- **UC Volumes**: Image storage at `/Volumes/{catalog}/genie_app/images/`

## Relevant Skills

- `databricks-genie` — Genie Space creation and querying
- `databricks-app-apx` — APX framework patterns (FastAPI + React)
- `databricks-app-python` — Databricks App authorization and deployment
- `databricks-synthetic-data-generation` — Fake data generation
- `databricks-asset-bundles` — Bundle-based deployment
- `databricks-config` — Profile and authentication setup

## Communication Style
- Be concise and direct
- Skip unnecessary explanations
- Get straight to the point
- No fluff or filler text

## Code Guidelines
- Write minimal, clean code
- Only include what's necessary to solve the problem
- Prefer simple solutions over complex ones
- Remove redundant code
- Use clear, short variable names
- Avoid over-engineering
- Always add docstrings and type hints for functions

## Response Format
- Lead with the solution
- Minimal context unless requested
- Code first, explanation only if needed
- No verbose introductions or conclusions
