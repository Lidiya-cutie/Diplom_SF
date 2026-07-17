from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_dashboard_html(
    leaderboard: pd.DataFrame,
    region_profit_samples: dict[str, pd.Series],
    cvar_table: pd.DataFrame,
    out_path: Path,
    title: str = "Diplom SF — Oilwells Decision Dashboard",
) -> Path:
    """Static Plotly HTML dashboard (CVaR + profit distributions + leaderboard)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Bootstrap mean profit (mln RUB)",
            "Loss probability vs 2.5% gate",
            "Profit distributions",
            "CVaR 5% (mln RUB, higher=better)",
        ),
        specs=[[{"type": "bar"}, {"type": "bar"}], [{"type": "xy"}, {"type": "bar"}]],
    )

    lb = leaderboard.copy()
    fig.add_trace(
        go.Bar(x=lb["region"], y=lb["mean_profit_mln"], name="mean profit"),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(x=lb["region"], y=lb["loss_prob"] * 100, name="loss %"),
        row=1,
        col=2,
    )
    fig.add_hline(y=2.5, row=1, col=2, line_dash="dash", annotation_text="2.5%")

    for region, profits in region_profit_samples.items():
        fig.add_trace(
            go.Histogram(
                x=profits / 1e6,
                name=region,
                opacity=0.55,
                nbinsx=40,
            ),
            row=2,
            col=1,
        )

    fig.add_trace(
        go.Bar(x=cvar_table["region"], y=cvar_table["cvar_mln"], name="CVaR5%"),
        row=2,
        col=2,
    )

    fig.update_layout(
        title_text=title,
        barmode="group",
        height=900,
        legend=dict(orientation="h"),
    )
    fig.update_xaxes(title_text="profit, mln RUB", row=2, col=1)
    fig.write_html(str(out_path), include_plotlyjs="cdn")
    return out_path
