"""Command line interface for Global Repair Ratchet v1."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .artifacts import read_json
from .wagner_ph_repair_ratchet_campaign import (
    replay_repair_ratchet_population,
    run_wagner_ph_repair_ratchet_campaign,
    verify_wagner_ph_repair_ratchet_campaign,
    wagner_ph_repair_ratchet_status,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-ph-global-repair-ratchet-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Global Repair Ratchet v1")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(
            run_wagner_ph_repair_ratchet_campaign(
                args.reference, args.output, args.workers, _progress, smoke=args.smoke
            )
        )
    except TimeoutError as error:
        print(f"Global Repair Ratchet stopped at time boundary: {error}", file=sys.stderr)
        return 124
    except Exception as error:
        print(f"Global Repair Ratchet failed: {error}", file=sys.stderr)
        return 1
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Global Repair Ratchet v1")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(wagner_ph_repair_ratchet_status(args.output), indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Global Repair Ratchet v1")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_wagner_ph_repair_ratchet_campaign(args.output)
    except Exception as error:
        print(f"Global Repair Ratchet verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def inspect_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Global Repair Ratchet results")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    result: dict[str, object] = {"status": wagner_ph_repair_ratchet_status(args.output)}
    if (args.output / "analysis.json").is_file():
        analysis = read_json(args.output / "analysis.json")
        result["nomination"] = analysis["nomination"]
        result["route_decisions"] = analysis["route_decisions"]
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay a selected repair-ratchet score")
    parser.add_argument("output", type=Path)
    parser.add_argument("population_id")
    args = parser.parse_args(argv)
    result = replay_repair_ratchet_population(
        args.output / "development" / "evolution", args.population_id
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["matches"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wagner PH Global Repair Ratchet v1")
    sub = parser.add_subparsers(dest="command", required=True)
    campaign = sub.add_parser("campaign")
    campaign.add_argument("--reference", required=True, type=Path)
    campaign.add_argument("--output", required=True, type=Path)
    campaign.add_argument("--workers", type=int, default=4)
    campaign.add_argument("--smoke", action="store_true")
    for name in ("status", "inspect", "verify"):
        command = sub.add_parser(name)
        command.add_argument("output", type=Path)
    replay = sub.add_parser("replay")
    replay.add_argument("output", type=Path)
    replay.add_argument("population_id")
    args = parser.parse_args(argv)
    if args.command == "campaign":
        values = [
            "--reference",
            str(args.reference),
            "--output",
            str(args.output),
            "--workers",
            str(args.workers),
        ]
        if args.smoke:
            values.append("--smoke")
        return campaign_main(values)
    if args.command == "status":
        return status_main([str(args.output)])
    if args.command == "inspect":
        return inspect_main([str(args.output)])
    if args.command == "verify":
        return verify_main([str(args.output)])
    return replay_main([str(args.output), args.population_id])


if __name__ == "__main__":
    raise SystemExit(main())
