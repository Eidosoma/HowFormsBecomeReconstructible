from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .campaign import (
    analyze_stage,
    benchmark_stage,
    fit_stage,
    register,
    replay_stage,
    run_all,
    simulate_stage,
    status,
    validate_stage,
)
from .config import profile_config


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="FEP–PH Experiment 1 exploratory active-inference protocell atlas"
    )
    value.add_argument(
        "command",
        choices=(
            "validate",
            "benchmark",
            "register",
            "fit",
            "simulate",
            "replay",
            "analyze",
            "all",
            "status",
        ),
    )
    value.add_argument("--profile", choices=("smoke", "quick", "full"), default="smoke")
    value.add_argument("--run-root", type=Path, default=Path("runs-fep-ph1"))
    value.add_argument("--workers", type=int)
    return value


def main() -> None:
    args = parser().parse_args()
    config = profile_config(args.profile)
    if args.workers is not None:
        if args.workers <= 0:
            raise SystemExit("--workers must be positive")
        config = replace(config, workers=args.workers)
    if args.command == "status":
        print(json.dumps(status(args.run_root, args.profile), indent=2, sort_keys=True))
    elif args.command == "validate":
        print(json.dumps(validate_stage(args.run_root, config), indent=2, sort_keys=True))
    elif args.command == "benchmark":
        print(json.dumps(benchmark_stage(args.run_root, config), indent=2, sort_keys=True))
    elif args.command == "register":
        path, resolved = register(args.run_root, config)
        print(f"registered: {path} (evaluation_matrices={resolved.evaluation_matrices})", flush=True)
    elif args.command == "fit":
        print(f"fit: {fit_stage(args.run_root, config)}", flush=True)
    elif args.command == "simulate":
        print(f"simulation: {simulate_stage(args.run_root, config)}", flush=True)
    elif args.command == "replay":
        print(f"replay: {replay_stage(args.run_root, config)}", flush=True)
    elif args.command == "analyze":
        print(f"analysis: {analyze_stage(args.run_root, config)}", flush=True)
    elif args.command == "all":
        print(f"analysis: {run_all(args.run_root, config)}", flush=True)
    else:
        raise AssertionError(f"unhandled command {args.command}")

