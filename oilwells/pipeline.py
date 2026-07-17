from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from oilwells.config import BusinessConfig
from oilwells.dashboard import build_dashboard_html
from oilwells.data import apply_duplicate_id_policy, load_all_regions
from oilwells.dq import audit_all
from oilwells.model import train_and_predict
from oilwells.models_ext import ModelKind, OFFICIAL_MODEL
from oilwells.profit import (
    bootstrap_profits,
    profit_from_top_wells,
    summarize_profits,
)
from oilwells.risk import var_cvar
from oilwells.sensitivity import run_sensitivity
from oilwells.tracking import dump_runs_json, log_region_run, setup_mlflow


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


def _evaluate_region(
    name: str,
    df: pd.DataFrame,
    cfg: BusinessConfig,
    model_kind: ModelKind | str,
) -> tuple[dict[str, Any], pd.Series]:
    pred, target, metrics = train_and_predict(df, cfg, model_kind=model_kind)
    point = profit_from_top_wells(pred, target, cfg)
    model_profits = bootstrap_profits(pred, target, cfg, mode="model")
    random_profits = bootstrap_profits(pred, target, cfg, mode="random")
    model_summary = summarize_profits(model_profits, cfg)
    random_summary = summarize_profits(random_profits, cfg)
    risk = var_cvar(model_profits, alpha=0.05)
    row = {
        "region": name,
        "model_kind": ModelKind(model_kind).value,
        "official_path": ModelKind(model_kind) == OFFICIAL_MODEL,
        "model_metrics": metrics,
        "point_profit": point,
        "point_profit_bln": point / 1e9,
        "bootstrap_model": model_summary,
        "bootstrap_random_baseline": random_summary,
        "lift_vs_random_mln": model_summary["mean_profit_mln"] - random_summary["mean_profit_mln"],
        "risk": risk,
    }
    return row, model_profits


def run_pipeline(
    data_dir: Path,
    out_dir: Path,
    cfg: BusinessConfig | None = None,
    *,
    model_kinds: Sequence[str] | None = None,
    include_sensitivity: bool = True,
    sensitivity_bootstrap: int = 400,
    mlflow_uri: str | Path | None = None,
    build_dashboard: bool = True,
) -> dict[str, Any]:
    cfg = cfg or BusinessConfig()
    kinds = [ModelKind(k) for k in (model_kinds or [ModelKind.LR.value])]
    regions, policy_info = prepare_regions(data_dir, cfg)
    dq = audit_all(regions)

    if mlflow_uri is None:
        mlflow_uri = out_dir / "mlruns"
    setup_mlflow(mlflow_uri)

    all_results: list[dict[str, Any]] = []
    profit_samples: dict[str, pd.Series] = {}

    for kind in kinds:
        for name, df in regions.items():
            row, profits = _evaluate_region(name, df, cfg, kind)
            all_results.append(row)
            key = f"{name}::{kind.value}"
            profit_samples[key] = profits

            metrics_flat = {
                "rmse": row["model_metrics"]["rmse"],
                "r2": row["model_metrics"]["r2"],
                "mean_profit_mln": row["bootstrap_model"]["mean_profit_mln"],
                "loss_prob": row["bootstrap_model"]["loss_prob"],
                "lift_vs_random_mln": row["lift_vs_random_mln"],
                "var_5_mln": row["risk"]["var_mln"],
                "cvar_5_mln": row["risk"]["cvar_mln"],
            }
            log_region_run(
                region=name,
                model_kind=kind.value,
                params={**cfg.to_dict(), "model_kind": kind.value},
                metrics=metrics_flat,
                tags={
                    "official_path": str(kind == OFFICIAL_MODEL),
                    "dq_critical": str(name in dq.get("critical_regions", [])),
                },
            )

    results_df = pd.DataFrame(
        [
            {
                "region": r["region"],
                "model_kind": r["model_kind"],
                "official_path": r["official_path"],
                "rmse": r["model_metrics"]["rmse"],
                "r2": r["model_metrics"]["r2"],
                "mean_profit_mln": r["bootstrap_model"]["mean_profit_mln"],
                "loss_prob": r["bootstrap_model"]["loss_prob"],
                "passes_risk_gate": r["bootstrap_model"]["passes_risk_gate"],
                "cvar_5_mln": r["risk"]["cvar_mln"],
                "var_5_mln": r["risk"]["var_mln"],
                "random_mean_profit_mln": r["bootstrap_random_baseline"]["mean_profit_mln"],
                "lift_vs_random_mln": r["lift_vs_random_mln"],
            }
            for r in all_results
        ]
    ).sort_values(["official_path", "mean_profit_mln"], ascending=[False, False])

    official = results_df[results_df["official_path"]]
    eligible = official[official["passes_risk_gate"]]
    recommendation = None
    if not eligible.empty:
        best = eligible.iloc[0]
        recommendation = {
            "region": best["region"],
            "model_kind": best["model_kind"],
            "mean_profit_mln": float(best["mean_profit_mln"]),
            "loss_prob": float(best["loss_prob"]),
            "cvar_5_mln": float(best["cvar_5_mln"]),
            "caveat": (
                "Region flagged critical in DQ — validate data source before business decision."
                if best["region"] in dq.get("critical_regions", [])
                else None
            ),
        }

    payload: dict[str, Any] = {
        "config": cfg.to_dict(),
        "model_kinds": [k.value for k in kinds],
        "policy": policy_info,
        "dq_summary": {
            "critical_regions": dq["critical_regions"],
            "summary": dq["summary"],
        },
        "regions": all_results,
        "leaderboard": results_df.to_dict(orient="records"),
        "recommendation": recommendation,
        "mlflow_tracking_uri": str(mlflow_uri),
    }

    if include_sensitivity:
        # sensitivity stays on official LR path
        payload["sensitivity"] = run_sensitivity(
            regions,
            cfg,
            n_bootstrap=sensitivity_bootstrap,
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "pipeline_report.json", payload)
    _write_json(out_dir / "dq_report.json", dq)
    results_df.to_csv(out_dir / "leaderboard.csv", index=False)
    dump_runs_json(mlflow_uri, out_dir / "mlflow_runs.json")

    if build_dashboard:
        # dashboard focuses on official LR rows when available
        dash_lb = official if not official.empty else results_df
        cvar_df = dash_lb[["region", "cvar_5_mln", "var_5_mln"]].drop_duplicates("region")
        samples = {
            r: profit_samples[f"{r}::{ModelKind.LR.value}"]
            for r in dash_lb["region"].unique()
            if f"{r}::{ModelKind.LR.value}" in profit_samples
        }
        if not samples:
            samples = {k: v for k, v in list(profit_samples.items())[:3]}
        build_dashboard_html(
            dash_lb.rename(columns={"mean_profit_mln": "mean_profit_mln"}),
            samples,
            cvar_df.rename(columns={"cvar_5_mln": "cvar_mln"}),
            out_dir / "dashboard.html",
        )
        payload["dashboard"] = str(out_dir / "dashboard.html")

    return payload


def run_smoke(
    data_dir: Path,
    out_dir: Path,
    subsample: int = 8000,
) -> dict[str, Any]:
    cfg = BusinessConfig(n_bootstrap=200)
    regions, policy_info = prepare_regions(data_dir, cfg)
    # If already small samples dir, don't resample below length
    small = {
        name: df if len(df) <= subsample else df.sample(n=subsample, random_state=cfg.random_state)
        for name, df in regions.items()
    }
    dq = audit_all(regions)
    region_results = []
    for name, df in small.items():
        for kind in (ModelKind.LR, ModelKind.ELASTICNET):
            pred, target, metrics = train_and_predict(df, cfg, model_kind=kind)
            profits = bootstrap_profits(pred, target, cfg, mode="model")
            model_summary = summarize_profits(profits, cfg)
            risk = var_cvar(profits, alpha=0.05)
            region_results.append(
                {
                    "region": name,
                    "model_kind": kind.value,
                    "rmse": metrics["rmse"],
                    "r2": metrics["r2"],
                    "loss_prob": model_summary["loss_prob"],
                    "cvar_5_mln": risk["cvar_mln"],
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
    assert "region_1" in dq["critical_regions"], "expected geo_data_1 critical DQ flags"
    assert any(r["model_kind"] == "elasticnet" for r in region_results)
    return payload
