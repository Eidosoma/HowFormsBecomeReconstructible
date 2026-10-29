"""Command-line interface for the contract-bridge capsule."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
_CACHE = Path(__file__).resolve().parents[2] / ".cache"
(_CACHE / "matplotlib").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_CACHE / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE))

from .config import BridgeConfig, results_root, work_root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contract-bridge",
        description="EIDOSOMA-1.5 exploratory contract-bridge campaign.",
    )
    parser.add_argument(
        "command",
        choices=(
            "validate",
            "build",
            "strict-mc",
            "freeze",
            "analyze",
            "report",
            "all",
            "status",
        ),
    )
    parser.add_argument("--mini", action="store_true", help="run the 2-species fixture")
    parser.add_argument("--jobs", type=int, default=8, help="worker processes (default: 8)")
    return parser


def _status(config: BridgeConfig) -> dict:
    results = results_root(config)
    progress_path = work_root(config) / "progress.json"
    payload: dict = {"mode": config.mode}
    if progress_path.exists():
        payload["progress"] = json.loads(progress_path.read_text())
    artifacts = (
        "build_manifest.json",
        "strict_feasibility.json",
        "mc_manifest.json",
        "frozen_components.json",
        "binomial_strict_atlas.csv",
        "contract_shift_summary.json",
        "translator_ladder.csv",
        "ordinal_frontier.csv",
        "estimator_rank_reliability.csv",
        "METRICS.json",
        "REPORT.md",
    )
    payload["artifacts"] = {name: (results / name).exists() for name in artifacts}
    pid_path = Path(__file__).resolve().parents[2] / ".runs" / "full.pid"
    if pid_path.exists():
        pid = int(pid_path.read_text().strip())
        try:
            os.kill(pid, 0)
            payload["detached_worker"] = {"pid": pid, "running": True}
        except OSError:
            payload["detached_worker"] = {"pid": pid, "running": False}
    return payload


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.jobs < 1:
        raise SystemExit("--jobs must be positive")
    config = BridgeConfig.mini() if args.mini else BridgeConfig()
    payload = None
    if args.command == "validate":
        from .validation import validate_bridge

        payload = validate_bridge(config)
    elif args.command == "build":
        from .pipeline import build_bridge

        payload = build_bridge(config, jobs=args.jobs)
    elif args.command == "strict-mc":
        from .pipeline import run_strict_mc

        payload = run_strict_mc(config, jobs=args.jobs)
    elif args.command == "freeze":
        from .pipeline import freeze_components

        payload = freeze_components(config)
    elif args.command == "analyze":
        from .pipeline import analyze_bridge

        payload = analyze_bridge(config, jobs=args.jobs)
    elif args.command == "report":
        from .reporting import generate_report

        payload = generate_report(config)
    elif args.command == "all":
        from .pipeline import analyze_bridge, build_bridge, freeze_components, run_strict_mc
        from .reporting import generate_report
        from .validation import validate_bridge

        validate_bridge(config)
        build_bridge(config, jobs=args.jobs)
        run_strict_mc(config, jobs=args.jobs)
        freeze_components(config)
        analyze_bridge(config, jobs=args.jobs)
        payload = generate_report(config)
    elif args.command == "status":
        payload = _status(config)
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
