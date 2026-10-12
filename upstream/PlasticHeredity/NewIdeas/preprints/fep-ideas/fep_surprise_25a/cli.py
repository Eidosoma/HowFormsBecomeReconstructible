from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from fep_surprise_25.budget import TimeBudgetExhausted

from .campaign import (
    analyze,
    audit_source,
    benchmark,
    config_for_source,
    generate_confirmation,
    prepare_confirmation,
    register,
    replay_confirmation,
    run_all,
    status,
    validate_stage,
)
from .worker import ReferenceShortfall


COMMANDS = (
    "source-audit",
    "validate",
    "benchmark",
    "register",
    "prepare-confirmation",
    "generate-confirmation",
    "replay-confirmation",
    "analyze",
    "all",
    "status",
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Run Experiment 2.5a: viability-aware Goldilocks Boundary amendment"
    )
    value.add_argument("command", choices=COMMANDS)
    value.add_argument("--profile", choices=("smoke", "quick", "full"), default="smoke")
    value.add_argument("--source-run-root", type=Path, default=Path("runs25"))
    value.add_argument("--run-root", type=Path, default=Path("runs25a"))
    value.add_argument(
        "--workers", type=int, default=max(1, min(8, os.cpu_count() or 1))
    )
    value.add_argument(
        "--confirm-full-launch",
        action="store_true",
        help="required before a full amendment may generate fresh scientific streams",
    )
    return value


def main() -> None:
    args = parser().parse_args()
    if args.command == "status":
        print(
            json.dumps(
                status(args.source_run_root, args.run_root, args.profile),
                indent=2,
                sort_keys=True,
            )
        )
        return
    config = config_for_source(args.source_run_root, args.profile)
    if args.workers < 1:
        raise SystemExit("--workers must be at least one")
    scientific_mutations = {
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
            "full amended scientific generation is gated; pass --confirm-full-launch explicitly"
        )
    if (
        args.profile == "full"
        and args.command in scientific_mutations
        and args.workers < config.generation_workers
    ):
        raise SystemExit(
            f"full amendment requires at least {config.generation_workers} requested workers"
        )
    try:
        if args.command == "source-audit":
            print(audit_source(args.source_run_root, args.run_root, config))
        elif args.command == "validate":
            print(validate_stage(args.source_run_root, args.run_root, config))
        elif args.command == "benchmark":
            print(benchmark(args.run_root, config, args.workers))
        elif args.command == "register":
            print(register(args.source_run_root, args.run_root, config))
        elif args.command == "prepare-confirmation":
            print(
                prepare_confirmation(
                    args.source_run_root, args.run_root, config, args.workers
                )
            )
        elif args.command == "generate-confirmation":
            print(
                generate_confirmation(
                    args.source_run_root, args.run_root, config, args.workers
                )
            )
        elif args.command == "replay-confirmation":
            print(
                replay_confirmation(
                    args.source_run_root, args.run_root, config, args.workers
                )
            )
        elif args.command == "analyze":
            print(analyze(args.source_run_root, args.run_root, config))
        elif args.command == "all":
            for result in run_all(
                args.source_run_root, args.run_root, config, args.workers
            ):
                print(result, flush=True)
    except (TimeBudgetExhausted, ReferenceShortfall) as error:
        print(str(error), flush=True)
        raise SystemExit(75) from error


if __name__ == "__main__":
    main()
