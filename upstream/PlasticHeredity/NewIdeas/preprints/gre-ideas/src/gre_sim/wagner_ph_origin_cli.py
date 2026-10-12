"""Command-line entry points for Wagner PH origin/discrimination v1."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .wagner_ph_origin_campaign import (
    replay_wagner_ph_origin_item,
    run_wagner_ph_origin_campaign,
    verify_wagner_ph_origin_campaign,
    wagner_ph_origin_status,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-ph-origin-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the four-hour Wagner PH origin/discrimination campaign"
    )
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_wagner_ph_origin_campaign(
            args.parent, args.output, args.workers, _progress, smoke=args.smoke
        )
    except TimeoutError as error:
        print(f"wagner-ph-origin campaign stopped at time boundary: {error}", file=sys.stderr)
        return 124
    except Exception as error:
        print(f"wagner-ph-origin campaign failed: {error}", file=sys.stderr)
        return 1
    print(result)
    return 0


def completion_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resume Wagner PH origin under the authorized completion window"
    )
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--original-consumed-seconds", type=int, required=True)
    parser.add_argument("--extension-hard-seconds", type=int, default=14_400)
    parser.add_argument("--extension-soft-seconds", type=int, default=13_500)
    args = parser.parse_args(argv)
    try:
        result = run_wagner_ph_origin_campaign(
            args.parent,
            args.output,
            args.workers,
            _progress,
            completion_extension=True,
            original_consumed_seconds=args.original_consumed_seconds,
            extension_hard_seconds=args.extension_hard_seconds,
            extension_soft_seconds=args.extension_soft_seconds,
        )
    except TimeoutError as error:
        print(
            f"wagner-ph-origin completion stopped at time boundary: {error}",
            file=sys.stderr,
        )
        return 124
    except Exception as error:
        print(f"wagner-ph-origin completion failed: {error}", file=sys.stderr)
        return 1
    print(result)
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a Wagner PH origin campaign")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(wagner_ph_origin_status(args.output), indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a sealed Wagner PH origin campaign")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        value = verify_wagner_ph_origin_campaign(args.output)
    except Exception as error:
        print(f"wagner-ph-origin verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay one Wagner PH origin item")
    parser.add_argument("output", type=Path)
    parser.add_argument("item")
    args = parser.parse_args(argv)
    try:
        value = replay_wagner_ph_origin_item(args.output, args.item)
    except Exception as error:
        print(f"wagner-ph-origin replay failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value.get("matches") else 1
