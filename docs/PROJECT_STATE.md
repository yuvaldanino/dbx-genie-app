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

All endpoints healthy as of last verification (2026-06-11, post P0 #2 deploy, commit `d1f0192`):
- Smoke: health/users/spaces/conversations all 200, 16 spaces
- Full ephemeral chat flow: COMPLETED, rows>0, chart suggestion
- Old-conversation history: 14/15 completed messages return full data (was 3/15 before the fix); the 1 is a legit 0-row query
- App SP now has real UC grants (catalog-level USE CATALOG/USE SCHEMA/SELECT + genie_app MODIFY + volume RW) — it had NONE before 2026-06-11
- Known UX cost: history load rebuilds message data serially → 10-40s for long conversations (fix = parallelize, see Quick wins)

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

#### 1. Result-quality parity with native Genie
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

#### 3. Embedded "Genie Chat" mode (new nav item)
A continuous, ChatGPT-style conversation with the space — like native Genie — alongside the existing save-each-query workspace.
- New sidebar nav button "Genie Chat" → new route `ui/routes/_sidebar/genie-chat.tsx`
- Implementation: reuse the existing backend entirely — `chat/start` already accepts `conversation_id` for continuation and `ephemeral: true` to skip persistence. The new UI keeps one conversation_id for the session and renders a scrolling thread (MessageBubble components exist).
- Not persisted: each app visit starts a fresh thread (per user decision). No DB changes needed.
- Do NOT iframe the actual Databricks Genie page — app auth headers/X-Frame-Options will fight you; the API path above gives the same experience in-brand.
- Result: three modes per space — Genie Chat (free conversation), Chat workspace (saved/starred queries, recents), Dashboard (precomputed + drawer).

#### 4. Smoothness / Databricks-ecosystem polish pass
The "janky" feeling. Sweep for:
- Loading states everywhere (skeletons not spinners where possible), optimistic UI, transitions
- Error handling: friendly toasts instead of blank screens or stuck spinners (some errors still swallow silently)
- Warehouse cold-start: first query after idle takes 1-3 min — show "warehouse warming up" messaging instead of an opaque wait, or fire a warehouse keep-alive/wake ping on app load
- Visual alignment with Databricks design language (spacing, typography, nav patterns)
- **Recommended questions always visible**: persistent left-panel list (sidebar section under Tables/History) showing the space's must-answer/sample questions (`sample_questions_json` on the space row) + Genie's suggested follow-ups; click → runs it. Demo presenters lean on this.

### Quick wins (small, high-visibility — found during P0 #2, 2026-06-11)
- [ ] **Parallelize history load** — `get_conversation_messages_endpoint` rebuilds message data serially → 10-40s opens on long conversations (worst visible jank right now). ThreadPoolExecutor over per-message fetches → ~max(single fetch). ~20 lines, contained.
- [ ] **Feedback space_id bug** — `/chat/feedback` (chat.py) resolves space_id from legacy `state.json`; `FeedbackIn` has no space_id field → thumbs up/down silently fails (or hits wrong space) for every space except the legacy default. Add `space_id` to FeedbackIn + frontend pass-through. ~15 lines.

### P1 — Worth doing, small
- [ ] **Health probe → Slack** — user HAS a webhook ready (Slack app created; ask user for the URL, store in Databricks secret scope, never in git). Every 30 min: ephemeral chat flow against a shared space → post ✅ healthy / ⚠️ degraded / ❌ down with latency + error. Scheduled Databricks job (`resources/`), ~150-line script.
- [ ] **ASCII input validation** — `spaces.py:459` Jobs API rejects non-Latin1 (curly quotes, emojis) → 500. Validate/transliterate in POST /api/spaces, friendly 400. ~20 lines.

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
