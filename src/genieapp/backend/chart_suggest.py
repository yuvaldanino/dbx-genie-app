"""Heuristic chart suggestion engine.

Examines column types/names from query results to suggest the best chart type.
"""

from __future__ import annotations

from .models import ChartSuggestion


# Column name patterns for type detection
DATE_PATTERNS = {"date", "time", "month", "year", "quarter", "week", "day", "period"}
NUMERIC_PATTERNS = {"count", "sum", "avg", "total", "amount", "price", "revenue", "cost", "profit", "quantity", "sales", "margin", "rate", "percent", "value"}
CATEGORY_PATTERNS = {"name", "category", "type", "tier", "status", "region", "industry", "segment", "group", "department"}


def _is_date_column(name: str) -> bool:
    """Check if column name suggests a date/time type."""
    lower = name.lower()
    return any(p in lower for p in DATE_PATTERNS)


def _is_numeric_column(name: str, sample_values: list) -> bool:
    """Check if column appears numeric based on name and sample values."""
    lower = name.lower()
    if any(p in lower for p in NUMERIC_PATTERNS):
        return True
    # Check sample values
    for val in sample_values[:5]:
        if val is None:
            continue
        try:
            float(str(val))
            return True
        except (ValueError, TypeError):
            return False
    return False


def _is_category_column(name: str) -> bool:
    """Check if column name suggests a categorical type."""
    lower = name.lower()
    return any(p in lower for p in CATEGORY_PATTERNS)


def suggest_chart(columns: list[str], data: list[dict]) -> ChartSuggestion | None:
    """Suggest a chart type based on column names and data.

    Args:
        columns: List of column names from query result.
        data: List of row dicts from query result.

    Returns:
        ChartSuggestion or None if no chart is appropriate.
    """
    if not columns or not data:
        return None

    # Single value → KPI
    if len(columns) == 1 and len(data) == 1:
        return ChartSuggestion(
            chart_type="kpi",
            y_axis=columns[0],
            title=columns[0].replace("_", " ").title(),
        )

    # Classify columns
    date_cols = [c for c in columns if _is_date_column(c)]
    sample_vals = {c: [row.get(c) for row in data[:10]] for c in columns}
    numeric_cols = [c for c in columns if _is_numeric_column(c, sample_vals.get(c, []))]
    category_cols = [c for c in columns if _is_category_column(c)]

    # Remaining non-numeric columns as potential categories
    non_numeric = [c for c in columns if c not in numeric_cols]
    if not category_cols and non_numeric:
        category_cols = non_numeric

    unique_count = len(data)

    # Date + numeric → line chart
    if date_cols and numeric_cols:
        return ChartSuggestion(
            chart_type="line",
            x_axis=date_cols[0],
            y_axis=numeric_cols[0],
            title=f"{numeric_cols[0].replace('_', ' ').title()} Over Time",
        )

    # Category + numeric with few categories → pie
    if category_cols and numeric_cols and unique_count <= 7:
        return ChartSuggestion(
            chart_type="pie",
            x_axis=category_cols[0],
            y_axis=numeric_cols[0],
            title=f"{numeric_cols[0].replace('_', ' ').title()} by {category_cols[0].replace('_', ' ').title()}",
        )

    # Category + numeric → bar chart
    if category_cols and numeric_cols:
        return ChartSuggestion(
            chart_type="bar",
            x_axis=category_cols[0],
            y_axis=numeric_cols[0],
            title=f"{numeric_cols[0].replace('_', ' ').title()} by {category_cols[0].replace('_', ' ').title()}",
        )

    # Two numeric columns → bar
    if len(numeric_cols) >= 2:
        return ChartSuggestion(
            chart_type="bar",
            x_axis=columns[0],
            y_axis=numeric_cols[0],
            title=f"{numeric_cols[0].replace('_', ' ').title()}",
        )

    # Default → table
    return ChartSuggestion(chart_type="table", title="Query Results")
