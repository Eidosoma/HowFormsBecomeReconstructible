"""Resolve the retained simulator explicitly without modifying it."""

from __future__ import annotations

import os
import sys
from pathlib import Path


CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
PLASTIC_HEREDITY_ROOT = Path(
    os.environ.get(
        "PLASTIC_HEREDITY_ROOT",
        str(
            CAMPAIGN_ROOT.parents[2]
            / "replicators.13.8.2026.codex"
        ),
    )
).expanduser().resolve()

REQUIRED_SIMULATOR_SOURCES = (
    "plastic_heredity/config.py",
    "plastic_heredity/regime_confirmation.py",
    "plastic_heredity/seeds.py",
    "plastic_heredity/simulator.py",
)


def validate_simulator_root() -> Path:
    missing = [
        name for name in REQUIRED_SIMULATOR_SOURCES if not (PLASTIC_HEREDITY_ROOT / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"simulator root {PLASTIC_HEREDITY_ROOT} is missing: {missing}"
        )
    return PLASTIC_HEREDITY_ROOT


validate_simulator_root()
if str(PLASTIC_HEREDITY_ROOT) not in sys.path:
    sys.path.insert(0, str(PLASTIC_HEREDITY_ROOT))

