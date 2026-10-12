"""Command-line interface for the ladder-web capsule."""

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

from .config import RUNGS, LadderConfig


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ladder-web")
    parser.add_argument("command", choices=("screen", "cone-shard", "cone"))
    parser.add_argument("--tiny", action="store_true")
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--n-shards", type=int, default=1)
    args = parser.parse_args(argv)
    config = LadderConfig.tiny() if args.tiny else LadderConfig()
    from .pipeline import run_lightcone, rung_screen

    if args.command == "screen":
        payload = {rung: rung_screen(config, rung) for rung in RUNGS}
    elif args.command == "cone-shard":
        payload = run_lightcone(config, n_shards=args.n_shards, shard=args.shard)
        payload = {k: v for k, v in payload.items() if k != "entries"}
    else:
        payload = run_lightcone(config, n_shards=args.n_shards)
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
