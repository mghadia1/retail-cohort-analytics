# How it works

## Pipeline

```
UCI zip ──download──▶ online_retail_II.xlsx ──prepare──▶ data/retail.parquet ──analyze──▶ outputs/
          (SHA-256)     2 sheets, 1,067,371 lines   (overlap removed,        (DuckDB SQL → CSV,
                                                     1,044,848 lines)          PNG, summary.json)
```

1. **download** (`data.py`) fetches the archive, extracts the workbook, and checks it against a pinned SHA-256. A different file fails loudly instead of silently producing different numbers.
2. **prepare** (`data.py`) reads both sheets with every text column forced to string. Some product descriptions are bare numbers, which otherwise break the parquet write. It then calls `combine_sheets`, which:
   - takes the first sheet's rows on or after 2010-12-01 and the second sheet's rows up to the first sheet's last timestamp,
   - sorts both on invoice, stock code, quantity, timestamp, and price, and requires them to be *identical*,
   - drops the first sheet's copy.
   If the windows differ, it raises instead of guessing which side is right.
3. **analyze** (`analysis.py` + `sql/`) opens an in-memory DuckDB, binds `raw_lines` to the parquet file, and runs `00_views.sql`. That file defines the cleaning rules once, as views:
   - `lines` adds `line_value`, `is_cancellation`, `is_merchandise`, and `order_month`,
   - `sales` keeps merchandise, non-cancelled lines with positive quantity and price,
   - `customer_sales` keeps sales that have a customer ID,
   - `merchandise_returns` keeps cancelled merchandise lines.
   Each analysis is one `.sql` file that reads those views. Changing a cleaning rule therefore changes every analysis consistently, and there is nowhere for two notebooks to disagree.

## Why SQL files, not pandas

Most of this could be written in pandas. Keeping it in SQL has three benefits:
- the queries are the portable artifact, and would run on Postgres, BigQuery, or Snowflake with small dialect changes,
- DuckDB scans the parquet file directly, so the full analysis takes about 2 seconds,
- the same views are reused by tests, which bind a 12-row DataFrame to `raw_lines` instead of the parquet file.

`analysis.run` only accepts names in `QUERIES`, so the CLI can never be pointed at an arbitrary string of SQL.

## The analyses

| File | Question | Key technique |
|---|---|---|
| `data_quality.sql` | What did each cleaning rule remove? | ordered `CASE` so each line counts once |
| `monthly_kpis.sql` | Revenue, orders, customers, AOV per month | `FILTER` aggregates; partial-month flag |
| `cohort_retention.sql` | What share of each monthly cohort buys again *k* months later? | first-purchase CTE, `date_diff('month')`, partial-period flag |
| `rfm.sql` | Recency / frequency / monetary scores and segments | `percent_rank` window functions |
| `revenue_concentration.sql` | Share of revenue from the top X% of customers | `row_number` over revenue, join to cut-offs |
| `returns_by_country.sql` | Returned value / gross sales by country | `LEFT JOIN` of two aggregates |

## Tests (13)

`tests/test_analysis.py` builds a 12-row fixture where every expected answer can be worked out by hand: three customers across three months, one anonymous sale, and one row for each cleaning rule. The tests cover:
- each cleaning rule,
- monthly KPIs,
- cohort retention, and the partial-final-month flag,
- skipping the left-censored first cohort,
- RFM recency, and tied frequencies sharing a score,
- revenue concentration,
- rejection of an unknown query name,
- sheet-overlap removal, and refusal when the overlap is not identical,
- checksum rejection.

None of them need the real dataset.

## Things to be able to explain

These are prompts, not answers. The answers should be in my own words:
- Why is the December 2009 cohort's retention not comparable to the others?
- Why `percent_rank` and not `NTILE` for the RFM scores?
- What would change if within-sheet duplicate lines were deleted?
- Why is Spain's 13% return rate not a finding?
