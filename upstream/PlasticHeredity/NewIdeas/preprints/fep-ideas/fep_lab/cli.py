from __future__ import annotations

import argparse
import json
from pathlib import Path

from .campaign import (
    benchmark_runtime,
    register,
    replay_stage,
    report_stage,
    run_all,
    simulate_stage,
    status,
    validate_stage,
)
from .config import profile_config


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Known-positive Markov-blanket and active-inference laboratory"
    )
    value.add_argument(
        "command",
        choices=(
            "benchmark",
            "register",
            "validate",
            "simulate",
            "replay",
            "report",
            "all",
            "status",
        ),
    )
    value.add_argument("--profile", choices=("smoke", "quick", "full"), default="smoke")
    value.add_argument("--run-root", type=Path, default=Path("runs-fep-lab"))
    return value


def main() -> None:
    args = parser().parse_args()
    config = profile_config(args.profile)
    if args.command == "status":
        print(json.dumps(status(args.run_root, args.profile), indent=2, sort_keys=True))
        return
    if args.command == "benchmark":
        if args.profile != "full":
            raise SystemExit("benchmark is defined only for the full profile")
        print(json.dumps(benchmark_runtime(config), indent=2, sort_keys=True))
        return
    if args.command == "register":
        path, resolved = register(args.run_root, config)
        print(f"registered: {path} (scale={resolved.selected_scale})", flush=True)
        return
    if args.command == "all":
        path = run_all(args.run_root, config)
        print(f"analysis: {path}", flush=True)
        return
    if args.command == "validate":
        result = validate_stage(args.run_root, config)
        print(json.dumps(result, indent=2, sort_keys=True), flush=True)
        return
    if args.command == "simulate":
        print(f"simulation: {simulate_stage(args.run_root, config)}", flush=True)
        return
    if args.command == "replay":
        print(f"replay: {replay_stage(args.run_root, config)}", flush=True)
        return
    if args.command == "report":
        print(f"analysis: {report_stage(args.run_root, config)}", flush=True)
        return
    raise AssertionError(f"unhandled command {args.command}")
