"""Plastic Heredity v2 GARD split: exact capacity and natural writing."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np

from .artifacts import read_json, sha256_file, verify_checksums, write_checksums, write_json
from .plastic_memory_gard import (
    _build_registry,
    _load_sim,
    _resolve_sim_path,
    _run_stage,
)


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _transfer_conditions() -> list[dict[str, Any]]:
    return [
        {
            "name": "gard-state-primary",
            "carriers": [
                "self_continuation",
                "state_transplant",
                "reset_both",
                "destination_matched_donor",
                "state_pattern_shuffle",
            ],
            "washout_ages": [0],
            "challenges": ["neutral_damage"],
            "futures_per_cell": 128,
        },
        {
            "name": "gard-state-recurrence",
            "carriers": ["state_transplant", "reset_both"],
            "washout_ages": [0],
            "challenges": ["forced_break"],
            "futures_per_cell": 128,
        },
        {
            "name": "gard-state-persistence",
            "carriers": ["state_transplant", "reset_both"],
            "washout_ages": [1, 2, 4, 8],
            "challenges": ["release_only", "neutral_damage", "forced_break"],
            "futures_per_cell": 64,
        },
    ]


def run_v2_gard_split(
    gard_root: Path,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Run exact transfer even when the natural GARD writer never calibrates."""

    if workers < 1 or workers > 8:
        raise ValueError("v2 GARD split requires 1-8 workers")
    sim_path = _resolve_sim_path(gard_root)
    sim = _load_sim(sim_path)
    fixture = sim.run_fissions(
        sim.make_initial_state(np.random.default_rng(2)),
        sim.make_beta(np.random.default_rng(1)),
        "02",
        2,
        np.random.default_rng(3),
    )
    if fixture["n_done"] != 2:
        raise AssertionError("frozen GARD fixture failed")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_checksums(destination)
        return destination
    provenance = {
        "format": "gre-plastic-heredity-v2-gard-provenance-v1",
        "gard_root": str(gard_root.resolve()),
        "sim_path": str(sim_path),
        "sim_sha256": sha256_file(sim_path),
        "source_access": "read-only",
        "capacity_and_writer_calibration_separated": True,
    }
    provenance_path = destination / "provenance.json"
    if provenance_path.is_file() and read_json(provenance_path) != provenance:
        raise ValueError("v2 GARD provenance changed")
    if not provenance_path.is_file():
        _atomic_json(provenance_path, provenance)

    exact_registry_path = destination / "exact-capacity-registry.json"
    if exact_registry_path.is_file():
        exact_registry = read_json(exact_registry_path)
    else:
        exact_registry = _build_registry(sim_path, 96, "v2-exact-capacity", progress)
        _atomic_json(exact_registry_path, exact_registry)
    exact_protocol = {
        "format": "gre-plastic-heredity-v2-gard-protocol-v1",
        "seed_label": "v2-exact-capacity",
        "calibration": False,
        "writer_mode": "exact_composition",
        "cue_doses": [[1.0, 1]],
        "conditions": _transfer_conditions(),
        "horizon": 32,
    }
    exact = _run_stage(
        sim_path,
        destination / "exact-capacity",
        exact_registry,
        exact_protocol,
        workers,
        progress,
    )
    exact_analysis = read_json(exact / "analysis.json")

    calibration_registry_path = destination / "natural-calibration-registry.json"
    if calibration_registry_path.is_file():
        calibration_registry = read_json(calibration_registry_path)
    else:
        calibration_registry = _build_registry(
            sim_path, 32, "v2-natural-calibration", progress
        )
        _atomic_json(calibration_registry_path, calibration_registry)
    calibration_protocol = {
        "format": "gre-plastic-heredity-v2-gard-protocol-v1",
        "seed_label": "v2-natural-calibration",
        "calibration": True,
        "writer_mode": "replacement_cue",
        "cue_doses": [
            [fraction, dwell]
            for fraction in (0.25, 0.50, 0.75, 1.0)
            for dwell in (1, 4, 16)
        ],
        "carriers": ["state_transplant"],
        "washout_ages": [0],
        "challenges": ["release_only"],
        "futures_per_cell": 16,
        "horizon": 8,
    }
    calibration = _run_stage(
        sim_path,
        destination / "natural-calibration",
        calibration_registry,
        calibration_protocol,
        workers,
        progress,
    )
    selection = read_json(calibration / "analysis.json")["selection"]
    _atomic_json(destination / "natural-cue-selection.json", selection)
    natural_confirmation_launched = False
    natural_analysis = None
    if all(value["ready"] for value in selection.values()):
        natural_registry_path = destination / "natural-confirmation-registry.json"
        if natural_registry_path.is_file():
            natural_registry = read_json(natural_registry_path)
        else:
            natural_registry = _build_registry(
                sim_path, 200, "v2-natural-confirmation", progress
            )
            _atomic_json(natural_registry_path, natural_registry)
        natural_protocol = {
            "format": "gre-plastic-heredity-v2-gard-protocol-v1",
            "seed_label": "v2-natural-confirmation",
            "calibration": False,
            "writer_mode": "replacement_cue",
            "cue_by_candidate": {
                model.removeprefix("gard-"): [
                    [value["cue"]["fraction"], value["cue"]["dwell"]]
                ]
                for model, value in selection.items()
            },
            "conditions": _transfer_conditions(),
            "horizon": 32,
        }
        natural = _run_stage(
            sim_path,
            destination / "natural-confirmation",
            natural_registry,
            natural_protocol,
            workers,
            progress,
        )
        natural_analysis = read_json(natural / "analysis.json")
        natural_confirmation_launched = True
    manifest = {
        "format": "gre-plastic-heredity-v2-gard-manifest-v1",
        "completed": True,
        "exact_capacity_gates": exact_analysis["gates"],
        "exact_capacity_passed": all(
            value["passed"] for value in exact_analysis["gates"].values()
        ),
        "natural_writer_selection": selection,
        "natural_confirmation_launched": natural_confirmation_launched,
        "natural_transfer_gates": (
            natural_analysis["gates"] if natural_analysis is not None else None
        ),
    }
    _atomic_json(destination / "manifest.json", manifest)
    (destination / "report.md").write_text(
        "# Plastic Heredity v2 GARD split\n\n"
        f"- Exact composition-transfer capacity: {manifest['exact_capacity_passed']}\n"
        f"- Natural writer calibrated: {natural_confirmation_launched}\n"
        "- The exact-capacity result is retained even if natural writing fails.\n",
        encoding="utf-8",
    )
    write_checksums(destination)
    verify_checksums(destination)
    return destination
