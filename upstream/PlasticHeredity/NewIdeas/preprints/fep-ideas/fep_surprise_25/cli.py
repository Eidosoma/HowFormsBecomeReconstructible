from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .budget import TimeBudgetExhausted
from .campaign import (
    analyze,
    benchmark,
    generate_confirmation,
    prepare_confirmation,
    register,
    replay_confirmation,
    screen,
    status,
    validate_stage,
)
from .config import profile_config


COMMANDS = (
    "validate",
    "benchmark",
    "register",
    "screen",
    "prepare-confirmation",
    "generate-confirmation",
    "replay-confirmation",
    "analyze",
    "all",
    "status",
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Run Experiment 2.5: dynamic-regime-gated Goldilocks Crossing"
    )
    value.add_argument("command", choices=COMMANDS)
    value.add_argument("--profile", choices=("smoke", "quick", "full"), default="smoke")
    value.add_argument("--run-root", type=Path, default=Path("runs25"))
    value.add_argument(
        "--workers", type=int, default=max(1, min(8, os.cpu_count() or 1))
    )
    value.add_argument(
        "--confirm-full-launch",
        action="store_true",
        help="required before a full profile may generate scientific matrices",
    )
    return value


def main() -> None:
    args = parser().parse_args()
    config = profile_config(args.profile)
    if args.workers < 1:
        raise SystemExit("--workers must be at least one")
    scientific_mutations = {
        "screen",
        "prepare-confirmation",
        "generate-confirmation",
        "replay-confirmation",
        "analyze",
        "all",
    }
    if (
        args.profile == "full"
        and args.command in scientific_mutations
        and not args.confirm_full_launch
    ):
        raise SystemExit(
            "full scientific generation is gated; pass --confirm-full-launch explicitly"
        )
    if (
        args.profile == "full"
        and args.command in scientific_mutations
        and args.workers < config.generation_workers
    ):
        raise SystemExit(
            f"full profile requires at least {config.generation_workers} requested workers "
            "to honor its timing registration"
        )
    if args.command == "status":
        print(json.dumps(status(args.run_root, args.profile), indent=2, sort_keys=True))
        return
    try:
        if args.command in ("validate", "all"):
            print(f"validation: {validate_stage(args.run_root, config)}", flush=True)
        if args.command in ("benchmark", "all"):
            print(f"benchmark: {benchmark(args.run_root, config, args.workers)}", flush=True)
        if args.command in ("register", "all"):
            print(f"registration: {register(args.run_root, config)}", flush=True)
        if args.command in ("screen", "all"):
            print(f"screen: {screen(args.run_root, config, args.workers)}", flush=True)
        if args.command in ("prepare-confirmation", "all"):
            print(
                f"confirmation design: {prepare_confirmation(args.run_root, config, args.workers)}",
                flush=True,
            )
        if args.command in ("generate-confirmation", "all"):
            print(
                f"confirmation: {generate_confirmation(args.run_root, config, args.workers)}",
                flush=True,
            )
        if args.command in ("replay-confirmation", "all"):
            print(
                f"confirmation replay: {replay_confirmation(args.run_root, config, args.workers)}",
                flush=True,
            )
        if args.command in ("analyze", "all"):
            print(f"analysis: {analyze(args.run_root, config)}", flush=True)
    except TimeBudgetExhausted as error:
        print(str(error), flush=True)
        raise SystemExit(75) from error
