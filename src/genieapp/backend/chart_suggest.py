"""Heuristic chart suggestion engine.

Examines column types/names from query results to suggest the best chart type.
"""

from __future__ import annotations

from .models import ChartSuggestion


# Column name patterns for type detection
DATE_PATTERNS = {"date", "time", "month", "year", "quarter", "week", "day", "period"}
NUMERIC_PATTERNS = {
    "count", "sum", "avg", "total", "amount", "price", "revenue", "cost",
    "profit", "quantity", "sales", "margin", "rate", "percent", "value",
    "weight", "score", "rating", "balance", "fee", "tax", "discount",
    "num", "number",
}
CATEGORY_PATTERNS = {
    "name", "category", "type", "tier", "status", "region", "industry",
    "segment", "group", "department", "brand", "model", "product", "channel",
    "country", "city", "state", "size", "color", "level", "class", "label",
}
ID_SUFFIXES = {"_id", "_key", "_pk", "_fk", "_code"}
GEO_LAT_PATTERNS = {"lat", "latitude"}
GEO_LON_PATTERNS = {"lon", "lng", "longitude"}


def _is_id_column(name: str) -> bool:
    """Check if column is an identifier (not a metric)."""
    lower = name.lower().strip()
    if lower == "id":
        return True
    return any(lower.endswith(s) for s in ID_SUFFIXES)


def _is_date_column(name: str) -> bool:
    """Check if column name suggests a date/time type."""
    lower = name.lower()
    return any(p in lower for p in DATE_PATTERNS)


def _is_named_numeric(name: str) -> bool:
    """Check if column name matches known numeric/metric patterns."""
    lower = name.lower()
    return any(p in lower for p in NUMERIC_PATTERNS)


def _is_numeric_by_values(sample_values: list) -> bool:
    """Check if majority of non-null sample values are numeric."""
    non_null = [v for v in sample_values[:10] if v is not None and str(v).strip() != ""]
    if not non_null:
        return False
    numeric_count = 0
    for val in non_null:
        try:
            float(str(val))
            numeric_count += 1
        except (ValueError, TypeError):
            pass
    return numeric_count > len(non_null) / 2


def _is_category_column(name: str) -> bool:
    """Check if column name suggests a categorical type."""
    lower = name.lower()
    return any(p in lower for p in CATEGORY_PATTERNS)


def _find_geo_columns(columns: list[str]) -> tuple[str | None, str | None]:
    """Find latitude and longitude columns by name."""
    lat_col = lon_col = None
    for c in columns:
        lower = c.lower().strip()
        if lower in GEO_LAT_PATTERNS:
            lat_col = c
        elif lower in GEO_LON_PATTERNS:
            lon_col = c
    return lat_col, lon_col


def _pick_best_metric(metric_cols: list[str]) -> str:
    """Pick the best metric column, preferring named metrics over value-detected ones."""
    # Prefer columns with explicit metric names
    for c in metric_cols:
        if _is_named_numeric(c):
            return c
    return metric_cols[0]


def _pick_best_category(category_cols: list[str], columns: list[str]) -> str:
    """Pick the best category column for x-axis."""
    # Prefer columns with explicit category names
    for c in category_cols:
        if _is_category_column(c):
            return c
    return category_cols[0]


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

    # --- Classify columns ---
    sample_vals = {c: [row.get(c) for row in data[:10]] for c in columns}

    id_cols: list[str] = []
    date_cols: list[str] = []
    metric_cols: list[str] = []  # Numeric columns that are actual metrics (not IDs)
    category_cols: list[str] = []

    for c in columns:
        if _is_id_column(c):
            id_cols.append(c)
        elif _is_date_column(c):
            date_cols.append(c)
        elif _is_named_numeric(c):
            metric_cols.append(c)
        elif _is_category_column(c):
            category_cols.append(c)
        elif _is_numeric_by_values(sample_vals.get(c, [])):
            # Numeric by value but not by name — could be a metric or a miscellaneous number
            metric_cols.append(c)
        else:
            # Non-numeric, non-date, non-ID — treat as category
            category_cols.append(c)

    row_count = len(data)

    # --- KPI: single value result ---
    # 1 column + 1 row
    if len(columns) == 1 and row_count == 1:
        return ChartSuggestion(
            chart_type="kpi",
            y_axis=columns[0],
            title=columns[0].replace("_", " ").title(),
        )

    # 1 row with metric column(s) — show the primary metric as KPI
    if row_count == 1 and metric_cols:
        best = _pick_best_metric(metric_cols)
        label_parts = []
        # If there's a category column, use it as context in the title
        if category_cols:
            label_val = data[0].get(category_cols[0], "")
            if label_val:
                label_parts.append(str(label_val))
        label_parts.append(best.replace("_", " ").title())
        return ChartSuggestion(
            chart_type="kpi",
            y_axis=best,
            title=" — ".join(label_parts),
        )

    # --- Geo → map ---
    lat_col, lon_col = _find_geo_columns(columns)
    if lat_col and lon_col:
        label_col = None
        for c in columns:
            if c not in (lat_col, lon_col) and c not in id_cols and c not in metric_cols:
                label_col = c
                break
        return ChartSuggestion(
            chart_type="map",
            x_axis=lon_col,
            y_axis=lat_col,
            title=label_col or "Locations",
        )

    # --- Time series: date + metric → line ---
    if date_cols and metric_cols:
        best_metric = _pick_best_metric(metric_cols)
        return ChartSuggestion(
            chart_type="line",
            x_axis=date_cols[0],
            y_axis=best_metric,
            title=f"{best_metric.replace('_', ' ').title()} Over Time",
        )

    # --- Category + metric ---
    if category_cols and metric_cols:
        best_cat = _pick_best_category(category_cols, columns)
        best_metric = _pick_best_metric(metric_cols)

        # Few rows → pie
        if 2 <= row_count <= 7:
            return ChartSuggestion(
                chart_type="pie",
                x_axis=best_cat,
                y_axis=best_metric,
                title=f"{best_metric.replace('_', ' ').title()} by {best_cat.replace('_', ' ').title()}",
            )

        # Many rows → bar
        return ChartSuggestion(
            chart_type="bar",
            x_axis=best_cat,
            y_axis=best_metric,
            title=f"{best_metric.replace('_', ' ').title()} by {best_cat.replace('_', ' ').title()}",
        )

    # --- Multiple metrics, no category → bar using first non-ID column as x ---
    if len(metric_cols) >= 2:
        # Find a reasonable x-axis (first non-metric, non-ID column)
        x_candidates = [c for c in columns if c not in metric_cols and c not in id_cols]
        x = x_candidates[0] if x_candidates else columns[0]
        best_metric = _pick_best_metric(metric_cols)
        return ChartSuggestion(
            chart_type="bar",
            x_axis=x,
            y_axis=best_metric,
            title=best_metric.replace("_", " ").title(),
        )

    # --- Default → table ---
    return ChartSuggestion(chart_type="table", title="Query Results")
