"""
sql_analysis.py
-----------------
STEP 2 of the pipeline: the actual SQL analysis layer, run against the
real MySQL table built by data_pipeline.py.

This is the "Designed Y+ SQL queries...evaluating branch performance,
customer trends, profitability" part of the project. 10 distinct,
business-question-driven queries are defined below (not 10 variations of
the same GROUP BY) — each answers something a retail ops or merchandising
team would actually ask:

  1.  top_selling_products        -> which categories move the most units?
  2.  highest_revenue_categories   -> which categories make the most money? (not always the same answer as #1)
  3.  branch_performance           -> revenue, profit, and avg basket size per branch
  4.  high_revenue_cities          -> geographic concentration of revenue
  5.  monthly_revenue_trend        -> seasonality / demand pattern over time
  6.  category_profitability       -> profit MARGIN, not just revenue, by category
  7.  payment_method_trends        -> customer payment preferences by branch
  8.  day_of_week_pattern          -> which days need more inventory/staffing
  9.  branch_profitability_rank    -> window function: rank branches by profit within their city
  10. underperforming_branches     -> branches below the network average (candidates for intervention)
"""

import logging
import pandas as pd
from sqlalchemy import create_engine

from config import SQLALCHEMY_URI, SALES_TABLE, INSIGHTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_engine():
    return create_engine(SQLALCHEMY_URI)


def run_query(engine, query: str) -> pd.DataFrame:
    """
    Run a raw SQL string and return a DataFrame.

    Uses `exec_driver_sql` rather than `text(query)` + pandas' default path
    because PyMySQL's DBAPI layer always runs queries through Python's `%`
    string-formatting (`query % args`) internally — so a literal `%Y`/`%m`
    inside a MySQL DATE_FORMAT() call gets misread as a format placeholder
    and blows up with "unsupported format character". Queries that use
    DATE_FORMAT/DAYNAME-style format strings escape `%` as `%%` to survive
    that step; this helper is what makes that escaping actually take effect.
    """
    with engine.connect() as conn:
        result = conn.exec_driver_sql(query)
        rows = result.fetchall()
        columns = result.keys()
    return pd.DataFrame(rows, columns=columns)


# ---------------------------------------------------------------------------
# 1. TOP-SELLING PRODUCTS (by units) — inventory planning question
# ---------------------------------------------------------------------------
Q_TOP_SELLING_PRODUCTS = """
SELECT
    category,
    SUM(quantity) AS total_units_sold,
    COUNT(*) AS transaction_count,
    ROUND(SUM(total_revenue), 2) AS total_revenue
FROM sales
GROUP BY category
ORDER BY total_units_sold DESC;
"""

# ---------------------------------------------------------------------------
# 2. HIGHEST-REVENUE CATEGORIES — deliberately separate from #1: a category
#    can sell fewer units but generate more revenue if unit price is higher
# ---------------------------------------------------------------------------
Q_HIGHEST_REVENUE_CATEGORIES = """
SELECT
    category,
    ROUND(SUM(total_revenue), 2) AS total_revenue,
    ROUND(AVG(unit_price), 2) AS avg_unit_price,
    RANK() OVER (ORDER BY SUM(total_revenue) DESC) AS revenue_rank
FROM sales
GROUP BY category
ORDER BY total_revenue DESC;
"""

# ---------------------------------------------------------------------------
# 3. BRANCH PERFORMANCE — revenue, profit, and basket size per branch
# ---------------------------------------------------------------------------
Q_BRANCH_PERFORMANCE = """
SELECT
    Branch,
    City,
    COUNT(*) AS transaction_count,
    ROUND(SUM(total_revenue), 2) AS total_revenue,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND(AVG(total_revenue), 2) AS avg_basket_value,
    ROUND(AVG(rating), 2) AS avg_customer_rating
FROM sales
GROUP BY Branch, City
ORDER BY total_revenue DESC;
"""

# ---------------------------------------------------------------------------
# 4. HIGH-REVENUE REGIONS/CITIES — geographic concentration
# ---------------------------------------------------------------------------
Q_HIGH_REVENUE_CITIES = """
SELECT
    City,
    COUNT(DISTINCT Branch) AS branch_count,
    ROUND(SUM(total_revenue), 2) AS total_revenue,
    ROUND(SUM(total_revenue) / COUNT(DISTINCT Branch), 2) AS revenue_per_branch
FROM sales
GROUP BY City
ORDER BY total_revenue DESC
LIMIT 15;
"""

# ---------------------------------------------------------------------------
# 5. MONTHLY REVENUE TREND — demand pattern / seasonality over time
# ---------------------------------------------------------------------------
Q_MONTHLY_REVENUE_TREND = """
SELECT
    DATE_FORMAT(date, '%%Y-%%m') AS sales_month,
    ROUND(SUM(total_revenue), 2) AS total_revenue,
    COUNT(*) AS transaction_count,
    ROUND(SUM(total_revenue) / COUNT(*), 2) AS avg_transaction_value
FROM sales
GROUP BY DATE_FORMAT(date, '%%Y-%%m')
ORDER BY sales_month;
"""
# NOTES:
#   - '%%' (not '%') because PyMySQL's DBAPI layer runs every query through
#     Python string-formatting before sending it — see run_query()'s docstring.
#   - Alias is `sales_month`, not `year_month` — YEAR_MONTH is a MySQL
#     reserved keyword (used in `INTERVAL ... YEAR_MONTH` expressions), so
#     it can't be used as a bare, unbacktick-quoted column alias. This is a
#     real MySQL gotcha, not a Python issue — worth knowing for an interview.

# ---------------------------------------------------------------------------
# 6. CATEGORY PROFITABILITY — profit MARGIN, not just raw profit dollars
# ---------------------------------------------------------------------------
Q_CATEGORY_PROFITABILITY = """
SELECT
    category,
    ROUND(SUM(total_revenue), 2) AS total_revenue,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND(100.0 * SUM(profit) / SUM(total_revenue), 2) AS profit_margin_pct
FROM sales
GROUP BY category
ORDER BY profit_margin_pct DESC;
"""

# ---------------------------------------------------------------------------
# 7. PAYMENT METHOD TRENDS — customer behavior, sliced by branch
# ---------------------------------------------------------------------------
Q_PAYMENT_METHOD_TRENDS = """
SELECT
    payment_method,
    COUNT(*) AS transaction_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM sales), 2) AS pct_of_all_transactions,
    ROUND(AVG(total_revenue), 2) AS avg_transaction_value
FROM sales
GROUP BY payment_method
ORDER BY transaction_count DESC;
"""

# ---------------------------------------------------------------------------
# 8. DAY-OF-WEEK PATTERN — which days need more inventory / staffing
# ---------------------------------------------------------------------------
Q_DAY_OF_WEEK_PATTERN = """
SELECT
    DAYNAME(date) AS day_of_week,
    COUNT(*) AS transaction_count,
    ROUND(SUM(total_revenue), 2) AS total_revenue,
    ROUND(AVG(total_revenue), 2) AS avg_transaction_value
FROM sales
GROUP BY DAYNAME(date), DAYOFWEEK(date)
ORDER BY DAYOFWEEK(date);
"""

# ---------------------------------------------------------------------------
# 9. BRANCH PROFITABILITY RANK WITHIN CITY — window function
#    (identifies the best branch in each multi-branch city)
# ---------------------------------------------------------------------------
Q_BRANCH_RANK_WITHIN_CITY = """
SELECT
    City,
    Branch,
    ROUND(SUM(profit), 2) AS total_profit,
    RANK() OVER (PARTITION BY City ORDER BY SUM(profit) DESC) AS profit_rank_in_city
FROM sales
GROUP BY City, Branch
ORDER BY City, profit_rank_in_city;
"""

# ---------------------------------------------------------------------------
# 10. UNDERPERFORMING BRANCHES — branches below the network average revenue,
#     the concrete "which branches need intervention" list
# ---------------------------------------------------------------------------
Q_UNDERPERFORMING_BRANCHES = """
WITH branch_revenue AS (
    SELECT Branch, City, ROUND(SUM(total_revenue), 2) AS total_revenue
    FROM sales
    GROUP BY Branch, City
),
network_avg AS (
    SELECT AVG(total_revenue) AS avg_branch_revenue FROM branch_revenue
)
SELECT
    b.Branch,
    b.City,
    b.total_revenue,
    ROUND(n.avg_branch_revenue, 2) AS network_avg_revenue,
    ROUND(b.total_revenue - n.avg_branch_revenue, 2) AS revenue_gap_vs_avg
FROM branch_revenue b
CROSS JOIN network_avg n
WHERE b.total_revenue < n.avg_branch_revenue
ORDER BY revenue_gap_vs_avg ASC
LIMIT 15;
"""

QUERIES = {
    "top_selling_products": Q_TOP_SELLING_PRODUCTS,
    "highest_revenue_categories": Q_HIGHEST_REVENUE_CATEGORIES,
    "branch_performance": Q_BRANCH_PERFORMANCE,
    "high_revenue_cities": Q_HIGH_REVENUE_CITIES,
    "monthly_revenue_trend": Q_MONTHLY_REVENUE_TREND,
    "category_profitability": Q_CATEGORY_PROFITABILITY,
    "payment_method_trends": Q_PAYMENT_METHOD_TRENDS,
    "day_of_week_pattern": Q_DAY_OF_WEEK_PATTERN,
    "branch_rank_within_city": Q_BRANCH_RANK_WITHIN_CITY,
    "underperforming_branches": Q_UNDERPERFORMING_BRANCHES,
}


def run_all_queries() -> dict:
    """Run every query above against MySQL, save each result for the
    dashboard, and return everything as a dict of DataFrames."""
    engine = get_engine()
    results = {}

    for name, query in QUERIES.items():
        df = run_query(engine, query)
        results[name] = df
        df.to_csv(f"{INSIGHTS_DIR}/{name}.csv", index=False)
        logger.info(f"  {name}: {len(df)} rows -> {INSIGHTS_DIR}/{name}.csv")

    return results


def print_key_insights(results: dict):
    """Surface the headline numbers a merchandising/ops team would act on."""
    print(f"\n=== Ran {len(QUERIES)} SQL queries against MySQL ===")

    top_products = results["top_selling_products"]
    print(f"\n--- Top-selling category by units ---")
    print(top_products.head(3).to_string(index=False))

    branch_perf = results["branch_performance"]
    print(f"\n--- Top 5 branches by revenue ---")
    print(branch_perf.head(5).to_string(index=False))

    cities = results["high_revenue_cities"]
    print(f"\n--- Top 5 highest-revenue cities ---")
    print(cities.head(5).to_string(index=False))

    margins = results["category_profitability"]
    print(f"\n--- Category profit margins (highest to lowest) ---")
    print(margins.to_string(index=False))

    underperf = results["underperforming_branches"]
    print(f"\n--- {len(underperf)} branches below network-average revenue "
          f"(top 5 furthest below average) ---")
    print(underperf.head(5).to_string(index=False))


if __name__ == "__main__":
    results = run_all_queries()
    print_key_insights(results)
