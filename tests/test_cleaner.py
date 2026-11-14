import pandas as pd

from src.cleaner import clean_customers, clean_phone
from src.quality import profile


def make(rows):
    cols = ["customer_id", "first_name", "last_name", "email", "phone", "city", "country", "signup_date"]
    return pd.DataFrame(rows, columns=cols, dtype="string")


def test_phone_normalisation():
    assert clean_phone("+91 98765 43211") == "9876543211"
    assert clean_phone("098765 43212") == "9876543212"
    assert pd.isna(clean_phone("12345"))
    assert pd.isna(clean_phone(pd.NA))


def test_standardises_text_fields():
    raw = make([["1", "  priya ", "NAIR", " Priya.Nair@Example.com ", "9876543211", " chennai", "india", "2024-02-03"]])
    row = clean_customers(raw).clean.iloc[0]
    assert (row["first_name"], row["last_name"]) == ("Priya", "Nair")
    assert row["email"] == "priya.nair@example.com"
    assert row["city"] == "Chennai"


def test_rejects_missing_and_invalid():
    raw = make([
        ["1", "A", "B", "", "9876543210", "X", "India", "2024-01-01"],
        ["2", "C", "", "c@example.com", "9876543210", "X", "India", "2024-01-01"],
        ["3", "D", "E", "not-an-email", "9876543210", "X", "India", "2024-01-01"],
    ])
    result = clean_customers(raw)
    assert result.clean.empty
    reasons = set(result.rejected["reject_reason"])
    assert reasons == {"missing email", "missing last_name", "invalid email"}


def test_dedupes_by_email_keeping_most_complete():
    raw = make([
        ["1", "A", "B", "a@example.com", "9876543210", "X", "", "2024-01-01"],
        ["2", "A", "B", "A@example.com", "9876543210", "X", "India", "2024-01-01"],
    ])
    result = clean_customers(raw)
    assert len(result.clean) == 1
    assert result.clean.iloc[0]["country"] == "India"
    assert result.stats["duplicates_removed"] == 1


def test_bad_phone_and_dates_are_nulled_not_rejected():
    raw = make([["1", "A", "B", "a@example.com", "123", "X", "India", "2099-01-01"]])
    result = clean_customers(raw)
    assert len(result.clean) == 1
    assert pd.isna(result.clean.iloc[0]["phone"])
    assert pd.isna(result.clean.iloc[0]["signup_date"])
    assert result.stats["invalid_phones_nulled"] == 1
    assert result.stats["invalid_dates_nulled"] == 1


def test_date_parsing_iso_not_swapped_and_dayfirst_fallback():
    raw = make([
        ["1", "A", "B", "a@example.com", "9876543210", "X", "India", "2024-02-03"],
        ["2", "C", "D", "c@example.com", "9876543211", "X", "India", "15/03/2024"],
        ["3", "E", "F", "e@example.com", "9876543212", "X", "India", "not a date"],
    ])
    dates = clean_customers(raw).clean["signup_date"].tolist()
    assert str(dates[0]) == "2024-02-03"
    assert str(dates[1]) == "2024-03-15"
    assert pd.isna(dates[2])


def test_profile_counts():
    raw = make([
        ["1", "A", "B", "a@example.com", "9876543210", "X", "India", "2024-01-01"],
        ["2", "A", "B", "A@example.com", "9876543210", "X", "India", "2024-01-01"],
        ["3", "C", "", "c@example.com", "", "X", "India", "2024-01-01"],
    ])
    p = profile(raw)
    assert p["exact_duplicate_rows"] == 0  # emails differ in case before cleaning
    assert p["duplicate_emails"] == 1
    assert p["incomplete_rows"] == 1
