# GenieApp — Phase Tracker

## Phase 1: DB Layer + Users + Router Split
- **Status**: complete
- **Branch**: `feature/db-layer-users`
- **Started**: 2026-03-18
- **Completed**: 2026-03-18
- **Key decisions**: User endpoints use Request-based WS client access (not DI) for local dev fallback to anonymous user
- **Deviations from plan**: Kept old `router.py` as dead code (not deleted) for reference during later phases
- **Files created**: `backend/db.py`, `backend/routes/__init__.py`, `routes/chat.py`, `routes/spaces.py`, `routes/tables.py`, `routes/users.py`, `routes/export.py`, `docs/TASKS.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`
- **Files modified**: `backend/app.py` (routes package), `backend/models.py` (UserOut, UserPreferencesIn), `pyproject.toml` (cachetools)
- **Test results**: version ✓, users/me ✓ (anonymous), users/me/preferences ✓, frontend build ✓, all routes registered ✓

## Phase 2: Conversation Persistence
- **Status**: not started
- **Branch**: `feature/conversation-persistence`
- **Started**: —
- **Completed**: —

## Phase 3: Multi-Space + BYOG
- **Status**: not started
- **Branch**: `feature/multi-space-byog`
- **Started**: —
- **Completed**: —

## Phase 4: Image Upload
- **Status**: not started
- **Branch**: `feature/image-upload`
- **Started**: —
- **Completed**: —

## Phase 5: Wire Templates
- **Status**: not started
- **Branch**: `feature/wire-templates`
- **Started**: —
- **Completed**: —

## Phase 6: Frontend Auth
- **Status**: not started
- **Branch**: `feature/frontend-auth`
- **Started**: —
- **Completed**: —

## Phase 7: Production Hardening
- **Status**: not started
- **Branch**: `feature/production-hardening`
- **Started**: —
- **Completed**: —
