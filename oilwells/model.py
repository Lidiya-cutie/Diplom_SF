from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from oilwells.config import BusinessConfig
from oilwells.models_ext import ModelKind, build_model


def train_and_predict(
    df: pd.DataFrame,
    cfg: BusinessConfig,
    model_kind: ModelKind | str = ModelKind.LR,
) -> tuple[pd.Series, pd.Series, dict[str, Any]]:
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

    model, needs_scaling = build_model(model_kind, random_state=cfg.random_state)
    kind = ModelKind(model_kind)

    if needs_scaling or kind == ModelKind.LR:
        scaler = StandardScaler()
        x_train_m = scaler.fit_transform(x_train)
        x_valid_m = scaler.transform(x_valid)
    else:
        x_train_m, x_valid_m = x_train, x_valid

    model.fit(x_train_m, y_train)
    pred = pd.Series(model.predict(x_valid_m), index=x_valid.index, name="prediction")

    metrics: dict[str, Any] = {
        "model_kind": kind.value,
        "official_path": kind == ModelKind.LR,
        "rmse": float(mean_squared_error(y_valid, pred) ** 0.5),
        "r2": float(r2_score(y_valid, pred)),
        "mean_fact_valid": float(y_valid.mean()),
        "mean_pred_valid": float(pred.mean()),
        "n_train": int(len(y_train)),
        "n_valid": int(len(y_valid)),
    }
    if hasattr(model, "coef_"):
        metrics["coef"] = {
            col: float(coef) for col, coef in zip(features.columns, model.coef_)
        }
        metrics["intercept"] = float(getattr(model, "intercept_", 0.0))

    return pred.reset_index(drop=True), y_valid.reset_index(drop=True), metrics
