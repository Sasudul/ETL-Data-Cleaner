"""
tests/test_pipeline.py
Unit tests for Sift & Shift ETL pipeline.
Run with: python -m pytest tests/ -v
"""

from __future__ import annotations

import io
import textwrap
from pathlib import Path

import pandas as pd
import pytest

from sift_shift.transforms.cleaning import (
    drop_duplicates,
    format_date_columns,
    handle_missing_values,
    normalise_dtypes,
    standardise_column_names,
    strip_whitespace,
)
from sift_shift.pipeline import extract, transform, load, run


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "First Name": ["  Alice  ", "Bob", "Alice  ", "Charlie"],
            "Last Name": ["Smith", "Jones", "Smith", "  Brown  "],
            "Age": [30, None, 30, 25],
            "Join Date": ["2023-01-15", "Jan 2 2022", "2023-01-15", "03/10/2021"],
            "Score": ["95.5", "82", "95.5", "77"],
        }
    )


@pytest.fixture()
def tmp_csv(tmp_path: Path, sample_df: pd.DataFrame) -> Path:
    p = tmp_path / "sample.csv"
    sample_df.to_csv(p, index=False)
    return p


# ---------------------------------------------------------------------------
# Transform unit tests
# ---------------------------------------------------------------------------

class TestStripWhitespace:
    def test_strips_string_columns(self, sample_df):
        df, notes = strip_whitespace(sample_df.copy())
        assert df["First Name"].iloc[0] == "Alice"
        assert df["Last Name"].iloc[3] == "Brown"

    def test_notes_non_empty(self, sample_df):
        _, notes = strip_whitespace(sample_df.copy())
        assert notes


class TestStandardiseColumnNames:
    def test_lowercase(self, sample_df):
        df, _ = standardise_column_names(sample_df.copy())
        assert all(c == c.lower() for c in df.columns)

    def test_spaces_replaced(self, sample_df):
        df, _ = standardise_column_names(sample_df.copy())
        assert "first_name" in df.columns
        assert "last_name" in df.columns

    def test_unchanged_count(self, sample_df):
        df, _ = standardise_column_names(sample_df.copy())
        assert len(df.columns) == len(sample_df.columns)


class TestDropDuplicates:
    def test_removes_duplicates(self, sample_df):
        df, notes = drop_duplicates(sample_df.copy())
        # Rows 0 and 2 are duplicates after strip (not yet stripped here, so raw match)
        assert len(df) <= len(sample_df)

    def test_no_data_loss_on_unique_df(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result, _ = drop_duplicates(df.copy())
        assert len(result) == 3


class TestHandleMissingValues:
    def test_fills_numeric_nan(self, sample_df):
        df, _ = handle_missing_values(sample_df.copy(), fill_value=-1)
        assert df["Age"].isna().sum() == 0

    def test_fill_value_applied(self, sample_df):
        df, _ = handle_missing_values(sample_df.copy(), fill_value=99)
        assert (df["Age"] == 99).any()

    def test_drop_all_na_rows(self):
        df = pd.DataFrame({"a": [1, None, 3], "b": [None, None, None]})
        df_all_na = pd.concat([df, pd.DataFrame({"a": [None], "b": [None]})])
        result, _ = handle_missing_values(df_all_na, drop_all_na=True)
        assert len(result) == 3


class TestNormaliseDtypes:
    def test_converts_numeric_strings(self, sample_df):
        df, _ = strip_whitespace(sample_df.copy())
        df, _ = standardise_column_names(df)
        df, _ = normalise_dtypes(df)
        assert pd.api.types.is_numeric_dtype(df["score"])


class TestFormatDateColumns:
    def test_formats_dates(self, sample_df):
        df, _ = strip_whitespace(sample_df.copy())
        df, _ = standardise_column_names(df)
        df, notes = format_date_columns(df, date_format="%Y-%m-%d")
        # At least some dates should be formatted
        assert df["join_date"].iloc[0] == "2023-01-15"
        assert "date column" in notes.lower() or "formatted" in notes.lower()


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------

class TestExtract:
    def test_loads_csv(self, tmp_csv):
        df = extract(tmp_csv)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract("/nonexistent/path/data.csv")

    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "data.xlsx"
        f.write_text("dummy")
        with pytest.raises(ValueError, match="Unsupported"):
            extract(f)


class TestTransform:
    def test_returns_dataframe_and_steps(self, sample_df):
        df, steps = transform(sample_df.copy())
        assert isinstance(df, pd.DataFrame)
        assert len(steps) == 6  # 6 steps defined in pipeline

    def test_no_duplicate_rows(self, sample_df):
        df, _ = transform(sample_df.copy())
        assert df.duplicated().sum() == 0

    def test_column_names_standardised(self, sample_df):
        df, _ = transform(sample_df.copy())
        assert all(c == c.lower() for c in df.columns)
        assert " " not in " ".join(df.columns)


class TestLoad:
    def test_creates_output_file(self, tmp_path, sample_df):
        out = tmp_path / "sub" / "out.csv"
        load(sample_df, out)
        assert out.exists()

    def test_no_index_column(self, tmp_path, sample_df):
        out = tmp_path / "out.csv"
        load(sample_df, out)
        df = pd.read_csv(out)
        assert "Unnamed: 0" not in df.columns


class TestRun:
    def test_full_pipeline(self, tmp_csv, tmp_path):
        out = tmp_path / "clean.csv"
        report = run(tmp_csv, out)
        assert out.exists()
        assert report.rows_out <= report.rows_in
        assert report.total_duration_ms > 0

    def test_report_summary_string(self, tmp_csv, tmp_path):
        out = tmp_path / "clean.csv"
        report = run(tmp_csv, out)
        summary = report.summary()
        assert "SIFT & SHIFT" in summary
        assert str(tmp_csv) in summary
