"""Creates Delta tables, Genie Space, and stores session metadata in Databricks."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

import requests
from databricks.sdk import WorkspaceClient

from .data_generator import get_sql_type

logger = logging.getLogger(__name__)


def _run_sql(ws: WorkspaceClient, warehouse_id: str, sql: str) -> dict[str, Any]:
    """Execute a SQL statement via the Databricks SQL API.

    Args:
        ws: Databricks WorkspaceClient.
        warehouse_id: SQL warehouse ID.
        sql: SQL statement to execute.

    Returns:
        API response dict.
    """
    resp = ws.api_client.do(
        "POST",
        "/api/2.0/sql/statements",
        body={
            "statement": sql,
            "warehouse_id": warehouse_id,
            "wait_timeout": "60s",
        },
    )
    state = resp.get("status", {}).get("state", "UNKNOWN")
    if state != "SUCCEEDED":
        logger.warning("SQL %s: %s — %s", state, sql[:80], resp)
    return resp


def create_schema(
    ws: WorkspaceClient,
    catalog: str,
    schema_name: str,
    warehouse_id: str,
) -> None:
    """Create a UC schema and volume for the company's data.

    Args:
        ws: Databricks WorkspaceClient.
        catalog: UC catalog name.
        schema_name: Schema name to create.
        warehouse_id: SQL warehouse ID.
    """
    logger.info("Creating schema %s.%s...", catalog, schema_name)
    _run_sql(ws, warehouse_id, f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema_name}`")
    _run_sql(ws, warehouse_id, f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema_name}`.raw_data")


def create_tables(
    ws: WorkspaceClient,
    catalog: str,
    schema_name: str,
    warehouse_id: str,
    schema_def: dict[str, Any],
    table_data: dict[str, list[dict]],
) -> list[dict[str, str]]:
    """Create Delta tables from generated data using SQL INSERT.

    Args:
        ws: Databricks WorkspaceClient.
        catalog: UC catalog name.
        schema_name: Schema name.
        warehouse_id: SQL warehouse ID.
        schema_def: LLM-designed schema with table definitions.
        table_data: Generated data from Faker, keyed by table name.

    Returns:
        List of table info dicts with full_name, table_name, comment.
    """
    tables_info = []

    for table_def in schema_def["tables"]:
        table_name = table_def["name"]
        full_name = f"`{catalog}`.`{schema_name}`.`{table_name}`"
        comment = table_def.get("comment", "")
        columns = table_def["columns"]
        rows = table_data.get(table_name, [])

        if not rows:
            logger.warning("No data for table %s, skipping", table_name)
            continue

        # Build column definitions
        col_defs = []
        for col in columns:
            sql_type = get_sql_type(col["faker"])
            col_comment = col.get("comment", "")
            col_def = f"`{col['name']}` {sql_type}"
            if col_comment:
                col_def += f" COMMENT '{col_comment.replace(chr(39), chr(39)+chr(39))}'"
            col_defs.append(col_def)

        # Drop and create table
        logger.info("Creating table %s (%d rows)...", full_name, len(rows))
        _run_sql(ws, warehouse_id, f"DROP TABLE IF EXISTS {full_name}")

        create_sql = f"CREATE TABLE {full_name} ({', '.join(col_defs)})"
        if comment:
            create_sql += f" COMMENT '{comment.replace(chr(39), chr(39)+chr(39))}'"
        _run_sql(ws, warehouse_id, create_sql)

        # Insert data in batches
        col_names = [col["name"] for col in columns]
        batch_size = 200
        for batch_start in range(0, len(rows), batch_size):
            batch = rows[batch_start : batch_start + batch_size]
            value_rows = []
            for row in batch:
                values = []
                for col in columns:
                    val = row.get(col["name"])
                    sql_type = get_sql_type(col["faker"])
                    if val is None:
                        values.append("NULL")
                    elif sql_type in ("STRING", "DATE"):
                        escaped = str(val).replace("'", "''")
                        values.append(f"'{escaped}'")
                    elif sql_type == "BOOLEAN":
                        values.append("TRUE" if val else "FALSE")
                    else:
                        values.append(str(val))
                value_rows.append(f"({', '.join(values)})")

            insert_sql = (
                f"INSERT INTO {full_name} ({', '.join(f'`{c}`' for c in col_names)}) "
                f"VALUES {', '.join(value_rows)}"
            )
            _run_sql(ws, warehouse_id, insert_sql)

        tables_info.append({
            "full_name": f"{catalog}.{schema_name}.{table_name}",
            "table_name": table_name,
            "comment": comment,
        })
        logger.info("Table %s created with %d rows", full_name, len(rows))

    return tables_info


def create_genie_space(
    ws: WorkspaceClient,
    warehouse_id: str,
    display_name: str,
    description: str,
    table_identifiers: list[str],
    sample_questions: list[str],
) -> str:
    """Create a Databricks Genie Space via REST API.

    Args:
        ws: Databricks WorkspaceClient.
        warehouse_id: SQL warehouse ID.
        display_name: Display name for the Genie Space.
        description: Company description.
        table_identifiers: List of full table names (catalog.schema.table).
        sample_questions: Sample questions for the space.

    Returns:
        The space_id of the created Genie Space.
    """
    logger.info("Creating Genie Space: %s", display_name)

    # Get current user for parent_path
    me = ws.current_user.me()
    parent_path = f"/Workspace/Users/{me.user_name}"

    # Sort tables alphabetically (API requirement)
    sorted_tables = sorted(table_identifiers)

    serialized = {
        "version": 2,
        "data_sources": {
            "tables": [{"identifier": tid} for tid in sorted_tables],
        },
        "config": {
            "sample_questions": [
                {"id": uuid.uuid4().hex, "question": [q]}
                for q in sample_questions
            ],
        },
        "instructions": {
            "text_instructions": [
                {"id": uuid.uuid4().hex, "content": [description]},
            ],
        },
    }

    payload = {
        "title": display_name,
        "description": description,
        "warehouse_id": warehouse_id,
        "parent_path": parent_path,
        "serialized_space": json.dumps(serialized),
    }

    # Use requests directly since SDK may not have the create space method
    host = ws.config.host.rstrip("/")
    headers = {
        "Authorization": f"Bearer {ws.config.token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(f"{host}/api/2.0/genie/spaces", headers=headers, json=payload)
    resp.raise_for_status()
    space = resp.json()
    space_id = space.get("space_id") or space.get("id", "")
    logger.info("Created Genie Space: %s", space_id)
    return space_id


def ensure_sessions_table(
    ws: WorkspaceClient,
    catalog: str,
    metadata_schema: str,
    warehouse_id: str,
) -> None:
    """Create the sessions metadata table if it doesn't exist.

    Args:
        ws: Databricks WorkspaceClient.
        catalog: UC catalog name.
        metadata_schema: Schema where the sessions table lives.
        warehouse_id: SQL warehouse ID.
    """
    full_name = f"`{catalog}`.`{metadata_schema}`.`sessions`"
    _run_sql(ws, warehouse_id, f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{metadata_schema}`")
    _run_sql(
        ws,
        warehouse_id,
        f"""CREATE TABLE IF NOT EXISTS {full_name} (
            session_id STRING NOT NULL COMMENT 'Unique session identifier',
            space_id STRING NOT NULL COMMENT 'Genie Space ID',
            company_name STRING NOT NULL COMMENT 'Company display name',
            description STRING COMMENT 'Company description',
            schema_name STRING NOT NULL COMMENT 'UC schema where company tables live',
            logo_path STRING COMMENT 'Path to company logo',
            primary_color STRING DEFAULT '#1a73e8' COMMENT 'Brand primary color',
            secondary_color STRING DEFAULT '#ea4335' COMMENT 'Brand secondary color',
            accent_color STRING DEFAULT '' COMMENT 'Brand accent color',
            chart_colors_json STRING COMMENT 'JSON array of chart hex colors',
            tables_json STRING COMMENT 'JSON array of table metadata',
            sample_questions_json STRING COMMENT 'JSON array of sample questions',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When this session was created'
        ) COMMENT 'Metadata for all created Genie Spaces'""",
    )
    logger.info("Sessions table ready: %s", full_name)


def save_session(
    ws: WorkspaceClient,
    catalog: str,
    metadata_schema: str,
    warehouse_id: str,
    *,
    space_id: str,
    company_name: str,
    description: str,
    schema_name: str,
    tables_info: list[dict[str, str]],
    sample_questions: list[str],
    logo_path: str = "",
    primary_color: str = "#1a73e8",
    secondary_color: str = "#ea4335",
    accent_color: str = "",
    chart_colors: list[str] | None = None,
) -> str:
    """Save a session record to the sessions metadata table.

    Args:
        ws: Databricks WorkspaceClient.
        catalog: UC catalog name.
        metadata_schema: Schema where the sessions table lives.
        warehouse_id: SQL warehouse ID.
        space_id: Genie Space ID.
        company_name: Company name.
        description: Company description.
        schema_name: UC schema for this company's tables.
        tables_info: List of table metadata dicts.
        sample_questions: Sample questions for the space.
        logo_path: Path to company logo.
        primary_color: Brand primary color hex.
        secondary_color: Brand secondary color hex.
        accent_color: Brand accent color hex.
        chart_colors: List of chart hex colors.

    Returns:
        The session_id.
    """
    session_id = uuid.uuid4().hex
    tables_json = json.dumps(tables_info).replace("'", "''")
    questions_json = json.dumps(sample_questions).replace("'", "''")
    chart_colors_json = json.dumps(chart_colors or []).replace("'", "''")
    desc_escaped = description.replace("'", "''")
    name_escaped = company_name.replace("'", "''")

    full_name = f"`{catalog}`.`{metadata_schema}`.`sessions`"
    _run_sql(
        ws,
        warehouse_id,
        f"""INSERT INTO {full_name}
            (session_id, space_id, company_name, description, schema_name,
             logo_path, primary_color, secondary_color, accent_color, chart_colors_json,
             tables_json, sample_questions_json)
        VALUES
            ('{session_id}', '{space_id}', '{name_escaped}', '{desc_escaped}', '{schema_name}',
             '{logo_path}', '{primary_color}', '{secondary_color}', '{accent_color}', '{chart_colors_json}',
             '{tables_json}', '{questions_json}')""",
    )
    logger.info("Session saved: %s (space: %s)", session_id, space_id)
    return session_id


def write_state_json(
    ws: WorkspaceClient,
    catalog: str,
    schema_name: str,
    *,
    space_id: str,
    display_name: str,
    warehouse_id: str,
    tables_info: list[dict[str, str]],
    sample_questions: list[str],
    company_name: str,
    description: str,
    logo_path: str = "",
    primary_color: str = "#1a73e8",
    secondary_color: str = "#ea4335",
    accent_color: str = "",
    chart_colors: list[str] | None = None,
) -> None:
    """Write state.json to UC Volume for the app to read.

    Args:
        ws: Databricks WorkspaceClient.
        catalog: UC catalog name.
        schema_name: Schema name.
        space_id: Genie Space ID.
        display_name: Display name.
        warehouse_id: SQL warehouse ID.
        tables_info: Table metadata list.
        sample_questions: Sample questions.
        company_name: Company name.
        description: Company description.
        logo_path: Logo path.
        primary_color: Primary brand color.
        secondary_color: Secondary brand color.
        accent_color: Accent brand color.
        chart_colors: List of chart hex colors.
    """
    state = {
        "space_id": space_id,
        "display_name": display_name,
        "catalog": catalog,
        "schema_name": schema_name,
        "warehouse_id": warehouse_id,
        "tables": tables_info,
        "sample_questions": sample_questions,
        "branding": {
            "company_name": company_name,
            "description": description,
            "logo_path": logo_path,
            "primary_color": primary_color,
            "secondary_color": secondary_color,
            "accent_color": accent_color,
            "chart_colors": chart_colors or [],
        },
    }

    volume_path = f"/Volumes/{catalog}/{schema_name}/raw_data/state.json"
    state_bytes = json.dumps(state, indent=2).encode("utf-8")

    import io
    ws.files.upload(volume_path, io.BytesIO(state_bytes), overwrite=True)
    logger.info("State written to %s", volume_path)
