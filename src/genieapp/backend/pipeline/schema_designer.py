"""LLM-powered schema designer — turns a company description into a table schema."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a data architect. Given a company description, design a realistic database schema.
Output ONLY valid JSON, no markdown fences.

RULES:
1. Create 3-5 tables representing the company's core business entities and transactions.
2. Each table should have 5-12 columns with realistic names.
3. Every table MUST have a primary key column as the first column (integer, sequential).
4. Use foreign keys to create relationships between tables. Specify "references": "table_name.column_name".
5. Include at least one date column and one numeric/financial column per table.
6. Column names should be snake_case, table names snake_case plural (e.g., "orders", "customers").
7. Add meaningful table comments and column comments — these are passed to the AI query engine.
8. Include sample_questions (5-7) that a business user would ask. Questions MUST reference actual column names.
9. Tables must be ordered so referenced tables come BEFORE tables that reference them.
10. Dimension/lookup tables: 20-50 rows. Fact/transaction tables: 100-150 rows. Keep row counts manageable.

AVAILABLE SQL TYPES:
- STRING — text, names, categories, addresses, emails, etc.
- INT — integers, counts, IDs
- DOUBLE — decimal numbers, prices, amounts, percentages
- DATE — dates in YYYY-MM-DD format
- BOOLEAN — true/false
- BIGINT — large integers

OUTPUT FORMAT (strict JSON):
{
  "tables": [
    {
      "name": "table_name",
      "comment": "What this table represents",
      "row_count": 100,
      "columns": [
        {
          "name": "column_name",
          "type": "STRING",
          "comment": "What this column represents",
          "primary_key": true,
          "references": ""
        }
      ]
    }
  ],
  "sample_questions": [
    "What is the total revenue by region?",
    "Which product has the highest sales volume?"
  ]
}

COLUMN DEFINITION FIELDS:
- "name": snake_case column name
- "type": one of STRING, INT, DOUBLE, DATE, BOOLEAN, BIGINT
- "comment": describes what this column stores (CRITICAL for the AI query engine)
- "primary_key": true only for the first column (the ID column)
- "references": "parent_table.parent_column" for foreign keys, empty string otherwise
"""


def design_schema(
    company_description: str,
    *,
    databricks_host: str,
    databricks_token: str,
    must_answer_questions: list[str] | None = None,
    model: str = "opendoor-claude-opus-46",
) -> dict[str, Any]:
    """Call the LLM to design a database schema based on the company description.

    Args:
        company_description: Free-text description of the company and their data.
        databricks_host: Databricks workspace ID for AI Gateway.
        databricks_token: Databricks PAT token.
        must_answer_questions: Optional list of questions the schema must support.
        model: Model name on the AI Gateway.

    Returns:
        Parsed schema dict with "tables" and "sample_questions".
    """
    client = OpenAI(
        api_key=databricks_token,
        base_url=f"https://{databricks_host}.ai-gateway.cloud.databricks.com/mlflow/v1",
    )

    # Build user prompt with optional must-answer questions
    user_prompt = company_description
    if must_answer_questions:
        questions_text = "\n".join(f"- {q}" for q in must_answer_questions)
        user_prompt += f"\n\nMUST-ANSWER QUESTIONS (the schema MUST support answering all of these via SQL):\n{questions_text}"

    logger.info("Calling LLM to design schema...")
    resp = client.chat.completions.create(
        model=model,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        raw = raw[start:end]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    try:
        schema = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed at position %d. Raw output:\n%s", e.pos, raw)
        raise
    logger.info(
        "Schema designed: %d tables, %d sample questions",
        len(schema.get("tables", [])),
        len(schema.get("sample_questions", [])),
    )
    return schema
