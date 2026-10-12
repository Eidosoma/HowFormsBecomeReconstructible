from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .campaign import (
    analyze_stage,
    analyze_stage_a_stage,
    benchmark_stage,
    develop_register,
    development_stage,
    fit_stage,
    register,
    register_stage_b,
    replay_development_stage,
    replay_fit_stage,
    replay_stage_a,
    replay_stage_b,
    run_all,
    stage_a_stage,
    stage_b_stage,
    status,
    validate_stage,
)
from .config import MAX_WORKERS, profile_config


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="FEP–PH1.9 causal-policy and selective-sensing atlas"
    )
    value.add_argument(
        "command",
        choices=(
            "validate",
            "develop-register",
            "develop",
            "replay-development",
            "fit",
            "replay-fit",
            "benchmark",
            "register",
            "stage-a",
            "replay-stage-a",
            "analyze-stage-a",
            "register-stage-b",
            "stage-b",
            "replay-stage-b",
            "analyze",
            "all",
            "status",
        ),
    )
    value.add_argument("--profile", choices=("smoke", "quick", "full"), default="smoke")
    value.add_argument("--run-root", type=Path, default=Path("runs-fep-ph19"))
    value.add_argument("--workers", type=int)
    return value


def main() -> None:
    args = parser().parse_args()
    config = profile_config(args.profile)
    if args.workers is not None:
        if not 0 < args.workers <= MAX_WORKERS:
            raise SystemExit(f"--workers must be between 1 and {MAX_WORKERS}")
        config = replace(config, workers=args.workers)
        config.validate()
    if args.command == "status":
        print(json.dumps(status(args.run_root, args.profile), indent=2, sort_keys=True))
    elif args.command == "validate":
        print(json.dumps(validate_stage(args.run_root, config), indent=2, sort_keys=True))
    elif args.command == "develop-register":
        print(f"development registration: {develop_register(args.run_root, config)}", flush=True)
    elif args.command == "develop":
        print(f"development: {development_stage(args.run_root, config)}", flush=True)
    elif args.command == "replay-development":
        print(f"development replay: {replay_development_stage(args.run_root, config)}", flush=True)
    elif args.command == "fit":
        print(f"fit: {fit_stage(args.run_root, config)}", flush=True)
    elif args.command == "replay-fit":
        print(f"fit replay: {replay_fit_stage(args.run_root, config)}", flush=True)
    elif args.command == "benchmark":
        print(json.dumps(benchmark_stage(args.run_root, config), indent=2, sort_keys=True))
    elif args.command == "register":
        path, resolved = register(args.run_root, config)
        print(
            f"registered: {path} (scales={resolved.stage_a_matrices},{resolved.stage_b_matrices})",
            flush=True,
        )
    elif args.command == "stage-a":
        print(f"Stage A: {stage_a_stage(args.run_root, config)}", flush=True)
    elif args.command == "replay-stage-a":
        print(f"Stage A replay: {replay_stage_a(args.run_root, config)}", flush=True)
    elif args.command == "analyze-stage-a":
        print(f"Stage A analysis: {analyze_stage_a_stage(args.run_root, config)}", flush=True)
    elif args.command == "register-stage-b":
        path, resolved = register_stage_b(args.run_root, config)
        print(f"Stage B registration: {path} ({'RUN' if resolved else 'STOP'})", flush=True)
    elif args.command == "stage-b":
        print(f"Stage B: {stage_b_stage(args.run_root, config)}", flush=True)
    elif args.command == "replay-stage-b":
        print(f"Stage B replay: {replay_stage_b(args.run_root, config)}", flush=True)
    elif args.command == "analyze":
        print(f"analysis: {analyze_stage(args.run_root, config)}", flush=True)
    elif args.command == "all":
        print(f"analysis: {run_all(args.run_root, config)}", flush=True)
    else:
        raise AssertionError(f"unhandled command {args.command}")


__all__ = ("main", "parser")
