"""
customer_trends.py
--------------------
STEP 3 of the pipeline: customer-behavior analysis to round out the
"customer trends" part of "evaluating branch performance, customer trends,
and profitability." Separate module from sql_analysis.py because these
queries are about SHOPPER behavior (when/how they buy, how they rate their
experience) rather than store/product performance.
"""

import logging
import pandas as pd

from sql_analysis import get_engine, run_query
from config import INSIGHTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Time-of-day shopping pattern — informs staffing schedules
# ---------------------------------------------------------------------------
Q_TIME_OF_DAY_PATTERN = """
SELECT
    CASE
        WHEN HOUR(time) < 12 THEN '1. Morning (before 12pm)'
        WHEN HOUR(time) < 17 THEN '2. Afternoon (12-5pm)'
        ELSE '3. Evening (after 5pm)'
    END AS time_of_day,
    COUNT(*) AS transaction_count,
    ROUND(AVG(total_revenue), 2) AS avg_transaction_value,
    ROUND(AVG(rating), 2) AS avg_rating
FROM sales
GROUP BY time_of_day
ORDER BY time_of_day;
"""

# ---------------------------------------------------------------------------
# Rating vs. spend — does a better in-store experience correlate with
# bigger baskets? A genuinely useful "is customer satisfaction worth
# investing in" business question.
# ---------------------------------------------------------------------------
Q_RATING_VS_SPEND = """
SELECT
    CASE
        WHEN rating < 6 THEN '1. Low (below 6)'
        WHEN rating < 8 THEN '2. Medium (6-8)'
        ELSE '3. High (8+)'
    END AS rating_tier,
    COUNT(*) AS transaction_count,
    ROUND(AVG(total_revenue), 2) AS avg_transaction_value,
    ROUND(AVG(quantity), 2) AS avg_items_per_basket
FROM sales
GROUP BY rating_tier
ORDER BY rating_tier;
"""

# ---------------------------------------------------------------------------
# Category preference by payment method — do cash vs. card vs. e-wallet
# customers shop differently? Useful for targeted promotions.
# ---------------------------------------------------------------------------
Q_CATEGORY_BY_PAYMENT = """
SELECT
    payment_method,
    category,
    COUNT(*) AS transaction_count,
    ROUND(SUM(total_revenue), 2) AS total_revenue
FROM sales
GROUP BY payment_method, category
ORDER BY payment_method, total_revenue DESC;
"""

# ---------------------------------------------------------------------------
# Branch-level rating leaders and laggards — customer experience by location
# ---------------------------------------------------------------------------
Q_BRANCH_RATING_OUTLIERS = """
SELECT
    Branch,
    City,
    COUNT(*) AS transaction_count,
    ROUND(AVG(rating), 2) AS avg_rating
FROM sales
GROUP BY Branch, City
HAVING COUNT(*) >= 30
ORDER BY avg_rating ASC
LIMIT 10;
"""

QUERIES = {
    "time_of_day_pattern": Q_TIME_OF_DAY_PATTERN,
    "rating_vs_spend": Q_RATING_VS_SPEND,
    "category_by_payment_method": Q_CATEGORY_BY_PAYMENT,
    "lowest_rated_branches": Q_BRANCH_RATING_OUTLIERS,
}


def run_customer_trend_analysis() -> dict:
    engine = get_engine()
    results = {}

    for name, query in QUERIES.items():
        df = run_query(engine, query)
        results[name] = df
        df.to_csv(f"{INSIGHTS_DIR}/{name}.csv", index=False)
        logger.info(f"  {name}: {len(df)} rows -> {INSIGHTS_DIR}/{name}.csv")

    return results


def print_customer_insights(results: dict):
    print(f"\n=== Customer trend analysis ({len(QUERIES)} queries) ===")

    print("\n--- Shopping pattern by time of day ---")
    print(results["time_of_day_pattern"].to_string(index=False))

    print("\n--- Does customer rating correlate with basket size? ---")
    print(results["rating_vs_spend"].to_string(index=False))

    print("\n--- 10 lowest-rated branches (30+ transactions) ---")
    print(results["lowest_rated_branches"].to_string(index=False))


if __name__ == "__main__":
    results = run_customer_trend_analysis()
    print_customer_insights(results)
