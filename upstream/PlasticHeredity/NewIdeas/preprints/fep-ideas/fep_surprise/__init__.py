"""Prospective compositional-surprise campaign for strict-8 GARD futures."""

import os
import tempfile
from pathlib import Path


# This campaign is batch-only.  Selecting a GUI backend in a worker launched by
# Codex, nohup, or tmux makes macOS abort while registering NSApplication.
_matplotlib_config = Path(tempfile.gettempdir()) / "fep-surprise-matplotlib"
_matplotlib_config.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_config))

from .config import CampaignConfig, profile_config

__all__ = ["CampaignConfig", "profile_config"]
