from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient


def setup_mlflow(tracking_uri: str | Path, experiment: str = "diplom-sf-oilwells") -> str:
    uri = str(tracking_uri)
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment)
    return uri


def log_region_run(
    *,
    region: str,
    model_kind: str,
    params: dict[str, Any],
    metrics: dict[str, float],
    artifacts: dict[str, Path] | None = None,
    tags: dict[str, str] | None = None,
) -> str:
    with mlflow.start_run(run_name=f"{region}-{model_kind}") as run:
        mlflow.set_tags({"region": region, "model_kind": model_kind, **(tags or {})})
        mlflow.log_params({k: str(v) for k, v in params.items()})
        mlflow.log_metrics({k: float(v) for k, v in metrics.items() if v is not None and v == v})
        for name, path in (artifacts or {}).items():
            if path.exists():
                mlflow.log_artifact(str(path), artifact_path=name)
        return run.info.run_id


def latest_experiment_runs(tracking_uri: str | Path, experiment: str = "diplom-sf-oilwells") -> list[dict[str, Any]]:
    setup_mlflow(tracking_uri, experiment)
    client = MlflowClient()
    exp = client.get_experiment_by_name(experiment)
    if exp is None:
        return []
    runs = client.search_runs([exp.experiment_id], order_by=["attributes.start_time DESC"], max_results=50)
    out = []
    for r in runs:
        out.append(
            {
                "run_id": r.info.run_id,
                "run_name": r.info.run_name,
                "status": r.info.status,
                "params": dict(r.data.params),
                "metrics": dict(r.data.metrics),
                "tags": dict(r.data.tags),
            }
        )
    return out


def dump_runs_json(tracking_uri: str | Path, out_path: Path, experiment: str = "diplom-sf-oilwells") -> Path:
    runs = latest_experiment_runs(tracking_uri, experiment)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
