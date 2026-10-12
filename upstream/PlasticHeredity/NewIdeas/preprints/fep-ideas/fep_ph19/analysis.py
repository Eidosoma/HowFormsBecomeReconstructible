from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np

from fep_lab.integrity import read_json, seal_directory, write_json
from fep_lab.seeds import derive_seed
from fep_ph15.endpoints import episode_metrics

from .config import ExperimentConfig, SWITCH_PROBABILITIES
from .types import ControllerName, InformationArm, SensingTiming


PRIMARY = "inherited_completion_fraction"


def _finite_mean(values: list[float]) -> float | None:
    array = np.asarray(values, dtype=np.float64)
    array = array[np.isfinite(array)]
    return float(array.mean()) if array.size else None


def _episode_values(episode: dict[str, np.ndarray], horizon: int) -> dict[str, float]:
    output = episode_metrics(episode, horizon)
    output[PRIMARY] = output["inherited_fixed_fraction"]
    valid = np.asarray(episode["decision_regime"], dtype=np.int64) >= 0
    beliefs = np.asarray(episode["pre_action_belief"], dtype=np.float64)
    regimes = np.asarray(episode["decision_regime"], dtype=np.int64)
    belief_valid = valid & np.all(np.isfinite(beliefs), axis=1)
    output["posterior_accuracy"] = (
        float(np.mean(beliefs[np.flatnonzero(belief_valid), regimes[belief_valid]]))
        if np.any(belief_valid)
        else float("nan")
    )
    correct = np.asarray(episode["correct_regime_action"], dtype=np.float64)
    output["adaptation_precision"] = (
        float(np.mean(correct[np.isfinite(correct)]))
        if np.any(np.isfinite(correct))
        else float("nan")
    )
    adapted = np.asarray(episode["adapted"], dtype=np.float64)
    opportunities = np.asarray(episode["adaptation_opportunity"], dtype=bool) & valid
    output["adaptation_coverage"] = (
        float(np.mean(adapted[opportunities])) if np.any(opportunities) else float("nan")
    )
    sampled = np.asarray(episode["sampled"], dtype=np.float64)
    output["live_sensing_fraction"] = (
        float(np.mean(sampled[valid])) if np.any(valid) else float("nan")
    )
    output["sample_fraction"] = float(np.mean(sampled))
    output["contingent_fraction"] = (
        float(np.mean(np.asarray(episode["policy_contingency"])[valid]))
        if np.any(valid)
        else float("nan")
    )
    return output


def load_rows(simulation: Path, config: ExperimentConfig) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((simulation / "cells").glob("*.npz")):
        manifest = read_json(path.with_suffix(".json"))
        with np.load(path, allow_pickle=False) as archive:
            arrays = {name: archive[name].copy() for name in archive.files}
        controllers = [str(value) for value in arrays["controller_names"]]
        excluded = {
            "controller_names",
            "matrix_id",
            "growth_budget",
            "authority_scale",
            "switch_probability",
        }
        for controller_index, controller in enumerate(controllers):
            branches = []
            for branch in range(config.branches):
                episode = {
                    name: value[controller_index, branch]
                    for name, value in arrays.items()
                    if name not in excluded
                }
                branches.append(_episode_values(episode, config.horizon))
            row: dict[str, Any] = {
                "stage": manifest["stage"],
                "matrix_id": int(manifest["matrix_id"]),
                "candidate": str(manifest["candidate"]),
                "switch_probability": float(manifest["switch_probability"]),
                "sensing_timing": str(manifest["sensing_timing"]),
                "information_arm": str(manifest["information_arm"]),
                "controller": controller,
            }
            for key in set().union(*(value.keys() for value in branches)):
                row[key] = _finite_mean(
                    [value.get(key, float("nan")) for value in branches]
                )
            rows.append(row)
    return rows


def _bootstrap(
    values: list[float],
    repetitions: int,
    rng: np.random.Generator,
    *,
    interval: float = 0.95,
) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    array = array[np.isfinite(array)]
    if not len(array):
        return {
            "estimate": None,
            "lower": None,
            "upper": None,
            "interval": interval,
            "n_matrices": 0,
        }
    draws = array[
        rng.integers(0, len(array), size=(repetitions, len(array)))
    ].mean(axis=1)
    tail = (1.0 - interval) / 2.0
    return {
        "estimate": float(array.mean()),
        "lower": float(np.quantile(draws, tail)),
        "upper": float(np.quantile(draws, 1.0 - tail)),
        "interval": interval,
        "n_matrices": int(len(array)),
    }


def _paired_values(
    rows: list[dict[str, Any]],
    left: str,
    right: str,
    outcome: str,
    predicate: Callable[[dict[str, Any]], bool],
) -> list[float]:
    selected = [row for row in rows if predicate(row)]
    keys = (
        "matrix_id",
        "candidate",
        "switch_probability",
        "sensing_timing",
        "information_arm",
    )
    index = {
        tuple(row[key] for key in keys) + (row["controller"],): row
        for row in selected
    }
    by_matrix: dict[int, list[float]] = defaultdict(list)
    for key in sorted({tuple(row[name] for name in keys) for row in selected}):
        left_row = index.get(key + (left,))
        right_row = index.get(key + (right,))
        if left_row is None or right_row is None:
            continue
        left_value, right_value = left_row.get(outcome), right_row.get(outcome)
        if left_value is None or right_value is None:
            continue
        difference = float(left_value) - float(right_value)
        if np.isfinite(difference):
            by_matrix[int(key[0])].append(difference)
    return [float(np.mean(values)) for _, values in sorted(by_matrix.items()) if values]


def _contrast(
    rows: list[dict[str, Any]],
    config: ExperimentConfig,
    rng: np.random.Generator,
    label: str,
    left: ControllerName,
    right: ControllerName,
    outcome: str,
    predicate: Callable[[dict[str, Any]], bool],
    *,
    interval: float = 0.95,
) -> dict[str, Any]:
    return {
        "label": label,
        "left": str(left),
        "right": str(right),
        "outcome": outcome,
        **_bootstrap(
            _paired_values(rows, str(left), str(right), outcome, predicate),
            config.bootstrap_repetitions,
            rng,
            interval=interval,
        ),
    }


def analyze_stage_a(
    config: ExperimentConfig, simulation: Path, output: Path
) -> dict[str, Any]:
    rows = load_rows(simulation, config)
    expected = config.stage_a_matrices * 6 * 4
    if len(rows) != expected:
        raise RuntimeError(f"expected {expected} Stage A rows, found {len(rows)}")
    rng = np.random.default_rng(
        derive_seed(config.master_seed, "fep_ph19.bootstrap.stage-a")
    )
    oracle = _contrast(
        rows,
        config,
        rng,
        "oracle_vs_noop",
        ControllerName.TRUE_REGIME_ORACLE,
        ControllerName.NOOP,
        PRIMARY,
        lambda _row: True,
    )
    sensing = _contrast(
        rows,
        config,
        rng,
        "always_sense_vs_reactive",
        ControllerName.ALWAYS_SENSE,
        ControllerName.REACTIVE,
        PRIMARY,
        lambda _row: True,
    )
    bands = [
        _contrast(
            rows,
            config,
            rng,
            f"always_sense_vs_reactive_switch_{switch:.2f}",
            ControllerName.ALWAYS_SENSE,
            ControllerName.REACTIVE,
            PRIMARY,
            lambda row, switch=switch: row["switch_probability"] == switch,
        )
        for switch in SWITCH_PROBABILITIES
    ]
    headroom = bool(
        oracle["lower"] is not None
        and oracle["lower"] > 0.0
        and sensing["lower"] is not None
        and sensing["lower"] > 0.0
        and all(value["estimate"] is not None and value["estimate"] > 0.0 for value in bands)
    )
    workflow_override = config.profile != "full"
    gate = {
        "schema": "fep-ph19-stage-a-gate-v1",
        "oracle_headroom": oracle,
        "informative_sensing_headroom": sensing,
        "switch_band_sensing_headroom": bands,
        "headroom_demonstrated": headroom,
        "workflow_only_override": workflow_override,
        "passed": headroom or workflow_override,
        "stage_b_action": "RUN" if headroom or workflow_override else "STOP",
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "gate.json", gate)
    write_json(
        output / "metrics.json",
        {
            "schema": "fep-ph19-stage-a-analysis-v1",
            "profile": config.profile,
            "rows": len(rows),
            "gate": gate,
        },
    )
    lines = [
        "# FEP–PH1.9 Stage A — sensing/action headroom",
        "",
        f"- Fresh headroom: **{'PASS' if headroom else 'FAIL'}**",
        f"- Stage B action: **{gate['stage_b_action']}**",
        "",
        "| Contrast | Estimate | 95% interval |",
        "|---|---:|---:|",
    ]
    for value in (oracle, sensing, *bands):
        lines.append(
            f"| {value['label']} | {value['estimate']} | [{value['lower']}, {value['upper']}] |"
        )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    seal_directory(output, ["gate.json", "metrics.json", "REPORT.md"])
    return gate


def _difference_in_differences(
    rows: list[dict[str, Any]],
    outcome: str,
    left: ControllerName,
    right: ControllerName,
) -> list[float]:
    relevant = [
        row
        for row in rows
        if row["controller"] in (str(left), str(right))
        and row["sensing_timing"] == str(SensingTiming.SAME_CYCLE)
    ]
    index = {
        (
            row["matrix_id"],
            row["candidate"],
            row["switch_probability"],
            row["information_arm"],
            row["controller"],
        ): row
        for row in relevant
    }
    by_matrix: dict[int, list[float]] = defaultdict(list)
    for matrix in sorted({int(row["matrix_id"]) for row in relevant}):
        for candidate in ("02", "03"):
            for switch in SWITCH_PROBABILITIES:
                effects: dict[str, float] = {}
                for arm in (str(InformationArm.INFORMATIVE), str(InformationArm.SHAM)):
                    lrow = index.get((matrix, candidate, switch, arm, str(left)))
                    rrow = index.get((matrix, candidate, switch, arm, str(right)))
                    if lrow is not None and rrow is not None:
                        effects[arm] = float(lrow[outcome]) - float(rrow[outcome])
                if len(effects) == 2:
                    by_matrix[matrix].append(
                        effects[str(InformationArm.INFORMATIVE)]
                        - effects[str(InformationArm.SHAM)]
                    )
    return [float(np.mean(values)) for _, values in sorted(by_matrix.items()) if values]


def _controller_means(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    outcomes = (
        PRIMARY,
        "completion_fraction",
        "survival_to_horizon",
        "live_sensing_fraction",
        "adaptation_precision",
        "adaptation_coverage",
        "abstract_action_cost",
        "physical_action_cost",
    )
    output: dict[str, dict[str, float | None]] = {}
    for controller in sorted({row["controller"] for row in rows}):
        selected = [
            row
            for row in rows
            if row["controller"] == controller
            and row["information_arm"] == str(InformationArm.INFORMATIVE)
            and row["sensing_timing"] == str(SensingTiming.SAME_CYCLE)
        ]
        output[controller] = {
            outcome: _finite_mean(
                [float(row[outcome]) for row in selected if row.get(outcome) is not None]
            )
            for outcome in outcomes
        }
    return output


def analyze_final(
    config: ExperimentConfig,
    simulation: Path,
    output: Path,
    *,
    fit_root: Path,
    integrity_valid: bool,
) -> dict[str, Any]:
    rows = load_rows(simulation, config)
    if not rows:
        raise RuntimeError("FEP–PH1.9 final analysis found no evaluation rows")
    rng = np.random.default_rng(
        derive_seed(config.master_seed, "fep_ph19.bootstrap.stage-b")
    )
    primary = lambda row: (
        row["information_arm"] == str(InformationArm.INFORMATIVE)
        and row["sensing_timing"] == str(SensingTiming.SAME_CYCLE)
    )
    sham = lambda row: (
        row["information_arm"] == str(InformationArm.SHAM)
        and row["sensing_timing"] == str(SensingTiming.SAME_CYCLE)
    )
    exact_vs_reactive = _contrast(
        rows,
        config,
        rng,
        "exact_efe_vs_reactive",
        ControllerName.EXACT_EFE,
        ControllerName.REACTIVE,
        PRIMARY,
        primary,
    )
    exact_vs_utility = _contrast(
        rows,
        config,
        rng,
        "exact_efe_vs_pragmatic",
        ControllerName.EXACT_EFE,
        ControllerName.EXACT_UTILITY,
        PRIMARY,
        primary,
    )
    exact_vs_always = _contrast(
        rows,
        config,
        rng,
        "exact_efe_vs_always_sense_equivalence",
        ControllerName.EXACT_EFE,
        ControllerName.ALWAYS_SENSE,
        PRIMARY,
        primary,
        interval=0.90,
    )
    sensing_reduction = _contrast(
        rows,
        config,
        rng,
        "always_sense_minus_exact_efe_sensing",
        ControllerName.ALWAYS_SENSE,
        ControllerName.EXACT_EFE,
        "live_sensing_fraction",
        primary,
    )
    did = {
        "label": "informative_minus_sham_exact_efe_vs_pragmatic",
        "outcome": PRIMARY,
        **_bootstrap(
            _difference_in_differences(
                rows, PRIMARY, ControllerName.EXACT_EFE, ControllerName.EXACT_UTILITY
            ),
            config.bootstrap_repetitions,
            rng,
        ),
    }
    sham_equivalence = _contrast(
        rows,
        config,
        rng,
        "exact_efe_vs_pragmatic_sham_equivalence",
        ControllerName.EXACT_EFE,
        ControllerName.EXACT_UTILITY,
        PRIMARY,
        sham,
        interval=0.90,
    )
    timing_yoke = _contrast(
        rows,
        config,
        rng,
        "exact_efe_vs_sensing_timing_yoke",
        ControllerName.EXACT_EFE,
        ControllerName.SENSING_YOKE,
        PRIMARY,
        primary,
    )
    same = _paired_values(
        rows,
        str(ControllerName.EXACT_EFE),
        str(ControllerName.EXACT_UTILITY),
        PRIMARY,
        lambda row: primary(row) and row["switch_probability"] == 0.15,
    )
    delayed = _paired_values(
        rows,
        str(ControllerName.EXACT_EFE),
        str(ControllerName.EXACT_UTILITY),
        PRIMARY,
        lambda row: row["information_arm"] == str(InformationArm.INFORMATIVE)
        and row["sensing_timing"] == str(SensingTiming.DELAYED),
    )
    timing_values = [left - right for left, right in zip(same, delayed, strict=True)]
    timing_specificity = {
        "label": "same_cycle_minus_delayed_exact_efe_advantage",
        "outcome": PRIMARY,
        **_bootstrap(timing_values, config.bootstrap_repetitions, rng),
    }
    exact_qualification = read_json(fit_root / "model-qualification.json")["exact"]
    recurrent_qualification = read_json(fit_root / "model-qualification.json")["recurrent"]
    recurrent_present = any(
        row["controller"] == str(ControllerName.RECURRENT_EFE) for row in rows
    )
    recurrent_replication: dict[str, Any] = {
        "entered_evaluation": recurrent_present,
        "qualification": recurrent_qualification,
    }
    if recurrent_present:
        recurrent_replication.update(
            {
                "versus_reactive": _contrast(
                    rows,
                    config,
                    rng,
                    "recurrent_efe_vs_reactive",
                    ControllerName.RECURRENT_EFE,
                    ControllerName.REACTIVE,
                    PRIMARY,
                    primary,
                ),
                "versus_pragmatic": _contrast(
                    rows,
                    config,
                    rng,
                    "recurrent_efe_vs_pragmatic",
                    ControllerName.RECURRENT_EFE,
                    ControllerName.RECURRENT_UTILITY,
                    PRIMARY,
                    primary,
                ),
            }
        )
    margin = config.efficiency_equivalence_margin
    sham_margin = config.sham_equivalence_margin
    component_tests = {
        "exact_model_qualified": bool(exact_qualification.get("qualified")),
        "recurrent_model_qualified": bool(recurrent_qualification.get("qualified")),
        "exact_efe_beats_reactive": bool(
            exact_vs_reactive["lower"] is not None and exact_vs_reactive["lower"] > 0.0
        ),
        "exact_efe_beats_pragmatic": bool(
            exact_vs_utility["lower"] is not None and exact_vs_utility["lower"] > 0.0
        ),
        "always_sense_equivalence": bool(
            exact_vs_always["lower"] is not None
            and exact_vs_always["lower"] > -margin
            and exact_vs_always["upper"] < margin
        ),
        "sensing_reduction": bool(
            sensing_reduction["lower"] is not None
            and sensing_reduction["lower"] > config.sensing_reduction_margin
        ),
        "information_specificity": bool(did["lower"] is not None and did["lower"] > 0.0),
        "sham_equivalence": bool(
            sham_equivalence["lower"] is not None
            and sham_equivalence["lower"] > -sham_margin
            and sham_equivalence["upper"] < sham_margin
        ),
        "timing_yoke_advantage": bool(
            timing_yoke["lower"] is not None and timing_yoke["lower"] > 0.0
        ),
        "same_cycle_specificity": bool(
            timing_specificity["lower"] is not None and timing_specificity["lower"] > 0.0
        ),
    }
    decision = {
        "integrity_verdict": "VALID" if integrity_valid else "INVALID",
        "scientific_status": (
            "WORKFLOW_ONLY"
            if config.profile != "full"
            else "EXPLORATORY_CAUSAL_SELECTIVE_SENSING_ATLAS_COMPLETE"
        ),
        "global_classifier": None,
        "claim_boundary": (
            "Tests engineered, blanket-limited selective sensing in reconstructed GARD; "
            "it does not establish intrinsic GARD inference, emergent blankets, inherited "
            "controller software, prebiotic chemistry, or a universal FEP mechanism."
        ),
    }
    metrics = {
        "schema": "fep-ph19-final-analysis-v1",
        "profile": config.profile,
        "primary_outcome": PRIMARY,
        "matrix_controller_rows": len(rows),
        "model_qualification": {
            "exact": exact_qualification,
            "recurrent": recurrent_qualification,
        },
        "exact_selective_sensing": {
            "versus_reactive": exact_vs_reactive,
            "versus_pragmatic": exact_vs_utility,
            "always_sense_equivalence": exact_vs_always,
            "sensing_reduction": sensing_reduction,
            "information_specificity": did,
            "sham_equivalence": sham_equivalence,
            "timing_yoke": timing_yoke,
            "timing_specificity": timing_specificity,
        },
        "recurrent_replication": recurrent_replication,
        "component_tests": component_tests,
        "controller_means": _controller_means(rows),
        "decision": decision,
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "metrics.json", metrics)
    lines = [
        "# FEP–PH1.9 — Causal Policy and Selective Sensing",
        "",
        f"- Integrity: **{decision['integrity_verdict']}**",
        f"- Scientific status: **{decision['scientific_status']}**",
        "- Global supported/not-supported classifier: **none (exploratory atlas)**",
        "",
        "| Preregistered component | Result |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {name} | {'PASS' if passed else 'FAIL'} |"
        for name, passed in component_tests.items()
    )
    lines.extend(("", decision["claim_boundary"], ""))
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    seal_directory(output, ["metrics.json", "REPORT.md"])
    return metrics


__all__ = ("analyze_final", "analyze_stage_a", "load_rows")
