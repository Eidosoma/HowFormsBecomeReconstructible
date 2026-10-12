"""Frozen finalist and candidate selection for Wagner induction rescue."""

from __future__ import annotations

from typing import Any


def _number(value: Any, default: float = float("-inf")) -> float:
    return float(value) if value is not None else default


def _rank_key(cell: dict[str, Any], gate: str) -> tuple[Any, ...]:
    acquisition = min(
        _number(cell["histories"][history]["exact_acquisition"]["lower"])
        for history in ("A", "B")
    )
    cue_gain = cell["metrics"]["cue_gain_over_no_cue"]
    crossover = cell["metrics"]["correct_minus_wrong"]
    model = cell["model"]
    intervention = cell["intervention"]
    mode_order = {
        "initialization": 0,
        "target_field": 1,
        "persistent_hard": 2,
    }
    return (
        not bool(cell.get(gate, False)),
        -_number(cue_gain.get("lower")),
        -_number(cue_gain.get("mean")),
        -_number(crossover.get("lower")),
        -_number(crossover.get("mean")),
        -acquisition,
        -float(model["gamma_variance"]),
        str(model["variant"]) != "wagner_sequential",
        mode_order.get(str(intervention["mode"]), 99),
        float(intervention["field_strength"]),
        float(intervention["fraction"]) * int(intervention["dwell"]),
        str(cell["condition"]),
    )


def select_screen_finalists(analysis: dict[str, Any]) -> dict[str, Any]:
    """Carry diverse screen winners into a fresh narrow replication."""

    candidates = [
        cell
        for cell in analysis["cells"].values()
        if cell["role"] == "candidate"
    ]
    ranked = sorted(candidates, key=lambda cell: _rank_key(cell, "screen_passed"))
    selected: list[dict[str, Any]] = []
    for mode in ("initialization", "target_field", "persistent_hard"):
        match = next(
            (cell for cell in ranked if cell["intervention"]["mode"] == mode),
            None,
        )
        if match is not None:
            selected.append(match)
    noisy = next(
        (
            cell
            for cell in ranked
            if abs(float(cell["model"]["gamma_variance"]) - 0.10) < 1e-12
        ),
        None,
    )
    if noisy is not None and noisy["condition"] not in {
        cell["condition"] for cell in selected
    }:
        selected.append(noisy)
    selected = selected[:4]
    return {
        "format": "gre-wagner-rescue-screen-selection-v1",
        "screen_ready_any": any(cell["screen_passed"] for cell in candidates),
        "selected": selected,
        "selected_condition_ids": [cell["condition"] for cell in selected],
        "ranking": [cell["condition"] for cell in ranked],
        "outcome_signs_used": True,
        "role": "exploratory fresh-cohort finalist generation",
    }


def select_replication_candidate(analysis: dict[str, Any]) -> dict[str, Any]:
    """Select one passing narrow-replication cell for untouched validation."""

    candidates = [
        cell
        for cell in analysis["cells"].values()
        if cell["role"] == "candidate"
    ]
    ranked = sorted(
        candidates, key=lambda cell: _rank_key(cell, "replication_passed")
    )
    selected = next(
        (cell for cell in ranked if cell["replication_passed"]), None
    )
    return {
        "format": "gre-wagner-rescue-replication-selection-v1",
        "selected": selected,
        "selected_condition_id": selected["condition"] if selected else None,
        "passing_condition_ids": [
            cell["condition"] for cell in ranked if cell["replication_passed"]
        ],
        "ranking": [cell["condition"] for cell in ranked],
        "outcome_signs_used": True,
        "role": "exploratory untouched validation candidate generation",
    }
