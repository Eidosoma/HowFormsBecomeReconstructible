from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.stats import spearmanr

from fep_lab.integrity import read_json, seal_directory, write_json

from .config import ExperimentConfig
from .endpoints import episode_metrics


METRICS = (
    "completion_fraction", "survival_to_horizon", "time_to_terminal",
    "growth_mean", "growth_cv", "recovery_after_shock",
    "inherited_fixed_fraction", "inherited_observed_fraction",
    "longest_inherited_run", "turnover", "anchor_decay",
    "abstract_action_cost", "physical_action_cost", "sample_fraction",
    "adapt_fraction", "regime_log_loss", "regime_brier", "mean_vfe",
    "mean_state_information_gain", "f12", "strict8",
)

PRIMARY_METRICS = (
    "completion_fraction", "survival_to_horizon", "growth_mean",
    "recovery_after_shock", "inherited_fixed_fraction",
    "inherited_observed_fraction", "longest_inherited_run", "turnover",
    "abstract_action_cost", "physical_action_cost", "regime_log_loss", "regime_brier",
)


def _finite_mean(values: list[float]) -> float | None:
    array = np.asarray(values, dtype=np.float64)
    array = array[np.isfinite(array)]
    return float(array.mean()) if array.size else None


def safe_spearman(left: np.ndarray, right: np.ndarray) -> dict[str, Any]:
    x = np.asarray(left, dtype=np.float64)
    y = np.asarray(right, dtype=np.float64)
    if x.shape != y.shape:
        raise ValueError("correlation inputs have different shapes")
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    reason = None
    if x.size < 3:
        reason = "insufficient_pairs"
    elif np.all(x == x[0]):
        reason = "constant_predictor"
    elif np.all(y == y[0]):
        reason = "constant_outcome"
    if reason is not None:
        return {"rho": None, "p_exploratory": None, "pairs": int(x.size), "undefined_reason": reason}
    rho, probability = spearmanr(x, y)
    if not (np.isfinite(rho) and np.isfinite(probability)):
        return {"rho": None, "p_exploratory": None, "pairs": int(x.size), "undefined_reason": "undefined_by_scipy"}
    return {"rho": float(rho), "p_exploratory": float(probability), "pairs": int(x.size), "undefined_reason": None}


def _cell_rows(path: Path, config: ExperimentConfig) -> list[dict[str, Any]]:
    manifest = read_json(path.with_suffix(".json"))
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    rows = []
    controllers = [str(value) for value in arrays["controller_names"]]
    excluded = {"controller_names", "matrix_id", "local_model_digest", "threshold_alignment", "threshold_growth", "growth_budget"}
    for controller_index, controller in enumerate(controllers):
        branch_values = []
        for branch in range(config.branches):
            episode = {name: value[controller_index, branch] for name, value in arrays.items() if name not in excluded}
            branch_values.append(episode_metrics(episode, config.horizon))
        row: dict[str, Any] = {
            "matrix_id": int(manifest["matrix_id"]),
            "candidate": manifest["candidate"], "family": manifest["family"],
            "channel": manifest["channel"], "tier": manifest["tier"],
            "volatility": manifest["volatility"], "controller": controller,
            "growth_budget": int(manifest["growth_budget"]),
            "actionability": manifest["actionability"],
            "actuator_polarity": manifest["actuator_polarity"],
            "molecular_dose": int(manifest["molecular_dose"]),
        }
        for metric in METRICS:
            row[metric] = _finite_mean([value[metric] for value in branch_values])
        rows.append(row)
    return rows


def _save_rows(rows: list[dict[str, Any]], path: Path) -> None:
    categorical = ("candidate", "family", "channel", "tier", "volatility", "controller", "actionability", "actuator_polarity")
    arrays: dict[str, np.ndarray] = {
        "matrix_id": np.asarray([row["matrix_id"] for row in rows], dtype=np.int32),
        "growth_budget": np.asarray([row["growth_budget"] for row in rows], dtype=np.int32),
        "molecular_dose": np.asarray([row["molecular_dose"] for row in rows], dtype=np.int8),
    }
    for name in categorical:
        arrays[name] = np.asarray([str(row[name]) for row in rows])
    for name in METRICS:
        arrays[name] = np.asarray([np.nan if row[name] is None else row[name] for row in rows], dtype=np.float64)
    np.savez_compressed(path, **arrays)


def _bootstrap(values: list[float], repetitions: int, rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"estimate": None, "lower_95": None, "upper_95": None, "n_matrices": 0, "p_exploratory": None}, np.asarray([])
    draws = finite[rng.integers(0, len(finite), size=(repetitions, len(finite)))].mean(axis=1)
    probability = min(1.0, 2.0 * min((np.count_nonzero(draws <= 0) + 1) / (repetitions + 1), (np.count_nonzero(draws >= 0) + 1) / (repetitions + 1)))
    return {
        "estimate": float(finite.mean()), "lower_95": float(np.quantile(draws, 0.025)),
        "upper_95": float(np.quantile(draws, 0.975)), "n_matrices": int(finite.size),
        "p_exploratory": float(probability),
    }, draws


def _strata() -> tuple[tuple[str, Callable[[dict[str, Any]], bool]], ...]:
    values: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [("overall", lambda row: True)]
    for field, categories in (
        ("candidate", ("02", "03")), ("family", ("nutrient", "catalytic")),
        ("channel", ("uptake", "molecular")), ("tier", ("transition", "hard")),
        ("volatility", ("slow", "fast")),
        ("actionability", ("ACTIONABLE", "MIXED", "NON_ACTIONABLE")),
    ):
        for category in categories:
            values.append((f"{field}={category}", lambda row, f=field, c=category: row[f] == c))
    return tuple(values)


def _paired_matrix_values(
    rows: list[dict[str, Any]], left: str, right: str, outcome: str,
    predicate: Callable[[dict[str, Any]], bool],
) -> list[float]:
    selected = [row for row in rows if predicate(row)]
    key_fields = ("matrix_id", "candidate", "family", "channel", "tier", "volatility")
    index = {tuple(row[name] for name in key_fields) + (row["controller"],): row for row in selected}
    by_matrix: dict[int, list[float]] = defaultdict(list)
    for key in sorted({tuple(row[name] for name in key_fields) for row in selected}):
        lvalue = index.get(key + (left,))
        rvalue = index.get(key + (right,))
        if lvalue is None or rvalue is None or lvalue[outcome] is None or rvalue[outcome] is None:
            continue
        by_matrix[int(key[0])].append(float(lvalue[outcome] - rvalue[outcome]))
    return [float(np.mean(values)) for _matrix, values in sorted(by_matrix.items()) if values]


def _interaction_values(
    rows: list[dict[str, Any]], outcome: str, predicate: Callable[[dict[str, Any]], bool]
) -> list[float]:
    pairs = (
        ("balanced_ai_local", "balanced_reward_local"),
        ("growth_ai_local", "growth_reward_local"),
    )
    selected = [row for row in rows if predicate(row)]
    key_fields = ("matrix_id", "candidate", "family", "channel", "tier", "volatility")
    index = {tuple(row[name] for name in key_fields) + (row["controller"],): row for row in selected}
    by_matrix: dict[int, list[float]] = defaultdict(list)
    for key in sorted({tuple(row[name] for name in key_fields) for row in selected}):
        values = [index.get(key + (name,)) for pair in pairs for name in pair]
        if any(value is None or value[outcome] is None for value in values):
            continue
        effect = (float(values[0][outcome]) - float(values[1][outcome])) - (float(values[2][outcome]) - float(values[3][outcome]))  # type: ignore[index]
        by_matrix[int(key[0])].append(effect)
    return [float(np.mean(values)) for _matrix, values in sorted(by_matrix.items()) if values]


def _bh(rows: list[dict[str, Any]]) -> None:
    eligible = [(index, float(row["p_exploratory"])) for index, row in enumerate(rows) if row.get("p_exploratory") is not None]
    m = len(eligible)
    adjusted: dict[int, float] = {}
    running = 1.0
    for rank_from_end, (index, probability) in enumerate(sorted(eligible, key=lambda item: item[1], reverse=True), start=1):
        rank = m - rank_from_end + 1
        running = min(running, probability * m / rank)
        adjusted[index] = min(1.0, running)
    for index, row in enumerate(rows):
        row["q_bh_exploratory"] = adjusted.get(index)


def _contrasts(rows: list[dict[str, Any]], config: ExperimentConfig) -> list[dict[str, Any]]:
    comparisons = (
        ("balanced_ai_local", "balanced_reward_local", "epistemic_local"),
        ("balanced_ai_local", "balanced_yoked_random_local", "yoked_timing"),
        ("balanced_ai_local", "reactive", "reactive"),
        ("balanced_ai_local", "noop", "noop"),
        ("balanced_ai_local", "growth_ai_local", "balanced_vs_growth_ai"),
        ("balanced_reward_local", "growth_reward_local", "balanced_vs_growth_reward"),
        ("balanced_ai_pooled", "balanced_ai_local", "pooled_vs_local_ai"),
        ("balanced_reward_pooled", "balanced_reward_local", "pooled_vs_local_reward"),
    )
    rng = np.random.default_rng(1_507_301)
    output = []
    for stratum, predicate in _strata():
        for left, right, label in comparisons:
            for outcome in PRIMARY_METRICS:
                interval, _draws = _bootstrap(_paired_matrix_values(rows, left, right, outcome, predicate), config.bootstrap_repetitions, rng)
                output.append({"stratum": stratum, "contrast": label, "left": left, "right": right, "outcome": outcome, **interval})
        for outcome in PRIMARY_METRICS:
            interval, _draws = _bootstrap(_interaction_values(rows, outcome, predicate), config.bootstrap_repetitions, rng)
            output.append({"stratum": stratum, "contrast": "preference_by_epistemic_interaction", "left": None, "right": None, "outcome": outcome, **interval})
    _bh(output)
    return output


def _summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    fields = ("candidate", "family", "channel", "tier", "volatility", "actionability", "controller")
    for row in rows:
        grouped[tuple(str(row[name]) for name in fields)].append(row)
    output = []
    for key, values in sorted(grouped.items()):
        output.append({
            **dict(zip(fields, key, strict=True)),
            "matrices": len(values),
            "metrics": {metric: _finite_mean([float("nan") if value[metric] is None else float(value[metric]) for value in values]) for metric in METRICS},
        })
    return output


def _pareto(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in summaries:
        groups[(row["candidate"], row["family"], row["channel"], row["tier"], row["volatility"])].append(row)
    output = []
    for group, candidates in sorted(groups.items()):
        usable = [row for row in candidates if all(row["metrics"].get(name) is not None for name in ("survival_to_horizon", "inherited_fixed_fraction", "abstract_action_cost"))]
        for row in usable:
            v = row["metrics"]
            dominated = any(
                other is not row
                and other["metrics"]["survival_to_horizon"] >= v["survival_to_horizon"]
                and other["metrics"]["inherited_fixed_fraction"] >= v["inherited_fixed_fraction"]
                and other["metrics"]["abstract_action_cost"] <= v["abstract_action_cost"]
                and (
                    other["metrics"]["survival_to_horizon"] > v["survival_to_horizon"]
                    or other["metrics"]["inherited_fixed_fraction"] > v["inherited_fixed_fraction"]
                    or other["metrics"]["abstract_action_cost"] < v["abstract_action_cost"]
                )
                for other in usable
            )
            if not dominated:
                output.append({"candidate": group[0], "family": group[1], "channel": group[2], "tier": group[3], "volatility": group[4], "controller": row["controller"], "survival": v["survival_to_horizon"], "inheritance": v["inherited_fixed_fraction"], "cost": v["abstract_action_cost"]})
    return output


def _screen_correlations(rows: list[dict[str, Any]], screen_root: Path) -> list[dict[str, Any]]:
    gains: dict[tuple[str, str, str], float] = {}
    for path in sorted((screen_root / "cells").glob("*.json")):
        payload = read_json(path)
        actuator = payload["actuator"]
        gains[(payload["candidate"], payload["family"], payload["channel"])] = 0.5 * (float(actuator["oracle_gain_transition"]) + float(actuator["oracle_gain_hard"]))
    output = []
    for outcome in ("completion_fraction", "inherited_fixed_fraction"):
        screen_values, effects = [], []
        for key, gain in sorted(gains.items()):
            selected = [row for row in rows if (row["candidate"], row["family"], row["channel"]) == key]
            values = _paired_matrix_values(selected, "balanced_ai_local", "noop", outcome, lambda row: True)
            if values:
                screen_values.append(gain)
                effects.append(float(np.mean(values)))
        output.append({"outcome": outcome, **safe_spearman(np.asarray(screen_values), np.asarray(effects))})
    return output


def _figures(summaries: list[dict[str, Any]], output: Path) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output.mkdir(parents=True, exist_ok=True)
    selected = [row for row in summaries if row["controller"] in {"balanced_ai_local", "growth_ai_local", "noop"}]
    figure, axis = plt.subplots(figsize=(7.2, 5.2))
    for controller, marker in (("balanced_ai_local", "o"), ("growth_ai_local", "s"), ("noop", "x")):
        values = [row for row in selected if row["controller"] == controller]
        axis.scatter([row["metrics"]["inherited_fixed_fraction"] for row in values], [row["metrics"]["survival_to_horizon"] for row in values], label=controller, marker=marker, alpha=0.6)
    axis.set_xlabel("ordinary inherited-boundary fraction")
    axis.set_ylabel("survival through horizon")
    axis.set_title("FEP–PH1.5 survival–heredity atlas")
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output / "survival_heredity.png", dpi=160)
    plt.close(figure)
    return ["figures/survival_heredity.png"]


def analyze_atlas(config: ExperimentConfig, simulation: Path, screen_root: Path, output: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted((simulation / "cells").glob("*.npz")):
        rows.extend(_cell_rows(path, config))
    if not rows:
        raise RuntimeError("FEP-PH1.5 found no evaluation rows")
    output.mkdir(parents=True, exist_ok=True)
    _save_rows(rows, output / "matrix_metrics.npz")
    summaries = _summaries(rows)
    contrasts = _contrasts(rows, config)
    metrics = {
        "schema": "fep-ph15-analysis-v1", "profile": config.profile,
        "matrix_rows": len(rows),
        "decision": {
            "integrity_verdict": "VALID",
            "scientific_status": "EXPLORATORY_ATLAS_COMPLETE" if config.profile == "full" else "WORKFLOW_ONLY",
            "positive_negative_classifier": None,
            "strict_events_are_held_out_descriptive_only": True,
        },
        "group_summaries": summaries,
        "paired_bootstrap_contrasts": contrasts,
        "screen_gain_correlations": _screen_correlations(rows, screen_root),
        "survival_inheritance_cost_pareto": _pareto(summaries),
        "claim_boundary": "Engineered goal-aligned steering in reconstructed GARD only; not intrinsic GARD active inference, inherited generative models, emergent blankets, prebiotic chemistry, or a universal FEP mechanism.",
    }
    write_json(output / "metrics.json", metrics)
    report = (
        "# FEP–PH Experiment 1.5 exploratory atlas\n\n"
        f"- Integrity: **{metrics['decision']['integrity_verdict']}**\n"
        f"- Scientific status: **{metrics['decision']['scientific_status']}**\n"
        f"- Matrix-level controller rows: {len(rows):,}\n\n"
        "This atlas asks whether active inference becomes useful when the physical actuators and ordinary survival/heredity goals are deliberately aligned. It has no global supported/not-supported classifier. F12 and strict-8 are held-out descriptive outcomes.\n\n"
        "Any favorable result supports engineered steering in these reconstructed simulators. It does not show that unmodified GARD already performs active inference or that its controller, blanket, or goals are chemically inherited.\n"
    )
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    figures = _figures(summaries, output / "figures")
    seal_directory(output, ["matrix_metrics.npz", "metrics.json", "REPORT.md", *figures])
    return metrics

