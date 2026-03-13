"""LLM-powered schema designer — turns a company description into a Faker-ready schema."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

# Faker providers we support and their SQL type mappings.
# The LLM prompt references this list so it only picks valid providers.
SUPPORTED_PROVIDERS = """
AVAILABLE FAKER PROVIDERS (use exactly these names in the "faker" field):

Identity / IDs:
  - "sequential_id"          → auto-increment integer (1, 2, 3, ...). SQL type: INT.

People:
  - "name"                   → full name. SQL type: STRING.
  - "first_name"             → first name only. SQL type: STRING.
  - "last_name"              → last name only. SQL type: STRING.
  - "email"                  → email address. SQL type: STRING.
  - "phone_number"           → phone number. SQL type: STRING.
  - "job"                    → job title. SQL type: STRING.

Companies:
  - "company"                → company name. SQL type: STRING.
  - "catch_phrase"           → marketing phrase. SQL type: STRING.
  - "bs"                     → business buzzword phrase. SQL type: STRING.

Locations:
  - "address"                → full street address. SQL type: STRING.
  - "city"                   → city name. SQL type: STRING.
  - "state"                  → state/province. SQL type: STRING.
  - "country"                → country name. SQL type: STRING.
  - "zipcode"                → postal code. SQL type: STRING.
  - "latitude"               → latitude float. SQL type: DOUBLE.
  - "longitude"              → longitude float. SQL type: DOUBLE.

Dates:
  - "date_between"           → random date. Requires "args": {"start_date": "-2y", "end_date": "today"}. SQL type: DATE.
  - "date_this_year"         → date in current year. SQL type: DATE.

Numbers:
  - "random_int"             → random integer. Requires "args": {"min": 1, "max": 100}. SQL type: INT.
  - "pyfloat"                → random float. Requires "args": {"min_value": 0, "max_value": 1000, "right_digits": 2}. SQL type: DOUBLE.

Categorical:
  - "random_element"         → pick from a list. Requires "args": {"elements": ["A", "B", "C"]}. SQL type: STRING.

Boolean:
  - "boolean"                → true/false. Optional "args": {"chance_of_getting_true": 75}. SQL type: BOOLEAN.

Text:
  - "text"                   → paragraph of text. Optional "args": {"max_nb_chars": 200}. SQL type: STRING.
  - "sentence"               → single sentence. SQL type: STRING.

Other:
  - "uuid4"                  → UUID string. SQL type: STRING.
  - "url"                    → URL. SQL type: STRING.
  - "currency_code"          → 3-letter currency code. SQL type: STRING.

Foreign Keys:
  - "fk"                     → references another table's ID. Requires "args": {"references": "table_name.column_name"}. SQL type: INT.
                                Values will be randomly sampled from the referenced table's generated IDs.
"""

SYSTEM_PROMPT = f"""You are a data architect. Given a company description, design a realistic database schema
that would represent their core business data. Output ONLY valid JSON, no markdown fences.

RULES:
1. Create 3-5 tables that represent the company's core business entities and transactions.
2. Each table should have 5-12 columns with realistic names and types.
3. Every table MUST have a primary key column as the first column, using "sequential_id" faker provider.
4. Use foreign keys ("fk" provider) to create relationships between tables.
5. Include at least one date column and one numeric/financial column per table.
6. Use "random_element" for categorical columns with domain-specific values (5-10 realistic options).
7. Make column names snake_case and table names snake_case plural (e.g., "shipments", "warehouses").
8. Add meaningful table comments and column comments that describe what each represents.
9. Include sample_questions (5-7) that a business user would ask about this data.
10. Tables should be ordered so that referenced tables come before tables that reference them.

{SUPPORTED_PROVIDERS}

OUTPUT FORMAT (strict JSON):
{{
  "tables": [
    {{
      "name": "table_name",
      "comment": "Description of what this table represents",
      "row_count": 1000,
      "columns": [
        {{
          "name": "column_name",
          "faker": "provider_name",
          "args": {{}},
          "comment": "What this column represents"
        }}
      ]
    }}
  ],
  "sample_questions": [
    "What were total sales last quarter?",
    "..."
  ]
}}
"""


def design_schema(
    company_description: str,
    *,
    databricks_host: str,
    databricks_token: str,
    model: str = "opendoor-claude-opus-46",
) -> dict[str, Any]:
    """Call the LLM to design a database schema based on the company description.

    Args:
        company_description: Free-text description of the company and their data.
        databricks_host: Databricks workspace ID for AI Gateway.
        databricks_token: Databricks PAT token.
        model: Model name on the AI Gateway.

    Returns:
        Parsed schema dict with "tables" and "sample_questions".
    """
    client = OpenAI(
        api_key=databricks_token,
        base_url=f"https://{databricks_host}.ai-gateway.cloud.databricks.com/mlflow/v1",
    )

    logger.info("Calling LLM to design schema...")
    resp = client.chat.completions.create(
        model=model,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": company_description},
        ],
    )

    raw = resp.choices[0].message.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    # Extract JSON object if there's surrounding text
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        raw = raw[start:end]
    # Fix trailing commas (common LLM issue)
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
