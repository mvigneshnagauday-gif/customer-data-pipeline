"""MySQL storage layer (SQLAlchemy + PyMySQL)."""
from __future__ import annotations

import json
from urllib.parse import quote_plus

import pandas as pd

from . import config

UPSERT_CUSTOMER = """
INSERT INTO customers
  (source_id, first_name, last_name, email, phone, city, country, signup_date)
VALUES
  (:source_id, :first_name, :last_name, :email, :phone, :city, :country, :signup_date)
ON DUPLICATE KEY UPDATE
  source_id   = VALUES(source_id),
  first_name  = VALUES(first_name),
  last_name   = VALUES(last_name),
  phone       = VALUES(phone),
  city        = VALUES(city),
  country     = VALUES(country),
  signup_date = VALUES(signup_date)
"""

INSERT_REJECTED = """
INSERT INTO rejected_records (source_file, source_row, reason, raw_data)
VALUES (:source_file, :source_row, :reason, :raw_data)
"""


def get_engine():
    from sqlalchemy import create_engine  # imported lazily so --dry-run needs no driver

    url = (
        f"mysql+pymysql://{config.MYSQL_USER}:{quote_plus(config.MYSQL_PASSWORD)}"
        f"@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE}"
    )
    return create_engine(url, pool_pre_ping=True)


def _none_if_na(value):
    return None if pd.isna(value) else value


def load_customers(engine, clean: pd.DataFrame) -> int:
    from sqlalchemy import text

    records = [
        {k: _none_if_na(v) for k, v in row.items() if k != "source_row"}
        for row in clean.to_dict(orient="records")
    ]
    if not records:
        return 0
    with engine.begin() as conn:  # one transaction: all rows or none
        conn.execute(text(UPSERT_CUSTOMER), records)
    return len(records)


def load_rejected(engine, rejected: pd.DataFrame, source_file: str) -> int:
    from sqlalchemy import text

    records = [
        {
            "source_file": source_file,
            "source_row": _none_if_na(row["source_row"]),
            "reason": row["reject_reason"],
            "raw_data": json.dumps(
                {k: _none_if_na(v) for k, v in row.items() if k not in ("source_row", "reject_reason")},
                default=str,
            ),
        }
        for row in rejected.to_dict(orient="records")
    ]
    with engine.begin() as conn:
        # Replace this file's previous rejects so re-runs don't pile up rows.
        conn.execute(text("DELETE FROM rejected_records WHERE source_file = :f"), {"f": source_file})
        if records:
            conn.execute(text(INSERT_REJECTED), records)
    return len(records)
