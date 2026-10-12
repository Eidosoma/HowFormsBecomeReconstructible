"""Command-line entry points for the Wagner local-memory PH campaign."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .local_ph_campaign import (
    local_ph_status,
    replay_local_campaign_future,
    run_local_ph_campaign,
    verify_local_ph_campaign,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-local-ph-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wagner-local-ph-campaign")
    parser.add_argument("--parent", type=Path, default=Path("runs/wagner-lineage-carrier-v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        print(run_local_ph_campaign(args.parent, args.output, args.workers, _progress, smoke=args.smoke))
    except TimeoutError as error:
        print(str(error), flush=True)
        return 124
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wagner-local-ph-status")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(local_ph_status(args.run), indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wagner-local-ph-verify")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(verify_local_ph_campaign(args.run), indent=2, sort_keys=True))
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wagner-local-ph-replay")
    parser.add_argument("run", type=Path)
    parser.add_argument("future_id")
    args = parser.parse_args(argv)
    print(json.dumps(replay_local_campaign_future(args.run, args.future_id), indent=2, sort_keys=True))
    return 0
