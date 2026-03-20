"""Space management endpoints — user-scoped CRUD, BYOG, template selection."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request

from ..app_config import get_state
from ..core import Dependencies, logger
from ..db import (
    CATALOG,
    SCHEMA,
    WAREHOUSE_ID,
    _SESSIONS_TABLE,
    _escape,
    create_space as db_create_space,
    get_dashboard_data,
    get_space,
    list_user_spaces,
    parse_sql_rows,
    run_sql,
    soft_delete_space,
    update_space_template,
)
from ..models import (
    AppConfigOut,
    BrandingOut,
    CreateByogSpaceIn,
    CreateSpaceIn,
    CreateSpaceOut,
    DashboardOut,
    DashboardPanel,
    JobStatusOut,
    RegisterSpaceIn,
    SpaceOut,
    TableInfoBrief,
    UpdateTemplateIn,
)

router = APIRouter()


def _get_user_id(request: Request) -> str:
    """Extract user_id from Databricks headers, fallback to 'anonymous'."""
    return request.headers.get("X-Forwarded-User", "anonymous")


def _row_to_space_out(r: dict) -> SpaceOut:
    """Convert a DB row dict to SpaceOut model."""
    chart_colors: list[str] = []
    if r.get("chart_colors_json"):
        try:
            chart_colors = json.loads(r["chart_colors_json"])
        except (json.JSONDecodeError, TypeError):
            pass
    return SpaceOut(
        space_id=r.get("space_id") or "",
        company_name=r.get("company_name") or "",
        description=r.get("description") or "",
        logo_path=r.get("logo_volume_path") or r.get("logo_path") or "",
        primary_color=r.get("primary_color") or "#1a73e8",
        secondary_color=r.get("secondary_color") or "#ea4335",
        accent_color=r.get("accent_color") or "",
        chart_colors=chart_colors,
        template_id=r.get("template_id") or "simple",
        space_type=r.get("space_type") or "generated",
        created_at=str(r.get("created_at") or ""),
    )


def _fallback_spaces() -> list[SpaceOut]:
    """Fall back to state.json if no spaces found."""
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


# --- User-scoped space listing ---

@router.get("/spaces", response_model=list[SpaceOut], operation_id="listSpaces")
def list_spaces(ws: Dependencies.Client, request: Request) -> list[SpaceOut]:
    """List spaces: user-owned from spaces table + legacy sessions table, deduped by space_id."""
    user_id = _get_user_id(request)
    seen_ids: set[str] = set()
    spaces: list[SpaceOut] = []

    # User-owned spaces from the spaces table
    try:
        rows = list_user_spaces(ws, user_id)
        for r in rows:
            out = _row_to_space_out(r)
            if out.space_id and out.space_id not in seen_ids:
                seen_ids.add(out.space_id)
                spaces.append(out)
    except Exception as e:
        logger.warning("list_user_spaces failed: %s", e)

    # Legacy sessions table (pipeline-created spaces before multi-user)
    try:
        result = run_sql(
            ws,
            f"SELECT * FROM {_SESSIONS_TABLE} ORDER BY created_at DESC",
        )
        for r in parse_sql_rows(result):
            sid = r.get("space_id") or ""
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                spaces.append(SpaceOut(
                    space_id=sid,
                    company_name=r.get("company_name") or "",
                    description=r.get("description") or "",
                    logo_path=r.get("logo_path") or "",
                    primary_color=r.get("primary_color") or "#1a73e8",
                    secondary_color=r.get("secondary_color") or "#ea4335",
                    accent_color=r.get("accent_color") or "",
                    chart_colors=json.loads(r["chart_colors_json"]) if r.get("chart_colors_json") else [],
                    created_at=str(r.get("created_at") or ""),
                ))
    except Exception as e:
        logger.warning("sessions table fallback failed: %s", e)

    if not spaces:
        return _fallback_spaces()
    return spaces


# --- BYOG (Bring Your Own Genie Space) ---

@router.post("/spaces/byog", response_model=SpaceOut, operation_id="createByogSpace")
def create_byog_space(
    req: CreateByogSpaceIn,
    ws: Dependencies.Client,
    headers: Dependencies.Headers,
    request: Request,
) -> SpaceOut:
    """Connect an existing Genie Space (BYOG). Validates access using user's OBO token."""
    user_id = _get_user_id(request)
    if user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate the user has access to this Genie Space using their OBO token
    if headers.token:
        try:
            from databricks.sdk import WorkspaceClient as WC
            user_ws = WC(token=headers.token.get_secret_value(), auth_type="pat")
            user_ws.genie.get_space(req.space_id)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot access Genie Space '{req.space_id}': {e}",
            )

    # Extract table metadata from the Genie Space
    tables_json = "[]"
    try:
        space_info = ws.genie.get_space(req.space_id)
        if space_info.table_identifiers:
            tables = [
                {"full_name": t.table_identifier or "", "table_name": (t.table_identifier or "").split(".")[-1], "comment": ""}
                for t in space_info.table_identifiers
                if t.table_identifier
            ]
            tables_json = json.dumps(tables)
    except Exception as e:
        logger.warning("Could not extract tables from Genie Space: %s", e)

    row = db_create_space(
        ws=ws,
        space_id=req.space_id,
        owner_user_id=user_id,
        company_name=req.company_name,
        space_type="byog",
        template_id=req.template_id,
        primary_color=req.primary_color,
        secondary_color=req.secondary_color,
        accent_color=req.accent_color,
        tables_json=tables_json,
    )
    return _row_to_space_out(row)


# --- Register pipeline space ---

@router.post("/spaces/register", response_model=SpaceOut, operation_id="registerPipelineSpace")
def register_pipeline_space(
    req: RegisterSpaceIn,
    ws: Dependencies.Client,
    request: Request,
) -> SpaceOut:
    """Register a pipeline-created space (from sessions table) into the spaces table."""
    user_id = _get_user_id(request)

    # Already in spaces table? Just update template if needed.
    existing = get_space(ws, req.space_id)
    if existing:
        if req.template_id != (existing.get("template_id") or "simple"):
            update_space_template(ws, req.space_id, req.template_id)
            existing["template_id"] = req.template_id
        return _row_to_space_out(existing)

    # Read from sessions table
    safe_id = _escape(req.space_id)
    result = run_sql(ws, f"SELECT * FROM {_SESSIONS_TABLE} WHERE space_id = '{safe_id}' LIMIT 1")
    sess_rows = parse_sql_rows(result)
    if not sess_rows:
        raise HTTPException(status_code=404, detail=f"Space '{req.space_id}' not found in sessions table")

    row = sess_rows[0]
    chart_colors: list[str] = []
    if row.get("chart_colors_json"):
        try:
            chart_colors = json.loads(row["chart_colors_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    new_row = db_create_space(
        ws=ws,
        space_id=req.space_id,
        owner_user_id=user_id,
        company_name=row.get("company_name", ""),
        description=row.get("description", ""),
        space_type="generated",
        template_id=req.template_id,
        logo_volume_path=row.get("logo_path", ""),
        primary_color=row.get("primary_color", "#1a73e8"),
        secondary_color=row.get("secondary_color", "#ea4335"),
        accent_color=row.get("accent_color", ""),
        chart_colors=chart_colors,
        tables_json=row.get("tables_json", "[]"),
        sample_questions_json=row.get("sample_questions_json", "[]"),
    )
    return _row_to_space_out(new_row)


# --- Template selection ---

@router.patch(
    "/spaces/{space_id}/template",
    response_model=dict[str, bool],
    operation_id="updateSpaceTemplate",
)
def update_template(
    space_id: str,
    req: UpdateTemplateIn,
    ws: Dependencies.Client,
) -> dict[str, bool]:
    """Update the UI template for a space."""
    valid_templates = {"simple", "widget", "dashboard", "command", "workspace"}
    if req.template_id not in valid_templates:
        raise HTTPException(status_code=400, detail=f"Invalid template_id. Must be one of: {valid_templates}")
    update_space_template(ws, space_id, req.template_id)
    return {"success": True}


# --- Soft delete ---

@router.delete("/spaces/{space_id}", operation_id="deleteSpace")
def delete_space(
    space_id: str,
    ws: Dependencies.Client,
) -> dict[str, bool]:
    """Soft-delete a space (set is_active=false)."""
    soft_delete_space(ws, space_id)
    return {"success": True}


# --- Space config ---

@router.get(
    "/spaces/{space_id}/config",
    response_model=AppConfigOut,
    operation_id="getSpaceConfig",
)
def get_space_config(space_id: str, ws: Dependencies.Client) -> AppConfigOut:
    """Get config for a specific Genie Space. Checks spaces table first, then sessions, then state.json."""
    # Try new spaces table first
    space = get_space(ws, space_id)
    if space:
        tables_info = json.loads(space.get("tables_json", "[]")) if space.get("tables_json") else []
        sample_questions = json.loads(space.get("sample_questions_json", "[]")) if space.get("sample_questions_json") else []
        chart_colors: list[str] = []
        if space.get("chart_colors_json"):
            try:
                chart_colors = json.loads(space["chart_colors_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        return AppConfigOut(
            space_id=space_id,
            display_name=f"{space.get('company_name', '')} Analytics",
            sample_questions=sample_questions,
            branding=BrandingOut(
                company_name=space.get("company_name") or "",
                description=space.get("description") or "",
                logo_path=space.get("logo_volume_path") or "",
                primary_color=space.get("primary_color") or "#1a73e8",
                secondary_color=space.get("secondary_color") or "#ea4335",
                accent_color=space.get("accent_color") or "",
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
            template_id=space.get("template_id") or "simple",
        )

    # Fall back to legacy sessions table
    safe_id = _escape(space_id)
    result = run_sql(
        ws,
        f"SELECT * FROM {_SESSIONS_TABLE} WHERE space_id = '{safe_id}' LIMIT 1",
    )
    rows = parse_sql_rows(result)

    if rows:
        row = rows[0]
        tables_info = json.loads(row.get("tables_json", "[]"))
        sample_questions = json.loads(row.get("sample_questions_json", "[]"))
        chart_colors = []
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
            template_id=row.get("template_id") or "simple",
        )

    # Final fallback: state.json
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
        template_id="simple",
    )


# --- Dashboard ---

@router.get(
    "/spaces/{space_id}/dashboard",
    response_model=DashboardOut,
    operation_id="getSpaceDashboard",
)
def get_space_dashboard(space_id: str, ws: Dependencies.Client) -> DashboardOut:
    """Get pre-computed dashboard data for a space."""
    data = get_dashboard_data(ws, space_id)
    if not data:
        return DashboardOut(panels=[], available=False)

    panels = []
    for p in data.get("panels", []):
        panels.append(DashboardPanel(
            id=p.get("id", ""),
            title=p.get("title", ""),
            chart_type=p.get("chart_type", "bar"),
            sql=p.get("sql", ""),
            columns=p.get("columns", []),
            data=p.get("data", []),
            position=p.get("position", 0),
        ))

    return DashboardOut(
        panels=sorted(panels, key=lambda p: p.position),
        available=True,
        generated_at=data.get("generated_at", ""),
    )


# --- Debug ---

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


# --- Space creation (pipeline trigger) ---

@router.post("/spaces", response_model=CreateSpaceOut, operation_id="createSpace")
def create_space_pipeline(
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


# --- Job status ---

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
