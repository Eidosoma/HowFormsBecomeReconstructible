"""Command-line interface for the xeno-bridge capsule."""

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
(_CACHE / "matplotlib").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_CACHE / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE))

from .config import XenoConfig, results_root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xeno-bridge",
        description="Non-GARD binary-polymer substrate for cross-formalism transfer.",
    )
    parser.add_argument(
        "command", choices=("validate", "screen", "bridge-dev", "bridge-confirm", "status")
    )
    parser.add_argument("--tiny", action="store_true", help="run the L=3 fixture")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    config = XenoConfig.tiny() if args.tiny else XenoConfig()
    payload = None
    if args.command == "validate":
        from .chemistry import build_chemistry

        config.validate()
        chemistry = build_chemistry(config)
        payload = {
            "config_digest": config.digest(),
            "n_species": chemistry.n_species,
            "n_reaction_pairs": chemistry.n_reactions,
        }
    elif args.command == "screen":
        from .screen import run_screen

        payload = run_screen(config)
    elif args.command == "bridge-dev":
        from .bridge import run_bridge

        payload = run_bridge(config, phase="dev")
    elif args.command == "bridge-confirm":
        import json as _json

        from .bridge import run_bridge
        from .config import results_root as _results

        dev_path = _results(config) / "bridge_dev.json"
        if not dev_path.exists():
            raise SystemExit("bridge-dev must run (and freeze its scaler) first")
        dev = _json.loads(dev_path.read_text())
        payload = run_bridge(
            config, phase="confirm", frozen_scaler=dev["summary"]["scaler"]
        )
    elif args.command == "status":
        results = results_root(config)
        payload = {
            "mode": config.mode,
            "artifacts": {name: (results / name).exists() for name in ("screen.json",)},
        }
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
