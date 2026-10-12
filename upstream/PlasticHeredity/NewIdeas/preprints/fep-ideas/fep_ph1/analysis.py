from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr

from fep_lab.integrity import read_json, seal_directory, write_json

from .config import ExperimentConfig
from .endpoints import episode_metrics


METRIC_NAMES = (
    "completion_fraction",
    "survival_to_horizon",
    "time_to_terminal",
    "growth_mean",
    "growth_cv",
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


def _finite_mean(values: np.ndarray) -> float | None:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    return float(np.mean(finite)) if finite.size else None


def _interval(
    values: np.ndarray, repetitions: int, rng: np.random.Generator
) -> dict[str, float | None]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"estimate": None, "lower_95": None, "upper_95": None, "n": 0}
    indices = rng.integers(0, len(finite), size=(repetitions, len(finite)))
    draws = np.mean(finite[indices], axis=1)
    return {
        "estimate": float(np.mean(finite)),
        "lower_95": float(np.quantile(draws, 0.025)),
        "upper_95": float(np.quantile(draws, 0.975)),
        "n": int(len(finite)),
    }


def _cell_rows(path: Path, config: ExperimentConfig) -> list[dict[str, Any]]:
    manifest = read_json(path.with_suffix(".json"))
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    controllers = [str(value) for value in arrays["controller_names"]]
    rows: list[dict[str, Any]] = []
    for controller_index, controller in enumerate(controllers):
        branch_metrics = []
        for branch in range(config.branches):
            episode = {
                name: value[controller_index, branch]
                for name, value in arrays.items()
                if name
                not in {
                    "controller_names",
                    "matrix_id",
                    "local_model_digest",
                    "threshold_alignment",
                    "threshold_growth",
                    "amplification_probe",
                }
            }
            branch_metrics.append(episode_metrics(episode, config.horizon))
        row: dict[str, Any] = {
            "matrix_id": int(manifest["matrix_id"]),
            "candidate": manifest["candidate"],
            "family": manifest["environment_family"],
            "channel": manifest["action_channel"],
            "regime": manifest["regime"],
            "severity": int(str(manifest["regime"]).split("-", 1)[0][1:]),
            "volatility": str(manifest["regime"]).split("-", 1)[1],
            "controller": controller,
            "amplification_probe": float(arrays["amplification_probe"][0]),
        }
        for metric in METRIC_NAMES:
            row[metric] = _finite_mean(
                np.asarray([values[metric] for values in branch_metrics], dtype=np.float64)
            )
        rows.append(row)
    return rows


def _save_matrix_rows(rows: list[dict[str, Any]], output: Path) -> None:
    categorical = (
        "candidate",
        "family",
        "channel",
        "regime",
        "volatility",
        "controller",
    )
    arrays: dict[str, np.ndarray] = {
        "matrix_id": np.asarray([row["matrix_id"] for row in rows], dtype=np.int32),
        "severity": np.asarray([row["severity"] for row in rows], dtype=np.int8),
        "amplification_probe": np.asarray(
            [row["amplification_probe"] for row in rows], dtype=np.float64
        ),
    }
    for name in categorical:
        arrays[name] = np.asarray([str(row[name]) for row in rows])
    for name in METRIC_NAMES:
        arrays[name] = np.asarray(
            [np.nan if row[name] is None else row[name] for row in rows],
            dtype=np.float64,
        )
    np.savez_compressed(output, **arrays)


def _group_summaries(
    rows: list[dict[str, Any]], config: ExperimentConfig
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(
            str(row[name])
            for name in ("candidate", "family", "channel", "regime", "controller")
        )
        groups[key].append(row)
    rng = np.random.default_rng(940_101)
    interval_metrics = {
        "completion_fraction",
        "inherited_fixed_fraction",
        "abstract_action_cost",
        "regime_log_loss",
        "f12",
        "strict8",
    }
    summaries = []
    for key, values in sorted(groups.items()):
        summary: dict[str, Any] = {
            "candidate": key[0],
            "family": key[1],
            "channel": key[2],
            "regime": key[3],
            "controller": key[4],
            "matrices": len(values),
            "metrics": {},
        }
        for metric in METRIC_NAMES:
            metric_values = np.asarray(
                [
                    np.nan if value[metric] is None else value[metric]
                    for value in values
                ],
                dtype=np.float64,
            )
            if metric in interval_metrics:
                summary["metrics"][metric] = _interval(
                    metric_values, config.bootstrap_repetitions, rng
                )
            else:
                finite = metric_values[np.isfinite(metric_values)]
                summary["metrics"][metric] = {
                    "estimate": float(np.mean(finite)) if finite.size else None,
                    "lower_95": None,
                    "upper_95": None,
                    "n": int(finite.size),
                }
        summaries.append(summary)
    return summaries


def _contrasts(
    rows: list[dict[str, Any]], config: ExperimentConfig
) -> list[dict[str, Any]]:
    index = {
        (
            row["matrix_id"],
            row["candidate"],
            row["family"],
            row["channel"],
            row["regime"],
            row["controller"],
        ): row
        for row in rows
    }
    comparisons = {
        "ai_pooled": (
            "reward_only_pooled",
            "yoked_random_pooled",
            "reactive",
            "noop",
        ),
        "ai_local": (
            "reward_only_local",
            "yoked_random_local",
            "reactive",
            "noop",
        ),
    }
    outcomes = (
        "completion_fraction",
        "inherited_fixed_fraction",
        "abstract_action_cost",
        "regime_log_loss",
        "f12",
        "strict8",
    )
    base_groups = sorted(
        {
            (
                row["candidate"],
                row["family"],
                row["channel"],
                row["regime"],
            )
            for row in rows
        }
    )
    rng = np.random.default_rng(940_102)
    output = []
    matrix_ids = sorted({int(row["matrix_id"]) for row in rows})
    for group in base_groups:
        for active, comparators in comparisons.items():
            for comparator in comparators:
                for outcome in outcomes:
                    differences = []
                    for matrix_id in matrix_ids:
                        left = index.get((matrix_id, *group, active))
                        right = index.get((matrix_id, *group, comparator))
                        if left is None or right is None:
                            continue
                        if left[outcome] is None or right[outcome] is None:
                            continue
                        differences.append(float(left[outcome] - right[outcome]))
                    output.append(
                        {
                            "candidate": group[0],
                            "family": group[1],
                            "channel": group[2],
                            "regime": group[3],
                            "active_controller": active,
                            "comparator": comparator,
                            "outcome": outcome,
                            **_interval(
                                np.asarray(differences, dtype=np.float64),
                                config.bootstrap_repetitions,
                                rng,
                            ),
                        }
                    )
    return output


def _dynamic_correlations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = {
        (
            row["matrix_id"],
            row["candidate"],
            row["family"],
            row["channel"],
            row["regime"],
            row["controller"],
        ): row
        for row in rows
    }
    groups = sorted(
        {
            (row["candidate"], row["family"], row["channel"], row["regime"])
            for row in rows
        }
    )
    output = []
    for group in groups:
        probe = []
        viability = []
        heredity = []
        for matrix_id in sorted({int(row["matrix_id"]) for row in rows}):
            active = index.get((matrix_id, *group, "ai_pooled"))
            noop = index.get((matrix_id, *group, "noop"))
            if active is None or noop is None:
                continue
            probe.append(float(active["amplification_probe"]))
            viability.append(
                float(active["completion_fraction"] - noop["completion_fraction"])
            )
            heredity.append(
                float(
                    active["inherited_fixed_fraction"]
                    - noop["inherited_fixed_fraction"]
                )
            )
        if len(probe) >= 3 and np.std(probe) > 0.0:
            viability_rho, viability_p = spearmanr(probe, viability)
            heredity_rho, heredity_p = spearmanr(probe, heredity)
            values = {
                "viability_rho": float(viability_rho),
                "viability_p_exploratory": float(viability_p),
                "heredity_rho": float(heredity_rho),
                "heredity_p_exploratory": float(heredity_p),
            }
        else:
            values = {
                "viability_rho": None,
                "viability_p_exploratory": None,
                "heredity_rho": None,
                "heredity_p_exploratory": None,
            }
        output.append(
            {
                "candidate": group[0],
                "family": group[1],
                "channel": group[2],
                "regime": group[3],
                "matrices": len(probe),
                **values,
            }
        )
    return output


def _figures(
    summaries: list[dict[str, Any]], contrasts: list[dict[str, Any]], output: Path
) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    active = [row for row in summaries if row["controller"] in ("ai_pooled", "ai_local")]
    figure, axis = plt.subplots(figsize=(7.2, 5.2))
    for controller, marker in (("ai_pooled", "o"), ("ai_local", "s")):
        selected = [row for row in active if row["controller"] == controller]
        axis.scatter(
            [row["metrics"]["abstract_action_cost"]["estimate"] for row in selected],
            [row["metrics"]["completion_fraction"]["estimate"] for row in selected],
            alpha=0.55,
            s=24,
            marker=marker,
            label=controller,
        )
    axis.set_xlabel("abstract action cost")
    axis.set_ylabel("completed-fission fraction")
    axis.set_title("Exploratory viability–cost map")
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "viability_cost.png", dpi=160)
    plt.close(figure)
    names.append("figures/viability_cost.png")

    selected = [
        row
        for row in contrasts
        if row["active_controller"] == "ai_pooled"
        and row["comparator"] == "reward_only_pooled"
        and row["outcome"] in ("completion_fraction", "inherited_fixed_fraction")
    ]
    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    x = np.arange(len(selected))
    estimates = [0.0 if row["estimate"] is None else row["estimate"] for row in selected]
    colors = [
        "tab:blue" if row["outcome"] == "completion_fraction" else "tab:orange"
        for row in selected
    ]
    axis.bar(x, estimates, color=colors, width=0.8)
    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.set_xticks([])
    axis.set_ylabel("active inference minus reward-only")
    axis.set_title("No-threshold exploratory controller contrasts")
    figure.tight_layout()
    figure.savefig(output / "ai_reward_contrasts.png", dpi=160)
    plt.close(figure)
    names.append("figures/ai_reward_contrasts.png")
    return names


def _report(metrics: dict[str, Any], output: Path) -> None:
    lines = [
        "# FEP–PH Experiment 1 exploratory atlas",
        "",
        f"- Integrity: **{metrics['decision']['integrity_verdict']}**",
        f"- Scientific status: **{metrics['decision']['scientific_status']}**",
        f"- Matrix-level controller rows: {metrics['matrix_rows']:,}",
        f"- Descriptive contrasts: {len(metrics['contrasts']):,}",
        "",
        "## Interpretation contract",
        "",
        "This atlas maps viability, ordinary compositional heredity, action cost, and belief quality across engineered environments. It has no positive/negative scientific classifier. Active inference, reward-only planning, reactive control, random action, no action, and oracle references remain separate.",
        "",
        "F12 and strict-8 are continuity readouts only. They were not preferences, fitting targets, actuator targets, scale-selection criteria, or gates.",
        "",
        "A favorable contrast would show engineered steering in reconstructed GARD. It would not show that unmodified GARD already performs active inference, that a Markov blanket emerged, that the controller is inherited, or that the model describes prebiotic chemistry.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze_atlas(
    config: ExperimentConfig, simulation: Path, output: Path
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted((simulation / "cells").glob("*.npz")):
        rows.extend(_cell_rows(path, config))
    if not rows:
        raise RuntimeError("FEP-PH1 analysis found no simulation cells")
    output.mkdir(parents=True, exist_ok=True)
    matrix_path = output / "matrix_metrics.npz"
    _save_matrix_rows(rows, matrix_path)
    summaries = _group_summaries(rows, config)
    contrasts = _contrasts(rows, config)
    dynamic = _dynamic_correlations(rows)
    decision = {
        "integrity_verdict": "VALID",
        "scientific_status": (
            "EXPLORATORY_ATLAS_COMPLETE"
            if config.profile == "full"
            else "WORKFLOW_ONLY"
        ),
        "positive_negative_classifier": None,
        "strict_events_are_descriptive_only": True,
    }
    metrics = {
        "schema": "fep-ph1-analysis-v1",
        "profile": config.profile,
        "matrix_rows": len(rows),
        "decision": decision,
        "group_summaries": summaries,
        "contrasts": contrasts,
        "dynamic_regime_correlations": dynamic,
        "claim_boundary": (
            "Engineered active-inference steering map in reconstructed GARD; not "
            "intrinsic GARD inference, emergent blankets, inherited controllers, "
            "prebiotic chemistry, or a universal FEP mechanism."
        ),
    }
    write_json(output / "metrics.json", metrics)
    figure_names = _figures(summaries, contrasts, output / "figures")
    _report(metrics, output / "REPORT.md")
    seal_directory(
        output,
        ["metrics.json", "matrix_metrics.npz", "REPORT.md", *figure_names],
    )
    return metrics
