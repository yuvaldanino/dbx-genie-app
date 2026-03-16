"""Main pipeline orchestrator — company description → Genie Space."""

from __future__ import annotations

import logging
import re
from typing import Any

from databricks.sdk import WorkspaceClient

from .data_generator import generate_all_tables
from .schema_designer import design_schema
from .theme_generator import generate_theme
from .space_creator import (
    create_genie_space,
    create_schema,
    create_tables,
    ensure_sessions_table,
    save_session,
    write_state_json,
)

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Convert a company name to a valid UC schema name.

    Args:
        name: Company name.

    Returns:
        Lowercase snake_case string safe for UC schema names.
    """
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_")
    # Ensure it doesn't start with a number
    if slug and slug[0].isdigit():
        slug = f"co_{slug}"
    return slug[:50]  # UC schema name length limit


def run_pipeline(
    company_description: str,
    company_name: str | None = None,
    *,
    catalog: str,
    warehouse_id: str,
    metadata_schema: str = "genie_app",
    databricks_host: str,
    databricks_token: str,
    logo_path: str = "",
    primary_color: str = "#1a73e8",
    secondary_color: str = "#ea4335",
) -> dict[str, Any]:
    """Run the full pipeline: design schema → generate data → create space.

    Args:
        company_description: Free-text description of the company.
        company_name: Optional explicit company name (extracted from description if not given).
        catalog: UC catalog to create tables in.
        warehouse_id: SQL warehouse ID.
        metadata_schema: Schema for the sessions metadata table.
        databricks_host: Workspace ID for AI Gateway (e.g. "7474655921234161").
        databricks_token: Databricks PAT token.
        logo_path: Path to company logo.
        primary_color: Brand primary color.
        secondary_color: Brand secondary color.

    Returns:
        Dict with space_id, session_id, schema_name, tables, sample_questions.
    """
    ws = WorkspaceClient()

    # Step 1: Design schema with LLM
    logger.info("=== Step 1: Designing schema ===")
    schema_def = design_schema(
        company_description,
        databricks_host=databricks_host,
        databricks_token=databricks_token,
    )

    # Extract company name from description if not provided
    if not company_name:
        company_name = company_description.split(".")[0].split(",")[0].strip()[:60]

    schema_name = _slugify(company_name)
    display_name = f"{company_name} Analytics"

    logger.info("Company: %s, Schema: %s.%s", company_name, catalog, schema_name)
    logger.info("Tables: %s", [t["name"] for t in schema_def["tables"]])

    # Step 1.5: Generate brand theme with LLM
    logger.info("=== Step 1.5: Generating brand theme ===")
    try:
        theme = generate_theme(
            company_name,
            company_description,
            databricks_host=databricks_host,
            databricks_token=databricks_token,
        )
        primary_color = theme["primary"]
        secondary_color = theme["secondary"]
        accent_color = theme["accent"]
        chart_colors = theme["chart_colors"]
    except Exception as e:
        logger.warning("Theme generation failed, using defaults: %s", e)
        accent_color = primary_color
        chart_colors = [primary_color, secondary_color, primary_color, secondary_color, primary_color]

    # Step 2: Generate data with Faker
    logger.info("=== Step 2: Generating data ===")
    table_data = generate_all_tables(schema_def)

    # Step 3: Create UC schema and tables
    logger.info("=== Step 3: Creating tables in Databricks ===")
    create_schema(ws, catalog, schema_name, warehouse_id)
    tables_info = create_tables(
        ws, catalog, schema_name, warehouse_id, schema_def, table_data,
    )

    table_identifiers = [t["full_name"] for t in tables_info]
    sample_questions = schema_def.get("sample_questions", [])

    # Step 4: Create Genie Space
    logger.info("=== Step 4: Creating Genie Space ===")
    space_id = create_genie_space(
        ws, warehouse_id, display_name, company_description,
        table_identifiers, sample_questions,
    )

    # Step 5: Save session metadata
    logger.info("=== Step 5: Saving session ===")
    ensure_sessions_table(ws, catalog, metadata_schema, warehouse_id)
    session_id = save_session(
        ws, catalog, metadata_schema, warehouse_id,
        space_id=space_id,
        company_name=company_name,
        description=company_description,
        schema_name=schema_name,
        tables_info=tables_info,
        sample_questions=sample_questions,
        logo_path=logo_path,
        primary_color=primary_color,
        secondary_color=secondary_color,
        accent_color=accent_color,
        chart_colors=chart_colors,
    )

    # Step 6: Write state.json to volume
    logger.info("=== Step 6: Writing state.json ===")
    write_state_json(
        ws, catalog, schema_name,
        space_id=space_id,
        display_name=display_name,
        warehouse_id=warehouse_id,
        tables_info=tables_info,
        sample_questions=sample_questions,
        company_name=company_name,
        description=company_description,
        logo_path=logo_path,
        primary_color=primary_color,
        secondary_color=secondary_color,
        accent_color=accent_color,
        chart_colors=chart_colors,
    )

    result = {
        "space_id": space_id,
        "session_id": session_id,
        "schema_name": schema_name,
        "company_name": company_name,
        "display_name": display_name,
        "tables": tables_info,
        "sample_questions": sample_questions,
    }

    logger.info("=== Pipeline complete! ===")
    logger.info("Space ID: %s", space_id)
    logger.info("Session ID: %s", session_id)
    logger.info("Schema: %s.%s", catalog, schema_name)

    return result
