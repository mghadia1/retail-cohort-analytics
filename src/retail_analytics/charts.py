"""Matplotlib figures for the README and results document."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

INK = "#1f2937"
ACCENT = "#2563eb"
MUTED = "#9ca3af"


def monthly_revenue(kpis: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 3.6))
    colors = [MUTED if partial else ACCENT for partial in kpis["is_partial_month"]]
    ax.bar(pd.to_datetime(kpis["order_month"]), kpis["revenue"] / 1e3, width=20, color=colors)
    ax.set_ylabel("Merchandise revenue (£ thousands)")
    ax.set_title("Monthly revenue, Dec 2009 - Dec 2011 (grey = partial month)", loc="left", color=INK)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def retention_heatmap(matrix: pd.DataFrame, path: Path, max_months: int = 12) -> None:
    data = matrix.loc[:, [c for c in matrix.columns if 1 <= c <= max_months]].dropna(how="all")
    fig, ax = plt.subplots(figsize=(9, 7))
    image = ax.imshow(data.to_numpy() * 100, cmap="Blues", aspect="auto", vmin=0, vmax=50)
    ax.set_xticks(range(len(data.columns)), [str(c) for c in data.columns])
    labels = [pd.Timestamp(m).strftime("%Y-%m") for m in data.index]
    ax.set_yticks(range(len(labels)), labels, fontsize=8)
    ax.set_xlabel("Months since first purchase")
    ax.set_title("Share of each cohort buying again (%)", loc="left", color=INK)
    for (row, col), value in pd.DataFrame(data.to_numpy()).stack().items():
        if pd.isna(value):
            continue
        ax.text(col, row, f"{value * 100:.0f}", ha="center", va="center", fontsize=6,
                color="white" if value > 0.3 else INK)
    fig.colorbar(image, ax=ax, fraction=0.03)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def rfm_segments(rfm: pd.DataFrame, path: Path) -> None:
    summary = (
        rfm.groupby("segment")
        .agg(customers=("customer_id", "count"), revenue=("monetary", "sum"))
        .sort_values("revenue")
    )
    share = summary / summary.sum() * 100
    fig, ax = plt.subplots(figsize=(8, 3.6))
    y = range(len(share))
    ax.barh([i + 0.2 for i in y], share["customers"], height=0.4, color=MUTED, label="% of customers")
    ax.barh([i - 0.2 for i in y], share["revenue"], height=0.4, color=ACCENT, label="% of revenue")
    ax.set_yticks(list(y), share.index)
    ax.set_xlabel("Percent")
    ax.set_title("RFM segments: customers vs revenue", loc="left", color=INK)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
