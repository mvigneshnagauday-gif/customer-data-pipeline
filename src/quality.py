"""Data quality profiling for raw customer data (run BEFORE cleaning)."""
from __future__ import annotations

import pandas as pd

from .cleaner import REQUIRED_FIELDS, standardize


def profile(raw: pd.DataFrame) -> dict:
    df = standardize(raw)
    emails = df["email"].str.lower()
    return {
        "rows": len(df),
        "exact_duplicate_rows": int(df.drop(columns="source_id").duplicated().sum()),
        "duplicate_emails": int(emails.dropna().duplicated().sum()),
        "missing_values": {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()},
        "incomplete_rows": int(df[REQUIRED_FIELDS].isna().any(axis=1).sum()),
    }


def format_profile(p: dict) -> str:
    lines = [
        "DATA QUALITY REPORT (raw input)",
        "-" * 40,
        f"Total rows:             {p['rows']}",
        f"Exact duplicate rows:   {p['exact_duplicate_rows']}",
        f"Duplicate emails:       {p['duplicate_emails']}",
        f"Incomplete rows:        {p['incomplete_rows']}  (missing {', '.join(REQUIRED_FIELDS)})",
        "Missing values by column:",
    ]
    if p["missing_values"]:
        lines += [f"  {col:<12} {n}" for col, n in p["missing_values"].items()]
    else:
        lines.append("  none")
    return "\n".join(lines)
