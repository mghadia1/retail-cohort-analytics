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

    an = sub.add_parser("analyze", help="run every SQL analysis and write CSVs, charts, and a summary")
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

    cohorts = results["cohort_retention"]
    rfm = results["rfm"]
    kpis = results["monthly_kpis"]
    concentration = results["revenue_concentration"].set_index("top_pct")["revenue_share_pct"]
    first = cohorts["cohort_month"].min()
    first_cohort_m1 = cohorts[(cohorts["cohort_month"] == first) & (cohorts["months_since"] == 1)]

    charts.monthly_revenue(kpis, out / "monthly_revenue.png")
    charts.retention_heatmap(analysis.retention_matrix(cohorts), out / "retention_heatmap.png")
    charts.rfm_segments(rfm, out / "rfm_segments.png")

    summary = {
        "sale_lines": int(con.execute("SELECT count(*) FROM sales").fetchone()[0]),
        "identified_customers": int(rfm["customer_id"].nunique()),
        "merchandise_revenue": round(float(kpis["revenue"].sum()), 2),
        "month1_retention_weighted_excl_first_cohort": round(analysis.weighted_retention(cohorts, 1), 4),
        "month3_retention_weighted_excl_first_cohort": round(analysis.weighted_retention(cohorts, 3), 4),
        "month12_retention_weighted_excl_first_cohort": round(analysis.weighted_retention(cohorts, 12), 4),
        "first_cohort_month1_retention": round(float(first_cohort_m1["retention"].iloc[0]), 4),
        "top_10pct_customer_revenue_share": float(concentration.loc[10]),
        "top_20pct_customer_revenue_share": float(concentration.loc[20]),
        "rfm_segments": rfm["segment"].value_counts().to_dict(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
