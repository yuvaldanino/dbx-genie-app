# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack Databricks application that generates fake company data and a Genie Space from user-provided inputs (company name, description, logo, color scheme). The app provides a chat interface to query the Genie Space with natural language, including chart/visualization rendering and export capabilities.

## Architecture

- **Framework**: APX (FastAPI + React) — full-stack monorepo
- **Backend**: FastAPI (Python), served at `/api`, code in `src/genieapp/backend/`
- **Frontend**: React + Vite + TanStack Router (file-based routing) + shadcn/ui, code in `src/genieapp/ui/`
- **Backend serves frontend**: Static build from `src/genieapp/__dist__/` at `/`, API at `/api`
- **Deployment**: Databricks Apps via Databricks Asset Bundles (`databricks.yml`)

### Key Backend Components

- `backend/app.py` — App entry point, creates FastAPI app via `core.create_app()`
- `backend/router.py` — All API routes (chat, tables, conversations, spaces, export)
- `backend/genie_client.py` — Databricks Genie API wrapper (sync and async chat flows)
- `backend/chart_suggest.py` — Heuristic chart type suggestion from query results
- `backend/app_config.py` — Loads `state.json` (created by setup pipeline) with Pydantic models
- `backend/models.py` — All Pydantic request/response models
- `backend/pipeline/` — Data generation pipeline: schema design → fake data → Genie Space creation
- `backend/core/` — APX framework internals (factory, config, dependencies, static serving)

### Key Frontend Components

- `ui/lib/api.ts` — Hand-written API client with axios + React Query hooks (not auto-generated)
- `ui/routes/` — File-based routing via TanStack Router
- `ui/components/apx/` — App components (ChartRenderer, DataTable, MessageBubble, MapRenderer, ExportButton)
- `ui/components/ui/` — shadcn/ui primitives

### Data Flow

1. **Setup pipeline** (`deploy.sh` or `backend/pipeline/`) generates fake data, creates UC tables, creates Genie Space, writes `state.json`
2. **App startup** reads `state.json` (local file or UC Volume via `STATE_FILE_PATH` env var) to get space_id, branding, table metadata
3. **Chat flow**: Frontend → `POST /api/chat/start` → polls `GET /api/chat/{conv}/{msg}/status` → fetches `GET /api/chat/{conv}/{msg}/result`
4. **Conversations** stored in-memory per process (not persisted)

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

# Deploy to Databricks (build + bundle deploy + grant permissions + run setup + start app)
./deploy.sh [target] [catalog] [schema]
# e.g. ./deploy.sh dev yd_launchpad_final_classic_catalog genie_app

# Deploy bundle only
databricks bundle deploy -t dev

# Databricks CLI uses profile "vm" (configured in databricks.yml)
```

## Package Managers

- **Python**: `uv` (not pip)
- **Frontend**: `bun`
- **Dev tooling**: `apx` toolkit

## Databricks Integration

- **Workspace profile**: `vm` (set in `databricks.yml`)
- **Key services**: Genie API (Databricks SDK `ws.genie.*`), Unity Catalog tables, SQL Statements API, Jobs API
- **State file**: `state.json` — written by setup pipeline, read at app startup via `app_config.get_state()`

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
