"""CLI for Wagner PH Interpreter-Depth v1."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .wagner_ph_depth_campaign import (
    replay_wagner_ph_depth,
    run_wagner_ph_depth_campaign,
    verify_wagner_ph_depth_campaign,
    wagner_ph_depth_status,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-ph-interpreter-depth-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Wagner PH Interpreter-Depth v1")
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_wagner_ph_depth_campaign(
            args.parent, args.output, args.workers, _progress, smoke=args.smoke
        )
    except TimeoutError as error:
        print(f"Interpreter-Depth campaign stopped at time boundary: {error}", file=sys.stderr)
        return 124
    except Exception as error:
        print(f"Interpreter-Depth campaign failed: {error}", file=sys.stderr)
        return 1
    print(result)
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Wagner PH Interpreter-Depth v1")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(wagner_ph_depth_status(args.output), indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Wagner PH Interpreter-Depth v1")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_wagner_ph_depth_campaign(args.output)
    except Exception as error:
        print(f"Interpreter-Depth verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay Interpreter-Depth scores, pedigrees, or atlas cells")
    parser.add_argument("output", type=Path)
    parser.add_argument("population_id", nargs="?")
    parser.add_argument("--phase", choices=("development", "confirmation"), default="development")
    parser.add_argument("--pedigree", action="store_true")
    parser.add_argument("--root-index", type=int, default=0)
    parser.add_argument("--lineage-index", type=int, default=0)
    parser.add_argument("--distance", type=int, default=1)
    parser.add_argument("--atlas-task", type=int)
    parser.add_argument("--atlas-edge", type=int, default=0)
    parser.add_argument("--atlas-operation", default="reset")
    args = parser.parse_args(argv)
    try:
        result = replay_wagner_ph_depth(
            args.output,
            args.population_id,
            phase=args.phase,
            pedigree=args.pedigree,
            root_index=args.root_index,
            lineage_index=args.lineage_index,
            distance=args.distance,
            atlas_task=args.atlas_task,
            atlas_edge=args.atlas_edge,
            atlas_operation=args.atlas_operation,
        )
    except Exception as error:
        print(f"Interpreter-Depth replay failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["matches"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wagner PH Interpreter-Depth v1")
    subparsers = parser.add_subparsers(dest="command", required=True)
    campaign = subparsers.add_parser("campaign")
    campaign.add_argument("--parent", required=True, type=Path)
    campaign.add_argument("--output", required=True, type=Path)
    campaign.add_argument("--workers", type=int, default=4)
    campaign.add_argument("--smoke", action="store_true")
    status = subparsers.add_parser("status")
    status.add_argument("output", type=Path)
    verify = subparsers.add_parser("verify")
    verify.add_argument("output", type=Path)
    replay = subparsers.add_parser("replay")
    replay.add_argument("output", type=Path)
    replay.add_argument("population_id", nargs="?")
    replay.add_argument("--phase", choices=("development", "confirmation"), default="development")
    replay.add_argument("--pedigree", action="store_true")
    replay.add_argument("--root-index", type=int, default=0)
    replay.add_argument("--lineage-index", type=int, default=0)
    replay.add_argument("--distance", type=int, default=1)
    replay.add_argument("--atlas-task", type=int)
    replay.add_argument("--atlas-edge", type=int, default=0)
    replay.add_argument("--atlas-operation", default="reset")
    args = parser.parse_args(argv)
    if args.command == "campaign":
        values = ["--parent", str(args.parent), "--output", str(args.output), "--workers", str(args.workers)]
        if args.smoke:
            values.append("--smoke")
        return campaign_main(values)
    if args.command == "status":
        return status_main([str(args.output)])
    if args.command == "verify":
        return verify_main([str(args.output)])
    values = [str(args.output)]
    if args.population_id is not None:
        values.append(args.population_id)
    values.extend(("--phase", args.phase, "--root-index", str(args.root_index), "--lineage-index", str(args.lineage_index), "--distance", str(args.distance)))
    if args.pedigree:
        values.append("--pedigree")
    if args.atlas_task is not None:
        values.extend(("--atlas-task", str(args.atlas_task), "--atlas-edge", str(args.atlas_edge), "--atlas-operation", args.atlas_operation))
    return replay_main(values)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
