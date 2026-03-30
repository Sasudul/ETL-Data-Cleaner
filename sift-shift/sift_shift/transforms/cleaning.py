"""
sift_shift/transforms/cleaning.py
Individual, composable transform functions.

Each function signature:
    fn(df: pd.DataFrame, **kwargs) -> tuple[pd.DataFrame, str]

The second return value is a human-readable notes string for the report.
"""

from __future__ import annotations

import re
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def strip_whitespace(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Strip leading/trailing whitespace from all string columns."""
    str_cols = df.select_dtypes(include="object").columns.tolist()
    for col in str_cols:
        df[col] = df[col].str.strip()
    return df, f"Stripped {len(str_cols)} string column(s)"


def standardise_column_names(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Lowercase column names and replace spaces / special chars with underscores."""
    original = list(df.columns)
    df.columns = [
        re.sub(r"[^\w]+", "_", col.strip().lower()).strip("_")
        for col in df.columns
    ]
    changed = sum(a != b for a, b in zip(original, df.columns))
    return df, f"Renamed {changed} column(s)"


def drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Remove completely duplicate rows."""
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    return df, f"Removed {removed:,} duplicate row(s)"


def handle_missing_values(
    df: pd.DataFrame,
    *,
    fill_value: Any = 0,
    drop_all_na: bool = True,
) -> tuple[pd.DataFrame, str]:
    """Fill numeric NaNs and optionally drop rows where all values are NaN."""
    before = len(df)
    notes_parts = []

    # Drop rows where every value is NaN
    if drop_all_na:
        df = df.dropna(how="all")
        dropped = before - len(df)
        if dropped:
            notes_parts.append(f"dropped {dropped:,} all-NaN rows")

    # Fill numeric columns
    num_cols = df.select_dtypes(include="number").columns.tolist()
    filled_count = int(df[num_cols].isna().sum().sum()) if num_cols else 0
    if num_cols:
        df[num_cols] = df[num_cols].fillna(fill_value)
    if filled_count:
        notes_parts.append(f"filled {filled_count:,} numeric NaN(s) with {fill_value!r}")

    # Fill string columns with empty string
    str_cols = df.select_dtypes(include="object").columns.tolist()
    str_filled = int(df[str_cols].isna().sum().sum()) if str_cols else 0
    if str_cols:
        df[str_cols] = df[str_cols].fillna("")
    if str_filled:
        notes_parts.append(f"filled {str_filled:,} string NaN(s) with ''")

    return df, "; ".join(notes_parts) or "No missing values found"


def normalise_dtypes(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Attempt to coerce object columns to numeric where possible."""
    converted = []
    for col in df.select_dtypes(include="object").columns:
        coerced = pd.to_numeric(df[col], errors="coerce")
        # Only convert if at least 80% of non-null values parse successfully
        valid_ratio = coerced.notna().sum() / max(df[col].notna().sum(), 1)
        if valid_ratio >= 0.8:
            df[col] = coerced
            converted.append(col)
    return df, f"Coerced {len(converted)} column(s) to numeric" if converted else "No dtype coercions"


def format_date_columns(
    df: pd.DataFrame,
    *,
    date_format: str = "%Y-%m-%d",
) -> tuple[pd.DataFrame, str]:
    """Detect and format columns whose name contains 'date' or 'time'."""
    date_cols = [
        col for col in df.columns
        if re.search(r"date|time|dt|timestamp", col, re.IGNORECASE)
        and df[col].dtype == object
    ]
    formatted = []
    for col in date_cols:
        try:
            parsed = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
            null_before = df[col].isna().sum()
            null_after = parsed.isna().sum()
            # Accept if we didn't massively increase nulls
            if null_after - null_before <= 0.05 * len(df):
                df[col] = parsed.dt.strftime(date_format)
                formatted.append(col)
        except Exception:
            logger.debug("Could not parse date column %r", col)

    return df, f"Formatted {len(formatted)} date column(s): {formatted}" if formatted else "No date columns detected"
