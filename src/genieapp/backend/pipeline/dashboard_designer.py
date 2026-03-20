"""LLM-powered dashboard panel designer — generates pre-computed dashboard definitions from table schemas."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a data dashboard designer. Given table schemas for a company's analytics database, generate 4-6 dashboard panel definitions.

RULES:
1. Start with 1-2 KPI panels (single aggregate number), then categorical charts, then time series.
2. Each panel's SQL must use fully-qualified 3-part table names (catalog.schema.table).
3. Keep SQL simple — single table queries, basic aggregates, GROUP BY. MAX 20 rows per query.
4. chart_type must be one of: kpi, bar, line, pie, area
5. For KPI: SQL should return exactly 1 row with 1 numeric column.
6. For bar/pie: SQL should return a categorical column + a numeric column.
7. For line/area: SQL should return a date/time column + a numeric column, ORDER BY the date column.
8. Position panels logically: KPIs first (position 0,1), then charts (position 2,3,4,5).

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


def design_dashboard(
    company_name: str,
    company_description: str,
    tables_info: list[dict],
    catalog: str,
    schema_name: str,
    *,
    databricks_host: str,
    databricks_token: str,
    model: str = "opendoor-claude-opus-46",
) -> list[dict[str, Any]]:
    """Call the LLM to generate dashboard panel definitions.

    Args:
        company_name: Company name.
        company_description: Free-text description.
        tables_info: List of table metadata dicts (full_name, columns, etc.).
        catalog: UC catalog name.
        schema_name: UC schema name.
        databricks_host: Databricks workspace ID for AI Gateway.
        databricks_token: Databricks PAT token.
        model: Model name on the AI Gateway.

    Returns:
        List of panel definition dicts.
    """
    client = OpenAI(
        api_key=databricks_token,
        base_url=f"https://{databricks_host}.ai-gateway.cloud.databricks.com/mlflow/v1",
    )

    # Build table schema description for the prompt
    tables_desc = []
    for t in tables_info:
        full_name = t.get("full_name", f"{catalog}.{schema_name}.{t.get('table_name', '')}")
        cols = t.get("columns", [])
        if cols:
            col_lines = [f"  - {c.get('name', '')}: {c.get('type', '')} ({c.get('comment', '')})" for c in cols]
            tables_desc.append(f"Table: {full_name}\nColumns:\n" + "\n".join(col_lines))
        else:
            tables_desc.append(f"Table: {full_name}")

    prompt = (
        f"Company: {company_name}\n"
        f"Description: {company_description}\n"
        f"Catalog: {catalog}, Schema: {schema_name}\n\n"
        f"Tables:\n{'---'.join(tables_desc)}"
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
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    # Extract JSON array
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start >= 0 and end > start:
        raw = raw[start:end]
    # Fix trailing commas
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    try:
        panels = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Dashboard JSON parse failed at position %d. Raw:\n%s", e.pos, raw)
        raise

    if not isinstance(panels, list):
        raise ValueError(f"Expected JSON array, got {type(panels).__name__}")

    logger.info("Dashboard designed: %d panels", len(panels))
    return panels
