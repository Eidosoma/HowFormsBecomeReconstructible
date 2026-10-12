"""Frozen engineering selectors for branching and the Stage B candidate."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .artifacts import (
    atomic_destination,
    read_json,
    read_jsonl_gz,
    write_checksums,
    write_json,
)
from .mechanism_config import MechanismCondition, MechanismSpec
from .mechanism_study import verify_mechanism_run


EQUIVALENCE_FIELDS = (
    "frozen_destination",
    "point_state_destination",
    "signature_destination",
    "competing_outcome",
    "active_capture",
    "stable_point_capture",
    "stable_signature_capture",
    "strict_library",
    "strict_state",
    "trace_digest",
)

MINIMUM_ASSIGNMENT_RATE = 0.80
MINIMUM_RELIABILITY = 0.80
MINIMUM_FORCED_CONVERGENCE_RATE = 0.80
ISOMORPHIC_RATE_MARGIN = 0.03


def audit_compiled_bridge(run: Path) -> dict[str, Any]:
    """Require pathwise equality for every registered compiled Wagner block."""

    verification = verify_mechanism_run(run)
    registration = read_json(run / "registration.json")
    spec = MechanismSpec.from_dict(registration["protocol"])
    condition_pairs: dict[str, str] = {}
    for compiled_condition in spec.conditions:
        if compiled_condition.variant != "wagner_compiled":
            continue
        native_variant = f"wagner_{compiled_condition.compiled_update_mode}"
        candidates = [
            condition
            for condition in spec.conditions
            if condition.source_set == compiled_condition.source_set
            and condition.variant == native_variant
            and condition.arms == compiled_condition.arms
            and condition.carryover_values == compiled_condition.carryover_values
            and condition.inheritance_modes == compiled_condition.inheritance_modes
            and condition.futures_per_cell == compiled_condition.futures_per_cell
            and 0.0 in condition.gamma_variances
        ]
        if len(candidates) == 1:
            condition_pairs[compiled_condition.name] = candidates[0].name
    if not condition_pairs:
        raise ValueError("mechanism run contains no complete compiled bridge block")

    native: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    compiled: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    native_to_compiled = {
        native_name: compiled_name
        for compiled_name, native_name in condition_pairs.items()
    }
    for record in read_jsonl_gz(run / "futures.jsonl.gz"):
        condition = str(record["condition"])
        if condition not in condition_pairs and condition not in native_to_compiled:
            continue
        if float(record["gamma_variance"]) != 0.0:
            continue
        pair_name = (
            condition if condition in condition_pairs else native_to_compiled[condition]
        )
        key = (
            pair_name,
            record["source_id"],
            record["state_id"],
            record["arm"],
            float(record["carryover"]),
            record["inheritance_mode"],
            record["future_index"],
        )
        values = tuple(record[name] for name in EQUIVALENCE_FIELDS)
        destination = native if condition in native_to_compiled else compiled
        if key in destination:
            raise ValueError(f"duplicate compiled-bridge coordinate: {key}")
        destination[key] = values
    if not compiled:
        raise ValueError("mechanism run contains no compiled bridge futures")
    common = set(native) & set(compiled)
    matches = sum(native[key] == compiled[key] for key in common)
    complete = len(common) == len(native) == len(compiled)
    pair_audits: dict[str, Any] = {}
    for compiled_name, native_name in sorted(condition_pairs.items()):
        native_keys = {key for key in native if key[0] == compiled_name}
        compiled_keys = {key for key in compiled if key[0] == compiled_name}
        pair_common = native_keys & compiled_keys
        pair_matches = sum(native[key] == compiled[key] for key in pair_common)
        pair_audits[compiled_name] = {
            "native_condition": native_name,
            "compiled_condition": compiled_name,
            "native_futures": len(native_keys),
            "compiled_futures": len(compiled_keys),
            "paired_futures": len(pair_common),
            "pathwise_matches": pair_matches,
            "pathwise_equal": (
                len(pair_common) == len(native_keys) == len(compiled_keys)
                and pair_matches == len(compiled_keys)
            ),
        }
    return {
        "verified_run": verification["verified"],
        "native_futures": len(native),
        "compiled_futures": len(compiled),
        "paired_futures": len(common),
        "pathwise_matches": matches,
        "pathwise_equal": complete and matches == len(compiled),
        "bridge_blocks": pair_audits,
    }


def phase_2_decision(phase_1: Path) -> dict[str, Any]:
    """Apply the conservative, sign-independent architecture-stage branch."""

    bridge = audit_compiled_bridge(phase_1)
    if not bridge["pathwise_equal"]:
        raise ValueError("compiled Wagner bridge failed; mechanism campaign must stop")
    analysis = read_json(phase_1 / "analysis.json")

    def rates_matching(*parts: str) -> list[float]:
        return [
            float(value["mean"])
            for name, value in analysis["rates"].items()
            if all(part in name for part in parts)
        ]

    wagner_zero_capture = rates_matching(
        "wagner-main.wagner_sequential",
        ".acute_mismatch.",
        ".lambda-1.",
        ".theta-0.",
        ".active_capture",
    )
    wagner_noisy_state = rates_matching(
        "wagner-main.wagner_sequential",
        ".acute_mismatch.",
        ".lambda-1.",
        ".theta-0.1.",
        ".stable_point_capture",
    )
    reliability = [
        float(value)
        for name, value in analysis["split_half_reliability"].items()
        if "exact_point_state.wagner-main.wagner_sequential" in name
        and ".acute_mismatch." in name
        and ".lambda-1." in name
        and ".theta-0.1." in name
    ]
    sufficiency = {
        "compiled_bridge_pathwise_equal": bridge["pathwise_equal"],
        "zero_noise_capture_at_least_0_80": bool(wagner_zero_capture)
        and min(wagner_zero_capture) >= 0.80,
        "noisy_state_assignment_at_least_0_80": bool(wagner_noisy_state)
        and min(wagner_noisy_state) >= 0.80,
        "noisy_state_reliability_at_least_0_80": bool(reliability)
        and min(reliability) >= 0.80,
        # Phase 1 preserves the original N=6 Boolean/N=10 Wagner pairing, so it
        # cannot establish an architecture-controlled equivalence result.
        "matched_architecture_equivalence_established": False,
    }
    # The architecture criterion is deliberately unachievable in Phase 1. This
    # makes the causal N-by-update factorial mandatory without consulting signs.
    required = not all(sufficiency.values())
    return {
        "format": "gre-mechanism-phase-2-decision-v1",
        "phase_2_required": required,
        "outcome_signs_used": False,
        "criteria": sufficiency,
        "bridge": bridge,
        "note": (
            "Phase 2 is required because Phase 1 cannot establish matched-N, "
            "matched-update architecture equivalence. Effect direction is never "
            "used to make this decision."
        ),
    }


def _rate_mean(
    analysis: dict[str, Any],
    condition: MechanismCondition,
    genes: int,
    arm: str,
    carryover: float,
    variance: float,
    mode: str,
    field: str,
) -> float | None:
    key = (
        f"{condition.name}.{condition.variant}.N-{genes}.{arm}."
        f"lambda-{carryover:g}.theta-{variance:g}.{mode}.{field}"
    )
    value = analysis["rates"].get(key)
    return None if value is None else float(value["mean"])


def _reliability_mean(
    analysis: dict[str, Any],
    endpoint: str,
    condition: MechanismCondition,
    genes: int,
    arm: str,
    carryover: float,
    variance: float,
    mode: str,
) -> float | None:
    key = (
        f"{endpoint}.{condition.name}.{condition.variant}.N-{genes}.{arm}."
        f"lambda-{carryover:g}.theta-{variance:g}.{mode}"
    )
    value = analysis["split_half_reliability"].get(key)
    return None if value is None else float(value)


def _committor_finite(
    analysis: dict[str, Any],
    endpoint: str,
    condition: MechanismCondition,
    genes: int,
    variance: float,
    mode: str,
) -> bool:
    key = (
        f"{endpoint}.{condition.name}.{condition.variant}.N-{genes}."
        f"acute_mismatch.lambda-1.theta-{variance:g}.{mode}"
    )
    value = analysis["committor"].get(key)
    if not isinstance(value, dict) or "mean_log_loss_gain" not in value:
        return False
    numbers = [
        float(value["mean_log_loss_gain"]),
        float(value["mean_brier_gain"]),
        float(value["committor_log_loss"]),
        float(value["baseline_log_loss"]),
        *(float(item) for item in value["interval"]),
    ]
    return all(math.isfinite(item) for item in numbers)


def _phase_3_condition_pairs(
    spec: MechanismSpec,
) -> list[tuple[MechanismCondition, MechanismCondition, int]]:
    """Find native main/control pairs without admitting a selected extra variant."""

    output: list[tuple[MechanismCondition, MechanismCondition, int]] = []
    for main in spec.conditions:
        if not {"natural", "acute_mismatch", "target_aligned_own_anchor"}.issubset(
            main.arms
        ):
            continue
        controls = [
            value
            for value in spec.conditions
            if value.source_set == main.source_set
            and value.variant == main.variant
            and value.compiled_update_mode == main.compiled_update_mode
            and {"joint_isomorphic", "single_attractor"}.issubset(value.arms)
        ]
        if len(controls) == 1:
            output.append((main, controls[0], spec.source(main.source_set).genes))
    return output


def _endpoint_engineering_audit(
    analysis: dict[str, Any],
    pairs: list[tuple[MechanismCondition, MechanismCondition, int]],
    endpoint: str,
    coverage_field: str | None,
) -> dict[str, Any]:
    strict_field = "strict_library" if endpoint == "frozen_library" else "strict_state"
    assignment: list[float] = []
    reliability: list[float] = []
    finite: list[bool] = []
    isomorphic: dict[str, float] = {}
    forced: dict[str, float] = {}
    expected_primary = 0
    expected_isomorphic = 0
    expected_forced = 0
    for main, controls, genes in pairs:
        for variance in main.gamma_variances:
            for mode in main.inheritance_modes:
                expected_primary += 1
                if coverage_field is not None:
                    value = _rate_mean(
                        analysis,
                        main,
                        genes,
                        "acute_mismatch",
                        1.0,
                        variance,
                        mode,
                        coverage_field,
                    )
                    if value is not None:
                        assignment.append(value)
                value = _reliability_mean(
                    analysis,
                    endpoint,
                    main,
                    genes,
                    "acute_mismatch",
                    1.0,
                    variance,
                    mode,
                )
                if value is not None:
                    reliability.append(value)
                finite.append(
                    _committor_finite(
                        analysis, endpoint, main, genes, variance, mode
                    )
                )

        common_carryover = sorted(
            set(main.carryover_values) & set(controls.carryover_values)
        )
        common_variance = sorted(
            set(main.gamma_variances) & set(controls.gamma_variances)
        )
        common_modes = sorted(
            set(main.inheritance_modes) & set(controls.inheritance_modes)
        )
        audit_fields = [strict_field]
        if coverage_field is not None:
            audit_fields.append(coverage_field)
        for carryover in common_carryover:
            for variance in common_variance:
                for mode in common_modes:
                    expected_isomorphic += len(audit_fields)
                    expected_forced += 1
                    for field in audit_fields:
                        natural = _rate_mean(
                            analysis,
                            main,
                            genes,
                            "natural",
                            carryover,
                            variance,
                            mode,
                            field,
                        )
                        joint = _rate_mean(
                            analysis,
                            controls,
                            genes,
                            "joint_isomorphic",
                            carryover,
                            variance,
                            mode,
                            field,
                        )
                        if natural is not None and joint is not None:
                            label = (
                                f"{main.source_set}.lambda-{carryover:g}."
                                f"theta-{variance:g}.{mode}.{field}"
                            )
                            isomorphic[label] = abs(natural - joint)
                    forced_value = _rate_mean(
                        analysis,
                        controls,
                        genes,
                        "single_attractor",
                        carryover,
                        variance,
                        mode,
                        strict_field,
                    )
                    if forced_value is not None:
                        forced[
                            f"{main.source_set}.lambda-{carryover:g}."
                            f"theta-{variance:g}.{mode}.{strict_field}"
                        ] = forced_value

    # Competing-outcome assignment is exhaustive by construction. It still has
    # to pass reliability, finiteness, control, and forced-convergence checks.
    if coverage_field is None and pairs:
        assignment = [1.0]
    assignment_complete = coverage_field is None or len(assignment) == expected_primary
    criteria = {
        "assignment_at_least_0_80": expected_primary > 0
        and assignment_complete
        and bool(assignment)
        and min(assignment) >= MINIMUM_ASSIGNMENT_RATE,
        "split_half_reliability_at_least_0_80": expected_primary > 0
        and len(reliability) == expected_primary
        and bool(reliability)
        and min(reliability) >= MINIMUM_RELIABILITY,
        "finite_committor_scores": expected_primary > 0
        and len(finite) == expected_primary
        and all(finite),
        "joint_isomorphic_margin_at_most_0_03": expected_isomorphic > 0
        and len(isomorphic) == expected_isomorphic
        and max(isomorphic.values()) <= ISOMORPHIC_RATE_MARGIN,
        "forced_convergence_at_least_0_80": expected_forced > 0
        and len(forced) == expected_forced
        and min(forced.values()) >= MINIMUM_FORCED_CONVERGENCE_RATE,
    }
    return {
        "criteria": criteria,
        "minimum_assignment": min(assignment) if assignment else None,
        "minimum_reliability": min(reliability) if reliability else None,
        "maximum_isomorphic_difference": (
            max(isomorphic.values()) if isomorphic else None
        ),
        "minimum_forced_convergence": min(forced.values()) if forced else None,
        "expected_primary_cells": expected_primary,
        "observed_assignment_cells": (
            expected_primary if coverage_field is None and pairs else len(assignment)
        ),
        "observed_reliability_cells": len(reliability),
        "expected_isomorphic_checks": expected_isomorphic,
        "observed_isomorphic_checks": len(isomorphic),
        "expected_forced_convergence_checks": expected_forced,
        "observed_forced_convergence_checks": len(forced),
        "isomorphic_differences": isomorphic,
        "forced_convergence_rates": forced,
    }


def _zero_carryover_audit(run: Path) -> dict[str, Any]:
    self_values: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    pairs = 0
    matches = 0
    for record in read_jsonl_gz(run / "futures.jsonl.gz"):
        if float(record["carryover"]) != 0.0:
            continue
        if record["inheritance_mode"] not in {"self", "donor_shuffled"}:
            continue
        key = (
            record["condition"],
            record["source_id"],
            record["state_id"],
            record["arm"],
            record["gamma_variance"],
            record["future_index"],
        )
        values = tuple(record[name] for name in EQUIVALENCE_FIELDS)
        if record["inheritance_mode"] == "self":
            self_values[key] = values
        else:
            pairs += 1
            matches += int(self_values.get(key) == values)
    # Canonical record ordering may place donor before self. Repeat only when necessary.
    if matches != pairs:
        donor_values: dict[tuple[Any, ...], tuple[Any, ...]] = {}
        for record in read_jsonl_gz(run / "futures.jsonl.gz"):
            if float(record["carryover"]) != 0.0:
                continue
            key = (
                record["condition"],
                record["source_id"],
                record["state_id"],
                record["arm"],
                record["gamma_variance"],
                record["future_index"],
            )
            values = tuple(record[name] for name in EQUIVALENCE_FIELDS)
            if record["inheritance_mode"] == "donor_shuffled":
                donor_values[key] = values
            elif record["inheritance_mode"] == "self":
                self_values[key] = values
        common = set(self_values) & set(donor_values)
        pairs = len(common)
        matches = sum(self_values[key] == donor_values[key] for key in common)
    return {"pairs": pairs, "matches": matches, "equal": pairs > 0 and pairs == matches}


def select_stage_b_candidate(phase_3: Path) -> dict[str, Any]:
    """Choose an endpoint by engineering criteria only, or return blocked."""

    verification = verify_mechanism_run(phase_3)
    analysis = read_json(phase_3 / "analysis.json")
    registration = read_json(phase_3 / "registration.json")
    spec = MechanismSpec.from_dict(registration["protocol"])
    pairs = _phase_3_condition_pairs(spec)
    zero = _zero_carryover_audit(phase_3)
    endpoint_order = (
        ("frozen_library", "active_capture"),
        ("exact_point_state", "stable_point_capture"),
        ("realized_signature", "stable_signature_capture"),
        ("competing_outcome", None),
    )
    audits: dict[str, Any] = {}
    selected: str | None = None
    for endpoint, coverage_field in endpoint_order:
        audit = _endpoint_engineering_audit(
            analysis, pairs, endpoint, coverage_field
        )
        criteria = dict(audit["criteria"])
        criteria["zero_carryover_pathwise_equivalence"] = zero["equal"]
        audit["criteria"] = criteria
        audits[endpoint] = audit
        if selected is None and all(criteria.values()):
            selected = endpoint
    return {
        "format": "gre-stage-b-candidate-selection-v1",
        "source_run": str(phase_3.resolve()),
        "source_protocol_digest": verification["protocol_digest"],
        "ready": selected is not None,
        "selected_endpoint": selected,
        "endpoint_order": [value[0] for value in endpoint_order],
        "outcome_signs_used_for_selection": False,
        "native_main_control_pairs": [
            {
                "main": main.name,
                "controls": controls.name,
                "source_set": main.source_set,
                "variant": main.variant,
                "genes": genes,
            }
            for main, controls, genes in pairs
        ],
        "thresholds": {
            "minimum_assignment_rate": MINIMUM_ASSIGNMENT_RATE,
            "minimum_reliability": MINIMUM_RELIABILITY,
            "minimum_forced_convergence_rate": (
                MINIMUM_FORCED_CONVERGENCE_RATE
            ),
            "isomorphic_rate_margin": ISOMORPHIC_RATE_MARGIN,
        },
        "audits": audits,
        "zero_carryover": zero,
        "scientific_primary": {
            "estimand": (
                "cross-fitted destination self-minus-donor gain in acute mismatch "
                "minus the same gain in each control"
            ),
            "controls": ["natural", "target_aligned_own_anchor"],
            "engines": ["boolean", "wagner"],
            "success_rule": (
                "all four engine-by-control contrasts have simultaneous 95% "
                "rulebook-bootstrap lower bounds above zero"
            ),
            "strict_switching": "secondary",
        },
        "seed": None,
        "launchable": False,
        "blocked_reason": None if selected else "no endpoint passed engineering criteria",
    }


def write_stage_b_candidate(phase_3: Path, destination: Path) -> Path:
    candidate = select_stage_b_candidate(phase_3)
    with atomic_destination(destination) as temporary:
        write_json(temporary / "stage-b-candidate.json", candidate)
        lines = [
            "# Stage B candidate protocol",
            "",
            "> Generated by engineering criteria only. This template has no seed and cannot be launched.",
            "",
            f"- Ready: {'yes' if candidate['ready'] else 'no'}",
            f"- Selected endpoint: `{candidate['selected_endpoint']}`",
            "- Scientific primary: mismatch-specific destination-history interaction against both natural and own-anchor controls.",
            "- Strict switching: secondary.",
            "",
        ]
        if candidate["blocked_reason"]:
            lines.append(f"Blocked: {candidate['blocked_reason']}")
            lines.append("")
        (temporary / "STAGE_B_CANDIDATE.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )
        write_checksums(temporary)
    return destination.resolve()
