"""Hand-checkable fixtures for the cleaning rules and each analysis.

Every expected number here can be worked out on paper from the rows below; none
of it depends on the real dataset, so the suite runs offline in CI.
"""

from __future__ import annotations

import pandas as pd
import pytest

from retail_analytics import analysis, data


def line(invoice, code, qty, ts, price, customer, country="United Kingdom"):
    return {
        "invoice": invoice,
        "stock_code": code,
        "description": "item",
        "quantity": qty,
        "invoice_date": pd.Timestamp(ts),
        "price": price,
        "customer_id": customer,
        "country": country,
    }


@pytest.fixture
def raw() -> pd.DataFrame:
    rows = [
        # customer 1: Jan cohort, buys again in Feb and Mar
        line("100", "85123A", 2, "2011-01-05", 10.0, 1),
        line("101", "22423", 1, "2011-02-10", 20.0, 1),
        line("102", "22423", 1, "2011-03-10", 20.0, 1),
        # customer 2: Jan cohort, never returns
        line("103", "22423", 4, "2011-01-20", 5.0, 2),
        # customer 3: Feb cohort, returns in Mar
        line("104", "15056bl", 3, "2011-02-01", 10.0, 3, "France"),
        line("105", "15056bl", 1, "2011-03-31", 10.0, 3, "France"),
        # anonymous sale: counts toward revenue, not toward customers
        line("106", "22423", 1, "2011-03-15", 50.0, None),
        # rows every rule must remove
        line("C107", "22423", -1, "2011-02-11", 20.0, 1),   # cancellation
        line("108", "POST", 1, "2011-01-05", 18.0, 1),      # postage
        line("109", "DCGS0058", 1, "2011-01-05", 3.0, 1),   # gift-shop channel
        line("110", "22423", 0, "2011-01-05", 20.0, 1),     # zero quantity
        line("111", "22423", 5, "2011-01-05", 0.0, 1),      # zero price
    ]
    frame = pd.DataFrame(rows)
    frame["customer_id"] = frame["customer_id"].astype("Int64")
    return frame


@pytest.fixture
def con(raw):
    return analysis.connect(raw)


def test_cleaning_rules_keep_only_merchandise_sales(con):
    kept = con.execute("SELECT invoice FROM sales ORDER BY invoice").df()["invoice"].tolist()
    assert kept == ["100", "101", "102", "103", "104", "105", "106"]


def test_data_quality_counts_each_rule_once(con):
    dq = analysis.run(con, "data_quality").set_index("rule")["lines"]
    assert dq.sum() == 12
    assert dq["1 cancellation line"] == 1
    assert dq["2 non-merchandise code (postage, fees, adjustments)"] == 2
    assert dq["3 non-positive quantity"] == 1
    assert dq["4 non-positive price"] == 1
    assert dq["5 kept as a sale"] == 7


def test_monthly_kpis(con):
    kpis = analysis.run(con, "monthly_kpis").set_index("order_month")
    jan, feb, mar = (kpis.loc[pd.Timestamp(m)] for m in ("2011-01-01", "2011-02-01", "2011-03-01"))
    assert jan["revenue"] == pytest.approx(40.0)        # 2*10 + 4*5
    assert feb["revenue"] == pytest.approx(50.0)        # 20 + 3*10
    assert mar["revenue"] == pytest.approx(80.0)        # 20 + 10 + 50
    assert mar["orders"] == 3
    assert mar["identified_customers"] == 2             # anonymous buyer not counted
    assert mar["anonymous_revenue_pct"] == pytest.approx(62.5)
    # data ends 2011-03-31, so March is complete; it starts 2011-01-05, so January is partial
    assert not mar["is_partial_month"]
    assert jan["is_partial_month"]


def test_unknown_query_is_rejected(con):
    with pytest.raises(KeyError):
        analysis.run(con, "DROP TABLE lines")


def _sheet(rows):
    return pd.DataFrame(rows, columns=["Invoice", "StockCode", "Quantity", "InvoiceDate", "Price"])


def test_sheet_overlap_is_removed_once():
    first = _sheet([
        ["1", "22423", 1, pd.Timestamp("2010-11-30"), 1.0],
        ["2", "22423", 1, pd.Timestamp("2010-12-02"), 1.0],
    ])
    second = _sheet([
        ["2", "22423", 1, pd.Timestamp("2010-12-02"), 1.0],
        ["3", "22423", 1, pd.Timestamp("2010-12-20"), 1.0],
    ])
    combined, removed = data.combine_sheets(first, second)
    assert removed == 1
    assert combined["Invoice"].tolist() == ["1", "2", "3"]


def test_sheet_overlap_mismatch_refuses():
    first = _sheet([["2", "22423", 1, pd.Timestamp("2010-12-02"), 1.0]])
    second = _sheet([["2", "22423", 9, pd.Timestamp("2010-12-02"), 1.0]])
    with pytest.raises(ValueError, match="not an exact duplicate"):
        data.combine_sheets(first, second)


def test_checksum_mismatch_is_rejected(tmp_path):
    (tmp_path / data.WORKBOOK_NAME).write_bytes(b"not the workbook")
    with pytest.raises(ValueError, match="checksum mismatch"):
        data.download(tmp_path)
