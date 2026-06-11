# Genie-rator

Multi-user Databricks App for Field Engineers: enter a company name + description → pipeline generates realistic fake data, UC tables, a Genie Space, and a branded chat UI with charts.

Built with APX (FastAPI + React). Live at: https://genieapp-dev-7474655921234161.aws.databricksapps.com

## Documentation

| Doc | Purpose |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Agent guidance: hard rules, architecture summary, dev commands |
| [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) | **Start here** — current state, incident history, known bugs, roadmap |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Deploy, post-deploy GRANT (critical!), verification, failure signatures |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design and data flow |
| [`docs/UI_UPDATES.md`](docs/UI_UPDATES.md) | UI change log + sandbox-first testing pattern |
| `docs/archive/` | Historical: migration notes, old ADRs, past code reviews |

## Repo layout

```
src/genieapp/backend/    FastAPI app (routes/, pipeline/, pg.py, db.py, genie_client.py)
src/genieapp/ui/         React frontend (routes/, components/apx/, lib/)
scripts/pipeline/        Pipeline notebooks (referenced by resources/*.yml jobs)
scripts/                 Tests + soak harness (legacy experiments in scripts/legacy/)
resources/               Databricks Asset Bundle job/app definitions
examples/                Sample pipeline outputs
deploy.sh                Deploy script (see docs/OPERATIONS.md for required env)
```

## Quick start

```bash
uv sync && bun install                 # deps
uv run uvicorn genieapp.backend.app:app --reload --port 8000   # backend
bun run --bun node_modules/.bin/vite dev                        # frontend (proxies /api)
```

Deploy: see [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — **do not skip the post-deploy GRANT step.**

## Branches

- `main` — stable. Last known-good tag: `v2-stable`
- `agent-overhaul` — active development branch
