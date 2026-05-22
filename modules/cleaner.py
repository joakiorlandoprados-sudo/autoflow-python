"""Data cleaning utilities for AutoFlow Python."""

from __future__ import annotations

import pandas as pd

import config


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize a DataFrame according to project rules."""

    if df.empty:
        config.safe_print("📊 Cleaning summary: the input data is empty, nothing to clean.")
        return df.copy()

    cleaned_df = df.copy()
    initial_rows, initial_cols = cleaned_df.shape

    cleaned_df = cleaned_df.dropna(how="all")
    rows_after_empty_drop = len(cleaned_df)
    dropped_empty_rows = initial_rows - rows_after_empty_drop

    cleaned_df = cleaned_df.dropna(axis=1, how="all")
    dropped_empty_columns = initial_cols - cleaned_df.shape[1]

    stripped_columns = _strip_string_columns(cleaned_df)
    converted_date_columns = _convert_date_columns(cleaned_df)
    missing_value_summary = _handle_missing_numeric_values(cleaned_df)

    before_duplicates = len(cleaned_df)
    cleaned_df = cleaned_df.drop_duplicates().reset_index(drop=True)
    removed_duplicates = before_duplicates - len(cleaned_df)

    config.safe_print("📊 Cleaning summary")
    config.safe_print(f"✅ Empty rows removed: {dropped_empty_rows}")
    config.safe_print(f"✅ Empty columns removed: {dropped_empty_columns}")
    config.safe_print(f"✅ String columns normalized: {stripped_columns}")
    config.safe_print(
        "✅ Date columns converted: "
        + (", ".join(converted_date_columns) if converted_date_columns else "none")
    )
    config.safe_print(f"✅ Numeric missing values handled: {missing_value_summary}")
    config.safe_print(f"✅ Duplicate rows removed: {removed_duplicates}")
    config.safe_print(
        f"✅ Final shape: {cleaned_df.shape[0]} rows x {cleaned_df.shape[1]} columns"
    )

    return cleaned_df


def _strip_string_columns(df: pd.DataFrame) -> int:
    """Trim whitespace and normalize empty strings in object-like columns."""

    stripped_count = 0
    object_columns = df.select_dtypes(include=["object", "string", "category"]).columns

    for column in object_columns:
        original_series = df[column].copy()
        df[column] = df[column].apply(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        df[column] = df[column].replace("", pd.NA)
        if not original_series.equals(df[column]):
            stripped_count += 1

    return stripped_count


def _convert_date_columns(df: pd.DataFrame) -> list[str]:
    """Attempt to convert date-like columns using multiple formats."""

    converted_columns: list[str] = []

    for column in df.columns:
        series = df[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            converted_columns.append(column)
            continue

        if not pd.api.types.is_object_dtype(series) and not pd.api.types.is_string_dtype(series):
            continue

        parsed_series = _best_date_parse(series)
        if parsed_series is not None:
            df[column] = parsed_series
            converted_columns.append(column)

    return converted_columns


def _best_date_parse(series: pd.Series) -> pd.Series | None:
    """Return the best parsed datetime series when conversion confidence is high enough."""

    working_series = series.astype("string")
    non_null = working_series.dropna()
    if non_null.empty:
        return None

    best_match: pd.Series | None = None
    best_ratio = 0.0
    column_name = str(series.name or "").lower()
    has_date_hint = any(token in column_name for token in ("date", "time", "month", "day"))
    date_like_pattern = (
        r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}"
        r"(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?$"
    )
    date_like_ratio = (
        non_null.str.fullmatch(date_like_pattern, na=False).sum() / len(non_null)
    )

    for date_format in config.DATE_FORMAT_CANDIDATES:
        parsed = pd.to_datetime(working_series, format=date_format, errors="coerce")
        ratio = _success_ratio(parsed, working_series)
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = parsed

    if has_date_hint or date_like_ratio >= 0.6:
        generic_parsed = pd.to_datetime(working_series, errors="coerce", dayfirst=True)
        generic_ratio = _success_ratio(generic_parsed, working_series)
        if generic_ratio > best_ratio:
            best_ratio = generic_ratio
            best_match = generic_parsed

    threshold = 0.6 if has_date_hint else 0.85

    if best_match is not None and best_ratio >= threshold:
        return best_match
    return None


def _success_ratio(parsed: pd.Series, original: pd.Series) -> float:
    """Calculate how many non-null values were successfully parsed."""

    original_non_null = original.notna().sum()
    if original_non_null == 0:
        return 0.0
    parsed_non_null = parsed.notna().sum()
    return parsed_non_null / original_non_null


def _handle_missing_numeric_values(df: pd.DataFrame) -> str:
    """Apply the configured missing value strategy to numeric columns."""

    numeric_columns = list(df.select_dtypes(include=["number"]).columns)
    if not numeric_columns:
        return "no numeric columns found"

    strategy = config.MISSING_VALUE_STRATEGY
    if strategy not in {"fill_zero", "drop", "flag"}:
        raise ValueError(
            "Invalid MISSING_VALUE_STRATEGY in config.py. "
            "Choose from: fill_zero, drop, flag."
        )

    missing_counts = {
        column: int(df[column].isna().sum())
        for column in numeric_columns
        if int(df[column].isna().sum()) > 0
    }
    if not missing_counts:
        return "no missing numeric values detected"

    if strategy == "fill_zero":
        for column in missing_counts:
            df[column] = df[column].fillna(0)
        total_filled = sum(missing_counts.values())
        return f"filled {total_filled} missing values with zero"

    if strategy == "drop":
        before_rows = len(df)
        df.dropna(subset=list(missing_counts), inplace=True)
        df.reset_index(drop=True, inplace=True)
        removed_rows = before_rows - len(df)
        return f"dropped {removed_rows} rows containing missing numeric values"

    flagged_columns: list[str] = []
    for column in missing_counts:
        flag_column = f"{column}{config.MISSING_FLAG_SUFFIX}"
        df[flag_column] = df[column].isna()
        fill_value = _median_or_zero(df[column])
        df[column] = df[column].fillna(fill_value)
        flagged_columns.append(flag_column)

    total_flagged = sum(missing_counts.values())
    return (
        f"flagged {total_flagged} missing values across "
        f"{len(flagged_columns)} helper columns"
    )


def _median_or_zero(series: pd.Series) -> float:
    """Return the column median when available, otherwise zero."""

    median = series.median()
    if pd.isna(median):
        return 0.0
    return float(median)
