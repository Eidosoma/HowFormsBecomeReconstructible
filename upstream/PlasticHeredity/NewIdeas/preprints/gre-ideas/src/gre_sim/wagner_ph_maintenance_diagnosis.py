"""Sealed Architecture-v1 reanalysis for Adaptive Maintenance v1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .wagner_ph_architecture_campaign import verify_wagner_ph_architecture_campaign
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_maintenance_config import MAINTENANCE_FORMAT, MaintenanceSpec


DIAGNOSIS_FORMAT = f"{MAINTENANCE_FORMAT}-diagnosis"
FEATURE_NAMES = (
    "pair_hamming_fraction",
    "mean_absolute_weight",
    "weight_standard_deviation",
    "maximum_absolute_weight",
    "maximum_target_row_share",
    "maximum_source_column_share",
    "spectral_norm",
    "repair_strength",
    "carrier_k_fraction",
    "carrier_bits_fraction",
    "carrier_write_rate",
    "carrier_coupling",
    "carrier_decay",
    "carrier_hysteresis",
)


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _task_interval(
    values: dict[str, float], spec: MaintenanceSpec, label: str
) -> dict[str, Any]:
    return _interval(
        values.values(),
        spec.diagnosis_seed,
        f"adaptive-maintenance-diagnosis.{label}",
        spec.bootstrap_repetitions,
        spec.interval_level,
    )


def _cell(value: dict[str, Any], persistence: float = 0.9) -> dict[str, Any]:
    return next(
        cell
        for cell in value["cells"]
        if abs(float(cell["persistence"]) - persistence) < 1e-12
        and abs(float(cell["cue_fraction"])) < 1e-12
    )


def _correct(cell: dict[str, Any], intervention: str, generation: int) -> float:
    return float(
        cell["conditions"][intervention]["checkpoints"][str(generation)]["correct_rate"]
    )


def _paired_pedigree(parent: Path, spec: MaintenanceSpec) -> dict[str, Any]:
    directory = parent / "confirmation" / "pedigree" / "populations"
    task_effects: dict[str, dict[str, Any]] = {}
    paired_rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("mh_repair_uniform.task-*.json")):
        value = read_json(path)
        natural = {
            (row["root_index"], row["lineage_index"], row["distance"]): row
            for row in value["rows"]
            if row["mode"] == "natural"
        }
        repair_off = {
            (row["root_index"], row["lineage_index"], row["distance"]): row
            for row in value["rows"]
            if row["mode"] == "repair_off"
        }
        if set(natural) != set(repair_off):
            raise ValueError("Architecture repair-on/off pedigree is not paired")
        for key in sorted(natural):
            on, off = natural[key], repair_off[key]
            paired_rows.append(
                {
                    "task_index": value["task_index"],
                    "root_index": key[0],
                    "lineage_index": key[1],
                    "distance": key[2],
                    "root_information": float(on["root_information"]),
                    "natural_information": float(on["descendant_information"]),
                    "repair_off_information": float(off["descendant_information"]),
                    "repair_information_effect": float(on["descendant_information"])
                    - float(off["descendant_information"]),
                    "natural_retained": bool(on["retained"]),
                    "repair_off_retained": bool(off["retained"]),
                    "retention_effect": float(on["retained"]) - float(off["retained"]),
                    "collapse_prevented": float(off["collapsed"]) - float(on["collapsed"]),
                    "repair_rescue": bool(
                        float(off["descendant_information"]) <= 0.0
                        and float(on["descendant_information"]) > 0.0
                    ),
                    "repair_harm": bool(
                        float(on["descendant_information"]) <= 0.0
                        and float(off["descendant_information"]) > 0.0
                    ),
                }
            )
    task_indices = sorted({int(row["task_index"]) for row in paired_rows})
    if not task_indices or task_indices != list(range(len(task_indices))):
        raise ValueError("Architecture confirmation diagnosis tasks are incomplete")
    for distance in spec.pedigree_depths:
        selected = [row for row in paired_rows if row["distance"] == distance]
        fields = (
            "repair_information_effect",
            "retention_effect",
            "collapse_prevented",
            "repair_rescue",
            "repair_harm",
        )
        summaries: dict[str, Any] = {}
        for field in fields:
            values = {
                str(task): float(
                    np.mean(
                        [float(row[field]) for row in selected if row["task_index"] == task]
                    )
                )
                for task in task_indices
            }
            summaries[field] = {
                "task_values": values,
                "interval": _task_interval(values, spec, f"repair.d{distance}.{field}"),
            }
        task_effects[str(distance)] = summaries
    strata: dict[str, Any] = {}
    bounds = {
        "nonpositive": (-float("inf"), 0.0),
        "weak_positive": (0.0, 0.125),
        "moderate_positive": (0.125, 0.25),
        "strong_positive": (0.25, float("inf")),
    }
    for label, (lower, upper) in bounds.items():
        selected = [
            row
            for row in paired_rows
            if row["distance"] == 4 and lower < row["root_information"] <= upper
        ]
        strata[label] = {
            "rows": len(selected),
            "mean_root_information": float(np.mean([row["root_information"] for row in selected])) if selected else None,
            "mean_repair_information_effect": float(np.mean([row["repair_information_effect"] for row in selected])) if selected else None,
            "repair_rescue_fraction": float(np.mean([row["repair_rescue"] for row in selected])) if selected else None,
            "repair_harm_fraction": float(np.mean([row["repair_harm"] for row in selected])) if selected else None,
        }
    return {
        "source_arm": "mh_repair_uniform",
        "paired_rows": paired_rows,
        "by_distance": task_effects,
        "distance_four_by_root_information": strata,
        "continuous_effects_are_primary_thresholds_are_descriptive": True,
    }


def _write_store_read(parent: Path, spec: MaintenanceSpec) -> dict[str, Any]:
    audit = parent / "confirmation" / "audit" / "populations"
    by_arm: dict[str, dict[str, Any]] = {}
    arms = ("mh_repair_uniform", "mh_single_ordinary")
    for arm in arms:
        values: dict[str, dict[str, float]] = {}
        for path in sorted(audit.glob(f"{arm}.population-*.json")):
            result = read_json(path)
            cell = _cell(result)
            first = 1
            last = max(int(key) for key in cell["conditions"]["natural"]["checkpoints"])
            values[str(result["population_index"])] = {
                "write_dependence_f1": _correct(cell, "natural", first)
                - _correct(cell, "founder_write_off", first),
                "store_renewal_dependence_final": _correct(cell, "natural", last)
                - _correct(cell, "renewal_off", last),
                "read_dependence_final": _correct(cell, "natural", last)
                - _correct(cell, "reader_off", last),
                "history_information_final": _correct(cell, "natural", last)
                - _correct(cell, "independent_history", last),
            }
        by_arm[arm] = {
            "task_values": values,
            "intervals": {
                field: _task_interval(
                    {task: row[field] for task, row in values.items()},
                    spec,
                    f"write-store-read.{arm}.{field}",
                )
                for field in next(iter(values.values()))
            },
        }
    contrasts: dict[str, Any] = {}
    for field in next(iter(by_arm[arms[0]]["task_values"].values())):
        values = {
            task: float(row[field])
            - float(by_arm[arms[1]]["task_values"][task][field])
            for task, row in by_arm[arms[0]]["task_values"].items()
        }
        contrasts[field] = {
            "task_values": values,
            "interval": _task_interval(values, spec, f"write-store-read.repair-minus-single.{field}"),
        }
    return {
        "arms": by_arm,
        "repair_minus_single": contrasts,
        "source_final_generation": last,
        "interpretation": (
            "write, renewal/store, and reader interventions are distinct causal cuts; "
            "their numerical effects need not add because the pathway is nonlinear"
        ),
    }


def _features(population: dict[str, Any]) -> list[float]:
    weights = np.asarray(
        population["selected_effective_genotype"]["rulebook"]["weights"], dtype=float
    )
    absolute = np.abs(weights)
    total = max(float(absolute.sum()), 1e-12)
    carrier = population["selected"]["carrier"]
    pair = population["task"]["pair"]
    genes = weights.shape[0]
    hamming = int(pair["left_state"] ^ pair["right_state"]).bit_count() / genes
    return [
        hamming,
        float(absolute.mean()),
        float(weights.std()),
        float(absolute.max()),
        float(absolute.sum(axis=1).max() / total),
        float(absolute.sum(axis=0).max() / total),
        float(np.linalg.norm(weights, ord=2)),
        float(population["selected"]["interpreter"]["repair_strength"]),
        float(carrier["k"]) / genes,
        float(carrier["bits_per_mark"]) / 8.0,
        float(carrier["write_rate"]),
        float(carrier["coupling"]),
        float(carrier["decay"]),
        float(carrier["hysteresis"]),
    ]


def _fit_ridge(x: np.ndarray, y: np.ndarray, ridge: float = 1.0) -> tuple[np.ndarray, float]:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale == 0.0] = 1.0
    z = (x - mean) / scale
    coefficients = np.linalg.solve(z.T @ z + ridge * np.eye(z.shape[1]), z.T @ (y - y.mean()))
    return coefficients, float(y.mean())


def _predictor(parent: Path, paired: dict[str, Any], spec: MaintenanceSpec) -> dict[str, Any]:
    populations = [
        read_json(path)
        for path in sorted(
            (parent / "confirmation" / "evolution" / "populations").glob(
                "mh_repair_uniform.population-*.json"
            )
        )
    ]
    outcomes = paired["by_distance"]["4"]["repair_information_effect"]["task_values"]
    x = np.asarray([_features(value) for value in populations], dtype=float)
    y = np.asarray([outcomes[str(value["population_index"])] for value in populations])
    predicted = []
    for heldout in range(len(y)):
        mask = np.arange(len(y)) != heldout
        train_x, train_y = x[mask], y[mask]
        mean = train_x.mean(axis=0)
        scale = train_x.std(axis=0)
        scale[scale == 0.0] = 1.0
        z = (train_x - mean) / scale
        coefficients = np.linalg.solve(
            z.T @ z + np.eye(z.shape[1]), z.T @ (train_y - train_y.mean())
        )
        predicted.append(
            float(train_y.mean() + ((x[heldout] - mean) / scale) @ coefficients)
        )
    correlation = (
        float(np.corrcoef(y, predicted)[0, 1])
        if np.std(y) > 0.0 and np.std(predicted) > 0.0
        else None
    )
    coefficients, intercept = _fit_ridge(x, y)
    ranking = sorted(
        (
            {"feature": name, "standardized_coefficient": float(value)}
            for name, value in zip(FEATURE_NAMES, coefficients)
        ),
        key=lambda value: -abs(value["standardized_coefficient"]),
    )
    return {
        "features": list(FEATURE_NAMES),
        "ridge": 1.0,
        "leave_one_task_out_predictions": {
            str(population["population_index"]): float(predicted[index])
            for index, population in enumerate(populations)
        },
        "observed_task_outcomes": {
            str(population["population_index"]): float(y[index])
            for index, population in enumerate(populations)
        },
        "leave_one_task_out_correlation": correlation,
        "full_fit_intercept": intercept,
        "full_fit_coefficient_ranking": ranking,
        "diagnostic_only_small_n_no_selection_or_gate_use": True,
    }


def run_maintenance_diagnosis(
    spec: MaintenanceSpec, parent: Path, destination: Path
) -> Path:
    spec.validate()
    parent = parent.resolve()
    destination = destination.resolve()
    parent_verification = verify_wagner_ph_architecture_campaign(parent)
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_maintenance_diagnosis(destination)
        return destination
    payload = {
        "spec": spec.to_dict(),
        "parent_checksum": sha256_file(parent / "SHA256SUMS"),
    }
    digest = canonical_digest(payload)
    registration = {
        "format": f"{DIAGNOSIS_FORMAT}-registration",
        "protocol_digest": digest,
        **payload,
        "parent": str(parent),
        "parent_verification": parent_verification,
        "uses_only_sealed_parent_confirmation_evidence": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing maintenance diagnosis registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    paired = _paired_pedigree(parent, spec)
    architecture_analysis = read_json(parent / "diagnosis" / "analysis.json")
    result = {
        "format": f"{DIAGNOSIS_FORMAT}-analysis",
        "continuous_repair_insurance": paired,
        "write_store_read": _write_store_read(parent, spec),
        "network_predictor": _predictor(parent, paired, spec),
        "architecture_factorial_reference": {
            "analysis_digest": architecture_analysis["analysis_digest"],
            "repair_carrier_factorial": architecture_analysis[
                "primary_repair_carrier_factorial"
            ],
            "note": "sealed Architecture-v1 topology x repair factorial; diagnostic only",
        },
        "cannot_select_cancel_or_modify_registered_development_arms": True,
    }
    result["analysis_digest"] = canonical_digest(result)
    _atomic_json(destination / "analysis.json", result)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{DIAGNOSIS_FORMAT}-manifest",
            "protocol_digest": digest,
            "analysis_digest": result["analysis_digest"],
            "paired_rows": len(paired["paired_rows"]),
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_maintenance_diagnosis(destination)
    return destination


def verify_maintenance_diagnosis(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    analysis = read_json(directory / "analysis.json")
    MaintenanceSpec.from_dict(registration["spec"])
    if registration.get("format") != f"{DIAGNOSIS_FORMAT}-registration":
        raise ValueError("maintenance diagnosis registration format mismatch")
    if manifest.get("format") != f"{DIAGNOSIS_FORMAT}-manifest":
        raise ValueError("maintenance diagnosis manifest format mismatch")
    payload = {key: registration[key] for key in ("spec", "parent_checksum")}
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("maintenance diagnosis protocol mismatch")
    if sha256_file(Path(registration["parent"]) / "SHA256SUMS") != registration["parent_checksum"]:
        raise ValueError("sealed Architecture-v1 parent changed")
    verify_wagner_ph_architecture_campaign(Path(registration["parent"]))
    analysis_payload = dict(analysis)
    archived = analysis_payload.pop("analysis_digest", None)
    if archived != canonical_digest(analysis_payload):
        raise ValueError("maintenance diagnosis analysis digest mismatch")
    if (
        manifest["protocol_digest"] != registration["protocol_digest"]
        or manifest["analysis_digest"] != analysis["analysis_digest"]
    ):
        raise ValueError("maintenance diagnosis references differ")
    return {
        "verified": True,
        "paired_rows": manifest["paired_rows"],
        "checksums": len(checksums),
    }


__all__ = (
    "FEATURE_NAMES",
    "run_maintenance_diagnosis",
    "verify_maintenance_diagnosis",
)
