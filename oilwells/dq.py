from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def audit_region(df: pd.DataFrame, region: str) -> dict[str, Any]:
    product = df["product"]
    features = df[["f0", "f1", "f2", "product"]]
    corr = features.corr(numeric_only=True)["product"].drop("product").to_dict()

    unique_product = int(product.nunique())
    zero_share = float((product == 0).mean())
    top_corr = max(abs(v) for v in corr.values()) if corr else 0.0

    flags: list[str] = []
    if unique_product <= 20:
        flags.append("product_near_discrete")
    if zero_share >= 0.05:
        flags.append("high_zero_product_share")
    if top_corr >= 0.98:
        flags.append("near_perfect_feature_target_corr")
    if int(df["id"].duplicated().sum()) > 0:
        flags.append("duplicate_ids")
    if df.isna().any().any():
        flags.append("missing_values")

    severity = "critical" if (
        "near_perfect_feature_target_corr" in flags and "product_near_discrete" in flags
    ) else ("warning" if flags else "ok")

    return {
        "region": region,
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_ids": int(df["id"].duplicated().sum()),
        "missing_by_column": df.isna().sum().astype(int).to_dict(),
        "product_zeros": int((product == 0).sum()),
        "product_zero_share": zero_share,
        "product_nunique": unique_product,
        "product_describe": product.describe().to_dict(),
        "corr_with_product": {k: float(v) for k, v in corr.items()},
        "max_abs_corr_with_product": float(top_corr),
        "flags": flags,
        "severity": severity,
        "recommendation": _recommendation(severity, flags, region),
    }


def _recommendation(severity: str, flags: list[str], region: str) -> str:
    if severity == "critical":
        return (
            f"{region}: target looks synthetic/leaked (discrete product + near-perfect correlation). "
            "Do not treat formal bootstrap win as business truth until source audit."
        )
    if severity == "warning":
        return f"{region}: review flags {flags} before production use."
    return f"{region}: no critical DQ flags."


def audit_all(regions: dict[str, pd.DataFrame]) -> dict[str, Any]:
    reports = [audit_region(df, name) for name, df in regions.items()]
    critical = [r["region"] for r in reports if r["severity"] == "critical"]
    return {
        "regions": reports,
        "critical_regions": critical,
        "summary": (
            f"{len(critical)} critical region(s): {', '.join(critical)}"
            if critical
            else "No critical DQ issues detected."
        ),
    }
