# Sift & Shift — ETL Data Cleaner

> **A modular, production-grade ETL pipeline for cleaning and standardising CSV files with Pandas.**

```
╔══════════════════════════════════════════════════════════╗
║              SIFT & SHIFT — PIPELINE REPORT              ║
╠══════════════════════════════════════════════════════════╣
║  Input  : input/sales_data.csv                           ║
║  Output : output/sales_data_cleaned.csv                  ║
╠══════════════════════════════════════════════════════════╣
║  Rows   :  1,200 in  →   1,185 out   (   15 removed,  1.2%)  ║
║  Time   :     42.1 ms total                              ║
╚══════════════════════════════════════════════════════════╝
```

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI](#cli)
  - [Python API](#python-api)
- [ETL Pipeline](#etl-pipeline)
  - [Extract](#extract)
  - [Transform](#transform)
  - [Load](#load)
- [Transform Steps](#transform-steps)
- [Configuration](#configuration)
- [Logging](#logging)
- [Testing](#testing)
- [Extending the Pipeline](#extending-the-pipeline)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**Sift & Shift** is a lightweight, dependency-minimal ETL pipeline that reads raw CSV files,
applies a reproducible cleaning sequence, and writes the processed output to an `output/` folder.

The architecture is deliberately modular:

- `sift_shift/pipeline.py` — orchestrates Extract → Transform → Load
- `sift_shift/transforms/cleaning.py` — composable, independently-testable cleaning steps
- `etl.py` — CLI entry point with argument parsing and colourised logging

Every transform step returns a `(DataFrame, notes: str)` tuple so the pipeline can measure
row counts, timing, and produce a structured `PipelineReport` without any global state.

---

## Features

| Category | Detail |
|---|---|
| **Extract** | Reads any `.csv`, `.tsv`, or `.txt` file via `pandas.read_csv()` |
| **Transform** | 6-step modular cleaning pipeline (see below) |
| **Load** | Writes cleaned CSV; auto-creates `output/` directory |
| **Reporting** | Structured `PipelineReport` with per-step timing and row counts |
| **Logging** | Colourised, timestamped `INFO`/`DEBUG` output via Python's `logging` |
| **CLI** | `argparse`-powered interface with `--help`, `--version`, `--verbose` |
| **Python API** | `run()` function usable directly in notebooks or scripts |
| **Testing** | Full `pytest` test suite covering every transform step and pipeline stage |
| **Packaging** | `pyproject.toml` with `[project.scripts]` entry point |

---

## Project Structure

```
ETL-Data-Cleaner/
├── input/                          # Place raw CSV files here
│   └── sample_data.csv             # Included sample for quick demo
├── output/                         # Cleaned CSVs written here (auto-created)
│   └── .gitkeep
├── sift_shift/                     # Core package
│   ├── __init__.py
│   ├── pipeline.py                 # Extract / Transform / Load + PipelineReport
│   ├── logging_config.py           # Colourised logging setup
│   └── transforms/
│       ├── __init__.py
│       └── cleaning.py             # Individual, composable transform functions
├── tests/
│   └── test_pipeline.py            # pytest test suite
├── etl.py                          # CLI entry point
├── pyproject.toml                  # Package metadata & tool config
├── requirements.txt                # Runtime dependencies
├── .gitignore
└── README.md
```

---

## Requirements

- **Python** 3.8+
- **pandas** ≥ 1.5

Optional (dev):

```
pytest>=7.0
pytest-cov
ruff
mypy
pandas-stubs
```

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Sasudul/ETL-Data-Cleaner.git
cd ETL-Data-Cleaner

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 3. Install runtime dependencies
pip install -r requirements.txt

# 4. (Optional) Install with dev extras
pip install -e ".[dev]"
```

---

## Usage

### CLI

Place one or more CSV files in `input/`, then run:

```bash
# Minimal — output defaults to output/<stem>_cleaned.csv
python etl.py --input input/sample_data.csv

# Specify output path
python etl.py --input input/sales.csv --output output/sales_clean.csv

# Custom fill value for numeric NaNs
python etl.py --input input/data.csv --fill-value -1

# Enable DEBUG logging
python etl.py --input input/data.csv --verbose

# Keep rows where every value is NaN (they are dropped by default)
python etl.py --input input/data.csv --keep-all-na-rows

# Help / version
python etl.py --help
python etl.py --version
```

**Full argument reference:**

| Argument | Short | Default | Description |
|---|---|---|---|
| `--input` | `-i` | *(required)* | Path to the input CSV file |
| `--output` | `-o` | `output/<stem>_cleaned.csv` | Destination CSV path |
| `--fill-value` | `-f` | `0` | Value used to fill missing numeric entries |
| `--date-format` | | `%Y-%m-%d` | strftime format for date columns |
| `--keep-all-na-rows` | | `False` | Disable dropping fully-empty rows |
| `--verbose` | `-v` | `False` | Enable DEBUG-level logging |
| `--version` | | | Print version and exit |

---

### Python API

```python
from sift_shift.pipeline import run, extract, transform, load

# ── High-level: full pipeline in one call ──────────────────────────────────
report = run(
    input_path="input/sales.csv",
    output_path="output/sales_clean.csv",   # optional
    fill_value=0,
    drop_all_na=True,
    date_format="%Y-%m-%d",
)
print(report.summary())
print(f"Rows removed: {report.rows_removed}")
print(f"Duration    : {report.total_duration_ms:.1f} ms")

# ── Low-level: step-by-step ────────────────────────────────────────────────
df = extract("input/sales.csv")
df_clean, steps = transform(df, fill_value=-1)
load(df_clean, "output/sales_clean.csv")

# ── Individual transforms ──────────────────────────────────────────────────
from sift_shift.transforms import drop_duplicates, standardise_column_names

df, notes = drop_duplicates(df)
df, notes = standardise_column_names(df)
```

---

## ETL Pipeline

### Extract

```python
def extract(filepath: str | Path, **read_kwargs) -> pd.DataFrame
```

- Validates path exists and has a supported extension (`.csv`, `.tsv`, `.txt`).
- Delegates to `pandas.read_csv()` — all extra kwargs are forwarded.
- Logs row/column count on success.

### Transform

```python
def transform(df, *, fill_value=0, drop_all_na=True, date_format="%Y-%m-%d")
    -> tuple[pd.DataFrame, list[StepResult]]
```

Applies 6 cleaning steps in sequence (see below).  
Returns the cleaned DataFrame **and** a list of `StepResult` objects containing
per-step timing and row-count deltas.

Because `transform()` is a pure function (accepts and returns a DataFrame),
you can substitute any custom implementation without modifying `extract()` or `load()`.

### Load

```python
def load(df: pd.DataFrame, output_path: str | Path) -> Path
```

- Creates parent directories automatically.
- Writes the DataFrame to CSV without the index column.
- Returns the resolved output path.

---

## Transform Steps

| # | Step | Description |
|---|---|---|
| 1 | **Strip whitespace** | Strips leading/trailing whitespace from all `object`-dtype columns |
| 2 | **Standardise column names** | Lowercases names; replaces spaces & special characters with `_` |
| 3 | **Drop duplicates** | Removes entirely duplicate rows |
| 4 | **Handle missing values** | Fills numeric NaNs with `fill_value`; fills string NaNs with `""`; optionally drops rows where all values are NaN |
| 5 | **Normalise dtypes** | Coerces `object` columns to numeric when ≥ 80% of non-null values parse successfully |
| 6 | **Format date columns** | Detects columns whose name contains `date`, `time`, `dt`, or `timestamp`; parses and reformats to `date_format` |

---

## Configuration

All configuration is passed explicitly — there are no environment variables or config files.
This makes pipelines fully reproducible and easy to test.

```python
report = run(
    input_path="input/data.csv",
    fill_value=0,           # numeric NaN fill value
    drop_all_na=True,       # drop rows where every value is NaN
    date_format="%Y-%m-%d", # date column output format
    read_kwargs={           # forwarded to pandas.read_csv()
        "encoding": "utf-8",
        "sep": ";",
    },
)
```

---

## Logging

The `sift_shift.logging_config` module provides colourised, timestamped output.

```
[INFO]  17:31:30  [EXTRACT] Reading: input/sample_data.csv
[INFO]  17:31:30  [EXTRACT] Loaded 1,200 rows × 8 columns
[INFO]  17:31:30  [TRANSFORM] Strip whitespace               rows: 1,200 → 1,200
[INFO]  17:31:30  [TRANSFORM] Drop duplicates                rows: 1,200 → 1,185
[INFO]  17:31:30  [TRANSFORM] Handle missing values          rows: 1,185 → 1,184
[INFO]  17:31:30  [LOAD] Saved 1,184 rows × 8 cols → output/sample_data_cleaned.csv
```

Colours per level: `DEBUG` = cyan · `INFO` = green · `WARNING` = yellow · `ERROR` = red

---

## Testing

```bash
# Run the full test suite
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ -v --cov=sift_shift --cov-report=term-missing
```

Test coverage includes:

- Every individual transform function
- `extract()` — happy path, missing file, unsupported extension
- `transform()` — step count, deduplication, column name standardisation
- `load()` — file creation, no index column
- `run()` — full pipeline integration, report generation

---

## Extending the Pipeline

### Add a custom transform step

```python
# my_transforms.py
import pandas as pd

def clip_outliers(df: pd.DataFrame, *, z_threshold: float = 3.0) -> tuple[pd.DataFrame, str]:
    """Clip numeric values beyond z_threshold standard deviations."""
    from scipy import stats
    num_cols = df.select_dtypes(include="number").columns
    for col in num_cols:
        z = stats.zscore(df[col].dropna())
        # ... clip logic ...
    return df, f"Clipped outliers in {len(num_cols)} column(s)"
```

Then inject it into a custom `transform()`:

```python
from sift_shift.transforms import drop_duplicates, standardise_column_names
from my_transforms import clip_outliers

def my_transform(df):
    df, _ = standardise_column_names(df)
    df, _ = drop_duplicates(df)
    df, _ = clip_outliers(df, z_threshold=2.5)
    return df
```

Because `extract()` and `load()` are independent, no other code changes are needed.

---

## Contributing

1. Fork the repo and create a feature branch: `git checkout -b feat/my-transform`
2. Write your changes with tests.
3. Run `python -m pytest` and ensure all tests pass.
4. Lint with `ruff check .`
5. Open a pull request.

---

## License

MIT © Sift & Shift
