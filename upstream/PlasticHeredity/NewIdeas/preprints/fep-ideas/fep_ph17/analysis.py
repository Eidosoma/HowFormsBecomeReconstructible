from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np

from fep_lab.integrity import read_json, seal_directory, write_json
from fep_lab.seeds import derive_seed
from fep_ph15.endpoints import episode_metrics

from .config import ExperimentConfig
from .types import ControllerName, InformationArm


OUTCOMES = (
    "inherited_completion_fraction",
    "completion_fraction",
    "survival_to_horizon",
    "recovery_after_shock",
    "abstract_action_cost",
    "posterior_accuracy",
    "correct_regime_action_rate",
    "sample_fraction",
)


def _finite_mean(values: list[float]) -> float | None:
    array = np.asarray(values, dtype=np.float64)
    array = array[np.isfinite(array)]
    return float(array.mean()) if array.size else None


def _episode_values(episode: dict[str, np.ndarray], horizon: int) -> dict[str, float]:
    output = episode_metrics(episode, horizon)
    output["inherited_completion_fraction"] = output["inherited_fixed_fraction"]
    beliefs = np.asarray(episode["body_regime_belief"], dtype=np.float64)
    regimes = np.asarray(episode["decision_regime"], dtype=np.int64)
    valid = (regimes >= 0) & np.all(np.isfinite(beliefs), axis=1)
    output["posterior_accuracy"] = (
        float(np.mean(beliefs[np.flatnonzero(valid), regimes[valid]]))
        if np.any(valid)
        else float("nan")
    )
    correct = np.asarray(episode["correct_regime_action"], dtype=np.float64)
    output["correct_regime_action_rate"] = (
        float(np.mean(correct[np.isfinite(correct)]))
        if np.any(np.isfinite(correct))
        else float("nan")
    )
    entropy = np.asarray(episode["posterior_entropy"], dtype=np.float64)
    sampled = np.asarray(episode["sampled"], dtype=np.float64)
    high = np.isfinite(entropy) & (entropy >= 0.65 * np.log(3.0))
    low = np.isfinite(entropy) & (entropy <= 0.35 * np.log(3.0))
    output["high_entropy_sample_fraction"] = (
        float(np.mean(sampled[high])) if np.any(high) else float("nan")
    )
    output["low_entropy_sample_fraction"] = (
        float(np.mean(sampled[low])) if np.any(low) else float("nan")
    )
    planning = np.asarray(episode["planning_fissions"], dtype=np.float64)
    output["total_planning_fissions"] = float(np.sum(planning))
    return output


def load_rows(
    simulation: Path, config: ExperimentConfig
) -> list[dict[str, Any]]:
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
                "tier": str(manifest["tier"]),
                "volatility": str(manifest["volatility"]),
                "authority_scale": float(manifest["authority_scale"]),
                "information_arm": str(manifest["information_arm"]),
                "controller": controller,
            }
            keys = set().union(*(value.keys() for value in branches))
            for key in keys:
                row[key] = _finite_mean([value.get(key, float("nan")) for value in branches])
            rows.append(row)
    return rows


def _authority_zero_biological_identity(simulation: Path) -> tuple[bool, int]:
    """Require exact paired trajectories when adaptive authority is absent."""

    fields = (
        "completed",
        "growth_steps",
        "similarity",
        "alignment_score",
        "decision_regime",
        "result_regime",
        "observations",
        "physical_action_cost",
        "parents",
        "compositions",
    )
    checked = 0
    for path in sorted((simulation / "cells").glob("*.npz")):
        metadata = read_json(path.with_suffix(".json"))
        if float(metadata["authority_scale"]) != 0.0:
            continue
        with np.load(path, allow_pickle=False) as archive:
            names = [str(value) for value in archive["controller_names"]]
            noop = names.index(str(ControllerName.NOOP))
            oracle = names.index(str(ControllerName.TRUE_REGIME_ORACLE))
            for field in fields:
                if not np.array_equal(
                    archive[field][noop], archive[field][oracle], equal_nan=True
                ):
                    return False, checked
        checked += 1
    return checked > 0, checked


def _bootstrap(
    values: list[float], repetitions: int, rng: np.random.Generator, *, interval: float = 0.95
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
    left: str,
    right: str,
    outcome: str,
    predicate: Callable[[dict[str, Any]], bool],
) -> list[float]:
    selected = [row for row in rows if predicate(row)]
    keys = (
        "matrix_id",
        "candidate",
        "tier",
        "volatility",
        "authority_scale",
        "information_arm",
    )
    index = {tuple(row[key] for key in keys) + (row["controller"],): row for row in selected}
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
    return [float(np.mean(value)) for _key, value in sorted(by_matrix.items()) if value]


def _difference_in_differences(
    rows: list[dict[str, Any]], outcome: str
) -> list[float]:
    relevant = [
        row
        for row in rows
        if row["controller"]
        in (str(ControllerName.ACTIVE_INFERENCE), str(ControllerName.PRAGMATIC))
    ]
    index = {
        (
            row["matrix_id"],
            row["candidate"],
            row["information_arm"],
            row["controller"],
        ): row
        for row in relevant
    }
    by_matrix: dict[int, list[float]] = defaultdict(list)
    for matrix_id in sorted({int(row["matrix_id"]) for row in relevant}):
        for candidate in ("02", "03"):
            values = {}
            for arm in (str(InformationArm.INFORMATIVE), str(InformationArm.SHAM)):
                active = index.get(
                    (matrix_id, candidate, arm, str(ControllerName.ACTIVE_INFERENCE))
                )
                pragmatic = index.get(
                    (matrix_id, candidate, arm, str(ControllerName.PRAGMATIC))
                )
                if active is None or pragmatic is None:
                    continue
                values[arm] = float(active[outcome]) - float(pragmatic[outcome])
            if len(values) == 2:
                by_matrix[matrix_id].append(
                    values[str(InformationArm.INFORMATIVE)]
                    - values[str(InformationArm.SHAM)]
                )
    return [float(np.mean(value)) for _key, value in sorted(by_matrix.items()) if value]


def _stage_a_contrast(
    rows: list[dict[str, Any]],
    authority: float,
    config: ExperimentConfig,
    rng: np.random.Generator,
) -> dict[str, Any]:
    predicate = lambda row: (
        row["tier"] == "hard"
        and row["volatility"] == "fast"
        and row["authority_scale"] == authority
    )
    return {
        "label": f"true_regime_oracle_vs_noop_at_authority_{authority:.1f}",
        "outcome": "inherited_completion_fraction",
        **_bootstrap(
            _paired_values(
                rows,
                str(ControllerName.TRUE_REGIME_ORACLE),
                str(ControllerName.NOOP),
                "inherited_completion_fraction",
                predicate,
            ),
            config.bootstrap_repetitions,
            rng,
        ),
    }


def analyze_stage_a(
    config: ExperimentConfig, simulation: Path, output: Path
) -> dict[str, Any]:
    rows = load_rows(simulation, config)
    expected = config.stage_a_matrices * 10 * 6
    if len(rows) != expected:
        raise RuntimeError(f"expected {expected} Stage A rows, found {len(rows)}")
    rng = np.random.default_rng(derive_seed(config.master_seed, "fep_ph17.bootstrap.stage-a"))
    current = _stage_a_contrast(rows, 1.0, config, rng)
    strengthened = _stage_a_contrast(rows, 1.5, config, rng)
    selected = None
    for authority, contrast in ((1.0, current), (1.5, strengthened)):
        if (
            contrast["estimate"] is not None
            and contrast["estimate"] >= 0.03
            and contrast["lower"] is not None
            and contrast["lower"] > 0.0
        ):
            selected = authority
            break
    identity, identity_cells = _authority_zero_biological_identity(simulation)
    if not identity:
        raise RuntimeError("authority-zero biological identity gate failed")
    # Development profiles exercise the complete conditional workflow without
    # pretending that one or eight matrices can adjudicate the scientific gate.
    # The full profile never receives this override.
    workflow_only_override = config.profile != "full"
    if workflow_only_override:
        selected = 1.0
    diagnostics = []
    for left, right, label in (
        (ControllerName.GOAL_D3, ControllerName.LEGACY_PROXY_D3, "goal_vs_proxy_d3"),
        (ControllerName.GOAL_D8, ControllerName.GOAL_D3, "depth8_vs_depth3_goal"),
        (ControllerName.REACTIVE, ControllerName.NOOP, "reactive_vs_noop"),
    ):
        for outcome in ("inherited_completion_fraction", "completion_fraction", "survival_to_horizon"):
            diagnostics.append(
                {
                    "label": label,
                    "outcome": outcome,
                    **_bootstrap(
                        _paired_values(
                            rows,
                            str(left),
                            str(right),
                            outcome,
                            lambda row: row["authority_scale"] == 1.0,
                        ),
                        config.bootstrap_repetitions,
                        rng,
                    ),
                }
            )
    gate = {
        "schema": "fep-ph17-stage-a-gate-v1",
        "authority_zero_identity": identity,
        "authority_zero_cells_checked": identity_cells,
        "current_authority": current,
        "strengthened_authority": strengthened,
        "passed": selected is not None,
        "selected_authority_scale": selected,
        "stage_b_action": "RUN" if selected is not None else "STOP",
        "workflow_only_override": workflow_only_override,
        "failure_status": (
            None
            if selected is not None
            else "CURRENT_ACTION_INTERFACE_HEADROOM_NOT_DEMONSTRATED"
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "gate.json", gate)
    metrics = {
        "schema": "fep-ph17-stage-a-analysis-v1",
        "profile": config.profile,
        "matrix_controller_rows": len(rows),
        "gate": gate,
        "diagnostic_contrasts": diagnostics,
    }
    write_json(output / "metrics.json", metrics)
    report = [
        "# FEP–PH Experiment 1.7 Stage A — goal-aligned controllability gate",
        "",
        f"- Authority-zero physical identity: **{'PASS' if identity else 'FAIL'}**",
        f"- Stage B gate: **{'PASS' if selected is not None else 'STOP'}**",
        f"- Selected authority: **{selected if selected is not None else 'none'}**",
        "",
        "| Contrast | Estimate | 95% interval |",
        "|---|---:|---:|",
    ]
    for contrast in (current, strengthened):
        report.append(
            f"| {contrast['label']} | {contrast['estimate']} | "
            f"[{contrast['lower']}, {contrast['upper']}] |"
        )
    (output / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    seal_directory(output, ["gate.json", "metrics.json", "REPORT.md"])
    return gate


def _contrast(
    rows: list[dict[str, Any]],
    left: ControllerName,
    right: ControllerName,
    outcome: str,
    arm: InformationArm,
    config: ExperimentConfig,
    rng: np.random.Generator,
    *,
    interval: float = 0.95,
) -> dict[str, Any]:
    return {
        "label": f"{left}_vs_{right}_{arm}",
        "outcome": outcome,
        **_bootstrap(
            _paired_values(
                rows,
                str(left),
                str(right),
                outcome,
                lambda row: row["information_arm"] == str(arm),
            ),
            config.bootstrap_repetitions,
            rng,
            interval=interval,
        ),
    }


def analyze_final(
    config: ExperimentConfig,
    stage_a_analysis: Path,
    stage_b_simulation: Path | None,
    output: Path,
) -> dict[str, Any]:
    gate = read_json(stage_a_analysis / "gate.json")
    reduced_power = config.stage_a_matrices < 24 or config.stage_b_matrices < 24
    output.mkdir(parents=True, exist_ok=True)
    if not gate["passed"]:
        decision = {
            "integrity_verdict": "VALID",
            "scientific_status": (
                "WORKFLOW_ONLY"
                if config.profile != "full"
                else "CURRENT_ACTION_INTERFACE_HEADROOM_NOT_DEMONSTRATED"
            ),
            "positive_negative_classifier": None,
            "stage_b_ran": False,
            "selected_authority_scale": None,
            "primary_outcome": "inherited_completion_fraction",
            "strict_events_are_held_out_descriptive_only": True,
            "reduced_power_scale": reduced_power,
        }
        metrics = {
            "schema": "fep-ph17-analysis-v1",
            "profile": config.profile,
            "stage_a_gate": gate,
            "stage_b": None,
            "decision": decision,
        }
    else:
        if stage_b_simulation is None:
            raise RuntimeError("Stage A passed but Stage B simulation is missing")
        rows = load_rows(stage_b_simulation, config)
        expected = config.stage_b_matrices * 4 * 8
        if len(rows) != expected:
            raise RuntimeError(f"expected {expected} Stage B rows, found {len(rows)}")
        rng = np.random.default_rng(derive_seed(config.master_seed, "fep_ph17.bootstrap.stage-b"))
        did = {
            "label": "information_value_difference_in_differences",
            "outcome": "inherited_completion_fraction",
            **_bootstrap(
                _difference_in_differences(rows, "inherited_completion_fraction"),
                config.bootstrap_repetitions,
                rng,
            ),
        }
        informative = _contrast(
            rows,
            ControllerName.ACTIVE_INFERENCE,
            ControllerName.PRAGMATIC,
            "inherited_completion_fraction",
            InformationArm.INFORMATIVE,
            config,
            rng,
        )
        sample_lesion = _contrast(
            rows,
            ControllerName.ACTIVE_INFERENCE,
            ControllerName.SAMPLE_LESION,
            "inherited_completion_fraction",
            InformationArm.INFORMATIVE,
            config,
            rng,
        )
        timing = _contrast(
            rows,
            ControllerName.ACTIVE_INFERENCE,
            ControllerName.EFE_YOKED,
            "inherited_completion_fraction",
            InformationArm.INFORMATIVE,
            config,
            rng,
        )
        action_semantics = _contrast(
            rows,
            ControllerName.ACTIVE_INFERENCE,
            ControllerName.EFE_SHUFFLED,
            "inherited_completion_fraction",
            InformationArm.INFORMATIVE,
            config,
            rng,
        )
        sham = _contrast(
            rows,
            ControllerName.ACTIVE_INFERENCE,
            ControllerName.PRAGMATIC,
            "inherited_completion_fraction",
            InformationArm.SHAM,
            config,
            rng,
            interval=0.90,
        )
        accuracy = _contrast(
            rows,
            ControllerName.ACTIVE_INFERENCE,
            ControllerName.PRAGMATIC,
            "posterior_accuracy",
            InformationArm.INFORMATIVE,
            config,
            rng,
        )
        correct_action = _contrast(
            rows,
            ControllerName.ACTIVE_INFERENCE,
            ControllerName.PRAGMATIC,
            "correct_regime_action_rate",
            InformationArm.INFORMATIVE,
            config,
            rng,
        )

        def positive(value: dict[str, Any], minimum: float = 0.0) -> bool:
            return (
                value["estimate"] is not None
                and value["estimate"] >= minimum
                and value["lower"] is not None
                and value["lower"] > 0.0
            )

        sham_equivalent = (
            sham["lower"] is not None
            and sham["upper"] is not None
            and sham["lower"] > -0.02
            and sham["upper"] < 0.02
        )
        supported = all(
            (
                positive(did, 0.02),
                positive(informative),
                positive(sample_lesion),
                positive(timing),
                sham_equivalent,
                positive(accuracy),
                positive(correct_action),
            )
        )
        decision = {
            "integrity_verdict": "VALID",
            "scientific_status": (
                "WORKFLOW_ONLY"
                if config.profile != "full"
                else "ENGINEERED_EPISTEMIC_CONTROL_SUPPORTED"
                if supported
                else "ENGINEERED_EPISTEMIC_CONTROL_NOT_SUPPORTED"
            ),
            "positive_negative_classifier": (
                None
                if config.profile != "full"
                else "HYPOTHESIS_SUPPORTED"
                if supported
                else "HYPOTHESIS_NOT_SUPPORTED"
            ),
            "stage_b_ran": True,
            "selected_authority_scale": gate["selected_authority_scale"],
            "primary_outcome": "inherited_completion_fraction",
            "strict_events_are_held_out_descriptive_only": True,
            "reduced_power_scale": reduced_power,
        }
        diagnostic_contrasts = []
        for left, right in (
            (ControllerName.ACTIVE_INFERENCE, ControllerName.NOOP),
            (ControllerName.ACTIVE_INFERENCE, ControllerName.REACTIVE),
            (ControllerName.PRAGMATIC, ControllerName.NOOP),
            (ControllerName.TRUE_REGIME_ORACLE, ControllerName.NOOP),
        ):
            for arm in (InformationArm.INFORMATIVE, InformationArm.SHAM):
                for outcome in (
                    "inherited_completion_fraction",
                    "completion_fraction",
                    "survival_to_horizon",
                    "recovery_after_shock",
                    "abstract_action_cost",
                ):
                    diagnostic_contrasts.append(
                        _contrast(rows, left, right, outcome, arm, config, rng)
                    )
        group_summaries = []
        for arm in (InformationArm.INFORMATIVE, InformationArm.SHAM):
            for controller in sorted({row["controller"] for row in rows}):
                selected_rows = [
                    row
                    for row in rows
                    if row["information_arm"] == str(arm)
                    and row["controller"] == controller
                ]
                group_summaries.append(
                    {
                        "information_arm": str(arm),
                        "controller": controller,
                        "matrices": len(
                            {int(row["matrix_id"]) for row in selected_rows}
                        ),
                        "condition_rows": len(selected_rows),
                        "metrics": {
                            outcome: _finite_mean(
                                [
                                    float(row[outcome])
                                    if row[outcome] is not None
                                    else float("nan")
                                    for row in selected_rows
                                ]
                            )
                            for outcome in OUTCOMES
                        },
                    }
                )
        metrics = {
            "schema": "fep-ph17-analysis-v1",
            "profile": config.profile,
            "matrix_controller_rows": len(rows),
            "stage_a_gate": gate,
            "stage_b": {
                "primary_difference_in_differences": did,
                "informative_superiority": informative,
                "sample_lesion": sample_lesion,
                "timing_yoke": timing,
                "action_semantics_descriptive": action_semantics,
                "sham_equivalence": {**sham, "equivalent_within_0.02": sham_equivalent},
                "posterior_accuracy": accuracy,
                "correct_regime_action": correct_action,
            },
            "diagnostic_contrasts": diagnostic_contrasts,
            "group_summaries": group_summaries,
            "decision": decision,
            "claim_boundary": (
                "Externally engineered, blanket-limited active inference in reconstructed "
                "GARD only; not intrinsic GARD beliefs, emergent blankets, inherited software "
                "control, prebiotic chemistry, or a universal FEP mechanism."
            ),
        }
    write_json(output / "metrics.json", metrics)
    report = [
        "# FEP–PH Experiment 1.7 goal-aligned dual-control challenge",
        "",
        f"- Integrity: **{decision['integrity_verdict']}**",
        f"- Scientific status: **{decision['scientific_status']}**",
        f"- Classifier: **{decision['positive_negative_classifier']}**",
        f"- Stage B ran: **{decision['stage_b_ran']}**",
        f"- Reduced-power scale: **{decision['reduced_power_scale']}**",
        "",
        "F12 and strict-8 are held-out descriptive outcomes and cannot determine this verdict.",
    ]
    if metrics.get("stage_b"):
        report.extend(("", "## Frozen Stage B gates", "", "| Gate | Estimate | Interval |", "|---|---:|---:|"))
        for key, value in metrics["stage_b"].items():
            report.append(
                f"| {key} | {value.get('estimate')} | "
                f"[{value.get('lower')}, {value.get('upper')}] |"
            )
    (output / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    seal_directory(output, ["metrics.json", "REPORT.md"])
    return metrics
