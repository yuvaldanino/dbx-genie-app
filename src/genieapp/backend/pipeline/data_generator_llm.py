"""Spec-based data generator — LLM designs distribution specs, Python generates rows."""

from __future__ import annotations

import datetime
import json
import logging
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)

SPEC_PROMPT = (
    "You are a data engineer designing a data generation specification.\n"
    "Output ONLY valid JSON, no markdown fences.\n\n"
    "For EACH column, provide {dist: TYPE, ...params}. Valid types:\n"
    "  sequential: {start:1}\n"
    "  fk_sample: {from_table:'X', from_column:'Y'}\n"
    "  weighted_choice: {values:['A','B'], weights:[0.6,0.4]}\n"
    "  uniform_int: {min:1, max:100}\n"
    "  uniform_float: {min:0.0, max:1000.0, decimals:2}\n"
    "  normal: {mean:50000, std:15000, min:20000, max:200000, decimals:2}\n"
    "  date_range: {start:'2023-01-01', end:'2025-04-28'}\n"
    "  boolean: {true_pct:0.7}\n"
    "  formula: {expr:'col_a * 0.85'} — for derived columns\n\n"
    "RULES:\n"
    "- Use formula for correlated columns (outstanding_balance from principal, maturity from origination)\n"
    "- Use normal for continuous numerics, weighted_choice ONLY for categorical\n"
    "- Dimension tables: all rows as fixtures (max 25). Fact: max 10 fixtures.\n"
    "- Every column MUST be in the columns dict.\n"
    "- weighted_choice values must be REAL domain-specific data.\n\n"
    "OUTPUT: {columns: {...}, fixtures: [...]}"
)


def _parse_json(raw: str) -> Any:
    """Parse LLM JSON output, handling fences and trailing commas."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw[: raw.rfind("```")]
    for sc, ec in [("{", "}"), ("[", "]")]:
        s, e = raw.find(sc), raw.rfind(ec) + 1
        if s >= 0 and e > s:
            c = re.sub(r",\s*([}\]])", r"\1", raw[s:e])
            try:
                return json.loads(c)
            except json.JSONDecodeError:
                continue
    return json.loads(raw)


def _get_table_dependencies(table_def: dict) -> set[str]:
    """Get table names this table depends on via FK references."""
    deps = set()
    for c in table_def.get("columns", []):
        ref = c.get("references", "")
        if ref:
            deps.add(ref.split(".")[0] if "." in ref else ref)
    return deps


def _generate_spec(
    table_def: dict,
    company_name: str,
    company_description: str,
    generated_tables: dict[str, list[dict]],
    must_answer_questions: list[str] | None,
    *,
    databricks_host: str,
    databricks_token: str,
    model: str,
) -> dict:
    """Ask LLM to design a data generation spec for one table."""
    client = OpenAI(
        api_key=databricks_token,
        base_url=f"https://{databricks_host}.ai-gateway.cloud.databricks.com/mlflow/v1",
    )
    name = table_def["name"]

    col_lines = []
    for c in table_def["columns"]:
        d = f"- {c['name']} ({c.get('type', 'STRING')})"
        if c.get("comment"):
            d += f": {c['comment']}"
        if c.get("primary_key"):
            d += " [PK]"
        if c.get("references"):
            d += f" [FK -> {c['references']}]"
        col_lines.append(d)

    fk_info = []
    for c in table_def["columns"]:
        ref = c.get("references", "")
        if not ref:
            continue
        rt = ref.split(".")[0] if "." in ref else ref
        rc = ref.split(".")[1] if "." in ref else f"{ref}_id"
        parent = generated_tables.get(rt, [])
        if parent:
            ids = list(set(str(r.get(rc)) for r in parent if r.get(rc) is not None))[:40]
            fk_info.append(f"Available {c['name']} values: {ids}")

    questions_text = ""
    if must_answer_questions:
        questions_text = "\nMust-answer questions:\n" + "\n".join(f"- {q}" for q in must_answer_questions)

    prompt = (
        f"Company: {company_name}\n"
        f"Description: {company_description}\n"
        f"Table: \"{name}\" — {table_def.get('comment', '')}\n"
        f"Row count: {table_def.get('row_count', 100)} | Type: {table_def.get('table_type', 'fact')}\n\n"
        f"Columns:\n" + "\n".join(col_lines) + "\n"
        + ("\n".join(fk_info) + "\n" if fk_info else "")
        + questions_text + "\n\nDesign the spec."
    )

    for attempt in range(3):
        try:
            raw = client.chat.completions.create(
                model=model, max_tokens=8192,
                messages=[{"role": "system", "content": SPEC_PROMPT}, {"role": "user", "content": prompt}],
            ).choices[0].message.content.strip()
            return _parse_json(raw)
        except Exception as e:
            if attempt == 2:
                logger.error("[%s] Spec generation failed: %s", name, str(e)[:100])
                return {"columns": {}, "fixtures": []}
            logger.warning("[%s] Spec parse retry %d", name, attempt + 1)

    return {"columns": {}, "fixtures": []}


def _generate_rows_from_spec(
    spec: dict,
    row_count: int,
    generated_tables: dict[str, list[dict]],
    table_def: dict,
) -> list[dict]:
    """Generate rows from an LLM-designed spec with two-pass formula + sanity checks."""
    columns = spec.get("columns", {})
    fixtures = spec.get("fixtures", [])
    rows = list(fixtures)
    start_id = len(rows) + 1

    # Split regular vs formula columns
    regular_cols = {cn: cs for cn, cs in columns.items() if isinstance(cs, dict) and cs.get("dist") != "formula"}
    formula_cols = {cn: cs for cn, cs in columns.items() if isinstance(cs, dict) and cs.get("dist") == "formula"}

    for i in range(max(0, row_count - len(rows))):
        row = {}

        # PASS 1: Regular columns
        for cn, cs in regular_cols.items():
            dist = cs.get("dist", cs.get("type", ""))
            try:
                if dist == "sequential":
                    row[cn] = cs.get("start", 1) + len(fixtures) + i
                elif dist == "fk_sample":
                    parent = generated_tables.get(cs.get("from_table", ""), [])
                    ids = [r.get(cs.get("from_column", "")) for r in parent if r.get(cs.get("from_column", "")) is not None]
                    row[cn] = random.choice(ids) if ids else random.randint(1, 10)
                elif dist == "weighted_choice":
                    vals = cs.get("values", cs.get("choices", ["A"]))
                    wts = cs.get("weights", [1.0 / len(vals)] * len(vals))
                    if len(wts) != len(vals):
                        wts = [1.0 / len(vals)] * len(vals)
                    total = sum(wts)
                    row[cn] = random.choices(vals, weights=[w / total for w in wts], k=1)[0]
                elif dist == "uniform_int":
                    row[cn] = random.randint(int(cs.get("min", 0)), int(cs.get("max", 100)))
                elif dist in ("uniform_float", "uniform_double"):
                    row[cn] = round(random.uniform(float(cs.get("min", 0)), float(cs.get("max", 1000))), int(cs.get("decimals", 2)))
                elif dist in ("normal", "gaussian"):
                    v = np.random.normal(float(cs.get("mean", 50)), float(cs.get("std", cs.get("stddev", 10))))
                    v = max(float(cs.get("min", 0)), min(float(cs.get("max", 1e9)), v))
                    row[cn] = round(float(v), int(cs.get("decimals", 2)))
                elif dist == "date_range":
                    s = datetime.date.fromisoformat(str(cs.get("start", "2023-01-01")))
                    e = datetime.date.fromisoformat(str(cs.get("end", "2025-04-28")))
                    d = (e - s).days
                    row[cn] = (s + datetime.timedelta(days=random.randint(0, max(d, 1)))).isoformat()
                elif dist == "boolean":
                    row[cn] = random.random() < float(cs.get("true_pct", 0.5))
                elif dist in ("fixed", "constant"):
                    row[cn] = cs.get("value", "")
                else:
                    # Fallback: try to infer
                    if "values" in cs:
                        row[cn] = random.choice(cs["values"])
                    elif "min" in cs and "max" in cs:
                        row[cn] = round(random.uniform(float(cs["min"]), float(cs["max"])), 2)
                    else:
                        row[cn] = None
            except Exception:
                row[cn] = None

        # PASS 2: Formula columns (all dependencies now available)
        for cn, cs in formula_cols.items():
            expr = str(cs.get("expr", "0"))
            try:
                ctx = {"__builtins__": {}, "round": round, "max": max, "min": min, "abs": abs, "int": int, "float": float}
                ctx.update(row)
                val = eval(expr, ctx)
                row[cn] = round(val, 2) if isinstance(val, float) else val
            except Exception:
                # Fallback: find a referenced column and derive from it
                for other_cn, other_val in row.items():
                    if other_cn in expr and isinstance(other_val, (int, float)) and other_val > 0:
                        row[cn] = round(other_val * random.uniform(0.5, 0.95), 2)
                        break
                else:
                    row[cn] = 0

        rows.append(row)

    # PASS 3: Post-generation sanity checks
    for row in rows[len(fixtures):]:
        # outstanding_balance <= principal
        for bal in ("outstanding_balance", "remaining_balance"):
            for prin in ("principal_amount", "original_amount", "loan_amount"):
                if bal in row and prin in row and isinstance(row[bal], (int, float)) and isinstance(row[prin], (int, float)):
                    if row[bal] > row[prin]:
                        row[bal] = round(row[prin] * random.uniform(0.3, 0.95), 2)

        # selling_price > dealer_cost
        if "selling_price" in row and "dealer_cost_at_sale" in row:
            sp, dc = row["selling_price"], row["dealer_cost_at_sale"]
            if isinstance(sp, (int, float)) and isinstance(dc, (int, float)) and sp < dc:
                row["selling_price"] = round(dc * random.uniform(1.02, 1.25), 2)

        # gross_profit = selling_price - cost
        if "gross_profit" in row and "selling_price" in row and "dealer_cost_at_sale" in row:
            sp, dc = row["selling_price"], row["dealer_cost_at_sale"]
            if isinstance(sp, (int, float)) and isinstance(dc, (int, float)):
                row["gross_profit"] = round(sp - dc, 2)

        # collected_amount <= charge_amount
        if "collected_amount" in row and "charge_amount" in row:
            ca, ch = row["collected_amount"], row["charge_amount"]
            if isinstance(ca, (int, float)) and isinstance(ch, (int, float)) and ca > ch:
                row["collected_amount"] = round(ch * random.uniform(0.5, 0.95), 2)

        # maturity_date > origination_date
        for mat_col in ("maturity_date",):
            for orig_col in ("origination_date", "start_date"):
                if mat_col in row and orig_col in row:
                    mat, orig = row.get(mat_col), row.get(orig_col)
                    if mat in (0, "0", None) or (isinstance(mat, str) and isinstance(orig, str) and mat <= orig):
                        try:
                            orig_d = datetime.date.fromisoformat(str(orig)[:10])
                            term = row.get("term_months", 60)
                            if not isinstance(term, (int, float)):
                                term = 60
                            row[mat_col] = (orig_d + datetime.timedelta(days=int(term) * 30)).isoformat()
                        except Exception:
                            pass

    return rows[:row_count]


def generate_all_tables_llm(
    schema: dict[str, Any],
    company_name: str,
    company_description: str,
    *,
    databricks_host: str,
    databricks_token: str,
    must_answer_questions: list[str] | None = None,
    model: str = "opendoor-claude-opus-46",
) -> dict[str, list[dict]]:
    """Generate data for all tables using spec-based approach.

    LLM generates distribution specs per table, Python generates rows instantly.
    Independent tables get specs in parallel.

    Args:
        schema: Schema dict with "tables" list.
        company_name: Company name for context.
        company_description: Business description for context.
        databricks_host: Workspace ID for AI Gateway.
        databricks_token: PAT token.
        must_answer_questions: Optional questions the data must support.
        model: LLM model name.

    Returns:
        Dict mapping table_name → list of row dicts.
    """
    tables_by_name = {t["name"]: t for t in schema["tables"]}
    generated: dict[str, list[dict]] = {}

    # Build dependency levels
    levels: list[list[str]] = []
    resolved: set[str] = set()
    remaining = set(tables_by_name.keys())

    while remaining:
        current = [n for n in remaining if _get_table_dependencies(tables_by_name[n]).issubset(resolved)]
        if not current:
            current = list(remaining)
        levels.append(current)
        resolved.update(current)
        remaining -= set(current)

    logger.info("Table generation levels: %s", levels)

    # Generate level by level
    for level_idx, level_names in enumerate(levels):
        logger.info("=== Level %d: %s %s ===", level_idx, level_names, "(parallel)" if len(level_names) > 1 else "")

        def _gen_spec(table_name: str) -> tuple[str, dict]:
            spec = _generate_spec(
                table_def=tables_by_name[table_name],
                company_name=company_name,
                company_description=company_description,
                generated_tables=generated,
                must_answer_questions=must_answer_questions,
                databricks_host=databricks_host,
                databricks_token=databricks_token,
                model=model,
            )
            return table_name, spec

        # Generate specs (parallel for independent tables)
        specs: dict[str, dict] = {}
        if len(level_names) == 1:
            name, spec = _gen_spec(level_names[0])
            specs[name] = spec
            logger.info("[%s] Spec: %d cols, %d fixtures", name, len(spec.get("columns", {})), len(spec.get("fixtures", [])))
        else:
            with ThreadPoolExecutor(max_workers=min(len(level_names), 4)) as executor:
                futures = {executor.submit(_gen_spec, n): n for n in level_names}
                for future in as_completed(futures):
                    name, spec = future.result()
                    specs[name] = spec
                    logger.info("[%s] Spec: %d cols, %d fixtures", name, len(spec.get("columns", {})), len(spec.get("fixtures", [])))

        # Generate rows from specs
        for name in level_names:
            table_def = tables_by_name[name]
            row_count = table_def.get("row_count", 100)
            rows = _generate_rows_from_spec(specs[name], row_count, generated, table_def)
            generated[name] = rows
            logger.info("[%s] Generated %d rows", name, len(rows))

    return generated
