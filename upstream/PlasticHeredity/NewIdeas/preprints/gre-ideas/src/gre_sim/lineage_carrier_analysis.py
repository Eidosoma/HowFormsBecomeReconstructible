"""Source-level inference and frozen gates for lineage-carrier studies."""

from __future__ import annotations

import collections
from pathlib import Path
from typing import Any

from .artifacts import read_jsonl_gz
from .lineage_carrier_config import LINEAGE_ANALYSIS_FORMAT, LineageStudySpec
from .plastic_memory_analysis import (
    _bootstrap,
    _cell,
    _outcome_key,
    _reliability,
    _source_metric_values,
)


def _contrast(
    source_rates: dict[tuple[Any, str, str], list[float]],
    outcomes: dict[Any, collections.Counter[str]],
    spec: LineageStudySpec,
    model: str,
    mark: str,
    left: str,
    right: str,
    generation: int,
    challenge: str,
    label: str,
    simultaneous: int,
) -> dict[str, Any]:
    raw = _source_metric_values(
        source_rates,
        outcomes,
        model,
        mark,
        left,
        right,
        generation,
        challenge,
    )
    return {
        name: _bootstrap(
            values,
            spec,
            f"lineage-carrier.{label}.{name}",
            simultaneous,
        )
        for name, values in raw.items()
        if name != "sources"
    }


def _source_field_differences(
    source_rates: dict[tuple[Any, str, str], list[float]],
    model: str,
    mark: str,
    left: str,
    right: str,
    generation: int,
    challenge: str,
    field: str,
) -> list[float]:
    sources = sorted(
        {
            source
            for (cell, source, candidate_field) in source_rates
            if candidate_field == field
            and cell[1] == model
            and cell[4] == mark
            and cell[5] in {left, right}
            and cell[6] == generation
            and cell[7] == challenge
        }
    )
    result: list[float] = []
    for source in sources:
        rates: dict[str, list[float]] = {}
        for arm in (left, right):
            matched = [
                value
                for (cell, source_id, candidate_field), value in source_rates.items()
                if source_id == source
                and candidate_field == field
                and cell[1] == model
                and cell[4] == mark
                and cell[5] == arm
                and cell[6] == generation
                and cell[7] == challenge
            ]
            rates[arm] = [sum(value[0] for value in matched), sum(value[1] for value in matched)]
        if all(rates[arm][1] for arm in (left, right)):
            result.append(
                rates[left][0] / rates[left][1] - rates[right][0] / rates[right][1]
            )
    return result


def _field_contrast(
    source_rates: dict[tuple[Any, str, str], list[float]],
    spec: LineageStudySpec,
    model: str,
    mark: str,
    left: str,
    right: str,
    generation: int,
    challenge: str,
    field: str,
    label: str,
    simultaneous: int,
) -> dict[str, Any]:
    return _bootstrap(
        _source_field_differences(
            source_rates,
            model,
            mark,
            left,
            right,
            generation,
            challenge,
            field,
        ),
        spec,
        f"lineage-carrier.{label}.{field}",
        simultaneous,
    )


def _rate(
    source_rates: dict[tuple[Any, str, str], list[float]],
    model: str,
    mark: str,
    arm: str,
    generation: int,
    challenge: str,
    field: str = "correct_hold8",
) -> float | None:
    matched = [
        value
        for (cell, _source, candidate_field), value in source_rates.items()
        if candidate_field == field
        and cell[1] == model
        and cell[4] == mark
        and cell[5] == arm
        and cell[6] == generation
        and cell[7] == challenge
    ]
    total = sum(value[1] for value in matched)
    return sum(value[0] for value in matched) / total if total else None


def _arm_by_kind(spec: LineageStudySpec, bottleneck: str, k: int = 0) -> str | None:
    matches = [
        value.name
        for value in spec.arms
        if value.bottleneck == bottleneck and (k == 0 or value.k == k)
    ]
    return sorted(matches)[0] if matches else None


def _control_names(spec: LineageStudySpec, arm_name: str) -> tuple[str, ...]:
    arm = next(value for value in spec.arms if value.name == arm_name)
    names: list[str] = []
    if arm.bottleneck == "targeted":
        random_name = _arm_by_kind(spec, "random", arm.k)
        # At k == genes, both arms retain every entry. Their ordering is
        # immaterial, so demanding strict superiority is impossible by design.
        if random_name is not None and arm.k < spec.genes:
            names.append(random_name)
    for name in ("pattern-shuffle", "write-disabled", "read-disabled", "zero"):
        if any(value.name == name for value in spec.arms):
            names.append(name)
    return tuple(names)


def _inapplicable_controls(
    spec: LineageStudySpec, arm_name: str
) -> dict[str, str]:
    arm = next(value for value in spec.arms if value.name == arm_name)
    if arm.bottleneck != "targeted" or arm.k != spec.genes:
        return {}
    random_name = _arm_by_kind(spec, "random", arm.k)
    if random_name is None:
        return {}
    return {
        random_name: (
            f"not a superiority control: targeted k={arm.k} and random k={arm.k} "
            f"both retain all {spec.genes} carrier entries and are structurally identical"
        )
    }


def _lineage_gate(
    source_rates: dict[tuple[Any, str, str], list[float]],
    outcomes: dict[Any, collections.Counter[str]],
    spec: LineageStudySpec,
    engine: str,
    candidate: str,
    recipient_mode: str,
    arm_name: str,
    simultaneous: int,
) -> dict[str, Any]:
    model = f"{engine}.{candidate}.{recipient_mode}"
    mark = candidate
    arm = next(value for value in spec.arms if value.name == arm_name)
    primary_generation = 4 if 4 in spec.checkpoint_generations else max(spec.checkpoint_generations)
    persistence_generation = 8 if 8 in spec.checkpoint_generations else primary_generation
    challenge = "forced_break" if "forced_break" in spec.challenges else spec.challenges[0]
    baseline = "zero" if any(value.name == "zero" for value in spec.arms) else spec.arms[-1].name
    primary = _contrast(
        source_rates,
        outcomes,
        spec,
        model,
        mark,
        arm_name,
        baseline,
        primary_generation,
        challenge,
        f"{model}.{arm_name}.primary",
        simultaneous,
    )
    persistence = _contrast(
        source_rates,
        outcomes,
        spec,
        model,
        mark,
        arm_name,
        baseline,
        persistence_generation,
        challenge,
        f"{model}.{arm_name}.persistence",
        simultaneous,
    )
    controls = {
        control: _contrast(
            source_rates,
            outcomes,
            spec,
            model,
            mark,
            arm_name,
            control,
            primary_generation,
            challenge,
            f"{model}.{arm_name}.control.{control}",
            simultaneous,
        )
        for control in _control_names(spec, arm_name)
    }
    inapplicable_controls = _inapplicable_controls(spec, arm_name)
    reliability = _reliability(
        source_rates, model, mark, arm_name, primary_generation, challenge
    )
    full_name = "natural-full" if any(value.name == "natural-full" for value in spec.arms) else arm_name
    full = _contrast(
        source_rates,
        outcomes,
        spec,
        model,
        mark,
        full_name,
        baseline,
        primary_generation,
        challenge,
        f"{model}.full-reference",
        simultaneous,
    )
    primary_risk = primary["risk_difference"]["mean"]
    full_risk = full["risk_difference"]["mean"]
    retention = (
        float(primary_risk) / float(full_risk)
        if primary_risk is not None and full_risk is not None and float(full_risk) > 0.0
        else None
    )
    opposite_flip = None
    if any(value.name == "opposite-history" for value in spec.arms):
        opposite_flip = _field_contrast(
            source_rates,
            spec,
            model,
            mark,
            "opposite-history",
            baseline,
            primary_generation,
            challenge,
            "wrong_hold8",
            f"{model}.opposite-flip",
            simultaneous,
        )
    ablation_reference = arm_name
    if spec.exploratory and any(value.name == "natural-full" for value in spec.arms):
        ablation_reference = "natural-full"
    ablation = rescue = None
    ablation_reduction = rescue_fraction = None
    if any(value.name == "ablate-generation-2" for value in spec.arms):
        ablation = _contrast(
            source_rates,
            outcomes,
            spec,
            model,
            mark,
            ablation_reference,
            "ablate-generation-2",
            primary_generation,
            challenge,
            f"{model}.ablation",
            simultaneous,
        )
        reference_rate = _rate(
            source_rates, model, mark, ablation_reference, primary_generation, challenge
        )
        ablated_rate = _rate(
            source_rates, model, mark, "ablate-generation-2", primary_generation, challenge
        )
        zero_rate = _rate(source_rates, model, mark, baseline, primary_generation, challenge)
        if (
            reference_rate is not None
            and ablated_rate is not None
            and zero_rate is not None
            and reference_rate > zero_rate
        ):
            ablation_reduction = (reference_rate - ablated_rate) / (
                reference_rate - zero_rate
            )
    if any(value.name == "ablate-2-rescue-3" for value in spec.arms):
        rescue = _contrast(
            source_rates,
            outcomes,
            spec,
            model,
            mark,
            "ablate-2-rescue-3",
            "ablate-generation-2",
            primary_generation,
            challenge,
            f"{model}.rescue",
            simultaneous,
        )
        rescued_rate = _rate(
            source_rates, model, mark, "ablate-2-rescue-3", primary_generation, challenge
        )
        ablated_rate = _rate(
            source_rates, model, mark, "ablate-generation-2", primary_generation, challenge
        )
        reference_rate = _rate(
            source_rates, model, mark, ablation_reference, primary_generation, challenge
        )
        if (
            rescued_rate is not None
            and ablated_rate is not None
            and reference_rate is not None
            and reference_rate > ablated_rate
        ):
            rescue_fraction = (rescued_rate - ablated_rate) / (
                reference_rate - ablated_rate
            )
    risk = primary["risk_difference"]
    crossover = primary["crossover"]
    logloss = primary["log_loss_gain"]
    persistence_risk = persistence["risk_difference"]
    persistence_crossover = persistence["crossover"]
    strict_phase = 4 in spec.checkpoint_generations
    criteria = {
        "generation_4_risk_at_least_0_05": not strict_phase
        or (risk["mean"] is not None and float(risk["mean"]) >= 0.05),
        "generation_4_risk_lower_above_zero": not strict_phase
        or (risk["lower"] is not None and float(risk["lower"]) > 0.0),
        "generation_4_crossover_at_least_0_05": not strict_phase
        or (crossover["mean"] is not None and float(crossover["mean"]) >= 0.05),
        "generation_4_crossover_lower_above_zero": not strict_phase
        or (crossover["lower"] is not None and float(crossover["lower"]) > 0.0),
        "generation_4_logloss_at_least_0_02": not strict_phase
        or (logloss["mean"] is not None and float(logloss["mean"]) >= 0.02),
        "generation_4_logloss_lower_above_zero": not strict_phase
        or (logloss["lower"] is not None and float(logloss["lower"]) > 0.0),
        "generation_8_risk_lower_above_zero": 8 not in spec.checkpoint_generations
        or (
            persistence_risk["lower"] is not None
            and float(persistence_risk["lower"]) > 0.0
        ),
        "generation_8_crossover_lower_above_zero": 8 not in spec.checkpoint_generations
        or (
            persistence_crossover["lower"] is not None
            and float(persistence_crossover["lower"]) > 0.0
        ),
        "split_half_reliability_at_least_0_80": reliability is not None
        and reliability >= 0.80,
        "minimal_retains_at_least_0_70_of_full": arm.bottleneck != "targeted"
        or (retention is not None and retention >= 0.70),
        "beats_registered_controls": not strict_phase
        or (
            bool(controls)
            and all(
                value["risk_difference"]["lower"] is not None
                and float(value["risk_difference"]["lower"]) > 0.0
                for value in controls.values()
            )
        ),
        "opposite_history_reverses_prediction": not strict_phase
        or (
            opposite_flip is not None
            and opposite_flip["lower"] is not None
            and float(opposite_flip["lower"]) > 0.0
        ),
        "ablation_removes_at_least_0_70": not strict_phase
        or (ablation_reduction is not None and ablation_reduction >= 0.70),
        "rescue_restores_at_least_0_70": not strict_phase
        or (rescue_fraction is not None and rescue_fraction >= 0.70),
    }
    calibration_passed = (
        risk["mean"] is not None
        and float(risk["mean"]) >= 0.02
        and crossover["mean"] is not None
        and float(crossover["mean"]) > 0.0
    )
    return {
        "engine": engine,
        "candidate": candidate,
        "recipient_mode": recipient_mode,
        "arm": arm_name,
        "bottleneck": arm.bottleneck,
        "k": arm.k if arm.bottleneck == "targeted" else (spec.genes if arm_name == "natural-full" else arm.k),
        "primary_generation": primary_generation,
        "persistence_generation": persistence_generation,
        "primary": primary,
        "persistence": persistence,
        "controls": controls,
        "inapplicable_controls": inapplicable_controls,
        "split_half_reliability": reliability,
        "retention_fraction": retention,
        "opposite_history_flip": opposite_flip,
        "ablation": ablation,
        "ablation_reduction": ablation_reduction,
        "rescue": rescue,
        "rescue_fraction": rescue_fraction,
        "criteria": criteria,
        "calibration_passed": calibration_passed,
        "passed": strict_phase and all(criteria.values()),
    }


def analyze_lineage_path(path: Path, spec: LineageStudySpec) -> dict[str, Any]:
    """Analyze source-paired lineage records without pooling engines."""

    spec.validate()
    source_rates: dict[tuple[Any, str, str], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    outcomes: dict[Any, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    future_ids: set[str] = set()
    models: dict[str, tuple[str, str, str]] = {}
    record_count = 0
    for record in read_jsonl_gz(path):
        record_count += 1
        future_id = str(record["future_id"])
        if future_id in future_ids:
            raise ValueError(f"duplicate lineage future: {future_id}")
        future_ids.add(future_id)
        cell = _cell(record)
        source = str(record["source_id"])
        for field in (
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
        models[str(record["model"])] = (
            str(record["engine"]),
            str(record["candidate"]),
            str(record["recipient_mode"]),
        )
    simultaneous = max(
        1,
        len(models)
        * len(spec.arms)
        * len(spec.checkpoint_generations)
        * len(spec.challenges)
        * 3,
    )
    comparisons: dict[str, Any] = {}
    baseline = "zero" if any(value.name == "zero" for value in spec.arms) else spec.arms[-1].name
    for model, (_engine, candidate, _recipient_mode) in sorted(models.items()):
        for arm in spec.arms:
            if arm.name == baseline:
                continue
            for generation in spec.checkpoint_generations:
                for challenge in spec.challenges:
                    label = f"{model}.{arm.name}.g{generation}.{challenge}"
                    comparisons[label] = _contrast(
                        source_rates,
                        outcomes,
                        spec,
                        model,
                        candidate,
                        arm.name,
                        baseline,
                        generation,
                        challenge,
                        label,
                        simultaneous,
                    )
    transfer_arms = [
        value.name
        for value in spec.arms
        if value.name == "natural-full" or value.bottleneck == "targeted"
    ]
    gates: dict[str, Any] = {}
    for model, (engine, candidate, recipient_mode) in sorted(models.items()):
        if recipient_mode != "clone":
            continue
        for arm_name in transfer_arms:
            gate = _lineage_gate(
                source_rates,
                outcomes,
                spec,
                engine,
                candidate,
                recipient_mode,
                arm_name,
                simultaneous,
            )
            gates[f"{model}.{arm_name}"] = gate
    rates: dict[str, Any] = {}
    for model, (_engine, candidate, _recipient_mode) in sorted(models.items()):
        for arm in spec.arms:
            for generation in spec.checkpoint_generations:
                for challenge in spec.challenges:
                    key = f"{model}.{arm.name}.g{generation}.{challenge}"
                    rates[key] = {
                        field: _rate(
                            source_rates,
                            model,
                            candidate,
                            arm.name,
                            generation,
                            challenge,
                            field,
                        )
                        for field in ("correct_hold8", "wrong_hold8", "returned")
                    }
    return {
        "format": LINEAGE_ANALYSIS_FORMAT,
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "exploratory": spec.exploratory,
        "record_count": record_count,
        "unique_future_ids": len(future_ids),
        "comparisons": comparisons,
        "lineage_gates": gates,
        "rates": rates,
        "thresholds": {
            "founder_acquisition": 0.80,
            "history_imbalance": 0.10,
            "generation_4_risk": 0.05,
            "generation_4_crossover": 0.05,
            "generation_4_log_loss_gain": 0.02,
            "split_half_reliability": 0.80,
            "minimal_retention": 0.70,
            "ablation_removal": 0.70,
            "rescue_restoration": 0.70,
        },
    }


def select_calibrated_carriers(
    analysis: dict[str, Any], maximum_wagner: int = 2, maximum_boolean: int = 1
) -> dict[str, Any]:
    """Select natural-written candidates; keep a labelled Boolean benchmark."""

    result: dict[str, Any] = {}
    for engine, maximum in (("wagner", maximum_wagner), ("boolean", maximum_boolean)):
        gates = [
            value
            for value in analysis["lineage_gates"].values()
            if value["engine"] == engine and value["arm"] == "natural-full"
        ]
        gates.sort(
            key=lambda value: (
                -float(value["primary"]["risk_difference"]["mean"] or -1e9),
                -float(value["primary"]["crossover"]["mean"] or -1e9),
                value["candidate"],
            )
        )
        passing = [value["candidate"] for value in gates if value["calibration_passed"]]
        result[engine] = tuple(passing[:maximum])
        result[f"{engine}_benchmark"] = gates[0]["candidate"] if gates else None
    return result


def select_discovery_candidate(analysis: dict[str, Any]) -> dict[str, Any] | None:
    """Freeze the smallest passing Wagner bottleneck, then persistence strength."""

    passing = [
        value
        for value in analysis["lineage_gates"].values()
        if value["engine"] == "wagner" and value["passed"]
    ]
    if not passing:
        return None
    passing.sort(
        key=lambda value: (
            int(value["k"]),
            -float(value["persistence"]["risk_difference"]["lower"] or -1e9),
            value["candidate"],
            value["arm"],
        )
    )
    selected = passing[0]
    return {
        "engine": "wagner",
        "candidate": selected["candidate"],
        "arm": selected["arm"],
        "k": int(selected["k"]),
        "generation_8_risk_lower": selected["persistence"]["risk_difference"]["lower"],
    }


def render_lineage_report(analysis: dict[str, Any]) -> str:
    lines = [
        f"# Wagner lineage carriers: {analysis['phase']}",
        "",
        "> Exploratory cohort." if analysis["exploratory"] else "> Untouched confirmation cohort.",
        "",
        f"- Checkpoint records: {analysis['record_count']:,}",
        f"- Unique future IDs: {analysis['unique_future_ids']:,}",
        "",
        "## Registered lineage gates",
        "",
    ]
    if not analysis["lineage_gates"]:
        lines.append("- No clone-recipient transfer arm was estimable.")
    for gate in analysis["lineage_gates"].values():
        failed = [name for name, passed in gate["criteria"].items() if not passed]
        lines.extend(
            (
                f"### {gate['engine']} / {gate['candidate']} / {gate['arm']}",
                "",
                f"- Verdict: **{'PASS' if gate['passed'] else 'fail'}**",
                f"- Generation-{gate['primary_generation']} risk gain: "
                f"{gate['primary']['risk_difference']['mean']}",
                f"- Generation-{gate['persistence_generation']} risk lower bound: "
                f"{gate['persistence']['risk_difference']['lower']}",
                f"- Failed criteria: {failed or 'none'}",
                f"- Inapplicable controls: {gate.get('inapplicable_controls') or 'none'}",
                "",
            )
        )
    lines.extend(
        (
            "## Interpretation boundary",
            "",
            "A passing confirmation establishes a naturally written carrier that crosses "
            "complete expression resets and remains history-specific across uncued GRN "
            "generations. It remains an in-silico mechanistic result, not a biological claim.",
            "",
        )
    )
    return "\n".join(lines)
