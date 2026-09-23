# How it works (part 1)

## Pipeline

```
UCI zip ──download──▶ online_retail_II.xlsx ──prepare──▶ data/retail.parquet ──analyze──▶ outputs/
          (SHA-256)     2 sheets, 1,067,371 lines   (overlap removed,        (DuckDB SQL → CSV,
                                                     1,044,848 lines)          PNG, summary.json)
```

1. **download** (`data.py`) fetches the archive, extracts the workbook, and checks it against a pinned SHA-256. If the file is different, it fails loudly instead of silently producing different numbers.
2. **prepare** (`data.py`) reads both sheets with every text column forced to string. Some product descriptions are bare numbers, and those otherwise break the parquet write. It then calls `combine_sheets`, which:
   - takes the first sheet's rows on or after 2010-12-01 and the second sheet's rows up to the first sheet's last timestamp,
   - sorts both on invoice, stock code, quantity, timestamp, and price, and requires them to be *identical*,
   - drops the first sheet's copy.

   If the two windows differ, it raises an error instead of guessing which side is right.
3. **analyze** (`analysis.py` + `sql/`) opens an in-memory DuckDB, binds `raw_lines` to the parquet file, and runs `00_views.sql`. That file defines the cleaning rules once, as views:
   - `lines` adds `line_value`, `is_cancellation`, `is_merchandise`, and `order_month`;
   - `sales` keeps merchandise lines that aren't cancelled, with positive quantity and price;
   - `customer_sales` keeps sales that have a customer ID;
   - `merchandise_returns` keeps cancelled merchandise lines.

   Each analysis is one `.sql` file that reads those views. Changing a cleaning rule therefore changes every analysis consistently, and the two parts of the project cannot disagree about what a "sale" is.

## Why SQL files, not pandas

- The queries are the portable artifact: they would run on Postgres, BigQuery, or Snowflake with small dialect changes.
- DuckDB scans the parquet file directly, so the analysis takes about 2 seconds.
- The tests reuse the same views, binding a 12-row DataFrame to `raw_lines` in place of the parquet file.

`analysis.run` only accepts names listed in `QUERIES`, so the CLI can never be pointed at an arbitrary string of SQL.

## The analyses in part 1

| File | Question | Key technique |
|---|---|---|
| `data_quality.sql` | What did each cleaning rule remove? | an ordered `CASE`, so each line counts once |
| `monthly_kpis.sql` | Revenue, orders, customers, and average order value per month | `FILTER` aggregates; a partial-month flag |

## Tests (7)

`tests/test_analysis.py` builds a 12-row fixture where every expected answer can be worked out by hand. The tests cover:
- each cleaning rule;
- the monthly KPIs and the partial-month flag;
- rejection of an unknown query name;
- removal of the sheet overlap, and refusal when the overlap is not identical;
- checksum rejection.

None of them need the real dataset.

## Things to be able to explain

- Why is the sheet overlap removed only after proving the two copies identical?
- Why are within-sheet duplicate lines kept?
- Why is December 2011 flagged instead of dropped?
