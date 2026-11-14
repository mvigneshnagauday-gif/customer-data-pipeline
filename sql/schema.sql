-- Run once:  mysql -u root -p < sql/schema.sql

CREATE DATABASE IF NOT EXISTS customer_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE customer_db;

-- Cleaned, validated customers. Email is the natural key, so re-running the
-- pipeline updates existing rows instead of creating duplicates.
CREATE TABLE IF NOT EXISTS customers (
  customer_id  INT AUTO_INCREMENT PRIMARY KEY,
  source_id    VARCHAR(20)  NULL,
  first_name   VARCHAR(50)  NOT NULL,
  last_name    VARCHAR(50)  NOT NULL,
  email        VARCHAR(255) NOT NULL,
  phone        CHAR(10)     NULL,
  city         VARCHAR(80)  NULL,
  country      VARCHAR(80)  NULL,
  signup_date  DATE         NULL,
  created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_customers_email (email),
  KEY idx_customers_city (city),
  KEY idx_customers_signup_date (signup_date)
) ENGINE=InnoDB;

-- Records that failed validation or were duplicates, kept for auditing.
CREATE TABLE IF NOT EXISTS rejected_records (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  source_file  VARCHAR(255) NOT NULL,
  source_row   INT          NULL,
  reason       VARCHAR(255) NOT NULL,
  raw_data     JSON         NULL,
  rejected_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_rejected_file (source_file)
) ENGINE=InnoDB;
