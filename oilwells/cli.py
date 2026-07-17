from __future__ import annotations

import argparse
from pathlib import Path

from oilwells.config import BusinessConfig, DuplicateIdPolicy
from oilwells.pipeline import run_dq, run_pipeline, run_smoke


def _add_io_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--data-dir", type=Path, default=Path("."))
    p.add_argument("--out-dir", type=Path, default=Path("artifacts"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="oilwells", description="Oil-well region selection pipeline")
    sub = p.add_subparsers(dest="command", required=True)

    dq_p = sub.add_parser("dq", help="Write data-quality audit JSON")
    _add_io_args(dq_p)

    run_p = sub.add_parser("run", help="Full pipeline: model + bootstrap + random baseline + sensitivity")
    _add_io_args(run_p)
    run_p.add_argument("--no-sensitivity", action="store_true")
    run_p.add_argument("--bootstrap", type=int, default=1000)
    run_p.add_argument("--sensitivity-bootstrap", type=int, default=400)
    run_p.add_argument(
        "--dup-id-policy",
        choices=[e.value for e in DuplicateIdPolicy],
        default=DuplicateIdPolicy.KEEP_ALL.value,
    )

    smoke_p = sub.add_parser("smoke", help="Fast CI smoke on subsample")
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

    if args.command == "run":
        cfg = BusinessConfig(
            n_bootstrap=args.bootstrap,
            duplicate_id_policy=DuplicateIdPolicy(args.dup_id_policy),
        )
        report = run_pipeline(
            data_dir,
            out_dir,
            cfg,
            include_sensitivity=not args.no_sensitivity,
            sensitivity_bootstrap=args.sensitivity_bootstrap,
        )
        rec = report.get("recommendation")
        print("Leaderboard:")
        for row in report["leaderboard"]:
            print(
                f"  {row['region']}: profit={row['mean_profit_mln']:.1f}m "
                f"loss={row['loss_prob']:.1%} lift_vs_random={row['lift_vs_random_mln']:.1f}m "
                f"gate={'OK' if row['passes_risk_gate'] else 'FAIL'}"
            )
        if rec:
            print(f"Recommendation: {rec['region']} (caveat={rec.get('caveat')})")
        else:
            print("Recommendation: none (no region passes risk gate)")
        print(f"Artifacts: {out_dir}")
        return 0

    raise SystemExit(f"unknown command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
