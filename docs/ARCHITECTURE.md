# GenieApp — Architecture

## System Overview

Full-stack Databricks app: FastAPI backend + React frontend. Users create/connect Genie Spaces, chat with them via natural language, and view results as charts/tables.

## Backend Modules

```
backend/
├── app.py                  # Entry point — creates FastAPI app
├── app_config.py           # state.json loader (legacy single-space)
├── db.py                   # Data access layer (UC Delta tables via SQL Statements API)
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
├── routes/                 # API route modules (split from router.py)
│   ├── __init__.py         # Aggregates all routers
│   ├── chat.py             # Chat endpoints (sync, async, feedback)
│   ├── spaces.py           # Space CRUD, config, creation
│   ├── tables.py           # Table browsing
│   ├── users.py            # User profile, preferences
│   └── export.py           # Conversation export
└── pipeline/               # Data generation pipeline
```

## Database Schema (UC Delta Tables)

Catalog: `yd_launchpad_final_classic_catalog`, Schema: `genie_app`

### Tables
| Table | Purpose |
|-------|---------|
| `users` | User profiles and preferences |
| `spaces` | Genie Space metadata (evolves from `sessions`) |
| `conversations` | Conversation pointers |
| `messages` | Message metadata (not full result data) |
| `images` | Uploaded image metadata |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/version` | App version |
| GET | `/api/config` | App config (legacy single-space) |
| GET | `/api/users/me` | Current user profile |
| PATCH | `/api/users/me/preferences` | Update user preferences |
| POST | `/api/chat` | Sync chat message |
| POST | `/api/chat/start` | Async chat start |
| GET | `/api/chat/{conv}/{msg}/status` | Poll message status |
| GET | `/api/chat/{conv}/{msg}/result` | Get completed result |
| POST | `/api/chat/feedback` | Send feedback |
| GET | `/api/tables` | List tables |
| GET | `/api/tables/{name}` | Table detail |
| GET | `/api/conversations` | List conversations |
| GET | `/api/conversations/{conv_id}` | Conversation messages |
| POST | `/api/export` | Export conversation |
| GET | `/api/spaces` | List spaces |
| GET | `/api/spaces/{space_id}/config` | Space config |
| POST | `/api/spaces` | Create space (trigger pipeline) |
| GET | `/api/jobs/{run_id}` | Job status |

## Environment Variables
| Var | Description |
|-----|-------------|
| `STATE_FILE_PATH` | Path to state.json (local or /Volumes/) |
| `DATABRICKS_HOST` | Workspace URL |
| `DATABRICKS_TOKEN` | Service principal token |
