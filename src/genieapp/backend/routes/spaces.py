"""Space management endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter

from ..app_config import get_state
from ..core import Dependencies, logger
from ..db import CATALOG, SCHEMA, WAREHOUSE_ID, _SESSIONS_TABLE, parse_sql_rows, run_sql
from ..models import (
    AppConfigOut,
    BrandingOut,
    CreateSpaceIn,
    CreateSpaceOut,
    JobStatusOut,
    SpaceOut,
    TableInfoBrief,
)

router = APIRouter()


def _fallback_spaces() -> list[SpaceOut]:
    """Fall back to state.json if sessions table is unavailable."""
    try:
        state = get_state()
        return [
            SpaceOut(
                space_id=state.space_id,
                company_name=state.branding.company_name,
                description=state.branding.description,
                logo_path=state.branding.logo_path,
                primary_color=state.branding.primary_color,
                secondary_color=state.branding.secondary_color,
                accent_color=state.branding.accent_color,
                chart_colors=state.branding.chart_colors,
            )
        ]
    except Exception:
        return []


@router.get("/spaces/debug", operation_id="debugSpaces")
def debug_spaces(ws: Dependencies.Client) -> dict:
    """Debug endpoint — shows raw SQL result for sessions query."""
    sql = f"SELECT * FROM {_SESSIONS_TABLE} ORDER BY created_at DESC"
    try:
        result = run_sql(ws, sql)
        rows = parse_sql_rows(result)
        return {
            "sql": sql,
            "raw_status": result.get("status"),
            "raw_keys": list(result.keys()),
            "parsed_row_count": len(rows),
            "rows": rows,
        }
    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__, "sql": sql}


@router.get("/spaces", response_model=list[SpaceOut], operation_id="listSpaces")
def list_spaces(ws: Dependencies.Client) -> list[SpaceOut]:
    """List all created Genie Spaces from the sessions table."""
    try:
        result = run_sql(
            ws,
            f"SELECT * FROM {_SESSIONS_TABLE} ORDER BY created_at DESC",
        )
        rows = parse_sql_rows(result)
        logger.info("list_spaces: SQL returned %d rows, keys=%s", len(rows), list(result.keys()))
        if not rows:
            logger.info("list_spaces: no rows, falling back. status=%s", result.get("status"))
            return _fallback_spaces()

        return [
            SpaceOut(
                space_id=r.get("space_id") or "",
                company_name=r.get("company_name") or "",
                description=r.get("description") or "",
                logo_path=r.get("logo_path") or "",
                primary_color=r.get("primary_color") or "#1a73e8",
                secondary_color=r.get("secondary_color") or "#ea4335",
                accent_color=r.get("accent_color") or "",
                chart_colors=json.loads(r["chart_colors_json"]) if r.get("chart_colors_json") else [],
                created_at=str(r.get("created_at") or ""),
            )
            for r in rows
        ]
    except Exception as e:
        logger.error("list_spaces exception: %s: %s", type(e).__name__, e)
        return _fallback_spaces()


@router.get(
    "/spaces/{space_id}/config",
    response_model=AppConfigOut,
    operation_id="getSpaceConfig",
)
def get_space_config(space_id: str, ws: Dependencies.Client) -> AppConfigOut:
    """Get config for a specific Genie Space from the sessions table."""
    from ..db import _escape

    safe_id = _escape(space_id)
    result = run_sql(
        ws,
        f"SELECT * FROM {_SESSIONS_TABLE} WHERE space_id = '{safe_id}' LIMIT 1",
    )
    rows = parse_sql_rows(result)

    if not rows:
        from .chat import _resolve_space_id

        state = get_state()
        return AppConfigOut(
            space_id=state.space_id,
            display_name=state.display_name,
            sample_questions=state.sample_questions,
            branding=BrandingOut(
                company_name=state.branding.company_name,
                description=state.branding.description,
                logo_path=state.branding.logo_path,
                primary_color=state.branding.primary_color,
                secondary_color=state.branding.secondary_color,
                accent_color=state.branding.accent_color,
                chart_colors=state.branding.chart_colors,
            ),
            tables=[
                TableInfoBrief(full_name=t.full_name, table_name=t.table_name, comment=t.comment)
                for t in state.tables
            ],
        )

    row = rows[0]
    tables_info = json.loads(row.get("tables_json", "[]"))
    sample_questions = json.loads(row.get("sample_questions_json", "[]"))

    chart_colors: list[str] = []
    if row.get("chart_colors_json"):
        try:
            chart_colors = json.loads(row["chart_colors_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    return AppConfigOut(
        space_id=space_id,
        display_name=f"{row.get('company_name', '')} Analytics",
        sample_questions=sample_questions,
        branding=BrandingOut(
            company_name=row.get("company_name") or "",
            description=row.get("description") or "",
            logo_path=row.get("logo_path") or "",
            primary_color=row.get("primary_color") or "#1a73e8",
            secondary_color=row.get("secondary_color") or "#ea4335",
            accent_color=row.get("accent_color") or "",
            chart_colors=chart_colors,
        ),
        tables=[
            TableInfoBrief(
                full_name=t.get("full_name", ""),
                table_name=t.get("table_name", ""),
                comment=t.get("comment", ""),
            )
            for t in tables_info
        ],
    )


@router.post("/spaces", response_model=CreateSpaceOut, operation_id="createSpace")
def create_space(
    req: CreateSpaceIn,
    ws: Dependencies.Client,
) -> CreateSpaceOut:
    """Trigger the DABs pipeline to create a new Genie Space."""
    job_id = 381399907081683
    try:
        run = ws.jobs.run_now(
            job_id=job_id,
            notebook_params={
                "catalog": CATALOG,
                "schema": SCHEMA,
                "company_name": req.company_name,
                "company_description": req.description,
                "logo_url": req.logo_url or "",
                "warehouse_id": WAREHOUSE_ID,
                "databricks_host_id": "7474655921234161",
                "llm_model": "opendoor-claude-opus-46",
            },
        )
        return CreateSpaceOut(run_id=str(run.run_id))
    except Exception as e:
        logger.error("create_space failed: %s: %s", type(e).__name__, e)
        raise


@router.get(
    "/jobs/{run_id}",
    response_model=JobStatusOut,
    operation_id="getJobStatus",
)
def get_job_status(run_id: str, ws: Dependencies.Client) -> JobStatusOut:
    """Poll the status of a pipeline job run."""
    run = ws.jobs.get_run(int(run_id))
    state = run.state

    life_cycle = state.life_cycle_state.value if state.life_cycle_state else "UNKNOWN"
    result_state = state.result_state.value if state.result_state else None

    if life_cycle in ("TERMINATED",):
        if result_state == "SUCCESS":
            status = "COMPLETED"
        else:
            status = "FAILED"
    elif life_cycle in ("INTERNAL_ERROR", "SKIPPED"):
        status = "FAILED"
    else:
        status = "RUNNING"

    space_id = None
    error = None
    if status == "COMPLETED":
        try:
            company_name = ""
            if run.overriding_parameters and run.overriding_parameters.notebook_params:
                company_name = run.overriding_parameters.notebook_params.get("company_name", "")

            from ..db import _escape

            if company_name:
                safe_name = _escape(company_name)
                result = run_sql(
                    ws,
                    f"SELECT space_id FROM {_SESSIONS_TABLE} "
                    f"WHERE company_name = '{safe_name}' ORDER BY created_at DESC LIMIT 1",
                )
            else:
                result = run_sql(
                    ws,
                    f"SELECT space_id FROM {_SESSIONS_TABLE} ORDER BY created_at DESC LIMIT 1",
                )
            rows = parse_sql_rows(result)
            if rows:
                space_id = rows[0].get("space_id")
        except Exception as e:
            logger.warning("Could not fetch space_id after job completion: %s", e)

    if status == "FAILED":
        error = state.state_message or "Pipeline failed"

    return JobStatusOut(
        run_id=run_id,
        status=status,
        space_id=space_id,
        error=error,
    )
