from __future__ import annotations

import argparse
from pathlib import Path

from oilwells.config import BusinessConfig, DuplicateIdPolicy
from oilwells.models_ext import ModelKind
from oilwells.pipeline import run_dq, run_pipeline, run_smoke


def _add_io_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--data-dir", type=Path, default=Path("."))
    p.add_argument("--out-dir", type=Path, default=Path("artifacts"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="oilwells", description="Oil-well region selection pipeline")
    sub = p.add_subparsers(dest="command", required=True)

    dq_p = sub.add_parser("dq", help="Write data-quality audit JSON")
    _add_io_args(dq_p)

    run_p = sub.add_parser(
        "run",
        help="Pipeline: official LR (+ optional experimental models), bootstrap, CVaR, MLflow, dashboard",
    )
    _add_io_args(run_p)
    run_p.add_argument("--no-sensitivity", action="store_true")
    run_p.add_argument("--no-dashboard", action="store_true")
    run_p.add_argument("--bootstrap", type=int, default=1000)
    run_p.add_argument("--sensitivity-bootstrap", type=int, default=400)
    run_p.add_argument(
        "--models",
        default="lr",
        help="Comma-separated model kinds: lr (official), elasticnet, gbr, hgbr",
    )
    run_p.add_argument(
        "--mlflow-uri",
        type=Path,
        default=None,
        help="MLflow tracking URI/dir (default: <out-dir>/mlruns)",
    )
    run_p.add_argument(
        "--dup-id-policy",
        choices=[e.value for e in DuplicateIdPolicy],
        default=DuplicateIdPolicy.KEEP_ALL.value,
    )

    compare_p = sub.add_parser(
        "compare",
        help="Compare official LR vs ElasticNet vs HistGBR (experimental models clearly labeled)",
    )
    _add_io_args(compare_p)
    compare_p.add_argument("--bootstrap", type=int, default=600)

    smoke_p = sub.add_parser("smoke", help="Fast CI smoke on subsample / sample data")
    _add_io_args(smoke_p)
    smoke_p.add_argument("--subsample", type=int, default=8000)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data_dir = args.data_dir.resolve()
    out_dir = args.out_dir.resolve()

    if args.command == "dq":
        report = run_dq(data_dir, out_dir)
        print(report["summary"])
        return 0

    if args.command == "smoke":
        report = run_smoke(data_dir, out_dir, subsample=args.subsample)
        print(f"smoke ok; critical={report['dq_critical_regions']}")
        return 0

    if args.command in {"run", "compare"}:
        models = (
            "lr,elasticnet,hgbr"
            if args.command == "compare"
            else args.models
        )
        kinds = [m.strip() for m in models.split(",") if m.strip()]
        for k in kinds:
            ModelKind(k)  # validate early
        cfg = BusinessConfig(
            n_bootstrap=args.bootstrap,
            duplicate_id_policy=DuplicateIdPolicy(
                getattr(args, "dup_id_policy", DuplicateIdPolicy.KEEP_ALL.value)
            ),
        )
        report = run_pipeline(
            data_dir,
            out_dir,
            cfg,
            model_kinds=kinds,
            include_sensitivity=(args.command == "run" and not args.no_sensitivity),
            sensitivity_bootstrap=getattr(args, "sensitivity_bootstrap", 400),
            mlflow_uri=getattr(args, "mlflow_uri", None) or (out_dir / "mlruns"),
            build_dashboard=not getattr(args, "no_dashboard", False),
        )
        print("Leaderboard:")
        for row in report["leaderboard"]:
            tag = "OFFICIAL" if row["official_path"] else "EXPERIMENTAL"
            print(
                f"  [{tag}] {row['region']}/{row['model_kind']}: "
                f"profit={row['mean_profit_mln']:.1f}m loss={row['loss_prob']:.1%} "
                f"CVaR5%={row['cvar_5_mln']:.1f}m gate={'OK' if row['passes_risk_gate'] else 'FAIL'}"
            )
        rec = report.get("recommendation")
        if rec:
            print(
                f"Official recommendation: {rec['region']} "
                f"(CVaR5%={rec['cvar_5_mln']:.1f}m, caveat={rec.get('caveat')})"
            )
        else:
            print("Official recommendation: none (no LR region passes risk gate)")
        if report.get("dashboard"):
            print(f"Dashboard: {report['dashboard']}")
        print(f"MLflow: {report['mlflow_tracking_uri']}  (mlflow ui --backend-store-uri …)")
        print(f"Artifacts: {out_dir}")
        return 0

    raise SystemExit(f"unknown command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
