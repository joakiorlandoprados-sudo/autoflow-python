"""Statistical summary generation for AutoFlow Python."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


def generate_stats(df: pd.DataFrame) -> dict[str, Any]:
    """Generate a structured statistics payload from a cleaned DataFrame."""

    numeric_columns = [
        column
        for column in df.select_dtypes(include=["number"]).columns
        if not pd.api.types.is_bool_dtype(df[column])
    ]
    categorical_columns = list(
        df.select_dtypes(include=["object", "string", "category", "bool"]).columns
    )
    date_columns = list(df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns)

    stats: dict[str, Any] = {
        "dataset": {
            "row_count": int(df.shape[0]),
            "column_count": int(df.shape[1]),
            "column_names": [str(column) for column in df.columns],
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "date_columns": date_columns,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "numeric": {},
        "categorical": {},
        "time_trend": None,
    }

    for column in numeric_columns:
        series = df[column].dropna()
        if series.empty:
            continue
        stats["numeric"][column] = {
            "min": _to_python_value(series.min()),
            "max": _to_python_value(series.max()),
            "mean": _to_python_value(round(float(series.mean()), 2)),
            "median": _to_python_value(round(float(series.median()), 2)),
            "std": _to_python_value(round(float(series.std(ddof=1)), 2))
            if len(series) > 1
            else 0.0,
            "total": _to_python_value(round(float(series.sum()), 2)),
            "missing": int(df[column].isna().sum()),
        }

    for column in categorical_columns:
        counts = df[column].fillna("Missing").astype(str).value_counts()
        top_values = [
            {"value": index, "count": int(value)}
            for index, value in counts.head(5).items()
        ]
        stats["categorical"][column] = {
            "unique_values": int(counts.size),
            "top_values": top_values,
        }

    stats["time_trend"] = _generate_time_trend(df, numeric_columns, date_columns)
    return stats


def _generate_time_trend(
    df: pd.DataFrame, numeric_columns: list[str], date_columns: list[str]
) -> dict[str, Any] | None:
    """Build a time trend summary when a date column is available."""

    if not date_columns:
        return None

    date_column = date_columns[0]
    trend_df = df.dropna(subset=[date_column]).copy()
    if trend_df.empty:
        return None

    metric_column = _pick_metric_column(numeric_columns)
    span_days = (trend_df[date_column].max() - trend_df[date_column].min()).days
    frequency = "MS" if span_days > 45 else "D"
    label_format = "%Y-%m" if frequency == "MS" else "%Y-%m-%d"

    if metric_column:
        grouped = (
            trend_df.groupby(pd.Grouper(key=date_column, freq=frequency))[metric_column]
            .sum()
            .dropna()
        )
        points = [
            {
                "period": period.strftime(label_format),
                "value": _to_python_value(round(float(value), 2)),
            }
            for period, value in grouped.items()
        ]
        peak = grouped.idxmax() if not grouped.empty else None
        lowest = grouped.idxmin() if not grouped.empty else None
        summary = (
            f"Tracked {metric_column} across {len(points)} periods from "
            f"{trend_df[date_column].min().date()} to {trend_df[date_column].max().date()}."
        )
        if peak is not None and lowest is not None:
            summary += (
                f" Peak period: {peak.strftime(label_format)}. "
                f"Lowest period: {lowest.strftime(label_format)}."
            )
        return {
            "date_column": date_column,
            "metric_column": metric_column,
            "granularity": "month" if frequency == "MS" else "day",
            "start_date": trend_df[date_column].min().date().isoformat(),
            "end_date": trend_df[date_column].max().date().isoformat(),
            "points": points,
            "summary": summary,
        }

    grouped_counts = trend_df.groupby(pd.Grouper(key=date_column, freq=frequency)).size()
    points = [
        {"period": period.strftime(label_format), "value": int(value)}
        for period, value in grouped_counts.items()
    ]
    return {
        "date_column": date_column,
        "metric_column": None,
        "granularity": "month" if frequency == "MS" else "day",
        "start_date": trend_df[date_column].min().date().isoformat(),
        "end_date": trend_df[date_column].max().date().isoformat(),
        "points": points,
        "summary": f"Tracked record volume across {len(points)} periods.",
    }


def _pick_metric_column(numeric_columns: list[str]) -> str | None:
    """Choose the most relevant numeric column for trend analysis."""

    if not numeric_columns:
        return None

    priority_keywords = (
        "net_revenue",
        "total_revenue",
        "revenue",
        "sales",
        "amount",
        "units_sold",
    )
    for keyword in priority_keywords:
        for column in numeric_columns:
            if keyword in column.lower():
                return column
    return numeric_columns[0]


def _to_python_value(value: Any) -> Any:
    """Convert pandas and NumPy scalar values into JSON-friendly Python types."""

    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except ValueError:
            pass
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value
