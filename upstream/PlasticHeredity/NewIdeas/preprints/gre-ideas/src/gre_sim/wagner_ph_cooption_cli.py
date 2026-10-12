"""Command-line interface for Wagner PH carrier meaning and co-option v1."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .artifacts import read_json
from .wagner_ph_cooption_campaign import (
    replay_wagner_ph_cooption,
    run_wagner_ph_cooption_campaign,
    run_wagner_ph_cooption_confirmation,
    verify_wagner_ph_cooption_confirmation,
    verify_wagner_ph_cooption_campaign,
    wagner_ph_cooption_status,
)


def _progress(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[wagner-ph-cooption-v1 {timestamp}] {message}", flush=True)


def campaign_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Wagner PH Co-option v1")
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_wagner_ph_cooption_campaign(
            args.parent, args.output, args.workers, _progress, smoke=args.smoke
        )
    except TimeoutError as error:
        print(f"Co-option campaign stopped at time boundary: {error}", file=sys.stderr)
        return 124
    except Exception as error:
        print(f"Co-option campaign failed: {error}", file=sys.stderr)
        return 1
    print(result)
    return 0


def status_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a Wagner PH Co-option run")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(wagner_ph_cooption_status(args.output), indent=2, sort_keys=True))
    return 0


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a sealed Wagner PH Co-option run")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        registration = read_json(args.output / "registration.json")
        value = (
            verify_wagner_ph_cooption_confirmation(args.output)
            if registration.get("format")
            == "gre-wagner-ph-cooption-confirmation-campaign-v1"
            else verify_wagner_ph_cooption_campaign(args.output)
        )
    except Exception as error:
        print(f"Co-option verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


def replay_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay one co-option unit")
    parser.add_argument("output", type=Path)
    parser.add_argument("stage", choices=("atlas", "evolution", "audit"))
    parser.add_argument("identifier")
    args = parser.parse_args(argv)
    try:
        value = replay_wagner_ph_cooption(args.output, args.stage, args.identifier)
    except Exception as error:
        print(f"Co-option replay failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["matches"] else 1


def confirmation_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run gated fresh co-option confirmation")
    parser.add_argument("--exploration", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--authorize-confirmation", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_wagner_ph_cooption_confirmation(
            args.exploration,
            args.output,
            args.workers,
            _progress,
            authorized=args.authorize_confirmation,
        )
    except TimeoutError as error:
        print(f"Co-option confirmation stopped at time boundary: {error}", file=sys.stderr)
        return 124
    except Exception as error:
        print(f"Co-option confirmation failed: {error}", file=sys.stderr)
        return 1
    print(result)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wagner PH Co-option v1")
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
    replay.add_argument("stage", choices=("atlas", "evolution", "audit"))
    replay.add_argument("identifier")
    confirmation = subparsers.add_parser("confirm")
    confirmation.add_argument("--exploration", required=True, type=Path)
    confirmation.add_argument("--output", required=True, type=Path)
    confirmation.add_argument("--workers", type=int, default=4)
    confirmation.add_argument("--authorize-confirmation", action="store_true")
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
    if args.command == "replay":
        return replay_main([str(args.output), args.stage, args.identifier])
    values = [
        "--exploration",
        str(args.exploration),
        "--output",
        str(args.output),
        "--workers",
        str(args.workers),
    ]
    if args.authorize_confirmation:
        values.append("--authorize-confirmation")
    return confirmation_main(values)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
