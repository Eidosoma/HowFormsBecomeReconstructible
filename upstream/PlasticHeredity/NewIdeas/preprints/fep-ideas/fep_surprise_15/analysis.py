from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import rankdata

from . import compat as _compat  # noqa: F401
from .config import Campaign15Config, NATURAL, NULL_MECHANISMS
from .observers import (
    ALL_OBSERVERS,
    INVARIANT_KNN,
    LEGACY_KNN,
    PRIMARY_OBSERVERS,
    SHELF,
)
from .predictor import FrozenPredictor15, log_loss, select_and_fit
from .worker import (
    ANOMALY_FEATURE_NAMES,
    BASELINE_FEATURE_NAMES,
    load_cell,
    load_observers,
)
from plastic_heredity.seeds import derive_seed


def _seed(config: Campaign15Config, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, domain, *parts) % (2**32 - 1)


def _finite(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    return array[np.isfinite(array)]


def holm_adjust(values: list[float]) -> list[float]:
    if not values:
        return []
    count = len(values)
    order = np.argsort(np.asarray(values), kind="mergesort")
    adjusted = np.empty(count, dtype=np.float64)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (count - rank) * float(values[int(index)]))
        adjusted[int(index)] = min(1.0, running)
    return adjusted.tolist()


def _bootstrap_mean(
    values: np.ndarray, repetitions: int, seed: int
) -> tuple[float, list[float]]:
    finite = _finite(values)
    if not len(finite):
        return float("nan"), [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(finite), size=(repetitions, len(finite)))
    samples = finite[indices].mean(axis=1)
    interval = np.quantile(samples, (0.025, 0.975))
    return float(np.mean(finite)), [float(interval[0]), float(interval[1])]


def _sign_randomization_p(
    values: np.ndarray, repetitions: int, seed: int, direction: str
) -> float:
    finite = _finite(values)
    if not len(finite):
        return 1.0
    oriented = finite if direction == "positive" else -finite
    observed = float(np.mean(oriented))
    rng = np.random.default_rng(seed)
    signs = rng.integers(0, 2, size=(repetitions, len(oriented))) * 2 - 1
    null = (signs @ oriented) / len(oriented)
    return float((np.count_nonzero(null >= observed) + 1) / (repetitions + 1))


def _test(
    values: np.ndarray,
    direction: str,
    config: Campaign15Config,
    domain: str,
    *parts: object,
) -> dict[str, Any]:
    seed = _seed(config, domain, *parts)
    mean, interval = _bootstrap_mean(values, config.bootstrap_repetitions, seed)
    p_value = _sign_randomization_p(
        values, config.randomization_repetitions, seed + 1, direction
    )
    directional = bool(
        np.isfinite(interval).all()
        and (interval[0] > 0 if direction == "positive" else interval[1] < 0)
    )
    return {
        "mean": mean,
        "ci95": interval,
        "matrix_count": int(np.isfinite(values).sum()),
        "direction": direction,
        "directional_ci": directional,
        "p_raw": p_value,
    }


def _cell_paths(
    cells: Path,
    *,
    mechanism: str | None = None,
    candidate: str | None = None,
) -> list[Path]:
    output = []
    for path in sorted(cells.glob("cell_*.joblib")):
        if path.stem.endswith("_observers"):
            continue
        if mechanism is not None and f"_{mechanism}_" not in path.name:
            continue
        if candidate is not None and f"_c{candidate}_" not in path.name:
            continue
        output.append(path)
    return output


def _prediction_arrays(paths: list[Path]) -> dict[str, np.ndarray]:
    names = (
        "matrix_id",
        "half",
        "outcome",
        "landmark",
        "first_break",
        "baseline",
        *ALL_OBSERVERS,
    )
    blocks: dict[str, list[np.ndarray]] = {name: [] for name in names}
    for path in paths:
        cell = load_cell(path)
        count = len(cell["prediction"]["outcome"])
        if not count:
            continue
        blocks["matrix_id"].append(
            np.full(count, int(cell["metadata"]["matrix_id"]), dtype=np.int64)
        )
        for name in ("half", "outcome", "landmark", "first_break"):
            blocks[name].append(np.asarray(cell["prediction"][name]))
        blocks["baseline"].append(np.asarray(cell["baseline"], dtype=np.float64))
        for observer in ALL_OBSERVERS:
            blocks[observer].append(np.asarray(cell[observer], dtype=np.float64))
    output: dict[str, np.ndarray] = {}
    for name, values in blocks.items():
        if values:
            output[name] = np.concatenate(values, axis=0)
        elif name == "baseline":
            output[name] = np.empty((0, len(BASELINE_FEATURE_NAMES)))
        elif name in ALL_OBSERVERS:
            output[name] = np.empty((0, len(ANOMALY_FEATURE_NAMES)))
        else:
            output[name] = np.empty(0, dtype=np.int64)
    return output


def fit_development_models(
    cells: Path, config: Campaign15Config, destination: Path
) -> dict[str, Any]:
    bundle: dict[str, Any] = {
        "format": "fep-surprise-15-predictors-v1",
        "baseline_features": BASELINE_FEATURE_NAMES,
        "anomaly_features": ANOMALY_FEATURE_NAMES,
        "observers": PRIMARY_OBSERVERS,
        "candidates": {},
    }
    summary: dict[str, Any] = {}
    for candidate in ("02", "03"):
        arrays = _prediction_arrays(
            _cell_paths(cells, mechanism=NATURAL, candidate=candidate)
        )
        if not len(arrays["outcome"]):
            raise RuntimeError(f"candidate {candidate} has no eligible break rows")
        models: dict[str, FrozenPredictor15] = {}
        models["baseline"] = select_and_fit(
            arrays["baseline"],
            arrays["outcome"],
            arrays["matrix_id"],
            config.predictor_c_grid,
            config.predictor_folds,
        )
        for observer in PRIMARY_OBSERVERS:
            models[observer] = select_and_fit(
                np.column_stack([arrays["baseline"], arrays[observer]]),
                arrays["outcome"],
                arrays["matrix_id"],
                config.predictor_c_grid,
                config.predictor_folds,
            )
        bundle["candidates"][candidate] = models
        summary[candidate] = {
            name: {
                "c": model.c,
                "calibration_slope": model.calibration_slope,
                "calibration_intercept": model.calibration_intercept,
                "constant": model.constant,
            }
            for name, model in models.items()
        }
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, destination, compress=3)
    return {
        "format": bundle["format"],
        "model_hash": joblib.hash(bundle),
        "models": summary,
    }


def _cycle_matrix_values(
    paths: list[Path], observer: str, half: str, metric: str
) -> tuple[np.ndarray, np.ndarray]:
    matrix_ids = []
    values = []
    for path in paths:
        cell = load_cell(path)
        rows = [row for row in cell["cycles"][observer] if row["half"] == half]
        if metric == "strict_recovery_difference":
            positives = [
                float(row["postbreak_recovery"])
                for row in rows
                if row["strict8"] and np.isfinite(row["postbreak_recovery"])
            ]
            near_misses = [
                float(row["postbreak_recovery"])
                for row in rows
                if row["run8_near_miss"] and np.isfinite(row["postbreak_recovery"])
            ]
            value = (
                float(np.mean(positives) - np.mean(near_misses))
                if positives and near_misses
                else float("nan")
            )
        else:
            selected = [
                float(row[metric])
                for row in rows
                if np.isfinite(row.get(metric, np.nan))
            ]
            value = float(np.mean(selected)) if selected else float("nan")
        matrix_ids.append(int(cell["metadata"]["matrix_id"]))
        values.append(value)
    return np.asarray(matrix_ids), np.asarray(values, dtype=np.float64)


def _cycle_value(rows: list[dict[str, Any]], metric: str) -> float:
    if metric == "strict_recovery_difference":
        positives = [
            float(row["postbreak_recovery"])
            for row in rows
            if row["strict8"] and np.isfinite(row["postbreak_recovery"])
        ]
        near_misses = [
            float(row["postbreak_recovery"])
            for row in rows
            if row["run8_near_miss"] and np.isfinite(row["postbreak_recovery"])
        ]
        return (
            float(np.mean(positives) - np.mean(near_misses))
            if positives and near_misses
            else float("nan")
        )
    selected = [
        float(row[metric])
        for row in rows
        if np.isfinite(row.get(metric, np.nan))
    ]
    return float(np.mean(selected)) if selected else float("nan")


def analyze_cycles(cells: Path, config: Campaign15Config) -> dict[str, Any]:
    contrasts = (
        ("break_excess", "positive"),
        ("strict_recovery_difference", "negative"),
    )
    accumulated: dict[tuple[str, str, str, str, str], list[float]] = {}
    prevalence_counts: dict[tuple[str, str], list[int]] = {}
    for path in _cell_paths(cells):
        cell = load_cell(path)
        metadata = cell["metadata"]
        mechanism = str(metadata["mechanism"])
        candidate = str(metadata["candidate"])
        canonical_rows = cell["cycles"][INVARIANT_KNN]
        prevalence = prevalence_counts.setdefault((mechanism, candidate), [0, 0, 0])
        prevalence[0] += sum(int(row["strict8"]) for row in canonical_rows)
        prevalence[1] += sum(int(row["has_run8"]) for row in canonical_rows)
        prevalence[2] += len(canonical_rows)
        for observer in PRIMARY_OBSERVERS:
            for half in ("A", "B"):
                rows = [
                    row for row in cell["cycles"][observer] if row["half"] == half
                ]
                for metric, _ in contrasts:
                    accumulated.setdefault(
                        (mechanism, candidate, observer, half, metric), []
                    ).append(_cycle_value(rows, metric))

    primary: list[dict[str, Any]] = []
    natural_cells: dict[str, Any] = {}
    for candidate in ("02", "03"):
        for observer in PRIMARY_OBSERVERS:
            for half in ("A", "B"):
                family = []
                for metric, direction in contrasts:
                    values = np.asarray(
                        accumulated.get(
                            (NATURAL, candidate, observer, half, metric), []
                        ),
                        dtype=np.float64,
                    )
                    row = {
                        "candidate": candidate,
                        "observer": observer,
                        "half": half,
                        "contrast": metric,
                        **_test(
                            values,
                            direction,
                            config,
                            "analysis15.cycle",
                            candidate,
                            observer,
                            half,
                            metric,
                        ),
                    }
                    family.append(row)
                    primary.append(row)
                adjusted = holm_adjust([row["p_raw"] for row in family])
                for row, p_value in zip(family, adjusted):
                    row["p_holm"] = p_value
                    row["passes"] = bool(
                        row["directional_ci"] and p_value < 0.05
                    )
                natural_cells[f"{candidate}/{observer}/{half}"] = family

    nulls: dict[str, Any] = {}
    for mechanism in NULL_MECHANISMS:
        for candidate in ("02", "03"):
            for observer in PRIMARY_OBSERVERS:
                for half in ("A", "B"):
                    rows = []
                    for metric, direction in contrasts:
                        values = np.asarray(
                            accumulated.get(
                                (mechanism, candidate, observer, half, metric), []
                            ),
                            dtype=np.float64,
                        )
                        rows.append(
                            {
                                "contrast": metric,
                                **_test(
                                    values,
                                    direction,
                                    config,
                                    "analysis15.null",
                                    mechanism,
                                    candidate,
                                    observer,
                                    half,
                                    metric,
                                ),
                            }
                        )
                    nulls[f"{mechanism}/{candidate}/{observer}/{half}"] = {
                        "contrasts": rows,
                        "both_directional": bool(
                            rows and all(row["directional_ci"] for row in rows)
                        ),
                    }

    prevalence: dict[str, Any] = {}
    for mechanism in (NATURAL, *NULL_MECHANISMS):
        for candidate in ("02", "03"):
            events, run8, futures = prevalence_counts.get(
                (mechanism, candidate), [0, 0, 0]
            )
            prevalence[f"{mechanism}/{candidate}"] = {
                "strict8_events": events,
                "run8_futures": run8,
                "futures": futures,
                "strict8_rate": events / futures if futures else None,
            }
    return {
        "primary_tests": primary,
        "natural_blocks": natural_cells,
        "null_controls": nulls,
        "prevalence": prevalence,
    }


def analyze_reference_reliability(
    cells: Path, config: Campaign15Config
) -> dict[str, Any]:
    accumulated: dict[tuple[str, str], list[float]] = {}
    for path in _cell_paths(cells, mechanism=NATURAL):
        metadata = load_cell(path)["metadata"]
        for observer in PRIMARY_OBSERVERS:
            accumulated.setdefault(
                (str(metadata["candidate"]), observer), []
            ).append(float(metadata["reference_reliability"][observer]))
    tests = []
    for candidate in ("02", "03"):
        for observer in PRIMARY_OBSERVERS:
            values = np.asarray(accumulated.get((candidate, observer), []))
            mean, interval = _bootstrap_mean(
                values,
                config.bootstrap_repetitions,
                _seed(config, "analysis15.reliability", candidate, observer),
            )
            tests.append(
                {
                    "candidate": candidate,
                    "observer": observer,
                    "mean_spearman": mean,
                    "ci95": interval,
                    "matrix_count": int(np.isfinite(values).sum()),
                    "passes": bool(
                        np.isfinite(interval).all()
                        and interval[0] > config.reference_reliability_floor
                    ),
                }
            )
    return {"tests": tests}


def analyze_mass_artifact(cells: Path, config: Campaign15Config) -> dict[str, Any]:
    signs = (
        ("raw_shock", "negative"),
        ("raw_growth", "positive"),
        ("scale_term", "negative"),
        ("growth_scale_term", "positive"),
        ("composition_term", "positive"),
        ("growth_composition_term", "negative"),
    )
    accumulated: dict[tuple[str, str, str], list[float]] = {}
    tests = []
    additive_max = 0.0
    primary_scale_max = {observer: 0.0 for observer in PRIMARY_OBSERVERS}
    for path in _cell_paths(cells, mechanism=NATURAL):
        cell = load_cell(path)
        candidate = str(cell["metadata"]["candidate"])
        for observer in PRIMARY_OBSERVERS:
            primary_scale_max[observer] = max(
                primary_scale_max[observer],
                float(cell["metadata"]["scale_max_abs"][observer]),
            )
        for half in ("A", "B"):
            rows = [
                row for row in cell["cycles"][LEGACY_KNN] if row["half"] == half
            ]
            for metric, _ in signs:
                accumulated.setdefault((candidate, half, metric), []).append(
                    _cycle_value(rows, metric)
                )
            for row in rows:
                additive_max = max(
                    additive_max,
                    abs(
                        row["raw_shock"]
                        - row["scale_term"]
                        - row["composition_term"]
                    ),
                    abs(
                        row["raw_growth"]
                        - row["growth_scale_term"]
                        - row["growth_composition_term"]
                    ),
                )
    for candidate in ("02", "03"):
        for half in ("A", "B"):
            family = []
            for metric, direction in signs:
                values = np.asarray(
                    accumulated.get((candidate, half, metric), []), dtype=np.float64
                )
                row = {
                    "candidate": candidate,
                    "half": half,
                    "metric": metric,
                    **_test(
                        values,
                        direction,
                        config,
                        "analysis15.mass",
                        candidate,
                        half,
                        metric,
                    ),
                }
                row["passes"] = row["directional_ci"]
                family.append(row)
                tests.append(row)
    scale_pass = all(
        value <= config.scale_tolerance for value in primary_scale_max.values()
    )
    decomposition_pass = additive_max <= 1e-10
    return {
        "legacy_sign_tests": tests,
        "primary_scientific_scale_max_abs": primary_scale_max,
        "primary_scale_invariance_passes": scale_pass,
        "additive_decomposition_max_abs_error": additive_max,
        "additive_decomposition_passes": decomposition_pass,
        "mass_artifact_confirmed": bool(
            tests
            and all(row["passes"] for row in tests)
            and scale_pass
            and decomposition_pass
        ),
    }


def _matrix_log_loss_gain(
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
    return unique, np.asarray(values, dtype=np.float64)


def _auc(labels: np.ndarray, scores: np.ndarray) -> tuple[float, int]:
    y = np.asarray(labels, dtype=np.int8)
    positives = int(y.sum())
    negatives = len(y) - positives
    pairs = positives * negatives
    if not pairs:
        return float("nan"), 0
    ranks = rankdata(np.asarray(scores, dtype=np.float64), method="average")
    value = (float(ranks[y == 1].sum()) - positives * (positives + 1) / 2) / pairs
    return value, pairs


def _matrix_concordance_gain(
    labels: np.ndarray,
    baseline: np.ndarray,
    enhanced: np.ndarray,
    matrices: np.ndarray,
    landmarks: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    output_ids = []
    output_values = []
    for matrix in np.unique(matrices):
        weighted_base = weighted_enhanced = 0.0
        total_pairs = 0
        matrix_selected = matrices == matrix
        for landmark in np.unique(landmarks[matrix_selected]):
            selected = matrix_selected & (landmarks == landmark)
            base_auc, pairs = _auc(labels[selected], baseline[selected])
            enhanced_auc, _ = _auc(labels[selected], enhanced[selected])
            if pairs:
                weighted_base += pairs * base_auc
                weighted_enhanced += pairs * enhanced_auc
                total_pairs += pairs
        output_ids.append(matrix)
        output_values.append(
            (weighted_enhanced - weighted_base) / total_pairs
            if total_pairs
            else float("nan")
        )
    return np.asarray(output_ids), np.asarray(output_values, dtype=np.float64)


def _permutation_log_loss_quantiles(
    labels: np.ndarray,
    baseline: np.ndarray,
    enhanced: np.ndarray,
    matrices: np.ndarray,
    landmarks: np.ndarray,
    break_times: np.ndarray,
    repetitions: int,
    seed: int,
) -> list[float]:
    if not len(labels):
        return [float("nan")] * 3
    y = np.asarray(labels, dtype=np.int8)
    matrix_values, inverse = np.unique(matrices, return_inverse=True)
    strata: dict[tuple[int, int, int], list[int]] = {}
    for index, key in enumerate(
        zip(matrices.tolist(), landmarks.tolist(), (break_times // 4).tolist())
    ):
        strata.setdefault(tuple(int(value) for value in key), []).append(index)
    strata_indices = [np.asarray(value, dtype=np.int64) for value in strata.values()]
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(repetitions):
        permuted = y.copy()
        for indices in strata_indices:
            if len(indices) > 1:
                permuted[indices] = y[indices[rng.permutation(len(indices))]]
        p_base = np.clip(baseline, 1e-12, 1.0 - 1e-12)
        p_enhanced = np.clip(enhanced, 1e-12, 1.0 - 1e-12)
        contribution = (
            -(permuted * np.log(p_base) + (1 - permuted) * np.log(1 - p_base))
            + permuted * np.log(p_enhanced)
            + (1 - permuted) * np.log(1 - p_enhanced)
        )
        totals = np.bincount(inverse, weights=contribution, minlength=len(matrix_values))
        counts = np.bincount(inverse, minlength=len(matrix_values))
        means.append(float(np.mean(totals / counts)))
    return [
        float(value)
        for value in np.quantile(np.asarray(means), (0.025, 0.5, 0.975))
    ]


def analyze_prediction(
    cells: Path,
    model_path: Path,
    config: Campaign15Config,
) -> dict[str, Any]:
    bundle = joblib.load(model_path)
    if bundle.get("format") != "fep-surprise-15-predictors-v1":
        raise ValueError("unsupported development predictor bundle")
    log_rows = []
    rank_rows = []
    blocks: dict[str, Any] = {}
    for candidate in ("02", "03"):
        arrays = _prediction_arrays(
            _cell_paths(cells, mechanism=NATURAL, candidate=candidate)
        )
        models = bundle["candidates"][candidate]
        baseline = models["baseline"].predict(arrays["baseline"])
        enhanced = {
            observer: models[observer].predict(
                np.column_stack([arrays["baseline"], arrays[observer]])
            )
            for observer in PRIMARY_OBSERVERS
        }
        for half_index, half in enumerate(("A", "B")):
            selected = arrays["half"] == half_index
            block: dict[str, Any] = {
                "rows": int(selected.sum()),
                "events": int(arrays["outcome"][selected].sum()),
            }
            for observer in PRIMARY_OBSERVERS:
                _, loss_gain = _matrix_log_loss_gain(
                    arrays["outcome"][selected],
                    baseline[selected],
                    enhanced[observer][selected],
                    arrays["matrix_id"][selected],
                )
                loss_row = {
                    "candidate": candidate,
                    "observer": observer,
                    "half": half,
                    "metric": "baseline_minus_enhanced_log_loss",
                    **_test(
                        loss_gain,
                        "positive",
                        config,
                        "analysis15.prediction.loss",
                        candidate,
                        observer,
                        half,
                    ),
                }
                loss_row["permutation_null_quantiles"] = (
                    _permutation_log_loss_quantiles(
                        arrays["outcome"][selected],
                        baseline[selected],
                        enhanced[observer][selected],
                        arrays["matrix_id"][selected],
                        arrays["landmark"][selected],
                        arrays["first_break"][selected],
                        min(512, config.randomization_repetitions),
                        _seed(
                            config,
                            "analysis15.prediction.permutation",
                            candidate,
                            observer,
                            half,
                        ),
                    )
                )
                _, concordance_gain = _matrix_concordance_gain(
                    arrays["outcome"][selected],
                    baseline[selected],
                    enhanced[observer][selected],
                    arrays["matrix_id"][selected],
                    arrays["landmark"][selected],
                )
                rank_row = {
                    "candidate": candidate,
                    "observer": observer,
                    "half": half,
                    "metric": "enhanced_minus_baseline_concordance",
                    **_test(
                        concordance_gain,
                        "positive",
                        config,
                        "analysis15.prediction.rank",
                        candidate,
                        observer,
                        half,
                    ),
                }
                log_rows.append(loss_row)
                rank_rows.append(rank_row)
                block[observer] = {"log_loss": loss_row, "ranking": rank_row}
            blocks[f"{candidate}/{half}"] = block
    for family in (log_rows, rank_rows):
        adjusted = holm_adjust([row["p_raw"] for row in family])
        for row, p_value in zip(family, adjusted):
            row["p_holm"] = p_value
            row["passes"] = bool(row["directional_ci"] and p_value < 0.05)
    loss_pass = bool(log_rows) and all(row["passes"] for row in log_rows)
    rank_pass = bool(rank_rows) and all(row["passes"] for row in rank_rows)
    verdict = (
        "CALIBRATED_PREDICTION"
        if loss_pass
        else "RANKING_ONLY"
        if rank_pass
        else "NO_INCREMENTAL_PREDICTION"
    )
    return {
        "model_hash": joblib.hash(bundle),
        "log_loss_tests": log_rows,
        "ranking_tests": rank_rows,
        "blocks": blocks,
        "calibrated_prediction_gate": loss_pass,
        "ranking_gate": rank_pass,
        "verdict": verdict,
    }


def _matched_foreign_indices(descriptors: np.ndarray) -> np.ndarray:
    values = np.asarray(descriptors, dtype=np.float64)
    if len(values) < 2:
        raise ValueError("foreign-beta matching needs at least two matrices")
    scale = values.std(axis=0, ddof=1)
    scale = np.where(scale >= 1e-12, scale, 1.0)
    standardized = (values - values.mean(axis=0)) / scale
    difference = standardized[:, None, :] - standardized[None, :, :]
    cost = np.sqrt(np.sum(difference * difference, axis=2))
    cost += 1e-12 * np.arange(len(values))[None, :]
    np.fill_diagonal(cost, float(np.max(cost) + 1e6))
    rows, columns = linear_sum_assignment(cost)
    assignment = np.empty(len(values), dtype=np.int64)
    assignment[rows] = columns
    if np.any(assignment == np.arange(len(values))):
        raise AssertionError("foreign-beta assignment contains a fixed point")
    return assignment


def analyze_native_specificity(
    cells: Path, config: Campaign15Config
) -> dict[str, Any]:
    tests = []
    matches: dict[str, Any] = {}
    for candidate in ("02", "03"):
        paths = _cell_paths(cells, mechanism=NATURAL, candidate=candidate)
        loaded = []
        for path in paths:
            cell = load_cell(path)
            loaded.append(
                {
                    "metadata": cell["metadata"],
                    "reference_probe": cell["reference_probe"],
                    "certification_probe": cell["certification_probe"],
                }
            )
        descriptors = np.asarray(
            [cell["metadata"]["beta_descriptor"] for cell in loaded]
        )
        foreign = _matched_foreign_indices(descriptors)
        matches[candidate] = [
            {
                "native_matrix": int(loaded[index]["metadata"]["matrix_id"]),
                "foreign_matrix": int(
                    loaded[int(other)]["metadata"]["matrix_id"]
                ),
            }
            for index, other in enumerate(foreign)
        ]
        differences: dict[tuple[str, str], list[float]] = {
            (observer, probe_name): []
            for observer in PRIMARY_OBSERVERS
            for probe_name in ("reference_probe", "certification_probe")
        }
        for index, other in enumerate(foreign):
            native_model = load_observers(
                paths[index].with_name(paths[index].stem + "_observers.joblib")
            )
            wrong_model = load_observers(
                paths[int(other)].with_name(
                    paths[int(other)].stem + "_observers.joblib"
                )
            )
            for observer in PRIMARY_OBSERVERS:
                parent_phase = (
                    len(
                        native_model.halves[0]
                        .calibrators[observer]
                        .sorted_scores
                    )
                    - 1
                )
                for probe_name, phase in (
                    ("reference_probe", parent_phase),
                    ("certification_probe", 0),
                ):
                    probe = loaded[index][probe_name]
                    value = float("nan")
                    if len(probe):
                        native_score = native_model.anomaly(probe, phase, observer)
                        wrong_score = wrong_model.anomaly(probe, phase, observer)
                        value = float(np.mean(wrong_score - native_score))
                    differences[(observer, probe_name)].append(value)
        for observer in PRIMARY_OBSERVERS:
            for probe_name in ("reference_probe", "certification_probe"):
                values = differences[(observer, probe_name)]
                row = {
                    "candidate": candidate,
                    "observer": observer,
                    "probe": probe_name,
                    **_test(
                        np.asarray(values),
                        "positive",
                        config,
                        "analysis15.native",
                        candidate,
                        observer,
                        probe_name,
                    ),
                }
                row["passes"] = row["directional_ci"]
                tests.append(row)
    return {
        "matching": matches,
        "tests": tests,
        "native_specificity_passes": bool(
            tests and all(row["passes"] for row in tests)
        ),
    }


def analyze_shelf_eligibility(cells: Path) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for candidate in ("02", "03"):
        paths = _cell_paths(cells, mechanism=NATURAL, candidate=candidate)
        eligible = []
        for path in paths:
            cell = load_cell(path)
            if cell["metadata"]["shelf_stability"]["stable_multishelf_eligible"]:
                eligible.append(int(cell["metadata"]["matrix_id"]))
        output[candidate] = {
            "eligible_matrices": eligible,
            "eligible_count": len(eligible),
            "total_matrices": len(paths),
        }
    return output


def adjudicate(
    cycles: dict[str, Any],
    reliability: dict[str, Any],
    mass: dict[str, Any],
    prediction: dict[str, Any],
    native: dict[str, Any],
    integrity: dict[str, bool],
    profile: str,
) -> dict[str, Any]:
    validity = bool(integrity) and all(integrity.values())
    observer_gates = {}
    for observer in PRIMARY_OBSERVERS:
        cycle_gate = all(
            row.get("passes", False)
            for row in cycles["primary_tests"]
            if row["observer"] == observer
        )
        reliability_gate = all(
            row.get("passes", False)
            for row in reliability["tests"]
            if row["observer"] == observer
        )
        observer_gates[observer] = bool(cycle_gate and reliability_gate)
    passed_observers = [name for name, passed in observer_gates.items() if passed]
    eligible_profile = profile == "full"
    if not eligible_profile:
        scientific = "NONSCIENTIFIC_PROFILE"
    elif not validity:
        scientific = "WITHHELD_INVALID"
    elif len(passed_observers) == len(PRIMARY_OBSERVERS):
        scientific = "OBSERVER_ROBUST_RECURRENCE"
    elif passed_observers:
        scientific = "OBSERVER_SPECIFIC_RECURRENCE"
    else:
        scientific = "RECURRENCE_NOT_SUPPORTED"
    instrument = bool(
        validity
        and mass["primary_scale_invariance_passes"]
        and all(row["passes"] for row in reliability["tests"])
        and native["native_specificity_passes"]
    )
    mass_verdict = (
        "NOT_ADJUDICATED_NONSCIENTIFIC"
        if not eligible_profile
        else "MASS_ARTIFACT_CONFIRMED"
        if mass["mass_artifact_confirmed"]
        else "MASS_ARTIFACT_NOT_CONFIRMED"
    )
    prediction_verdict = (
        "NOT_ADJUDICATED_NONSCIENTIFIC"
        if not eligible_profile
        else prediction["verdict"]
    )
    instrument_verdict = (
        "NOT_ADJUDICATED_NONSCIENTIFIC"
        if not eligible_profile
        else "RULEBOOK_INSTRUMENT_QUALIFIED"
        if instrument
        else "RULEBOOK_INSTRUMENT_NOT_QUALIFIED"
    )
    return {
        "profile_is_scientifically_eligible": eligible_profile,
        "integrity_verdict": "VALID" if validity else "INVALID",
        "integrity_gates": integrity,
        "observer_gates": observer_gates,
        "scientific_verdict": scientific,
        "mass_diagnosis": mass_verdict,
        "prediction_verdict": prediction_verdict,
        "rulebook_instrument_verdict": instrument_verdict,
        "claim_boundary": (
            "At most observer-robust, beta-and-contract-conditioned compositional "
            "recurrence in reconstructed GARD; not variational free energy, active "
            "inference, cognition, autonomous control, prebiotic chemistry, an "
            "inherited probability repertoire, or Platonic causation."
        ),
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def render_report(metrics: dict[str, Any]) -> str:
    decision = metrics["decision"]
    lines = [
        "# Experiment 1.5: scale-, phase-, and observer-audited recurrence",
        "",
        f"- Integrity: **{decision['integrity_verdict']}**",
        f"- Scientific verdict: **{decision['scientific_verdict']}**",
        f"- Mass diagnosis: **{decision['mass_diagnosis']}**",
        f"- Prediction: **{decision['prediction_verdict']}**",
        f"- Rulebook instrument: **{decision['rulebook_instrument_verdict']}**",
        "",
        "## Primary recurrence contrasts",
        "",
        "| Candidate | Observer | Half | Contrast | Mean | 95% CI | Holm p | Pass |",
        "|---|---|:---:|---|---:|---:|---:|:---:|",
    ]
    for row in metrics["cycles"]["primary_tests"]:
        low, high = row["ci95"]
        lines.append(
            f"| {row['candidate']} | {row['observer']} | {row['half']} | "
            f"{row['contrast']} | {row['mean']:+.6f} | "
            f"[{low:+.6f}, {high:+.6f}] | {row['p_holm']:.4g} | "
            f"{row['passes']} |"
        )
    lines.extend(
        [
            "",
            "## Prospective prediction",
            "",
            "| Metric | Candidate | Observer | Half | Gain | 95% CI | Holm p | Pass |",
            "|---|---|---|:---:|---:|---:|---:|:---:|",
        ]
    )
    for metric_name, rows in (
        ("log loss", metrics["prediction"]["log_loss_tests"]),
        ("concordance", metrics["prediction"]["ranking_tests"]),
    ):
        for row in rows:
            low, high = row["ci95"]
            lines.append(
                f"| {metric_name} | {row['candidate']} | {row['observer']} | "
                f"{row['half']} | {row['mean']:+.6f} | "
                f"[{low:+.6f}, {high:+.6f}] | {row['p_holm']:.4g} | "
                f"{row['passes']} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            decision["claim_boundary"],
            "",
            "Null panels, mass decompositions, reference reliability, native/foreign "
            "scores, and shelf eligibility are reported in `metrics.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def analyze_confirmation(
    cells: Path,
    model_path: Path,
    config: Campaign15Config,
    destination: Path,
    integrity: dict[str, bool],
) -> dict[str, Any]:
    cycles = analyze_cycles(cells, config)
    reliability = analyze_reference_reliability(cells, config)
    mass = analyze_mass_artifact(cells, config)
    prediction = analyze_prediction(cells, model_path, config)
    native = analyze_native_specificity(cells, config)
    shelf = analyze_shelf_eligibility(cells)
    metrics: dict[str, Any] = {
        "format": "fep-surprise-15-results-v1",
        "profile": config.profile,
        "cycles": cycles,
        "reference_reliability": reliability,
        "mass_artifact": mass,
        "prediction": prediction,
        "native_specificity": native,
        "shelf_eligibility": shelf,
    }
    metrics["decision"] = adjudicate(
        cycles, reliability, mass, prediction, native, integrity, config.profile
    )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "metrics.json").write_text(
        json.dumps(_json_ready(metrics), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (destination / "REPORT.md").write_text(
        render_report(metrics), encoding="utf-8"
    )
    return metrics
