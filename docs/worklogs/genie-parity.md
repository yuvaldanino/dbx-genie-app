# Worklog — Session A: P0 #1 Result-quality parity (`feat/genie-parity`)

> Contract: docs/worklogs/PARALLEL_PLAN.md (Session A brief). This is Session A's ONLY doc file during the parallel phase.
> Format per entry: date · what · how verified · decisions/flags for integration.

## Entries

### 2026-06-11 — Diagnosis protocol started (no code changes yet)

Probe: `scripts/parity_probe.py` (committed on this branch) → artifacts in `/tmp/parity/*.json`.
- 5 fixed questions vs Coca-Cola shared space (`01f1441695…`), three captures each:
  `qN_app` (app's parsed result) · `qN_app_raw` (raw GenieMessage for the SAME message) · `qN_native_raw` (direct SDK ask = native-engine baseline)
- Context A/B: same question (`Show me the monthly sales trend`) fresh vs appended to the user's longest conversation (`ab_fresh` / `ab_resumed`)
- Also capturing the space's CURRENT live instructions (evidence of the degraded instruction-builder output)

Verification of claims = artifact diffs, summarized below when probe completes.

### 2026-06-11 — Diagnosis results (artifacts: /tmp/parity/*.json, 5 questions × app/native + A/B)

| # | Finding | Evidence | Implication |
|---|---|---|---|
| 2 | **SQL generation parity is FINE for fresh asks** — 4/5 "different" SQLs are cosmetic only (backticks, aliases, semicolons; q1 diff shown in artifacts), row counts equal | `qN_app.json` vs `qN_native_raw.json` | The engine isn't worse through the app; the gap is instructions + presentation |
| 3 | **Native returns TWO text attachments per answer**: a data narrative (~300-460ch) AND a conversational follow-up offer ("Would you prefer to see…?", ~110-150ch). The app's parser keeps ONE `description` (loop overwrites; single field) → the follow-up texture is always dropped | every `qN_native_raw.json` has 2 texts; `ChatMessageOut` has one description | Fix: parser collects ALL text attachments; additive `ChatMessageOut` field (e.g. `follow_up_text`); render in UI (pairs perfectly with Genie Chat mode) |
| 4 | **Attachment visibility is identity-scoped**: text attachments of SP-created messages are NOT returned to a different identity fetching the same message (verified via raw REST, same ids, 0 text as user vs 298ch desc via app/SP) | q1 refetch experiments | Production-safe (app always fetches as SP). Probe captures labeled `qN_app_raw` under-report — ignore them; trust `qN_app` (SP-parsed) + `qN_native_raw` (user-created) |
| 5 | **Context depth does NOT degrade SQL**: fresh vs 1-deep vs synthetic 7-deep → identical SQL & 36 rows (`ab_long_context.json`). Auto-resume behavior in QueryWorkspace can stay — no conversation-behavior change needed | ab_*.json | Hypothesis closed. BONUS evidence for Finding 3: the 7-deep response's `description` came back as the FOLLOW-UP text ("Would you like to see…?") — i.e., the app randomly surfaces narrative OR dangling counter-question depending on attachment order. Parser fix priority RAISED |
| 6 | **Bug found**: `POST /chat/start` with a conversation_id from another space → unhandled 500 (probe tripped it; a stale `conversationId` URL param can too) | probe log | Defensive fix in chat.py (friendly 400/fresh-start fallback) — A owns chat.py |

### 2026-06-11 — Finding 1 (measured): live spaces are effectively UNINSTRUCTED

`GET /api/2.0/genie/spaces/{id}?include_serialized_space=true` on Coca-Cola:
- instructions = **280 chars, company description only** — no data dictionary, no types, no FK/categorical info (full payload: `/tmp/parity/space_current.json`)
- 10 sample questions present; tables wired correctly
- Implication: retuning cannot source from `pipeline_state.json` (older spaces lack `tables` there). Better design: generate instructions from **live UC metadata** (ws.tables.get for columns/types/comments + cheap DISTINCT/MIN-MAX sampling for categorical values & ranges) — uniform for all 16 spaces AND fixes the pipeline builder with the same code path.
