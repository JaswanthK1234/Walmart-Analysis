"""
config.py
---------
Central settings for the Walmart sales analytics pipeline.

DATA SOURCE: This project ships with the public "Walmart 10k Sales" dataset
(10,051 transactions across 100 branches / 98 cities, 2019-2023) — the
standard dataset used for Walmart SQL portfolio projects. Swap
`RAW_DATA_CSV` for your own export (same shape: one row per transaction,
branch/city, category, unit price, quantity, date, payment method) to run
this against real company data instead.

DATABASE: Real MySQL, not a stand-in. Update the credentials below (or set
them as environment variables) to point at your own MySQL instance.
"""

import os

DATA_DIR = "data"
RAW_DATA_CSV = f"{DATA_DIR}/Walmart.csv"
CLEANED_DATA_CSV = f"{DATA_DIR}/walmart_clean.csv"

INSIGHTS_DIR = f"{DATA_DIR}/dashboard_exports"

# ---------------------------------------------------------------------------
# MySQL connection settings. Override via environment variables in
# production rather than editing this file directly.
# ---------------------------------------------------------------------------
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "walmart_app")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "walmart_pw")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "walmartSales")

SQLALCHEMY_URI = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)

SALES_TABLE = "sales"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(INSIGHTS_DIR, exist_ok=True)
