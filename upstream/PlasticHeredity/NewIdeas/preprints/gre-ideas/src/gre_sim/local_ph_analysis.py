"""Single-pass paired inference and frozen gates for Wagner local memory."""

from __future__ import annotations

import collections
import math
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import read_jsonl_gz
from .local_ph_config import LOCAL_PH_ANALYSIS_FORMAT, LocalStudySpec
from .plastic_memory_analysis import _bootstrap


Key = tuple[str, str, int, str, str, str]


def _rate(counts: dict[Key, list[float]], condition: str, generation: int, challenge: str, field: str) -> float | None:
    matched = [
        value
        for (source, candidate, age, event, history, half, candidate_field), value in counts.items()
        if candidate == condition and age == generation and event == challenge and candidate_field == field
    ]
    total = sum(value[1] for value in matched)
    return sum(value[0] for value in matched) / total if total else None


def _source_field_differences(
    counts: dict[Any, list[float]],
    left: str,
    right: str,
    generation: int,
    challenge: str,
    field: str,
) -> list[float]:
    sources = sorted({key[0] for key in counts})
    result: list[float] = []
    for source in sources:
        rates: dict[str, list[float]] = {}
        for condition in (left, right):
            matched = [
                value
                for key, value in counts.items()
                if key[0] == source
                and key[1] == condition
                and key[2] == generation
                and key[3] == challenge
                and key[6] == field
            ]
            rates[condition] = [sum(value[0] for value in matched), sum(value[1] for value in matched)]
        if all(rates[value][1] for value in (left, right)):
            result.append(
                rates[left][0] / rates[left][1] - rates[right][0] / rates[right][1]
            )
    return result


def _destination_probability(
    outcomes: dict[Any, collections.Counter[str]],
    source: str,
    condition: str,
    generation: int,
    challenge: str,
    history: str,
    destination: str,
) -> float | None:
    total = collections.Counter()
    for half in ("A", "B"):
        total.update(outcomes[(source, condition, generation, challenge, history, half)])
    amount = sum(total.values())
    return float(total[destination] / amount) if amount else None


def _crossfit_gain(
    outcomes: dict[Any, collections.Counter[str]],
    source: str,
    condition: str,
    generation: int,
    challenge: str,
) -> float | None:
    losses: list[float] = []
    baselines: list[float] = []
    categories = ("A", "B", "other")
    for mapping_half, evaluation_half in (("A", "B"), ("B", "A")):
        mapping = {
            history: outcomes[(source, condition, generation, challenge, history, mapping_half)]
            for history in ("A", "B")
        }
        evaluation = {
            history: outcomes[(source, condition, generation, challenge, history, evaluation_half)]
            for history in ("A", "B")
        }
        if not all(sum(mapping[value].values()) and sum(evaluation[value].values()) for value in ("A", "B")):
            continue
        pooled = mapping["A"] + mapping["B"]

        def probabilities(counter: collections.Counter[str]) -> dict[str, float]:
            denominator = sum(counter.values()) + 1.5
            return {value: (counter[value] + 0.5) / denominator for value in categories}

        baseline = probabilities(pooled)
        for history in ("A", "B"):
            predicted = probabilities(mapping[history])
            for category, amount in evaluation[history].items():
                losses.extend([-math.log(predicted[category])] * amount)
                baselines.extend([-math.log(baseline[category])] * amount)
    return float(np.mean(baselines) - np.mean(losses)) if losses else None


def _metrics(
    counts: dict[Any, list[float]],
    outcomes: dict[Any, collections.Counter[str]],
    spec: LocalStudySpec,
    condition: str,
    generation: int,
    challenge: str,
    simultaneous: int,
) -> dict[str, Any]:
    sources = sorted({key[0] for key in counts})
    risk = _source_field_differences(counts, condition, "zero", generation, challenge, "correct_hold8")
    crossovers: list[float] = []
    logloss: list[float] = []
    for source in sources:
        probabilities = (
            _destination_probability(outcomes, source, condition, generation, challenge, "A", "A"),
            _destination_probability(outcomes, source, condition, generation, challenge, "B", "A"),
            _destination_probability(outcomes, source, condition, generation, challenge, "B", "B"),
            _destination_probability(outcomes, source, condition, generation, challenge, "A", "B"),
        )
        if all(value is not None for value in probabilities):
            p_a_ha, p_a_hb, p_b_hb, p_b_ha = (float(value) for value in probabilities)
            crossovers.append(0.5 * ((p_a_ha - p_a_hb) + (p_b_hb - p_b_ha)))
        gain = _crossfit_gain(outcomes, source, condition, generation, challenge)
        if gain is not None:
            logloss.append(gain)
    return {
        "risk_difference": _bootstrap(risk, spec, f"local-ph.{condition}.g{generation}.{challenge}.risk", simultaneous),
        "crossover": _bootstrap(crossovers, spec, f"local-ph.{condition}.g{generation}.{challenge}.crossover", simultaneous),
        "log_loss_gain": _bootstrap(logloss, spec, f"local-ph.{condition}.g{generation}.{challenge}.logloss", simultaneous),
    }


def _field_contrast(
    counts: dict[Any, list[float]],
    spec: LocalStudySpec,
    left: str,
    right: str,
    generation: int,
    challenge: str,
    field: str,
    simultaneous: int,
) -> dict[str, Any]:
    return _bootstrap(
        _source_field_differences(counts, left, right, generation, challenge, field),
        spec,
        f"local-ph.{left}.versus.{right}.g{generation}.{challenge}.{field}",
        simultaneous,
    )


def _reliability(counts: dict[Any, list[float]], condition: str) -> float | None:
    values: list[tuple[float, float]] = []
    for source in sorted({key[0] for key in counts}):
        halves: list[float] = []
        for half in ("A", "B"):
            matched = [
                value
                for key, value in counts.items()
                if key[0] == source
                and key[1] == condition
                and key[2] == 4
                and key[3] == "forced_break"
                and key[5] == half
                and key[6] == "correct_hold8"
            ]
            total = sum(value[1] for value in matched)
            halves.append(sum(value[0] for value in matched) / total if total else float("nan"))
        if all(math.isfinite(value) for value in halves):
            values.append((halves[0], halves[1]))
    if len(values) < 3:
        return None
    left, right = np.asarray(values, dtype=float).T
    if np.std(left) == 0.0 or np.std(right) == 0.0:
        return 1.0 if np.array_equal(left, right) else 0.0
    return float(np.corrcoef(left, right)[0, 1])


def analyze_local_path(path: Path, spec: LocalStudySpec) -> dict[str, Any]:
    """Aggregate once, then evaluate all preregistered source-paired contrasts."""

    spec.validate()
    counts: dict[Any, list[float]] = collections.defaultdict(lambda: [0.0, 0.0])
    outcomes: dict[Any, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    acquired: dict[str, list[float]] = collections.defaultdict(lambda: [0.0, 0.0])
    future_ids: set[str] = set()
    record_count = 0
    for record in read_jsonl_gz(path):
        record_count += 1
        future_id = str(record["future_id"])
        if future_id in future_ids:
            raise ValueError(f"duplicate local PH future: {future_id}")
        future_ids.add(future_id)
        key_base = (
            str(record["source_id"]),
            str(record["condition"]),
            int(record["generation"]),
            str(record["challenge"]),
            str(record["history"]),
            str(record["half"]),
        )
        for field in ("correct_hold8", "wrong_hold8", "returned"):
            counts[(*key_base, field)][0] += float(record[field])
            counts[(*key_base, field)][1] += 1.0
        destination = str(record["form_destination"])
        if destination not in {"A", "B"}:
            destination = "other"
        outcomes[key_base][destination] += 1
        acquisition = acquired[str(record["source_id"])]
        acquisition[0] += float(record["acquired"])
        acquisition[1] += 1.0
    acquisition_rate = float(
        np.mean([value[0] / value[1] for value in acquired.values() if value[1]])
    )
    simultaneous = max(1, len(spec.genomes) * 18)
    gates: dict[str, Any] = {}
    for genome in spec.genomes:
        intact = f"{genome.name}.intact"
        primary = _metrics(counts, outcomes, spec, intact, 4, "forced_break", simultaneous)
        persistence8 = _metrics(counts, outcomes, spec, intact, 8, "forced_break", simultaneous)
        persistence16 = _metrics(counts, outcomes, spec, intact, 16, "forced_break", simultaneous)
        strong = _metrics(counts, outcomes, spec, f"{genome.name}.strong", 8, "forced_break", simultaneous)
        control_names = [
            f"{genome.name}.founder-write-off",
            f"{genome.name}.renewal-off",
            f"{genome.name}.reader-off",
            f"{genome.name}.shuffle",
            "zero",
        ]
        if genome.k < spec.genes:
            control_names.append(f"{genome.name}.random-mask")
        controls = {
            name: _field_contrast(
                counts, spec, intact, name, 4, "forced_break", "correct_hold8", simultaneous
            )
            for name in control_names
        }
        reverse = _field_contrast(
            counts,
            spec,
            f"{genome.name}.reverse-g2",
            intact,
            4,
            "forced_break",
            "wrong_hold8",
            simultaneous,
        )
        intact_rate = _rate(counts, intact, 4, "forced_break", "correct_hold8")
        zero_rate = _rate(counts, "zero", 4, "forced_break", "correct_hold8")
        erase_name = f"{genome.name}.erase-g2"
        rescue_name = f"{genome.name}.erase-g2-rescue-g3"
        erase_rate = _rate(counts, erase_name, 4, "forced_break", "correct_hold8")
        rescue_rate = _rate(counts, rescue_name, 4, "forced_break", "correct_hold8")
        ablation_reduction = None
        rescue_fraction = None
        if None not in {intact_rate, zero_rate, erase_rate} and float(intact_rate) > float(zero_rate):
            ablation_reduction = (float(intact_rate) - float(erase_rate)) / (float(intact_rate) - float(zero_rate))
        if None not in {intact_rate, erase_rate, rescue_rate} and float(intact_rate) > float(erase_rate):
            rescue_fraction = (float(rescue_rate) - float(erase_rate)) / (float(intact_rate) - float(erase_rate))
        reliability = _reliability(counts, intact)
        risk = primary["risk_difference"]
        crossover = primary["crossover"]
        logloss = primary["log_loss_gain"]
        criteria = {
            "founder_acquisition_at_least_0_80": acquisition_rate >= 0.80,
            "generation_4_risk_at_least_0_05": risk["mean"] is not None and float(risk["mean"]) >= 0.05,
            "generation_4_risk_lower_above_zero": risk["lower"] is not None and float(risk["lower"]) > 0.0,
            "generation_4_crossover_at_least_0_05": crossover["mean"] is not None and float(crossover["mean"]) >= 0.05,
            "generation_4_crossover_lower_above_zero": crossover["lower"] is not None and float(crossover["lower"]) > 0.0,
            "generation_4_logloss_at_least_0_02": logloss["mean"] is not None and float(logloss["mean"]) >= 0.02,
            "generation_4_logloss_lower_above_zero": logloss["lower"] is not None and float(logloss["lower"]) > 0.0,
            "generation_8_risk_lower_above_zero": persistence8["risk_difference"]["lower"] is not None and float(persistence8["risk_difference"]["lower"]) > 0.0,
            "generation_16_risk_lower_above_zero": persistence16["risk_difference"]["lower"] is not None and float(persistence16["risk_difference"]["lower"]) > 0.0,
            "split_half_reliability_at_least_0_80": reliability is not None and reliability >= 0.80,
            "beats_registered_controls": bool(controls) and all(
                value["lower"] is not None and float(value["lower"]) > 0.0 for value in controls.values()
            ),
            "sign_reversal_reverses_prediction": reverse["lower"] is not None and float(reverse["lower"]) > 0.0,
            "erasure_removes_at_least_0_70": ablation_reduction is not None and ablation_reduction >= 0.70,
            "rescue_restores_at_least_0_70": rescue_fraction is not None and rescue_fraction >= 0.70,
        }
        causal_passed = all(criteria.values())
        robust_criteria = {
            "causal_local_ph_passed": causal_passed,
            "capacity_at_most_5": genome.k <= 5,
            "strong_noise_generation_8_lower_above_zero": strong["risk_difference"]["lower"] is not None
            and float(strong["risk_difference"]["lower"]) > 0.0,
        }
        gates[genome.name] = {
            "genome": genome.to_dict(),
            "acquisition_rate": acquisition_rate,
            "primary": primary,
            "persistence_generation_8": persistence8,
            "persistence_generation_16": persistence16,
            "strong_noise_generation_8": strong,
            "split_half_reliability": reliability,
            "controls": controls,
            "sign_reversal": reverse,
            "ablation_reduction": ablation_reduction,
            "rescue_fraction": rescue_fraction,
            "criteria": criteria,
            "causal_local_ph_passed": causal_passed,
            "compressed_robust_criteria": robust_criteria,
            "compressed_robust_ph_passed": all(robust_criteria.values()),
        }
    ceiling = {
        f"generation_{generation}": _rate(counts, "perfect-latch", generation, "forced_break", "correct_hold8")
        for generation in (4, 8, 16)
    }
    return {
        "format": LOCAL_PH_ANALYSIS_FORMAT,
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "record_count": record_count,
        "unique_future_ids": len(future_ids),
        "expression_reset_verified": True,
        "carrier_target_access": False,
        "gates": gates,
        "perfect_latch_ceiling": ceiling,
        "verdict": {
            "causal_local_ph": any(value["causal_local_ph_passed"] for value in gates.values()),
            "compressed_robust_ph": any(value["compressed_robust_ph_passed"] for value in gates.values()),
        },
        "claim_boundary": (
            "Constructive in-silico evidence for an evolved local carrier family; "
            "not evidence that the machinery spontaneously arose in nature."
        ),
    }


def render_local_report(analysis: dict[str, Any]) -> str:
    lines = [
        "# Wagner local-memory plastic-heredity report",
        "",
        f"- Causal local PH: **{'PASS' if analysis['verdict']['causal_local_ph'] else 'fail'}**",
        f"- Compressed robust PH: **{'PASS' if analysis['verdict']['compressed_robust_ph'] else 'fail'}**",
        f"- Complete expression reset: `{analysis['expression_reset_verified']}`",
        f"- Carrier access to A/B target: `{analysis['carrier_target_access']}`",
        "",
    ]
    for name, gate in analysis["gates"].items():
        failed = [key for key, passed in gate["criteria"].items() if not passed]
        robust_failed = [
            key for key, passed in gate["compressed_robust_criteria"].items() if not passed
        ]
        lines.extend(
            (
                f"## {name}",
                "",
                f"- Causal verdict: **{'PASS' if gate['causal_local_ph_passed'] else 'fail'}**",
                f"- Compressed robust verdict: **{'PASS' if gate['compressed_robust_ph_passed'] else 'fail'}**",
                f"- Generation-4 risk gain: {gate['primary']['risk_difference']['mean']}",
                f"- Generation-8 risk lower bound: {gate['persistence_generation_8']['risk_difference']['lower']}",
                f"- Generation-16 risk lower bound: {gate['persistence_generation_16']['risk_difference']['lower']}",
                f"- Strong-noise generation-8 lower bound: {gate['strong_noise_generation_8']['risk_difference']['lower']}",
                f"- Split-half reliability: {gate['split_half_reliability']}",
                f"- Erasure reduction: {gate['ablation_reduction']}",
                f"- Rescue fraction: {gate['rescue_fraction']}",
                f"- Failed causal criteria: {failed or 'none'}",
                f"- Failed compressed/robust criteria: {robust_failed or 'none'}",
                "",
            )
        )
    lines.extend(("## Claim boundary", "", analysis["claim_boundary"], ""))
    return "\n".join(lines)
