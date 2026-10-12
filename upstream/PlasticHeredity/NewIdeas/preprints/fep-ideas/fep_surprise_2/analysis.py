from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.stats import rankdata

from fep_surprise_15.observers import INVARIANT_KNN, SHELF
from fep_surprise_15.predictor import log_loss
from plastic_heredity.seeds import derive_seed

from .config import ARMS, BETA_CHANGE_ARMS, BETA_PANEL_ARMS, Campaign2Config
from .predictor import MODEL_VARIANTS, FrozenHurdle2, fit_hurdle, model_features
from .worker import load_design, load_futures


def _seed(config: Campaign2Config, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, domain, *parts) % (2**32 - 1)


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


def _bootstrap(
    values: np.ndarray, repetitions: int, seed: int
) -> tuple[float, list[float]]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if not len(finite):
        return float("nan"), [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    samples = finite[
        rng.integers(0, len(finite), size=(repetitions, len(finite)))
    ].mean(axis=1)
    interval = np.quantile(samples, (0.025, 0.975))
    return float(np.mean(finite)), [float(interval[0]), float(interval[1])]


def _sign_p(values: np.ndarray, repetitions: int, seed: int) -> float:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if not len(finite):
        return 1.0
    observed = float(np.mean(finite))
    rng = np.random.default_rng(seed)
    signs = rng.integers(0, 2, size=(repetitions, len(finite))) * 2 - 1
    null = signs @ finite / len(finite)
    return float((np.count_nonzero(null >= observed) + 1) / (repetitions + 1))


def _positive_test(
    values: np.ndarray, config: Campaign2Config, domain: str, *parts: object
) -> dict[str, Any]:
    seed = _seed(config, domain, *parts)
    mean, interval = _bootstrap(values, config.bootstrap_repetitions, seed)
    return {
        "mean": mean,
        "ci95": interval,
        "matrix_count": int(np.isfinite(values).sum()),
        "p_raw": _sign_p(
            values, config.randomization_repetitions, seed + 1
        ),
        "directional_ci": bool(np.isfinite(interval).all() and interval[0] > 0),
    }


def _equivalence(
    values: np.ndarray,
    margin: float,
    config: Campaign2Config,
    domain: str,
    *parts: object,
) -> dict[str, Any]:
    mean, interval = _bootstrap(
        values, config.bootstrap_repetitions, _seed(config, domain, *parts)
    )
    return {
        "mean_difference": mean,
        "ci95": interval,
        "margin": margin,
        "matrix_count": int(np.isfinite(values).sum()),
        "passes": bool(
            np.isfinite(interval).all()
            and interval[0] >= -margin
            and interval[1] <= margin
        ),
    }


def _design_paths(cells: Path, candidate: str | None = None) -> list[Path]:
    paths = sorted(cells.glob("cell_*_design.joblib"))
    if candidate is not None:
        paths = [path for path in paths if f"_c{candidate}_" in path.name]
    return paths


def _future_for_design(path: Path) -> Path:
    return path.with_name(path.name.replace("_design.joblib", "_futures.joblib"))


def _records(
    cells: Path,
    candidate: str,
    observer: str,
    reference_half: int,
    branch_half: str | None = None,
) -> dict[str, Any]:
    numeric: dict[str, list[Any]] = {
        "matrix": [],
        "landmark": [],
        "arm": [],
        "branch": [],
        "first_break": [],
        "strict8": [],
        "f12": [],
        "destination": [],
    }
    features = {variant: [] for variant in MODEL_VARIANTS}
    profiles: list[dict[str, Any]] = []
    for design_path in _design_paths(cells, candidate):
        design = load_design(design_path)
        futures = load_futures(_future_for_design(design_path))
        matrix = int(design["metadata"]["matrix_id"])
        branches = futures["strict8"].shape[2]
        midpoint = branches // 2
        for landmark_index, landmark in enumerate(design["landmarks"]):
            for arm_index, _arm_name in enumerate(ARMS):
                profile = design["shelf_profiles"][landmark_index][arm_index]
                row_features = {
                    variant: model_features(
                        design["baseline"][landmark_index],
                        design["launch_metrics"][landmark_index, arm_index],
                        design["mismatch_jump"][observer][
                            landmark_index, arm_index, reference_half
                        ],
                        profile,
                        variant,
                    )
                    for variant in MODEL_VARIANTS
                }
                for branch in range(branches):
                    half = "A" if branch < midpoint else "B"
                    if branch_half is not None and half != branch_half:
                        continue
                    numeric["matrix"].append(matrix)
                    numeric["landmark"].append(int(landmark))
                    numeric["arm"].append(arm_index)
                    numeric["branch"].append(branch)
                    for name in ("first_break", "strict8", "f12", "destination"):
                        numeric[name].append(
                            int(futures[name][landmark_index, arm_index, branch])
                        )
                    profiles.append(profile)
                    for variant in MODEL_VARIANTS:
                        features[variant].append(row_features[variant])
    output: dict[str, Any] = {
        name: np.asarray(values, dtype=np.int64) for name, values in numeric.items()
    }
    output.update(
        {
            variant: np.stack(values) if values else np.empty((0, 0))
            for variant, values in features.items()
        }
    )
    output["profiles"] = profiles
    return output


def fit_development_models(
    cells: Path, config: Campaign2Config, destination: Path
) -> dict[str, Any]:
    bundle: dict[str, Any] = {
        "format": "fep-surprise-2-predictors-v1",
        "profile": config.profile,
        "models": {},
    }
    summary: dict[str, Any] = {}
    for candidate in ("02", "03"):
        bundle["models"][candidate] = {}
        summary[candidate] = {}
        for observer in (INVARIANT_KNN, SHELF):
            bundle["models"][candidate][observer] = {}
            summary[candidate][observer] = {}
            for reference_half in (0, 1):
                rows = _records(cells, candidate, observer, reference_half)
                if not len(rows["strict8"]):
                    raise RuntimeError(f"no development rows for candidate {candidate}")
                fitted: dict[str, FrozenHurdle2] = {}
                for variant in MODEL_VARIANTS:
                    fitted[variant] = fit_hurdle(
                        rows[variant],
                        rows["first_break"],
                        rows["strict8"],
                        rows["matrix"],
                        horizon=config.development.horizon,
                        c_grid=config.predictor_c_grid,
                        folds=config.predictor_folds,
                    )
                key = str(reference_half)
                bundle["models"][candidate][observer][key] = fitted
                summary[candidate][observer][key] = {
                    variant: {
                        "departure_c": model.departure.model.c,
                        "conditional_c": model.conditional_strict8.c,
                        "departure_constant": model.departure.model.constant,
                        "conditional_constant": model.conditional_strict8.constant,
                    }
                    for variant, model in fitted.items()
                }
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, destination, compress=3)
    return {
        "format": bundle["format"],
        "model_hash": joblib.hash(bundle),
        "models": summary,
    }


def _matrix_values(
    matrix: np.ndarray, values: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    ids = np.unique(matrix)
    return ids, np.asarray([np.mean(values[matrix == item]) for item in ids])


def _binary_loss_by_matrix(
    rows: dict[str, Any], labels: np.ndarray, prediction: np.ndarray
) -> np.ndarray:
    output = []
    for matrix in np.unique(rows["matrix"]):
        selected = rows["matrix"] == matrix
        output.append(log_loss(labels[selected], prediction[selected]))
    return np.asarray(output, dtype=np.float64)


def _absolute_latency_by_matrix(
    rows: dict[str, Any], prediction: np.ndarray, horizon: int
) -> np.ndarray:
    observed = np.where(rows["first_break"] >= 0, rows["first_break"] + 1, horizon)
    return np.asarray(
        [
            np.mean(np.abs(observed[rows["matrix"] == matrix] - prediction[rows["matrix"] == matrix]))
            for matrix in np.unique(rows["matrix"])
        ],
        dtype=np.float64,
    )


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(labels, dtype=bool)
    positives = int(y.sum())
    negatives = len(y) - positives
    if positives == 0 or negatives == 0:
        return float("nan")
    ranks = rankdata(scores, method="average")
    return float(
        (ranks[y].sum() - positives * (positives + 1) / 2)
        / (positives * negatives)
    )


def _finite_mean(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    return float(np.mean(finite)) if len(finite) else float("nan")


def _auc_by_matrix(
    rows: dict[str, Any], labels: np.ndarray, prediction: np.ndarray
) -> np.ndarray:
    return np.asarray(
        [
            _auc(labels[rows["matrix"] == matrix], prediction[rows["matrix"] == matrix])
            for matrix in np.unique(rows["matrix"])
        ]
    )


def _arm_label_permutation(
    rows: dict[str, Any],
    labels: np.ndarray,
    landscape: np.ndarray,
    comparator: np.ndarray,
    config: Campaign2Config,
    domain: str,
) -> dict[str, Any]:
    """Shuffle state-level outcome rates among the eight beta-only arms."""

    arm_count = len(BETA_PANEL_ARMS)
    rates = []
    landscape_probability = []
    comparator_probability = []
    for matrix in np.unique(rows["matrix"]):
        for landmark in np.unique(rows["landmark"][rows["matrix"] == matrix]):
            base = (rows["matrix"] == matrix) & (rows["landmark"] == landmark)
            group_rate = []
            group_landscape = []
            group_comparator = []
            valid = True
            for arm in range(arm_count):
                selected = base & (rows["arm"] == arm)
                if not selected.any():
                    valid = False
                    break
                group_rate.append(float(np.mean(labels[selected])))
                group_landscape.append(float(np.mean(landscape[selected])))
                group_comparator.append(float(np.mean(comparator[selected])))
            if valid:
                rates.append(group_rate)
                landscape_probability.append(group_landscape)
                comparator_probability.append(group_comparator)
    y = np.asarray(rates, dtype=np.float64)
    p_landscape = np.clip(np.asarray(landscape_probability), 1e-12, 1 - 1e-12)
    p_comparator = np.clip(np.asarray(comparator_probability), 1e-12, 1 - 1e-12)
    if not len(y):
        return {"gain": float("nan"), "p_value": 1.0, "groups": 0, "passes": False}

    delta_zero = -np.log(1 - p_comparator) + np.log(1 - p_landscape)
    delta_slope = -np.log(p_comparator) + np.log(p_landscape) - delta_zero

    def gain(outcome: np.ndarray) -> np.ndarray:
        return np.mean(delta_zero + outcome * delta_slope, axis=(-2, -1))

    observed = float(gain(y))
    rng = np.random.default_rng(_seed(config, domain))
    exceed = 0
    completed = 0
    while completed < config.randomization_repetitions:
        count = min(64, config.randomization_repetitions - completed)
        order = np.argsort(rng.random((count, *y.shape)), axis=2)
        shuffled = np.take_along_axis(y[None, :, :], order, axis=2)
        exceed += int(np.count_nonzero(gain(shuffled) >= observed))
        completed += count
    p_value = float((exceed + 1) / (config.randomization_repetitions + 1))
    return {
        "gain": observed,
        "p_value": p_value,
        "groups": len(y),
        "passes": bool(observed > 0 and p_value < 0.05),
    }


def _intervention_checks(cells: Path, config: Campaign2Config) -> dict[str, Any]:
    output: dict[str, Any] = {
        "isomorphism": [],
        "positive_mismatch": [],
        "dose_trends": [],
        "analytic_alignment": [],
    }
    no_op = ARMS.index("NOOP")
    isomorphic = ARMS.index("ISOMORPHIC_BOTH_100")
    for candidate in ("02", "03"):
        designs = _design_paths(cells, candidate)
        iso_break = []
        iso_strict = []
        iso_latency = []
        aligned = []
        mismatch_values = {
            (observer, half): []
            for observer in (INVARIANT_KNN, SHELF)
            for half in (0, 1)
        }
        slopes = {
            (metric, series, observer, half): []
            for metric in ("J", "M")
            for series in ("permutation", "morph")
            for observer in (INVARIANT_KNN, SHELF)
            for half in (0, 1)
        }
        for path in designs:
            design = load_design(path)
            future = load_futures(_future_for_design(path))
            first = future["first_break"]
            horizon = config.confirmation.horizon
            iso_break.append(
                float(np.mean(first[:, isomorphic] >= 0) - np.mean(first[:, no_op] >= 0))
            )
            iso_strict.append(
                float(np.mean(future["strict8"][:, isomorphic]) - np.mean(future["strict8"][:, no_op]))
            )
            latency = np.where(first >= 0, first + 1, horizon)
            iso_latency.append(
                float(np.mean(latency[:, isomorphic]) - np.mean(latency[:, no_op]))
            )
            aligned.append(
                float(np.max(np.abs(design["launch_metrics"][:, isomorphic, 11])))
            )
            for observer in (INVARIANT_KNN, SHELF):
                jump = np.asarray(design["mismatch_jump"][observer])
                for half in (0, 1):
                    mismatch_values[(observer, half)].append(
                        float(np.mean(jump[:, 1:8, half]))
                    )
                    permutation_y = np.mean(jump[:, 1:5, half], axis=0)
                    morph_y = np.mean(jump[:, 5:8, half], axis=0)
                    slopes[("J", "permutation", observer, half)].append(
                        float(np.polyfit(config.permutation_counts, permutation_y, 1)[0])
                    )
                    slopes[("J", "morph", observer, half)].append(
                        float(np.polyfit(config.morph_levels, morph_y, 1)[0])
                    )
                    local = np.asarray(design["launch_metrics"][:, :, 11])
                    slopes[("M", "permutation", observer, half)].append(
                        float(np.polyfit(config.permutation_counts, np.mean(local[:, 1:5], axis=0), 1)[0])
                    )
                    slopes[("M", "morph", observer, half)].append(
                        float(np.polyfit(config.morph_levels, np.mean(local[:, 5:8], axis=0), 1)[0])
                    )
        output["isomorphism"].extend(
            [
                {"candidate": candidate, "endpoint": "break", **_equivalence(np.asarray(iso_break), config.break_equivalence_margin, config, "analysis2.iso", candidate, "break")},
                {"candidate": candidate, "endpoint": "strict8", **_equivalence(np.asarray(iso_strict), config.strict8_equivalence_margin, config, "analysis2.iso", candidate, "strict8")},
                {"candidate": candidate, "endpoint": "latency", **_equivalence(np.asarray(iso_latency), config.latency_equivalence_margin, config, "analysis2.iso", candidate, "latency")},
            ]
        )
        output["analytic_alignment"].append(
            {
                "candidate": candidate,
                "maximum_aligned_local_mismatch": float(max(aligned, default=np.inf)),
                "passes": bool(max(aligned, default=np.inf) <= config.aligned_mismatch_tolerance),
            }
        )
        for (observer, half), values in mismatch_values.items():
            output["positive_mismatch"].append(
                {
                    "candidate": candidate,
                    "observer": observer,
                    "reference_half": half,
                    **_positive_test(np.asarray(values), config, "analysis2.jump", candidate, observer, half),
                }
            )
        for (metric, series, observer, half), values in slopes.items():
            output["dose_trends"].append(
                {
                    "candidate": candidate,
                    "metric": metric,
                    "series": series,
                    "observer": observer,
                    "reference_half": half,
                    **_positive_test(np.asarray(values), config, "analysis2.dose", candidate, metric, series, observer, half),
                }
            )
    for family in (output["positive_mismatch"], output["dose_trends"]):
        adjusted = holm_adjust([row["p_raw"] for row in family])
        for row, p_value in zip(family, adjusted):
            row["p_holm"] = p_value
            row["passes"] = bool(row["directional_ci"] and p_value < 0.05)
    return output


def _prediction_checks(
    cells: Path, predictors: dict[str, Any], config: Campaign2Config
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    raw_tests: list[dict[str, Any]] = []
    for candidate in ("02", "03"):
        for observer in (INVARIANT_KNN, SHELF):
            for reference_half in (0, 1):
                models = predictors["models"][candidate][observer][str(reference_half)]
                for branch_half in ("A", "B"):
                    rows = _records(
                        cells, candidate, observer, reference_half, branch_half
                    )
                    predictions = {
                        variant: models[variant].predict(rows[variant])
                        for variant in MODEL_VARIANTS
                    }
                    cell: dict[str, Any] = {
                        "candidate": candidate,
                        "observer": observer,
                        "reference_half": reference_half,
                        "branch_half": branch_half,
                        "rows": len(rows["strict8"]),
                        "strict8_events": int(rows["strict8"].sum()),
                        "comparisons": [],
                        "ranking": {},
                        "calibration": {},
                    }
                    for endpoint, label_name, prediction_name in (
                        ("break", None, "break"),
                        ("strict8", "strict8", "joint_strict8"),
                    ):
                        labels = (
                            (rows["first_break"] >= 0).astype(np.int8)
                            if label_name is None
                            else rows[label_name]
                        )
                        for comparator in ("physical", "local"):
                            left = _binary_loss_by_matrix(
                                rows, labels, predictions[comparator][prediction_name]
                            )
                            right = _binary_loss_by_matrix(
                                rows, labels, predictions["landscape"][prediction_name]
                            )
                            test = {
                                "endpoint": endpoint,
                                "comparison": f"landscape_vs_{comparator}",
                                **_positive_test(
                                    left - right,
                                    config,
                                    "analysis2.prediction",
                                    candidate,
                                    observer,
                                    reference_half,
                                    branch_half,
                                    endpoint,
                                    comparator,
                                ),
                            }
                            raw_tests.append(test)
                            cell["comparisons"].append(test)
                        cell["ranking"][endpoint] = {
                            variant: _finite_mean(
                                _auc_by_matrix(
                                    rows, labels, predictions[variant][prediction_name]
                                )
                            )
                            for variant in MODEL_VARIANTS
                        }
                        cell["calibration"][endpoint] = {
                            variant: {
                                "log_loss": log_loss(
                                    labels, predictions[variant][prediction_name]
                                ),
                                "brier": float(
                                    np.mean(
                                        (labels - predictions[variant][prediction_name]) ** 2
                                    )
                                ),
                            }
                            for variant in MODEL_VARIANTS
                        }
                    physical_latency = _absolute_latency_by_matrix(
                        rows, predictions["physical"]["latency"], config.confirmation.horizon
                    )
                    landscape_latency = _absolute_latency_by_matrix(
                        rows, predictions["landscape"]["latency"], config.confirmation.horizon
                    )
                    latency_test = {
                        "endpoint": "latency",
                        "comparison": "landscape_vs_physical",
                        **_positive_test(
                            physical_latency - landscape_latency,
                            config,
                            "analysis2.latency",
                            candidate,
                            observer,
                            reference_half,
                            branch_half,
                        ),
                    }
                    raw_tests.append(latency_test)
                    cell["comparisons"].append(latency_test)
                    cell["outcome_permutation"] = {
                        endpoint: _arm_label_permutation(
                            rows,
                            (rows["first_break"] >= 0).astype(np.int8)
                            if endpoint == "break"
                            else rows["strict8"],
                            predictions["landscape"][
                                "break" if endpoint == "break" else "joint_strict8"
                            ],
                            predictions["local"][
                                "break" if endpoint == "break" else "joint_strict8"
                            ],
                            config,
                            f"analysis2.arm_permutation.{candidate}.{observer}.{reference_half}.{branch_half}.{endpoint}",
                        )
                        for endpoint in ("break", "strict8")
                    }
                    output.append(cell)
    adjusted = holm_adjust([row["p_raw"] for row in raw_tests])
    for row, p_value in zip(raw_tests, adjusted):
        row["p_holm"] = p_value
        row["passes"] = bool(row["directional_ci"] and p_value < 0.05)
    return output


def _destination_checks(cells: Path, config: Campaign2Config) -> list[dict[str, Any]]:
    output = []
    raw_tests: list[dict[str, Any]] = []
    for candidate in ("02", "03"):
        # Observer choice does not enter this shelf-only test; partitions are
        # admitted only after agreement between their disjoint-training halves.
        for branch_half in ("A", "B"):
            rows = _records(cells, candidate, SHELF, 0, branch_half)
            selected = np.asarray(
                [
                    destination >= 0
                    and bool(profile.get("eligible"))
                    and ARMS[int(arm)] in BETA_CHANGE_ARMS
                    for destination, profile, arm in zip(
                        rows["destination"], rows["profiles"], rows["arm"]
                    )
                ],
                dtype=bool,
            )
            indices = np.flatnonzero(selected)
            matrix_ids = rows["matrix"][selected]
            labels = rows["destination"][selected]
            scores: dict[str, list[float]] = {name: [] for name in ("capture", "occupancy", "nearest")}
            accuracy: dict[str, list[int]] = {name: [] for name in scores}
            for index, label in zip(indices, labels):
                profile = rows["profiles"][int(index)]
                for name in scores:
                    probability = np.asarray(profile[name], dtype=np.float64)
                    scores[name].append(float(-np.log(max(probability[int(label)], 1e-12))))
                    accuracy[name].append(int(np.argmax(probability) == int(label)))
            cell: dict[str, Any] = {
                "candidate": candidate,
                "branch_half": branch_half,
                "events": len(labels),
                "matrices": int(len(np.unique(matrix_ids))),
                "eligible": bool(
                    len(labels) >= config.destination_min_events
                    and len(np.unique(matrix_ids)) >= config.destination_min_matrices
                ),
                "mean_log_loss": {
                    name: float(np.mean(values)) if values else float("nan")
                    for name, values in scores.items()
                },
                "accuracy": {
                    name: float(np.mean(values)) if values else float("nan")
                    for name, values in accuracy.items()
                },
                "comparisons": [],
            }
            for comparator in ("occupancy", "nearest"):
                matrix_gain = []
                for matrix in np.unique(matrix_ids):
                    mask = matrix_ids == matrix
                    matrix_gain.append(
                        float(
                            np.mean(np.asarray(scores[comparator])[mask])
                            - np.mean(np.asarray(scores["capture"])[mask])
                        )
                    )
                test = {
                    "comparison": f"capture_vs_{comparator}",
                    **_positive_test(
                        np.asarray(matrix_gain),
                        config,
                        "analysis2.destination",
                        candidate,
                        branch_half,
                        comparator,
                    ),
                }
                raw_tests.append(test)
                cell["comparisons"].append(test)
            output.append(cell)
    adjusted = holm_adjust([row["p_raw"] for row in raw_tests])
    for row, p_value in zip(raw_tests, adjusted):
        row["p_holm"] = p_value
        row["passes"] = bool(row["directional_ci"] and p_value < 0.05)
    for cell in output:
        cell["passes"] = bool(
            cell["eligible"] and all(row["passes"] for row in cell["comparisons"])
        )
    return output


def _all(rows: list[dict[str, Any]], key: str = "passes") -> bool:
    return bool(rows and all(bool(row.get(key)) for row in rows))


def analyze_confirmation(
    cells: Path,
    predictor_path: Path,
    config: Campaign2Config,
    destination: Path,
    integrity: dict[str, bool],
) -> dict[str, Any]:
    predictors = joblib.load(predictor_path)
    if predictors.get("format") != "fep-surprise-2-predictors-v1":
        raise ValueError("unsupported Experiment 2 predictors")
    intervention = _intervention_checks(cells, config)
    prediction = _prediction_checks(cells, predictors, config)
    destination_tests = _destination_checks(cells, config)

    departure_comparisons = [
        comparison
        for cell in prediction
        for comparison in cell["comparisons"]
        if comparison["endpoint"] in ("break", "latency")
        and comparison["comparison"] == "landscape_vs_physical"
    ]
    strict_comparisons = [
        comparison
        for cell in prediction
        for comparison in cell["comparisons"]
        if comparison["endpoint"] == "strict8"
        and comparison["comparison"] in (
            "landscape_vs_physical",
            "landscape_vs_local",
        )
    ]
    departure_randomization = [
        cell["outcome_permutation"]["break"] for cell in prediction
    ]
    strict_randomization = [
        cell["outcome_permutation"]["strict8"] for cell in prediction
    ]
    gates = {
        "tier_a_physical_control": bool(
            _all(intervention["isomorphism"])
            and _all(intervention["analytic_alignment"])
        ),
        "tier_a_positive_rulebook_mismatch": _all(
            intervention["positive_mismatch"]
        ),
        "tier_a_graded_intrinsic_dose": _all(intervention["dose_trends"]),
        "tier_b_departure_prediction": _all(departure_comparisons),
        "tier_b_event_specific_departure": _all(departure_randomization),
        "tier_c_joint_strict8_prediction": _all(strict_comparisons),
        "tier_c_event_specific_strict8": _all(strict_randomization),
        "tier_d_destination_capture": _all(destination_tests),
    }
    integrity_valid = bool(integrity and all(integrity.values()))
    scientific_eligible = config.profile == "full"
    if not integrity_valid:
        scientific_verdict = "INVALID_NO_SCIENTIFIC_VERDICT"
    elif not scientific_eligible:
        scientific_verdict = "NONSCIENTIFIC_PROFILE"
    elif all(gates.values()):
        scientific_verdict = "FULL_REHOMING_HYPOTHESIS_SUPPORTED"
    elif all(
        gates[key]
        for key in (
            "tier_a_physical_control",
            "tier_a_positive_rulebook_mismatch",
            "tier_a_graded_intrinsic_dose",
            "tier_b_departure_prediction",
            "tier_b_event_specific_departure",
            "tier_c_joint_strict8_prediction",
            "tier_c_event_specific_strict8",
        )
    ):
        scientific_verdict = "DEPARTURE_AND_STRICT8_SUPPORTED_DESTINATION_NOT_SUPPORTED"
    elif all(
        gates[key]
        for key in (
            "tier_a_physical_control",
            "tier_a_positive_rulebook_mismatch",
            "tier_a_graded_intrinsic_dose",
            "tier_b_departure_prediction",
            "tier_b_event_specific_departure",
        )
    ):
        scientific_verdict = "RULEBOOK_MISMATCH_PREDICTS_DEPARTURE_ONLY"
    elif gates["tier_a_physical_control"]:
        scientific_verdict = "PHYSICAL_INTERVENTION_VALID_LANDSCAPE_NOT_SUPPORTED"
    else:
        scientific_verdict = "HYPOTHESIS_NOT_SUPPORTED"
    metrics: dict[str, Any] = {
        "format": "fep-surprise-2-analysis-v1",
        "integrity": integrity,
        "intervention": intervention,
        "prediction": prediction,
        "destination": destination_tests,
        "gates": gates,
        "decision": {
            "integrity_verdict": "VALID" if integrity_valid else "INVALID",
            "scientific_verdict": scientific_verdict,
            "profile_is_scientifically_eligible": scientific_eligible,
            "claim_boundary": (
                "At most, simulator-specific rulebook-conditioned rehoming; "
                "not FEP, active inference, cognition, autonomous control, "
                "prebiotic chemistry, or a universal origin-of-life mechanism."
            ),
        },
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True, allow_nan=True) + "\n",
        encoding="utf-8",
    )
    passed = sum(int(value) for value in gates.values())
    report = [
        "# Experiment 2 report",
        "",
        f"**Integrity verdict:** `{metrics['decision']['integrity_verdict']}`  ",
        f"**Scientific verdict:** `{scientific_verdict}`",
        "",
        "## Bottom line",
        "",
        f"{passed}/{len(gates)} preregistered tier gates passed. "
        "The tiers deliberately separate intervention validity, departure, "
        "strict-8 prediction, and destination capture so a partial result cannot "
        "be promoted into the full rehoming claim.",
        "",
        "## Gate table",
        "",
        "| Gate | Pass |",
        "|---|---:|",
        *[f"| {name} | {'yes' if value else 'no'} |" for name, value in gates.items()],
        "",
        "## Interpretation boundary",
        "",
        metrics["decision"]["claim_boundary"],
        "",
        "Full numerical results, calibration metrics, ranking metrics, whole-matrix "
        "intervals, multiplicity-adjusted tests, and arm-label randomization gates "
        "are in `metrics.json`.",
    ]
    (destination / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return metrics
