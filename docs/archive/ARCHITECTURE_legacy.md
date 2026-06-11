# GenieApp — Architecture

## System Overview

Multi-user Databricks app: FastAPI backend + React frontend. Users create/connect Genie Spaces, choose UI templates, chat via natural language, view results as charts/tables. Persistent conversations across restarts.

## Backend Modules

```
backend/
├── app.py                  # Entry point — creates app, ensure_tables on startup
├── app_config.py           # state.json loader (legacy single-space fallback)
├── db.py                   # Data access layer (UC Delta tables via SQL Statements API)
│                           # Functions: ensure_tables, user CRUD, conversation CRUD,
│                           # message CRUD, space CRUD, TTL caches
├── chart_suggest.py        # Heuristic chart type suggestion
├── genie_client.py         # Databricks Genie API wrapper
├── models.py               # All Pydantic request/response models
├── core/                   # APX framework internals
├── routes/                 # API route modules
│   ├── chat.py             # Chat, feedback, conversations, version, health
│   ├── spaces.py           # Space CRUD, BYOG, config, template, jobs
│   ├── tables.py           # Table browsing, app config
│   ├── users.py            # User profile, preferences
│   ├── upload.py           # Image upload/retrieval
│   └── export.py           # Conversation export
├── router.py               # Legacy monolithic router (dead code)
└── pipeline/               # Data generation pipeline
```

## Frontend Structure

```
ui/
├── lib/
│   ├── api.ts              # API client (axios + React Query hooks)
│   └── useChatFlow.ts      # Reusable chat polling hook
├── components/apx/
│   ├── AuthProvider.tsx     # User auth context
│   ├── PreferencesPanel.tsx # Theme + template preferences
│   ├── TemplateRenderer.tsx # Lazy template loader
│   ├── template-testing/   # 5 demo templates + mock data
│   ├── ChartRenderer.tsx   # Chart rendering
│   ├── DataTable.tsx        # Table rendering
│   ├── MessageBubble.tsx   # Chat message component
│   └── ...
├── routes/
│   ├── __root.tsx          # Root layout (ThemeProvider + AuthProvider)
│   ├── index.tsx           # Landing / space creation
│   ├── spaces.tsx          # Space list
│   └── _sidebar/
│       ├── route.tsx       # Sidebar layout (nav, tables, history, user info)
│       ├── chat.tsx        # Chat page
│       └── templates.tsx   # Template picker
└── components/ui/          # shadcn/ui primitives
```

## Database Schema (UC Delta Tables)

Catalog: `yd_launchpad_final_classic_catalog`, Schema: `genie_app`

### `users`
| Column | Type | Notes |
|--------|------|-------|
| user_id | STRING | From X-Forwarded-User. Application-enforced PK |
| email | STRING | From X-Forwarded-Email |
| username | STRING | From X-Forwarded-Preferred-Username |
| default_template | STRING | simple/widget/dashboard/command/workspace |
| preferences_json | STRING | Extensible JSON blob |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### `spaces`
| Column | Type | Notes |
|--------|------|-------|
| space_id | STRING | Genie Space ID. Application-enforced PK |
| owner_user_id | STRING | FK to users |
| company_name | STRING | |
| description | STRING | |
| schema_name | STRING | UC schema (NULL for BYOG) |
| space_type | STRING | generated or byog |
| template_id | STRING | UI template |
| logo_volume_path | STRING | UC Volume path |
| primary_color, secondary_color, accent_color | STRING | |
| chart_colors_json | STRING | JSON array |
| tables_json | STRING | JSON array |
| sample_questions_json | STRING | JSON array |
| warehouse_id | STRING | |
| is_active | BOOLEAN | Soft delete |
| created_at, updated_at | TIMESTAMP | |

### `conversations`
| Column | Type | Notes |
|--------|------|-------|
| conversation_id | STRING | From Genie API |
| space_id | STRING | FK to spaces |
| user_id | STRING | FK to users |
| title | STRING | First question, truncated |
| message_count | INT | |
| is_archived | BOOLEAN | |
| created_at, updated_at | TIMESTAMP | |

### `messages`
| Column | Type | Notes |
|--------|------|-------|
| message_id | STRING | From Genie API |
| conversation_id | STRING | FK to conversations |
| user_id | STRING | FK to users |
| question | STRING | User's question |
| status | STRING | COMPLETED, FAILED, etc. |
| sql_text | STRING | Generated SQL |
| description | STRING | Genie text response |
| is_clarification | BOOLEAN | |
| feedback_rating | STRING | POSITIVE or NEGATIVE |
| created_at | TIMESTAMP | |

### `images`
| Column | Type | Notes |
|--------|------|-------|
| image_id | STRING | UUID |
| user_id | STRING | FK to users |
| space_id | STRING | FK to spaces (nullable) |
| filename | STRING | Original filename |
| content_type | STRING | MIME type |
| volume_path | STRING | /Volumes/... path |
| size_bytes | BIGINT | |
| created_at | TIMESTAMP | |

## Caching Strategy
- **Frontend**: React Query with `staleTime: Infinity` for config, `30s` for space lists
- **Backend**: `cachetools.TTLCache` — user profile (5min), space list (30s)
- **Conversation data**: Metadata in DB, full result data from Genie API on-demand

## Auth Flow
1. Databricks Apps proxy injects `X-Forwarded-User`, `X-Forwarded-Email`, `X-Forwarded-Access-Token`
2. `GET /api/users/me` → upserts user in DB, returns profile
3. BYOG validation uses user's OBO token (`X-Forwarded-Access-Token`)
4. Local dev: headers absent → anonymous user fallback
