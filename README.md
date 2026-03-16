# Sift & Shift — ETL Data Cleaner

A simple, modular Python-based ETL (Extract, Transform, Load) tool for cleaning and standardising CSV files using [Pandas](https://pandas.pydata.org/).

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [ETL Pipeline](#etl-pipeline)
  - [Extract](#extract)
  - [Transform](#transform)
  - [Load](#load)
- [Configuration](#configuration)
- [Logging](#logging)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**Sift & Shift** is a lightweight ETL pipeline that reads raw CSV files, cleans and standardises the data, and writes the processed output to an `output/` folder. The code is intentionally modular so that the Transform logic can be swapped out or extended without touching the Extract or Load stages.

---

## Features

- **Extract** — reads any CSV file from a configurable input folder.
- **Transform** — cleans data in a reproducible, step-by-step pipeline:
  - Removes duplicate rows.
  - Handles missing values (fill with a default value or drop rows).
  - Standardises column names (lowercase, spaces replaced with underscores).
  - Formats date columns to `YYYY-MM-DD`.
- **Load** — exports the cleaned DataFrame to a new CSV file inside an `output/` folder.
- Built-in **logging / print statements** at every stage for easy progress tracking.
- Fully modular design — swap in a custom `transform()` function with no changes required elsewhere.

---

## Project Structure

```
ETL-Data-Cleaner/
├── input/                  # Place raw CSV files here
├── output/                 # Cleaned CSV files are written here (auto-created)
├── etl.py                  # Main ETL script (Extract → Transform → Load)
├── requirements.txt        # Python dependencies
├── .gitignore
└── README.md
```

---

## Requirements

- Python 3.8+
- [pandas](https://pandas.pydata.org/) >= 1.3

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Sasudul/ETL-Data-Cleaner.git
cd ETL-Data-Cleaner

# 2. (Optional) Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Usage

Place one or more CSV files in the `input/` folder, then run:

```bash
python etl.py --input input/your_file.csv
```

The cleaned file will be saved to `output/your_file_cleaned.csv`.

---

## ETL Pipeline

### Extract

```python
def extract(filepath: str) -> pd.DataFrame:
    """Read a CSV file and return a DataFrame."""
```

Reads the CSV at `filepath` using `pandas.read_csv()` and logs the number of rows and columns loaded.

### Transform

```python
def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardise the DataFrame."""
```

Applies the following steps in order:

| Step | Description |
|------|-------------|
| 1 | **Drop duplicates** — removes entirely duplicate rows. |
| 2 | **Handle missing values** — fills numeric columns with `0` and drops rows where all values are `NaN`. |
| 3 | **Standardise column names** — converts to lowercase and replaces spaces with underscores. |
| 4 | **Format date columns** — detects columns whose name contains `date` and parses them to `YYYY-MM-DD`. |

Because `transform()` is a standalone function that accepts and returns a `DataFrame`, you can replace it with any custom implementation without modifying `extract()` or `load()`.

### Load

```python
def load(df: pd.DataFrame, output_path: str) -> None:
    """Write the cleaned DataFrame to a CSV file."""
```

Creates the `output/` directory if it does not exist, then writes the DataFrame to `output_path` using `pandas.to_csv()` (without the index column).

---

## Configuration

| Argument | Default | Description |
|----------|---------|-------------|
| `--input` | *(required)* | Path to the input CSV file. |
| `--output` | `output/` | Folder where the cleaned CSV is saved. |
| `--fill-value` | `0` | Value used to fill missing numeric entries. |

---

## Logging

The script uses Python's built-in `logging` module (level `INFO`) and prints a summary at each stage:

```
[INFO] Extract  — loaded 1,200 rows × 8 columns from input/sales_data.csv
[INFO] Transform — after dedup: 1,185 rows
[INFO] Transform — missing values handled
[INFO] Transform — column names standardised
[INFO] Transform — date columns formatted
[INFO] Load     — saved cleaned data to output/sales_data_cleaned.csv
```

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-improvement`.
3. Commit your changes: `git commit -m "Add my improvement"`.
4. Push to your fork: `git push origin feature/my-improvement`.
5. Open a Pull Request.

Please ensure any new Transform steps are added as separate, well-named functions so the pipeline remains easy to read and test.

---

## License

This project is licensed under the [MIT License](LICENSE).
