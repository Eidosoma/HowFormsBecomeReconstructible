"""CLI for Wagner PH Adaptive Maintenance v1."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .artifacts import read_json
from .wagner_ph_maintenance_campaign import (
    replay_wagner_ph_maintenance,
    run_wagner_ph_maintenance_campaign,
    run_wagner_ph_maintenance_confirmation,
    verify_wagner_ph_maintenance_campaign,
    verify_wagner_ph_maintenance_confirmation,
    wagner_ph_maintenance_status,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-ph-adaptive-maintenance-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Adaptive Maintenance v1 development")
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(
            run_wagner_ph_maintenance_campaign(
                args.parent, args.output, args.workers, _progress, smoke=args.smoke
            )
        )
    except TimeoutError as error:
        print(f"Adaptive Maintenance development stopped at time boundary: {error}", file=sys.stderr)
        return 124
    except Exception as error:
        print(f"Adaptive Maintenance development failed: {error}", file=sys.stderr)
        return 1
    return 0


def confirmation_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run explicitly authorized fresh confirmation")
    parser.add_argument("--development", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--authorize-confirmation", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(
            run_wagner_ph_maintenance_confirmation(
                args.development,
                args.output,
                args.workers,
                _progress,
                authorize_confirmation=args.authorize_confirmation,
            )
        )
    except TimeoutError as error:
        print(f"Adaptive Maintenance confirmation stopped at time boundary: {error}", file=sys.stderr)
        return 124
    except Exception as error:
        print(f"Adaptive Maintenance confirmation failed: {error}", file=sys.stderr)
        return 1
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Adaptive Maintenance v1")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(wagner_ph_maintenance_status(args.output), indent=2, sort_keys=True))
    return 0


def inspect_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect status and available scientific results")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    result = {"status": wagner_ph_maintenance_status(args.output)}
    if (args.output / "analysis.json").is_file():
        analysis = read_json(args.output / "analysis.json")
        if "development_analysis" in analysis:
            result["diagnosis"] = analysis["diagnosis_analysis"]
            result["decisions"] = analysis["development_analysis"]["candidate_decisions"]
            result["nomination"] = analysis["nomination"]
        else:
            result["confirmation"] = analysis["confirmation"]
            result["decisions"] = analysis["candidate_decisions"]
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Adaptive Maintenance v1")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        registration = read_json(args.output / "registration.json")
        if registration.get("campaign_kind") == "explicitly-authorized-confirmation":
            result = verify_wagner_ph_maintenance_confirmation(args.output)
        else:
            result = verify_wagner_ph_maintenance_campaign(args.output)
    except Exception as error:
        print(f"Adaptive Maintenance verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay Adaptive Maintenance scores or pedigrees")
    parser.add_argument("output", type=Path)
    parser.add_argument("population_id")
    parser.add_argument("--pedigree", action="store_true")
    parser.add_argument("--root-index", type=int, default=0)
    parser.add_argument("--lineage-index", type=int, default=0)
    parser.add_argument("--distance", type=int, default=1)
    parser.add_argument(
        "--mode",
        choices=(
            "natural",
            "repair_off",
            "uniform_repair",
            "shuffled_repair",
            "concerted",
            "mean_decoder",
            "single_copy",
        ),
        default="natural",
    )
    args = parser.parse_args(argv)
    try:
        result = replay_wagner_ph_maintenance(
            args.output,
            args.population_id,
            pedigree=args.pedigree,
            root_index=args.root_index,
            lineage_index=args.lineage_index,
            distance=args.distance,
            mode=args.mode,
        )
    except Exception as error:
        print(f"Adaptive Maintenance replay failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["matches"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wagner PH Adaptive Maintenance v1")
    sub = parser.add_subparsers(dest="command", required=True)
    campaign = sub.add_parser("campaign")
    campaign.add_argument("--parent", required=True, type=Path)
    campaign.add_argument("--output", required=True, type=Path)
    campaign.add_argument("--workers", type=int, default=4)
    campaign.add_argument("--smoke", action="store_true")
    confirmation = sub.add_parser("confirm")
    confirmation.add_argument("--development", required=True, type=Path)
    confirmation.add_argument("--output", required=True, type=Path)
    confirmation.add_argument("--workers", type=int, default=4)
    confirmation.add_argument("--authorize-confirmation", action="store_true")
    for name in ("status", "inspect", "verify"):
        command = sub.add_parser(name)
        command.add_argument("output", type=Path)
    replay = sub.add_parser("replay")
    replay.add_argument("output", type=Path)
    replay.add_argument("population_id")
    replay.add_argument("--pedigree", action="store_true")
    replay.add_argument("--root-index", type=int, default=0)
    replay.add_argument("--lineage-index", type=int, default=0)
    replay.add_argument("--distance", type=int, default=1)
    replay.add_argument("--mode", default="natural")
    args = parser.parse_args(argv)
    if args.command == "campaign":
        values = ["--parent", str(args.parent), "--output", str(args.output), "--workers", str(args.workers)]
        if args.smoke:
            values.append("--smoke")
        return campaign_main(values)
    if args.command == "confirm":
        values = ["--development", str(args.development), "--output", str(args.output), "--workers", str(args.workers)]
        if args.authorize_confirmation:
            values.append("--authorize-confirmation")
        return confirmation_main(values)
    if args.command == "status":
        return status_main([str(args.output)])
    if args.command == "inspect":
        return inspect_main([str(args.output)])
    if args.command == "verify":
        return verify_main([str(args.output)])
    values = [
        str(args.output),
        args.population_id,
        "--root-index",
        str(args.root_index),
        "--lineage-index",
        str(args.lineage_index),
        "--distance",
        str(args.distance),
        "--mode",
        args.mode,
    ]
    if args.pedigree:
        values.append("--pedigree")
    return replay_main(values)


if __name__ == "__main__":
    raise SystemExit(main())
