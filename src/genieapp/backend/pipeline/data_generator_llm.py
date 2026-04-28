"""LLM-powered data generator — produces realistic data via Claude instead of Faker.
Supports parallel generation of independent tables."""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a data engineer generating realistic sample data for a company's analytics database.
You MUST return ONLY a valid JSON array of row objects. No markdown fences, no explanation, no text before or after.

RULES:
1. Use REAL, realistic data — real city names, real product names, realistic prices and amounts.
2. Dates must be ISO format (YYYY-MM-DD) within the last 2 years.
3. Numeric values must be realistic for the business domain (not random large numbers).
4. Primary key / ID columns should be sequential integers starting from 1.
5. Foreign key columns must ONLY use values from the provided parent ID list.
6. Ensure good variety — don't repeat the same values. Spread data across categories.
7. For monetary values, use realistic amounts with 2 decimal places.
8. For status/category columns, use a realistic distribution (not perfectly uniform).
9. String values should look like real business data, not lorem ipsum or gibberish.
10. Every row must have ALL columns — no missing fields.
"""

MAX_BATCH_SIZE = 75  # Keep batches small to avoid JSON parse errors


def _parse_json_array(raw: str) -> list[dict]:
    """Parse LLM output into a JSON array, handling common formatting issues."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start >= 0 and end > start:
        raw = raw[start:end]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    return json.loads(raw)


def _build_column_descriptions(table_def: dict) -> str:
    """Build column description string for the LLM prompt."""
    lines = []
    for col in table_def.get("columns", []):
        name = col["name"]
        sql_type = col.get("sql_type", col.get("type", "STRING"))
        comment = col.get("comment", "")
        is_pk = col.get("primary_key", False)
        fk_ref = col.get("references", "")

        desc = f"- {name} ({sql_type})"
        if comment:
            desc += f": {comment}"
        if is_pk:
            desc += " [PRIMARY KEY, sequential integer starting from 1]"
        if fk_ref:
            desc += f" [FOREIGN KEY → {fk_ref}]"
        lines.append(desc)
    return "\n".join(lines)


def _build_fk_context(table_def: dict, generated_tables: dict[str, list[dict]]) -> str:
    """Build FK value context so the LLM uses valid parent IDs."""
    fk_lines = []
    for col in table_def.get("columns", []):
        fk_ref = col.get("references", "")
        if not fk_ref:
            continue

        if "." in fk_ref:
            ref_table, ref_col = fk_ref.split(".", 1)
        else:
            ref_table, ref_col = fk_ref, f"{fk_ref}_id"

        parent_rows = generated_tables.get(ref_table, [])
        if parent_rows:
            parent_ids = [row.get(ref_col) for row in parent_rows if row.get(ref_col) is not None]
            if parent_ids:
                if len(parent_ids) <= 50:
                    id_str = str(parent_ids)
                else:
                    import random
                    sample = random.sample(parent_ids, 50)
                    id_str = f"{sample} (sampled from {len(parent_ids)} total)"
                fk_lines.append(f"- Column '{col['name']}' must use values from: {id_str}")

    if fk_lines:
        return "Foreign key constraints (use ONLY these values):\n" + "\n".join(fk_lines)
    return ""


def _get_table_dependencies(table_def: dict) -> set[str]:
    """Get the set of table names this table depends on via FK references."""
    deps = set()
    for col in table_def.get("columns", []):
        ref = col.get("references", "")
        if ref:
            ref_table = ref.split(".")[0] if "." in ref else ref
            deps.add(ref_table)
    return deps


def generate_table_data_llm(
    table_def: dict,
    company_name: str,
    company_description: str,
    generated_tables: dict[str, list[dict]],
    row_count: int = 100,
    *,
    databricks_host: str,
    databricks_token: str,
    model: str = "opendoor-claude-opus-46",
) -> list[dict]:
    """Generate realistic data for one table via LLM."""
    client = OpenAI(
        api_key=databricks_token,
        base_url=f"https://{databricks_host}.ai-gateway.cloud.databricks.com/mlflow/v1",
    )

    table_name = table_def["name"]
    table_comment = table_def.get("comment", "")
    col_desc = _build_column_descriptions(table_def)
    fk_context = _build_fk_context(table_def, generated_tables)

    base_prompt = f"""Company: {company_name}
Description: {company_description}

Table: "{table_name}"
{f"Table description: {table_comment}" if table_comment else ""}

Columns:
{col_desc}

{fk_context}"""

    logger.info("Generating %d rows for '%s' via LLM...", row_count, table_name)

    all_rows: list[dict] = []
    batch_size = min(row_count, MAX_BATCH_SIZE)
    remaining = row_count
    max_retries = 2

    while remaining > 0:
        current_batch = min(batch_size, remaining)

        if all_rows:
            batch_prompt = f"""{base_prompt}

Generate exactly {current_batch} rows. Continue sequential IDs from {len(all_rows) + 1}.
Do NOT repeat any previously generated data.
Return a JSON array of {current_batch} row objects. Each row must have ALL columns."""
        else:
            batch_prompt = f"""{base_prompt}

Generate exactly {current_batch} rows.
Return a JSON array of {current_batch} row objects. Each row must have ALL columns."""

        for attempt in range(max_retries + 1):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    max_tokens=16384,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": batch_prompt},
                    ],
                )

                raw = resp.choices[0].message.content.strip()
                rows = _parse_json_array(raw)

                if not isinstance(rows, list):
                    raise ValueError(f"Expected array, got {type(rows).__name__}")

                all_rows.extend(rows)
                remaining -= len(rows)
                logger.info("  Got %d rows for '%s' (total: %d/%d)", len(rows), table_name, len(all_rows), row_count)
                break  # Success, exit retry loop

            except (json.JSONDecodeError, ValueError) as e:
                if attempt < max_retries:
                    logger.warning("  Parse error for '%s' (attempt %d/%d): %s — retrying", table_name, attempt + 1, max_retries + 1, str(e)[:100])
                else:
                    logger.error("  Failed to parse LLM output for '%s' after %d attempts", table_name, max_retries + 1)
                    remaining = 0  # Give up on remaining rows
                    break
            except Exception as e:
                logger.error("  LLM call failed for '%s': %s", table_name, e)
                remaining = 0
                break

    logger.info("Generated %d rows for '%s'", len(all_rows), table_name)
    return all_rows[:row_count]


def generate_all_tables_llm(
    schema: dict[str, Any],
    company_name: str,
    company_description: str,
    *,
    databricks_host: str,
    databricks_token: str,
    model: str = "opendoor-claude-opus-46",
) -> dict[str, list[dict]]:
    """Generate data for all tables using LLM, with parallel execution for independent tables.

    Tables are grouped into dependency levels:
    - Level 0: tables with no FK dependencies (generated in parallel)
    - Level 1: tables that depend only on level 0 (generated in parallel after level 0)
    - etc.
    """
    tables_by_name = {t["name"]: t for t in schema["tables"]}
    generated: dict[str, list[dict]] = {}

    # Build dependency graph and group into levels
    levels: list[list[str]] = []
    resolved: set[str] = set()
    remaining_tables = set(tables_by_name.keys())

    while remaining_tables:
        # Find tables whose dependencies are all resolved
        current_level = []
        for name in remaining_tables:
            deps = _get_table_dependencies(tables_by_name[name])
            if deps.issubset(resolved):
                current_level.append(name)

        if not current_level:
            # Circular dependency or missing table — just add remaining
            logger.warning("Could not resolve dependencies for: %s — generating sequentially", remaining_tables)
            current_level = list(remaining_tables)

        levels.append(current_level)
        resolved.update(current_level)
        remaining_tables -= set(current_level)

    logger.info("Table generation levels: %s", [[t for t in level] for level in levels])

    # Generate each level in parallel
    for level_idx, level_tables in enumerate(levels):
        logger.info("=== Generating level %d: %s ===", level_idx, level_tables)

        def _gen_table(table_name: str) -> tuple[str, list[dict]]:
            table_def = tables_by_name[table_name]
            row_count = table_def.get("row_count", 100)
            rows = generate_table_data_llm(
                table_def=table_def,
                company_name=company_name,
                company_description=company_description,
                generated_tables=generated,  # Only contains completed levels
                row_count=row_count,
                databricks_host=databricks_host,
                databricks_token=databricks_token,
                model=model,
            )
            return table_name, rows

        if len(level_tables) == 1:
            # Single table — no need for thread pool
            name, rows = _gen_table(level_tables[0])
            generated[name] = rows
        else:
            # Multiple independent tables — generate in parallel
            with ThreadPoolExecutor(max_workers=min(len(level_tables), 4)) as executor:
                futures = {executor.submit(_gen_table, name): name for name in level_tables}
                for future in as_completed(futures):
                    name, rows = future.result()
                    generated[name] = rows

    return generated
