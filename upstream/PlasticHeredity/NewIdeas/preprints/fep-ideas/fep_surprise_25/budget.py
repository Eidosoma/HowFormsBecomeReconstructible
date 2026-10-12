from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .config import Campaign25Config


class TimeBudgetExhausted(RuntimeError):
    pass


def budget_path(run_root: Path, profile: str) -> Path:
    return run_root.resolve() / profile / "budget_start.json"


def ensure_budget(run_root: Path, config: Campaign25Config) -> dict[str, Any]:
    path = budget_path(run_root, config.profile)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format": "fep-surprise-25-budget-v1",
        "started_epoch": time.time(),
        "budget_seconds": config.scientific_budget_seconds,
        "graceful_stop_seconds": config.graceful_stop_seconds,
    }
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
    return payload


def budget_status(run_root: Path, config: Campaign25Config) -> dict[str, Any]:
    payload = ensure_budget(run_root, config)
    elapsed = max(0.0, time.time() - float(payload["started_epoch"]))
    return {
        **payload,
        "elapsed_seconds": elapsed,
        "remaining_seconds": max(0.0, config.scientific_budget_seconds - elapsed),
        "graceful_remaining_seconds": max(
            0.0, config.graceful_stop_seconds - elapsed
        ),
    }


def guard_budget(run_root: Path, config: Campaign25Config, stage: str) -> None:
    status = budget_status(run_root, config)
    if status["elapsed_seconds"] >= config.graceful_stop_seconds:
        raise TimeBudgetExhausted(
            f"TIME_BUDGET_EXHAUSTED_NO_VERDICT at {stage}: "
            f"{status['elapsed_seconds']:.1f}s elapsed"
        )
