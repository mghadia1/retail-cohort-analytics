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

