"""LLM-powered brand theme generator — turns a company name + description into a color palette."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a brand designer. Given a company name and description, generate a professional brand color palette.

RULES:
1. If the company is a real, well-known brand (e.g. Nike, Starbucks, Coca-Cola), use their ACTUAL brand colors.
2. For unknown companies, generate a professional palette that matches the vibe of the description.
3. Primary = the main brand color. Secondary = a complementary neutral or contrasting color. Accent = a highlight/CTA color.
4. Chart colors should be 5 harmonious colors derived from the brand palette, suitable for data visualization.
5. All colors must be valid hex codes (e.g. "#ff6900").
6. Ensure sufficient contrast — primary and accent should work as button backgrounds with white text.

OUTPUT FORMAT (strict JSON, no markdown fences):
{
  "primary": "#hex",
  "secondary": "#hex",
  "accent": "#hex",
  "chart_colors": ["#hex1", "#hex2", "#hex3", "#hex4", "#hex5"]
}
"""


def generate_theme(
    company_name: str,
    company_description: str,
    *,
    databricks_host: str,
    databricks_token: str,
    model: str = "opendoor-claude-opus-46",
) -> dict[str, Any]:
    """Call the LLM to generate a brand color palette.

    Args:
        company_name: Company name.
        company_description: Free-text description of the company.
        databricks_host: Databricks workspace ID for AI Gateway.
        databricks_token: Databricks PAT token.
        model: Model name on the AI Gateway.

    Returns:
        Dict with primary, secondary, accent (hex strings) and chart_colors (list of hex strings).
    """
    client = OpenAI(
        api_key=databricks_token,
        base_url=f"https://{databricks_host}.ai-gateway.cloud.databricks.com/mlflow/v1",
    )

    prompt = f"Company: {company_name}\nDescription: {company_description}"

    logger.info("Calling LLM to generate brand theme for %s...", company_name)
    resp = client.chat.completions.create(
        model=model,
        max_tokens=1024,
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
    # Extract JSON object
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        raw = raw[start:end]
    # Fix trailing commas
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    try:
        theme = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Theme JSON parse failed at position %d. Raw:\n%s", e.pos, raw)
        raise

    # Validate and provide defaults
    result = {
        "primary": theme.get("primary", "#1a73e8"),
        "secondary": theme.get("secondary", "#1a1a1a"),
        "accent": theme.get("accent", "#4285f4"),
        "chart_colors": theme.get("chart_colors", [])[:5],
    }

    # Pad chart_colors to 5 if needed
    while len(result["chart_colors"]) < 5:
        result["chart_colors"].append(result["primary"])

    logger.info(
        "Theme generated: primary=%s, secondary=%s, accent=%s, charts=%s",
        result["primary"],
        result["secondary"],
        result["accent"],
        result["chart_colors"],
    )
    return result
