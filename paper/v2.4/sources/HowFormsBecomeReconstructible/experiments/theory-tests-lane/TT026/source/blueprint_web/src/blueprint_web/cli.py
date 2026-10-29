"""Command-line interface for the blueprint-web capsule."""

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

from .config import BlueprintConfig


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="blueprint-web")
    parser.add_argument("command", choices=("calibrate",))
    args = parser.parse_args(argv)
    from .pipeline import run_calibration

    payload = run_calibration(BlueprintConfig())
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
