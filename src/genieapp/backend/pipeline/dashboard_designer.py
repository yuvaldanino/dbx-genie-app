"""LLM-powered dashboard creation — designs panels, executes SQL, stores results."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from databricks.sdk import WorkspaceClient
from openai import OpenAI

from ..chart_suggest import suggest_chart
from ..db import _SESSIONS_TABLE, _SPACES_TABLE, _escape, parse_sql_rows, run_sql
from .data_generator import get_sql_type

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a data dashboard designer. Given table schemas for a company's analytics database, generate 4-6 dashboard panel definitions.

RULES:
1. Start with 1-2 KPI panels (single aggregate number), then categorical charts, then time series.
2. Each panel's SQL must use fully-qualified 3-part table names (catalog.schema.table).
3. Keep SQL simple — single table queries, basic aggregates, GROUP BY. MAX 20 rows per query.
4. chart_type must be one of: kpi, bar, line, pie, area
5. For KPI: SQL should return exactly 1 row with 1 numeric column. Use a descriptive alias like `total_revenue`, NOT `sum_1`.
6. For bar/pie: SQL should return a categorical column + a numeric column. The categorical column must be a name/category/type column, NOT an ID column.
7. For line/area: SQL should return a date/time column + a numeric column, ORDER BY the date column.
8. Position panels logically: KPIs first (position 0,1), then charts (position 2,3,4,5).
9. NEVER use ID columns (ending in _id, _key, _pk) as the aggregated metric. Use COUNT(*), SUM, AVG on meaningful business columns.
10. All SQL column aliases must be human-readable (e.g., `SUM(amount) as total_revenue`, `COUNT(*) as order_count`).
11. For bar charts, LIMIT to 10 rows and ORDER BY the metric DESC to show top values.

OUTPUT FORMAT (strict JSON array, no markdown fences):
[
  {
    "title": "Total Revenue",
    "sql": "SELECT SUM(revenue) as total_revenue FROM catalog.schema.table",
    "chart_type": "kpi",
    "position": 0
  },
  {
    "title": "Revenue by Category",
    "sql": "SELECT category, SUM(revenue) as revenue FROM catalog.schema.table GROUP BY category ORDER BY revenue DESC LIMIT 10",
    "chart_type": "bar",
    "position": 2
  }
]
"""


def _build_tables_prompt(
    schema_def: dict[str, Any],
    tables_info: list[dict],
    catalog: str,
    schema_name: str,
) -> str:
    """Build a rich table description for the LLM using schema_def columns."""
    tables_desc = []

    # Build a lookup from schema name → full_name
    # tables_info uses prefixed names (e.g., "gap_regions") while schema_def uses
    # unprefixed names (e.g., "regions"), so match by suffix
    full_name_map: dict[str, str] = {}
    for t in tables_info:
        full_name_map[t.get("table_name", "")] = t.get("full_name", "")
        # Also map the unprefixed name (strip company slug prefix)
        tname = t.get("table_name", "")
        for sep_idx in range(len(tname)):
            if tname[sep_idx] == "_":
                suffix = tname[sep_idx + 1:]
                full_name_map[suffix] = t.get("full_name", "")

    for tbl in schema_def.get("tables", []):
        t_name = tbl["name"]
        full_name = full_name_map.get(t_name, f"{catalog}.{schema_name}.{t_name}")
        t_comment = tbl.get("comment", "")

        lines = [f"Table: {full_name}"]
        if t_comment:
            lines[0] += f" — {t_comment}"
        lines.append("Columns:")

        for col in tbl.get("columns", []):
            c_name = col["name"]
            faker = col.get("faker", "")
            sql_type = get_sql_type(faker) if faker else "STRING"
            c_comment = col.get("comment", "")
            args = col.get("args", {})

            desc = f"  - {c_name}: {sql_type}"
            if c_comment:
                desc += f" ({c_comment})"
            if faker == "random_element":
                elems = args.get("elements", [])
                if elems:
                    desc += f" [values: {', '.join(str(e) for e in elems[:6])}]"
            if faker == "fk":
                ref = args.get("references", "")
                if ref:
                    desc += f" [FK → {ref}]"
            lines.append(desc)

        tables_desc.append("\n".join(lines))

    return "\n---\n".join(tables_desc)


def design_dashboard(
    company_name: str,
    company_description: str,
    tables_info: list[dict],
    catalog: str,
    schema_name: str,
    *,
    databricks_host: str,
    databricks_token: str,
    schema_def: dict[str, Any] | None = None,
    model: str = "opendoor-claude-opus-46",
) -> list[dict[str, Any]]:
    """Call the LLM to generate dashboard panel definitions.

    Args:
        company_name: Company name.
        company_description: Free-text description.
        tables_info: List of table metadata dicts (full_name, table_name, comment).
        catalog: UC catalog name.
        schema_name: UC schema name.
        databricks_host: Databricks workspace ID for AI Gateway.
        databricks_token: Databricks PAT token.
        schema_def: Full schema with column details (preferred over tables_info).
        model: Model name on the AI Gateway.

    Returns:
        List of panel definition dicts.
    """
    client = OpenAI(
        api_key=databricks_token,
        base_url=f"https://{databricks_host}.ai-gateway.cloud.databricks.com/mlflow/v1",
    )

    # Build table description — use schema_def if available for rich column info
    if schema_def and schema_def.get("tables"):
        tables_prompt = _build_tables_prompt(schema_def, tables_info, catalog, schema_name)
    else:
        # Fallback to basic table info
        parts = []
        for t in tables_info:
            full_name = t.get("full_name", f"{catalog}.{schema_name}.{t.get('table_name', '')}")
            cols = t.get("columns", [])
            if cols:
                col_lines = [f"  - {c.get('name', '')}: {c.get('type', '')} ({c.get('comment', '')})" for c in cols]
                parts.append(f"Table: {full_name}\nColumns:\n" + "\n".join(col_lines))
            else:
                parts.append(f"Table: {full_name}")
        tables_prompt = "\n---\n".join(parts)

    prompt = (
        f"Company: {company_name}\n"
        f"Description: {company_description}\n"
        f"Catalog: {catalog}, Schema: {schema_name}\n\n"
        f"Tables:\n{tables_prompt}"
    )

    logger.info("Calling LLM to design dashboard for %s...", company_name)
    resp = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start >= 0 and end > start:
        raw = raw[start:end]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    panels = json.loads(raw)
    if not isinstance(panels, list):
        raise ValueError(f"Expected JSON array, got {type(panels).__name__}")

    logger.info("Dashboard designed: %d panels", len(panels))
    return panels


def _execute_panel_sql(
    ws: WorkspaceClient,
    warehouse_id: str,
    sql: str,
) -> tuple[list[str], list[dict]]:
    """Execute a panel's SQL and return (columns, data)."""
    result = run_sql(ws, sql, raise_on_error=True)
    rows = parse_sql_rows(result)
    if not rows:
        return [], []

    columns = list(rows[0].keys()) if rows else []

    # Convert all values to JSON-safe types
    def _to_json_safe(v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, (int, float, str, bool)):
            return v
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        if hasattr(v, "item"):  # numpy scalar
            return v.item()
        if hasattr(v, "__class__") and "nat" in type(v).__name__.lower():
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return str(v)

    clean_rows = []
    for row in rows:
        clean_rows.append({k: _to_json_safe(v) for k, v in row.items()})

    return columns, clean_rows


def create_dashboard(
    ws: WorkspaceClient,
    warehouse_id: str,
    space_id: str,
    company_name: str,
    company_description: str,
    tables_info: list[dict],
    catalog: str,
    schema_name: str,
    *,
    databricks_host: str,
    databricks_token: str,
    schema_def: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Design dashboard panels, execute SQL, validate charts, and store results.

    Args:
        ws: Databricks WorkspaceClient.
        warehouse_id: SQL warehouse ID.
        space_id: Space ID to store dashboard for.
        company_name: Company name.
        company_description: Company description.
        tables_info: Table metadata list.
        catalog: UC catalog.
        schema_name: UC schema.
        databricks_host: Workspace ID for AI Gateway.
        databricks_token: PAT token.
        schema_def: Full schema with columns (for rich LLM prompt).

    Returns:
        Dashboard payload dict, or None if creation failed.
    """
    # Step 1: Design panels via LLM
    try:
        panel_defs = design_dashboard(
            company_name, company_description, tables_info, catalog, schema_name,
            databricks_host=databricks_host, databricks_token=databricks_token,
            schema_def=schema_def,
        )
    except Exception:
        logger.exception("Dashboard design failed")
        return None

    if not panel_defs:
        logger.warning("No panel definitions generated")
        return None

    # Step 2: Execute each panel's SQL and validate
    panels = []
    for i, pdef in enumerate(panel_defs):
        title = pdef.get("title", f"Panel {i}")
        sql = pdef.get("sql", "")
        chart_type = pdef.get("chart_type", "bar")
        position = pdef.get("position", i)

        if not sql:
            logger.warning("SKIP '%s': no SQL", title)
            continue

        try:
            columns, data = _execute_panel_sql(ws, warehouse_id, sql)
            if not data:
                logger.warning("SKIP '%s': no data returned", title)
                continue

            # Step 3: Validate chart type using our suggest_chart logic
            suggestion = suggest_chart(columns, data)
            if suggestion:
                # Override LLM's chart_type if our heuristic disagrees
                chart_type = suggestion.chart_type

            panels.append({
                "id": uuid.uuid4().hex[:12],
                "title": title,
                "chart_type": chart_type,
                "sql": sql,
                "columns": columns,
                "data": data[:20],  # Cap at 20 rows
                "position": position,
            })
            logger.info("OK '%s': %d rows, type=%s", title, len(data), chart_type)

        except Exception:
            logger.exception("FAIL '%s'", title)

    if not panels:
        logger.warning("No panels succeeded")
        return None

    # Step 4: Build payload
    dashboard_payload = {
        "panels": panels,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    dashboard_json_str = json.dumps(dashboard_payload).replace("'", "''")

    # Step 5: Write to spaces table
    try:
        run_sql(
            ws,
            f"UPDATE {_SPACES_TABLE} SET dashboard_json = '{dashboard_json_str}' WHERE space_id = '{_escape(space_id)}'",
        )
        logger.info("Dashboard written to spaces table for %s", space_id)
    except Exception:
        logger.exception("Failed to write dashboard to spaces table")

    # Step 6: Also write to sessions table (backward compat)
    try:
        safe_name = company_name.replace("'", "''")
        run_sql(
            ws,
            f"UPDATE {_SESSIONS_TABLE} SET dashboard_json = '{dashboard_json_str}' WHERE company_name = '{safe_name}'",
            raise_on_error=False,
        )
    except Exception:
        logger.debug("Failed to write dashboard to sessions table (non-critical)")

    logger.info("Dashboard created: %d panels for '%s'", len(panels), company_name)
    return dashboard_payload
