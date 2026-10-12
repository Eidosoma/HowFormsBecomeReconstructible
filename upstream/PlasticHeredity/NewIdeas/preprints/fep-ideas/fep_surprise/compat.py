"""Read-only bridge to the relocated completed simulator package."""

from __future__ import annotations

import os
import sys
from pathlib import Path

CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
CODEX_ROOT = Path(
    os.environ.get(
        "PLASTIC_HEREDITY_ROOT",
        str(CAMPAIGN_ROOT.parents[2] / "replicators.13.8.2026.codex"),
    )
).expanduser().resolve()

required = (
    "plastic_heredity/config.py",
    "plastic_heredity/regime_confirmation.py",
    "plastic_heredity/seeds.py",
    "plastic_heredity/simulator.py",
)
missing = [name for name in required if not (CODEX_ROOT / name).is_file()]
if missing:
    raise FileNotFoundError(
        f"simulator root {CODEX_ROOT} is missing required sources: {missing}"
    )
if str(CODEX_ROOT) not in sys.path:
    sys.path.insert(0, str(CODEX_ROOT))
