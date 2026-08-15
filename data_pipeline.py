"""
data_pipeline.py
------------------
STEP 1 of the pipeline: clean the raw transaction export and load it into
MySQL — the "Built MySQL analytics pipeline to evaluate Walmart sales
performance" part of the project.

Real-world data-quality issues handled here (found by actually inspecting
this dataset, not assumed):
  - `unit_price` is stored as a string with a "$" prefix (e.g. "$74.69")
  - 31 rows have missing unit_price / quantity
  - dates are stored as DD/MM/YY strings, not a proper date type
  - no pre-computed revenue/profit columns — these are derived here so SQL
    analysts downstream don't have to redo this arithmetic in every query
"""

import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import String, Float, Integer, Date

from config import RAW_DATA_CSV, CLEANED_DATA_CSV, SQLALCHEMY_URI, SALES_TABLE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def clean_data(raw_csv: str = RAW_DATA_CSV) -> pd.DataFrame:
    """Load the raw export and fix known data-quality issues."""
    df = pd.read_csv(raw_csv)

    before = len(df)

    # unit_price arrives as "$74.69" — strip the currency symbol and cast to float
    df["unit_price"] = (
        df["unit_price"].astype(str).str.replace("$", "", regex=False).astype(float)
    )

    # Drop rows missing the fields needed to compute revenue — can't safely
    # impute a transaction's price or quantity, so these are excluded rather
    # than guessed at (31 rows in the raw export, ~0.3% of the data)
    df = df.dropna(subset=["unit_price", "quantity"])

    # Dates are DD/MM/YY strings — parse into a real date type so SQL can
    # do date arithmetic / EXTRACT(MONTH FROM ...) downstream
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%y")

    # Derived columns every downstream query will need — computing them once
    # here means every SQL query afterward is simpler and consistent
    df["total_revenue"] = df["unit_price"] * df["quantity"]
    df["profit"] = df["total_revenue"] * df["profit_margin"]

    logger.info(f"Cleaned data: {before} -> {len(df)} rows "
                f"({before - len(df)} dropped for missing price/quantity)")

    return df.reset_index(drop=True)


def load_into_mysql(df: pd.DataFrame, table_name: str = SALES_TABLE):
    """
    Load the cleaned DataFrame into MySQL using SQLAlchemy + pandas'
    `to_sql`. In a real company pipeline this step would more likely be a
    scheduled ETL job (Airflow, dbt, etc.) reading from a data warehouse
    extract — this reproduces the same end state (a queryable SQL table)
    for a portfolio-scale dataset.
    """
    engine = create_engine(SQLALCHEMY_URI)

    # Explicit column types: pandas' default to_sql maps every string column
    # to MySQL's unbounded TEXT type, which MySQL then REFUSES to index
    # ("BLOB/TEXT column used in key specification without a key length").
    # Declaring VARCHAR lengths up front avoids that entirely and matches
    # what a real analytics table should look like anyway.
    dtype_map = {
        "Branch": String(20),
        "City": String(50),
        "category": String(50),
        "payment_method": String(20),
        "date": Date(),
        "unit_price": Float(),
        "quantity": Float(),
        "rating": Float(),
        "profit_margin": Float(),
        "total_revenue": Float(),
        "profit": Float(),
        "invoice_id": Integer(),
    }

    df.to_sql(table_name, engine, if_exists="replace", index=False,
              chunksize=1000, dtype=dtype_map)

    # Add indexes on the columns analytical queries filter/group by most —
    # this is the kind of detail that separates "wrote some SQL" from
    # "built a pipeline," since unindexed GROUP BYs on 10K+ rows across
    # many branches get noticeably slower without them.
    with engine.connect() as conn:
        for col in ["Branch", "City", "category", "date", "payment_method"]:
            index_name = f"idx_{table_name}_{col.lower()}"
            try:
                conn.execute(text(f"CREATE INDEX {index_name} ON {table_name} (`{col}`)"))
            except Exception as e:
                logger.warning(f"Could not create index on {col} (may already exist): {e}")
        conn.commit()

    logger.info(f"Loaded {len(df)} rows into MySQL table `{table_name}` with indexes on key columns")


def run_data_pipeline():
    cleaned_df = clean_data()
    cleaned_df.to_csv(CLEANED_DATA_CSV, index=False)
    load_into_mysql(cleaned_df)
    return cleaned_df


if __name__ == "__main__":
    run_data_pipeline()
