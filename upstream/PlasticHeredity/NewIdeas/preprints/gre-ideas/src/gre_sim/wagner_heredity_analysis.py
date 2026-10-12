"""Streaming, rulebook-level gates for the Wagner heredity ladder."""

from __future__ import annotations

import collections
from pathlib import Path
from typing import Any

from .artifacts import read_jsonl_gz
from .plastic_memory_analysis import (
    _bootstrap,
    _candidate_gate,
    _cell,
    _outcome_key,
    _source_metric_values,
)
from .wagner_heredity_config import (
    WAGNER_HEREDITY_ANALYSIS_FORMAT,
    WagnerHereditySpec,
)


def _history_rates(
    source_rates: dict[tuple[Any, str, str], list[float]],
    model: str,
    mark: str,
    carrier: str,
    age: int,
    challenge: str,
    history: str,
    field: str = "correct_hold8",
) -> list[float]:
    totals: dict[str, list[float]] = collections.defaultdict(lambda: [0.0, 0.0])
    for (cell, source, candidate_field), value in source_rates.items():
        if (
            candidate_field == field
            and cell[1] == model
            and cell[4] == mark
            and cell[5] == carrier
            and cell[6] == age
            and cell[7] == challenge
            and cell[8] == history
        ):
            totals[source][0] += value[0]
            totals[source][1] += value[1]
    return [value[0] / value[1] for value in totals.values() if value[1]]


def _contrast(
    spec: WagnerHereditySpec,
    memory_spec: Any,
    source_rates: dict[tuple[Any, str, str], list[float]],
    outcomes: dict[Any, collections.Counter[str]],
    model: str,
    mark: str,
    carrier: str,
    baseline: str,
    age: int,
    challenge: str,
    label: str,
    simultaneous: int,
) -> dict[str, Any]:
    raw = _source_metric_values(
        source_rates,
        outcomes,
        model,
        mark,
        carrier,
        baseline,
        age,
        challenge,
    )
    return {
        name: _bootstrap(
            values,
            memory_spec,
            f"wagner-heredity.{label}.{name}",
            simultaneous,
        )
        for name, values in raw.items()
        if name != "sources"
    }


def analyze_heredity_path(
    records_path: Path, spec: WagnerHereditySpec
) -> dict[str, Any]:
    """Analyze a compressed future stream without retaining individual records."""

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
    equivalence_pairs: dict[tuple[Any, ...], dict[str, str]] = {}
    control_matches: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    future_ids: set[str] = set()
    record_count = 0
    for record in read_jsonl_gz(records_path):
        record_count += 1
        future_id = str(record["future_id"])
        if future_id in future_ids:
            raise ValueError(f"duplicate Wagner heredity future: {future_id}")
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
            amount = source_rates[(cell, source, field)]
            amount[0] += float(record[field])
            amount[1] += 1.0
        half_amount = source_rates[
            (cell, source, f"correct_hold8.half-{record['half']}")
        ]
        half_amount[0] += float(record["correct_hold8"])
        half_amount[1] += 1.0
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
            values = acquisition[(record["model"], source, record["history"])]
            values[0] += float(record["acquired"])
            values[1] += 1.0
        if record["carrier"] in {
            "self_continuation",
            "state_transplant",
        } and record["mark_setting"] == "none":
            pair_key = (
                record["condition"],
                source,
                record["midpoint_index"],
                record["history"],
                record["washout_age"],
                record["challenge"],
                record["future_index"],
            )
            equivalence_pairs.setdefault(pair_key, {})[
                str(record["carrier"])
            ] = str(record["trace_digest"])
        if record["carrier"] in {
            "destination_matched_donor",
            "descriptor_matched_null",
            "state_pattern_shuffle",
        }:
            values = control_matches[str(record["carrier"])]
            values[0] += int(bool(record["descriptor_exact"]))
            values[1] += 1

    complete_pairs = [value for value in equivalence_pairs.values() if len(value) == 2]
    pair_matches = sum(
        value["self_continuation"] == value["state_transplant"]
        for value in complete_pairs
    )
    equivalence = {
        "pairs": len(complete_pairs),
        "matches": pair_matches,
        "equal": bool(complete_pairs) and pair_matches == len(complete_pairs),
    }
    primary = [writer for writer in spec.writers if writer.primary]
    active_marks = [mark for mark in spec.mark_settings if mark.active]
    simultaneous = max(1, 5 * (len(primary) + len(active_marks)))

    acquisition_summary: dict[str, Any] = {}
    for writer in spec.writers:
        histories: dict[str, Any] = {}
        for history in ("A", "B"):
            per_source = [
                value[0] / value[1]
                for (model, _source, candidate_history), value in acquisition.items()
                if model == writer.name
                and candidate_history == history
                and value[1]
            ]
            histories[history] = _bootstrap(
                per_source,
                memory_spec,
                f"wagner-heredity.acquisition.{writer.name}.{history}",
                simultaneous,
            )
        acquisition_summary[writer.name] = histories

    state_gates: dict[str, Any] = {}
    for writer in spec.writers:
        base_gate = _candidate_gate(
            memory_spec,
            source_rates,
            outcomes,
            writer.name,
            "none",
            "state_transplant",
            0,
            "neutral_damage",
            equivalence,
            simultaneous,
        )
        shuffle = _contrast(
            spec,
            memory_spec,
            source_rates,
            outcomes,
            writer.name,
            "none",
            "state_transplant",
            "state_pattern_shuffle",
            0,
            "neutral_damage",
            f"{writer.name}.shuffle",
            simultaneous,
        )
        age_one = _contrast(
            spec,
            memory_spec,
            source_rates,
            outcomes,
            writer.name,
            "none",
            "state_transplant",
            "reset_both",
            1,
            "release_only",
            f"{writer.name}.age-one",
            simultaneous,
        )
        absolute = {
            history: _bootstrap(
                _history_rates(
                    source_rates,
                    writer.name,
                    "none",
                    "state_transplant",
                    0,
                    "neutral_damage",
                    history,
                ),
                memory_spec,
                f"wagner-heredity.{writer.name}.absolute.{history}",
                simultaneous,
            )
            for history in ("A", "B")
        }
        ceiling_name = writer.ceiling_writer or writer.name
        candidate_mean = sum(
            float(absolute[history]["mean"] or 0.0) for history in ("A", "B")
        ) / 2.0
        ceiling_values = [
            value
            for history in ("A", "B")
            for value in _history_rates(
                source_rates,
                ceiling_name,
                "none",
                "state_transplant",
                0,
                "neutral_damage",
                history,
            )
        ]
        ceiling_mean = (
            sum(ceiling_values) / len(ceiling_values) if ceiling_values else None
        )
        ceiling_fraction = (
            candidate_mean / ceiling_mean
            if ceiling_mean is not None and ceiling_mean > 0.0
            else None
        )
        acquired = acquisition_summary[writer.name]
        acquisition_means = [acquired[history]["mean"] for history in ("A", "B")]
        criteria = {
            **base_gate["criteria"],
            "both_histories_acquisition_at_least_0_80": all(
                value is not None and float(value) >= 0.80
                for value in acquisition_means
            ),
            "history_acquisition_imbalance_at_most_0_10": all(
                value is not None for value in acquisition_means
            )
            and abs(float(acquisition_means[0]) - float(acquisition_means[1]))
            <= 0.10,
            "both_histories_absolute_hold8_at_least_0_20": all(
                absolute[history]["mean"] is not None
                and float(absolute[history]["mean"]) >= 0.20
                for history in ("A", "B")
            ),
            "retention_at_least_0_70_of_ceiling": ceiling_fraction is not None
            and ceiling_fraction >= 0.70,
            "state_beats_shuffle_lower_above_zero": bool(shuffle)
            and shuffle["risk_difference"]["lower"] is not None
            and float(shuffle["risk_difference"]["lower"]) > 0.0,
            "generation_one_risk_lower_above_zero": bool(age_one)
            and age_one["risk_difference"]["lower"] is not None
            and float(age_one["risk_difference"]["lower"]) > 0.0,
            "generation_one_crossover_lower_above_zero": bool(age_one)
            and age_one["crossover"]["lower"] is not None
            and float(age_one["crossover"]["lower"]) > 0.0,
        }
        state_gates[writer.name] = {
            "writer": writer.name,
            "tier": writer.tier,
            "primary": writer.primary,
            "gamma_variance": writer.gamma_variance,
            "intervention": {
                "mode": writer.intervention.mode,
                "fraction": writer.intervention.fraction,
                "dwell": writer.intervention.dwell,
                "field_strength": writer.intervention.field_strength,
            },
            "primary_transfer": base_gate,
            "shuffle_contrast": shuffle,
            "generation_one": age_one,
            "absolute_hold8": absolute,
            "ceiling_writer": ceiling_name,
            "ceiling_hold8": ceiling_mean,
            "ceiling_fraction": ceiling_fraction,
            "criteria": criteria,
            "passed": all(criteria.values()),
        }

    mark_gates: dict[str, dict[str, Any]] = {}
    for writer in primary:
        mark_gates[writer.name] = {}
        for mark in active_marks:
            primary_gate = _candidate_gate(
                memory_spec,
                source_rates,
                outcomes,
                writer.name,
                mark.name,
                "mark_transplant",
                0,
                "forced_break",
                equivalence,
                simultaneous,
            )
            controls = {
                baseline: _contrast(
                    spec,
                    memory_spec,
                    source_rates,
                    outcomes,
                    writer.name,
                    mark.name,
                    "mark_transplant",
                    baseline,
                    0,
                    "forced_break",
                    f"{writer.name}.{mark.name}.{baseline}",
                    simultaneous,
                )
                for baseline in (
                    "mark_pattern_shuffle",
                    "write_disabled",
                    "mark_inert",
                )
            }
            ablation = _contrast(
                spec,
                memory_spec,
                source_rates,
                outcomes,
                writer.name,
                mark.name,
                "mark_random_ablation",
                "mark_ablation",
                0,
                "forced_break",
                f"{writer.name}.{mark.name}.targeted-ablation",
                simultaneous,
            )
            rescue = _contrast(
                spec,
                memory_spec,
                source_rates,
                outcomes,
                writer.name,
                mark.name,
                "mark_rescue",
                "mark_ablation",
                0,
                "forced_break",
                f"{writer.name}.{mark.name}.rescue",
                simultaneous,
            )
            absolute = {
                history: _bootstrap(
                    _history_rates(
                        source_rates,
                        writer.name,
                        mark.name,
                        "mark_transplant",
                        0,
                        "forced_break",
                        history,
                    ),
                    memory_spec,
                    f"wagner-heredity.{writer.name}.{mark.name}.absolute.{history}",
                    simultaneous,
                )
                for history in ("A", "B")
            }
            criteria = {
                **{
                    name: value
                    for name, value in primary_gate["criteria"].items()
                    if name != "self_transplant_equivalence"
                },
                **{
                    f"beats_{baseline}_lower_above_zero": bool(value)
                    and value["risk_difference"]["lower"] is not None
                    and float(value["risk_difference"]["lower"]) > 0.0
                    for baseline, value in controls.items()
                },
                "targeted_ablation_exceeds_random_damage": bool(ablation)
                and ablation["risk_difference"]["lower"] is not None
                and float(ablation["risk_difference"]["lower"]) > 0.0,
                "mark_rescue_restores_over_targeted_ablation": bool(rescue)
                and rescue["risk_difference"]["lower"] is not None
                and float(rescue["risk_difference"]["lower"]) > 0.0,
                "both_histories_absolute_hold8_at_least_0_20": all(
                    absolute[history]["mean"] is not None
                    and float(absolute[history]["mean"]) >= 0.20
                    for history in ("A", "B")
                ),
            }
            mark_gates[writer.name][mark.name] = {
                "primary_transfer": primary_gate,
                "controls": controls,
                "ablation": ablation,
                "rescue": rescue,
                "absolute_hold8": absolute,
                "criteria": criteria,
                "passed": all(criteria.values()),
            }

    persistence: dict[str, Any] = {}
    for writer in spec.writers:
        for mark_name, carrier in (
            ("none", "state_transplant"),
            *((mark.name, "mark_transplant") for mark in active_marks),
        ):
            for age in (1, 2, 4, 8):
                for challenge in ("release_only", "neutral_damage", "forced_break"):
                    values = _contrast(
                        spec,
                        memory_spec,
                        source_rates,
                        outcomes,
                        writer.name,
                        mark_name,
                        carrier,
                        "reset_both",
                        age,
                        challenge,
                        f"persistence.{writer.name}.{mark_name}.{age}.{challenge}",
                        simultaneous,
                    )
                    if values["risk_difference"]["sources"]:
                        persistence[
                            f"{writer.name}.{mark_name}.{carrier}.age-{age}.{challenge}"
                        ] = values

    return {
        "format": WAGNER_HEREDITY_ANALYSIS_FORMAT,
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "exploratory": spec.exploratory,
        "record_count": record_count,
        "unique_future_ids": len(future_ids),
        "acquisition": acquisition_summary,
        "state_transfer_gates": state_gates,
        "mark_transfer_gates": mark_gates,
        "persistence": persistence,
        "self_transplant_equivalence": equivalence,
        "control_match_rates": {
            carrier: value[0] / value[1]
            for carrier, value in sorted(control_matches.items())
            if value[1]
        },
        "thresholds": {
            "acquisition": 0.80,
            "acquisition_imbalance": 0.10,
            "absolute_hold8": 0.20,
            "ceiling_fraction": 0.70,
            "risk_difference": 0.05,
            "crossover": 0.05,
            "log_loss_gain": 0.02,
            "split_half_reliability": 0.80,
            "interval_level": spec.interval_level,
            "simultaneous_primary_tests": simultaneous,
        },
    }


def passing_state_writers(analysis: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        name
        for name, gate in analysis["state_transfer_gates"].items()
        if gate["primary"] and gate["passed"]
    )


def select_mark_candidate(
    analysis: dict[str, Any], writer_name: str
) -> str | None:
    candidates = [
        (name, gate)
        for name, gate in analysis["mark_transfer_gates"].get(writer_name, {}).items()
        if gate["passed"]
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item[1]["primary_transfer"]["metrics"]["risk_difference"]["mean"],
            item[1]["primary_transfer"]["metrics"]["log_loss_gain"]["mean"],
            item[0],
        ),
    )[0]
