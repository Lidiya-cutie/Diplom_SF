from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from oilwells.config import BusinessConfig


FEATURE_COLS = ("f0", "f1", "f2")


def train_and_predict(
    df: pd.DataFrame,
    cfg: BusinessConfig,
) -> tuple[pd.Series, pd.Series, dict[str, Any]]:
    """Fit LinearRegression on train; return valid predictions/targets + metrics."""
    work = df.copy()
    if "id" in work.columns:
        work = work.drop(columns=["id"])

    features = work.drop(columns=["product"])
    target = work["product"]

    x_train, x_valid, y_train, y_valid = train_test_split(
        features,
        target,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
    )

    scaler = StandardScaler()
    x_train_s = scaler.fit_transform(x_train)
    x_valid_s = scaler.transform(x_valid)

    model = LinearRegression()
    model.fit(x_train_s, y_train)
    pred = pd.Series(model.predict(x_valid_s), index=x_valid.index, name="prediction")

    metrics = {
        "rmse": float(mean_squared_error(y_valid, pred) ** 0.5),
        "r2": float(r2_score(y_valid, pred)),
        "mean_fact_valid": float(y_valid.mean()),
        "mean_pred_valid": float(pred.mean()),
        "n_train": int(len(y_train)),
        "n_valid": int(len(y_valid)),
        "coef": {
            col: float(coef)
            for col, coef in zip(features.columns, model.coef_)
        },
        "intercept": float(model.intercept_),
    }

    pred = pred.reset_index(drop=True)
    y_valid = y_valid.reset_index(drop=True)
    return pred, y_valid, metrics
