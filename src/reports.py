"""Run the summary queries in sql/queries.sql and print the results."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

QUERIES_FILE = Path(__file__).resolve().parent.parent / "sql" / "queries.sql"


def load_queries(path: Path = QUERIES_FILE) -> dict[str, str]:
    """Parse '-- name: foo' blocks into {name: sql}."""
    queries: dict[str, str] = {}
    for block in re.split(r"^-- name:\s*", path.read_text(), flags=re.MULTILINE)[1:]:
        name, _, body = block.partition("\n")
        queries[name.strip()] = body.strip().rstrip(";")
    return queries


def run_reports(engine) -> None:
    from sqlalchemy import text

    for name, sql in load_queries().items():
        df = pd.read_sql(text(sql), engine)
        print(f"\n== {name.replace('_', ' ').upper()} ==")
        print(df.to_string(index=False) if not df.empty else "(no rows)")
