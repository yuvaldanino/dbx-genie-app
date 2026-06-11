# PROJECT_STATE.md — Genie-rator Handoff Document

> **Audience**: A fresh Claude session picking up this project on the `agent-overhaul` branch.
> **Last updated**: 2026-06-11. Baseline tag: `v2-stable` (rollback: `git checkout v2-stable`).
>
> **Doc map**: this file = state/bugs/roadmap · [`OPERATIONS.md`](OPERATIONS.md) = deploy/test/recovery · [`ARCHITECTURE.md`](ARCHITECTURE.md) = system design + complete data-store/services/auth map · [`UI_UPDATES.md`](UI_UPDATES.md) = UI change log + sandbox-first pattern · [`../CLAUDE.md`](../CLAUDE.md) = hard rules, dev commands, full API table · `archive/` = historical background only

## What this app is

**Genie-rator** — multi-user Databricks App for Field Engineers. An FE enters a company name + description + must-answer questions → a pipeline generates realistic fake data, creates UC tables, a Genie Space, and a branded chat UI (logo, brand colors, charts). FEs use it to demo Genie to customers with the *customer's own branding and domain*.

Live app: https://genieapp-dev-7474655921234161.aws.databricksapps.com
~16 spaces exist (Nike, Coca-Cola, Starbucks, Porsche, GitHub, etc.). Read `CLAUDE.md` for architecture, `OPERATIONS.md` for deploy/test procedures.

## Current state: WORKING and verified

As of 2026-06-11, post-integration of PR #1 (Genie Chat) + PR #2 (parity) into `agent-overhaul` (merge `412f598`):
- **P0 #1, #2, #3 are DONE and live.** P0 #4 (polish sweep) remains.
- Smoke green (16 spaces), history loads ~2s/conversation with full data (14/16 completed-with-SQL; was 3/15 pre-fix), chat flow green
- All 25 Genie spaces carry rich auto-generated instructions; new spaces auto-enrich on register
- App SP has real UC grants (it had NONE before 2026-06-11 — deploy.sh grant JSON was broken since inception)
- The parallel two-session experiment worked: zero merge conflicts, both worklogs in `docs/worklogs/`

## Production incident history (read this — patterns repeat)

| Incident | Root cause | Fix |
|---|---|---|
| "Data disappeared, only Acme shows" (x2) | Postgres pool captured OAuth token once at startup; token expires ~1h; pool reconnects fail silently → app falls back to state.json | `pg.py` rewritten: per-connection token mint, 30min token cache, 50min conn TTL, SELECT 1 validation only when idle >30s, 2-conn pre-warm. Tests: `scripts/test_pg_pool_logic.py` |
| "Chat stuck on Processing forever" | `/chat/result` used user OBO token for Genie API; platform began enforcing `genie` OAuth scope which OBO tokens lack → 403 → unhandled 500 | `chat.py`: dropped OBO, uses SP client (like `/status` always did), wrapped in try/except returning structured error |
| 10s+ tail latencies | v1 of pool fix ran SELECT 1 network roundtrip on EVERY checkout | Hot-path skip: validate only if idle >30s |
| App SP had ZERO UC grants (found 2026-06-11) | deploy.sh's hand-rolled JSON escaped backticks as `\`` (invalid JSON) → CLI rejected every GRANT since the script existed; "WARN (ERROR)" was misread as "grant already exists" noise → SQL re-execution fallback silently failed for all expired results | Grants applied (catalog-level USE CATALOG/USE SCHEMA/SELECT + genie_app MODIFY + volume RW); deploy.sh run_sql rebuilt with json.dumps and loud FAILED output |

**The meta-pattern**: every incident was a long-lived credential trusted forever with no fallback. When touching auth/tokens/connections, always ask: what happens when this expires mid-flight?

## North star (set by user, 2026-06-11)

> The app must feel as **smooth and trustworthy as the native Databricks Genie experience**. Right now it feels janky — good idea, weak execution polish. The user wants to be *proud* to share this with all of Databricks. Every change should be judged against: "does this make it feel more like the Databricks ecosystem, and do users always get good results?"

The two biggest user-reported problems, verbatim:
1. "Sometimes the results are absolute garbage" — and **the same Genie space gives noticeably better answers on the native Databricks Genie page than through this app**. Closing that gap is the #1 quality goal.
2. Old conversations "tweak out": you open a recent question and get text + SQL but **no graphs/data**.

## Improvement roadmap (re-prioritized with user, 2026-06-11)

### P0 — The big four (work these first)

#### 1. Result-quality parity with native Genie — ✅ DONE 2026-06-11 (PR #2)
Diagnosis-driven (evidence: `docs/worklogs/genie-parity.md`, probe: `scripts/parity_probe.py`). Verdicts: SQL generation parity was FINE; context depth harmless (auto-resume stays). The real gaps, all fixed:
- **All 25 spaces were effectively uninstructed** → `pipeline/instruction_builder.py` generates rich instructions from live UC metadata (real types, profiled values, FK joins, date coverage); `scripts/retune_spaces.py` applied to all 25 (verified); **new spaces auto-enrich on `/api/spaces/register`** (background, downgrade-guarded)
- **Parser kept only the LAST text attachment** → UI randomly showed Genie's "Would you prefer…?" offer INSTEAD of the answer. Now: all texts collected, narrative→`description`, offer→`follow_up_text` (rendered as 💡 hint in QueryWorkspace + MessageBubble)
- ⚠️ The public `PATCH /genie/spaces/{id}` **silently ignores instruction edits** — instruction writes go through the internal data-rooms API (see instruction_builder.py docstring)
- Measured: "revenue this year" now clamps to real data bounds (was: empty garbage); date-trap class of questions fixed
- Deferred to later: generated-data realism improvements (assess demo quality first)
- Verify on next pipeline run: data-rooms instruction write as the app SP (retunes ran as the user)

#### 3. Embedded "Genie Chat" mode — ✅ DONE 2026-06-11 (PR #1, built by parallel Session B)
New sidebar nav "Genie Chat" → `/genie-chat?spaceId=…` — ephemeral ChatGPT-style thread per space (continuous conversation_id, not persisted, New-chat resets via key bump). `GenieChatThread.tsx` composes MessageBubble/useChatFlow without modifying them. Evidence: `docs/worklogs/genie-chat-mode.md`.

#### (original diagnosis notes for #1, kept for history)
The same space answers better at databricks.com/genie than through the app. Code-reading findings (2026-06-11) updated this diagnosis plan:
- **Conversation context — hypothesis REVERSED by code reading**: `useChatFlow.ts` DOES reuse `conversation_id`, and QueryWorkspace auto-resumes the user's most recent conversation on page load (`QueryWorkspace.tsx:59-62`). The risk is the opposite of what was assumed: one ever-growing conversation accumulating weeks of stale demo context that pollutes new questions. A/B test live: same question in fresh vs long-resumed conversation, native vs app.
- **Genie space instructions — CONFIRMED broken, concrete fix known**: `build_genie_instructions` (notebook 03 + `space_creator.py`) keys on the old `faker`/`args` schema format, but `schema_designer.py` v3 emits `type`/`references`. Result for every v3 space: all columns listed as STRING, Relationships section always empty, Categorical Values always empty, generic query tips. Fix the builder for v3 format + **retune the ~16 existing spaces** by PATCHing their live instructions (user approved 2026-06-11; test on one space, verify before/after).
- **Response handling**: `_parse_genie_response` keeps only the LAST text and LAST query attachment (loop overwrites); native UI shows all. Also uses the legacy non-attachment-scoped `get_message_query_result` — newer API is attachment-scoped. Compare raw `GenieMessage` payloads native vs app.
- **Result truncation**: check `is_truncated` handling and row limits; the app may render partial data without saying so.
- **Space config extras**: example SQL per must-answer question, column descriptions on UC tables (column comments DO survive today; types/relationships don't).
- **Generated data realism** feeds this too: uniform fake data → boring/garbage answers. Improve distributions (seasonality, power-law, regional correlation), FK consistency, plausible time series (`data_generator_llm.py` spec prompts).

#### 2. Old conversations lose graphs → recompute + precompute — ✅ DONE 2026-06-11
Root cause chain turned out to be THREE layers, all fixed and verified live (14/15 old messages now return full data, was 3/15):
- ✅ `/conversations/{conv_id}` used OBO token → 403 (`genie` scope) → silent metadata-only. Fixed: uses `ws` (SP).
- ✅ **deploy.sh UC grants had never actually applied** (JSON escaping bug, see incident table) — so the `_reexecute_sql()` fallback for expired results always failed with INSUFFICIENT_PERMISSIONS. Fixed: grants applied + script rebuilt.
- ✅ `_reexecute_sql` gave up at 50s (cold warehouse = silent empty). Now raises on failure and accepts a poll budget; recompute path polls up to 180s extra.
- ✅ `POST /api/chat/{conv}/{msg}/recompute` (re-runs persisted sql_text, no Genie round-trip) + QueryWorkspace UI: per-message Recompute button, amber "Expired" badge, "Recompute all (N)" in Recent tab. These are now the *recovery* layer — with grants fixed, history re-fetch mostly self-heals inline.
- **Follow-up (open)**: history load re-fetches messages serially — 40s for a 13-message conversation. Parallelize per-message fetch in `get_conversation_messages_endpoint` (ThreadPoolExecutor) → ~max(single fetch).

#### ~~3. Embedded "Genie Chat" mode~~ → done, see above. Three modes per space now live: Genie Chat (free conversation), Chat workspace (saved/starred queries, recents), Dashboard (precomputed + drawer).

#### 4. Smoothness / Databricks-ecosystem polish pass — ✅ DONE 2026-06-11
- **Warehouse cold-start UX**: `POST /api/warehouse/wake` fires a background SELECT 1; called once on app load (AuthProvider) so the warehouse warms before the first question. `PENDING_WAREHOUSE` status now says "Warehouse warming up — first query can take a minute or two…"
- **Skeletons** (no more blank-then-pop): Recent tab while a conversation rebuilds, result panel, spaces grid, sidebar tables, dashboard (KPI row + chart panels)
- **Errors surfaced**: sonner toasts (already installed) wired to recompute failures; create-space surfaces the server's friendly `detail` instead of axios generic text
- **Feedback bug FIXED**: 👍/👎 resolves space from body → conversation → state.json (was state.json-only = silently broken for all non-default spaces); MessageBubble passes spaceId for ephemeral threads
- **ASCII validation**: create-space transliterates smart punctuation, friendly 400 for emoji/non-Latin (was opaque Jobs API 500)
- **Recommended questions panel**: sidebar section (amber Lightbulb, default open) — sample questions, one click → auto-runs in workspace via `?ask=` param
- CSV export hidden in ephemeral Genie Chat threads (nothing persisted to export)

### Quick wins (small, high-visibility — found during P0 #2, 2026-06-11)
- [x] **Parallelize history load** — DONE 2026-06-11. `get_conversation_messages_endpoint` now rebuilds per-message data via ThreadPoolExecutor (≤6 workers, order-preserving `pool.map`, ownership check unchanged). Was 10-40s serial on long conversations.
- [x] **Feedback space_id bug** — DONE 2026-06-11 (P0 #4): server resolves body → conversation → state.json.

### P1 — Worth doing, small
- [ ] **Health probe → Slack** — user HAS a webhook ready (Slack app created; ask user for the URL, store in Databricks secret scope, never in git). Every 30 min: ephemeral chat flow against a shared space → post ✅ healthy / ⚠️ degraded / ❌ down with latency + error. Scheduled Databricks job (`resources/`), ~150-line script.
- [x] **ASCII input validation** — DONE 2026-06-11 (P0 #4): transliterate + friendly 400 in POST /api/spaces.

### P2 — Later (explicitly deprioritized by user)
- [ ] Better dashboard ("would be sick" — but after P0)
- [ ] Admin panel improvements (late phase)
- [ ] ~~Automate post-deploy GRANT~~ — **user decision: manual is fine.** Deploys are infrequent; do NOT add automation overhead. The psql command stays documented in OPERATIONS.md if ever wanted.
- [ ] ~~Space sharing~~ — not needed right now
- [ ] 2MB JS bundle code-splitting; remove dead code (`router.py`, Delta shadow tables in `ensure_tables`)

## Secondary known bugs (not user-priorities, keep on radar)

- Email columns in generated data sometimes get numeric values (spec issue)
- Formula-derived columns occasionally produce 0 on eval failure
- Pipeline notebooks duplicate logic from `backend/pipeline/` Python modules

## Working agreements (how the user likes to work)

- **Sandbox-first UI changes**: test in `test.html` component sandbox before touching real app code (see `UI_UPDATES.md` for the pattern)
- **Track changes** in `UI_UPDATES.md` with how each fix works
- **Verify everything against the live app** with curl before declaring success (see OPERATIONS.md for verification flows)
- **Report failures honestly and immediately** — the user wants running commentary on what's happening, especially during deploys
- **Plan before big changes** — user wants explicit plans with "why this won't destroy the app" risk assessments
- Concise communication, no fluff (see CLAUDE.md Communication Style)

## Branch/rollback strategy

- `main` — stable, protected by convention. Tag `v2-stable` = last known-good.
- `agent-overhaul` — experimental branch for the model overhaul. Go wild here.
- Rollback app code: `git checkout v2-stable && ./deploy.sh` (then GRANT — see OPERATIONS.md)
- DB is NOT branched — Lakebase data is shared between branches. Schema changes must be backward compatible or coordinated.
