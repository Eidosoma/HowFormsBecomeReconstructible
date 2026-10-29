"""Command-line interface for the setpoint-rewrite capsule."""

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

from .config import RewriteConfig


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="setpoint-rewrite")
    parser.add_argument("command", choices=("shard", "gates"))
    parser.add_argument("--tiny", action="store_true")
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--n-shards", type=int, default=1)
    args = parser.parse_args(argv)
    config = RewriteConfig.tiny() if args.tiny else RewriteConfig()
    from .pipeline import run_gates, run_shard

    if args.command == "shard":
        payload = run_shard(config, args.shard, args.n_shards)
        payload = {k: v for k, v in payload.items() if k != "entries"}
    else:
        payload = run_gates(config, n_shards=args.n_shards)
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
