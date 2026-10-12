"""Frozen Stage A design-validation acceptance audit."""

from __future__ import annotations

import collections
import math
from pathlib import Path
from typing import Any

from .config import StudySpec
from .study import load_run, recompute_analysis, verify_run


EXPECTED_FUTURES = 573_440
EXPECTED_RULEBOOKS_PER_ENGINE = 32
MINIMUM_CAPTURE_RATE = 0.60
MINIMUM_RELIABILITY = 0.80
MINIMUM_FORCED_CONVERGENCE_RATE = 0.80
ISOMORPHIC_RATE_MARGIN = 0.03
KAPPA_GRID = (0.0, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)

SUMMARY_FIELDS = (
    "destination",
    "strict_event",
    "first_break",
    "stable_destination_cycle",
    "active_capture",
    "old_return",
    "point_cycles",
    "cycle_cycles",
    "nonconvergent_cycles",
    "trace_digest",
)


def _finite_primary(analysis: dict[str, Any]) -> bool:
    values: list[float] = []
    for result in analysis["primary"].values():
        values.extend(
            [
                float(result["mean_log_loss_gain"]),
                float(result["mean_brier_gain"]),
                float(result["committor_accuracy"]),
                float(result["committor_ece"]),
                *(float(value) for value in result["interval"]),
            ]
        )
    for result in analysis["history_contrast"].values():
        values.append(float(result["mean_self_minus_donor_gain"]))
        values.extend(float(value) for value in result["interval"])
    return all(math.isfinite(value) for value in values)


def _secondary_rate(
    analysis: dict[str, Any],
    engine: str,
    mode: str,
    arm: str,
    carryover: float,
    name: str,
) -> float:
    key = f"{engine}.sampled.{mode}.{arm}.lambda-{carryover:g}"
    return float(analysis["secondary"][key][name])


def audit_stage_a_run(directory: Path) -> dict[str, Any]:
    """Apply the preregistered engineering-readiness checks to one sealed run."""

    verification = verify_run(directory)
    spec, registry, records, analysis = load_run(directory)
    if spec != StudySpec.stage_a_v2():
        raise ValueError("run does not use the frozen Stage A v2 protocol")

    source_counts = collections.Counter(
        bundle["engine"] for bundle in registry["sources"]
    )
    cell_counts: dict[tuple[Any, ...], collections.Counter[str]] = (
        collections.defaultdict(collections.Counter)
    )
    for record in records:
        key = (
            record["engine"],
            record["source_id"],
            int(record["state_id"]),
            record["arm"],
            float(record["carryover"]),
            record["inheritance_mode"],
        )
        cell_counts[key][record["half"]] += 1
    expected_cells = (
        len(registry["sources"])
        * spec.launch_states_per_rulebook
        * len(spec.arms)
        * len(spec.carryover_values)
        * len(spec.inheritance_modes)
    )
    complete_cells = len(cell_counts) == expected_cells and all(
        counts == {"A": 32, "B": 32} for counts in cell_counts.values()
    )

    lookup = {
        (
            record["engine"],
            record["source_id"],
            int(record["state_id"]),
            record["arm"],
            float(record["carryover"]),
            int(record["future_index"]),
            record["inheritance_mode"],
        ): record
        for record in records
    }
    zero_pairs = 0
    zero_pairs_equal = True
    for record in records:
        if record["inheritance_mode"] != "self" or float(record["carryover"]) != 0.0:
            continue
        donor_key = (
            record["engine"],
            record["source_id"],
            int(record["state_id"]),
            record["arm"],
            0.0,
            int(record["future_index"]),
            "donor_shuffled",
        )
        donor = lookup.get(donor_key)
        zero_pairs += 1
        if donor is None or any(record[name] != donor[name] for name in SUMMARY_FIELDS):
            zero_pairs_equal = False
            break

    reliability = analysis["split_half_destination_reliability"]
    reliability_ready = all(
        float(value) >= MINIMUM_RELIABILITY for value in reliability.values()
    )
    capture_rates = {
        f"{engine}.{mode}": _secondary_rate(
            analysis,
            engine,
            mode,
            "acute_mismatch",
            1.0,
            "active_capture_rate",
        )
        for engine in spec.engines
        for mode in spec.inheritance_modes
    }
    capture_ready = all(
        value >= MINIMUM_CAPTURE_RATE for value in capture_rates.values()
    )
    forced_rates = {
        f"{engine}.{mode}.lambda-{carryover:g}": _secondary_rate(
            analysis,
            engine,
            mode,
            "single_attractor",
            carryover,
            "strict_rate",
        )
        for engine in spec.engines
        for mode in spec.inheritance_modes
        for carryover in spec.carryover_values
    }
    forced_ready = all(
        value >= MINIMUM_FORCED_CONVERGENCE_RATE for value in forced_rates.values()
    )
    isomorphic_differences: dict[str, dict[str, float]] = {}
    for engine in spec.engines:
        for mode in spec.inheritance_modes:
            for carryover in spec.carryover_values:
                label = f"{engine}.{mode}.lambda-{carryover:g}"
                isomorphic_differences[label] = {
                    name: abs(
                        _secondary_rate(
                            analysis,
                            engine,
                            mode,
                            "natural",
                            carryover,
                            name,
                        )
                        - _secondary_rate(
                            analysis,
                            engine,
                            mode,
                            "joint_isomorphic",
                            carryover,
                            name,
                        )
                    )
                    for name in ("strict_rate", "active_capture_rate")
                }
    isomorphic_ready = all(
        difference <= ISOMORPHIC_RATE_MARGIN
        for values in isomorphic_differences.values()
        for difference in values.values()
    )
    shrinkage_ready = (
        tuple(float(value) for value in analysis["shrinkage"]["kappa_grid"])
        == KAPPA_GRID
        and analysis["shrinkage"]["evaluation_half_used_for_selection"] is False
        and source_counts
        == {engine: EXPECTED_RULEBOOKS_PER_ENGINE for engine in spec.engines}
    )
    recomputation_matches = bool(recompute_analysis(directory)["matches"])

    criteria = {
        "sealed_verification": bool(verification["verified"]),
        "exact_record_count": len(records) == EXPECTED_FUTURES,
        "complete_balanced_cells": complete_cells,
        "unique_future_ids": len({record["future_id"] for record in records})
        == len(records),
        "zero_carryover_pathwise_equivalence": zero_pairs_equal
        and zero_pairs == EXPECTED_FUTURES // 4,
        "independent_analysis_recomputation": recomputation_matches,
        "finite_primary_scores": _finite_primary(analysis),
        "nested_shrinkage_ready": shrinkage_ready,
        "minimum_split_half_reliability": reliability_ready,
        "minimum_primary_capture": capture_ready,
        "forced_convergence_detector": forced_ready,
        "joint_isomorphic_margin": isomorphic_ready,
    }
    return {
        "format": "gre-stage-a-readiness-audit-v1",
        "cohort_id": spec.cohort_id,
        "ready_for_stage_b_design": all(criteria.values()),
        "outcome_signs_used_for_readiness": False,
        "criteria": criteria,
        "thresholds": {
            "minimum_capture_rate": MINIMUM_CAPTURE_RATE,
            "minimum_reliability": MINIMUM_RELIABILITY,
            "minimum_forced_convergence_rate": MINIMUM_FORCED_CONVERGENCE_RATE,
            "isomorphic_rate_margin": ISOMORPHIC_RATE_MARGIN,
        },
        "observed": {
            "zero_carryover_pairs": zero_pairs,
            "capture_rates": capture_rates,
            "forced_convergence_rates": forced_rates,
            "split_half_reliability": reliability,
            "isomorphic_rate_differences": isomorphic_differences,
        },
    }
