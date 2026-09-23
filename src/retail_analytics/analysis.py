"""Run the SQL analyses in DuckDB and return pandas DataFrames."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import duckdb
import pandas as pd

QUERIES = (
    "data_quality",
    "monthly_kpis",
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

