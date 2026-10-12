"""Frozen causal gates and fair-engine contrasts for Plastic Heredity v2."""

from __future__ import annotations

import collections
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import read_jsonl_gz
from .plastic_heredity_v2_config import (
    PLASTIC_HEREDITY_V2_ANALYSIS_FORMAT,
    PlasticHeredityV2Spec,
)
from .plastic_memory_analysis import (
    _bootstrap,
    _candidate_gate,
    _cell,
    _outcome_key,
    _source_metric_values,
)
from .plastic_memory_config import CueDose
from .rng import rng_for


def _history_rates(
    source_rates: dict[tuple[Any, str, str], list[float]],
    model: str,
    carrier: str,
    age: int,
    challenge: str,
    history: str,
) -> list[float]:
    totals: dict[str, list[float]] = collections.defaultdict(lambda: [0.0, 0.0])
    for (cell, source, field), value in source_rates.items():
        if (
            field == "correct_hold8"
            and cell[1] == model
            and cell[4] == "none"
            and cell[5] == carrier
            and cell[6] == age
            and cell[7] == challenge
            and cell[8] == history
        ):
            totals[source][0] += value[0]
            totals[source][1] += value[1]
    return [value[0] / value[1] for value in totals.values() if value[1]]


def _contrast(
    memory_spec: Any,
    source_rates: dict[tuple[Any, str, str], list[float]],
    outcomes: dict[Any, collections.Counter[str]],
    model: str,
    carrier: str,
    baseline: str,
    age: int,
    challenge: str,
    label: str,
    simultaneous: int,
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    raw = _source_metric_values(
        source_rates,
        outcomes,
        model,
        "none",
        carrier,
        baseline,
        age,
        challenge,
    )
    estimates = {
        name: _bootstrap(
            values,
            memory_spec,
            f"plastic-heredity-v2.{label}.{name}",
            simultaneous,
        )
        for name, values in raw.items()
        if name != "sources"
    }
    return estimates, raw


def _equivalence(
    pairs: dict[tuple[Any, ...], dict[str, str]],
) -> dict[str, Any]:
    complete = [value for value in pairs.values() if len(value) == 2]
    matches = sum(
        value["self_continuation"] == value["state_transplant"]
        for value in complete
    )
    return {
        "pairs": len(complete),
        "matches": matches,
        "equal": bool(complete) and matches == len(complete),
    }


def _difference_interval(
    left: list[float],
    right: list[float],
    spec: PlasticHeredityV2Spec,
    label: str,
    level: float,
    simultaneous_tests: int = 1,
) -> dict[str, Any]:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if not a.size or not b.size:
        return {
            "mean": None,
            "interval": [None, None],
            "left_sources": int(a.size),
            "right_sources": int(b.size),
        }
    rng = rng_for(spec.master_seed, "plastic-heredity-v2-engine-bootstrap", label)
    repetitions = spec.bootstrap_repetitions
    left_indices = rng.integers(0, a.size, size=(repetitions, a.size))
    right_indices = rng.integers(0, b.size, size=(repetitions, b.size))
    draws = np.mean(a[left_indices], axis=1) - np.mean(b[right_indices], axis=1)
    tail = (1.0 - level) / (2.0 * max(1, simultaneous_tests))
    return {
        "mean": float(np.mean(a) - np.mean(b)),
        "interval": [
            float(np.quantile(draws, tail)),
            float(np.quantile(draws, 1.0 - tail)),
        ],
        "left_sources": int(a.size),
        "right_sources": int(b.size),
    }


def fair_engine_verdict(
    analysis: dict[str, Any], spec: PlasticHeredityV2Spec
) -> dict[str, Any]:
    """Classify the Boolean-minus-Wagner difference under frozen margins."""

    inputs = analysis["engine_comparison_inputs"]
    if set(inputs) != {"boolean", "wagner"}:
        return {
            "verdict": "not-estimable",
            "reason": "both engines are required",
        }
    margins = {"risk_difference": 0.02, "crossover": 0.05, "log_loss_gain": 0.01}
    simultaneous: dict[str, Any] = {}
    equivalence: dict[str, Any] = {}
    for metric in margins:
        simultaneous[metric] = _difference_interval(
            inputs["boolean"][metric],
            inputs["wagner"][metric],
            spec,
            f"simultaneous.{metric}",
            spec.interval_level,
            3,
        )
        equivalence[metric] = _difference_interval(
            inputs["boolean"][metric],
            inputs["wagner"][metric],
            spec,
            f"equivalence.{metric}",
            0.90,
        )
    risk = simultaneous["risk_difference"]
    risk_interval = risk["interval"]
    excludes_zero = (
        risk_interval[0] is not None
        and (float(risk_interval[0]) > 0.0 or float(risk_interval[1]) < 0.0)
    )
    risk_mean = risk["mean"]
    direction = 0.0 if risk_mean is None else float(np.sign(risk_mean))
    directional_agreement = direction != 0.0 and all(
        value["mean"] is not None and float(np.sign(value["mean"])) == direction
        for name, value in simultaneous.items()
        if name != "risk_difference"
    )
    different = (
        risk_mean is not None
        and abs(float(risk_mean)) >= margins["risk_difference"]
        and excludes_zero
        and directional_agreement
    )
    equivalent = all(
        value["interval"][0] is not None
        and float(value["interval"][0]) > -margins[name]
        and float(value["interval"][1]) < margins[name]
        for name, value in equivalence.items()
    )
    verdict = "different" if different else "equivalent" if equivalent else "inconclusive"
    return {
        "contrast": "boolean-minus-wagner",
        "verdict": verdict,
        "simultaneous_intervals": simultaneous,
        "equivalence_intervals_90": equivalence,
        "equivalence_margins": margins,
        "criteria": {
            "absolute_risk_delta_at_least_0_02": risk_mean is not None
            and abs(float(risk_mean)) >= margins["risk_difference"],
            "simultaneous_risk_interval_excludes_zero": excludes_zero,
            "crossover_and_logloss_direction_agree": directional_agreement,
            "all_90_percent_intervals_inside_equivalence_margins": equivalent,
        },
    }


def analyze_state_channel_path(
    futures_path: Path, spec: PlasticHeredityV2Spec
) -> dict[str, Any]:
    """Analyze an exact or natural state-channel study without pooling engines."""

    spec.validate()
    memory_spec = spec.memory_spec()
    source_rates: dict[tuple[Any, str, str], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    outcomes: dict[Any, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    acquisition: dict[tuple[str, str, str], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    acquisition_seen: set[tuple[Any, ...]] = set()
    pairs: dict[tuple[Any, ...], dict[str, str]] = {}
    control_matches: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    future_ids: set[str] = set()
    record_count = 0
    for record in read_jsonl_gz(futures_path):
        record_count += 1
        future_id = str(record["future_id"])
        if future_id in future_ids:
            raise ValueError(f"duplicate v2 state-channel future: {future_id}")
        future_ids.add(future_id)
        cell = _cell(record)
        source = str(record["source_id"])
        for field in (
            "acquired",
            "correct_hold8",
            "wrong_hold8",
            "generic_hold8",
            "returned",
        ):
            value = source_rates[(cell, source, field)]
            value[0] += float(record[field])
            value[1] += 1.0
        half = source_rates[(cell, source, f"correct_hold8.half-{record['half']}")]
        half[0] += float(record["correct_hold8"])
        half[1] += 1.0
        outcomes[_outcome_key(record)][str(record["form_destination"])] += 1
        acquisition_key = (
            record["model"],
            source,
            record["midpoint_index"],
            record["history"],
            record["future_index"],
        )
        if acquisition_key not in acquisition_seen:
            acquisition_seen.add(acquisition_key)
            amount = acquisition[(str(record["model"]), source, str(record["history"]))]
            amount[0] += float(record["acquired"])
            amount[1] += 1.0
        if record["carrier"] in {"self_continuation", "state_transplant"}:
            key = (
                record["condition"],
                source,
                record["midpoint_index"],
                record["history"],
                record["washout_age"],
                record["challenge"],
                record["future_index"],
            )
            pairs.setdefault(key, {})[str(record["carrier"])] = str(
                record["trace_digest"]
            )
        if record["carrier"] in {
            "destination_matched_donor",
            "descriptor_matched_null",
            "state_pattern_shuffle",
        }:
            values = control_matches[str(record["carrier"])]
            values[0] += int(bool(record["descriptor_exact"]))
            values[1] += 1

    path_equivalence = _equivalence(pairs)
    models = tuple(model.name for model in memory_spec.models)
    simultaneous = max(1, len(models) * 9)
    acquisition_summary: dict[str, Any] = {}
    for model in models:
        acquisition_summary[model] = {}
        for history in ("A", "B"):
            values = [
                amount[0] / amount[1]
                for (candidate, _source, candidate_history), amount in acquisition.items()
                if candidate == model and candidate_history == history and amount[1]
            ]
            acquisition_summary[model][history] = _bootstrap(
                values,
                memory_spec,
                f"plastic-heredity-v2.acquisition.{model}.{history}",
                simultaneous,
            )

    gates: dict[str, Any] = {}
    comparison_inputs: dict[str, Any] = {}
    for model in models:
        primary = _candidate_gate(
            memory_spec,
            source_rates,
            outcomes,
            model,
            "none",
            "state_transplant",
            0,
            "neutral_damage",
            path_equivalence,
            simultaneous,
        )
        shuffle, _ = _contrast(
            memory_spec,
            source_rates,
            outcomes,
            model,
            "state_transplant",
            "state_pattern_shuffle",
            0,
            "neutral_damage",
            f"{model}.shuffle",
            simultaneous,
        )
        generation_one, _ = _contrast(
            memory_spec,
            source_rates,
            outcomes,
            model,
            "state_transplant",
            "reset_both",
            1,
            "release_only",
            f"{model}.generation-one",
            simultaneous,
        )
        _, raw = _contrast(
            memory_spec,
            source_rates,
            outcomes,
            model,
            "state_transplant",
            "reset_both",
            0,
            "neutral_damage",
            f"{model}.engine-input",
            simultaneous,
        )
        engine = model.split(".", 1)[0]
        comparison_inputs[engine] = {
            name: list(values)
            for name, values in raw.items()
            if name != "sources"
        }
        absolute = {
            history: _bootstrap(
                _history_rates(
                    source_rates,
                    model,
                    "state_transplant",
                    0,
                    "neutral_damage",
                    history,
                ),
                memory_spec,
                f"plastic-heredity-v2.absolute.{model}.{history}",
                simultaneous,
            )
            for history in ("A", "B")
        }
        acquired = acquisition_summary[model]
        means = [acquired[history]["mean"] for history in ("A", "B")]
        criteria = {
            **primary["criteria"],
            "both_histories_acquisition_at_least_0_80": all(
                value is not None and float(value) >= 0.80 for value in means
            ),
            "history_acquisition_imbalance_at_most_0_10": all(
                value is not None for value in means
            )
            and abs(float(means[0]) - float(means[1])) <= 0.10,
            "both_histories_absolute_hold8_at_least_0_20": all(
                absolute[history]["mean"] is not None
                and float(absolute[history]["mean"]) >= 0.20
                for history in ("A", "B")
            ),
            "state_beats_pattern_shuffle": shuffle["risk_difference"]["lower"]
            is not None
            and float(shuffle["risk_difference"]["lower"]) > 0.0,
            "generation_one_risk_lower_above_zero": generation_one[
                "risk_difference"
            ]["lower"]
            is not None
            and float(generation_one["risk_difference"]["lower"]) > 0.0,
            "generation_one_crossover_lower_above_zero": generation_one[
                "crossover"
            ]["lower"]
            is not None
            and float(generation_one["crossover"]["lower"]) > 0.0,
        }
        gates[model] = {
            "model": model,
            "engine": engine,
            "primary_transfer": primary,
            "shuffle_contrast": shuffle,
            "generation_one": generation_one,
            "absolute_hold8": absolute,
            "criteria": criteria,
            "passed": all(criteria.values()),
        }

    result = {
        "format": PLASTIC_HEREDITY_V2_ANALYSIS_FORMAT,
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "exploratory": spec.exploratory,
        "record_count": record_count,
        "unique_future_ids": len(future_ids),
        "acquisition": acquisition_summary,
        "state_channel_gates": gates,
        "engine_comparison_inputs": comparison_inputs,
        "self_transplant_equivalence": path_equivalence,
        "control_match_rates": {
            name: values[0] / values[1]
            for name, values in sorted(control_matches.items())
            if values[1]
        },
        "thresholds": {
            "acquisition": 0.80,
            "acquisition_imbalance": 0.10,
            "absolute_hold8": 0.20,
            "risk_difference": 0.05,
            "crossover": 0.05,
            "log_loss_gain": 0.02,
            "split_half_reliability": 0.80,
            "interval_level": spec.interval_level,
            "simultaneous_primary_tests": simultaneous,
        },
    }
    result["fair_engine_verdict"] = fair_engine_verdict(result, spec)
    return result


def passing_engines(analysis: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        gate["engine"]
        for gate in analysis["state_channel_gates"].values()
        if gate["passed"]
    )


def select_weakest_balanced_cues(
    analysis: dict[str, Any], spec: PlasticHeredityV2Spec
) -> dict[str, CueDose]:
    """Use acquisition only; no post-release outcome can choose a writer."""

    selected: dict[str, CueDose] = {}
    for engine in spec.engines:
        candidates: list[tuple[float, int, CueDose]] = []
        for writer in spec.writers:
            if writer.engines != (engine,):
                continue
            model = f"{engine}.{writer.name}"
            histories = analysis["acquisition"].get(model, {})
            means = [histories.get(history, {}).get("mean") for history in ("A", "B")]
            if (
                all(value is not None and float(value) >= 0.80 for value in means)
                and abs(float(means[0]) - float(means[1])) <= 0.10
            ):
                dose = CueDose(writer.fraction, writer.dwell)
                candidates.append((dose.fraction, dose.dwell, dose))
        if candidates:
            selected[engine] = min(candidates, key=lambda value: value[:2])[2]
    return selected


def render_state_channel_report(analysis: dict[str, Any]) -> str:
    lines = [
        f"# Plastic Heredity v2: {analysis['phase']}",
        "",
        (
            "> Exploratory cohort."
            if analysis["exploratory"]
            else "> Untouched confirmatory cohort."
        ),
        "",
        f"- Futures: {analysis['record_count']:,}",
        f"- Fair-engine verdict: **{analysis['fair_engine_verdict']['verdict']}**",
        "",
        "## Engine-specific state-channel gates",
        "",
    ]
    for gate in analysis["state_channel_gates"].values():
        metrics = gate["primary_transfer"]["metrics"]
        failed = [name for name, passed in gate["criteria"].items() if not passed]
        lines.extend(
            (
                f"### {gate['engine']} — {'PASS' if gate['passed'] else 'fail'}",
                "",
                f"- State-minus-reset risk: {metrics['risk_difference']['mean']}",
                f"- History crossover: {metrics['crossover']['mean']}",
                f"- Held-out log-loss gain: {metrics['log_loss_gain']['mean']}",
                f"- Failed criteria: {failed or 'none'}",
                "",
            )
        )
    lines.extend(
        (
            "## Interpretation boundary",
            "",
            "This assay gives both engines the same complete expression-state write. "
            "A pass therefore establishes a minimal state-carried history channel, not "
            "a hidden molecular carrier. The fair-engine verdict asks whether the two "
            "implementations differ after that writing advantage is equalized.",
            "",
        )
    )
    return "\n".join(lines)
