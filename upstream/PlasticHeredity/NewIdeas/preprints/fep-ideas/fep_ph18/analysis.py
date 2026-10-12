from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np

from fep_lab.integrity import read_json, seal_directory, write_json
from fep_lab.seeds import derive_seed
from fep_ph15.endpoints import episode_metrics

from .config import CONFIRM_SWITCH_PROBABILITIES, ExperimentConfig
from .types import ControllerName, InformationArm, SensingTiming


PRIMARY = "inherited_completion_fraction"
EQUIVALENCE_MARGIN = 0.02


def _finite_mean(values: list[float]) -> float | None:
    array = np.asarray(values, dtype=np.float64)
    array = array[np.isfinite(array)]
    return float(array.mean()) if array.size else None


def _episode_values(episode: dict[str, np.ndarray], horizon: int) -> dict[str, float]:
    output = episode_metrics(episode, horizon)
    output[PRIMARY] = output["inherited_fixed_fraction"]
    beliefs = np.asarray(episode["pre_action_belief"], dtype=np.float64)
    regimes = np.asarray(episode["decision_regime"], dtype=np.int64)
    valid = (regimes >= 0) & np.all(np.isfinite(beliefs), axis=1)
    output["posterior_accuracy"] = (
        float(np.mean(beliefs[np.flatnonzero(valid), regimes[valid]]))
        if np.any(valid)
        else float("nan")
    )
    correct = np.asarray(episode["correct_regime_action"], dtype=np.float64)
    output["adaptation_precision"] = (
        float(np.mean(correct[np.isfinite(correct)]))
        if np.any(np.isfinite(correct))
        else float("nan")
    )
    adapted = np.asarray(episode["adapted"], dtype=np.float64)
    opportunities = np.asarray(episode["adaptation_opportunity"], dtype=bool)
    output["adaptation_coverage"] = (
        float(np.mean(adapted[opportunities])) if np.any(opportunities) else float("nan")
    )
    output["sample_fraction"] = float(np.mean(np.asarray(episode["sampled"])))
    output["contingent_fraction"] = float(
        np.mean(np.asarray(episode["policy_contingency"], dtype=np.float64))
    )
    output["mean_instrumental_value"] = float(
        np.nanmean(np.asarray(episode["instrumental_value"], dtype=np.float64))
    )
    output["mean_epistemic_value"] = float(
        np.nanmean(np.asarray(episode["epistemic_value"], dtype=np.float64))
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
                "volatility": str(manifest["volatility"]),
                "sensing_timing": str(manifest["sensing_timing"]),
                "information_arm": str(manifest["information_arm"]),
                "controller": controller,
            }
            keys = set().union(*(value.keys() for value in branches))
            for key in keys:
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
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {
            "estimate": None,
            "lower": None,
            "upper": None,
            "interval": interval,
            "n_matrices": 0,
        }
    draws = finite[
        rng.integers(0, len(finite), size=(repetitions, len(finite)))
    ].mean(axis=1)
    tail = (1.0 - interval) / 2.0
    return {
        "estimate": float(np.mean(finite)),
        "lower": float(np.quantile(draws, tail)),
        "upper": float(np.quantile(draws, 1.0 - tail)),
        "interval": interval,
        "n_matrices": int(len(finite)),
    }


def _paired_values(
    rows: list[dict[str, Any]],
    left: ControllerName,
    right: ControllerName,
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
        left_row = index.get(key + (str(left),))
        right_row = index.get(key + (str(right),))
        if left_row is None or right_row is None:
            continue
        left_value, right_value = left_row.get(outcome), right_row.get(outcome)
        if left_value is None or right_value is None:
            continue
        difference = float(left_value) - float(right_value)
        if np.isfinite(difference):
            by_matrix[int(key[0])].append(difference)
    return [
        float(np.mean(value)) for _key, value in sorted(by_matrix.items()) if value
    ]


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
            _paired_values(rows, left, right, outcome, predicate),
            config.bootstrap_repetitions,
            rng,
            interval=interval,
        ),
    }


def analyze_stage_a(
    config: ExperimentConfig, simulation: Path, output: Path
) -> dict[str, Any]:
    rows = load_rows(simulation, config)
    expected = config.stage_a_matrices * 10 * 3
    if len(rows) != expected:
        raise RuntimeError(f"expected {expected} Stage A rows, found {len(rows)}")
    rng = np.random.default_rng(
        derive_seed(config.master_seed, "fep_ph18.bootstrap.stage-a")
    )
    pooled = _contrast(
        rows,
        config,
        rng,
        "oracle_vs_noop_pooled",
        ControllerName.TRUE_REGIME_ORACLE,
        ControllerName.NOOP,
        PRIMARY,
        lambda _row: True,
    )
    versus_reactive = _contrast(
        rows,
        config,
        rng,
        "oracle_vs_reactive_pooled",
        ControllerName.TRUE_REGIME_ORACLE,
        ControllerName.REACTIVE,
        PRIMARY,
        lambda _row: True,
    )
    bands = []
    for switch in (0.02, 0.08, 0.15, 0.25, 0.40):
        bands.append(
            _contrast(
                rows,
                config,
                rng,
                f"oracle_vs_noop_switch_{switch:.2f}",
                ControllerName.TRUE_REGIME_ORACLE,
                ControllerName.NOOP,
                PRIMARY,
                lambda row, switch=switch: row["switch_probability"] == switch,
            )
        )
    confirmation_bands = [
        value
        for value in bands
        if any(
            abs(float(value["label"].rsplit("_", 1)[-1]) - target) < 1.0e-12
            for target in CONFIRM_SWITCH_PROBABILITIES
        )
    ]
    headroom = bool(
        pooled["lower"] is not None
        and pooled["lower"] > 0.0
        and versus_reactive["estimate"] is not None
        and versus_reactive["estimate"] > 0.0
        and all(
            item["estimate"] is not None and item["estimate"] > 0.0
            for item in confirmation_bands
        )
    )
    workflow_only_override = config.profile != "full"
    passed = headroom or workflow_only_override
    gate = {
        "schema": "fep-ph18-stage-a-gate-v1",
        "pooled_oracle_headroom": pooled,
        "oracle_vs_reactive": versus_reactive,
        "switch_band_headroom": bands,
        "confirmation_bands": list(CONFIRM_SWITCH_PROBABILITIES),
        "headroom_demonstrated": headroom,
        "passed": passed,
        "stage_b_action": "RUN" if passed else "STOP",
        "selected_authority_scale": 1.0 if passed else None,
        "workflow_only_override": workflow_only_override,
        "failure_status": None if passed else "GOAL_ALIGNED_HEADROOM_NOT_DEMONSTRATED",
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "gate.json", gate)
    metrics = {
        "schema": "fep-ph18-stage-a-analysis-v1",
        "profile": config.profile,
        "matrix_controller_rows": len(rows),
        "gate": gate,
    }
    write_json(output / "metrics.json", metrics)
    lines = [
        "# FEP–PH1.8 Stage A — dynamic-regime headroom screen",
        "",
        f"- Goal-aligned headroom: **{'PASS' if headroom else 'FAIL'}**",
        f"- Stage B action: **{gate['stage_b_action']}**",
        "",
        "| Contrast | Estimate | 95% interval |",
        "|---|---:|---:|",
    ]
    for contrast in (pooled, versus_reactive, *bands):
        lines.append(
            f"| {contrast['label']} | {contrast['estimate']} | "
            f"[{contrast['lower']}, {contrast['upper']}] |"
        )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    seal_directory(output, ["gate.json", "metrics.json", "REPORT.md"])
    return metrics


def _difference_in_differences(
    rows: list[dict[str, Any]],
    outcome: str,
    left: ControllerName,
    right: ControllerName,
) -> list[float]:
    relevant = [row for row in rows if row["controller"] in (str(left), str(right))]
    index = {
        (
            row["matrix_id"],
            row["candidate"],
            row["switch_probability"],
            row["sensing_timing"],
            row["information_arm"],
            row["controller"],
        ): row
        for row in relevant
    }
    by_matrix: dict[int, list[float]] = defaultdict(list)
    for matrix in sorted({int(row["matrix_id"]) for row in relevant}):
        for candidate in ("02", "03"):
            for switch in CONFIRM_SWITCH_PROBABILITIES:
                for timing in (str(SensingTiming.DELAYED), str(SensingTiming.SAME_CYCLE)):
                    effects: dict[str, float] = {}
                    for arm in (str(InformationArm.INFORMATIVE), str(InformationArm.SHAM)):
                        left_row = index.get((matrix, candidate, switch, timing, arm, str(left)))
                        right_row = index.get((matrix, candidate, switch, timing, arm, str(right)))
                        if left_row is not None and right_row is not None:
                            effects[arm] = float(left_row[outcome]) - float(right_row[outcome])
                    if len(effects) == 2:
                        by_matrix[matrix].append(
                            effects[str(InformationArm.INFORMATIVE)]
                            - effects[str(InformationArm.SHAM)]
                        )
    return [float(np.mean(values)) for _, values in sorted(by_matrix.items()) if values]


def _arm_difference(
    rows: list[dict[str, Any]], controller: ControllerName, outcome: str
) -> list[float]:
    relevant = [row for row in rows if row["controller"] == str(controller)]
    index = {
        (
            row["matrix_id"],
            row["candidate"],
            row["switch_probability"],
            row["sensing_timing"],
            row["information_arm"],
        ): row
        for row in relevant
    }
    by_matrix: dict[int, list[float]] = defaultdict(list)
    base_keys = {
        (row["matrix_id"], row["candidate"], row["switch_probability"], row["sensing_timing"])
        for row in relevant
    }
    for key in sorted(base_keys):
        informative = index.get(key + (str(InformationArm.INFORMATIVE),))
        sham = index.get(key + (str(InformationArm.SHAM),))
        if informative is None or sham is None:
            continue
        difference = float(informative[outcome]) - float(sham[outcome])
        if np.isfinite(difference):
            by_matrix[int(key[0])].append(difference)
    return [float(np.mean(values)) for _, values in sorted(by_matrix.items()) if values]


def _timing_volatility_interaction(
    rows: list[dict[str, Any]], outcome: str
) -> list[float]:
    relevant = [
        row
        for row in rows
        if row["information_arm"] == str(InformationArm.INFORMATIVE)
        and row["controller"]
        in (str(ControllerName.CONTINGENT_EFE), str(ControllerName.CONTINGENT_UTILITY))
    ]
    index = {
        (
            row["matrix_id"],
            row["candidate"],
            row["switch_probability"],
            row["sensing_timing"],
            row["controller"],
        ): row
        for row in relevant
    }
    by_matrix: dict[int, list[float]] = defaultdict(list)
    for matrix in sorted({int(row["matrix_id"]) for row in relevant}):
        for candidate in ("02", "03"):
            timing_effect: dict[float, float] = {}
            for switch in (0.08, 0.25):
                controller_effect: dict[str, float] = {}
                for controller in (
                    ControllerName.CONTINGENT_EFE,
                    ControllerName.CONTINGENT_UTILITY,
                ):
                    same = index.get(
                        (matrix, candidate, switch, str(SensingTiming.SAME_CYCLE), str(controller))
                    )
                    delayed = index.get(
                        (matrix, candidate, switch, str(SensingTiming.DELAYED), str(controller))
                    )
                    if same is not None and delayed is not None:
                        controller_effect[str(controller)] = float(same[outcome]) - float(delayed[outcome])
                if len(controller_effect) == 2:
                    timing_effect[switch] = (
                        controller_effect[str(ControllerName.CONTINGENT_EFE)]
                        - controller_effect[str(ControllerName.CONTINGENT_UTILITY)]
                    )
            if len(timing_effect) == 2:
                by_matrix[matrix].append(timing_effect[0.25] - timing_effect[0.08])
    return [float(np.mean(values)) for _, values in sorted(by_matrix.items()) if values]


def analyze_final(
    config: ExperimentConfig,
    simulation: Path,
    output: Path,
    *,
    integrity_valid: bool,
) -> dict[str, Any]:
    rows = load_rows(simulation, config)
    model_selection = read_json(simulation.parent / "fit" / "model-selection.json")
    expected = config.stage_b_matrices * 24 * 10
    if len(rows) != expected:
        raise RuntimeError(f"expected {expected} Stage B rows, found {len(rows)}")
    rng = np.random.default_rng(
        derive_seed(config.master_seed, "fep_ph18.bootstrap.stage-b")
    )
    informative = lambda row: row["information_arm"] == str(InformationArm.INFORMATIVE)
    sham = lambda row: row["information_arm"] == str(InformationArm.SHAM)
    comparator_names = (
        (ControllerName.CONTINGENT_UTILITY, "utility"),
        (ControllerName.REACTIVE, "reactive"),
        (ControllerName.OPEN_LOOP_EFE, "open_loop"),
        (ControllerName.SAMPLE_LESION, "sample_lesion"),
    )
    advantages: dict[str, Any] = {}
    for comparator, label in comparator_names:
        advantages[label] = _contrast(
            rows,
            config,
            rng,
            f"contingent_efe_vs_{label}_informative",
            ControllerName.CONTINGENT_EFE,
            comparator,
            PRIMARY,
            informative,
        )
    band_advantages = []
    for switch in CONFIRM_SWITCH_PROBABILITIES:
        band_advantages.append(
            _contrast(
                rows,
                config,
                rng,
                f"efe_vs_utility_informative_switch_{switch:.2f}",
                ControllerName.CONTINGENT_EFE,
                ControllerName.CONTINGENT_UTILITY,
                PRIMARY,
                lambda row, switch=switch: informative(row)
                and row["switch_probability"] == switch,
            )
        )
    did = {
        "label": "information_vs_sham_difference_in_differences",
        "outcome": PRIMARY,
        **_bootstrap(
            _difference_in_differences(
                rows,
                PRIMARY,
                ControllerName.CONTINGENT_EFE,
                ControllerName.CONTINGENT_UTILITY,
            ),
            config.bootstrap_repetitions,
            rng,
        ),
    }
    sham_equivalence = _contrast(
        rows,
        config,
        rng,
        "efe_vs_utility_sham_equivalence",
        ControllerName.CONTINGENT_EFE,
        ControllerName.CONTINGENT_UTILITY,
        PRIMARY,
        sham,
        interval=0.90,
    )
    precision = _contrast(
        rows,
        config,
        rng,
        "efe_vs_reactive_adaptation_precision",
        ControllerName.CONTINGENT_EFE,
        ControllerName.REACTIVE,
        "adaptation_precision",
        informative,
    )
    coverage = _contrast(
        rows,
        config,
        rng,
        "efe_vs_utility_adaptation_coverage",
        ControllerName.CONTINGENT_EFE,
        ControllerName.CONTINGENT_UTILITY,
        "adaptation_coverage",
        informative,
    )
    posterior_instrument = {
        "label": "always_sense_informative_vs_sham_posterior_instrument",
        "controller": str(ControllerName.ALWAYS_SENSE),
        "outcome": "posterior_accuracy",
        **_bootstrap(
            _arm_difference(rows, ControllerName.ALWAYS_SENSE, "posterior_accuracy"),
            config.bootstrap_repetitions,
            rng,
        ),
    }
    contingency = _contrast(
        rows,
        config,
        rng,
        "efe_vs_open_loop_contingency_activation",
        ControllerName.CONTINGENT_EFE,
        ControllerName.OPEN_LOOP_EFE,
        "contingent_fraction",
        informative,
    )
    interaction = {
        "label": "timing_by_volatility_interaction",
        "outcome": PRIMARY,
        **_bootstrap(
            _timing_volatility_interaction(rows, PRIMARY),
            config.bootstrap_repetitions,
            rng,
        ),
    }

    gate_results = {
        "efe_beats_utility": bool(
            advantages["utility"]["lower"] is not None
            and advantages["utility"]["lower"] > 0.0
            and all(
                value["estimate"] is not None and value["estimate"] > 0.0
                for value in band_advantages
            )
        ),
        "efe_beats_reactive": bool(
            advantages["reactive"]["lower"] is not None
            and advantages["reactive"]["lower"] > 0.0
        ),
        "contingency_beats_open_loop": bool(
            advantages["open_loop"]["lower"] is not None
            and advantages["open_loop"]["lower"] > 0.0
        ),
        "sensing_beats_lesion": bool(
            advantages["sample_lesion"]["lower"] is not None
            and advantages["sample_lesion"]["lower"] > 0.0
        ),
        "information_specific_difference_in_differences": bool(
            did["lower"] is not None and did["lower"] > 0.0
        ),
        "sham_equivalence": bool(
            sham_equivalence["lower"] is not None
            and sham_equivalence["upper"] is not None
            and sham_equivalence["lower"] > -EQUIVALENCE_MARGIN
            and sham_equivalence["upper"] < EQUIVALENCE_MARGIN
        ),
        "adaptation_precision_and_coverage": bool(
            precision["estimate"] is not None
            and precision["estimate"] >= 0.0
            and coverage["estimate"] is not None
            and coverage["estimate"] > 0.0
        ),
        "timing_by_volatility_interaction": bool(
            interaction["lower"] is not None and interaction["lower"] > 0.0
        ),
    }
    workflow_only = config.profile != "full"
    supported = all(gate_results.values()) if not workflow_only else False
    component_verdicts = {
        "nonlinear_body_model": (
            "CALIBRATION_PASSED"
            if model_selection.get("model_calibration_passed") is True
            else "CALIBRATION_NOT_PASSED_WORKFLOW_ONLY"
        ),
        "information_instrument": (
            "DEMONSTRATED"
            if posterior_instrument["estimate"] is not None
            and posterior_instrument["estimate"] > 0.0
            else "NOT_DEMONSTRATED"
        ),
        "observation_contingency": (
            "ACTIVATED"
            if contingency["estimate"] is not None and contingency["estimate"] > 0.0
            else "NOT_ACTIVATED"
        ),
        "biological_fep_advantage": "SUPPORTED" if supported else "NOT_SUPPORTED",
    }
    decision = {
        "integrity_verdict": "VALID" if integrity_valid else "INVALID",
        "scientific_status": (
            "WORKFLOW_ONLY"
            if workflow_only
            else "HYPOTHESIS_SUPPORTED"
            if supported
            else "HYPOTHESIS_NOT_SUPPORTED"
        ),
        "positive_negative_classifier": None if workflow_only else supported,
        "reduced_power_scale": bool(config.stage_b_matrices < 24),
        "claim_boundary": (
            "Tests engineered, blanket-limited contingent active inference in "
            "reconstructed GARD; it does not establish intrinsic GARD inference, "
            "emergent Markov blankets, prebiotic chemistry, or a universal FEP mechanism."
        ),
    }
    metrics = {
        "schema": "fep-ph18-final-analysis-v1",
        "profile": config.profile,
        "matrix_controller_rows": len(rows),
        "primary_outcome": PRIMARY,
        "model_selection": model_selection,
        "advantages": advantages,
        "three_band_advantages": band_advantages,
        "information_specificity": did,
        "sham_equivalence": sham_equivalence,
        "adaptation_precision": precision,
        "adaptation_coverage": coverage,
        "posterior_instrument": posterior_instrument,
        "contingency_activation": contingency,
        "timing_volatility_interaction": interaction,
        "strict_gates": gate_results,
        "component_verdicts": component_verdicts,
        "decision": decision,
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "metrics.json", metrics)
    lines = [
        "# FEP–PH1.8 — Contingent Active Inference and Timescale Matching",
        "",
        f"- Integrity: **{decision['integrity_verdict']}**",
        f"- Scientific status: **{decision['scientific_status']}**",
        f"- Strict gates passed: **{sum(gate_results.values())}/{len(gate_results)}**",
        "",
        "| Gate | Result |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {name} | {'PASS' if passed else 'FAIL'} |"
        for name, passed in gate_results.items()
    )
    lines.extend(("", decision["claim_boundary"], ""))
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    seal_directory(output, ["metrics.json", "REPORT.md"])
    return metrics
