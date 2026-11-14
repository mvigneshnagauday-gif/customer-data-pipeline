"""Validation and transformation of raw customer records."""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

NULL_TOKENS = {"", "n/a", "na", "null", "none", "-", "nan"}
REQUIRED_FIELDS = ["first_name", "last_name", "email"]
OUTPUT_COLUMNS = [
    "source_id", "first_name", "last_name", "email",
    "phone", "city", "country", "signup_date",
]
EMAIL_PATTERN = r"^[a-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)*\.[a-z]{2,}$"


@dataclass
class CleanResult:
    clean: pd.DataFrame
    rejected: pd.DataFrame
    stats: dict


def standardize(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalise column names, trim whitespace and turn null-like tokens into NA."""
    df = raw.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns={"customer_id": "source_id"})
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    for col in df.columns:
        s = df[col].astype("string").str.strip()
        df[col] = s.mask(s.str.lower().isin(NULL_TOKENS))
    return df


def clean_phone(value) -> object:
    """Return a 10-digit phone number, or NA if it cannot be made valid."""
    if pd.isna(value):
        return pd.NA
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if len(digits) == 10 else pd.NA


def clean_customers(raw: pd.DataFrame) -> CleanResult:
    df = standardize(raw)
    df["source_row"] = raw.index + 2  # line number in the CSV (header is line 1)

    # --- transformations -------------------------------------------------
    for col in ("first_name", "last_name", "city", "country"):
        df[col] = df[col].str.title()
    df["email"] = df["email"].str.lower()

    phone_before = df["phone"].notna()
    df["phone"] = df["phone"].apply(clean_phone).astype("string")
    invalid_phones = int((phone_before & df["phone"].isna()).sum())

    date_before = df["signup_date"].notna()
    # ISO dates (YYYY-MM-DD) are parsed strictly; anything else is read day-first (DD/MM/YYYY).
    iso = pd.to_datetime(df["signup_date"], format="%Y-%m-%d", errors="coerce")
    other = pd.to_datetime(
        df["signup_date"].where(iso.isna()), errors="coerce", format="mixed", dayfirst=True
    )
    parsed = iso.fillna(other)
    parsed = parsed.mask(parsed > pd.Timestamp.today().normalize())  # no future dates
    df["signup_date"] = parsed
    invalid_dates = int((date_before & df["signup_date"].isna()).sum())

    # --- validation ------------------------------------------------------
    reasons = pd.Series("", index=df.index, dtype="object")
    for field in REQUIRED_FIELDS:
        reasons = reasons.where(~df[field].isna(), reasons + f"missing {field}; ")
    bad_email = df["email"].notna() & ~df["email"].fillna("").str.match(EMAIL_PATTERN).astype(bool)
    reasons = reasons.where(~bad_email, reasons + "invalid email; ")
    reasons = reasons.str.rstrip("; ")

    invalid_rows = df[reasons != ""].assign(reject_reason=reasons[reasons != ""])
    valid = df[reasons == ""]

    # --- de-duplication (by email, keep the most complete / newest) ------
    ranked = valid.assign(_score=valid[OUTPUT_COLUMNS].notna().sum(axis=1))
    ranked = ranked.sort_values(
        ["_score", "signup_date"], ascending=[False, False],
        na_position="last", kind="stable",
    )
    kept = ranked.drop_duplicates(subset="email", keep="first")
    dupes = ranked.loc[~ranked.index.isin(kept.index)].assign(reject_reason="duplicate email")

    clean = kept.drop(columns="_score").sort_values("source_row")
    rejected = pd.concat([invalid_rows, dupes.drop(columns="_score")]).sort_values("source_row")

    clean = clean[OUTPUT_COLUMNS + ["source_row"]].copy()
    clean["signup_date"] = clean["signup_date"].dt.date
    rejected = rejected[OUTPUT_COLUMNS + ["source_row", "reject_reason"]].copy()
    rejected["signup_date"] = rejected["signup_date"].dt.date

    stats = {
        "rows_in": len(raw),
        "rows_clean": len(clean),
        "rows_rejected": len(rejected),
        "duplicates_removed": len(dupes),
        "invalid_rows": len(invalid_rows),
        "invalid_phones_nulled": invalid_phones,
        "invalid_dates_nulled": invalid_dates,
    }
    return CleanResult(clean=clean, rejected=rejected, stats=stats)
