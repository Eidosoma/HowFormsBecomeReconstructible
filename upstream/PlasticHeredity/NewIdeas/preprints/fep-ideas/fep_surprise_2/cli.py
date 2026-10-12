from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .campaign import (
    analyze,
    develop,
    generate_confirmation,
    prepare_confirmation,
    register,
    replay_confirmation,
    status,
    validate_stage,
)
from .config import profile_config


COMMANDS = (
    "validate",
    "register",
    "develop",
    "prepare-confirmation",
    "generate-confirmation",
    "replay-confirmation",
    "analyze",
    "all",
    "status",
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Run the preregistered Experiment 2 rulebook-mismatch campaign"
    )
    value.add_argument("command", choices=COMMANDS)
    value.add_argument(
        "--profile", choices=("smoke", "quick", "full"), default="smoke"
    )
    value.add_argument("--run-root", type=Path, default=Path("runs2"))
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
    mutating_science = {
        "develop",
        "prepare-confirmation",
        "generate-confirmation",
        "replay-confirmation",
        "analyze",
        "all",
    }
    if (
        args.profile == "full"
        and args.command in mutating_science
        and not args.confirm_full_launch
    ):
        raise SystemExit(
            "full scientific generation is gated; pass --confirm-full-launch explicitly"
        )
    if args.command == "status":
        print(json.dumps(status(args.run_root, args.profile), indent=2, sort_keys=True))
        return
    if args.command in ("validate", "all"):
        print(f"validation: {validate_stage(args.run_root, config)}", flush=True)
    if args.command in ("register", "all"):
        print(f"registration: {register(args.run_root, config)}", flush=True)
    if args.command in ("develop", "all"):
        print(f"development: {develop(args.run_root, config, args.workers)}", flush=True)
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


if __name__ == "__main__":
    main()
