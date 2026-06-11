"""Genie space instruction generator — builds rich instructions from LIVE UC metadata.

Replaces the faker-format `build_genie_instructions` (which silently degraded for
v3 schemas: every column typed STRING, no relationships, no categorical values).
This builder needs no pipeline state: it reads table schemas via the UC API and
profiles the actual data (distinct values, date/numeric ranges) with cheap SQL,
so it works identically for retuning existing spaces and for new pipeline runs.
"""

from __future__ import annotations

import logging
from typing import Any

from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)

# STRING columns with at most this many distinct values are listed as categorical.
MAX_CATEGORICAL = 15
# Hard cap on instruction size (Genie handles large text, stay well clear of limits).
MAX_CHARS = 9000

_NUMERIC_TYPES = {"INT", "BIGINT", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL", "LONG"}
_MONEY_HINTS = ("amount", "price", "revenue", "total", "cost", "salary", "value", "spend", "usd")


def _sql(ws: WorkspaceClient, warehouse_id: str, statement: str) -> list[dict]:
    """Run a statement and return rows as dicts ([] on any failure)."""
    try:
        resp = ws.api_client.do(
            "POST",
            "/api/2.0/sql/statements",
            body={"statement": statement, "warehouse_id": warehouse_id, "wait_timeout": "50s"},
        )
        if resp.get("status", {}).get("state") != "SUCCEEDED":
            logger.warning("profile SQL %s: %s", resp.get("status", {}).get("state"), statement[:80])
            return []
        cols = [c["name"] for c in resp.get("manifest", {}).get("schema", {}).get("columns", [])]
        return [dict(zip(cols, row)) for row in resp.get("result", {}).get("data_array", [])]
    except Exception as e:
        logger.warning("profile SQL failed: %s — %s", str(e)[:120], statement[:80])
        return []


def _get_table_meta(ws: WorkspaceClient, full_name: str) -> dict[str, Any] | None:
    """Fetch table schema from UC: name, comment, columns(name/type/comment)."""
    try:
        t = ws.tables.get(full_name)
        return {
            "full_name": full_name,
            "name": t.name or full_name.split(".")[-1],
            "comment": t.comment or "",
            "columns": [
                {
                    "name": c.name or "",
                    "type": (c.type_text or str(c.type_name or "")).upper(),
                    "comment": c.comment or "",
                }
                for c in (t.columns or [])
            ],
        }
    except Exception as e:
        logger.warning("tables.get failed for %s: %s", full_name, str(e)[:120])
        return None


def _profile_table(ws: WorkspaceClient, warehouse_id: str, meta: dict) -> dict[str, Any]:
    """One pass of cheap profiling: distinct counts, date ranges, money ranges."""
    fq = meta["full_name"]
    quoted = ".".join(f"`{p}`" for p in fq.split("."))
    exprs: list[str] = ["COUNT(*) AS _row_count"]
    for c in meta["columns"]:
        name, typ = c["name"], c["type"]
        base = typ.split("(")[0]
        if base == "STRING":
            exprs.append(f"APPROX_COUNT_DISTINCT(`{name}`) AS `nd__{name}`")
        elif base in ("DATE", "TIMESTAMP", "TIMESTAMP_NTZ"):
            exprs.append(f"CAST(MIN(`{name}`) AS STRING) AS `min__{name}`")
            exprs.append(f"CAST(MAX(`{name}`) AS STRING) AS `max__{name}`")
        elif base in _NUMERIC_TYPES and any(h in name.lower() for h in _MONEY_HINTS):
            exprs.append(f"CAST(MIN(`{name}`) AS STRING) AS `min__{name}`")
            exprs.append(f"CAST(MAX(`{name}`) AS STRING) AS `max__{name}`")
    rows = _sql(ws, warehouse_id, f"SELECT {', '.join(exprs)} FROM {quoted}")
    profile: dict[str, Any] = dict(rows[0]) if rows else {}

    # Distinct values for low-cardinality string columns.
    values: dict[str, list[str]] = {}
    for c in meta["columns"]:
        nd = profile.get(f"nd__{c['name']}")
        try:
            nd_int = int(nd) if nd is not None else None
        except (TypeError, ValueError):
            nd_int = None
        if nd_int is not None and 1 <= nd_int <= MAX_CATEGORICAL:
            vr = _sql(
                ws, warehouse_id,
                f"SELECT DISTINCT `{c['name']}` AS v FROM {quoted} WHERE `{c['name']}` IS NOT NULL LIMIT {MAX_CATEGORICAL}",
            )
            vals = [str(r["v"]) for r in vr if r.get("v") is not None]
            # Skip free-text columns that merely happen to be small tables.
            if vals and max(len(v) for v in vals) <= 40:
                values[c["name"]] = vals
    profile["_values"] = values
    return profile


def _detect_relationships(metas: list[dict]) -> list[str]:
    """Heuristic FK detection: non-first columns matching another table's first (PK) column."""
    pk_owner: dict[str, str] = {}
    for m in metas:
        if m["columns"]:
            pk_owner.setdefault(m["columns"][0]["name"], m["name"])
    rels = []
    for m in metas:
        for c in m["columns"][1:]:
            owner = pk_owner.get(c["name"])
            if owner and owner != m["name"]:
                rels.append(f"- {m['name']}.{c['name']} → {owner}.{c['name']}")
    return rels


def build_instructions_from_uc(
    ws: WorkspaceClient,
    warehouse_id: str,
    table_full_names: list[str],
    company_description: str,
) -> str:
    """Build rich Genie instructions from live UC schemas + data profiling.

    Sections: description, data dictionary (real types/comments/values/ranges),
    relationships, date coverage, query tips. Capped at MAX_CHARS.
    """
    metas = [m for fq in table_full_names if (m := _get_table_meta(ws, fq))]
    if not metas:
        return company_description

    profiles = {m["name"]: _profile_table(ws, warehouse_id, m) for m in metas}

    lines: list[str] = [company_description.strip(), "", "## Data Dictionary"]
    date_coverage: list[str] = []
    query_tips: list[str] = []

    for m in metas:
        prof = profiles.get(m["name"], {})
        header = f"### Table: {m['name']}"
        if m["comment"]:
            header += f" — {m['comment']}"
        rc = prof.get("_row_count")
        if rc is not None:
            header += f" ({rc} rows)"
        lines += [header, "| Column | Type | Description |", "|---|---|---|"]

        for c in m["columns"]:
            desc_parts = [c["comment"]] if c["comment"] else []
            vals = prof.get("_values", {}).get(c["name"])
            if vals:
                desc_parts.append("Values: " + ", ".join(vals))
            mn, mx = prof.get(f"min__{c['name']}"), prof.get(f"max__{c['name']}")
            base = c["type"].split("(")[0]
            if mn is not None and mx is not None:
                if base in ("DATE", "TIMESTAMP", "TIMESTAMP_NTZ"):
                    date_coverage.append(f"- {m['name']}.{c['name']}: {mn} → {mx}")
                    desc_parts.append(f"Range: {mn} → {mx}")
                else:
                    desc_parts.append(f"Range: {mn} – {mx}")
            if base in _NUMERIC_TYPES and any(h in c["name"].lower() for h in _MONEY_HINTS):
                query_tips.append(f"- Monetary aggregation: SUM(`{c['name']}`) or AVG(`{c['name']}`) on {m['name']}")
            lines.append(f"| {c['name']} | {c['type']} | {'. '.join(desc_parts)} |")
        lines.append("")

    rels = _detect_relationships(metas)
    if rels:
        lines += ["## Relationships (join keys)"] + rels + [""]
    if date_coverage:
        lines += [
            "## Date Coverage (use these bounds — do NOT assume data extends to today)"
        ] + date_coverage + [""]

    lines.append("## Query Tips")
    seen: set[str] = set()
    for tip in query_tips:
        if tip not in seen:
            seen.add(tip)
            lines.append(tip)
    for m in metas:
        for c in m["columns"]:
            if c["type"].split("(")[0] in ("DATE", "TIMESTAMP", "TIMESTAMP_NTZ"):
                lines.append(f"- Time trends: GROUP BY DATE_TRUNC('MONTH', `{c['name']}`) on {m['name']}")
                break
    lines.append("- Prefer joining via the relationship keys listed above")

    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS - 20] + "\n…(truncated)"
    return text


INSTRUCTION_TITLE = "Data dictionary & query guidance (auto-generated)"


def apply_instructions_to_space(ws: WorkspaceClient, space_id: str, text: str) -> bool:
    """Write text instructions to a live Genie space.

    Uses the internal data-rooms API — the public `PATCH /genie/spaces/{id}`
    silently ignores `serialized_space.instructions` edits (verified 2026-06-11).
    Updates the existing TEXT_INSTRUCTION in place (preserving its id) or
    creates one if the space has none.

    Returns:
        True if the refetched content matches what was sent.
    """
    base = f"/api/2.0/data-rooms/{space_id}/instructions"
    body = {"title": INSTRUCTION_TITLE, "content": text, "instruction_type": "TEXT_INSTRUCTION"}
    try:
        instrs = ws.api_client.do("GET", base).get("instructions", [])
        existing = [i for i in instrs if i.get("instruction_type") == "TEXT_INSTRUCTION"]
        if existing:
            ws.api_client.do("POST", f"{base}/{existing[0]['instruction_id']}", body=body)
        else:
            ws.api_client.do("POST", base, body=body)
        after = ws.api_client.do("GET", base).get("instructions", [])
        got = next((i.get("content", "") for i in after if i.get("instruction_type") == "TEXT_INSTRUCTION"), "")
        return got.strip() == text.strip()
    except Exception as e:
        logger.warning("apply_instructions_to_space failed for %s: %s", space_id, str(e)[:200])
        return False


def enrich_space_instructions(
    ws: WorkspaceClient,
    warehouse_id: str,
    space_id: str,
    table_full_names: list[str],
    company_description: str,
) -> bool:
    """Build rich instructions from UC and apply them to the space (best-effort).

    Refuses to downgrade: skips the write when the generated text is thin
    (tables unreadable / no dictionary).
    """
    text = build_instructions_from_uc(ws, warehouse_id, table_full_names, company_description)
    if "## Data Dictionary" not in text or len(text) < 800:
        logger.warning("Skipping instruction enrich for %s — thin output (%d ch)", space_id, len(text))
        return False
    ok = apply_instructions_to_space(ws, space_id, text)
    logger.info("Instruction enrich for %s: %s (%d ch)", space_id, "OK" if ok else "FAILED", len(text))
    return ok
