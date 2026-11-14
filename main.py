"""Customer data pipeline: CSV -> profile -> clean/validate -> MySQL -> reports."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.cleaner import clean_customers
from src.quality import format_profile, profile

OUTPUT_DIR = Path("output")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import, clean and store customer records.")
    p.add_argument("--csv", default="data/customers_raw.csv", help="input CSV path")
    p.add_argument("--dry-run", action="store_true", help="clean and write CSVs only; skip MySQL")
    p.add_argument("--report-only", action="store_true", help="skip import, just run SQL reports")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.report_only:
        from src.db import get_engine
        from src.reports import run_reports

        run_reports(get_engine())
        return

    # 1. Load (read everything as text so nothing is silently coerced)
    raw = pd.read_csv(args.csv, dtype=str, keep_default_na=False)

    # 2. Profile raw data quality
    print(format_profile(profile(raw)))

    # 3. Clean + validate
    result = clean_customers(raw)
    print("\nCLEANING SUMMARY")
    print("-" * 40)
    for key, value in result.stats.items():
        print(f"{key:<24} {value}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    result.clean.drop(columns="source_row").to_csv(OUTPUT_DIR / "cleaned_customers.csv", index=False)
    result.rejected.to_csv(OUTPUT_DIR / "rejected_customers.csv", index=False)
    print(f"\nWrote {OUTPUT_DIR}/cleaned_customers.csv and {OUTPUT_DIR}/rejected_customers.csv")

    if args.dry_run:
        print("Dry run: MySQL load skipped.")
        return

    # 4. Store in MySQL, then 5. report
    from src.db import get_engine, load_customers, load_rejected
    from src.reports import run_reports

    engine = get_engine()
    n_ok = load_customers(engine, result.clean)
    n_bad = load_rejected(engine, result.rejected, source_file=Path(args.csv).name)
    print(f"Loaded {n_ok} customers and {n_bad} rejected records into MySQL.")
    run_reports(engine)


if __name__ == "__main__":
    main()
