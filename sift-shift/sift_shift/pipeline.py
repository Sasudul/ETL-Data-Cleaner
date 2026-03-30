"""
sift_shift/pipeline.py
Core ETL pipeline: Extract → Transform → Load
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .transforms import (
    drop_duplicates,
    handle_missing_values,
    standardise_column_names,
    format_date_columns,
    strip_whitespace,
    normalise_dtypes,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result / Report dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    name: str
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    duration_ms: float
    notes: str = ""

    @property
    def rows_removed(self) -> int:
        return self.rows_before - self.rows_after

    @property
    def cols_changed(self) -> int:
        return abs(self.columns_before - self.columns_after)


@dataclass
class PipelineReport:
    input_path: Path
    output_path: Path
    rows_in: int
    rows_out: int
    cols_in: int
    cols_out: int
    total_duration_ms: float
    steps: list[StepResult] = field(default_factory=list)

    @property
    def rows_removed(self) -> int:
        return self.rows_in - self.rows_out

    @property
    def reduction_pct(self) -> float:
        if self.rows_in == 0:
            return 0.0
        return round((self.rows_removed / self.rows_in) * 100, 2)

    def summary(self) -> str:
        lines = [
            "",
            "╔══════════════════════════════════════════════════════════╗",
            "║              SIFT & SHIFT — PIPELINE REPORT              ║",
            "╠══════════════════════════════════════════════════════════╣",
            f"║  Input  : {str(self.input_path):<47} ║",
            f"║  Output : {str(self.output_path):<47} ║",
            "╠══════════════════════════════════════════════════════════╣",
            f"║  Rows   : {self.rows_in:>6,} in  →  {self.rows_out:>6,} out   "
            f"({self.rows_removed:>5,} removed, {self.reduction_pct:>5.1f}%)  ║",
            f"║  Cols   : {self.cols_in:>6} in  →  {self.cols_out:>6} out"
            f"{'':>29}║",
            f"║  Time   : {self.total_duration_ms:>8.1f} ms total"
            f"{'':>34}║",
            "╠══════════════════════════════════════════════════════════╣",
            "║  TRANSFORM STEPS                                         ║",
        ]
        for i, s in enumerate(self.steps, 1):
            status = "✓" if s.rows_after <= s.rows_before else "↑"
            lines.append(
                f"║  {i}. {s.name:<30}  {status}  {s.duration_ms:>6.1f} ms  ║"
            )
            if s.rows_removed:
                lines.append(f"║     └─ removed {s.rows_removed:,} rows{'':<36}║")
            if s.notes:
                lines.append(f"║     └─ {s.notes[:52]:<52}║")
        lines += [
            "╚══════════════════════════════════════════════════════════╝",
            "",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------

def extract(filepath: str | Path, **read_kwargs: Any) -> pd.DataFrame:
    """Read a CSV file and return a DataFrame.

    Parameters
    ----------
    filepath:
        Path to the input CSV file.
    **read_kwargs:
        Extra keyword arguments forwarded to ``pandas.read_csv()``.

    Returns
    -------
    pd.DataFrame
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.suffix.lower() not in {".csv", ".tsv", ".txt"}:
        raise ValueError(f"Unsupported file type: {path.suffix!r}. Expected .csv / .tsv / .txt")

    logger.info("[EXTRACT] Reading: %s", path)
    df = pd.read_csv(path, **read_kwargs)
    logger.info("[EXTRACT] Loaded %s rows × %s columns", f"{len(df):,}", len(df.columns))
    return df


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

def transform(
    df: pd.DataFrame,
    *,
    fill_value: int | float | str = 0,
    drop_all_na: bool = True,
    date_format: str = "%Y-%m-%d",
) -> tuple[pd.DataFrame, list[StepResult]]:
    """Apply the full cleaning pipeline to a DataFrame.

    Steps
    -----
    1. Strip whitespace from string columns.
    2. Standardise column names.
    3. Drop duplicate rows.
    4. Handle missing values.
    5. Normalise dtypes (numeric coercion).
    6. Format date columns.

    Returns
    -------
    Cleaned DataFrame + list of StepResult records.
    """
    steps: list[StepResult] = []

    def _run(name: str, fn, *args, **kwargs) -> pd.DataFrame:
        nonlocal df
        r0, c0 = len(df), len(df.columns)
        t0 = time.perf_counter()
        df, notes = fn(df, *args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1_000
        result = StepResult(
            name=name,
            rows_before=r0,
            rows_after=len(df),
            columns_before=c0,
            columns_after=len(df.columns),
            duration_ms=elapsed,
            notes=notes,
        )
        steps.append(result)
        logger.info("[TRANSFORM] %-35s  rows: %s → %s", name, f"{r0:,}", f"{len(df):,}")
        if notes:
            logger.debug("[TRANSFORM]   ↳ %s", notes)
        return df

    _run("Strip whitespace", strip_whitespace)
    _run("Standardise column names", standardise_column_names)
    _run("Drop duplicates", drop_duplicates)
    _run("Handle missing values", handle_missing_values, fill_value=fill_value, drop_all_na=drop_all_na)
    _run("Normalise dtypes", normalise_dtypes)
    _run("Format date columns", format_date_columns, date_format=date_format)

    return df, steps


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Write the cleaned DataFrame to a CSV file.

    Parameters
    ----------
    df:
        Cleaned DataFrame to persist.
    output_path:
        Full path (including filename) for the output CSV.

    Returns
    -------
    Resolved output Path.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    logger.info("[LOAD] Saved %s rows × %s cols → %s", f"{len(df):,}", len(df.columns), out)
    return out


# ---------------------------------------------------------------------------
# High-level run()
# ---------------------------------------------------------------------------

def run(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    fill_value: int | float | str = 0,
    drop_all_na: bool = True,
    date_format: str = "%Y-%m-%d",
    read_kwargs: dict[str, Any] | None = None,
) -> PipelineReport:
    """Run the full ETL pipeline and return a PipelineReport.

    Parameters
    ----------
    input_path:
        Path to the raw input CSV.
    output_path:
        Destination CSV path.  Defaults to ``output/<stem>_cleaned.csv``.
    fill_value:
        Value used to fill missing numeric entries.
    drop_all_na:
        Whether to drop rows where every value is NaN.
    date_format:
        strftime format string for date columns.
    read_kwargs:
        Extra keyword arguments forwarded to ``pandas.read_csv()``.
    """
    t_start = time.perf_counter()

    in_path = Path(input_path)
    if output_path is None:
        output_path = Path("output") / f"{in_path.stem}_cleaned{in_path.suffix}"
    out_path = Path(output_path)

    # --- Extract ---
    df_raw = extract(in_path, **(read_kwargs or {}))
    rows_in, cols_in = len(df_raw), len(df_raw.columns)

    # --- Transform ---
    df_clean, steps = transform(
        df_raw.copy(),
        fill_value=fill_value,
        drop_all_na=drop_all_na,
        date_format=date_format,
    )

    # --- Load ---
    load(df_clean, out_path)

    total_ms = (time.perf_counter() - t_start) * 1_000

    report = PipelineReport(
        input_path=in_path,
        output_path=out_path,
        rows_in=rows_in,
        rows_out=len(df_clean),
        cols_in=cols_in,
        cols_out=len(df_clean.columns),
        total_duration_ms=total_ms,
        steps=steps,
    )

    logger.info("[PIPELINE] Completed in %.1f ms", total_ms)
    return report
