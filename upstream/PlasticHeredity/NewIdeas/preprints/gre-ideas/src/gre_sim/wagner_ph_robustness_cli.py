"""CLI for Wagner PH Mutation Autopsy and Robustness Ratchet v1."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .wagner_ph_robustness_campaign import (
    replay_wagner_ph_robustness,
    run_wagner_ph_robustness_campaign,
    verify_wagner_ph_robustness_campaign,
    wagner_ph_robustness_status,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-ph-robustness-ratchet-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Wagner PH Robustness Ratchet v1")
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_wagner_ph_robustness_campaign(
            args.parent, args.output, args.workers, _progress, smoke=args.smoke
        )
    except TimeoutError as error:
        print(f"Robustness campaign stopped at time boundary: {error}", file=sys.stderr)
        return 124
    except Exception as error:
        print(f"Robustness campaign failed: {error}", file=sys.stderr)
        return 1
    print(result)
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Wagner PH Robustness Ratchet v1")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(wagner_ph_robustness_status(args.output), indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Wagner PH Robustness Ratchet v1")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_wagner_ph_robustness_campaign(args.output)
    except Exception as error:
        print(f"Robustness verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay a robustness score or mutation event")
    parser.add_argument("output", type=Path)
    parser.add_argument("population_id")
    parser.add_argument("--pedigree", action="store_true")
    parser.add_argument("--parent-index", type=int, default=0)
    parser.add_argument("--child-index", type=int, default=0)
    parser.add_argument("--grandchild-index", type=int)
    args = parser.parse_args(argv)
    try:
        result = replay_wagner_ph_robustness(
            args.output,
            args.population_id,
            pedigree=args.pedigree,
            parent_index=args.parent_index,
            child_index=args.child_index,
            grandchild_index=args.grandchild_index,
        )
    except Exception as error:
        print(f"Robustness replay failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["matches"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wagner PH Robustness Ratchet v1")
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
    replay.add_argument("population_id")
    replay.add_argument("--pedigree", action="store_true")
    replay.add_argument("--parent-index", type=int, default=0)
    replay.add_argument("--child-index", type=int, default=0)
    replay.add_argument("--grandchild-index", type=int)
    args = parser.parse_args(argv)
    if args.command == "campaign":
        values = [
            "--parent",
            str(args.parent),
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
    if args.command == "verify":
        return verify_main([str(args.output)])
    values = [str(args.output), args.population_id]
    if args.pedigree:
        values.append("--pedigree")
    values.extend(("--parent-index", str(args.parent_index), "--child-index", str(args.child_index)))
    if args.grandchild_index is not None:
        values.extend(("--grandchild-index", str(args.grandchild_index)))
    return replay_main(values)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
