# Retail Cohort Analytics

SQL-first customer analytics on about one million real e-commerce transactions, using DuckDB, pandas, and matplotlib.

> **Status: learning project, part 1 of 2 (September 2026).** This part is the foundation: a checksum-verified download, a fix for a duplicated-rows problem in the source file, cleaning rules written once in SQL, a data-quality audit, and monthly revenue KPIs. **Part 2** covers cohort retention, RFM customer segmentation, revenue concentration, and return rates. It is built on these same views and will be published next. The dataset is real, from one UK online gift wholesaler (2009–2011), so nothing here generalises to retail as a whole.

![Monthly merchandise revenue](docs/figures/monthly_revenue.png)

## Quickstart

```bash
git clone https://github.com/mghadia1/retail-cohort-analytics.git
cd retail-cohort-analytics
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[dev]'

python -m pytest -q tests                 # 7 tests, offline, hand-checkable fixtures

retail-analytics download                 # UCI archive, SHA-256 verified (~45 MB)
retail-analytics prepare                  # workbook -> parquet, removes the sheet overlap (~30 s)
retail-analytics analyze                  # data-quality audit + monthly KPIs -> outputs/ (~2 s)
```

## What part 1 found (run 2026-09-22)

| | |
|---|---|
| Lines in the source workbook | 1,067,371 across two yearly sheets |
| Lines after removing the sheet overlap | 1,044,848 |
| Kept as merchandise sales | **1,014,944** (97.14%) from 5,852 identified customers |
| Merchandise revenue | **£19.70M**, peaking every November (£1.44M in 2010, £1.46M in 2011) |

## The problem the source file had

**The two Excel sheets overlap.** Every line from 1–9 December 2010 appears in both the "2009–2010" and the "2010–2011" sheet. Stacking them naively double-counts **22,523 rows**. `prepare` proves the two copies are identical and keeps one. If they ever differ, it refuses to guess which copy is right.

The last month (December 2011) holds only 9 days of data, so it is flagged as partial instead of being read as a collapse in sales.

Details: [docs/results.md](docs/results.md) and [docs/how-it-works.md](docs/how-it-works.md).

## Dataset

[UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii), by Daqing Chen, CC BY 4.0.
