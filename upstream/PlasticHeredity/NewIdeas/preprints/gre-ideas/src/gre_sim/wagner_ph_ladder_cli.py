"""Command-line interface for Wagner PH Origin Ladder v1."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .wagner_ph_ladder_campaign import (
    replay_wagner_ph_ladder_task,
    run_wagner_ph_ladder_campaign,
    verify_wagner_ph_ladder_campaign,
    wagner_ph_ladder_status,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-ph-origin-ladder-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Wagner PH Origin Ladder v1")
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_wagner_ph_ladder_campaign(
            args.parent,
            args.output,
            args.workers,
            _progress,
            smoke=args.smoke,
        )
    except TimeoutError as error:
        print(f"Origin Ladder stopped at time boundary: {error}", file=sys.stderr)
        return 124
    except Exception as error:
        print(f"Origin Ladder failed: {error}", file=sys.stderr)
        return 1
    print(result)
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect an Origin Ladder run")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(wagner_ph_ladder_status(args.output), indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a sealed Origin Ladder run")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        value = verify_wagner_ph_ladder_campaign(args.output)
    except Exception as error:
        print(f"Origin Ladder verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay one Origin Ladder task")
    parser.add_argument("output", type=Path)
    parser.add_argument("task_id")
    args = parser.parse_args(argv)
    try:
        value = replay_wagner_ph_ladder_task(args.output, args.task_id)
    except Exception as error:
        print(f"Origin Ladder replay failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["matches"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wagner PH Origin Ladder v1")
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
    replay.add_argument("task_id")
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
    return replay_main([str(args.output), args.task_id])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
