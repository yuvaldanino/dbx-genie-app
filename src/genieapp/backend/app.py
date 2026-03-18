"""FastAPI application entry point."""

from .core import create_app, create_router, logger
from .routes import sub_routers

router = create_router()
for sub in sub_routers:
    router.include_router(sub)

app = create_app(routers=[router])


@app.on_event("startup")
async def _ensure_db_tables() -> None:
    """Create application tables on first startup (best-effort)."""
    try:
        ws = app.state.workspace_client
        from .db import ensure_tables
        ensure_tables(ws)
        logger.info("ensure_tables completed successfully")
    except Exception as e:
        logger.warning("ensure_tables skipped (expected in local dev): %s", e)
