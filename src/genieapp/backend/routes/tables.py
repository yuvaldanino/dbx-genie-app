"""Table browsing endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from ..app_config import get_state
from ..core import Dependencies
from ..genie_client import get_table_detail
from ..models import (
    AppConfigOut,
    BrandingOut,
    ColumnInfo,
    TableDetailOut,
    TableInfoBrief,
    TableInfoOut,
)

router = APIRouter()


@router.get("/config", response_model=AppConfigOut, operation_id="getAppConfig")
async def get_app_config() -> AppConfigOut:
    """Get app configuration and branding for frontend."""
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


@router.get("/tables", response_model=list[TableInfoOut], operation_id="listTables")
async def list_tables() -> list[TableInfoOut]:
    """List all tables in the Genie Space."""
    state = get_state()
    return [
        TableInfoOut(
            full_name=t.full_name,
            table_name=t.table_name,
            comment=t.comment,
        )
        for t in state.tables
    ]


@router.get("/tables/{name}", response_model=TableDetailOut, operation_id="getTableDetail")
def get_table(name: str, ws: Dependencies.Client) -> TableDetailOut:
    """Get detailed table schema information."""
    state = get_state()

    full_name = None
    for t in state.tables:
        if t.table_name == name or t.full_name == name:
            full_name = t.full_name
            break

    if not full_name:
        full_name = f"{state.catalog}.{state.schema_name}.{name}"

    detail = get_table_detail(ws, full_name)
    return TableDetailOut(
        full_name=detail["full_name"],
        table_name=detail["table_name"],
        comment=detail.get("comment", ""),
        columns=[ColumnInfo(**c) for c in detail.get("columns", [])],
        row_count=detail.get("row_count", 0),
    )
