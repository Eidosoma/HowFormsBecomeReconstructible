"""Command-line interface for the glider-test capsule."""

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

from .config import LifeConfig


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="glider-test")
    parser.add_argument("command", choices=("observer",))
    parser.add_argument("--tiny", action="store_true")
    parser.add_argument("--flip-noise", type=float, default=None)
    parser.add_argument("--copy-error", type=float, default=None)
    args = parser.parse_args(argv)
    config = LifeConfig.tiny() if args.tiny else LifeConfig()
    overrides = {}
    if args.flip_noise is not None:
        overrides["flip_noise"] = args.flip_noise
    if args.copy_error is not None:
        overrides["copy_error"] = args.copy_error
    from .pipeline import run_observer

    payload = run_observer(config, screen_overrides=overrides or None)
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
