"""Download, verify, and prepare the UCI Online Retail II workbook.

The workbook ships as two sheets ("Year 2009-2010" and "Year 2010-2011"). They
overlap: every line from 2010-12-01 to 2010-12-09 appears in both. Stacking the
sheets naively double-counts that week, so `prepare` proves the overlap is
identical and then keeps one copy.
"""

from __future__ import annotations

import hashlib
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

DATASET_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
WORKBOOK_NAME = "online_retail_II.xlsx"
# SHA-256 of the extracted workbook, recorded 2026-09-22. The zip is hashed
# indirectly: if UCI re-zips the same workbook the check still passes.
WORKBOOK_SHA256 = "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980"

OVERLAP_START = pd.Timestamp("2010-12-01")
TEXT_COLUMNS = {"Invoice": str, "StockCode": str, "Description": str, "Country": str}
KEY_COLUMNS = ["Invoice", "StockCode", "Quantity", "InvoiceDate", "Price"]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(destination: Path) -> Path:
    """Fetch the archive, extract the workbook, and verify its checksum."""
    destination.mkdir(parents=True, exist_ok=True)
    workbook = destination / WORKBOOK_NAME
    if not workbook.exists():
        archive = destination / "online_retail_ii.zip"
        urllib.request.urlretrieve(DATASET_URL, archive)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extract(WORKBOOK_NAME, destination)
        archive.unlink()
    actual = sha256_of(workbook)
    if actual != WORKBOOK_SHA256:
        raise ValueError(f"checksum mismatch for {workbook}: {actual}")
    return workbook


def combine_sheets(first: pd.DataFrame, second: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Stack the two yearly sheets, dropping the duplicated overlap window once.

    Returns the combined frame and the number of overlap rows removed. Raises if
    the overlap is not an exact copy, because then silently keeping one side
    would lose real transactions.
    """
    overlap_end = first["InvoiceDate"].max()
    first_window = first[first["InvoiceDate"] >= OVERLAP_START]
    second_window = second[second["InvoiceDate"] <= overlap_end]

    def canonical(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[KEY_COLUMNS].sort_values(KEY_COLUMNS).reset_index(drop=True)

    if not canonical(first_window).equals(canonical(second_window)):
        raise ValueError("sheet overlap window is not an exact duplicate; refusing to drop it")

    kept_first = first[first["InvoiceDate"] < OVERLAP_START].assign(source_sheet=1)
    combined = pd.concat([kept_first, second.assign(source_sheet=2)], ignore_index=True)
    return combined, len(first_window)


def prepare(workbook: Path, output: Path) -> dict[str, int]:
    """Convert the workbook to one parquet file with normalised column names."""
    sheets = list(pd.read_excel(workbook, sheet_name=None, dtype=TEXT_COLUMNS).values())
    if len(sheets) != 2:
        raise ValueError(f"expected 2 sheets, found {len(sheets)}")
    combined, removed = combine_sheets(*sheets)
    combined = combined.rename(
        columns={
            "Invoice": "invoice",
            "StockCode": "stock_code",
            "Description": "description",
            "Quantity": "quantity",
            "InvoiceDate": "invoice_date",
            "Price": "price",
            "Customer ID": "customer_id",
            "Country": "country",
        }
    )
    combined["customer_id"] = combined["customer_id"].astype("Int64")
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output, index=False)
    return {"rows_written": len(combined), "overlap_rows_removed": removed}
