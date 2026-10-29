"""Command-line interface for the voltage-web capsule."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
_CACHE = Path(__file__).resolve().parents[2] / ".cache"
_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE))

from .config import VoltageConfig


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="voltage-web")
    parser.add_argument("command", choices=("screen", "regeneration"))
    parser.add_argument("--tiny", action="store_true")
    parser.add_argument("--point", type=int, default=None)
    parser.add_argument("--coupling", type=float, default=None)
    parser.add_argument("--sigma", type=float, default=None)
    parser.add_argument("--activity-budget", type=int, default=None)
    args = parser.parse_args(argv)
    config = VoltageConfig.tiny() if args.tiny else VoltageConfig()
    from .pipeline import run_regeneration, run_screen

    if args.command == "screen":
        payload = run_screen(config, point=args.point)
    else:
        overrides = {
            k: v for k, v in (
                ("coupling", args.coupling), ("sigma", args.sigma),
                ("activity_budget", args.activity_budget),
            ) if v is not None
        }
        payload = run_regeneration(config, overrides or None)
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
