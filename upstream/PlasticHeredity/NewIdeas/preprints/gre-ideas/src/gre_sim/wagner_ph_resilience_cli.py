"""CLI for Wagner PH Interpreter Resilience v1."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .wagner_ph_resilience_campaign import (
    replay_wagner_ph_resilience,
    run_wagner_ph_resilience_campaign,
    verify_wagner_ph_resilience_campaign,
    wagner_ph_resilience_status,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-ph-interpreter-resilience-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Wagner PH Interpreter Resilience v1")
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(run_wagner_ph_resilience_campaign(args.parent, args.reference, args.output, args.workers, _progress, smoke=args.smoke))
    except TimeoutError as error:
        print(f"Interpreter Resilience campaign stopped at time boundary: {error}", file=sys.stderr); return 124
    except Exception as error:
        print(f"Interpreter Resilience campaign failed: {error}", file=sys.stderr); return 1
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Interpreter Resilience v1")
    parser.add_argument("output", type=Path); args = parser.parse_args(argv)
    print(json.dumps(wagner_ph_resilience_status(args.output), indent=2, sort_keys=True)); return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Interpreter Resilience v1")
    parser.add_argument("output", type=Path); args = parser.parse_args(argv)
    try: result = verify_wagner_ph_resilience_campaign(args.output)
    except Exception as error:
        print(f"Interpreter Resilience verification failed: {error}", file=sys.stderr); return 1
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay Interpreter Resilience scores or pedigrees")
    parser.add_argument("output", type=Path); parser.add_argument("population_id")
    parser.add_argument("--phase", choices=("development", "confirmation"), default="development")
    parser.add_argument("--pedigree", action="store_true"); parser.add_argument("--root-index", type=int, default=0)
    parser.add_argument("--lineage-index", type=int, default=0); parser.add_argument("--distance", type=int, default=1)
    parser.add_argument("--mode", choices=("natural", "mechanism_off"), default="natural")
    args = parser.parse_args(argv)
    try:
        result = replay_wagner_ph_resilience(args.output, args.population_id, phase=args.phase, pedigree=args.pedigree, root_index=args.root_index, lineage_index=args.lineage_index, distance=args.distance, mode=args.mode)
    except Exception as error:
        print(f"Interpreter Resilience replay failed: {error}", file=sys.stderr); return 1
    print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["matches"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wagner PH Interpreter Resilience v1")
    sub = parser.add_subparsers(dest="command", required=True)
    campaign = sub.add_parser("campaign"); campaign.add_argument("--parent", required=True, type=Path); campaign.add_argument("--reference", required=True, type=Path); campaign.add_argument("--output", required=True, type=Path); campaign.add_argument("--workers", type=int, default=4); campaign.add_argument("--smoke", action="store_true")
    status = sub.add_parser("status"); status.add_argument("output", type=Path)
    verify = sub.add_parser("verify"); verify.add_argument("output", type=Path)
    replay = sub.add_parser("replay"); replay.add_argument("output", type=Path); replay.add_argument("population_id"); replay.add_argument("--phase", choices=("development", "confirmation"), default="development"); replay.add_argument("--pedigree", action="store_true"); replay.add_argument("--root-index", type=int, default=0); replay.add_argument("--lineage-index", type=int, default=0); replay.add_argument("--distance", type=int, default=1); replay.add_argument("--mode", choices=("natural", "mechanism_off"), default="natural")
    args = parser.parse_args(argv)
    if args.command == "campaign":
        values = ["--parent", str(args.parent), "--reference", str(args.reference), "--output", str(args.output), "--workers", str(args.workers)]
        if args.smoke: values.append("--smoke")
        return campaign_main(values)
    if args.command == "status": return status_main([str(args.output)])
    if args.command == "verify": return verify_main([str(args.output)])
    values = [str(args.output), args.population_id, "--phase", args.phase, "--root-index", str(args.root_index), "--lineage-index", str(args.lineage_index), "--distance", str(args.distance), "--mode", args.mode]
    if args.pedigree: values.append("--pedigree")
    return replay_main(values)


if __name__ == "__main__":
    raise SystemExit(main())
