from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .campaign import (
    analyze,
    develop,
    generate_confirmation,
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
    "generate-confirmation",
    "replay-confirmation",
    "analyze",
    "all",
    "status",
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Run the preregistered Experiment 1.5 campaign"
    )
    value.add_argument("command", choices=COMMANDS)
    value.add_argument(
        "--profile", choices=("smoke", "quick", "full"), default="smoke"
    )
    value.add_argument("--run-root", type=Path, default=Path("runs15"))
    value.add_argument(
        "--workers", type=int, default=max(1, min(8, os.cpu_count() or 1))
    )
    return value


def main() -> None:
    args = parser().parse_args()
    config = profile_config(args.profile)
    if args.workers < 1:
        raise SystemExit("--workers must be at least one")
    if args.command == "status":
        print(
            json.dumps(status(args.run_root, args.profile), indent=2, sort_keys=True)
        )
        return
    if args.command in ("validate", "all"):
        result = validate_stage(args.run_root, config)
        print(f"validation: {result}", flush=True)
    if args.command in ("register", "all"):
        result = register(args.run_root, config)
        print(f"registration: {result}", flush=True)
    if args.command in ("develop", "all"):
        result = develop(args.run_root, config, args.workers)
        print(f"development: {result}", flush=True)
    if args.command in ("generate-confirmation", "all"):
        result = generate_confirmation(args.run_root, config, args.workers)
        print(f"confirmation: {result}", flush=True)
    if args.command in ("replay-confirmation", "all"):
        result = replay_confirmation(args.run_root, config, args.workers)
        print(f"confirmation replay: {result}", flush=True)
    if args.command in ("analyze", "all"):
        result = analyze(args.run_root, config)
        print(f"analysis: {result}", flush=True)


if __name__ == "__main__":
    main()
