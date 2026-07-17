from __future__ import annotations

from enum import Enum

from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import ElasticNet, LinearRegression


class ModelKind(str, Enum):
    """Official task constraint is LinearRegression; others are experimental."""

    LR = "lr"  # official SkillFactory path
    ELASTICNET = "elasticnet"  # experimental
    GBR = "gbr"  # experimental GradientBoosting
    HGBR = "hgbr"  # experimental HistGradientBoosting (faster)


OFFICIAL_MODEL = ModelKind.LR


def build_model(kind: ModelKind | str, random_state: int = 12345):
    kind = ModelKind(kind)
    if kind == ModelKind.LR:
        return LinearRegression(), False  # model, needs_scaling
    if kind == ModelKind.ELASTICNET:
        return ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=random_state, max_iter=5000), True
    if kind == ModelKind.GBR:
        return (
            GradientBoostingRegressor(
                random_state=random_state,
                n_estimators=120,
                max_depth=3,
                learning_rate=0.08,
            ),
            False,
        )
    if kind == ModelKind.HGBR:
        return (
            HistGradientBoostingRegressor(
                random_state=random_state,
                max_depth=6,
                learning_rate=0.08,
                max_iter=200,
            ),
            False,
        )
    raise ValueError(kind)
