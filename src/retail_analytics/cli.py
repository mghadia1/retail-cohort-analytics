"""Command line: `retail-analytics download | prepare | analyze`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from retail_analytics import analysis, charts, data


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="retail-analytics")
    sub = parser.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download", help="fetch and checksum the UCI workbook")
    dl.add_argument("--destination", type=Path, default=Path("data/raw"))

    prep = sub.add_parser("prepare", help="convert the workbook to parquet, removing the sheet overlap")
    prep.add_argument("--workbook", type=Path, default=Path("data/raw") / data.WORKBOOK_NAME)
    prep.add_argument("--out", type=Path, default=Path("data/retail.parquet"))

    an = sub.add_parser("analyze", help="run the data-quality audit and monthly KPIs; write CSVs, a chart, and a summary")
    an.add_argument("--data", type=Path, default=Path("data/retail.parquet"))
    an.add_argument("--out", type=Path, default=Path("outputs"))

    args = parser.parse_args(argv)
    if args.command == "download":
        print(data.download(args.destination))
    elif args.command == "prepare":
        print(json.dumps(data.prepare(args.workbook, args.out), indent=2))
    else:
        print(json.dumps(analyze(args.data, args.out), indent=2))


def analyze(parquet: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    con = analysis.connect(parquet)
    results = {name: analysis.run(con, name) for name in analysis.QUERIES}
    for name, frame in results.items():
        frame.to_csv(out / f"{name}.csv", index=False)

    kpis = results["monthly_kpis"]
    charts.monthly_revenue(kpis, out / "monthly_revenue.png")

    summary = {
        "sale_lines": int(con.execute("SELECT count(*) FROM sales").fetchone()[0]),
        "identified_customers": int(con.execute("SELECT count(DISTINCT customer_id) FROM customer_sales").fetchone()[0]),
        "merchandise_revenue": round(float(kpis["revenue"].sum()), 2),
        "months": int(len(kpis)),
        "partial_months": [str(m.date()) for m in kpis.loc[kpis["is_partial_month"], "order_month"]],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
