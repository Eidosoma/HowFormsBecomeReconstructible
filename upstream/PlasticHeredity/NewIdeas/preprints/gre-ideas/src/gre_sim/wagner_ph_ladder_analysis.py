"""Barrier-specific analyses for Wagner PH Origin Ladder v1."""

from __future__ import annotations

import collections
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .artifacts import canonical_digest, read_json
from .rng import rng_for
from .wagner_ph_ladder_config import LADDER_ANALYSIS_FORMAT, WagnerPHLadderSpec


def _interval(
    values: Iterable[float], spec: WagnerPHLadderSpec, label: str
) -> dict[str, Any]:
    array = np.asarray(tuple(float(value) for value in values), dtype=float)
    if not array.size:
        return {
            "mean": None,
            "interval": [None, None],
            "lower": None,
            "upper": None,
            "tasks": 0,
            "positive_tasks": 0,
        }
    random = rng_for(spec.master_seed, "origin-ladder-bootstrap", label)
    indices = random.integers(
        0, array.size, size=(spec.bootstrap_repetitions, array.size)
    )
    means = np.mean(array[indices], axis=1)
    tail = (1.0 - spec.interval_level) / 2.0
    return {
        "mean": float(np.mean(array)),
        "interval": [
            float(np.quantile(means, tail)),
            float(np.quantile(means, 1.0 - tail)),
        ],
        "lower": float(np.quantile(means, tail)),
        "upper": float(np.quantile(means, 1.0 - tail)),
        "tasks": int(array.size),
        "positive_tasks": int(np.sum(array > 0.0)),
    }


def _cell(result: dict[str, Any], stage: str, cell_id: str) -> dict[str, Any]:
    return next(value for value in result[stage] if value["cell_id"] == cell_id)


def _lineage_rate(
    result: dict[str, Any],
    stage: str,
    cell_id: str,
    condition: str,
    generation: int,
    field: str = "correct_rate",
) -> float:
    return float(
        _cell(result, stage, cell_id)["conditions"][condition][str(generation)][
            field
        ]
    )


def _ecology_rate(
    result: dict[str, Any],
    cell_id: str,
    condition: str,
    relation: str = "overall",
    field: str = "correct_rate",
) -> float | None:
    value = _cell(result, "ecology", cell_id)["conditions"][condition][relation][
        field
    ]
    return None if value is None else float(value)


def _paired(
    results: list[dict[str, Any]],
    getter_left: Any,
    getter_right: Any,
) -> list[float]:
    values: list[float] = []
    for result in results:
        left = getter_left(result)
        right = getter_right(result)
        if left is not None and right is not None:
            values.append(float(left) - float(right))
    return values


def analyze_origin_autopsy(parent: Path) -> dict[str, Any]:
    """Pair original training outcomes with their already-sealed heldout outcomes."""

    parent = parent.resolve()
    evolution = parent / "evolution" / "populations"
    audit = parent / "heldout-causal-pedigree-audit" / "populations"
    rows: list[dict[str, Any]] = []
    for path in sorted(evolution.glob("*.json")):
        selected = read_json(path)
        heldout_path = audit / path.name
        if not heldout_path.is_file():
            raise FileNotFoundError(f"missing paired origin audit: {heldout_path}")
        heldout = read_json(heldout_path)
        if selected["population_id"] != heldout["population_id"]:
            raise ValueError("origin population pairing mismatch")
        carrier = selected["selected"]["carrier"]
        training = selected["selected_training_score"]
        row = {
            "population_id": selected["population_id"],
            "treatment": selected["treatment"],
            "scaffold": selected["scaffold"],
            "capacity": int(carrier["k"]),
            "write_rate": float(carrier["write_rate"]),
            "coupling": float(carrier["coupling"]),
            "writer_reader_active": bool(
                heldout["selected_writer_active"] and heldout["selected_reader_active"]
            ),
            "training_gain": float(training["selected_gain"]),
            "training_renewal": float(training["renewal_contrast"]),
            "training_fitness": float(training["fitness"]),
            "heldout_gain_g8": float(heldout["selected_g8"]),
            "heldout_renewal_g8": float(heldout["renewal_contrast_g8"]),
        }
        row["gain_optimism"] = row["training_gain"] - row["heldout_gain_g8"]
        row["renewal_optimism"] = (
            row["training_renewal"] - row["heldout_renewal_g8"]
        )
        rows.append(row)
    by_treatment: dict[str, Any] = {}
    for treatment in sorted({str(value["treatment"]) for value in rows}):
        selected = [value for value in rows if value["treatment"] == treatment]
        training = np.asarray([value["training_gain"] for value in selected])
        heldout = np.asarray([value["heldout_gain_g8"] for value in selected])
        correlation = None
        if len(selected) >= 3 and np.std(training) > 0 and np.std(heldout) > 0:
            correlation = float(np.corrcoef(training, heldout)[0, 1])
        by_treatment[treatment] = {
            "populations": len(selected),
            "writer_reader_active": sum(
                bool(value["writer_reader_active"]) for value in selected
            ),
            "capacity_counts": dict(
                sorted(collections.Counter(value["capacity"] for value in selected).items())
            ),
            "mean_training_gain": float(np.mean(training)),
            "mean_heldout_gain_g8": float(np.mean(heldout)),
            "mean_gain_optimism": float(
                np.mean([value["gain_optimism"] for value in selected])
            ),
            "mean_training_renewal": float(
                np.mean([value["training_renewal"] for value in selected])
            ),
            "mean_heldout_renewal_g8": float(
                np.mean([value["heldout_renewal_g8"] for value in selected])
            ),
            "training_heldout_gain_correlation": correlation,
        }
    explicit = [
        value for value in rows if str(value["treatment"]).endswith("explicit_renewal")
    ]
    return {
        "format": "gre-wagner-ph-origin-ladder-autopsy-v1",
        "parent": str(parent),
        "population_rows": len(rows),
        "by_treatment": by_treatment,
        "explicit_summary": {
            "populations": len(explicit),
            "mean_training_gain": float(
                np.mean([value["training_gain"] for value in explicit])
            ),
            "mean_heldout_gain_g8": float(
                np.mean([value["heldout_gain_g8"] for value in explicit])
            ),
            "mean_training_renewal": float(
                np.mean([value["training_renewal"] for value in explicit])
            ),
            "mean_heldout_renewal_g8": float(
                np.mean([value["heldout_renewal_g8"] for value in explicit])
            ),
            "selected_capacity_median": float(
                np.median([value["capacity"] for value in explicit])
            ),
        },
        "diagnosis": {
            "training_generalization_gap_present": bool(
                np.mean([value["training_gain"] for value in explicit])
                > np.mean([value["heldout_gain_g8"] for value in explicit]) + 0.05
            ),
            "capacity_collapsed_to_k1": bool(
                np.median([value["capacity"] for value in explicit]) <= 1.0
            ),
            "autopsy_cannot_separate_capacity_from_coordination": True,
        },
        "population_details": rows,
        "rows_digest": canonical_digest(rows),
    }


def _capacity_analysis(
    results: list[dict[str, Any]], spec: WagnerPHLadderSpec
) -> dict[str, Any]:
    generation = max(spec.checkpoints)
    cells: dict[str, Any] = {}
    for metadata in results[0]["capacity"]:
        cell_id = str(metadata["cell_id"])
        effect_definitions = {
            "intact_minus_zero": ("intact", "zero", generation, "correct_rate"),
            "renewal_dependence": (
                "intact",
                "renewal_off",
                generation,
                "correct_rate",
            ),
            "reader_dependence": (
                "intact",
                "reader_off",
                generation,
                "correct_rate",
            ),
            "founder_write_dependence_g0": (
                "intact",
                "founder_write_off",
                0,
                "correct_rate",
            ),
        }
        effects: dict[str, Any] = {}
        for label, (left, right, checkpoint, field) in effect_definitions.items():
            effects[label] = _interval(
                _paired(
                    results,
                    lambda result, left=left, checkpoint=checkpoint, field=field: _lineage_rate(
                        result, "capacity", cell_id, left, checkpoint, field
                    ),
                    lambda result, right=right, checkpoint=checkpoint, field=field: _lineage_rate(
                        result, "capacity", cell_id, right, checkpoint, field
                    ),
                ),
                spec,
                f"capacity.{cell_id}.{label}",
            )
        effects["opposite_donor_following_g0"] = _interval(
            _paired(
                results,
                lambda result: _lineage_rate(
                    result,
                    "capacity",
                    cell_id,
                    "opposite_history_transplant",
                    0,
                    "wrong_rate",
                ),
                lambda result: _lineage_rate(
                    result,
                    "capacity",
                    cell_id,
                    "opposite_history_transplant",
                    0,
                    "correct_rate",
                ),
            ),
            spec,
            f"capacity.{cell_id}.opposite-donor-following",
        )
        gain = effects["intact_minus_zero"]
        renewal = effects["renewal_dependence"]
        reader = effects["reader_dependence"]
        donor = effects["opposite_donor_following_g0"]
        mechanism_feasible = bool(
            gain["mean"] >= spec.gain_gate
            and gain["lower"] > spec.gain_lower_gate
            and reader["mean"] >= spec.causal_gate
            and reader["lower"] > spec.causal_lower_gate
            and donor["mean"] >= spec.causal_gate
            and donor["lower"] > spec.causal_lower_gate
        )
        renewing_ph_pass = bool(
            mechanism_feasible
            and renewal["mean"] >= spec.causal_gate
            and renewal["lower"] > spec.causal_lower_gate
        )
        cells[cell_id] = {
            "k": int(metadata["k"]),
            "bits_per_mark": int(metadata["bits_per_mark"]),
            "alphabet_size": int(metadata["alphabet_size"]),
            "payload_upper_bits": int(metadata["payload_upper_bits"]),
            "effects": effects,
            "mechanism_feasible": mechanism_feasible,
            "renewing_ph_pass": renewing_ph_pass,
        }
    feasible = [
        (name, value) for name, value in cells.items() if value["mechanism_feasible"]
    ]
    renewing = [
        (name, value) for name, value in cells.items() if value["renewing_ph_pass"]
    ]
    order = lambda item: (
        item[1]["payload_upper_bits"],
        item[1]["k"],
        item[1]["bits_per_mark"],
    )
    smallest_feasible = min(feasible, key=order)[0] if feasible else None
    smallest_renewing = min(renewing, key=order)[0] if renewing else None
    diagnostic = max(
        cells,
        key=lambda name: (
            float(cells[name]["effects"]["intact_minus_zero"]["mean"])
            + float(cells[name]["effects"]["renewal_dependence"]["mean"])
            + float(cells[name]["effects"]["reader_dependence"]["mean"])
        ),
    )
    k1_pass = any(
        value["renewing_ph_pass"] for value in cells.values() if value["k"] == 1
    )
    larger_pass = any(
        value["renewing_ph_pass"] for value in cells.values() if value["k"] > 1
    )
    return {
        "checkpoint_generation": generation,
        "cells": cells,
        "smallest_feasible_cell": smallest_feasible,
        "smallest_renewing_cell": smallest_renewing,
        "diagnostic_best_cell": diagnostic,
        "capacity_barrier_supported": bool(not k1_pass and larger_pass),
        "no_tested_capacity_sufficient": not bool(renewing),
        "gate_definitions": {
            "mechanism_feasible": "intact-minus-zero and reader/donor causality pass",
            "renewing_ph": "mechanism feasible plus intact-minus-renewal-off passes",
            "gain_mean": spec.gain_gate,
            "gain_interval_lower": spec.gain_lower_gate,
            "causal_mean": spec.causal_gate,
            "causal_interval_lower_strictly_above": spec.causal_lower_gate,
        },
    }


def _reachable_path(
    scores: dict[tuple[int, int], float],
    maximum_writer: int,
    maximum_reader: int,
    tolerance: float,
) -> list[tuple[int, int]] | None:
    start = (0, 0)
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    queue = collections.deque([start])
    while queue:
        current = queue.popleft()
        if current == (maximum_writer, maximum_reader):
            path: list[tuple[int, int]] = []
            node: tuple[int, int] | None = current
            while node is not None:
                path.append(node)
                node = parent[node]
            return list(reversed(path))
        for following in ((current[0] + 1, current[1]), (current[0], current[1] + 1)):
            if following not in scores or following in parent:
                continue
            if scores[following] + tolerance + 1e-12 < scores[current]:
                continue
            parent[following] = current
            queue.append(following)
    return None


def _coordination_analysis(
    results: list[dict[str, Any]],
    spec: WagnerPHLadderSpec,
    capacity_analysis: dict[str, Any],
) -> dict[str, Any]:
    generation = max(spec.checkpoints)
    cells: dict[str, Any] = {}
    for metadata in results[0]["coordination"]:
        cell_id = str(metadata["cell_id"])
        k = int(metadata["k"])
        origin_id = f"k{k}.w0.r0"
        gain = _interval(
            _paired(
                results,
                lambda result: _lineage_rate(
                    result, "coordination", cell_id, "intact", generation
                ),
                lambda result: _lineage_rate(
                    result, "coordination", origin_id, "intact", generation
                ),
            ),
            spec,
            f"coordination.{cell_id}.gain",
        )
        renewal = _interval(
            _paired(
                results,
                lambda result: _lineage_rate(
                    result, "coordination", cell_id, "intact", generation
                ),
                lambda result: _lineage_rate(
                    result, "coordination", cell_id, "renewal_off", generation
                ),
            ),
            spec,
            f"coordination.{cell_id}.renewal",
        )
        cost = float(
            0.05 * k / spec.genes
            + 0.025 * float(metadata["coupling"])
            + 0.025 * float(metadata["write_rate"])
        )
        score = float(gain["mean"] + 0.5 * renewal["mean"] - cost)
        capacity_causal = bool(
            capacity_analysis["cells"][f"k{k}.b{spec.coordination_bits}"][
                "mechanism_feasible"
            ]
        )
        viable = bool(
            capacity_causal
            and
            gain["mean"] >= spec.gain_gate
            and gain["lower"] > spec.gain_lower_gate
            and renewal["mean"] >= spec.causal_gate
        )
        cells[cell_id] = {
            "k": k,
            "writer_index": int(metadata["writer_index"]),
            "reader_index": int(metadata["reader_index"]),
            "write_rate": float(metadata["write_rate"]),
            "coupling": float(metadata["coupling"]),
            "gain": gain,
            "renewal_dependence": renewal,
            "registered_resource_cost": cost,
            "diagnostic_score": score,
            "capacity_causality_validated": capacity_causal,
            "viable_endpoint": viable,
        }
    capacities: dict[str, Any] = {}
    maximum_writer = len(spec.writer_rates) - 1
    maximum_reader = len(spec.reader_couplings) - 1
    for k in spec.coordination_capacities:
        subset = {
            (int(value["writer_index"]), int(value["reader_index"])): float(
                value["diagnostic_score"]
            )
            for value in cells.values()
            if value["k"] == k
        }
        strict = _reachable_path(subset, maximum_writer, maximum_reader, 0.0)
        drift = _reachable_path(
            subset,
            maximum_writer,
            maximum_reader,
            spec.path_drift_tolerance,
        )
        strong = cells[f"k{k}.w{maximum_writer}.r{maximum_reader}"]
        weak = cells[f"k{k}.w1.r1"]
        writer_only = cells[f"k{k}.w{maximum_writer}.r0"]
        reader_only = cells[f"k{k}.w0.r{maximum_reader}"]
        capacities[str(k)] = {
            "off_off_score": cells[f"k{k}.w0.r0"]["diagnostic_score"],
            "writer_only_score": writer_only["diagnostic_score"],
            "reader_only_score": reader_only["diagnostic_score"],
            "weak_both_score": weak["diagnostic_score"],
            "strong_both_score": strong["diagnostic_score"],
            "strong_endpoint_viable": strong["viable_endpoint"],
            "weak_endpoint_viable": weak["viable_endpoint"],
            "strict_non_decreasing_path": strict,
            "drift_tolerant_path": drift,
            "coordination_valley_supported": bool(
                strong["viable_endpoint"] and strict is None
            ),
            "shallow_valley_crossable_with_registered_drift": bool(
                strong["viable_endpoint"] and strict is None and drift is not None
            ),
            "strength_threshold_supported": bool(
                strong["viable_endpoint"] and not weak["viable_endpoint"]
            ),
        }
    any_strong = any(value["strong_endpoint_viable"] for value in capacities.values())
    return {
        "checkpoint_generation": generation,
        "cells": cells,
        "by_capacity": capacities,
        "any_strong_endpoint_viable": any_strong,
        "coordination_valley_supported_any_capacity": any(
            value["coordination_valley_supported"] for value in capacities.values()
        ),
        "mechanism_grn_mismatch_supported": not any_strong,
        "path_rule": "increase writer or reader one registered step at a time; score may not fall",
        "drift_tolerance": spec.path_drift_tolerance,
        "score_rule": "g8 gain + 0.5*renewal dependence - registered carrier resource cost",
    }


def _ecology_analysis(
    results: list[dict[str, Any]], spec: WagnerPHLadderSpec
) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for metadata in results[0]["ecology"]:
        cell_id = str(metadata["cell_id"])
        effects: dict[str, Any] = {}
        for label, left, right, relation in (
            ("intact_minus_zero", "intact", "zero", "overall"),
            ("reader_dependence", "intact", "reader_off", "overall"),
            ("renewal_dependence", "intact", "renewal_off", "overall"),
            ("stay_advantage", "intact", "zero", "stay"),
            ("switch_advantage", "intact", "zero", "switch"),
        ):
            effects[label] = _interval(
                _paired(
                    results,
                    lambda result, left=left, relation=relation: _ecology_rate(
                        result, cell_id, left, relation
                    ),
                    lambda result, right=right, relation=relation: _ecology_rate(
                        result, cell_id, right, relation
                    ),
                ),
                spec,
                f"ecology.{cell_id}.{label}",
            )
        gain = effects["intact_minus_zero"]
        reader = effects["reader_dependence"]
        renewal = effects["renewal_dependence"]
        useful = bool(
            gain["mean"] is not None
            and gain["mean"] >= spec.ecology_gain_gate
            and gain["lower"] > 0.0
            and reader["mean"] is not None
            and reader["mean"] > 0.0
        )
        renewal_dependent = bool(
            renewal["mean"] is not None
            and renewal["mean"] > 0.0
            and renewal["lower"] > 0.0
        )
        cells[cell_id] = {
            "k": int(metadata["k"]),
            "persistence": float(metadata["persistence"]),
            "effects": effects,
            "ecologically_useful": useful,
            "renewal_dependent": renewal_dependent,
        }
    by_capacity: dict[str, Any] = {}
    for k in spec.ecology_capacities:
        subset = sorted(
            (value for value in cells.values() if value["k"] == k),
            key=lambda value: value["persistence"],
        )
        useful = [value["persistence"] for value in subset if value["ecologically_useful"]]
        low = subset[0]["effects"]["intact_minus_zero"]["mean"]
        high = subset[-1]["effects"]["intact_minus_zero"]["mean"]
        by_capacity[str(k)] = {
            "minimum_useful_persistence": min(useful) if useful else None,
            "useful_persistence_values": useful,
            "always_switch_gain": low,
            "always_stay_gain": high,
            "predictability_sign_reversal": bool(low is not None and high is not None and low < 0.0 < high),
        }
    return {
        "cells": cells,
        "by_capacity": by_capacity,
        "any_ecological_usefulness": any(
            value["ecologically_useful"] for value in cells.values()
        ),
        "predictability_condition_supported": any(
            value["predictability_sign_reversal"] for value in by_capacity.values()
        ),
        "reward_rule": "offspring correct development before its own inducing cue; no memory or carrier term",
        "interpretation_boundary": "This is an anticipatory parent-offspring environment model, not a claim that every natural niche has this timing.",
    }


def analyze_ladder_results(
    results: list[dict[str, Any]],
    spec: WagnerPHLadderSpec,
    autopsy: dict[str, Any],
) -> dict[str, Any]:
    spec.validate()
    if len(results) != spec.tasks:
        raise ValueError("Origin Ladder analysis requires every frozen task")
    capacity = _capacity_analysis(results, spec)
    coordination = _coordination_analysis(results, spec, capacity)
    ecology = _ecology_analysis(results, spec)
    candidates = [
        (name, value)
        for name, value in capacity["cells"].items()
        if value["renewing_ph_pass"]
        and value["bits_per_mark"] == spec.ecology_bits
        and ecology["by_capacity"][str(value["k"])][
            "predictability_sign_reversal"
        ]
        and ecology["by_capacity"][str(value["k"])]["minimum_useful_persistence"]
        is not None
    ]
    candidates.sort(
        key=lambda item: (
            item[1]["payload_upper_bits"],
            ecology["by_capacity"][str(item[1]["k"])][
                "minimum_useful_persistence"
            ],
        )
    )
    finalist = None
    if candidates:
        name, value = candidates[0]
        finalist = {
            "capacity_cell": name,
            "k": value["k"],
            "bits_per_mark": value["bits_per_mark"],
            "minimum_useful_persistence": ecology["by_capacity"][str(value["k"])][
                "minimum_useful_persistence"
            ],
            "selection_rule": "smallest four-bit renewing capacity that is ecologically useful; then lowest useful persistence",
            "confirmation_eligible": True,
        }
    diagnoses = {
        "training_overfit_supported": bool(
            autopsy["diagnosis"]["training_generalization_gap_present"]
        ),
        "capacity_barrier_supported": bool(capacity["capacity_barrier_supported"]),
        "coordination_valley_supported": bool(
            coordination["coordination_valley_supported_any_capacity"]
        ),
        "strength_threshold_supported": any(
            value["strength_threshold_supported"]
            for value in coordination["by_capacity"].values()
        ),
        "ecological_predictability_condition_supported": bool(
            ecology["predictability_condition_supported"]
        ),
        "tested_mechanism_incompatible_with_grns": bool(
            coordination["mechanism_grn_mismatch_supported"]
        ),
    }
    return {
        "format": LADDER_ANALYSIS_FORMAT,
        "protocol_digest": canonical_digest(spec.to_dict()),
        "tasks": len(results),
        "mean_founder_acquisition_rate": float(
            np.mean([value["acquisition_rate"] for value in results])
        ),
        "autopsy": autopsy,
        "capacity_frontier": capacity,
        "coordination_surface": coordination,
        "ecological_value_map": ecology,
        "barrier_diagnoses": diagnoses,
        "finalist": finalist,
        "confirmation_reserve": {
            "status": "untouched",
            "eligible": finalist is not None,
            "tasks": spec.confirmation_tasks,
            "futures_per_history": spec.confirmation_futures_per_history,
            "seed_digest": canonical_digest(spec.confirmation_seed),
            "rng_draws_consumed": 0,
            "authorization_required": True,
        },
        "claim_boundary": "Exploratory in-silico barrier diagnosis for a predefined target-blind carrier channel; it neither demonstrates de-novo molecular invention nor establishes natural occurrence.",
    }


def render_ladder_report(analysis: dict[str, Any]) -> str:
    diagnoses = analysis["barrier_diagnoses"]
    capacity = analysis["capacity_frontier"]
    ecology = analysis["ecological_value_map"]
    finalist = analysis["finalist"]
    lines = [
        "# Wagner PH Origin Ladder v1",
        "",
        f"- Fresh Wagner tasks: **{analysis['tasks']}**",
        f"- Founder acquisition: **{analysis['mean_founder_acquisition_rate']:.3f}**",
        f"- Smallest feasible quantized carrier: **{capacity['smallest_feasible_cell'] or 'none'}**",
        f"- Smallest renewal-dependent carrier: **{capacity['smallest_renewing_cell'] or 'none'}**",
        f"- Confirmation finalist: **{finalist['capacity_cell'] if finalist else 'none'}**",
        "- Confirmation reserve: **untouched**",
        "",
        "## Barrier diagnoses",
        "",
    ]
    for key, value in diagnoses.items():
        lines.append(f"- {key.replace('_', ' ')}: **{'supported' if value else 'not supported'}**")
    lines.extend(("", "## Ecological predictability", ""))
    for k, value in ecology["by_capacity"].items():
        lines.append(
            f"- k={k}: minimum useful persistence = **{value['minimum_useful_persistence']}**; "
            f"always-switch gain = {value['always_switch_gain']}; always-stay gain = {value['always_stay_gain']}"
        )
    lines.extend(
        (
            "",
            "## Interpretation boundary",
            "",
            analysis["claim_boundary"],
            "",
        )
    )
    return "\n".join(lines)
