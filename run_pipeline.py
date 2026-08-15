"""
run_pipeline.py
----------------
Orchestrator: runs the full Walmart sales analytics pipeline end-to-end.

    1. Data cleaning + MySQL load  (data_pipeline.py)
    2. Core SQL analysis            (sql_analysis.py)      -> 10 queries
    3. Customer trend analysis      (customer_trends.py)    -> 4 queries
    4. Dashboard build              (manual, Power BI/Tableau — see guide)

Usage:
    python run_pipeline.py

Requires a running MySQL server reachable with the credentials in
config.py (or the matching environment variables).
"""

import logging

import data_pipeline
import sql_analysis
import customer_trends

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("STEP 1/3: Cleaning data and loading into MySQL...")
    data_pipeline.run_data_pipeline()

    logger.info("STEP 2/3: Running core SQL analysis (branch, product, revenue)...")
    core_results = sql_analysis.run_all_queries()
    sql_analysis.print_key_insights(core_results)

    logger.info("STEP 3/3: Running customer trend analysis...")
    trend_results = customer_trends.run_customer_trend_analysis()
    customer_trends.print_customer_insights(trend_results)

    total_queries = len(sql_analysis.QUERIES) + len(customer_trends.QUERIES)
    logger.info(
        f"Pipeline complete. Ran {total_queries} SQL queries total. "
        f"All results are in data/dashboard_exports/ — see DASHBOARD_BUILD_GUIDE.md "
        f"to assemble the Power BI / Tableau dashboard."
    )


if __name__ == "__main__":
    main()
