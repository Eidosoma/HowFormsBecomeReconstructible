"""Command-line entry points for Wagner–Plastic Heredity Bridge v1."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .wagner_ph_bridge_campaign import (
    replay_wagner_ph_bridge_item,
    run_wagner_ph_bridge_campaign,
    verify_wagner_ph_bridge_campaign,
    wagner_ph_bridge_status,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-ph-bridge-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wagner-ph-bridge-campaign")
    parser.add_argument("--parent", type=Path, default=Path("runs/wagner-local-ph-v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        print(
            run_wagner_ph_bridge_campaign(
                args.parent, args.output, args.workers, _progress, smoke=args.smoke
            )
        )
    except TimeoutError as error:
        print(str(error), flush=True)
        return 124
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wagner-ph-bridge-status")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(wagner_ph_bridge_status(args.run), indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wagner-ph-bridge-verify")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(verify_wagner_ph_bridge_campaign(args.run), indent=2, sort_keys=True))
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wagner-ph-bridge-replay")
    parser.add_argument("run", type=Path)
    parser.add_argument("item_id")
    args = parser.parse_args(argv)
    print(
        json.dumps(
            replay_wagner_ph_bridge_item(args.run, args.item_id),
            indent=2,
            sort_keys=True,
        )
    )
    return 0
