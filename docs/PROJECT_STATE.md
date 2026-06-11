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

All endpoints healthy as of last verification (2026-06-11):
- Smoke: health/users/spaces/conversations all 200
- Burst: 20 sequential requests, flat ~0.35s
- Concurrent: 30/30 OK at 10-parallel
- Full chat flow: COMPLETED with data

## Production incident history (read this — patterns repeat)

| Incident | Root cause | Fix |
|---|---|---|
| "Data disappeared, only Acme shows" (x2) | Postgres pool captured OAuth token once at startup; token expires ~1h; pool reconnects fail silently → app falls back to state.json | `pg.py` rewritten: per-connection token mint, 30min token cache, 50min conn TTL, SELECT 1 validation only when idle >30s, 2-conn pre-warm. Tests: `scripts/test_pg_pool_logic.py` |
| "Chat stuck on Processing forever" | `/chat/result` used user OBO token for Genie API; platform began enforcing `genie` OAuth scope which OBO tokens lack → 403 → unhandled 500 | `chat.py`: dropped OBO, uses SP client (like `/status` always did), wrapped in try/except returning structured error |
| 10s+ tail latencies | v1 of pool fix ran SELECT 1 network roundtrip on EVERY checkout | Hot-path skip: validate only if idle >30s |

**The meta-pattern**: every incident was a long-lived credential trusted forever with no fallback. When touching auth/tokens/connections, always ask: what happens when this expires mid-flight?

## Known bugs (unfixed, prioritized)

1. **Non-ASCII input crashes space creation** — `spaces.py:459` `ws.jobs.run_now` rejects non-Latin1 chars (curly quotes, em-dashes, emojis) in notebook params with 500. Fix: validate in POST /api/spaces handler, return friendly 400, or transliterate. ~20 lines.
2. **`/conversations/{id}` (chat.py ~line 305) still prefers OBO** for Genie re-fetch. Degrades gracefully (metadata-only fallback) but history view loses data tables. Fix: same as `/chat/result` — drop `user_ws or ws`, use `ws`.
3. **Manual GRANT after every deploy** — see OPERATIONS.md. The single biggest operational hazard. Should be automated in deploy.sh.
4. **First user request after idle is slow** — SQL warehouse cold start (~1-3 min). Consider keep-alive ping or messaging in UI.
5. **2MB JS bundle** — no code splitting. Vite warns on every build.
6. **Dead code** — `backend/router.py` is an unused legacy monolith.

## Improvement roadmap (agreed with user 2026-06-11)

### Tier 1 — Reliability (do first)
- [x] Pool token refresh (deployed, verified)
- [ ] **Automate post-deploy GRANT** — psql command is documented in OPERATIONS.md but **NOT YET VERIFIED** (sandbox lacked psql). First: verify it works, then wire into deploy.sh as final step. Until then the user runs it manually.
- [ ] **Health probe job** — every 30 min, full chat flow against a shared space, post status to Slack (user is getting webhook approved; design exists in git history of plan files: ephemeral chat → status → result → Slack webhook with ✅/⚠️/❌)
- [ ] ASCII input validation (bug #1)
- [ ] Fix `/conversations/{id}` OBO (bug #2)

### Tier 2 — Result quality (user's main dissatisfaction)
- [ ] **Generated data realism** — current Faker data is too uniform; needs realistic distributions (seasonality, power-law sales, regional correlations), cross-table FK consistency, plausible time series
- [ ] **Genie space tuning** — add instructions, sample SQL, column descriptions during pipeline so Genie answers better
- [ ] **Chart selection** — heuristics in `chart_suggest.py` are basic

### Tier 3 — Features
- [ ] Space sharing between users
- [ ] Dashboard view improvements
- [ ] Conversation export polish
- [ ] Admin panel improvements

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
