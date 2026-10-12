"""Dedicated command entry points for the lineage-carrier campaign."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .lineage_carrier_bounded import (
    bounded_initial_replication_status,
    run_bounded_initial_replication,
    verify_bounded_initial_replication,
    write_bounded_gate_correction,
)
from .lineage_carrier_orchestrator import (
    lineage_carrier_status,
    replay_lineage_campaign_future,
    run_lineage_carrier_campaign,
    verify_lineage_carrier_campaign,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-lineage-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lineage-carrier-campaign")
    parser.add_argument("--parent", type=Path, default=Path("runs/plastic-heredity-v2"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--through", choices=("discovery", "confirmation", "full"), default="discovery"
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--smoke", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    print(
        run_lineage_carrier_campaign(
            args.output,
            args.parent,
            args.through,
            args.workers,
            _progress,
            smoke=args.smoke,
        )
    )
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lineage-carrier-status")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(lineage_carrier_status(args.run), indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lineage-carrier-verify")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            verify_lineage_carrier_campaign(args.run), indent=2, sort_keys=True
        )
    )
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lineage-carrier-replay")
    parser.add_argument("run", type=Path)
    parser.add_argument("future_id")
    args = parser.parse_args(argv)
    print(
        json.dumps(
            replay_lineage_campaign_future(args.run, args.future_id),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def initial_replication_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lineage-carrier-initial-replication")
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    print(
        run_bounded_initial_replication(
            args.campaign, args.output, args.workers, _progress
        )
    )
    return 0


def initial_status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lineage-carrier-initial-status")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            bounded_initial_replication_status(args.run), indent=2, sort_keys=True
        )
    )
    return 0


def initial_verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lineage-carrier-initial-verify")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            verify_bounded_initial_replication(args.run), indent=2, sort_keys=True
        )
    )
    return 0


def initial_audit_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lineage-carrier-initial-audit")
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    print(write_bounded_gate_correction(args.run, args.output))
    return 0
