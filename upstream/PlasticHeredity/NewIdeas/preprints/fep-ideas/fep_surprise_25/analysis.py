from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
from sklearn.linear_model import LogisticRegression

from fep_surprise_15.predictor import log_loss
from plastic_heredity.seeds import derive_seed

from .config import ARMS, Campaign25Config
from .worker import load_design, load_futures


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -40.0, 40.0)))


def _fit_predict(
    train_x: np.ndarray,
    train_y: np.ndarray,
    test_x: np.ndarray,
    c: float,
) -> np.ndarray:
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0, ddof=0)
    scale = np.where(np.isfinite(scale) & (scale >= 1e-8), scale, 1.0)
    prevalence = float(np.clip(train_y.mean(), 1e-6, 1 - 1e-6))
    if len(np.unique(train_y)) < 2:
        return np.full(len(test_x), prevalence)
    model = LogisticRegression(
        C=float(c), solver="lbfgs", max_iter=2_000, random_state=0
    ).fit((train_x - mean) / scale, train_y)
    return model.predict_proba((test_x - mean) / scale)[:, 1]


def _crossfit(
    values: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    folds: int,
    c: float,
) -> np.ndarray:
    unique = np.unique(groups)
    if len(unique) < 2:
        return _fit_predict(values, labels, values, c)
    count = max(2, min(int(folds), len(unique)))
    output = np.full(len(labels), np.nan)
    for fold in range(count):
        test_groups = unique[np.arange(len(unique)) % count == fold]
        test = np.isin(groups, test_groups)
        output[test] = _fit_predict(values[~test], labels[~test], values[test], c)
    if not np.isfinite(output).all():
        raise RuntimeError("matrix-group cross-fit left unscored rows")
    return output


def _holm(pvalues: list[float]) -> list[float]:
    if not pvalues:
        return []
    order = np.argsort(pvalues)
    adjusted = np.ones(len(pvalues))
    running = 0.0
    total = len(pvalues)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (total - rank) * pvalues[index]))
        adjusted[index] = running
    return adjusted.tolist()


def _paired_inference(
    values: np.ndarray, repetitions: int, seed: int
) -> dict[str, Any]:
    data = np.asarray(values, dtype=float)
    data = data[np.isfinite(data)]
    if not len(data):
        return {"estimate": None, "ci95": [None, None], "p": 1.0, "n": 0}
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(data), size=(repetitions, len(data)))
    boot = data[indices].mean(axis=1)
    signs = rng.choice(np.asarray([-1.0, 1.0]), size=(repetitions, len(data)))
    randomized = (signs * data).mean(axis=1)
    estimate = float(data.mean())
    return {
        "estimate": estimate,
        "ci95": np.quantile(boot, [0.025, 0.975]).tolist(),
        "p": float((1 + np.count_nonzero(randomized >= estimate)) / (repetitions + 1)),
        "n": int(len(data)),
    }


def _unpaired_inference(
    left: np.ndarray, right: np.ndarray, repetitions: int, seed: int
) -> dict[str, Any]:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if not len(a) or not len(b):
        return {"estimate": None, "ci95": [None, None], "p": 1.0, "n": [len(a), len(b)]}
    rng = np.random.default_rng(seed)
    boot = np.asarray(
        [
            rng.choice(a, len(a), replace=True).mean()
            - rng.choice(b, len(b), replace=True).mean()
            for _ in range(repetitions)
        ]
    )
    pooled = np.r_[a, b]
    observed = float(a.mean() - b.mean())
    null = []
    for _ in range(repetitions):
        shuffled = rng.permutation(pooled)
        null.append(float(shuffled[: len(a)].mean() - shuffled[len(a) :].mean()))
    return {
        "estimate": observed,
        "ci95": np.quantile(boot, [0.025, 0.975]).tolist(),
        "p": float((1 + np.count_nonzero(np.asarray(null) >= observed)) / (repetitions + 1)),
        "n": [int(len(a)), int(len(b))],
    }


def _profile_summary(profile: dict[str, Any], key: str) -> tuple[float, float]:
    values = np.asarray(profile.get(key, []), dtype=float)
    if not len(values):
        return 0.0, 0.0
    selected = values > 0
    return (
        float(-np.sum(values[selected] * np.log(values[selected]))),
        float(np.max(values)),
    )


def _rows(cells: Path) -> dict[str, np.ndarray]:
    collected: dict[str, list[Any]] = defaultdict(list)
    for design_path in sorted(cells.glob("cell_*_design.joblib")):
        future_path = design_path.with_name(
            design_path.name.replace("_design.joblib", "_futures.joblib")
        )
        design = load_design(design_path)
        future = load_futures(future_path)
        meta = design["metadata"]
        branch_count = future["strict8"].shape[2]
        for landmark_index, landmark in enumerate(future["landmarks"]):
            for arm_index, arm in enumerate(ARMS):
                pilot = design["pilots"][landmark_index][arm_index]
                pilot_features = np.asarray(
                    [
                        pilot["break_probability"],
                        pilot["complete_fraction"],
                        pilot["destination_entropy"],
                        pilot["destination_maximum"],
                    ]
                )
                one_hot = np.eye(len(ARMS), dtype=float)[arm_index]
                physical = np.r_[
                    design["baseline"][landmark_index],
                    design["launch_metrics"][landmark_index, arm_index],
                    one_hot,
                ]
                regime = np.r_[physical, design["regime"][landmark_index]]
                pilot_vector = np.r_[regime, pilot_features]
                for branch in range(branch_count):
                    collected["matrix"].append(int(meta["matrix_id"]))
                    collected["candidate"].append(str(meta["candidate"]))
                    collected["stratum"].append(str(meta["stratum"]))
                    collected["landmark"].append(int(landmark))
                    collected["arm"].append(arm)
                    collected["arm_index"].append(arm_index)
                    collected["branch"].append(branch)
                    collected["branch_half"].append(
                        "A" if branch < branch_count // 2 else "B"
                    )
                    collected["strict8"].append(
                        int(future["strict8"][landmark_index, arm_index, branch])
                    )
                    collected["departed"].append(
                        int(future["departed"][landmark_index, arm_index, branch])
                    )
                    collected["complete"].append(
                        int(future["complete"][landmark_index, arm_index, branch])
                    )
                    collected["destination"].append(
                        int(future["destination"][landmark_index, arm_index, branch])
                    )
                    collected["followed"].append(
                        int(future["durability_followed"][landmark_index, arm_index, branch])
                    )
                    collected["durable16"].append(
                        int(future["durable16"][landmark_index, arm_index, branch])
                    )
                    collected["durability_complete"].append(
                        int(future["durability_complete"][landmark_index, arm_index, branch])
                    )
                    collected["durable_destination"].append(
                        int(future["durable_destination"][landmark_index, arm_index, branch])
                    )
                    collected["physical"].append(physical)
                    collected["regime"].append(regime)
                    collected["pilot"].append(pilot_vector)
                    for observer in ("shelf", "invariant_knn"):
                        jump = design["mismatch_jump"][observer][landmark_index, arm_index]
                        for half in range(2):
                            j = float(jump[half])
                            local = float(
                                design["launch_metrics"][landmark_index, arm_index, -1]
                            )
                            collected[f"{observer}_{half}"].append(
                                np.r_[pilot_vector, j, j * j, j * local]
                            )
                    profile = design["shelf_profiles"][landmark_index][arm_index]
                    collected["profile"].append(profile)
                    collected["pilot_destination"].append(
                        np.asarray(pilot["destination_probability"], dtype=float)
                    )
    output = {}
    object_keys = {
        "candidate", "stratum", "arm", "branch_half", "profile", "pilot_destination"
    }
    for key, values in collected.items():
        output[key] = np.asarray(values, dtype=object if key in object_keys else None)
    return output


def _matrix_values(
    data: dict[str, np.ndarray], mask: np.ndarray, value: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    matrices = np.unique(data["matrix"][mask])
    means = np.asarray(
        [np.mean(value[mask & (data["matrix"] == matrix)]) for matrix in matrices]
    )
    return matrices, means


def _apply_holm(results: dict[str, dict[str, Any]]) -> None:
    adjusted = _holm([float(value["p"]) for value in results.values()])
    for value, p_adjusted in zip(results.values(), adjusted):
        value["holm_p"] = p_adjusted
        low = value["ci95"][0]
        value["pass"] = bool(
            low is not None and float(low) > 0 and p_adjusted < 0.05
        )


def _prediction_gates(
    data: dict[str, np.ndarray], config: Campaign25Config
) -> dict[str, Any]:
    output: dict[str, Any] = {"blocks": {}}
    for candidate in ("02", "03"):
        for branch_half in ("A", "B"):
            mask = (data["candidate"] == candidate) & (
                data["branch_half"] == branch_half
            )
            y = data["strict8"][mask].astype(np.int8)
            groups = data["matrix"][mask].astype(np.int64)
            predictions = {
                family: _crossfit(
                    np.stack(data[family][mask]),
                    y,
                    groups,
                    config.crossfit_folds,
                    config.predictor_c,
                )
                for family in ("physical", "regime", "pilot")
            }
            losses = {
                family: -(
                    y * np.log(np.clip(value, 1e-12, 1 - 1e-12))
                    + (1 - y) * np.log(np.clip(1 - value, 1e-12, 1 - 1e-12))
                )
                for family, value in predictions.items()
            }
            block = f"c{candidate}_half{branch_half}"
            _, dynamic_values = _matrix_values(
                {key: value[mask] for key, value in data.items()},
                np.ones(mask.sum(), dtype=bool),
                losses["physical"] - losses["regime"],
            )
            _, pilot_values = _matrix_values(
                {key: value[mask] for key, value in data.items()},
                np.ones(mask.sum(), dtype=bool),
                losses["regime"] - losses["pilot"],
            )
            output["blocks"][block] = {
                "dynamic_regime_gain": _paired_inference(
                    dynamic_values,
                    config.bootstrap_repetitions,
                    derive_seed(config.master_seed, "experiment25.analysis.dynamic", block),
                ),
                "pilot_gain": _paired_inference(
                    pilot_values,
                    config.bootstrap_repetitions,
                    derive_seed(config.master_seed, "experiment25.analysis.pilot", block),
                ),
                "prevalence": float(y.mean()),
                "rows": int(len(y)),
            }
            for observer in ("shelf", "invariant_knn"):
                for half in range(2):
                    family = f"{observer}_{half}"
                    prediction = _crossfit(
                        np.stack(data[family][mask]), y, groups,
                        config.crossfit_folds, config.predictor_c,
                    )
                    enhanced_loss = -(
                        y * np.log(np.clip(prediction, 1e-12, 1 - 1e-12))
                        + (1 - y) * np.log(np.clip(1 - prediction, 1e-12, 1 - 1e-12))
                    )
                    _, values = _matrix_values(
                        {key: value[mask] for key, value in data.items()},
                        np.ones(mask.sum(), dtype=bool),
                        losses["pilot"] - enhanced_loss,
                    )
                    output["blocks"][block][f"{observer}_half{half}_gain"] = (
                        _paired_inference(
                            values,
                            config.bootstrap_repetitions,
                            derive_seed(
                                config.master_seed,
                                "experiment25.analysis.surprise",
                                block,
                                observer,
                                half,
                            ),
                        )
                    )
    for metric in ("dynamic_regime_gain", "pilot_gain"):
        family = {key: value[metric] for key, value in output["blocks"].items()}
        _apply_holm(family)
    for observer in ("shelf", "invariant_knn"):
        family = {
            f"{block}_atlas{half}": values[f"{observer}_half{half}_gain"]
            for block, values in output["blocks"].items()
            for half in range(2)
        }
        _apply_holm(family)
    output["dynamic_regime_all_blocks"] = all(
        value["dynamic_regime_gain"]["pass"]
        for value in output["blocks"].values()
    )
    output["pilot_all_blocks"] = all(
        value["pilot_gain"]["pass"] for value in output["blocks"].values()
    )
    output["shelf_surprise_all_blocks"] = all(
        values[f"shelf_half{half}_gain"]["pass"]
        for values in output["blocks"].values()
        for half in range(2)
    )
    output["knn_surprise_all_blocks_exploratory"] = all(
        values[f"invariant_knn_half{half}_gain"]["pass"]
        for values in output["blocks"].values()
        for half in range(2)
    )
    return output


def _contrast_gates(data: dict[str, np.ndarray], config: Campaign25Config) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {}
    for candidate in ("02", "03"):
        for half in ("A", "B"):
            base = (data["candidate"] == candidate) & (data["branch_half"] == half)
            block = f"c{candidate}_half{half}"
            arm = data["arm"]
            stable = base & (data["stratum"] == "stable") & (arm == "PERM_NATIVE")
            saturated = base & (data["stratum"] == "saturated") & (arm == "PERM_NATIVE")
            _, stable_rate = _matrix_values(data, stable, data["strict8"])
            _, saturated_rate = _matrix_values(data, saturated, data["strict8"])
            results[f"stable_over_saturated::{block}"] = _unpaired_inference(
                stable_rate, saturated_rate, config.bootstrap_repetitions,
                derive_seed(config.master_seed, "experiment25.analysis.stable", block),
            )
            transitional = base & (data["stratum"] == "transitional")

            def conditional(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
                matrices = np.unique(data["matrix"][mask])
                values, retained = [], []
                for matrix in matrices:
                    selected = mask & (data["matrix"] == matrix)
                    denominator = int(data["departed"][selected].sum())
                    if denominator:
                        retained.append(matrix)
                        values.append(float(data["strict8"][selected].sum() / denominator))
                return np.asarray(retained), np.asarray(values)

            central = transitional & np.isin(arm, ["PERM_SIGMA_325", "PERM_NATIVE"])
            endpoint = transitional & np.isin(arm, ["PERM_SIGMA_250", "PERM_SIGMA_500"])
            central_m, central_v = conditional(central)
            endpoint_m, endpoint_v = conditional(endpoint)
            common = np.intersect1d(central_m, endpoint_m)
            central_map = dict(zip(central_m.tolist(), central_v.tolist()))
            endpoint_map = dict(zip(endpoint_m.tolist(), endpoint_v.tolist()))
            gold = np.asarray([central_map[m] - endpoint_map[m] for m in common])
            results[f"goldilocks::{block}"] = _paired_inference(
                gold, config.bootstrap_repetitions,
                derive_seed(config.master_seed, "experiment25.analysis.goldilocks", block),
            )
            perm = transitional & (arm == "PERM_SIGMA_325")
            aligned = transitional & (arm == "ALIGNED_SIGMA_325")
            perm_m, perm_v = conditional(perm)
            aligned_m, aligned_v = conditional(aligned)
            common = np.intersect1d(perm_m, aligned_m)
            pmap, amap = dict(zip(perm_m.tolist(), perm_v.tolist())), dict(zip(aligned_m.tolist(), aligned_v.tolist()))
            mismatch = np.asarray([pmap[m] - amap[m] for m in common])
            results[f"central_mismatch::{block}"] = _paired_inference(
                mismatch, config.bootstrap_repetitions,
                derive_seed(config.master_seed, "experiment25.analysis.mismatch", block),
            )
            normalized = base & (arm == "NORMALIZED_MORPH_050")
            raw = base & (arm == "RAW_MORPH_050")
            nm, nv = _matrix_values(data, normalized, data["strict8"])
            rm, rv = _matrix_values(data, raw, data["strict8"])
            common = np.intersect1d(nm, rm)
            nmap, rmap = dict(zip(nm.tolist(), nv.tolist())), dict(zip(rm.tolist(), rv.tolist()))
            morph = np.asarray([nmap[m] - rmap[m] for m in common])
            results[f"normalized_over_raw::{block}"] = _paired_inference(
                morph, config.bootstrap_repetitions,
                derive_seed(config.master_seed, "experiment25.analysis.morph", block),
            )
    _apply_holm(results)
    families = {}
    for prefix in (
        "stable_over_saturated", "goldilocks", "central_mismatch", "normalized_over_raw"
    ):
        members = {key: value for key, value in results.items() if key.startswith(prefix + "::")}
        families[prefix] = {
            "blocks": members,
            "all_pass": all(value["pass"] for value in members.values()),
        }
    return {
        "tests": results,
        "families": families,
        "all_primary_regime_contrasts": all(
            value["all_pass"] for value in families.values()
        ),
    }


def _destination_gate(data: dict[str, np.ndarray], config: Campaign25Config) -> dict[str, Any]:
    blocks = {}
    for candidate in ("02", "03"):
        for half in ("A", "B"):
            base = (
                (data["candidate"] == candidate)
                & (data["branch_half"] == half)
                & (data["stratum"] == "stable")
                & (data["destination"] >= 0)
            )
            gains, matrices = [], []
            for index in np.flatnonzero(base):
                profile = data["profile"][index]
                pilot = np.asarray(data["pilot_destination"][index], dtype=float)
                occupancy = np.asarray(profile.get("occupancy", []), dtype=float)
                label = int(data["destination"][index])
                if not profile.get("eligible") or label >= len(pilot) or label >= len(occupancy):
                    continue
                gains.append(
                    float(np.log(max(pilot[label], 1e-12)) - np.log(max(occupancy[label], 1e-12)))
                )
                matrices.append(int(data["matrix"][index]))
            matrix_values = []
            for matrix in np.unique(matrices):
                matrix_values.append(
                    np.mean([gain for gain, group in zip(gains, matrices) if group == matrix])
                )
            block = f"c{candidate}_half{half}"
            result = _paired_inference(
                np.asarray(matrix_values), config.bootstrap_repetitions,
                derive_seed(config.master_seed, "experiment25.analysis.destination", block),
            )
            result["events"] = len(gains)
            result["matrices"] = len(np.unique(matrices))
            result["eligible"] = bool(
                len(gains) >= config.destination_min_events
                and len(np.unique(matrices)) >= config.destination_min_matrices
            )
            blocks[block] = result
    _apply_holm(blocks)
    return {
        "blocks": blocks,
        "all_eligible_and_pass": all(
            result["eligible"] and result["pass"] for result in blocks.values()
        ),
    }


def _durability_gate(data: dict[str, np.ndarray], config: Campaign25Config) -> dict[str, Any]:
    selected_arms = np.isin(
        data["arm"], ["PERM_SIGMA_325", "PERM_NATIVE", "NORMALIZED_MORPH_050"]
    )
    blocks = {}
    for candidate in ("02", "03"):
        for half in ("A", "B"):
            mask = (
                (data["candidate"] == candidate)
                & (data["branch_half"] == half)
                & selected_arms
                & (data["followed"] == 1)
            )
            matrices, values = _matrix_values(data, mask, data["durable16"])
            block = f"c{candidate}_half{half}"
            result = _paired_inference(
                values - 0.5, config.bootstrap_repetitions,
                derive_seed(config.master_seed, "experiment25.analysis.durability", block),
            )
            result["events"] = int(mask.sum())
            result["matrices"] = int(len(matrices))
            result["complete_fraction"] = (
                float(data["durability_complete"][mask].mean()) if mask.any() else None
            )
            blocks[block] = result
    _apply_holm(blocks)
    return {
        "blocks": blocks,
        "all_blocks_majority_durable": all(value["pass"] for value in blocks.values()),
    }


def analyze_confirmation(
    cells: Path,
    config: Campaign25Config,
    destination: Path,
    integrity: dict[str, bool],
) -> dict[str, Any]:
    data = _rows(cells)
    prediction = _prediction_gates(data, config)
    contrasts = _contrast_gates(data, config)
    destinations = _destination_gate(data, config)
    durability = _durability_gate(data, config)
    integrity_valid = bool(all(integrity.values()))
    scientific_profile = config.profile == "full"
    if not scientific_profile:
        regime_verdict = dynamic_verdict = surprise_verdict = durability_verdict = "NONSCIENTIFIC_PROFILE"
    else:
        regime_verdict = (
            "REGIME_GATED_REHOMING_SUPPORTED"
            if contrasts["all_primary_regime_contrasts"]
            else "REGIME_GATED_REHOMING_NOT_SUPPORTED"
        )
        dynamic_verdict = (
            "DYNAMIC_REGIME_PREDICTIVE"
            if prediction["dynamic_regime_all_blocks"]
            else "DYNAMIC_REGIME_NOT_PREDICTIVE"
        )
        surprise_verdict = (
            "CONDITIONAL_SURPRISE_ADDS_VALUE"
            if prediction["shelf_surprise_all_blocks"]
            else "SURPRISE_NOT_INCREMENTAL"
        )
        durability_verdict = (
            "DURABLE_SELECTED_LINEAGE_REHOMING"
            if durability["all_blocks_majority_durable"]
            else "TRANSIENT_REGIME_GATED_RECAPTURE"
        )
    decision = {
        "integrity_verdict": "VALID" if integrity_valid else "INVALID",
        "profile_is_scientifically_eligible": scientific_profile,
        "regime_verdict": regime_verdict,
        "dynamic_prediction_verdict": dynamic_verdict,
        "fep_incremental_verdict": surprise_verdict,
        "durability_verdict": durability_verdict,
        "destination_committor_supported": bool(destinations["all_eligible_and_pass"]),
        "claim_boundary": (
            "Simulator-specific dynamic-regime and calibrated-surprise results only; "
            "no variational-free-energy, active-inference, cognition, autonomy, "
            "prebiotic-chemistry, universal-origin, or Platonic-causation claim."
        ),
    }
    metrics = {
        "format": "fep-surprise-25-metrics-v1",
        "decision": decision,
        "integrity": integrity,
        "prediction": prediction,
        "regime_contrasts": contrasts,
        "destination": destinations,
        "durability": durability,
        "counts": {
            "rows": int(len(data["strict8"])),
            "strict8": int(data["strict8"].sum()),
            "departed": int(data["departed"].sum()),
            "terminal_prefixes": int(np.count_nonzero(data["complete"] == 0)),
            "durability_followed": int(data["followed"].sum()),
        },
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = (
        "# Experiment 2.5 report\n\n"
        f"- Integrity: **{decision['integrity_verdict']}**\n"
        f"- Regime gate: **{regime_verdict}**\n"
        f"- Dynamic prediction: **{dynamic_verdict}**\n"
        f"- Conditional surprise: **{surprise_verdict}**\n"
        f"- Durability: **{durability_verdict}**\n\n"
        "The claim boundary in `metrics.json` is part of this adjudication.\n"
    )
    (destination / "REPORT.md").write_text(report, encoding="utf-8")
    return metrics
