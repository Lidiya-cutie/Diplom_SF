from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from oilwells.config import BusinessConfig


def profit_from_top_wells(
    predictions: pd.Series,
    target: pd.Series,
    cfg: BusinessConfig,
) -> float:
    data = pd.DataFrame({"predictions": predictions, "target": target})
    selected = data.sort_values("predictions", ascending=False).head(cfg.wells_target)
    return float(selected["target"].sum() * cfg.product_revenue - cfg.budget)


def profit_random_wells(
    target: pd.Series,
    cfg: BusinessConfig,
    rng: np.random.RandomState,
) -> float:
    """Baseline: pick wells_target random wells from the sampled pool (by position)."""
    n = len(target)
    take = min(cfg.wells_target, n)
    idx = rng.choice(n, size=take, replace=False)
    return float(target.iloc[idx].sum() * cfg.product_revenue - cfg.budget)


def bootstrap_profits(
    predictions: pd.Series,
    target: pd.Series,
    cfg: BusinessConfig,
    mode: str = "model",
) -> pd.Series:
    """
    mode=model: top wells_target by prediction inside each bootstrap pool.
    mode=random: random wells_target inside each bootstrap pool (baseline).
    Sampling uses positions (iloc) so replace=True cannot break label alignment.
    """
    state = np.random.RandomState(cfg.random_state)
    n = len(target)
    profits: list[float] = []
    for _ in range(cfg.n_bootstrap):
        idx = state.randint(0, n, size=cfg.wells_pool)
        pred_sub = predictions.iloc[idx].reset_index(drop=True)
        target_sub = target.iloc[idx].reset_index(drop=True)
        if mode == "model":
            profits.append(profit_from_top_wells(pred_sub, target_sub, cfg))
        elif mode == "random":
            # independent RNG stream derived from state for within-pool random picks
            profits.append(profit_random_wells(target_sub, cfg, state))
        else:
            raise ValueError(mode)
    return pd.Series(profits)


def summarize_profits(profits: pd.Series, cfg: BusinessConfig) -> dict[str, Any]:
    lower = float(profits.quantile(0.025))
    upper = float(profits.quantile(0.975))
    mean = float(profits.mean())
    loss_prob = float((profits < 0).mean())
    return {
        "mean_profit": mean,
        "mean_profit_mln": mean / 1e6,
        "ci_low": lower,
        "ci_high": upper,
        "ci_low_mln": lower / 1e6,
        "ci_high_mln": upper / 1e6,
        "loss_prob": loss_prob,
        "passes_risk_gate": loss_prob < cfg.loss_threshold,
    }
