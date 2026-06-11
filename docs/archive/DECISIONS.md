# GenieApp — Architecture Decision Log

## ADR-001: UC Delta Tables over Lakebase Postgres
- **Date**: 2026-03-18
- **Decision**: Use UC Delta Tables accessed via SQL Statements API
- **Rationale**: No new infrastructure to provision, existing `_run_sql` pattern works, read latency (1-3s) acceptable with frontend React Query caching and server-side TTL cache
- **Alternatives considered**: Lakebase Postgres (faster reads, proper FK, but new dependency to provision and manage)

## ADR-002: Router Split into Route Modules
- **Date**: 2026-03-18
- **Decision**: Split monolithic `router.py` (628 lines) into `routes/` package with per-domain modules
- **Rationale**: Enables independent development per phase, clearer ownership, easier code review
- **Modules**: chat, spaces, tables, users, export
