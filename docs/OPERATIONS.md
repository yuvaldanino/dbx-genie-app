# OPERATIONS.md — Deploy, Test, and Recovery Procedures

> Everything an agent needs to operate this app autonomously.
>
> **Doc map**: this file = deploy/test/recovery · [`PROJECT_STATE.md`](PROJECT_STATE.md) = state/bugs/roadmap · [`ARCHITECTURE.md`](ARCHITECTURE.md) = system design + data-store/services map · [`../CLAUDE.md`](../CLAUDE.md) = hard rules + dev commands

## Deploy

```bash
PATH="/opt/homebrew/bin:$PATH" DATABRICKS_CLI_PATH=/opt/homebrew/bin/databricks ./deploy.sh
```

- The `PATH` prefix is REQUIRED: two `databricks` CLIs are installed; the legacy v0.18 at `~/Library/Python/3.9/bin` breaks bundle Terraform auth ("legacy databricks CLI detected").
- deploy.sh does: vite build → bundle deploy → restore Lakebase postgres resource (bundle strips it every time) → UC grants → app deploy.
- UC GRANT lines must say `OK`. (Historical note: until 2026-06-11 the script's hand-rolled JSON escaped backticks as `\``, so every grant silently failed — the old "WARN (ERROR) is expected noise" advice was wrong. The app SP had NO catalog grants until then; fixed by granting catalog-level USE CATALOG/USE SCHEMA/SELECT + genie_app MODIFY + raw_data volume RW.)
- Transient `cannot read job ... timed out` errors from the Jobs API happen; retry after 60s. If bundle keeps failing but only app code changed, you can deploy the app artifact directly (files must already be uploaded by a previous successful bundle deploy — this does NOT pick up local changes by itself):
  `databricks apps deploy genieapp-dev --profile vm --source-code-path /Workspace/Users/yuval.danino@databricks.com/.bundle/genieapp/dev/files`

## ⚠️ CRITICAL: Post-deploy GRANT (every deploy, no exceptions)

Every deploy resets the app SP's Lakebase role membership. Until the GRANT runs, the app returns 500 on `/api/users/me` and falls back to showing only "Acme Corporation". **This has caused 2 production incidents.**

```sql
GRANT app_rw TO "677d1641-521c-4df6-91f4-dacea8be74e7";
```

### Programmatic path (preferred — agent can self-serve)

Connection details (from `/api/admin/lakebase-test`, admin-only endpoint):
- Host: `ep-flat-haze-d2mzy9ui.database.us-east-1.cloud.databricks.com`
- Port: 5432, DB: `databricks_postgres`, SSL: require
- Auth: your Databricks OAuth token as password, your email as user

```bash
TOKEN=$(databricks auth token --profile vm | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
PGPASSWORD="$TOKEN" /opt/homebrew/opt/libpq/bin/psql \
  "host=ep-flat-haze-d2mzy9ui.database.us-east-1.cloud.databricks.com port=5432 dbname=databricks_postgres user=yuval.danino@databricks.com sslmode=require" \
  -c 'GRANT app_rw TO "677d1641-521c-4df6-91f4-dacea8be74e7";' \
  -c "SELECT pg_has_role('677d1641-521c-4df6-91f4-dacea8be74e7', 'app_rw', 'member');"
```

**Status: VERIFIED 2026-06-11** (returns `GRANT ROLE` + `t`). psql lives at `/opt/homebrew/opt/libpq/bin/psql` (keg-only, installed via `brew install libpq`). The GRANT is idempotent — safe to run any time. Per user decision this stays a manual agent-run step, NOT wired into deploy.sh.

> **Why this machine can't use pip/uv/bun for new packages**: `/etc/hosts` deliberately pins `pypi.org` (+ ~12 mirrors) and the npm registry to `127.0.0.1` (supply-chain protection). `uv sync` / `bun install` fail with "Connection refused" for anything not already cached. Homebrew (ghcr.io) and github.com are NOT blocked. Do not edit /etc/hosts — work around via brew or vendored deps.

### Fallback (manual)
Ask the user: "Run `GRANT app_rw TO "677d1641-521c-4df6-91f4-dacea8be74e7";` in the **Lakebase SQL editor** (the Postgres one, NOT the regular Databricks SQL editor)."

## Verification suite (run after EVERY deploy)

```bash
TOKEN=$(databricks auth token --profile vm | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
APP=https://genieapp-dev-7474655921234161.aws.databricksapps.com

# 1. Smoke — all must be 200; spaces must be >1 (n=1 means Acme fallback = GRANT missing)
curl -sL -w 'HTTP:%{http_code}\n' -o /dev/null -H "Authorization: Bearer $TOKEN" "$APP/api/health"
curl -sL -w 'HTTP:%{http_code}\n' -o /dev/null -H "Authorization: Bearer $TOKEN" "$APP/api/users/me"
curl -sL -H "Authorization: Bearer $TOKEN" "$APP/api/spaces" | python3 -c "import sys,json; print('spaces:', len(json.load(sys.stdin)))"

# 2. Burst — 20 sequential /api/users/me; healthy = flat ~0.35s, max <1s
# 3. Full chat flow (use ephemeral:true to avoid polluting history):
#    POST /api/chat/start {"question":"...","space_id":"01f144169528170cab22ee3e2a5803e4","ephemeral":true}
#    poll GET /api/chat/{conv}/{msg}/status?space_id=...   until is_complete
#    GET /api/chat/{conv}/{msg}/result?space_id=...&ephemeral=true   → expect 200, row_count>0
```

Stable space IDs for testing: Coca-Cola `01f144169528170cab22ee3e2a5803e4` (shared), Starbucks `01f1279e5f7117e99e11462df7077b2b` (shared).

## Local tests

```bash
# Pool logic (mocked, no DB needed): 9 tests
.venv/bin/python scripts/test_pg_pool_logic.py

# Frontend types
bun run --bun node_modules/.bin/tsc --noEmit   # pre-existing errors in admin.tsx are known

# Backend syntax (venv may lack psycopg2 locally; use ast)
python3 -c "import ast; ast.parse(open('src/genieapp/backend/pg.py').read())"

# 75-min soak (background): scripts/lakebase_soak.sh — logs to /tmp/genieapp-soak.log
# NOTE: soak generates ~4 req/min; fine on current pool, was what exposed the v1 latency bug
```

## Reading production logs

No REST API for app logs. Options:
- `https://genieapp-dev-7474655921234161.aws.databricksapps.com/logz` — HTML/websocket viewer (browser only; curl gets the HTML shell, not logs)
- Ask the user to paste logs from the Databricks Apps UI (Logs tab)
- Infer from API responses (status codes + latency tell you most of it)

## Common failure signatures

| Symptom | Cause | Fix |
|---|---|---|
| `/api/users/me` 500 + only Acme space visible | GRANT missing after deploy | Run the GRANT |
| Chat stuck on "Processing", `/result` 500 | Genie API auth (check for `Invalid scope, required scopes: genie`) | Must use SP client (`ws`), never OBO, for genie.* calls |
| All endpoints slow/timeout | Pool validation overhead or app overload | Check pool settings (PG_* env vars), restart app |
| First request after idle ~1-3min slow | SQL warehouse cold start | Expected; retry |
| `create_space` 500 `Only Latin1 (ASCII)` | Non-ASCII chars in user input (curly quotes!) | Known bug #1 in PROJECT_STATE.md |
| Deploy fails `legacy databricks CLI detected` | Wrong CLI in PATH | Use the PATH prefix shown above |
| `databricks auth token` fails refresh | Expired profile | Ask user: `! databricks auth login --profile vm` |

## App restart (without deploy)

```bash
databricks apps stop genieapp-dev --profile vm
databricks apps start genieapp-dev --profile vm   # takes ~60-90s
```
Restart does NOT reset the Lakebase grant (only deploys do).

## Key identifiers

| Thing | Value |
|---|---|
| App name / target | `genieapp-dev` (bundle target `dev`) |
| App URL | https://genieapp-dev-7474655921234161.aws.databricksapps.com |
| Workspace profile | `vm` |
| App service principal | `677d1641-521c-4df6-91f4-dacea8be74e7` |
| Lakebase host | `ep-flat-haze-d2mzy9ui.database.us-east-1.cloud.databricks.com` |
| Lakebase db / role | `databricks_postgres` / `app_rw` |
| UC catalog.schema | `yd_launchpad_final_classic_catalog.genie_app` |
| Warehouse (app SQL) | `fc62b388f737b2d3` (hardcoded in db.py) |
