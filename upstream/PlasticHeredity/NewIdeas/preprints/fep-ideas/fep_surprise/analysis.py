from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
from sklearn.metrics import average_precision_score

from . import compat as _compat  # noqa: F401
from .config import CampaignConfig
from .landscape import LandscapeEnsemble
from .predictor import FrozenPredictor, log_loss, select_c_and_fit
from .worker import BASELINE_FEATURE_NAMES, ESTIMATORS, SURPRISE_FEATURE_NAMES, load_cell
from plastic_heredity.seeds import derive_seed


def _seed(config: CampaignConfig, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, domain, *parts) % (2**32 - 1)


def _finite(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    return values[np.isfinite(values)]


def holm_adjust(values: list[float]) -> list[float]:
    if not values:
        return []
    count = len(values)
    order = np.argsort(np.asarray(values), kind="mergesort")
    adjusted = np.empty(count, dtype=np.float64)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (count - rank) * values[int(index)])
        adjusted[int(index)] = min(1.0, running)
    return adjusted.tolist()


def _bootstrap_mean(
    matrix_values: np.ndarray,
    repetitions: int,
    seed: int,
) -> tuple[float, list[float]]:
    values = _finite(matrix_values)
    if not len(values):
        return np.nan, [np.nan, np.nan]
    observed = float(np.mean(values))
    rng = np.random.default_rng(seed)
    choices = rng.integers(0, len(values), size=(repetitions, len(values)))
    samples = values[choices].mean(axis=1)
    interval = np.quantile(samples, (0.025, 0.975))
    return observed, [float(interval[0]), float(interval[1])]


def _sign_randomization_p(
    matrix_values: np.ndarray,
    repetitions: int,
    seed: int,
    direction: str,
) -> float:
    values = _finite(matrix_values)
    if not len(values):
        return 1.0
    signed = values if direction == "positive" else -values
    observed = float(np.mean(signed))
    rng = np.random.default_rng(seed)
    signs = rng.integers(0, 2, size=(repetitions, len(signed))) * 2 - 1
    null = (signs @ signed) / len(signed)
    return float((np.count_nonzero(null >= observed) + 1) / (repetitions + 1))


def _paths(cells: Path, *, mechanism: str | None = None, candidate: str | None = None) -> list[Path]:
    result = []
    for path in sorted(cells.glob("cell_*.joblib")):
        if path.name.endswith("_landscape.joblib"):
            continue
        name = path.name
        if mechanism is not None and f"_{mechanism}_" not in name:
            continue
        if candidate is not None and f"_c{candidate}_" not in name:
            continue
        result.append(path)
    return result


def _prediction_arrays(paths: list[Path]) -> dict[str, np.ndarray]:
    blocks: dict[str, list[np.ndarray]] = {
        "matrix_id": [],
        "half": [],
        "outcome": [],
        "landmark": [],
        "first_break": [],
        "baseline": [],
        "mixture": [],
        "knn": [],
        "fixed": [],
    }
    for path in paths:
        cell = load_cell(path)
        count = len(cell["prediction"]["outcome"])
        if not count:
            continue
        blocks["matrix_id"].append(
            np.full(count, cell["metadata"]["matrix_id"], dtype=np.int64)
        )
        blocks["half"].append(np.asarray(cell["prediction"]["half"], dtype=np.int8))
        blocks["outcome"].append(
            np.asarray(cell["prediction"]["outcome"], dtype=np.int8)
        )
        blocks["landmark"].append(
            np.asarray(cell["prediction"]["landmark"], dtype=np.int16)
        )
        blocks["first_break"].append(
            np.asarray(cell["prediction"]["first_break"], dtype=np.int16)
        )
        for name in ("baseline", "mixture", "knn", "fixed"):
            blocks[name].append(np.asarray(cell[name], dtype=np.float64))
    output = {}
    for name, values in blocks.items():
        if values:
            output[name] = np.concatenate(values, axis=0)
        elif name in ("baseline", "mixture", "knn", "fixed"):
            width = len(BASELINE_FEATURE_NAMES) if name == "baseline" else len(
                SURPRISE_FEATURE_NAMES
            )
            output[name] = np.empty((0, width))
        else:
            output[name] = np.empty(0, dtype=np.int64)
    return output


def fit_development_models(
    cells: Path,
    config: CampaignConfig,
    destination: Path,
) -> dict[str, Any]:
    bundle: dict[str, Any] = {
        "format": "fep-surprise-predictors-v1",
        "baseline_features": BASELINE_FEATURE_NAMES,
        "surprise_features": SURPRISE_FEATURE_NAMES,
        "candidates": {},
    }
    for candidate in ("02", "03"):
        arrays = _prediction_arrays(
            _paths(cells, mechanism="NATURAL_GARD", candidate=candidate)
        )
        if not len(arrays["outcome"]):
            raise RuntimeError(f"candidate {candidate} has no eligible break rows")
        candidate_models: dict[str, FrozenPredictor] = {}
        candidate_models["baseline"] = select_c_and_fit(
            arrays["baseline"],
            arrays["outcome"],
            arrays["matrix_id"],
            config.predictor_c_grid,
            config.predictor_folds,
        )
        for name in ("mixture", "knn", "fixed"):
            values = np.column_stack([arrays["baseline"], arrays[name]])
            candidate_models[name] = select_c_and_fit(
                values,
                arrays["outcome"],
                arrays["matrix_id"],
                config.predictor_c_grid,
                config.predictor_folds,
            )
        bundle["candidates"][candidate] = candidate_models
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, destination, compress=3)
    return {
        "format": bundle["format"],
        "candidates": {
            candidate: {name: model.c for name, model in models.items()}
            for candidate, models in bundle["candidates"].items()
        },
    }


def _cycle_matrix_values(
    paths: list[Path], estimator: str, half: str, metric: str
) -> tuple[np.ndarray, np.ndarray]:
    matrices = []
    values = []
    for path in paths:
        cell = load_cell(path)
        underlying = {
            "strict_recovery_difference": "postbreak_recovery",
            "strict_daughter_difference": "postbreak_daughters",
        }.get(metric, metric)
        selected = [
            row
            for row in cell["cycle"][estimator]
            if row["half"] == half and np.isfinite(row.get(underlying, np.nan))
        ]
        if metric == "strict_recovery_difference":
            positive = [row["postbreak_recovery"] for row in selected if row["positive"]]
            negative = [row["postbreak_recovery"] for row in selected if not row["positive"]]
            value = (
                float(np.mean(positive) - np.mean(negative))
                if positive and negative
                else 0.0
                if negative
                else np.nan
            )
        elif metric == "strict_daughter_difference":
            positive = [row["postbreak_daughters"] for row in selected if row["positive"]]
            negative = [row["postbreak_daughters"] for row in selected if not row["positive"]]
            value = (
                float(np.mean(positive) - np.mean(negative))
                if positive and negative
                else 0.0
                if negative
                else np.nan
            )
        else:
            raw = [row[metric] for row in selected if np.isfinite(row[metric])]
            value = float(np.mean(raw)) if raw else np.nan
        matrices.append(cell["metadata"]["matrix_id"])
        values.append(value)
    return np.asarray(matrices, dtype=np.int64), np.asarray(values, dtype=np.float64)


def analyze_cycles(cells: Path, config: CampaignConfig) -> dict[str, Any]:
    contrasts = (
        ("shock", "positive"),
        ("growth", "negative"),
        ("break_excess", "positive"),
        ("strict_recovery_difference", "negative"),
    )
    output: dict[str, Any] = {"cells": {}, "primary_tests": []}
    tests = []
    for mechanism in (
        "NATURAL_GARD",
        "HOMOGENEOUS_GENERATIVE",
        "FISSION_ONLY_GENERATIVE",
    ):
        for candidate in ("02", "03"):
            paths = _paths(cells, mechanism=mechanism, candidate=candidate)
            if not paths:
                continue
            for estimator in ESTIMATORS:
                for half in ("A", "B"):
                    key = f"{mechanism}/{candidate}/{estimator}/{half}"
                    entry: dict[str, Any] = {}
                    for metric, direction in contrasts:
                        _, values = _cycle_matrix_values(paths, estimator, half, metric)
                        seed = _seed(config, "analysis.cycle", key, metric)
                        mean, interval = _bootstrap_mean(
                            values, config.bootstrap_repetitions, seed
                        )
                        p = _sign_randomization_p(
                            values,
                            config.randomization_repetitions,
                            seed + 1,
                            direction,
                        )
                        row = {
                            "mechanism": mechanism,
                            "candidate": candidate,
                            "estimator": estimator,
                            "half": half,
                            "contrast": metric,
                            "direction": direction,
                            "mean": mean,
                            "ci95": interval,
                            "matrix_count": int(np.isfinite(values).sum()),
                            "p_raw": p,
                        }
                        row["directional_ci"] = bool(
                            interval[0] > 0
                            if direction == "positive"
                            else interval[1] < 0
                        )
                        entry[metric] = row
                        if mechanism == "NATURAL_GARD":
                            tests.append(row)
                    # Certification state contrast is descriptive.
                    _, cert = _cycle_matrix_values(
                        paths, estimator, half, "strict_daughter_difference"
                    )
                    entry["strict_daughter_difference"] = {
                        "mean": _bootstrap_mean(
                            cert,
                            config.bootstrap_repetitions,
                            _seed(config, "analysis.certification", key),
                        )[0],
                        "matrix_count": int(np.isfinite(cert).sum()),
                    }
                    output["cells"][key] = entry
    # Four contrasts form one family within candidate/estimator/branch half.
    for candidate in ("02", "03"):
        for estimator in ESTIMATORS:
            for half in ("A", "B"):
                family = [
                    row
                    for row in tests
                    if row["candidate"] == candidate
                    and row["estimator"] == estimator
                    and row["half"] == half
                ]
                adjusted = holm_adjust([row["p_raw"] for row in family])
                for row, p_adjusted in zip(family, adjusted):
                    row["p_holm"] = p_adjusted
                    if row["direction"] == "positive":
                        directional_ci = row["ci95"][0] > 0
                    else:
                        directional_ci = row["ci95"][1] < 0
                    row["passes"] = bool(directional_ci and p_adjusted < 0.05)
    output["primary_tests"] = tests
    output["null_complete_pattern"] = {}
    for mechanism in ("HOMOGENEOUS_GENERATIVE", "FISSION_ONLY_GENERATIVE"):
        for candidate in ("02", "03"):
            for estimator in ESTIMATORS:
                for half in ("A", "B"):
                    key = f"{mechanism}/{candidate}/{estimator}/{half}"
                    entry = output["cells"].get(key, {})
                    output["null_complete_pattern"][key] = bool(
                        entry
                        and all(
                            entry[name].get("directional_ci", False)
                            for name, _ in contrasts
                        )
                    )
    return output


def _matrix_loss_gain(
    labels: np.ndarray,
    baseline: np.ndarray,
    enhanced: np.ndarray,
    matrices: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    unique = np.unique(matrices)
    values = []
    for matrix in unique:
        selected = matrices == matrix
        values.append(
            log_loss(labels[selected], baseline[selected])
            - log_loss(labels[selected], enhanced[selected])
        )
    return unique, np.asarray(values)


def _matrix_brier_gain(
    labels: np.ndarray,
    baseline: np.ndarray,
    enhanced: np.ndarray,
    matrices: np.ndarray,
) -> np.ndarray:
    unique = np.unique(matrices)
    return np.asarray(
        [
            float(
                np.mean((labels[matrices == matrix] - baseline[matrices == matrix]) ** 2)
                - np.mean((labels[matrices == matrix] - enhanced[matrices == matrix]) ** 2)
            )
            for matrix in unique
        ]
    )


def _permutation_gain_null(
    labels: np.ndarray,
    baseline: np.ndarray,
    enhanced: np.ndarray,
    matrices: np.ndarray,
    repetitions: int,
    seed: int,
) -> list[float]:
    rng = np.random.default_rng(seed)
    unique = np.unique(matrices)
    values = []
    for _ in range(repetitions):
        permuted = labels.copy()
        for matrix in unique:
            selected = np.flatnonzero(matrices == matrix)
            permuted[selected] = permuted[rng.permutation(selected)]
        _, gain = _matrix_loss_gain(permuted, baseline, enhanced, matrices)
        values.append(float(np.mean(gain)))
    return [float(v) for v in np.quantile(values, (0.025, 0.5, 0.975))]


def analyze_prediction(
    cells: Path,
    model_path: Path,
    config: CampaignConfig,
) -> dict[str, Any]:
    bundle = joblib.load(model_path)
    output: dict[str, Any] = {"tests": [], "cells": {}}
    primary_rows = []
    for candidate in ("02", "03"):
        arrays = _prediction_arrays(
            _paths(cells, mechanism="NATURAL_GARD", candidate=candidate)
        )
        models = bundle["candidates"][candidate]
        baseline_prediction = models["baseline"].predict(arrays["baseline"])
        enhanced_predictions = {
            name: models[name].predict(
                np.column_stack([arrays["baseline"], arrays[name]])
            )
            for name in ("mixture", "knn", "fixed")
        }
        for half_index, half_name in enumerate(("A", "B")):
            selected = arrays["half"] == half_index
            entry: dict[str, Any] = {
                "rows": int(selected.sum()),
                "events": int(arrays["outcome"][selected].sum()),
            }
            for estimator in ("mixture", "knn"):
                _, gain = _matrix_loss_gain(
                    arrays["outcome"][selected],
                    baseline_prediction[selected],
                    enhanced_predictions[estimator][selected],
                    arrays["matrix_id"][selected],
                )
                seed = _seed(
                    config, "analysis.prediction", candidate, half_name, estimator
                )
                mean, interval = _bootstrap_mean(
                    gain, config.bootstrap_repetitions, seed
                )
                p = _sign_randomization_p(
                    gain,
                    config.randomization_repetitions,
                    seed + 1,
                    "positive",
                )
                row = {
                    "candidate": candidate,
                    "half": half_name,
                    "estimator": estimator,
                    "log_loss_gain": mean,
                    "ci95": interval,
                    "p_raw": p,
                    "matrices": int(np.isfinite(gain).sum()),
                }
                brier = _matrix_brier_gain(
                    arrays["outcome"][selected],
                    baseline_prediction[selected],
                    enhanced_predictions[estimator][selected],
                    arrays["matrix_id"][selected],
                )
                row["brier_gain"] = _bootstrap_mean(
                    brier, config.bootstrap_repetitions, seed + 2
                )[0]
                labels_selected = arrays["outcome"][selected]
                row["average_precision_baseline"] = (
                    float(
                        average_precision_score(
                            labels_selected, baseline_prediction[selected]
                        )
                    )
                    if len(np.unique(labels_selected)) > 1
                    else None
                )
                row["average_precision_enhanced"] = (
                    float(
                        average_precision_score(
                            labels_selected, enhanced_predictions[estimator][selected]
                        )
                    )
                    if len(np.unique(labels_selected)) > 1
                    else None
                )
                row["outcome_permutation_gain_quantiles"] = _permutation_gain_null(
                    labels_selected,
                    baseline_prediction[selected],
                    enhanced_predictions[estimator][selected],
                    arrays["matrix_id"][selected],
                    min(config.randomization_repetitions, 512),
                    seed + 3,
                )
                primary_rows.append(row)
                entry[estimator] = row
            # Mixture versus forced-one-target, positive means the mixture wins.
            _, repertoire_gain = _matrix_loss_gain(
                arrays["outcome"][selected],
                enhanced_predictions["fixed"][selected],
                enhanced_predictions["mixture"][selected],
                arrays["matrix_id"][selected],
            )
            fixed_mean, fixed_interval = _bootstrap_mean(
                    repertoire_gain,
                    config.bootstrap_repetitions,
                    _seed(config, "analysis.fixed", candidate, half_name),
                )
            entry["mixture_over_fixed"] = {
                "log_loss_gain": fixed_mean,
                "ci95": fixed_interval,
                "passes": bool(fixed_interval[0] > 0),
            }
            output["cells"][f"{candidate}/{half_name}"] = entry
    adjusted = holm_adjust([row["p_raw"] for row in primary_rows])
    for row, p_adjusted in zip(primary_rows, adjusted):
        row["p_holm"] = p_adjusted
        row["passes"] = bool(row["ci95"][0] > 0 and p_adjusted < 0.05)
    output["tests"] = primary_rows
    return output


def analyze_wrong_beta(cells: Path, config: CampaignConfig) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for candidate in ("02", "03"):
        paths = _paths(cells, mechanism="NATURAL_GARD", candidate=candidate)
        loaded = [load_cell(path) for path in paths]
        landscapes: list[LandscapeEnsemble] = [
            joblib.load(path.with_name(path.stem + "_landscape.joblib")) for path in paths
        ]
        for estimator in ESTIMATORS:
            reference_diffs = []
            certification_diffs = []
            for index, (cell, landscape) in enumerate(zip(loaded, landscapes)):
                foreign = landscapes[(index + 1) % len(landscapes)]
                for key, destination in (
                    ("reference_probe", reference_diffs),
                    ("certification_probe", certification_diffs),
                ):
                    probe = cell[key]
                    if not len(probe):
                        continue
                    native_score = landscape.score(probe, estimator)
                    foreign_score = foreign.score(probe, estimator)
                    destination.append(float(np.mean(foreign_score - native_score)))
            ref_mean, ref_ci = _bootstrap_mean(
                np.asarray(reference_diffs),
                config.bootstrap_repetitions,
                _seed(config, "analysis.wrong_beta.reference", candidate, estimator),
            )
            cert_mean, cert_ci = _bootstrap_mean(
                np.asarray(certification_diffs),
                config.bootstrap_repetitions,
                _seed(config, "analysis.wrong_beta.certification", candidate, estimator),
            )
            output[f"{candidate}/{estimator}"] = {
                "wrong_minus_native_reference": ref_mean,
                "reference_ci95": ref_ci,
                "wrong_minus_native_certification": cert_mean,
                "certification_ci95": cert_ci,
                "passes_reference": bool(ref_ci[0] > 0),
                "passes_certification": bool(np.isfinite(cert_ci[0]) and cert_ci[0] > 0),
            }
    return output


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def adjudicate(cycles: dict[str, Any], prediction: dict[str, Any], wrong_beta: dict[str, Any]) -> dict[str, Any]:
    cycle_pass = bool(cycles["primary_tests"]) and all(
        row.get("passes", False) for row in cycles["primary_tests"]
    )
    prediction_pass = bool(prediction["tests"]) and all(
        row.get("passes", False) for row in prediction["tests"]
    )
    fixed_pass = all(
        cell["mixture_over_fixed"]["passes"]
        for cell in prediction["cells"].values()
    )
    beta_pass = bool(wrong_beta) and all(
        item["passes_reference"] and item["passes_certification"]
        for item in wrong_beta.values()
    )
    null_pass = not any(cycles.get("null_complete_pattern", {}).values())
    if cycle_pass and prediction_pass and fixed_pass and beta_pass and null_pass:
        conclusion = "FULL_SUPPORT"
    elif cycle_pass and not prediction_pass:
        conclusion = "GEOMETRIC_RELABELING_OR_GENERIC_SELF_ORGANIZATION"
    elif cycle_pass:
        conclusion = "PARTIAL_SELF_ORGANIZATION"
    else:
        conclusion = "HYPOTHESIS_NOT_SUPPORTED"
    return {
        "cycle_gate": cycle_pass,
        "incremental_prediction_gate": prediction_pass,
        "mixture_over_fixed_gate": fixed_pass,
        "native_beta_gate": beta_pass,
        "null_does_not_reproduce_complete_pattern": null_pass,
        "conclusion": conclusion,
        "claim_boundary": (
            "At most a beta-and-contract-conditioned coarse-grained probability "
            "landscape; not variational free energy, active inference, cognition, "
            "or nonphysical Platonic causation."
        ),
    }


def render_report(metrics: dict[str, Any]) -> str:
    decision = metrics["decision"]
    lines = [
        "# Cross-fitted compositional-surprise cycle",
        "",
        f"**Decision:** `{decision['conclusion']}`",
        "",
        "## Registered gates",
        "",
        f"- Surprise-cycle family: **{decision['cycle_gate']}**",
        f"- Incremental strict-8 prediction: **{decision['incremental_prediction_gate']}**",
        f"- Mixture over fixed-target predictor: **{decision['mixture_over_fixed_gate']}**",
        f"- Native-beta specificity: **{decision['native_beta_gate']}**",
        f"- Null chemistry lacks complete pattern: **{decision['null_does_not_reproduce_complete_pattern']}**",
        "",
        "## Natural-cycle contrasts",
        "",
        "| Candidate | Estimator | Half | Contrast | Mean | 95% CI | Holm p | Pass |",
        "|---|---|---:|---|---:|---:|---:|:---:|",
    ]
    for row in metrics["cycles"]["primary_tests"]:
        lo, hi = row["ci95"]
        lines.append(
            f"| {row['candidate']} | {row['estimator']} | {row['half']} | "
            f"{row['contrast']} | {row['mean']:+.5f} | [{lo:+.5f}, {hi:+.5f}] | "
            f"{row['p_holm']:.4g} | {row['passes']} |"
        )
    lines.extend(
        [
            "",
            "## Incremental prediction",
            "",
            "| Candidate | Estimator | Half | Log-loss gain | 95% CI | Holm p | Pass |",
            "|---|---|---:|---:|---:|---:|:---:|",
        ]
    )
    for row in metrics["prediction"]["tests"]:
        lo, hi = row["ci95"]
        lines.append(
            f"| {row['candidate']} | {row['estimator']} | {row['half']} | "
            f"{row['log_loss_gain']:+.6f} | [{lo:+.6f}, {hi:+.6f}] | "
            f"{row['p_holm']:.4g} | {row['passes']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            decision["claim_boundary"],
            "",
            "Homogeneous and fission-only cells are reported in `metrics.json` as a "
            "mechanistic decomposition and cannot rescue a failed natural result.",
            "",
        ]
    )
    return "\n".join(lines)


def analyze_confirmation(
    cells: Path,
    model_path: Path,
    config: CampaignConfig,
    destination: Path,
) -> dict[str, Any]:
    cycles = analyze_cycles(cells, config)
    prediction = analyze_prediction(cells, model_path, config)
    wrong_beta = analyze_wrong_beta(cells, config)
    metrics = {
        "format": "fep-surprise-results-v1",
        "profile": config.profile,
        "cycles": cycles,
        "prediction": prediction,
        "wrong_beta": wrong_beta,
    }
    metrics["decision"] = adjudicate(cycles, prediction, wrong_beta)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "metrics.json").write_text(
        json.dumps(_json_ready(metrics), indent=2, sort_keys=True) + "\n"
    )
    (destination / "REPORT.md").write_text(render_report(metrics), encoding="utf-8")
    return metrics
