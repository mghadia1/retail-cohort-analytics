"""Run the SQL analyses in DuckDB and return pandas DataFrames."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import duckdb
import pandas as pd

QUERIES = (
    "data_quality",
    "monthly_kpis",
    "cohort_retention",
    "rfm",
    "revenue_concentration",
    "returns_by_country",
)


def _sql(name: str) -> str:
    return resources.files("retail_analytics").joinpath("sql", f"{name}.sql").read_text()


def connect(source: Path | pd.DataFrame) -> duckdb.DuckDBPyConnection:
    """Open an in-memory database with `raw_lines` bound to a parquet file or DataFrame."""
    con = duckdb.connect()
    if isinstance(source, pd.DataFrame):
        con.register("raw_lines", source)
    else:
        con.read_parquet(str(source)).create_view("raw_lines")
    con.execute(_sql("00_views"))
    return con


def run(con: duckdb.DuckDBPyConnection, name: str) -> pd.DataFrame:
    if name not in QUERIES:
        raise KeyError(f"unknown query {name!r}; choose from {QUERIES}")
    return con.execute(_sql(name)).df()


def retention_matrix(cohorts: pd.DataFrame, mask_partial: bool = True) -> pd.DataFrame:
    """Pivot the long cohort table to cohort_month x months_since retention."""
    frame = cohorts
    if mask_partial:
        frame = frame[~frame["is_partial_period"]]
    return frame.pivot(index="cohort_month", columns="months_since", values="retention")


def weighted_retention(cohorts: pd.DataFrame, months_since: int, skip_first_cohort: bool = True) -> float:
    """Cohort-size-weighted retention at one offset, over cohorts that reach it.

    The first cohort is skipped by default: the extract starts 2009-12-01, so
    every returning customer who shopped before then is miscounted as "new"
    that month, which makes the first cohort look far more loyal than it is.
    """
    frame = cohorts[(cohorts["months_since"] == months_since) & ~cohorts["is_partial_period"]]
    if skip_first_cohort:
        frame = frame[frame["cohort_month"] != cohorts["cohort_month"].min()]
    if frame.empty:
        return float("nan")
    return float(frame["active_customers"].sum() / frame["cohort_size"].sum())
