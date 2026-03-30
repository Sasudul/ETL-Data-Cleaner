"""
etl.py  —  Sift & Shift CLI entry point
Usage:
    python etl.py --input input/your_file.csv
    python etl.py --input input/sales.csv --output output/sales_clean.csv --fill-value -1
    python etl.py --input input/data.csv --verbose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sift_shift.logging_config import configure
from sift_shift.pipeline import run


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sift-shift",
        description=(
            "Sift & Shift — ETL Data Cleaner\n"
            "Cleans and standardises CSV files through a modular pipeline.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python etl.py --input input/sales.csv\n"
            "  python etl.py --input input/sales.csv --output output/clean.csv\n"
            "  python etl.py --input input/sales.csv --fill-value -1 --verbose\n"
        ),
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        metavar="FILE",
        help="Path to the input CSV file (required).",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        metavar="FILE",
        help="Destination CSV path. Defaults to output/<stem>_cleaned.csv.",
    )
    parser.add_argument(
        "--fill-value", "-f",
        default=0,
        metavar="VALUE",
        help="Value used to fill missing numeric entries (default: 0).",
    )
    parser.add_argument(
        "--date-format",
        default="%Y-%m-%d",
        metavar="FMT",
        help="strftime format for date columns (default: %%Y-%%m-%%d).",
    )
    parser.add_argument(
        "--keep-all-na-rows",
        action="store_true",
        default=False,
        help="Do NOT drop rows where every value is NaN.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Sift & Shift 1.0.0",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    configure("DEBUG" if args.verbose else "INFO")

    # Coerce fill_value to a number if possible
    fill_value: int | float | str = args.fill_value
    try:
        fill_value = int(fill_value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        try:
            fill_value = float(fill_value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass  # keep as string

    try:
        report = run(
            input_path=args.input,
            output_path=args.output,
            fill_value=fill_value,
            drop_all_na=not args.keep_all_na_rows,
            date_format=args.date_format,
        )
        print(report.summary())
        return 0
    except FileNotFoundError as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"\n[ERROR] Pipeline failed: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
