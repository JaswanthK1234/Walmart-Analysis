# Walmart Sales Analytics Pipeline

End-to-end MySQL analytics pipeline analyzing 10,000+ Walmart transactions
to surface demand patterns, branch performance, and profitability —
built to support inventory planning and pricing decisions, not just
produce a report.

## Pipeline

```
Raw transaction export (CSV)
        |
        v
data_pipeline.py    -> cleans data (strips $, drops bad rows, parses dates),
        |               loads into a real MySQL table with indexes
        v
sql_analysis.py      -> 10 SQL queries: top products, branch performance,
        |                revenue by city, monthly trends, profit margins,
        |                underperforming branches (window functions + CTEs)
        v
customer_trends.py   -> 4 more queries: time-of-day patterns, rating vs.
        |                spend, payment method preferences by category
        v
Power BI / Tableau    -> dashboard (manual — see DASHBOARD_BUILD_GUIDE.md)
```

## Setup

```bash
pip install -r requirements.txt
```

You need a running MySQL server. Quick local setup:

```bash
sudo apt-get install mysql-server
sudo service mysql start
mysql -u root -e "
  CREATE DATABASE walmartSales;
  CREATE USER 'walmart_app'@'localhost' IDENTIFIED BY 'walmart_pw';
  GRANT ALL PRIVILEGES ON walmartSales.* TO 'walmart_app'@'localhost';
  FLUSH PRIVILEGES;
"
```

Then either use those default credentials (already set in `config.py`) or
override via environment variables: `MYSQL_HOST`, `MYSQL_PORT`,
`MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`.

No API keys needed for data — this ships with the public **Walmart 10k
Sales** dataset (`data/Walmart.csv`, 10,051 transactions, 100 branches,
2019–2023), the standard dataset for Walmart SQL portfolio projects. To
run this on your own retailer's data, replace that CSV and adjust column
names in `data_pipeline.py` and `sql_analysis.py` to match.

## Run

```bash
python run_pipeline.py
```

This cleans the data, loads it into MySQL, and runs all 14 SQL queries,
writing every result to `data/dashboard_exports/`. Then follow
`DASHBOARD_BUILD_GUIDE.md` to assemble the dashboard by hand in Power BI
or Tableau (no CLI/API exists for that step — it's manual by nature).

## Results on the included dataset (example numbers — yours will differ)

- **10,020 transactions** analyzed via SQL (10,051 raw, 31 dropped for
  missing price/quantity) across **100 branches** in **98 cities**
- **Top sellers by volume:** Fashion accessories and Home & lifestyle
  (~9,700 units each) — but **Food & beverages has the best profit
  margin** (40.3%) despite lower volume — a real volume-vs-margin tradeoff
  a merchandising team would want to know about
- **15 branches** sit below the network's average revenue — a concrete,
  named list for a "which stores need intervention" conversation
- **Customers who rate their experience 8+/10 spend 23% more per basket**
  ($143 vs. $116) than those rating below 6 — suggests in-store
  experience investment has a real revenue link, not just a satisfaction
  metric

These numbers come from the public dataset included here, not a real
company — swap in your own data before quoting these on a resume.

## Real bugs hit and fixed while building this (worth knowing for an interview)

- **pandas `to_sql` defaults to unbounded `TEXT` for string columns**,
  which MySQL refuses to index ("BLOB/TEXT column used in key
  specification without a key length"). Fixed by passing explicit
  `VARCHAR` types via SQLAlchemy's `dtype=` parameter.
- **PyMySQL's DBAPI layer runs every query through Python's `%`
  string-formatting** before sending it to MySQL, so a literal `%Y-%m`
  inside `DATE_FORMAT()` gets misread as a format placeholder. Fixed by
  escaping `%` as `%%` and using `exec_driver_sql` explicitly.
- **`YEAR_MONTH` is a MySQL reserved keyword** (used in `INTERVAL ...
  YEAR_MONTH` expressions), so it can't be used as a bare column alias —
  renamed to `sales_month`.

## Known limitations / where human judgment is still required

- The dashboard itself (Power BI `.pbix` or Tableau `.twbx`) has to be
  built by hand — neither tool has a scriptable API for report creation.
- "Boosting inventory planning" and "optimizing pricing strategy" are
  decisions a merchandising/ops team makes using these numbers — the
  pipeline surfaces the data, it doesn't make or validate the business
  call.
- Branch/city names in the dataset are anonymized-style labels (WALM001,
  etc.) rather than real Walmart locations — treat all findings as
  illustrative of the analysis approach, not real operational insight.

## Tech stack

Python · MySQL 8.0 · SQLAlchemy · pandas · Power BI / Tableau (dashboard,
built manually from exports)
