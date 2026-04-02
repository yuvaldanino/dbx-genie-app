# Genie App — Comprehensive Review Report

**Date**: 2026-03-23
**Reviewers**: 8 specialized agents across 4 domains
**Total Findings**: 85

---

## Executive Summary — Top 10 Critical & High Priority Findings

| # | Severity | Domain | Finding | File |
|---|----------|--------|---------|------|
| 1 | **CRITICAL** | Backend | SQL injection risk — string interpolation without parameterized queries | `db.py:68-70` |
| 2 | **CRITICAL** | Databricks | `ws.config.token` used with raw `requests` — breaks non-PAT auth in production | `pipeline/space_creator.py:212-217` |
| 3 | **CRITICAL** | Databricks | Hardcoded warehouse ID ignores provisioned env var | `db.py:17` + `app.yaml:15` |
| 4 | **CRITICAL** | Data Quality | SQL injection in dashboard notebook — LLM output interpolated into SQL | `scripts/pipeline/04_create_dashboard.ipynb` |
| 5 | **CRITICAL** | Data Quality | FK fallback generates random invalid references | `pipeline/data_generator.py:77-81` |
| 6 | **HIGH** | Backend | Anonymous user fallback — most endpoints accessible without auth | `routes/chat.py:51`, `spaces.py:44` |
| 7 | **HIGH** | Backend | No ownership checks — users can delete/read/modify other users' resources | `routes/spaces.py:271`, `export.py:19` |
| 8 | **HIGH** | Backend | Race condition in `get_or_create_user` — duplicate records | `db.py:188-243` |
| 9 | **HIGH** | Frontend | Polling loop not cancellable on unmount — memory leak | `useChatFlow.ts:94-171` |
| 10 | **HIGH** | Databricks | Hardcoded `databricks_host_id` in 6+ locations — non-portable | Multiple files |

---

## Section 1: Backend Integrity (23 findings)

### Critical (1)

**B1. SQL Injection via String Interpolation**
- `src/genieapp/backend/db.py:68-70`
- `_escape()` handles backslashes and single quotes only. While sufficient for Databricks SQL today, the entire approach is architecturally fragile — every new query must remember to call `_escape()`.
- **Fix**: Migrate to parameterized queries via SQL Statements API `parameters` field.

### High (5)

**B2. Anonymous User Fallback Enables Unauthenticated Access**
- `routes/chat.py:51-53`, `spaces.py:44-46`, `upload.py:21-23`
- `_get_user_id()` falls back to `"anonymous"` — all endpoints except BYOG proceed without auth. All anonymous users share one identity.
- **Fix**: Add middleware rejecting requests without `X-Forwarded-User` (except `/health`, `/version`).

**B3. No Ownership Checks on Mutating Operations**
- `routes/spaces.py:271` (delete), `:256` (update template), `export.py:19`, `chat.py:276`
- Any user can delete spaces, change templates, read conversations, and export data belonging to other users.
- **Fix**: Verify `owner_user_id` matches requesting user before proceeding.

**B4. Debug Endpoint Exposes Internal Data**
- `routes/spaces.py:426-441`
- `GET /api/spaces/debug` dumps entire sessions table with no auth.
- **Fix**: Remove or gate behind admin auth.

**B5. Race Condition in `get_or_create_user`**
- `db.py:188-243`
- Check-then-insert is not atomic — concurrent requests create duplicate users.
- **Fix**: Use `MERGE INTO ... WHEN NOT MATCHED THEN INSERT`.

**B6. Hardcoded Job ID**
- `routes/spaces.py:452`
- `job_id = 381399907081683` breaks if job is recreated or workspace changes.
- **Fix**: Move to environment variable.

### Medium (10)

| ID | Finding | File |
|----|---------|------|
| B7 | Header spoofing in non-proxy environments | `core/_headers.py:23-39` |
| B8 | Internal error details leaked to clients | `db.py:53`, `spaces.py:163`, `upload.py:64` |
| B9 | File upload: content-type trust, SVG XSS, filename injection | `routes/upload.py:26-86` |
| B10 | Feedback endpoint uses wrong space_id (state.json singleton) | `routes/chat.py:234-248` |
| B11 | Unhandled exceptions in `start_chat` async flow | `routes/chat.py:156-179` |
| B12 | `get_job_status` crashes on non-integer run_id | `routes/spaces.py:482` |
| B13 | Export endpoint has no auth check | `routes/export.py:19-48` |
| B14 | Race condition in `_persist_message_start` | `routes/chat.py:79-95` |
| B15 | Race condition in `create_space` (BYOG) | `db.py:474-524` |
| B16 | Hardcoded catalog/schema/warehouse in db.py | `db.py:15-17` |

### Low (7)

| ID | Finding | File |
|----|---------|------|
| B17 | No CORS middleware | `core/_factory.py` |
| B18 | No rate limiting (especially on job creation) | All routes |
| B19 | No input length validation on chat questions | `models.py:60` |
| B20 | SPA 404 returns plain text, not JSON | `core/_static.py:31` |
| B21 | TTL cache stale in multi-worker deployment | `db.py:27-28` |
| B22 | `ensure_tables` failure silently swallowed | `app.py:21-22` |
| B23 | SQL Statements API 50s timeout with no retry | `db.py:48` |

---

## Section 2: Frontend UI (40 findings)

### Critical (3)

**F1. Polling Loop Not Cancellable on Unmount**
- `src/genieapp/ui/lib/useChatFlow.ts:94-171`
- Async `while` loop continues after component unmounts — memory leak, setState on unmounted component.
- **Fix**: Use `AbortController` ref, check `signal.aborted` each iteration, pass signal to axios.

**F2. Race Condition on Rapid Message Sends**
- `useChatFlow.ts:174-231`
- `msgIndex = messages.length` captured at call time — two rapid sends get same index, second overwrites first.
- **Fix**: Use ref-based counter or unique message IDs, update by ID not index.

**F3. No `<label htmlFor>` Associations on Form Inputs**
- `routes/index.tsx:163-171`, `spaces.tsx:145-151`, `PreferencesPanel.tsx:76-91`
- Screen readers can't determine which label belongs to which input.
- **Fix**: Add matching `id`/`htmlFor` pairs.

### High (6)

| ID | Finding | File |
|----|---------|------|
| F4 | Stale closure over `messages.length` in sendMessage | `useChatFlow.ts:231` |
| F5 | Silent error swallowing in polling loop (empty catch) | `useChatFlow.ts:136-138` |
| F6 | Space cards are clickable divs — not keyboard accessible | `spaces.tsx:269-304` |
| F7 | WelcomeScreen sample questions not keyboard accessible | `WelcomeScreen.tsx:43-53` |
| F8 | GenieDrawer has no focus trap or Escape-to-close | `GenieDrawer.tsx:39-153` |
| F9 | PreferencesPanel has no focus trap or Escape handling | `PreferencesPanel.tsx:62-119` |

### Medium (16)

| ID | Finding | File |
|----|---------|------|
| F10 | Sidebar not collapsible on mobile — no responsive layout | `_sidebar/route.tsx:104-303` |
| F11 | QueryWorkspace left sidebar fixed 320px, no collapse | `QueryWorkspace.tsx:142` |
| F12 | No error state when API config fails — infinite spinner | `_sidebar/chat.tsx:33-38` |
| F13 | Missing aria-labels on all icon-only buttons | Multiple files |
| F14 | DataTable has no accessible table semantics | `DataTable.tsx:23-53` |
| F15 | `coerceNumeric` runs on every render (unmemoized) | `ChartRenderer.tsx:62-67` |
| F16 | `useMemo` used for side effect in MapRenderer | `MapRenderer.tsx:33-39` |
| F17 | No error boundary around chart/map rendering | `ChartRenderer.tsx`, `MapRenderer.tsx` |
| F18 | Landing page polling loop same unmount issue | `routes/index.tsx:84-132` |
| F19 | Silent feedback loss — `useSendFeedback` no error handling | `MessageBubble.tsx:74-79` |
| F20 | `BrandThemeInjector` doesn't react to system theme changes | `BrandThemeInjector.tsx:20-26` |
| F21 | No toast on BYOG success or preference save | `spaces.tsx:66`, `PreferencesPanel.tsx:40` |
| F22 | ExportButton silently fails (no catch block) | `ExportButton.tsx:23-36` |
| F23 | `handleExportChart` is dead code | `ExportButton.tsx:38-48` |
| F24 | MapRenderer popup uses hardcoded gray colors | `MapRenderer.tsx:89-92` |
| F25 | Recharts Tooltip doesn't respect dark mode | `ChartRenderer.tsx:162-213` |

### Low (15)

| ID | Finding | File |
|----|---------|------|
| F26 | Textarea on landing page has no accessible label | `index.tsx:270-276` |
| F27 | Color picker inputs have no accessible labels | `spaces.tsx:165-170` |
| F28 | Logo upload toggle lacks aria-pressed | `index.tsx:180-207` |
| F29 | Template selector buttons lack group semantics | `spaces.tsx:203-219` |
| F30 | DataTable renders all 100 rows without virtualization | `DataTable.tsx:37-45` |
| F31 | `handleExportChart` uses global DOM selector | `ExportButton.tsx:38-48` |
| F32 | QueryWorkspace sidebar cards use array index as key | `QueryWorkspace.tsx:194, 265` |
| F33 | No `staleTime` on `useConversationMessages` hook | `api.ts:292-301` |
| F34 | AuthProvider context value not memoized | `AuthProvider.tsx:25-28` |
| F35 | SyntaxHighlighter always uses `oneDark` regardless of theme | `MessageBubble.tsx:156-168` |
| F36 | No skip-to-content link for keyboard nav | `__root.tsx` |
| F37 | No "empty" hint when conversation history is empty | `_sidebar/route.tsx:207` |
| F38 | Keyboard shortcut hint missing for chat input | `QueryWorkspace.tsx:367-373` |
| F39 | `useMemo` for side effect (duplicate of F16) | `MapRenderer.tsx:33-38` |
| F40 | Landing page decorative blobs may cause overflow flicker | `index.tsx:146-147` |

---

## Section 3: Databricks SDK & Resources (28 findings)

### Critical (3)

**D1. `ws.config.token` Used with Raw `requests` Library**
- `pipeline/space_creator.py:212-217`
- Bypasses SDK auth (token refresh, OAuth, SP auth). Breaks in production Databricks Apps.
- **Fix**: Replace with `ws.api_client.do("POST", "/api/2.0/genie/spaces", body=payload)`.

**D2. Hardcoded Warehouse ID Ignores Provisioned Env Var**
- `db.py:17` + `app.yaml:15`
- `app.yaml` provisions `DATABRICKS_WAREHOUSE_ID` but code uses hardcoded `551addcb4415adb7`.
- **Fix**: `WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "551addcb4415adb7")`.

**D3. Hardcoded `databricks_host_id` in 6+ Locations**
- `create_space_job.yml:16`, `routes/spaces.py:463`, `router.py:558`, `scripts/run_pipeline.py:23`, `scripts/test_faker.py:25`
- Ties entire pipeline to one workspace.
- **Fix**: Add as bundle variable, read from env in Python.

### High (5)

| ID | Finding | File |
|----|---------|------|
| D4 | Hardcoded LLM model name in 5+ locations | Multiple files |
| D5 | Hardcoded catalog not passed from bundle to app | `db.py:15`, `app.yaml:13` |
| D6 | No cluster/compute config on job definitions | `setup_job.yml`, `create_space_job.yml` |
| D7 | Genie Space permission grant may use wrong API path | `deploy.sh:75` |
| D8 | Hardcoded service principal ID in pipeline notebook | `scripts/pipeline/03_create_space.ipynb` |

### Medium (11)

| ID | Finding | File |
|----|---------|------|
| D9 | Using `ws.api_client.do()` instead of SDK `statement_execution` | `db.py:45` |
| D10 | `run_sql` treats RUNNING/PENDING as success | `db.py:51` |
| D11 | Missing pagination for large Genie query results | `genie_client.py:200-230` |
| D12 | `deploy.sh` reads local `state.json` that remote job doesn't write | `deploy.sh:68-72` |
| D13 | `deploy.sh` missing `CREATE_TABLE` grant | `deploy.sh:55` |
| D14 | `create_space_job` allows 10 concurrent runs — collision risk | `create_space_job.yml:6` |
| D15 | Notebooks use `requests` directly instead of SDK | `scripts/03_setup_genie.ipynb` |
| D16 | SCIM preview API used instead of stable SDK | `scripts/03_setup_genie.ipynb` |
| D17 | Hardcoded warehouse ID fallback in setup notebook | `scripts/03_setup_genie.ipynb` |
| D18 | `ws.config.token` may be None for non-PAT auth | `space_creator.py:214` |
| D19 | `_classify_error` not used for Genie-reported errors | `genie_client.py:56` |

### Low (9)

| ID | Finding | File |
|----|---------|------|
| D20 | Only one deployment target (`dev`) defined | `databricks.yml:29-34` |
| D21 | `app.yaml` hardcodes Volume path for STATE_FILE_PATH | `app.yaml:13` |
| D22 | `setup_job` has no `max_concurrent_runs` limit | `setup_job.yml` |
| D23 | Pipeline `_run_sql` logs but doesn't raise on failure | `space_creator.py:39-42` |
| D24 | Batch INSERT size of 200 is appropriate | `space_creator.py:119` |
| D25 | `dbutils.fs.put` vs SDK `ws.files.upload` inconsistency | Notebooks |
| D26 | `GenieMessage.message_id or resp.id` field access order | `genie_client.py:166` |
| D27 | No timeout handling in Genie client sync calls | `genie_client.py:41-46` |
| D28 | SQL Statements API 50s timeout with no retry | `db.py:48` |

---

## Section 4: Data Quality & Dashboards (21 findings)

### Critical (2)

**Q1. SQL Injection in Dashboard Notebook**
- `scripts/pipeline/04_create_dashboard.ipynb` (cell 6)
- LLM-generated `dashboard_json` (containing SQL) is string-interpolated into an UPDATE statement.
- **Fix**: Use parameterized queries or DataFrame API.

**Q2. FK Fallback Generates Random Invalid References**
- `pipeline/data_generator.py:77-81`
- When referenced table not found, falls back to `random_int(1, 100)` — broken joins.
- **Fix**: Raise error instead of silent fallback. Validate FK targets in schema.

### High (3)

| ID | Finding | File |
|----|---------|------|
| Q3 | No schema validation after LLM response | `schema_designer.py:161-165` |
| Q4 | No cleanup on partial pipeline failure — orphaned resources | `pipeline/run.py:72-182` |
| Q5 | Failed dashboard panels silently dropped, empty dashboard stored | `scripts/pipeline/04_create_dashboard.ipynb` |

### Medium (9)

| ID | Finding | File |
|----|---------|------|
| Q6 | No retry on LLM failure or malformed output | `schema_designer.py:138-165` |
| Q7 | Prompt doesn't constrain row_count (LLM could return 1M) | `schema_designer.py:96` |
| Q8 | No null value generation — unrealistically complete data | `data_generator.py:50-123` |
| Q9 | No contrast validation on LLM-generated colors | `theme_generator.py:91-110` |
| Q10 | Chart color padding duplicates primary color | `theme_generator.py:99-101` |
| Q11 | `_is_numeric_column` short-circuits on first sample value | `chart_suggest.py:25-39` |
| Q12 | All non-numeric columns become categories as fallback | `chart_suggest.py:104-106` |
| Q13 | Product prices regenerated independently in legacy notebook | `scripts/01_generate_data.ipynb` |
| Q14 | DashboardView doesn't handle `map`/`table` panel types | `DashboardView.tsx:52` |

### Low (7)

| ID | Finding | File |
|----|---------|------|
| Q15 | Pipeline not idempotent — re-runs create duplicates | `pipeline/run.py` |
| Q16 | Company name extraction is fragile | `pipeline/run.py:83-84` |
| Q17 | No explicit normalization guidance in LLM prompt | `schema_designer.py:72-111` |
| Q18 | No TIMESTAMP Faker provider | `schema_designer.py:16-70` |
| Q19 | No hex format validation on LLM color output | `theme_generator.py:91-96` |
| Q20 | Geo detection requires exact column name match | `chart_suggest.py:82-95` |
| Q21 | Pie chart threshold uses row count, not unique category count | `chart_suggest.py:120` |

---

## Prioritized Action Plan

### Phase 1: Critical Security Fixes (do first)
1. **Add auth middleware** — reject requests without `X-Forwarded-User` (B2)
2. **Add ownership checks** on all resource endpoints (B3, B7, B13)
3. **Remove debug endpoint** (B4)
4. **Fix `ws.config.token` usage** — use `ws.api_client.do()` instead of `requests` (D1, D18)
5. **Fix SQL injection in dashboard notebook** — use parameterized queries (Q1)
6. **Fix FK fallback** — raise error instead of random values (Q2)

### Phase 2: High-Impact Infrastructure (do next)
7. **Parameterize hardcoded values** — warehouse ID, catalog, schema, host ID, LLM model (D2, D3, D4, D5, B16)
   - Read from env vars with current values as defaults
   - Single change addresses 5+ findings
8. **Fix polling loop memory leaks** — add AbortController to `useChatFlow` and landing page (F1, F18)
9. **Fix rapid-send race condition** — use message IDs instead of array indices (F2)
10. **Add LLM output validation** — schema validation, panel validation, hex color validation (Q3, Q6)
11. **Fix race conditions in DB layer** — use MERGE for create-or-get patterns (B5, B14, B15)

### Phase 3: Production Hardening (next sprint)
12. **Add error boundaries** around chart/map rendering (F17)
13. **Fix error handling in polling** — break on consecutive failures, surface errors (F5)
14. **Add explicit compute config** to job definitions (D6)
15. **Fix `deploy.sh`** — fetch state.json from Volume, add CREATE_TABLE grant (D12, D13)
16. **Sanitize error messages** — generic client errors, detailed server logs (B8)
17. **File upload hardening** — magic byte validation, SVG sanitization (B9)
18. **Add rate limiting** on chat and space creation endpoints (B18)

### Phase 4: UX & Accessibility (ongoing)
19. **Keyboard accessibility** — focusable cards, focus traps, Escape handlers (F6-F9)
20. **Form accessibility** — label associations, aria-labels, role attributes (F3, F13, F14)
21. **Responsive design** — collapsible sidebar, mobile layout (F10, F11)
22. **Error/empty states** — replace infinite spinners with error messages (F12, F21, F22)
23. **Dark mode consistency** — themed tooltips, code blocks, map popups (F24, F25, F35)

### Quick Wins (< 30 min each)
- `WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "551addcb4415adb7")` — 1 line fix (D2)
- Remove `GET /api/spaces/debug` endpoint — delete ~15 lines (B4)
- Add `Field(max_length=10000)` to `ChatMessageIn.question` (B19)
- Return `JSONResponse` for API 404s (B20)
- Add `aria-label` to icon-only buttons (F13)
- Remove dead `handleExportChart` code (F23)
- Change `useMemo` to `useEffect` in MapRenderer (F16)
- Add `staleTime: 10_000` to `useConversationMessages` (F33)
- Add `scope="col"` to DataTable `<th>` elements (F14)

---

## Findings by Severity

| Severity | Count | Breakdown |
|----------|-------|-----------|
| **Critical** | 5 | Backend: 1, Databricks: 3, Data Quality: 2 |
| **High** | 14 | Backend: 5, Frontend: 6, Databricks: 5, Data Quality: 3 |
| **Medium** | 39 | Backend: 10, Frontend: 16, Databricks: 11, Data Quality: 9 |
| **Low** | 27 | Backend: 7, Frontend: 15, Databricks: 9, Data Quality: 7 |
| **Total** | **85** | |
