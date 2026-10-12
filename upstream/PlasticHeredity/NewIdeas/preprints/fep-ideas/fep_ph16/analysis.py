from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np

from fep_lab.integrity import read_json, seal_directory, write_json
from fep_ph15.endpoints import episode_metrics

from .config import ExperimentConfig
from .types import ControllerName


BASE_METRICS = (
    "completion_fraction",
    "survival_to_horizon",
    "time_to_terminal",
    "growth_mean",
    "growth_cv",
    "recovery_after_shock",
    "inherited_fixed_fraction",
    "inherited_observed_fraction",
    "longest_inherited_run",
    "turnover",
    "anchor_decay",
    "abstract_action_cost",
    "physical_action_cost",
    "sample_fraction",
    "adapt_fraction",
    "regime_log_loss",
    "regime_brier",
    "mean_vfe",
    "mean_state_information_gain",
    "f12",
    "strict8",
)
EXTRA_METRICS = (
    "inherited_completion_fraction",
    "mean_planning_fissions",
    "total_planning_fissions",
    "mean_model_entropy",
    "mean_action_entropy",
)
METRICS = BASE_METRICS + EXTRA_METRICS
PRIMARY_OUTCOMES = (
    "inherited_completion_fraction",
    "completion_fraction",
    "survival_to_horizon",
    "recovery_after_shock",
    "abstract_action_cost",
)


COMPARISONS = (
    (
        ControllerName.PHYSICAL_ORACLE,
        ControllerName.NOOP,
        "physical_oracle_vs_noop",
    ),
    (
        ControllerName.RICH_REWARD,
        ControllerName.NOOP,
        "rich_reward_vs_noop",
    ),
    (
        ControllerName.RICH_REWARD,
        ControllerName.COARSE_REWARD,
        "rich_body_vs_coarse_model",
    ),
    (
        ControllerName.RICH_EFE,
        ControllerName.RICH_REWARD,
        "epistemic_value_given_rich_model",
    ),
    (
        ControllerName.RICH_EFE,
        ControllerName.RICH_EFE_YOKED,
        "rich_efe_timing_vs_exact_multiset_yoke",
    ),
    (
        ControllerName.RICH_EFE,
        ControllerName.RICH_EFE_SHUFFLED,
        "rich_efe_vs_shuffled_action_semantics",
    ),
    (
        ControllerName.CATEGORICAL_ORACLE,
        ControllerName.CATEGORICAL_AI,
        "true_regime_categorical_oracle_vs_reference",
    ),
    (
        ControllerName.REACTIVE,
        ControllerName.NOOP,
        "reactive_vs_noop",
    ),
)


def _finite_mean(values: list[float]) -> float | None:
    array = np.asarray(values, dtype=np.float64)
    array = array[np.isfinite(array)]
    return float(array.mean()) if array.size else None


def _entropy_rows(values: np.ndarray) -> float:
    array = np.asarray(values, dtype=np.float64)
    valid = np.all(np.isfinite(array), axis=1) & (array.sum(axis=1) > 0.0)
    if not np.any(valid):
        return float("nan")
    probability = array[valid] / array[valid].sum(axis=1, keepdims=True)
    probability = np.maximum(probability, 1.0e-300)
    return float(np.mean(-np.sum(probability * np.log(probability), axis=1)))


def _episode_values(episode: dict[str, np.ndarray], horizon: int) -> dict[str, float]:
    output = episode_metrics(episode, horizon)
    output["inherited_completion_fraction"] = output["inherited_fixed_fraction"]
    planning = np.asarray(episode["planning_fissions"], dtype=np.float64)
    output["mean_planning_fissions"] = float(np.mean(planning))
    output["total_planning_fissions"] = float(np.sum(planning))
    output["mean_model_entropy"] = _entropy_rows(episode["model_weights"])
    output["mean_action_entropy"] = _entropy_rows(episode["action_probabilities"])
    return output


def _cell_rows(path: Path, config: ExperimentConfig) -> list[dict[str, Any]]:
    manifest = read_json(path.with_suffix(".json"))
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    controllers = [str(value) for value in arrays["controller_names"]]
    excluded = {
        "controller_names",
        "matrix_id",
        "growth_budget",
        "coarse_offsets",
        "rich_offsets",
    }
    output: list[dict[str, Any]] = []
    for controller_index, controller in enumerate(controllers):
        branch_metrics = []
        for branch in range(config.branches):
            episode = {
                name: value[controller_index, branch]
                for name, value in arrays.items()
                if name not in excluded
            }
            branch_metrics.append(_episode_values(episode, config.horizon))
        row: dict[str, Any] = {
            "matrix_id": int(manifest["matrix_id"]),
            "candidate": str(manifest["candidate"]),
            "family": str(manifest["family"]),
            "channel": str(manifest["channel"]),
            "tier": str(manifest["tier"]),
            "volatility": str(manifest["volatility"]),
            "actionability": str(manifest["actionability"]),
            "mechanism": str(manifest["mechanism"]),
            "controller": controller,
            "growth_budget": int(manifest["growth_budget"]),
        }
        for metric in METRICS:
            row[metric] = _finite_mean([value[metric] for value in branch_metrics])
        output.append(row)
    return output


def _save_rows(rows: list[dict[str, Any]], path: Path) -> None:
    categorical = (
        "candidate",
        "family",
        "channel",
        "tier",
        "volatility",
        "actionability",
        "mechanism",
        "controller",
    )
    arrays: dict[str, np.ndarray] = {
        "matrix_id": np.asarray([row["matrix_id"] for row in rows], dtype=np.int32),
        "growth_budget": np.asarray([row["growth_budget"] for row in rows], dtype=np.int32),
    }
    for name in categorical:
        arrays[name] = np.asarray([str(row[name]) for row in rows])
    for name in METRICS:
        arrays[name] = np.asarray(
            [np.nan if row[name] is None else row[name] for row in rows],
            dtype=np.float64,
        )
    np.savez_compressed(path, **arrays)


def _strata() -> tuple[tuple[str, Callable[[dict[str, Any]], bool]], ...]:
    output: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("overall", lambda _row: True)
    ]
    for field, categories in (
        ("candidate", ("02", "03")),
        ("family", ("nutrient", "catalytic")),
        ("channel", ("uptake", "molecular")),
        ("tier", ("transition", "hard")),
        ("volatility", ("slow", "fast")),
        ("actionability", ("ACTIONABLE", "MIXED", "NON_ACTIONABLE")),
    ):
        for category in categories:
            output.append(
                (
                    f"{field}={category}",
                    lambda row, f=field, c=category: row[f] == c,
                )
            )
    return tuple(output)


def _paired_matrix_values(
    rows: list[dict[str, Any]],
    left: str,
    right: str,
    outcome: str,
    predicate: Callable[[dict[str, Any]], bool],
) -> list[float]:
    selected = [row for row in rows if predicate(row)]
    key_fields = (
        "matrix_id",
        "candidate",
        "family",
        "channel",
        "tier",
        "volatility",
    )
    index = {
        tuple(row[name] for name in key_fields) + (row["controller"],): row
        for row in selected
    }
    by_matrix: dict[int, list[float]] = defaultdict(list)
    condition_keys = sorted(
        {tuple(row[name] for name in key_fields) for row in selected}
    )
    for key in condition_keys:
        left_row = index.get(key + (left,))
        right_row = index.get(key + (right,))
        if left_row is None or right_row is None:
            continue
        left_value, right_value = left_row[outcome], right_row[outcome]
        if left_value is None or right_value is None:
            continue
        difference = float(left_value) - float(right_value)
        if np.isfinite(difference):
            by_matrix[int(key[0])].append(difference)
    return [
        float(np.mean(values))
        for _matrix, values in sorted(by_matrix.items())
        if values
    ]


def _bootstrap(
    values: list[float], repetitions: int, rng: np.random.Generator
) -> dict[str, Any]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {
            "estimate": None,
            "lower_95": None,
            "upper_95": None,
            "n_matrices": 0,
            "p_exploratory": None,
        }
    draws = finite[
        rng.integers(0, len(finite), size=(repetitions, len(finite)))
    ].mean(axis=1)
    probability = min(
        1.0,
        2.0
        * min(
            (np.count_nonzero(draws <= 0.0) + 1) / (repetitions + 1),
            (np.count_nonzero(draws >= 0.0) + 1) / (repetitions + 1),
        ),
    )
    return {
        "estimate": float(finite.mean()),
        "lower_95": float(np.quantile(draws, 0.025)),
        "upper_95": float(np.quantile(draws, 0.975)),
        "n_matrices": int(finite.size),
        "p_exploratory": float(probability),
    }


def _bh(rows: list[dict[str, Any]]) -> None:
    eligible = [
        (index, float(row["p_exploratory"]))
        for index, row in enumerate(rows)
        if row.get("p_exploratory") is not None
    ]
    total = len(eligible)
    adjusted: dict[int, float] = {}
    running = 1.0
    for rank_from_end, (index, probability) in enumerate(
        sorted(eligible, key=lambda item: item[1], reverse=True), start=1
    ):
        rank = total - rank_from_end + 1
        running = min(running, probability * total / rank)
        adjusted[index] = min(1.0, running)
    for index, row in enumerate(rows):
        row["q_bh_exploratory"] = adjusted.get(index)


def _contrasts(rows: list[dict[str, Any]], config: ExperimentConfig) -> list[dict[str, Any]]:
    rng = np.random.default_rng(1_606_301)
    output: list[dict[str, Any]] = []
    for stratum, predicate in _strata():
        for left, right, label in COMPARISONS:
            for outcome in PRIMARY_OUTCOMES:
                output.append(
                    {
                        "stratum": stratum,
                        "contrast": label,
                        "left": str(left),
                        "right": str(right),
                        "outcome": outcome,
                        **_bootstrap(
                            _paired_matrix_values(
                                rows, str(left), str(right), outcome, predicate
                            ),
                            config.bootstrap_repetitions,
                            rng,
                        ),
                    }
                )
    _bh(output)
    return output


def _summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "candidate",
        "family",
        "channel",
        "tier",
        "volatility",
        "actionability",
        "controller",
    )
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row[name]) for name in fields)].append(row)
    output = []
    for key, values in sorted(grouped.items()):
        output.append(
            {
                **dict(zip(fields, key, strict=True)),
                "matrices": len(values),
                "metrics": {
                    metric: _finite_mean(
                        [
                            float("nan") if value[metric] is None else float(value[metric])
                            for value in values
                        ]
                    )
                    for metric in METRICS
                },
            }
        )
    return output


def _pareto(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in summaries:
        grouped[
            (
                row["candidate"],
                row["family"],
                row["channel"],
                row["tier"],
                row["volatility"],
            )
        ].append(row)
    output = []
    for group, candidates in sorted(grouped.items()):
        usable = [
            row
            for row in candidates
            if all(
                row["metrics"].get(name) is not None
                for name in (
                    "completion_fraction",
                    "inherited_completion_fraction",
                    "abstract_action_cost",
                )
            )
        ]
        for row in usable:
            value = row["metrics"]
            dominated = any(
                other is not row
                and other["metrics"]["completion_fraction"]
                >= value["completion_fraction"]
                and other["metrics"]["inherited_completion_fraction"]
                >= value["inherited_completion_fraction"]
                and other["metrics"]["abstract_action_cost"]
                <= value["abstract_action_cost"]
                and (
                    other["metrics"]["completion_fraction"]
                    > value["completion_fraction"]
                    or other["metrics"]["inherited_completion_fraction"]
                    > value["inherited_completion_fraction"]
                    or other["metrics"]["abstract_action_cost"]
                    < value["abstract_action_cost"]
                )
                for other in usable
            )
            if not dominated:
                output.append(
                    {
                        "candidate": group[0],
                        "family": group[1],
                        "channel": group[2],
                        "tier": group[3],
                        "volatility": group[4],
                        "controller": row["controller"],
                        "completion": value["completion_fraction"],
                        "inherited_completion": value[
                            "inherited_completion_fraction"
                        ],
                        "cost": value["abstract_action_cost"],
                    }
                )
    return output


def _model_diagnostics(fit_root: Path) -> list[dict[str, Any]]:
    output = []
    for path in sorted((fit_root / "causal").glob("*.json")):
        payload = read_json(path)
        output.append(
            {
                "mechanism": payload["mechanism"],
                "model": payload["model"],
                "ridge_lambda": payload["summary"]["ridge_lambda"],
                "cross_validation": payload["summary"]["cross_validation"],
                "rows": payload["training_rows"],
            }
        )
    return output


def _calibration_diagnostics(simulation: Path) -> dict[str, Any]:
    coarse_norms, rich_norms, rows = [], [], []
    for path in sorted((simulation / "cells").glob("*.json")):
        payload = read_json(path)
        rows.append(int(payload["calibration_rows"]))
        with np.load(path.with_suffix(".npz"), allow_pickle=False) as archive:
            coarse_norms.append(float(np.linalg.norm(archive["coarse_offsets"])))
            rich_norms.append(float(np.linalg.norm(archive["rich_offsets"])))
    return {
        "cells": len(rows),
        "calibration_rows_per_cell": _finite_mean([float(value) for value in rows]),
        "mean_coarse_offset_norm": _finite_mean(coarse_norms),
        "mean_rich_offset_norm": _finite_mean(rich_norms),
    }


def _figures(summaries: list[dict[str, Any]], output: Path) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output.mkdir(parents=True, exist_ok=True)
    selected_names = {
        str(ControllerName.NOOP),
        str(ControllerName.PHYSICAL_ORACLE),
        str(ControllerName.COARSE_REWARD),
        str(ControllerName.RICH_REWARD),
        str(ControllerName.RICH_EFE),
    }
    selected = [row for row in summaries if row["controller"] in selected_names]
    figure, axis = plt.subplots(figsize=(7.4, 5.4))
    for controller in sorted(selected_names):
        values = [row for row in selected if row["controller"] == controller]
        axis.scatter(
            [row["metrics"]["inherited_completion_fraction"] for row in values],
            [row["metrics"]["completion_fraction"] for row in values],
            label=controller,
            alpha=0.6,
            s=28,
        )
    axis.set_xlabel("inherited completion fraction")
    axis.set_ylabel("completion fraction")
    axis.set_title("FEP–PH1.6 causal body-model oracle ladder")
    axis.legend(fontsize=6)
    figure.tight_layout()
    figure.savefig(output / "causal_ladder.png", dpi=160)
    plt.close(figure)
    return ["figures/causal_ladder.png"]


def analyze_atlas(
    config: ExperimentConfig, simulation: Path, fit_root: Path, output: Path
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted((simulation / "cells").glob("*.npz")):
        rows.extend(_cell_rows(path, config))
    if not rows:
        raise RuntimeError("FEP-PH1.6 found no evaluation rows")
    expected = config.evaluation_matrices * 24 * 10
    if len(rows) != expected:
        raise RuntimeError(f"expected {expected} matrix-controller rows, found {len(rows)}")
    output.mkdir(parents=True, exist_ok=True)
    _save_rows(rows, output / "matrix_metrics.npz")
    summaries = _summaries(rows)
    contrasts = _contrasts(rows, config)
    metrics = {
        "schema": "fep-ph16-analysis-v1",
        "profile": config.profile,
        "matrix_controller_rows": len(rows),
        "decision": {
            "integrity_verdict": "VALID",
            "scientific_status": (
                "EXPLORATORY_CAUSAL_BODY_MODEL_ATLAS_COMPLETE"
                if config.profile == "full"
                else "WORKFLOW_ONLY"
            ),
            "positive_negative_classifier": None,
            "primary_outcome": "inherited_completion_fraction",
            "strict_events_are_held_out_descriptive_only": True,
        },
        "causal_ladder": [str(value) for value in ControllerName],
        "group_summaries": summaries,
        "paired_matrix_bootstrap_contrasts": contrasts,
        "causal_model_cross_validation": _model_diagnostics(fit_root),
        "calibration_diagnostics": _calibration_diagnostics(simulation),
        "survival_inheritance_cost_pareto": _pareto(summaries),
        "heldout_event_description": {
            "mean_f12": _finite_mean([float(row["f12"]) for row in rows]),
            "mean_strict8": _finite_mean([float(row["strict8"]) for row in rows]),
            "used_for_fitting_or_control": False,
        },
        "claim_boundary": (
            "Engineered causal body-model steering and a diagnostic physical oracle in "
            "reconstructed GARD only; not intrinsic GARD active inference, inherited "
            "generative models, emergent blankets, prebiotic chemistry, or a universal FEP mechanism."
        ),
    }
    write_json(output / "metrics.json", metrics)
    overall = [row for row in contrasts if row["stratum"] == "overall"]
    report_lines = [
        "# FEP–PH Experiment 1.6 exploratory causal body-model atlas",
        "",
        f"- Integrity: **{metrics['decision']['integrity_verdict']}**",
        f"- Scientific status: **{metrics['decision']['scientific_status']}**",
        f"- Matrix-controller rows: {len(rows):,}",
        "- Global supported/not-supported verdict: **none (exploratory)**",
        "",
        "## Overall frozen contrasts",
        "",
        "| Contrast | Outcome | Estimate | 95% bootstrap interval |",
        "|---|---:|---:|---:|",
    ]
    for row in overall:
        if row["estimate"] is None:
            estimate = interval = "NA"
        else:
            estimate = f"{row['estimate']:.6f}"
            interval = f"[{row['lower_95']:.6f}, {row['upper_95']:.6f}]"
        report_lines.append(
            f"| {row['contrast']} | {row['outcome']} | {estimate} | {interval} |"
        )
    report_lines.extend(
        (
            "",
            "The physical rollout oracle is a bounded, privileged-state diagnostic on "
            "isolated planning RNG streams, not a guaranteed upper bound. Every learned controller remains "
            "blanket-limited. Favorable results therefore locate controller/model bottlenecks; "
            "they do not establish intrinsic inference by GARD.",
            "",
            "F12 and strict-8 remain held-out descriptive outcomes and cannot determine any "
            "claim in this atlas.",
            "",
        )
    )
    (output / "REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")
    figures = _figures(summaries, output / "figures")
    seal_directory(
        output,
        ["matrix_metrics.npz", "metrics.json", "REPORT.md", *figures],
    )
    return metrics
