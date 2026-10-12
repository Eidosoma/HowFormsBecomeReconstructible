"""Bounded descriptive analysis for Experiment 1."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .artifacts import append_jsonl, read_jsonl, write_json
from .upstream import load_memory


def _rate_interval(
    rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool], replicates: int
) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "memory_rate": None, "network_balanced_rate": None, "ci95": None}
    memory_rate = float(np.mean([predicate(row) for row in rows]))
    by_model: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_model[int(row["model_id"])].append(row)
    model_ids = sorted(by_model)
    model_rates = np.asarray(
        [np.mean([predicate(row) for row in by_model[model]]) for model in model_ids],
        dtype=float,
    )
    balanced = float(np.mean(model_rates))
    rng = np.random.Generator(np.random.Philox(20260824))
    boot = np.empty(replicates, dtype=float)
    for index in range(replicates):
        draw = rng.integers(0, len(model_rates), size=len(model_rates))
        boot[index] = float(np.mean(model_rates[draw]))
    return {
        "n": len(rows),
        "model_count": len(model_ids),
        "memory_rate": memory_rate,
        "network_balanced_rate": balanced,
        "ci95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
    }


def _format_rate(summary: dict[str, Any]) -> str:
    if summary.get("memory_rate") is None:
        return "n/a"
    return (
        f"{100 * summary['memory_rate']:.1f}% of {summary['n']} memories; "
        f"network-balanced {100 * summary['network_balanced_rate']:.1f}% "
        f"(exploratory 95% interval {100 * summary['ci95'][0]:.1f}–"
        f"{100 * summary['ci95'][1]:.1f}%)"
    )


def analyze(output: Path) -> dict[str, Any]:
    output = output.resolve()
    registration_path = output / "registration.json"
    source_gate_path = output / "source-gate.json"
    state_path = output / "state.json"
    registration = (
        json.loads(registration_path.read_text(encoding="utf-8"))
        if registration_path.is_file()
        else {}
    )
    source_gate = (
        json.loads(source_gate_path.read_text(encoding="utf-8"))
        if source_gate_path.is_file()
        else {"pass": False}
    )
    state = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if state_path.is_file()
        else {"status": "unknown"}
    )
    correction = list(read_jsonl(output / "independent-correction.jsonl"))
    washout = list(read_jsonl(output / "washout.jsonl"))
    replicates = int(registration.get("protocol", {}).get("bootstrap_replicates", 10000))

    released_positive_rows = [row for row in correction if row["released_is_broken"]]
    reproduced = _rate_interval(
        released_positive_rows,
        lambda row: bool(row["valid"] and row["is_broken"]),
        replicates,
    )
    released_positive_memories = sorted(
        {row["memory_task_id"] for row in released_positive_rows}
    )
    reproduced_memories = sorted(
        {
            row["memory_task_id"]
            for row in released_positive_rows
            if row["valid"] and row["is_broken"]
        }
    )

    cohort_lookup = {
        item["task_id"]: item for item in registration.get("cohort", [])
    }
    memory_bounds: dict[str, np.ndarray] = {}
    for task_id, item in cohort_lookup.items():
        try:
            memory_bounds[task_id] = load_memory(Path(item["memory_path"])).bounds
        except Exception:
            continue

    grouped: dict[tuple[str, float], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in washout:
        grouped[(row["memory_task_id"], float(row["washout_duration"]))][row["arm"]] = row
    classifications: list[dict[str, Any]] = []
    for (task_id, duration), arms in sorted(grouped.items()):
        required = {"naive", "trained_no_reset", "cs_sham", "control_only", "combined_reset"}
        if not required.issubset(arms):
            continue
        combined = arms["combined_reset"]
        no_reset = arms["trained_no_reset"]
        sham = arms["cs_sham"]
        control = arms["control_only"]
        valid = all(bool(arms[name]["valid"]) for name in required)
        specific = bool(
            valid
            and combined["challenge_is_broken"]
            and not no_reset["challenge_is_broken"]
            and not sham["challenge_is_broken"]
        )
        masking = bool(
            valid
            and combined["reset_is_broken"]
            and not combined["challenge_is_broken"]
        )
        record: dict[str, Any] = {
            "task_id": f"classification|{task_id}|{duration:g}",
            "memory_task_id": task_id,
            "model_id": combined["model_id"],
            "washout_duration": duration,
            "valid": valid,
            "combined_durable_reset": bool(valid and combined["challenge_is_broken"]),
            "specific_durable_reset": specific,
            "control_only_sufficient": bool(valid and control["challenge_is_broken"]),
            "spontaneous_decay": bool(valid and no_reset["challenge_is_broken"]),
            "masking_or_recovery": masking,
        }
        bounds = memory_bounds.get(task_id)
        if bounds is not None and valid:
            scale = np.maximum(np.abs(bounds[:, 1] - bounds[:, 0]), 1e-8)
            naive = np.asarray(arms["naive"]["challenge_phase"]["terminal_y"], dtype=float)
            trained = np.asarray(
                arms["trained_no_reset"]["challenge_phase"]["terminal_y"], dtype=float
            )
            candidate = np.asarray(
                combined["challenge_phase"]["terminal_y"], dtype=float
            )
            d_nt = float(np.sqrt(np.mean(((naive - trained) / scale) ** 2)))
            d_naive = float(np.sqrt(np.mean(((candidate - naive) / scale) ** 2)))
            d_trained = float(np.sqrt(np.mean(((candidate - trained) / scale) ** 2)))
            record.update(
                {
                    "distance_naive": d_naive,
                    "distance_trained": d_trained,
                    "naive_trained_distance": d_nt,
                    "nearest_reference": "naive" if d_naive < d_trained else "trained",
                    "off_reference_candidate": bool(
                        combined["challenge_is_broken"]
                        and d_naive > d_nt
                        and d_trained > d_nt
                    ),
                }
            )
        classifications.append(record)

    classification_path = output / "classifications.jsonl"
    if classification_path.exists():
        classification_path.unlink()
    append_jsonl(classification_path, classifications)

    duration_summaries: dict[str, Any] = {}
    for duration in sorted({row["washout_duration"] for row in classifications}):
        rows = [row for row in classifications if row["washout_duration"] == duration]
        valid_rows = [row for row in rows if row["valid"]]
        duration_summaries[str(duration)] = {
            name: _rate_interval(valid_rows, lambda row, n=name: bool(row[n]), replicates)
            for name in (
                "combined_durable_reset",
                "specific_durable_reset",
                "control_only_sufficient",
                "spontaneous_decay",
                "masking_or_recovery",
            )
        }

    long_specific = [
        row
        for row in classifications
        if row["washout_duration"] == 2500.0 and row["specific_durable_reset"]
    ]
    long_models = {row["model_id"] for row in long_specific}
    medium_rows = [
        row for row in classifications if row["washout_duration"] == 500.0 and row["valid"]
    ]
    returned_medium = [row for row in medium_rows if row["masking_or_recovery"]]
    sequence_change = (
        1.0 - len(reproduced_memories) / len(released_positive_memories)
        if released_positive_memories
        else None
    )
    invalid_conditions = [row for row in washout if not bool(row["valid"])]
    invalid_cells = [row for row in classifications if not bool(row["valid"])]
    invalid_by_arm = {
        arm: sum(row["arm"] == arm for row in invalid_conditions)
        for arm in sorted({row["arm"] for row in invalid_conditions})
    }
    invalid_by_duration = {
        str(duration): sum(
            float(row["washout_duration"]) == duration for row in invalid_conditions
        )
        for duration in sorted(
            {float(row["washout_duration"]) for row in invalid_conditions}
        )
    }
    invalid_by_model = {
        str(model_id): sum(
            int(row["model_id"]) == model_id for row in invalid_conditions
        )
        for model_id in sorted({int(row["model_id"]) for row in invalid_conditions})
    }
    if len(long_specific) >= 8 and len(long_models) >= 3:
        recommendation = "advance-to-observer-ladder"
    elif (
        medium_rows
        and len(returned_medium) / len(medium_rows) >= 0.80
        and len(long_models) < 3
    ):
        recommendation = "prioritize-masking-dynamics"
    elif sequence_change is not None and sequence_change > 0.10:
        recommendation = "prioritize-baseline-audit"
    else:
        recommendation = "retain-mixed-exploratory-result"

    result = {
        "run_status": state.get("status"),
        "source_gate": source_gate,
        "cohort_size": registration.get("cohort_size"),
        "released_positive_action_reproduction": reproduced,
        "released_positive_memory_count": len(released_positive_memories),
        "independently_reproduced_memory_count": len(reproduced_memories),
        "memory_verdict_change_fraction": sequence_change,
        "washout_condition_count": len(washout),
        "valid_washout_condition_count": len(washout) - len(invalid_conditions),
        "invalid_washout_condition_count": len(invalid_conditions),
        "invalid_washout_by_arm": invalid_by_arm,
        "invalid_washout_by_duration": invalid_by_duration,
        "invalid_washout_by_model": invalid_by_model,
        "complete_classification_count": len(classifications),
        "valid_classification_count": len(classifications) - len(invalid_cells),
        "invalid_classification_count": len(invalid_cells),
        "duration_summaries": duration_summaries,
        "long_specific_count": len(long_specific),
        "long_specific_model_count": len(long_models),
        "heuristic_recommendation": recommendation,
        "claim_boundary": (
            "Exploratory operational-reset evidence only; no true-erasure, "
            "plastic-heredity, biological-safety, agency, or clinical claim."
        ),
    }
    write_json(output / "analysis.json", result)

    experiment_id = registration.get("experiment_id", "grn-reset-washout")
    lines = [
        f"# {experiment_id} report",
        "",
        f"**Run status:** `{result['run_status']}`  ",
        f"**Source-faithful gate:** `{'PASS' if source_gate.get('pass') else 'FAIL'}`  ",
        f"**Heuristic next step:** `{recommendation}`",
        "",
        "## Baseline audit",
        "",
        f"Released-positive action reproduction under independent starts: {_format_rate(reproduced)}.",
        f"At memory level, {len(reproduced_memories)} of {len(released_positive_memories)} selected released-positive memories retained at least one independently successful action.",
        "",
        "## Numerical validity",
        "",
        f"{len(invalid_conditions)} of {len(washout)} completed assay conditions were numerically invalid; {len(invalid_cells)} complete five-arm cells contained at least one invalid condition.",
        "Non-finite values were recorded as JSON nulls without imputation or reruns. Any affected five-arm cell was excluded from rate denominators.",
        "",
        "## Washout and re-challenge",
        "",
    ]
    if not duration_summaries:
        lines.append("No complete five-arm washout cells were available for classification.")
    else:
        for duration, summaries in duration_summaries.items():
            lines.extend(
                [
                    f"### Washout {duration}",
                    "",
                    f"- Combined-arm durable operational reset: {_format_rate(summaries['combined_durable_reset'])}.",
                    f"- Control-specific durable reset: {_format_rate(summaries['specific_durable_reset'])}.",
                    f"- Control-only sufficiency: {_format_rate(summaries['control_only_sufficient'])}.",
                    f"- Spontaneous decay without reset: {_format_rate(summaries['spontaneous_decay'])}.",
                    f"- Masking or recovery after an operational reset: {_format_rate(summaries['masking_or_recovery'])}.",
                    "",
                ]
            )
    lines.extend(
        [
            "## Claim boundary",
            "",
            result["claim_boundary"],
            "The full-state distances are descriptive nearest-reference diagnostics, not proof of reversion, erasure, or rehoming.",
            "",
        ]
    )
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return result
