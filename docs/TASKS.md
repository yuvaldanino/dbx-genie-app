# GenieApp — Phase Tracker

## Phase 1: DB Layer + Users + Router Split
- **Status**: complete
- **Branch**: `feature/db-layer-users`
- **Started**: 2026-03-18
- **Completed**: 2026-03-18
- **Key decisions**: User endpoints use Request-based WS client access for local dev anonymous fallback
- **Files created**: `backend/db.py`, `backend/routes/` package (chat, spaces, tables, users, export), `docs/` (TASKS, ARCHITECTURE, DECISIONS)
- **Files modified**: `backend/app.py`, `backend/models.py`, `pyproject.toml`

## Phase 2: Conversation Persistence
- **Status**: complete
- **Branch**: `feature/conversation-persistence`
- **Started**: 2026-03-18
- **Completed**: 2026-03-18
- **Key decisions**: DB writes are best-effort (don't block chat flow), store metadata only (not full data arrays)
- **Files modified**: `backend/db.py` (conversation/message CRUD), `routes/chat.py` (DB-backed), `routes/export.py`

## Phase 3: Multi-Space + BYOG
- **Status**: complete
- **Branch**: `feature/multi-space-byog`
- **Started**: 2026-03-18
- **Completed**: 2026-03-18
- **Key decisions**: BYOG validates via OBO token, fallback chain: spaces → sessions → state.json
- **Files modified**: `db.py` (space CRUD), `routes/spaces.py` (BYOG, template, delete), `models.py`

## Phase 4: Image Upload
- **Status**: complete
- **Branch**: `feature/image-upload`
- **Started**: 2026-03-18
- **Completed**: 2026-03-18
- **Files created**: `routes/upload.py`
- **Files modified**: `routes/__init__.py`, `pyproject.toml` (python-multipart)

## Phase 5: Wire Templates
- **Status**: complete
- **Branch**: `feature/wire-templates`
- **Started**: 2026-03-18
- **Completed**: 2026-03-18
- **Files created**: `ui/lib/useChatFlow.ts`, `ui/components/apx/TemplateRenderer.tsx`
- **Files modified**: `ui/lib/api.ts`, `ui/routes/_sidebar/chat.tsx`, `ui/routes/_sidebar/templates.tsx`

## Phase 6: Frontend Auth
- **Status**: complete
- **Branch**: `feature/frontend-auth`
- **Started**: 2026-03-18
- **Completed**: 2026-03-18
- **Files created**: `ui/components/apx/AuthProvider.tsx`, `ui/components/apx/PreferencesPanel.tsx`
- **Files modified**: `ui/routes/__root.tsx`, `ui/routes/_sidebar/route.tsx`

## Phase 7: Production Hardening
- **Status**: complete
- **Branch**: `feature/production-hardening`
- **Started**: 2026-03-18
- **Completed**: 2026-03-18
- **Files modified**: `backend/app.py` (ensure_tables on startup), `routes/chat.py` (health endpoint), `CLAUDE.md`
