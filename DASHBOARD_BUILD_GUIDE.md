# Dashboard Build Guide (Power BI / Tableau)

Like the SQL layer, this part is scriptable up to a point — but the actual
dashboard canvas has to be assembled by hand in Power BI Desktop or
Tableau, since neither has a CLI/API for programmatic report building.
Every CSV below is pre-aggregated so this is drag-and-drop from here.

## 1. Import the data

Import all 14 files from `data/dashboard_exports/` — each is one query's
result, already aggregated to dashboard grain.

| File | Answers |
|---|---|
| `branch_performance.csv` | Which branches make the most revenue/profit? |
| `top_selling_products.csv` | Which categories sell the most units? |
| `highest_revenue_categories.csv` | Which categories make the most money? |
| `high_revenue_cities.csv` | Where is revenue concentrated geographically? |
| `monthly_revenue_trend.csv` | How does demand change over time? |
| `category_profitability.csv` | Which categories have the best margins? |
| `underperforming_branches.csv` | Which branches need intervention? |
| `time_of_day_pattern.csv` | When do customers shop? |
| `rating_vs_spend.csv` | Does satisfaction correlate with spend? |
| `lowest_rated_branches.csv` | Where is customer experience weakest? |
| `payment_method_trends.csv`, `day_of_week_pattern.csv`, `branch_rank_within_city.csv`, `category_by_payment_method.csv` | supporting detail views |

## 2. Suggested pages & visuals

**Page 1 — Executive Overview**
- KPI cards: total revenue, total profit, overall avg rating, branch count
- Bar chart: `total_revenue` by `Branch` (top 15), from `branch_performance.csv`
- Line chart: `total_revenue` by `sales_month`, from `monthly_revenue_trend.csv`
  — the demand-pattern / seasonality visual

**Page 2 — Product & Profitability**
- Bar chart: `total_units_sold` by `category` (inventory planning view),
  from `top_selling_products.csv`
- Bar chart: `profit_margin_pct` by `category`, from `category_profitability.csv`
  — deliberately next to the units chart, since the two rankings differ
  (highest-volume category isn't always highest-margin)

**Page 3 — Branch & Customer Insights**
- Map or bar chart: `total_revenue` by `City`, from `high_revenue_cities.csv`
- Table: `underperforming_branches.csv`, conditionally formatted red on
  `revenue_gap_vs_avg` — this is the literal "which branches need help" list
- Scatter or column chart: `avg_transaction_value` by `rating_tier`, from
  `rating_vs_spend.csv` — makes the satisfaction-drives-spend case visually

## 3. DAX measures worth adding (Power BI)

```dax
Total Network Revenue = SUM(branch_performance[total_revenue])

Revenue Gap % =
DIVIDE(
    SUM(underperforming_branches[revenue_gap_vs_avg]),
    AVERAGE(underperforming_branches[network_avg_revenue])
)

Avg Rating (Weighted) =
SUMX(branch_performance, branch_performance[avg_customer_rating] * branch_performance[transaction_count])
/ SUM(branch_performance[transaction_count])
```

## 4. Publishing

Power BI: **File → Publish → Publish to Power BI** for a shareable link.
Tableau: **Server → Publish Workbook** (Tableau Public is free for
portfolio use). Either way, a live link is a stronger resume/portfolio
artifact than static screenshots.
