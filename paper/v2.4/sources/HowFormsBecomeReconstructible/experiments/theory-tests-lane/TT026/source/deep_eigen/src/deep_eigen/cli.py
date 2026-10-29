"""Command-line interface for the deep-eigen capsule."""

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

from .config import DeepEigenConfig


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="deep-eigen")
    parser.add_argument("command", choices=("gates",))
    parser.parse_args(argv)
    from .pipeline import run_gates

    payload = run_gates(DeepEigenConfig())
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
