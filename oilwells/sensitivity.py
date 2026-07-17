from __future__ import annotations

from typing import Any

import pandas as pd

from oilwells.config import BusinessConfig
from oilwells.model import train_and_predict
from oilwells.profit import bootstrap_profits, summarize_profits


def run_sensitivity(
    regions: dict[str, pd.DataFrame],
    base: BusinessConfig,
    *,
    revenue_factors: tuple[float, ...] = (0.8, 1.0, 1.2),
    budget_factors: tuple[float, ...] = (0.8, 1.0, 1.2),
    pool_sizes: tuple[int, ...] = (300, 500, 700),
    n_bootstrap: int = 400,
) -> dict[str, Any]:
    """Grid sensitivity around business knobs (reduced bootstrap for speed)."""
    rows_list: list[dict[str, Any]] = []

    cached: dict[str, tuple[pd.Series, pd.Series]] = {}
    for name, df in regions.items():
        pred, tgt, _ = train_and_predict(df, base)
        cached[name] = (pred, tgt)

    for rev_f in revenue_factors:
        for bud_f in budget_factors:
            for pool in pool_sizes:
                cfg = BusinessConfig(
                    budget=base.budget * bud_f,
                    wells_target=base.wells_target,
                    wells_pool=pool,
                    product_revenue=base.product_revenue * rev_f,
                    loss_threshold=base.loss_threshold,
                    n_bootstrap=n_bootstrap,
                    test_size=base.test_size,
                    random_state=base.random_state,
                    duplicate_id_policy=base.duplicate_id_policy,
                )
                if cfg.wells_pool < cfg.wells_target:
                    continue
                for name, (pred, tgt) in cached.items():
                    profits = bootstrap_profits(pred, tgt, cfg, mode="model")
                    summary = summarize_profits(profits, cfg)
                    rows_list.append(
                        {
                            "region": name,
                            "revenue_factor": rev_f,
                            "budget_factor": bud_f,
                            "wells_pool": pool,
                            "product_revenue": cfg.product_revenue,
                            "budget": cfg.budget,
                            **summary,
                        }
                    )

    frame = pd.DataFrame(rows_list)
    if frame.empty:
        return {"runs": [], "pass_rate_by_region": {}}

    pass_rate = (
        frame.groupby("region")["passes_risk_gate"].mean().sort_values(ascending=False).to_dict()
    )
    return {
        "n_runs": int(len(frame)),
        "n_bootstrap_per_run": n_bootstrap,
        "pass_rate_by_region": {k: float(v) for k, v in pass_rate.items()},
        "runs": frame.to_dict(orient="records"),
    }
