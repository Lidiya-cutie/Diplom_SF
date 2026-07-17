from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from oilwells.config import BusinessConfig
from oilwells.data import apply_duplicate_id_policy, load_all_regions
from oilwells.dq import audit_all
from oilwells.model import train_and_predict
from oilwells.profit import (
    bootstrap_profits,
    profit_from_top_wells,
    summarize_profits,
)
from oilwells.sensitivity import run_sensitivity


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_regions(
    data_dir: Path,
    cfg: BusinessConfig,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    raw = load_all_regions(data_dir)
    prepared: dict[str, pd.DataFrame] = {}
    policy_meta: dict[str, Any] = {}
    for name, df in raw.items():
        cleaned, meta = apply_duplicate_id_policy(df, cfg.duplicate_id_policy)
        prepared[name] = cleaned
        policy_meta[name] = meta
    return prepared, {"duplicate_id_policy": policy_meta}


def run_dq(data_dir: Path, out_dir: Path) -> dict[str, Any]:
    regions = load_all_regions(data_dir)
    report = audit_all(regions)
    _write_json(out_dir / "dq_report.json", report)
    return report


def run_pipeline(
    data_dir: Path,
    out_dir: Path,
    cfg: BusinessConfig | None = None,
    *,
    include_sensitivity: bool = True,
    sensitivity_bootstrap: int = 400,
) -> dict[str, Any]:
    cfg = cfg or BusinessConfig()
    regions, policy_info = prepare_regions(data_dir, cfg)
    dq = audit_all(regions)

    region_results: list[dict[str, Any]] = []
    for name, df in regions.items():
        pred, target, metrics = train_and_predict(df, cfg)
        point = profit_from_top_wells(pred, target, cfg)
        model_profits = bootstrap_profits(pred, target, cfg, mode="model")
        random_profits = bootstrap_profits(pred, target, cfg, mode="random")
        model_summary = summarize_profits(model_profits, cfg)
        random_summary = summarize_profits(random_profits, cfg)
        lift_mln = model_summary["mean_profit_mln"] - random_summary["mean_profit_mln"]
        region_results.append(
            {
                "region": name,
                "model_metrics": metrics,
                "point_profit": point,
                "point_profit_bln": point / 1e9,
                "bootstrap_model": model_summary,
                "bootstrap_random_baseline": random_summary,
                "lift_vs_random_mln": lift_mln,
            }
        )

    results_df = pd.DataFrame(
        [
            {
                "region": r["region"],
                "rmse": r["model_metrics"]["rmse"],
                "r2": r["model_metrics"]["r2"],
                "mean_profit_mln": r["bootstrap_model"]["mean_profit_mln"],
                "loss_prob": r["bootstrap_model"]["loss_prob"],
                "passes_risk_gate": r["bootstrap_model"]["passes_risk_gate"],
                "random_mean_profit_mln": r["bootstrap_random_baseline"]["mean_profit_mln"],
                "random_loss_prob": r["bootstrap_random_baseline"]["loss_prob"],
                "lift_vs_random_mln": r["lift_vs_random_mln"],
            }
            for r in region_results
        ]
    ).sort_values("mean_profit_mln", ascending=False)

    eligible = results_df[results_df["passes_risk_gate"]]
    recommendation = None
    if not eligible.empty:
        best = eligible.iloc[0]
        recommendation = {
            "region": best["region"],
            "mean_profit_mln": float(best["mean_profit_mln"]),
            "loss_prob": float(best["loss_prob"]),
            "caveat": (
                "Region flagged critical in DQ — validate data source before business decision."
                if best["region"] in dq.get("critical_regions", [])
                else None
            ),
        }

    payload: dict[str, Any] = {
        "config": cfg.to_dict(),
        "policy": policy_info,
        "dq_summary": {
            "critical_regions": dq["critical_regions"],
            "summary": dq["summary"],
        },
        "regions": region_results,
        "leaderboard": results_df.to_dict(orient="records"),
        "recommendation": recommendation,
    }

    if include_sensitivity:
        payload["sensitivity"] = run_sensitivity(
            regions,
            cfg,
            n_bootstrap=sensitivity_bootstrap,
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "pipeline_report.json", payload)
    _write_json(out_dir / "dq_report.json", dq)
    results_df.to_csv(out_dir / "leaderboard.csv", index=False)
    return payload


def run_smoke(
    data_dir: Path,
    out_dir: Path,
    subsample: int = 8000,
) -> dict[str, Any]:
    """Fast CI path: subsample rows, fewer bootstrap iterations."""
    cfg = BusinessConfig(n_bootstrap=200)
    regions, policy_info = prepare_regions(data_dir, cfg)
    small = {
        name: df.sample(n=min(subsample, len(df)), random_state=cfg.random_state)
        for name, df in regions.items()
    }
    # temporary write not needed — run on small dict via local loop
    dq = audit_all(regions)  # full DQ still cheap
    region_results = []
    for name, df in small.items():
        pred, target, metrics = train_and_predict(df, cfg)
        model_summary = summarize_profits(
            bootstrap_profits(pred, target, cfg, mode="model"), cfg
        )
        random_summary = summarize_profits(
            bootstrap_profits(pred, target, cfg, mode="random"), cfg
        )
        region_results.append(
            {
                "region": name,
                "rmse": metrics["rmse"],
                "r2": metrics["r2"],
                "loss_prob": model_summary["loss_prob"],
                "random_loss_prob": random_summary["loss_prob"],
                "passes_risk_gate": model_summary["passes_risk_gate"],
            }
        )
    payload = {
        "mode": "smoke",
        "subsample": subsample,
        "config": cfg.to_dict(),
        "policy": policy_info,
        "dq_critical_regions": dq["critical_regions"],
        "regions": region_results,
    }
    _write_json(out_dir / "smoke_report.json", payload)
    # hard asserts for CI
    assert "region_1" in dq["critical_regions"], "expected geo_data_1 critical DQ flags"
    assert all("rmse" in r for r in region_results)
    return payload
