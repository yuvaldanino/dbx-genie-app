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

### 2026-06-11 — Fixes implemented (commit 24b3098)

1. **Instruction generator** (`pipeline/instruction_builder.py`): builds rich instructions from LIVE UC metadata — real types, profiled categorical values (DISTINCT on ≤15-cardinality strings), FK joins (PK-name heuristic), date coverage with explicit "do NOT assume data extends to today", money ranges, query tips. Capped 9000ch.
2. **Retune tooling** (`scripts/retune_spaces.py` list/preview/apply/apply-all): ⚠️ **public `PATCH /genie/spaces/{id}` silently ignores `serialized_space.instructions` edits** (verified: PATCH 200 + response echoes old content; sample_questions edits DO persist). The working path is the **internal data-rooms API**: `POST /api/2.0/data-rooms/{sid}/instructions/{iid}` `{title, content, instruction_type}` (the Genie UI's own surface; marker test + revert verified). Internal-API maintenance caveat documented in script. Backups → /tmp/retune_backup. Downgrade guard: refuses to write thin output.
3. **Coca-Cola before/after (measured)**: instructions 301ch → 6996ch. Date-trap "revenue this year" (data ends 2024-12, today 2026-06): SQL now clamps to `<= '2024-12-29'` (was: would query 2026 → empty). "Best product and why": single-metric lookup → multi-metric CTE (revenue+units+orders+avg). Engine reads the data-rooms store ✓.
4. **Parser fix** (Finding 3): collect ALL text attachments; narrative→description, trailing question→new `follow_up_text` field (additive — B's ChatMessageOut literals unaffected, TS field optional); QueryWorkspace renders it as a hint line. start_chat cross-space conversation_id → fresh-conversation fallback (was 500).
5. **Integration note for B's Genie Chat**: render `follow_up_text` as a tappable chip in the thread (post-merge polish; B's PR is frozen by contract).

### 2026-06-11 — Rollout + live verification (deployed from this branch)

- **All 25 active spaces retuned, 100% VERIFIED** (log: /tmp/retune_all.log; backups: /tmp/retune_backup/). Range: Footlocker 17ch→7236ch, Starbucks 237ch→7625ch; several capped at 8993ch (MAX_CHARS — consider bumping later).
- Parser deployed; split heuristic v2 (classify by SHAPE — offer text can arrive before the narrative). Live spot check: `description` = narrative, `follow_up_text` = "Would you prefer…" ✓
- deploy.sh UC grant lines: first all-`OK:` run (profile fix held).
- verify_live: smoke green, history 14/16 with data at ~1.5-2s/conversation, chat flow green.
- **Remaining on this branch**: wire instruction generation into NEW space creation (pipeline currently still uses the old faker-format builder; cleanest = generate server-side on `/api/spaces/register` using instruction_builder, since the app SP now has UC perms). Then PR.

### 2026-06-11 — Finding 1 (measured): live spaces are effectively UNINSTRUCTED

`GET /api/2.0/genie/spaces/{id}?include_serialized_space=true` on Coca-Cola:
- instructions = **280 chars, company description only** — no data dictionary, no types, no FK/categorical info (full payload: `/tmp/parity/space_current.json`)
- 10 sample questions present; tables wired correctly
- Implication: retuning cannot source from `pipeline_state.json` (older spaces lack `tables` there). Better design: generate instructions from **live UC metadata** (ws.tables.get for columns/types/comments + cheap DISTINCT/MIN-MAX sampling for categorical values & ranges) — uniform for all 16 spaces AND fixes the pipeline builder with the same code path.
