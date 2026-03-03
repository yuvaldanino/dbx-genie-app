"""Heuristic chart suggestion engine.

Examines column types/names from query results to suggest the best chart type.
"""

from __future__ import annotations

from .models import ChartSuggestion


# Column name patterns for type detection
DATE_PATTERNS = {"date", "time", "month", "year", "quarter", "week", "day", "period"}
NUMERIC_PATTERNS = {"count", "sum", "avg", "total", "amount", "price", "revenue", "cost", "profit", "quantity", "sales", "margin", "rate", "percent", "value"}
CATEGORY_PATTERNS = {"name", "category", "type", "tier", "status", "region", "industry", "segment", "group", "department"}
GEO_LAT_PATTERNS = {"lat", "latitude"}
GEO_LON_PATTERNS = {"lon", "lng", "longitude"}


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


def _find_geo_columns(columns: list[str]) -> tuple[str | None, str | None]:
    """Find latitude and longitude columns by name. Returns (lat_col, lon_col)."""
    lat_col = lon_col = None
    for c in columns:
        lower = c.lower().strip()
        if lower in GEO_LAT_PATTERNS:
            lat_col = c
        elif lower in GEO_LON_PATTERNS:
            lon_col = c
    return lat_col, lon_col


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

    # Geo columns → map
    lat_col, lon_col = _find_geo_columns(columns)
    if lat_col and lon_col:
        # Find a label column (name, company, etc.) for popups
        label_col = None
        for c in columns:
            if c not in (lat_col, lon_col) and not _is_numeric_column(c, []):
                label_col = c
                break
        return ChartSuggestion(
            chart_type="map",
            x_axis=lon_col,
            y_axis=lat_col,
            title=label_col or "Locations",
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
