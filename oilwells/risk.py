from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def var_cvar(profits: pd.Series | np.ndarray, alpha: float = 0.05) -> dict[str, float]:
    """
    VaR/CVaR for a profit distribution (higher is better).

    VaR_alpha = empirical alpha-quantile of profits.
    CVaR_alpha = mean of profits at or below VaR_alpha (tail expectation).
    """
    s = pd.Series(profits, dtype=float).dropna().sort_values()
    if s.empty:
        return {"alpha": alpha, "var": float("nan"), "cvar": float("nan"), "tail_n": 0}
    var = float(s.quantile(alpha))
    tail = s[s <= var]
    if tail.empty:
        tail = s.iloc[: max(1, int(np.ceil(alpha * len(s))))]
    return {
        "alpha": float(alpha),
        "var": var,
        "var_mln": var / 1e6,
        "cvar": float(tail.mean()),
        "cvar_mln": float(tail.mean()) / 1e6,
        "tail_n": int(len(tail)),
    }
