from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .blanket import build_blanket_model, impulse_response
from .config import LabConfig
from .integrity import read_json, seal_directory, write_json
from .simulation import CONTROLLERS

SCENARIOS = ("epistemic", "known", "disturbed")


def _cell_path(simulation: Path, scenario: str, controller: str) -> Path:
    return simulation / "homeostat" / f"{scenario}--{controller}.npz"


def _load_cell(simulation: Path, scenario: str, controller: str) -> dict[str, np.ndarray]:
    with np.load(_cell_path(simulation, scenario, controller), allow_pickle=False) as data:
        return {name: data[name].copy() for name in data.files}


def _metric(cell: dict[str, np.ndarray], name: str) -> np.ndarray:
    return np.asarray(cell[f"metric_{name}"], dtype=np.float64)


def _paired_difference(
    left: np.ndarray,
    right: np.ndarray,
    repetitions: int,
    rng: np.random.Generator,
) -> dict[str, float]:
    difference = np.asarray(left, dtype=np.float64) - np.asarray(right, dtype=np.float64)
    if difference.shape != np.asarray(right).shape:
        raise ValueError("paired arrays must share a shape")
    draws = np.empty(repetitions, dtype=np.float64)
    for repetition in range(repetitions):
        indices = rng.integers(0, len(difference), size=len(difference))
        draws[repetition] = float(np.mean(difference[indices]))
    return {
        "estimate": float(np.mean(difference)),
        "lower_95": float(np.quantile(draws, 0.025)),
        "upper_95": float(np.quantile(draws, 0.975)),
    }


def _action_distribution(cell: dict[str, np.ndarray]) -> np.ndarray:
    actions = np.asarray(cell["executed_actions"], dtype=np.int64).ravel()
    counts = np.bincount(actions, minlength=4).astype(np.float64)
    return counts / counts.sum()


def _gate(name: str, passed: bool, criterion: str, **evidence: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "criterion": criterion,
        "evidence": evidence,
    }


def analyze_campaign(
    config: LabConfig,
    profile_root: Path,
    output: Path,
) -> dict[str, Any]:
    simulation = profile_root / "simulation"
    validation = read_json(profile_root / "validation" / "validation.json")
    cells = {
        (scenario, controller): _load_cell(simulation, scenario, controller)
        for scenario in SCENARIOS
        for controller in CONTROLLERS
    }
    summaries: dict[str, dict[str, float]] = {}
    metric_names = (
        "viable_fraction",
        "depleted_fraction",
        "overloaded_fraction",
        "sample_fraction",
        "first_sample",
        "mean_action_cost",
        "regime_log_loss",
        "mean_regime_entropy",
        "mean_vfe",
    )
    for (scenario, controller), cell in cells.items():
        summaries[f"{scenario}--{controller}"] = {
            name: float(np.mean(_metric(cell, name))) for name in metric_names
        }

    blanket_intact = read_json(simulation / "blanket" / "intact.metrics.json")
    blanket_broken = read_json(simulation / "blanket" / "blanket_break.metrics.json")
    intact_partial = float(blanket_intact["partial_correlation_external_internal"])
    intact_ci = tuple(float(value) for value in blanket_intact["bootstrap_ci_95"])
    intact_cmi = float(blanket_intact["conditional_mutual_information"])
    broken_partial = float(blanket_broken["partial_correlation_external_internal"])
    broken_ci = tuple(float(value) for value in blanket_broken["bootstrap_ci_95"])

    rng = np.random.default_rng(884931)
    repetitions = config.bootstrap_repetitions
    uncertain_sampling = _paired_difference(
        _metric(cells[("epistemic", "active_inference")], "first_sample"),
        _metric(cells[("known", "active_inference")], "first_sample"),
        repetitions,
        rng,
    )
    epistemic_ablation = _paired_difference(
        _metric(cells[("epistemic", "active_inference")], "first_sample"),
        _metric(cells[("epistemic", "epistemic_lesion")], "first_sample"),
        repetitions,
        rng,
    )
    active_random = _paired_difference(
        _metric(cells[("disturbed", "active_inference")], "viable_fraction"),
        _metric(cells[("disturbed", "random")], "viable_fraction"),
        repetitions,
        rng,
    )
    active_noop = _paired_difference(
        _metric(cells[("disturbed", "active_inference")], "viable_fraction"),
        _metric(cells[("disturbed", "no_op")], "viable_fraction"),
        repetitions,
        rng,
    )
    scrambled_log_loss = _paired_difference(
        _metric(cells[("epistemic", "scrambled_likelihood")], "regime_log_loss"),
        _metric(cells[("epistemic", "active_inference")], "regime_log_loss"),
        repetitions,
        rng,
    )
    active_reversed = _paired_difference(
        _metric(cells[("disturbed", "active_inference")], "viable_fraction"),
        _metric(cells[("disturbed", "reversed_preferences")], "viable_fraction"),
        repetitions,
        rng,
    )
    oracle_active = _paired_difference(
        _metric(cells[("disturbed", "oracle")], "viable_fraction"),
        _metric(cells[("disturbed", "active_inference")], "viable_fraction"),
        repetitions,
        rng,
    )
    active_actions = _action_distribution(cells[("disturbed", "active_inference")])
    reversed_actions = _action_distribution(cells[("disturbed", "reversed_preferences")])
    action_tv = float(0.5 * np.abs(active_actions - reversed_actions).sum())
    action_lesion = cells[("epistemic", "action_lesion")]
    no_op = cells[("epistemic", "no_op")]
    lesion_pathwise = np.array_equal(action_lesion["states"], no_op["states"]) and np.array_equal(
        action_lesion["observations"], no_op["observations"]
    )

    entropy_check = next(
        check
        for check in validation["checks"]
        if check["name"] == "sampling_reduces_expected_regime_entropy"
    )
    gates = [
        _gate(
            "numerical_validation",
            bool(validation["all_pass"]),
            "all analytic and dual-engine checks pass",
        ),
        _gate(
            "blanket_intact_partial",
            abs(intact_partial) < 0.02 and intact_ci[0] <= 0.0 <= intact_ci[1],
            "|partial correlation| < 0.02 and bootstrap interval contains zero",
            estimate=intact_partial,
            interval=intact_ci,
        ),
        _gate(
            "blanket_intact_cmi",
            intact_cmi < 2e-4,
            "Gaussian conditional mutual information < 2e-4",
            estimate=intact_cmi,
        ),
        _gate(
            "blanket_break",
            abs(broken_partial) > 0.08 and not (broken_ci[0] <= 0.0 <= broken_ci[1]),
            "lesion |partial correlation| > 0.08 and interval excludes zero",
            estimate=broken_partial,
            interval=broken_ci,
        ),
        _gate(
            "informative_cue",
            bool(entropy_check["passed"]),
            "sampling reduces expected regime entropy by at least 0.20 nats",
            reduction=entropy_check["reduction"],
        ),
        _gate(
            "uncertainty_drives_sampling",
            uncertain_sampling["lower_95"] >= 0.15,
            "paired lower bound for uncertain minus known first sampling >= 0.15",
            **uncertain_sampling,
        ),
        _gate(
            "epistemic_value_drives_sampling",
            epistemic_ablation["lower_95"] >= 0.15,
            "paired lower bound for full minus epistemic-lesion sampling >= 0.15",
            **epistemic_ablation,
        ),
        _gate(
            "active_beats_random",
            active_random["lower_95"] >= 0.05,
            "paired viable-occupancy lower bound >= 0.05",
            **active_random,
        ),
        _gate(
            "active_beats_noop",
            active_noop["lower_95"] >= 0.05,
            "paired viable-occupancy lower bound >= 0.05",
            **active_noop,
        ),
        _gate(
            "scrambled_likelihood_harms_inference",
            scrambled_log_loss["lower_95"] >= 0.10,
            "paired log-loss increase lower bound >= 0.10 nats",
            **scrambled_log_loss,
        ),
        _gate(
            "preference_reversal_changes_action",
            action_tv >= 0.25,
            "action-distribution total variation >= 0.25",
            estimate=action_tv,
            active_distribution=active_actions,
            reversed_distribution=reversed_actions,
        ),
        _gate(
            "preference_reversal_reduces_viability",
            active_reversed["lower_95"] >= 0.15,
            "paired viable-occupancy lower bound >= 0.15",
            **active_reversed,
        ),
        _gate(
            "action_lesion_matches_noop",
            lesion_pathwise,
            "matched hidden-state and observation paths are bitwise identical",
        ),
        _gate(
            "oracle_upper_reference",
            oracle_active["estimate"] >= -0.01,
            "oracle mean viability is no more than 0.01 below active inference",
            **oracle_active,
        ),
    ]
    eligible = config.profile == "full"
    verdict = (
        "VALIDATION_PASS"
        if eligible and all(gate["passed"] for gate in gates)
        else "VALIDATION_FAIL"
        if eligible
        else "WORKFLOW_ONLY"
        if config.profile == "smoke"
        else "DEVELOPMENT_ONLY"
    )
    result = {
        "profile": config.profile,
        "eligible_for_validation_verdict": eligible,
        "verdict": verdict,
        "all_gates_pass": all(gate["passed"] for gate in gates),
        "gates": gates,
        "blanket": {"intact": blanket_intact, "blanket_break": blanket_broken},
        "homeostat_summaries": summaries,
        "fixed_feedback_is_descriptive_only": True,
        "claim_boundary": (
            "Engineered known-positive informational FEP laboratory; not thermodynamic "
            "free energy, emergent agency, GARD, plastic heredity, or prebiotic chemistry."
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "metrics.json", result)
    _write_figures(result, cells, output / "figures")
    _write_report(result, output / "REPORT.md")
    figure_names = sorted(
        str(path.relative_to(output)) for path in (output / "figures").glob("*.png")
    )
    seal_directory(output, ["metrics.json", "REPORT.md", *figure_names])
    return result


def _write_figures(
    result: dict[str, Any],
    cells: dict[tuple[str, str], dict[str, np.ndarray]],
    output: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output.mkdir(parents=True, exist_ok=True)
    intact = build_blanket_model("intact")
    figure, axis = plt.subplots(figsize=(5.2, 4.2))
    image = axis.imshow(intact.precision, cmap="coolwarm", vmin=-1.0, vmax=1.0)
    axis.set_xticks(range(4), intact.partition)
    axis.set_yticks(range(4), intact.partition)
    axis.set_title("Stationary precision matrix")
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    figure.savefig(output / "blanket_precision.png", dpi=160)
    plt.close(figure)

    times = np.linspace(0.0, 8.0, 161)
    external_impulse = impulse_response(intact, 0, times)
    internal_impulse = impulse_response(intact, 2, times)
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.8), sharey=True)
    for index, name in enumerate(intact.partition):
        axes[0].plot(times, external_impulse[:, index], label=name)
        axes[1].plot(times, internal_impulse[:, index], label=name)
    axes[0].set_title("Impulse at external state")
    axes[1].set_title("Impulse at internal state")
    for axis in axes:
        axis.set_xlabel("time")
    axes[0].set_ylabel("response")
    axes[1].legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output / "blanket_impulses.png", dpi=160)
    plt.close(figure)

    controllers = list(CONTROLLERS)
    viability = [
        result["homeostat_summaries"][f"disturbed--{name}"]["viable_fraction"]
        for name in controllers
    ]
    figure, axis = plt.subplots(figsize=(9.5, 4.2))
    axis.bar(range(len(controllers)), viability)
    axis.set_xticks(range(len(controllers)), controllers, rotation=35, ha="right")
    axis.set_ylim(0.0, 1.0)
    axis.set_ylabel("fraction in viable reservoir state")
    axis.set_title("Disturbed homeostat controller comparison")
    figure.tight_layout()
    figure.savefig(output / "controller_viability.png", dpi=160)
    plt.close(figure)

    sampling_labels = ("uncertain/full", "known/full", "uncertain/no epistemic")
    sampling = (
        result["homeostat_summaries"]["epistemic--active_inference"]["first_sample"],
        result["homeostat_summaries"]["known--active_inference"]["first_sample"],
        result["homeostat_summaries"]["epistemic--epistemic_lesion"]["first_sample"],
    )
    figure, axis = plt.subplots(figsize=(6.4, 4.0))
    axis.bar(range(3), sampling)
    axis.set_xticks(range(3), sampling_labels, rotation=20, ha="right")
    axis.set_ylim(0.0, 1.0)
    axis.set_ylabel("first-action sampling probability")
    axis.set_title("Epistemic sampling controls")
    figure.tight_layout()
    figure.savefig(output / "epistemic_sampling.png", dpi=160)
    plt.close(figure)

    trace = cells[("epistemic", "active_inference")]
    steps = np.arange(trace["states"].shape[1])
    lean = trace["beliefs"][0, :, :6].sum(axis=1)
    reservoir = (trace["states"][0] // 2) % 3
    figure, axes = plt.subplots(3, 1, figsize=(9.0, 6.5), sharex=True)
    axes[0].plot(steps, lean)
    axes[0].set_ylabel("P(lean)")
    axes[1].step(steps, reservoir, where="post")
    axes[1].set_ylabel("reservoir")
    axes[2].step(steps, trace["executed_actions"][0], where="post")
    axes[2].set_ylabel("action")
    axes[2].set_xlabel("timestep")
    figure.suptitle("Representative active-inference episode")
    figure.tight_layout()
    figure.savefig(output / "representative_episode.png", dpi=160)
    plt.close(figure)


def _write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# FEP Laboratory v1 Validation Report",
        "",
        f"**Profile:** `{result['profile']}`",
        "",
        f"**Verdict:** `{result['verdict']}`",
        "",
        "## Gate table",
        "",
        "| Gate | Outcome | Criterion |",
        "|---|---:|---|",
    ]
    for gate in result["gates"]:
        lines.append(
            f"| `{gate['name']}` | {'PASS' if gate['passed'] else 'FAIL'} | {gate['criterion']} |"
        )
    lines.extend(
        (
            "",
            "## Interpretation",
            "",
            "This capsule validates two deliberately engineered fixtures: an analytic "
            "stationary Gaussian Markov blanket and a discrete active-inference "
            "homeostat. The fixed-feedback controller is descriptive and is not a gate.",
            "",
            "## Claim boundary",
            "",
            result["claim_boundary"],
            "",
            "No GARD or plastic-heredity dynamics are imported or evaluated in v1.",
        )
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
