"""Dedicated command entry points for Plastic Heredity v2."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .plastic_heredity_v2_orchestrator import (
    plastic_heredity_v2_status,
    replay_plastic_heredity_v2,
    run_plastic_heredity_v2_campaign,
    verify_plastic_heredity_v2_campaign,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[plastic-heredity-v2 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="plastic-heredity-v2-campaign")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--through", choices=("wave-1", "wave-2", "full"), default="wave-1")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--parent-evolution",
        type=Path,
        default=Path("runs/wagner-heredity-v1/evolution-confirmation"),
    )
    parser.add_argument(
        "--gard-root",
        type=Path,
        default=Path("../strict-8-paper-preparations"),
    )
    parser.add_argument("--no-gard", action="store_true")
    args = parser.parse_args(argv)
    result = run_plastic_heredity_v2_campaign(
        args.output,
        args.through,
        args.workers,
        args.parent_evolution,
        None if args.no_gard else args.gard_root,
        _progress,
    )
    print(result)
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="plastic-heredity-v2-status")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(plastic_heredity_v2_status(args.run), indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="plastic-heredity-v2-verify")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            verify_plastic_heredity_v2_campaign(args.run), indent=2, sort_keys=True
        )
    )
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="plastic-heredity-v2-replay")
    parser.add_argument("run", type=Path)
    parser.add_argument("future_id")
    args = parser.parse_args(argv)
    print(
        json.dumps(
            replay_plastic_heredity_v2(args.run, args.future_id),
            indent=2,
            sort_keys=True,
        )
    )
    return 0
