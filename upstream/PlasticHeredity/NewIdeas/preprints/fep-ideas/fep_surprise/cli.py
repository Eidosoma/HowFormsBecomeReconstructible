from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .campaign import (
    confirm,
    develop,
    register,
    registration_path,
    replay,
    status,
    verify_registration,
)
from .config import profile_config
from .validation import validate


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "command",
        choices=("register", "validate", "develop", "confirm", "replay", "all", "status"),
    )
    value.add_argument("--profile", choices=("smoke", "quick", "full"), default="smoke")
    value.add_argument("--run-root", type=Path, default=Path("runs"))
    value.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    return value


def main() -> None:
    args = parser().parse_args()
    config = profile_config(args.profile)
    if args.command == "status":
        print(json.dumps(status(args.run_root, args.profile), indent=2, sort_keys=True))
        return
    if args.command in ("register", "all"):
        path = register(args.run_root, config)
        print(f"registered: {path}", flush=True)
    else:
        verify_registration(registration_path(args.run_root, args.profile), config)
    if args.command in ("validate", "all"):
        result = validate(config, args.run_root / args.profile / "validation")
        print(f"validation: {result}", flush=True)
    if args.command in ("develop", "all"):
        path = develop(args.run_root, config, args.workers)
        print(f"development: {path}", flush=True)
    if args.command in ("confirm", "all"):
        path = confirm(args.run_root, config, args.workers)
        print(f"confirmation: {path}", flush=True)
    if args.command in ("replay", "all"):
        path = replay(args.run_root, config)
        print(f"replay: {path}", flush=True)


if __name__ == "__main__":
    main()

