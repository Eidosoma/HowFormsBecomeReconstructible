"""Streaming rulebook-level analysis and frozen plastic-memory gates."""

from __future__ import annotations

import collections
import math
from typing import Any, Iterable

import numpy as np

from .plastic_memory_config import PLASTIC_MEMORY_ANALYSIS_FORMAT, PlasticMemorySpec
from .rng import rng_for


Cell = tuple[str, str, float, int, str, str, int, str, str]
OutcomeKey = tuple[str, str, str, int, str, str, str, str]


def _cell(record: dict[str, Any]) -> Cell:
    return (
        str(record["condition"]),
        str(record["model"]),
        float(record["cue_fraction"]),
        int(record["cue_dwell"]),
        str(record["mark_setting"]),
        str(record["carrier"]),
        int(record["washout_age"]),
        str(record["challenge"]),
        str(record["history"]),
    )


def _outcome_key(record: dict[str, Any]) -> OutcomeKey:
    return (
        str(record["model"]),
        str(record["mark_setting"]),
        str(record["carrier"]),
        int(record["washout_age"]),
        str(record["challenge"]),
        str(record["source_id"]),
        str(record["history"]),
        str(record["half"]),
    )


def _bootstrap(
    values: list[float],
    spec: PlasticMemorySpec,
    label: str,
    simultaneous_tests: int = 1,
) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return {"mean": None, "interval": [None, None], "lower": None, "sources": 0}
    rng = rng_for(spec.master_seed, "plastic-memory-bootstrap", label)
    indices = rng.integers(0, array.size, size=(spec.bootstrap_repetitions, array.size))
    means = np.mean(array[indices], axis=1)
    ordinary_tail = (1.0 - spec.interval_level) / 2.0
    simultaneous_tail = (1.0 - spec.interval_level) / max(1, simultaneous_tests)
    return {
        "mean": float(np.mean(array)),
        "interval": [
            float(np.quantile(means, ordinary_tail)),
            float(np.quantile(means, 1.0 - ordinary_tail)),
        ],
        "lower": float(np.quantile(means, simultaneous_tail)),
        "sources": int(array.size),
        "positive_sources": int(np.sum(array > 0.0)),
    }


def _descriptive(values: list[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return {"mean": None, "sources": 0}
    return {
        "mean": float(np.mean(array)),
        "sources": int(array.size),
        "minimum": float(np.min(array)),
        "maximum": float(np.max(array)),
    }


def _probabilities(counts: collections.Counter[str], alpha: float = 0.5) -> dict[str, float]:
    categories = ("A", "B", "other")
    denominator = sum(counts.values()) + alpha * len(categories)
    return {category: (counts[category] + alpha) / denominator for category in categories}


def _crossfit_gain(
    outcomes: dict[OutcomeKey, collections.Counter[str]],
    model: str,
    mark: str,
    carrier: str,
    age: int,
    challenge: str,
    source: str,
) -> float | None:
    losses: list[float] = []
    baselines: list[float] = []
    for mapping_half, evaluation_half in (("A", "B"), ("B", "A")):
        mapping = {
            history: outcomes.get(
                (model, mark, carrier, age, challenge, source, history, mapping_half),
                collections.Counter(),
            )
            for history in ("A", "B")
        }
        evaluation = {
            history: outcomes.get(
                (model, mark, carrier, age, challenge, source, history, evaluation_half),
                collections.Counter(),
            )
            for history in ("A", "B")
        }
        if not all(sum(mapping[history].values()) and sum(evaluation[history].values()) for history in ("A", "B")):
            continue
        pooled = mapping["A"] + mapping["B"]
        baseline_probabilities = _probabilities(pooled)
        for history in ("A", "B"):
            state_probabilities = _probabilities(mapping[history])
            for category, amount in evaluation[history].items():
                losses.extend([-math.log(state_probabilities[category])] * amount)
                baselines.extend([-math.log(baseline_probabilities[category])] * amount)
    if not losses:
        return None
    return float(np.mean(baselines) - np.mean(losses))


def _source_metric_values(
    source_rates: dict[tuple[Cell, str, str], list[float]],
    outcomes: dict[OutcomeKey, collections.Counter[str]],
    model: str,
    mark: str,
    carrier: str,
    baseline_carrier: str,
    age: int,
    challenge: str,
) -> dict[str, list[float]]:
    sources = sorted(
        {
            source
            for (cell, source, field) in source_rates
            if cell[1] == model
            and cell[4] == mark
            and cell[5] in {carrier, baseline_carrier}
            and cell[6] == age
            and cell[7] == challenge
            and field == "correct_hold8"
        }
    )
    risk_differences: list[float] = []
    crossovers: list[float] = []
    gains: list[float] = []
    retained_sources: list[str] = []
    for source in sources:
        rates: dict[tuple[str, str], list[float]] = {}
        for candidate in (carrier, baseline_carrier):
            for history in ("A", "B"):
                matched = [
                    value
                    for (cell, source_id, field), value in source_rates.items()
                    if source_id == source
                    and field == "correct_hold8"
                    and cell[1] == model
                    and cell[4] == mark
                    and cell[5] == candidate
                    and cell[6] == age
                    and cell[7] == challenge
                    and cell[8] == history
                ]
                total = sum(value[1] for value in matched)
                rates[(candidate, history)] = [
                    sum(value[0] for value in matched),
                    total,
                ]
        if any(rates[key][1] == 0 for key in rates):
            continue
        carrier_rate = sum(rates[(carrier, history)][0] for history in ("A", "B")) / sum(
            rates[(carrier, history)][1] for history in ("A", "B")
        )
        baseline_rate = sum(
            rates[(baseline_carrier, history)][0] for history in ("A", "B")
        ) / sum(rates[(baseline_carrier, history)][1] for history in ("A", "B"))
        risk_differences.append(float(carrier_rate - baseline_rate))

        def destination_probability(history: str, destination: str) -> float:
            counts = collections.Counter()
            for half in ("A", "B"):
                counts.update(
                    outcomes.get(
                        (model, mark, carrier, age, challenge, source, history, half),
                        collections.Counter(),
                    )
                )
            total = sum(counts.values())
            return float(counts[destination] / total) if total else float("nan")

        p_a_ha = destination_probability("A", "A")
        p_a_hb = destination_probability("B", "A")
        p_b_hb = destination_probability("B", "B")
        p_b_ha = destination_probability("A", "B")
        if not all(math.isfinite(value) for value in (p_a_ha, p_a_hb, p_b_hb, p_b_ha)):
            risk_differences.pop()
            continue
        crossovers.append(0.5 * ((p_a_ha - p_a_hb) + (p_b_hb - p_b_ha)))
        gain = _crossfit_gain(outcomes, model, mark, carrier, age, challenge, source)
        if gain is None:
            risk_differences.pop()
            crossovers.pop()
            continue
        gains.append(gain)
        retained_sources.append(source)
    return {
        "risk_difference": risk_differences,
        "crossover": crossovers,
        "log_loss_gain": gains,
        "sources": retained_sources,
    }


def _reliability(
    source_rates: dict[tuple[Cell, str, str], list[float]],
    model: str,
    mark: str,
    carrier: str,
    age: int,
    challenge: str,
) -> float | None:
    values: dict[str, dict[str, list[float]]] = collections.defaultdict(
        lambda: {"A": [0.0, 0.0], "B": [0.0, 0.0]}
    )
    for (cell, source, field), amount in source_rates.items():
        if (
            field.startswith("correct_hold8.half-")
            and cell[1] == model
            and cell[4] == mark
            and cell[5] == carrier
            and cell[6] == age
            and cell[7] == challenge
        ):
            half = field.removeprefix("correct_hold8.half-")
            values[source][half][0] += amount[0]
            values[source][half][1] += amount[1]
    paired = [
        (halves["A"][0] / halves["A"][1], halves["B"][0] / halves["B"][1])
        for halves in values.values()
        if halves["A"][1] and halves["B"][1]
    ]
    if len(paired) < 3:
        return None
    left, right = np.asarray(paired, dtype=float).T
    if np.std(left) == 0.0 or np.std(right) == 0.0:
        return 1.0 if np.array_equal(left, right) else 0.0
    return float(np.corrcoef(left, right)[0, 1])


def _candidate_gate(
    spec: PlasticMemorySpec,
    source_rates: dict[tuple[Cell, str, str], list[float]],
    outcomes: dict[OutcomeKey, collections.Counter[str]],
    model: str,
    mark: str,
    carrier: str,
    age: int,
    challenge: str,
    equivalence: dict[str, Any],
    simultaneous_tests: int,
) -> dict[str, Any]:
    raw = _source_metric_values(
        source_rates,
        outcomes,
        model,
        mark,
        carrier,
        "reset_both",
        age,
        challenge,
    )
    metrics = {
        name: _bootstrap(values, spec, f"gate.{model}.{mark}.{carrier}.{age}.{challenge}.{name}", simultaneous_tests)
        for name, values in raw.items()
        if name != "sources"
    }
    reliability = _reliability(source_rates, model, mark, carrier, age, challenge)
    criteria = {
        "risk_difference_at_least_0_05": metrics["risk_difference"]["mean"] is not None
        and float(metrics["risk_difference"]["mean"]) >= 0.05,
        "risk_difference_lower_above_zero": metrics["risk_difference"]["lower"] is not None
        and float(metrics["risk_difference"]["lower"]) > 0.0,
        "crossover_at_least_0_05": metrics["crossover"]["mean"] is not None
        and float(metrics["crossover"]["mean"]) >= 0.05,
        "crossover_lower_above_zero": metrics["crossover"]["lower"] is not None
        and float(metrics["crossover"]["lower"]) > 0.0,
        "log_loss_gain_at_least_0_02": metrics["log_loss_gain"]["mean"] is not None
        and float(metrics["log_loss_gain"]["mean"]) >= 0.02,
        "log_loss_gain_lower_above_zero": metrics["log_loss_gain"]["lower"] is not None
        and float(metrics["log_loss_gain"]["lower"]) > 0.0,
        "split_half_reliability_at_least_0_80": reliability is not None
        and reliability >= 0.80,
        "self_transplant_equivalence": bool(equivalence.get("equal", False)),
    }
    return {
        "model": model,
        "mark_setting": mark,
        "carrier": carrier,
        "baseline": "reset_both",
        "washout_age": age,
        "challenge": challenge,
        "metrics": metrics,
        "split_half_reliability": reliability,
        "criteria": criteria,
        "passed": all(criteria.values()),
        "source_ids": raw["sources"],
    }


def analyze_memory_records(
    records: Iterable[dict[str, Any]], spec: PlasticMemorySpec
) -> dict[str, Any]:
    spec.validate()
    source_rates: dict[tuple[Cell, str, str], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    outcomes: dict[OutcomeKey, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    acquisition: dict[tuple[str, float, int, str, str], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    control_matches: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    self_digests: dict[tuple[Any, ...], str] = {}
    transplant_pairs = 0
    transplant_matches = 0
    future_ids: set[str] = set()
    record_count = 0
    for record in records:
        record_count += 1
        future_id = str(record["future_id"])
        if future_id in future_ids:
            raise ValueError(f"duplicate plastic-memory future id: {future_id}")
        future_ids.add(future_id)
        cell = _cell(record)
        source = str(record["source_id"])
        for field in ("acquired", "correct_hold8", "wrong_hold8", "generic_hold8", "returned"):
            value = source_rates[(cell, source, field)]
            value[0] += float(record[field])
            value[1] += 1.0
        half_field = f"correct_hold8.half-{record['half']}"
        half_value = source_rates[(cell, source, half_field)]
        half_value[0] += float(record["correct_hold8"])
        half_value[1] += 1.0
        outcomes[_outcome_key(record)][str(record["form_destination"])] += 1
        acquisition_key = (
            str(record["model"]),
            float(record["cue_fraction"]),
            int(record["cue_dwell"]),
            str(record["history"]),
            source,
        )
        acquisition[acquisition_key][0] += float(record["acquired"])
        acquisition[acquisition_key][1] += 1.0
        if record["carrier"] in {
            "descriptor_matched_null",
            "destination_matched_donor",
            "state_pattern_shuffle",
        }:
            matched = control_matches[str(record["carrier"])]
            matched[0] += int(bool(record["descriptor_exact"]))
            matched[1] += 1
        if record["mark_setting"] == "none" and record["carrier"] in {
            "self_continuation",
            "state_transplant",
        }:
            key = (
                record["condition"],
                source,
                record["midpoint_index"],
                record["history"],
                record["washout_age"],
                record["challenge"],
                record["future_index"],
            )
            if record["carrier"] == "self_continuation":
                self_digests[key] = str(record["trace_digest"])
            else:
                transplant_pairs += 1
                transplant_matches += int(self_digests.get(key) == record["trace_digest"])

    if transplant_matches != transplant_pairs:
        # Lexical carrier ordering can put state transplant before self. The
        # persisted pairing count is still checked by the study verifier; mark
        # this analysis audit incomplete rather than silently calling it equal.
        equivalence = {
            "pairs": transplant_pairs,
            "matches": transplant_matches,
            "equal": False,
            "note": "pairing requires order-independent verifier audit",
        }
    else:
        equivalence = {
            "pairs": transplant_pairs,
            "matches": transplant_matches,
            "equal": transplant_pairs > 0,
        }

    rates: dict[str, Any] = {}
    for (cell, source, field), total in source_rates.items():
        if total[1] == 0:
            continue
        key = (
            f"{cell[0]}.{cell[1]}.cue-{cell[2]:g}x{cell[3]}.mark-{cell[4]}."
            f"{cell[5]}.age-{cell[6]}.{cell[7]}.history-{cell[8]}.{field}"
        )
        rates.setdefault(key, []).append(total[0] / total[1])
    # The registered inferential bootstraps are applied to causal contrasts
    # below. Fine-grained cell rates remain descriptive to keep reanalysis
    # bounded even for the 200-rulebook confirmation.
    rate_summaries = {key: _descriptive(values) for key, values in rates.items()}

    calibration: dict[str, Any] = {}
    grouped_acquisition: dict[tuple[str, float, int, str], list[float]] = collections.defaultdict(list)
    for (model, fraction, dwell, history, _source), value in acquisition.items():
        if value[1]:
            grouped_acquisition[(model, fraction, dwell, history)].append(value[0] / value[1])
    for key, values in sorted(grouped_acquisition.items()):
        model, fraction, dwell, history = key
        label = f"{model}.cue-{fraction:g}x{dwell}.history-{history}"
        calibration[label] = _bootstrap(values, spec, f"calibration.{label}")

    primary_models = [model.name for model in spec.models if model.primary]
    state_candidate_count = sum(
        any(
            condition.model == model
            and "state_transplant" in condition.carrier_arms
            for condition in spec.conditions
        )
        for model in primary_models
    )
    mark_candidate_count = sum(
        any(
            condition.model == model
            and mark.name in condition.mark_settings
            and "mark_transplant" in condition.carrier_arms
            for condition in spec.conditions
        )
        for model in primary_models
        for mark in spec.mark_settings
        if mark.active
    )
    simultaneous = max(1, (state_candidate_count + mark_candidate_count) * 3)
    state_gates = {
        model: _candidate_gate(
            spec,
            source_rates,
            outcomes,
            model,
            "none",
            "state_transplant",
            0,
            "neutral_damage",
            equivalence,
            simultaneous,
        )
        for model in primary_models
        if any(condition.model == model and "state_transplant" in condition.carrier_arms for condition in spec.conditions)
    }
    mark_gates: dict[str, dict[str, Any]] = {}
    for model in primary_models:
        mark_gates[model] = {}
        for mark in spec.mark_settings:
            if not mark.active:
                continue
            if not any(
                condition.model == model
                and mark.name in condition.mark_settings
                and "mark_transplant" in condition.carrier_arms
                for condition in spec.conditions
            ):
                continue
            mark_gates[model][mark.name] = _candidate_gate(
                spec,
                source_rates,
                outcomes,
                model,
                mark.name,
                "mark_transplant",
                0,
                "forced_break",
                equivalence,
                simultaneous,
            )

    persistence: dict[str, Any] = {}
    for model in primary_models:
        for mark_name, carrier, challenge in (
            ("none", "state_transplant", "neutral_damage"),
            *(
                (mark.name, "mark_transplant", "forced_break")
                for mark in spec.mark_settings
                if mark.active
            ),
        ):
            for age in (1, 2, 4, 8):
                if not any(
                    condition.model == model
                    and mark_name in condition.mark_settings
                    and carrier in condition.carrier_arms
                    and age in condition.washout_ages
                    and challenge in condition.challenges
                    for condition in spec.conditions
                ):
                    continue
                raw = _source_metric_values(
                    source_rates,
                    outcomes,
                    model,
                    mark_name,
                    carrier,
                    "reset_both",
                    age,
                    challenge,
                )
                label = f"{model}.{mark_name}.{carrier}.age-{age}.{challenge}"
                persistence[label] = {
                    name: _bootstrap(values, spec, f"persistence.{label}.{name}")
                    for name, values in raw.items()
                    if name != "sources"
                }

    return {
        "format": PLASTIC_MEMORY_ANALYSIS_FORMAT,
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "exploratory": spec.exploratory,
        "record_count": record_count,
        "unique_future_ids": len(future_ids),
        "rates": rate_summaries,
        "calibration": calibration,
        "state_transfer_gates": state_gates,
        "mark_transfer_gates": mark_gates,
        "persistence": persistence,
        "self_transplant_equivalence": equivalence,
        "descriptor_exact_rate": (
            control_matches["descriptor_matched_null"][0]
            / control_matches["descriptor_matched_null"][1]
            if control_matches["descriptor_matched_null"][1]
            else None
        ),
        "control_match_rates": {
            carrier: values[0] / values[1]
            for carrier, values in sorted(control_matches.items())
            if values[1]
        },
        "thresholds": {
            "risk_difference": 0.05,
            "crossover": 0.05,
            "log_loss_gain": 0.02,
            "split_half_reliability": 0.80,
            "interval_level": spec.interval_level,
            "simultaneous_primary_tests": simultaneous,
        },
    }


def select_calibrated_cues(analysis: dict[str, Any]) -> dict[str, Any]:
    """Choose the least successful pulse dose without consulting memory outcomes."""

    cells: dict[tuple[str, float, int], dict[str, float]] = collections.defaultdict(dict)
    for label, value in analysis["calibration"].items():
        model, rest = label.split(".cue-", 1)
        dose, history = rest.split(".history-", 1)
        fraction_text, dwell_text = dose.split("x", 1)
        if value["mean"] is not None:
            cells[(model, float(fraction_text), int(dwell_text))][history] = float(value["mean"])
    selected: dict[str, Any] = {}
    for model in sorted({key[0] for key in cells}):
        eligible = []
        for (candidate_model, fraction, dwell), histories in cells.items():
            if candidate_model != model or set(histories) != {"A", "B"}:
                continue
            if min(histories.values()) < 0.80 or abs(histories["A"] - histories["B"]) > 0.10:
                continue
            eligible.append((fraction * dwell, fraction, dwell, histories))
        if not eligible:
            selected[model] = {"ready": False, "cue": None}
            continue
        _, fraction, dwell, histories = min(eligible, key=lambda value: value[:3])
        selected[model] = {
            "ready": True,
            "cue": {"fraction": fraction, "dwell": dwell},
            "history_rates": histories,
            "selection_used_post_release_outcomes": False,
        }
    return {
        "format": "gre-plastic-memory-cue-selection-v1",
        "models": selected,
        "all_primary_ready": bool(selected) and all(value["ready"] for value in selected.values()),
    }


def select_mark_candidates(analysis: dict[str, Any]) -> dict[str, Any]:
    """Choose the shortest, weakest passing slow-mark setting per engine."""

    selections: dict[str, Any] = {}
    for model, gates in analysis["mark_transfer_gates"].items():
        passing = [value for value in gates.values() if value["passed"]]
        passing.sort(
            key=lambda value: (
                int(value["mark_setting"].split(".")[0].removeprefix("half-")),
                float(value["mark_setting"].split("mu-")[1]),
            )
        )
        selections[model] = {
            "selected": passing[0]["mark_setting"] if passing else None,
            "passing": [value["mark_setting"] for value in passing],
        }
    common = None
    if selections:
        sets = [set(value["passing"]) for value in selections.values()]
        common_values = set.intersection(*sets) if sets else set()
        if common_values:
            common = min(
                common_values,
                key=lambda name: (
                    int(name.split(".")[0].removeprefix("half-")),
                    float(name.split("mu-")[1]),
                ),
            )
    return {
        "format": "gre-plastic-memory-mark-selection-v1",
        "models": selections,
        "common_selected": common,
        "outcome_signs_used": True,
        "role": "fresh confirmation candidate generation only",
    }
