# Customer Data Management and Validation System

A data pipeline that imports customer records from CSV files, profiles and cleans them with **Python and Pandas**, validates and stores them in **MySQL**, and produces summary reports with **SQL**.

**Tech stack:** Python · Pandas · SQLAlchemy · MySQL · SQL · pytest

## What it does

| Stage | What happens | Code |
|-------|--------------|------|
| 1. Import | Reads the CSV as text so nothing is silently coerced | `main.py` |
| 2. Profile | Reports duplicates, missing values and incomplete records in the raw data | `src/quality.py` |
| 3. Clean & validate | Trims whitespace, fixes name/email casing, normalises phones and dates, rejects invalid rows, de-duplicates by email (keeps the most complete record) | `src/cleaner.py` |
| 4. Store | Upserts clean records into MySQL in a single transaction; saves rejected rows with a reason for auditing | `src/db.py`, `sql/schema.sql` |
| 5. Report | Runs the SQL summary queries | `sql/queries.sql`, `src/reports.py` |

### Validation rules

- **Required:** `first_name`, `last_name`, `email`. A missing one rejects the row.
- **Email:** must be well-formed (lowercased first). Otherwise the row is rejected.
- **Duplicates:** same email (case-insensitive) counts as a duplicate. The most complete, most recent record is kept; the rest go to `rejected_records` as `duplicate email`.
- **Phone:** reduced to 10 digits (handles `+91`, leading `0`, spaces). If it can't be made valid, it is set to NULL and the row is kept.
- **Signup date:** `YYYY-MM-DD` is read strictly; other formats are read day-first (`DD/MM/YYYY`). Unparseable or future dates are set to NULL and the row is kept.

The phone rule is India-style (10 digits). Change `clean_phone()` in `src/cleaner.py` for other formats.

## Project structure

```
customer-data-pipeline/
├── main.py                 # entry point
├── data/customers_raw.csv  # sample messy data
├── sql/
│   ├── schema.sql          # tables: customers, rejected_records
│   └── queries.sql         # summary report queries
├── src/
│   ├── cleaner.py          # validation + transformation
│   ├── quality.py          # data quality profiling
│   ├── db.py               # MySQL storage
│   ├── reports.py          # runs queries.sql
│   └── config.py           # reads .env
├── tests/test_cleaner.py
├── requirements.txt
└── .env.example
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then edit .env with your MySQL password
mysql -u root -p < sql/schema.sql
```

## Usage

```bash
python main.py --dry-run         # clean only; writes output/*.csv, no database needed
python main.py                   # full run: clean, load into MySQL, print reports
python main.py --csv path/to/your.csv
python main.py --report-only     # just run the SQL reports
pytest                           # run tests
```

### Sample run (`--dry-run` on the included data)

```
Total rows:             20
Exact duplicate rows:   1
Duplicate emails:       3
Incomplete rows:        2

rows_clean               14
rows_rejected            6
duplicates_removed       3
invalid_phones_nulled    1
invalid_dates_nulled     2
```

### Example queries

```sql
-- Look up a customer
SELECT * FROM customers WHERE email = 'aarav.sharma@example.com';

-- Customers per city
SELECT city, COUNT(*) AS customers FROM customers GROUP BY city ORDER BY customers DESC;
```

## Possible improvements

- Fuzzy matching to catch near-duplicate names
- Chunked loading for very large CSV files
- Logging and a scheduled run (cron / Airflow)
