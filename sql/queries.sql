-- Summary report queries. Each block starts with "-- name: <query_name>"
-- and is run by `python main.py --report-only` (src/reports.py).

-- name: total_customers
SELECT COUNT(*) AS total_customers
FROM customers;

-- name: customers_by_city
SELECT city, COUNT(*) AS customers
FROM customers
WHERE city IS NOT NULL
GROUP BY city
ORDER BY customers DESC, city;

-- name: signups_by_month
SELECT DATE_FORMAT(signup_date, '%Y-%m') AS month, COUNT(*) AS signups
FROM customers
WHERE signup_date IS NOT NULL
GROUP BY month
ORDER BY month;

-- name: data_completeness
SELECT
  COUNT(*)                   AS total,
  SUM(phone IS NULL)         AS missing_phone,
  SUM(city IS NULL)          AS missing_city,
  SUM(country IS NULL)       AS missing_country,
  SUM(signup_date IS NULL)   AS missing_signup_date
FROM customers;

-- name: recent_customers
SELECT customer_id, CONCAT(first_name, ' ', last_name) AS full_name,
       email, city, signup_date
FROM customers
ORDER BY signup_date DESC, customer_id DESC
LIMIT 10;

-- name: rejected_by_reason
SELECT reason, COUNT(*) AS records
FROM rejected_records
GROUP BY reason
ORDER BY records DESC, reason;
