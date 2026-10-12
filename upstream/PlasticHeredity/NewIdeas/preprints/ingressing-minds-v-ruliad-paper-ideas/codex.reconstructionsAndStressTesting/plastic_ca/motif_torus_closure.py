"""Stage-6Q torus-equivariant closure of the Stage-6P motion lead."""

from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Callable, Sequence

import numpy as np

from . import motif_acquisition_repair as ar
from . import motif_causal_attractor as cn
from . import motif_counterfactual_carrier as co
from . import motif_inverse_distillation as il
from . import motif_latent_regeneration as lm
from . import motif_phenotype_bridge as pb
from . import motif_polarity_closure as pc
from . import motif_writer_closure as wc
from .life_family import life_rule_notation


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_TORUS_CLOSURE_PROTOCOL.md"
DISCOVERY_LOG = ROOT / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"
DEFAULT_STAGE6P_ROOT = ROOT / "results/ca-motif-polarity-closure-stage-6p"
DEFAULT_STAGE6O_ROOT = pc.DEFAULT_STAGE6O_ROOT
DEFAULT_STAGE6N_ROOT = pc.DEFAULT_STAGE6N_ROOT
DEFAULT_STAGE6M_ROOT = pc.DEFAULT_STAGE6M_ROOT
DEFAULT_STAGE6L_ROOT = pc.DEFAULT_STAGE6L_ROOT
DEFAULT_STAGE6K_ROOT = il.DEFAULT_STAGE6K_ROOT
PARENT_STAGE6P_DIGEST = (
    "c1e4e99e5bfc034c04630b5bf29caa793848c4856b28ca4f659d2fbd377102fe"
)
PHASES = (
    "integrity",
    "observer-audit",
    "allocation",
    "spatial-writer-fit",
    "paired-spatial-screen",
    "fresh-spatial-validation",
    "spatial-endurance",
    "adjudicate",
)


@dataclass(frozen=True)
class TorusClosureProfile:
    motion_scan_per_rule: int
    motion_development_pairs: int
    motion_screen_pairs: int
    motion_validation_pairs: int
    screen_generations: int
    validation_generations: int
    maximum_advanced_candidates: int


PROFILES = {
    "smoke": TorusClosureProfile(512, 4, 1, 2, 2, 2, 2),
    "reference": TorusClosureProfile(8192, 40, 8, 24, 4, 8, 2),
}


@dataclass(frozen=True)
class TorusClosureContract(pc.PolarityClosureContract):
    implementation_version: str = "ca-motif-torus-closure-v1"
    namespace: str = "plastic-ca-motif-torus-closure-v1"
    placement_generation4_minimum: float = 0.60
    placement_generation8_minimum: float = 0.55
    zero_noise_placement_minimum: float = 0.75
    placement_difference_maximum: float = 0.05
    outgoing_code_agreement_minimum: float = 0.90
    bitwise_equivariance_minimum: float = 0.90
    standard_noise_degradation_maximum: float = 0.20

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "placement_generation4_minimum": self.placement_generation4_minimum,
                "placement_generation8_minimum": self.placement_generation8_minimum,
                "zero_noise_placement_minimum": self.zero_noise_placement_minimum,
                "placement_difference_maximum": self.placement_difference_maximum,
                "outgoing_code_agreement_minimum": self.outgoing_code_agreement_minimum,
                "bitwise_equivariance_minimum": self.bitwise_equivariance_minimum,
                "standard_noise_degradation_maximum": self.standard_noise_degradation_maximum,
                "observer": "largest-empty-gap-torus-signature",
                "noise_pairing": "common-random-numbers-across-placement",
                "final_reserve_policy": "unreachable-and-never-open-in-stage-6q",
            }
        )
        return payload


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _empty(reason: str) -> dict[str, Any]:
    return {
        "state": "complete",
        "stage_gate": False,
        "skipped_reason": reason,
        "final_audit_trajectory_state": "untouched",
    }


def _parent_integrity(
    stage6p_root: Path = DEFAULT_STAGE6P_ROOT,
    stage6o_root: Path = DEFAULT_STAGE6O_ROOT,
    stage6n_root: Path = DEFAULT_STAGE6N_ROOT,
    stage6m_root: Path = DEFAULT_STAGE6M_ROOT,
    stage6l_root: Path = DEFAULT_STAGE6L_ROOT,
) -> dict[str, Any]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "MANIFEST.json",
        "STAGE_DECISION.json",
        "stage6p/COHORTS.json",
        "stage6p/MOTION_VALIDATION_BANK.json",
        "stage6p/motion-fit/MODELS.json",
        "stage6p/motion-validation/RESULTS.json",
        "COMPLETE",
    )
    missing = [str(stage6p_root / name) for name in required if not (stage6p_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6P artifacts: {missing}")
    result = _load_json(stage6p_root / "RESULTS.json")
    status = _load_json(stage6p_root / "STATUS.json")
    design = _load_json(stage6p_root / "DESIGN.json")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6Q requires a complete Stage-6P parent")
    if result.get("design_digest") != PARENT_STAGE6P_DIGEST:
        raise ValueError("Stage-6Q parent Stage-6P design is not the frozen run")
    if result.get("verdict") != "NO_POLARITY_OR_COMPACT_CLOSURE":
        raise ValueError("Stage-6Q requires the registered Stage-6P boundary")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6P final reserve was touched")
    expected = design.get("implementation_hashes", {}).get(
        "motif_polarity_closure.py"
    )
    if expected != ar._sha256(Path(pc.__file__)):
        raise ValueError("Stage-6P implementation changed after its frozen run")
    ancestry = pc._parent_integrity(
        stage6o_root, stage6n_root, stage6m_root, stage6l_root
    )
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "parent_result_sha256": ar._sha256(stage6p_root / "RESULTS.json"),
        "stage6p_required_hashes": {
            name: ar._sha256(stage6p_root / name) for name in required
        },
        "procedural_pair_ids_sha256": ancestry["procedural_pair_ids_sha256"],
        "procedural_trajectories_sealed": True,
        "final_pair_count": 62,
        "final_pair_ids_sha256": ancestry["final_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
    }


def _axis_arc(values: np.ndarray, extent: int) -> tuple[np.ndarray, int]:
    coordinates = np.asarray(values, dtype=np.int64) % int(extent)
    unique = np.unique(coordinates)
    if not len(unique):
        return coordinates, 0
    if len(unique) == 1:
        start = int(unique[0])
    else:
        gaps = np.diff(np.concatenate((unique, unique[:1] + int(extent))))
        gap_index = int(np.argmax(gaps))
        start = int(unique[(gap_index + 1) % len(unique)])
    return ((coordinates - start) % int(extent)).astype(np.int64), start


def _torus_translation_signature(
    state: np.ndarray,
) -> tuple[tuple[tuple[int, int], ...], tuple[int, int]] | None:
    values = np.asarray(state, dtype=np.bool_)
    coordinates = np.argwhere(values)
    if not len(coordinates):
        return None
    ys, y_origin = _axis_arc(coordinates[:, 0], values.shape[0])
    xs, x_origin = _axis_arc(coordinates[:, 1], values.shape[1])
    signature = tuple(
        sorted((int(y), int(x)) for y, x in zip(ys, xs, strict=True))
    )
    return signature, (y_origin, x_origin)


def _signed_modular_delta(left: int, right: int, extent: int) -> int:
    value = (int(right) - int(left)) % int(extent)
    if value > int(extent) // 2:
        value -= int(extent)
    return int(value)


def _detect_mover_torus(
    history: Sequence[np.ndarray],
    *,
    start: int = 16,
    period_maximum: int = 16,
) -> dict[str, Any] | None:
    if len(history) <= start + 2:
        return None
    first = _torus_translation_signature(history[start])
    if first is None:
        return None
    shape = np.asarray(history[start]).shape
    for period in range(1, period_maximum + 1):
        if start + 2 * period >= len(history):
            break
        second = _torus_translation_signature(history[start + period])
        third = _torus_translation_signature(history[start + 2 * period])
        if second is None or third is None:
            continue
        if first[0] != second[0] or second[0] != third[0]:
            continue
        displacement = (
            _signed_modular_delta(first[1][0], second[1][0], shape[0]),
            _signed_modular_delta(first[1][1], second[1][1], shape[1]),
        )
        repeated = (
            _signed_modular_delta(second[1][0], third[1][0], shape[0]),
            _signed_modular_delta(second[1][1], third[1][1], shape[1]),
        )
        if displacement == (0, 0) or displacement != repeated:
            continue
        return {
            "period": period,
            "displacement_yx": displacement,
            "live_cells": len(first[0]),
            "detection_start": start,
            "verified_repetitions": 2,
            "torus_aware": True,
        }
    return None


def _torus_foreground_overlap(
    observed: np.ndarray, target: np.ndarray
) -> dict[str, float]:
    left = _torus_translation_signature(observed)
    right = _torus_translation_signature(target)
    if left is None or right is None:
        return {"foreground_f1": 0.0, "foreground_iou": 0.0, "mass_ratio": 0.0}
    observed_set, target_set = set(left[0]), set(right[0])
    intersection = len(observed_set & target_set)
    union = len(observed_set | target_set)
    precision = intersection / len(observed_set) if observed_set else 0.0
    recall = intersection / len(target_set) if target_set else 0.0
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision + recall > 0.0
        else 0.0
    )
    return {
        "foreground_f1": float(f1),
        "foreground_iou": float(intersection / union) if union else 0.0,
        "mass_ratio": float(len(observed_set) / len(target_set)) if target_set else 0.0,
    }


def _torus_d4_overlap(observed: np.ndarray, target: np.ndarray) -> dict[str, Any]:
    best: dict[str, Any] = {
        "foreground_f1": 0.0,
        "foreground_iou": 0.0,
        "mass_ratio": 0.0,
        "form_symmetry": 0,
    }
    for symmetry in range(8):
        transformed = il._d4_blocks(
            np.asarray(target, dtype=np.float32), symmetry
        )
        score = _torus_foreground_overlap(observed, transformed >= 0.5)
        if (score["foreground_f1"], score["foreground_iou"]) > (
            best["foreground_f1"],
            best["foreground_iou"],
        ):
            best = {**score, "form_symmetry": symmetry}
    return best


def _torus_motion_metrics(
    observed_history: Sequence[np.ndarray],
    target_history: Sequence[np.ndarray],
    instructed_displacement: Sequence[int],
    original_displacement: Sequence[int],
) -> dict[str, Any]:
    detection = _detect_mover_torus(observed_history)
    target_detection = _detect_mover_torus(target_history)
    if detection is None or target_detection is None:
        return {
            "mover_detected": False,
            "foreground_f1": 0.0,
            "foreground_iou": 0.0,
            "mass_ratio": 0.0,
            "form_symmetry": None,
            "instruction_direction_similarity": 0.0,
            "signed_original_direction_similarity": 0.0,
            "correct_instruction_direction": False,
            "form_success": False,
        }
    best: dict[str, Any] = {
        "foreground_f1": 0.0,
        "foreground_iou": 0.0,
        "mass_ratio": 0.0,
        "form_symmetry": 0,
    }
    observed_start = int(detection["detection_start"])
    target_start = int(target_detection["detection_start"])
    phases = max(int(detection["period"]), int(target_detection["period"]))
    for left_phase in range(phases):
        for right_phase in range(phases):
            score = _torus_d4_overlap(
                observed_history[min(len(observed_history) - 1, observed_start + left_phase)],
                target_history[min(len(target_history) - 1, target_start + right_phase)],
            )
            if (score["foreground_f1"], score["foreground_iou"]) > (
                best["foreground_f1"],
                best["foreground_iou"],
            ):
                best = score
    instruction = wc._velocity_similarity(
        detection["displacement_yx"], instructed_displacement
    )
    original = wc._velocity_similarity(
        detection["displacement_yx"], original_displacement
    )
    form_success = bool(
        best["foreground_f1"] >= 0.70 and 0.5 <= best["mass_ratio"] <= 2.0
    )
    return {
        "mover_detected": True,
        **best,
        "instruction_direction_similarity": float(instruction),
        "signed_original_direction_similarity": float(original),
        "correct_instruction_direction": bool(instruction > 0.5),
        "form_success": form_success,
        "detected_period": int(detection["period"]),
        "detected_displacement_yx": list(detection["displacement_yx"]),
    }


def _run_observer_audit(stage6p_root: Path) -> dict[str, Any]:
    bank = _load_json(stage6p_root / "stage6p/MOTION_VALIDATION_BANK.json")
    pair = bank["pairs"][0]
    specification = pair["forward"]
    rule = int(pair["rule"])
    initial = wc._unpack_state_hex(specification["initial_hex"], (32, 32))
    centered = wc._simulate_history(initial, rule, 48)
    signature = _torus_translation_signature(centered[16])
    if signature is None:
        raise ValueError("observer audit mover became blank")
    shift = (-int(signature[1][0]), -int(signature[1][1]))
    seam_initial = np.roll(initial, shift, axis=(0, 1))
    seam = wc._simulate_history(seam_initial, rule, 48)
    bitwise = all(
        np.array_equal(np.roll(left, shift, axis=(0, 1)), right)
        for left, right in zip(centered, seam, strict=True)
    )
    legacy_centered = wc._detect_mover(centered)
    legacy_seam = wc._detect_mover(seam)
    torus_centered = _detect_mover_torus(centered)
    torus_seam = _detect_mover_torus(seam)
    overlap = _torus_d4_overlap(seam[16], centered[16])
    gate = bool(
        legacy_centered is not None
        and legacy_seam is None
        and torus_centered is not None
        and torus_seam is not None
        and tuple(torus_centered["displacement_yx"])
        == tuple(torus_seam["displacement_yx"])
        and overlap["foreground_f1"] == 1.0
        and bitwise
    )
    return {
        "state": "complete",
        "stage_gate": gate,
        "audit_pair_id": pair["pair_id"],
        "rule": rule,
        "registered_shift_yx": list(shift),
        "legacy_centered_detected": legacy_centered is not None,
        "legacy_seam_detected": legacy_seam is not None,
        "torus_centered_detected": torus_centered is not None,
        "torus_seam_detected": torus_seam is not None,
        "torus_centered_displacement_yx": (
            list(torus_centered["displacement_yx"])
            if torus_centered is not None
            else None
        ),
        "torus_seam_displacement_yx": (
            list(torus_seam["displacement_yx"])
            if torus_seam is not None
            else None
        ),
        "torus_foreground_f1": overlap["foreground_f1"],
        "life_update_bitwise_translation_equivariant": bitwise,
        "legacy_observer_seam_exclusion_confirmed": legacy_seam is None,
        "stage6p_verdict_reinterpreted": False,
        "new_prospective_trajectories_required": True,
        "final_audit_trajectory_state": "untouched",
    }


def _augmented_motion_rows(
    pairs: Sequence[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    features: list[np.ndarray] = []
    shapes: list[np.ndarray] = []
    orientations: list[int] = []
    groups: list[str] = []
    rules: list[int] = []
    shifts = ((0, 0), (11, -13), (16, 16), (-15, 14))
    for pair in pairs:
        rule = int(pair["rule"])
        for direction in ("forward", "opposite"):
            specification = pair[direction]
            initial = wc._unpack_state_hex(specification["initial_hex"], (32, 32))
            base_history = wc._simulate_history(initial, rule, 64)
            period = int(specification["period"])
            for endpoint in range(16, 16 + period):
                canonical, _ = lm._canonicalize_motion_phase(
                    base_history,
                    endpoint,
                    period,
                    specification["displacement_yx"],
                )
                for shift in shifts:
                    history = [
                        np.roll(state, shift, axis=(0, 1)) for state in base_history
                    ]
                    base_feature = pc._wrap_motion_features(history, endpoint)
                    for symmetry in range(8):
                        blocks = il._d4_blocks(
                            base_feature[:-1].reshape(4, 8, 8), symmetry
                        )
                        features.append(
                            np.concatenate(
                                (blocks.reshape(-1), np.ones(1, dtype=np.float32))
                            )
                        )
                        velocity = il._transform_velocity(
                            specification["displacement_yx"], symmetry
                        )
                        orientations.append(lm._orientation_from_velocity(velocity))
                        shapes.append(canonical.reshape(-1))
                        groups.append(str(pair["pair_id"]))
                        rules.append(rule)
    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(shapes, dtype=np.float32),
        np.asarray(orientations, dtype=np.int8),
        np.asarray(groups, dtype=str),
        np.asarray(rules, dtype=np.int64),
    )


def _fit_augmented_model(
    pairs: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    features, shapes, orientations, groups, rules = _augmented_motion_rows(pairs)
    fold_count = min(6, len(set(groups.tolist())))
    folds = wc._pair_blocked_folds(groups, fold_count)
    fold_models: dict[str, dict[str, Any]] = {}
    fold_rows: list[dict[str, Any]] = []
    for fold in range(fold_count):
        train = folds != fold
        test = folds == fold
        model = cn._fit_motion_medoid_arrays(
            features,
            shapes,
            orientations,
            rules,
            train,
            8,
            "rule-conditioned-medoid",
            ar._hash_seed("stage6q-augmented-wrap", fold),
        )
        model["model_id"] = f"stage6q-augmented-wrap-fold{fold}"
        model["feature_mode"] = "wrap-aware-explicit-translation-augmentation"
        model["model_digest"] = _digest(model)
        fold_models[str(fold)] = model
        shape_prediction, orientation_prediction = pc._predict_head(
            model, features[test]
        )
        decoded = np.stack(
            [
                cn._medoid_for_rule(model, int(rule))[int(code) % 8]
                for code, rule in zip(
                    shape_prediction.tolist(), rules[test].tolist(), strict=True
                )
            ]
        )
        fold_rows.append(
            {
                "fold": fold,
                "foreground_f1": float(
                    np.mean(
                        [
                            cn._foreground_vector_f1(left, right)
                            for left, right in zip(decoded, shapes[test], strict=True)
                        ]
                    )
                ),
                "orientation_accuracy": float(
                    np.mean(orientation_prediction == orientations[test])
                ),
            }
        )
    model = cn._fit_motion_medoid_arrays(
        features,
        shapes,
        orientations,
        rules,
        np.ones(len(features), dtype=np.bool_),
        8,
        "rule-conditioned-medoid",
        ar._hash_seed("stage6q-augmented-wrap", "full"),
    )
    model["model_id"] = "stage6q-augmented-wrap-rule-conditioned-medoid-k8"
    model["feature_mode"] = "wrap-aware-explicit-translation-augmentation"
    model["model_digest"] = _digest(model)
    return model, fold_models, {
        "training_examples": len(features),
        "training_pair_count": len(set(groups.tolist())),
        "folds": fold_rows,
    }


def _load_k4_model(stage6n_root: Path) -> dict[str, Any]:
    path = (
        stage6n_root
        / "stage6n/motion-medoid-fit/checkpoints/"
        "rule-conditioned-medoid-k4.json"
    )
    payload = _load_json(path)
    if payload.get("design_digest") != co.PARENT_STAGE6N_DIGEST:
        raise ValueError("Stage-6N k4 motion model digest mismatch")
    return copy.deepcopy(payload["fitted"]["model"])


def _candidate_ladder(
    stage6p_root: Path,
    stage6n_root: Path,
    development_pairs: Sequence[dict[str, Any]],
    profile_name: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parent = _load_json(stage6p_root / "stage6p/motion-fit/MODELS.json")
    by_id = {row["candidate_id"]: row for row in parent["candidates"]}
    baseline = copy.deepcopy(by_id["stage6p-slow-latch-r90-e32"])
    baseline["candidate_id"] = "stage6q-stage6p-latch-r90-e32"
    wrap = copy.deepcopy(by_id["stage6p-wrap-aware-refit"])
    wrap.update(
        {
            "candidate_id": "stage6q-wrap-head-latch-r90-e32",
            "writer_kind": "slow-polarity-latch",
            "endpoint": 32,
            "latch_retention": 0.90,
            "latch_input_gain": 0.10,
            "zero_born_latch": True,
            "threefold_polarity_bit": True,
            "payload_bits": 7,
        }
    )
    augmented_model, fold_models, augmented_metadata = _fit_augmented_model(
        development_pairs
    )
    augmented = copy.deepcopy(wrap)
    augmented.update(
        {
            "candidate_id": "stage6q-augmented-wrap-latch-r90-e32",
            "model": augmented_model,
            "fold_models": fold_models,
        }
    )
    medoid = copy.deepcopy(baseline)
    medoid.update(
        {
            "candidate_id": "stage6q-torus-medoid-latch-r90-e32",
            "writer_kind": "torus-medoid-latch",
            "feature_mode": "torus-visible-medoid",
        }
    )
    medoid75 = copy.deepcopy(medoid)
    medoid75.update(
        {
            "candidate_id": "stage6q-torus-medoid-latch-r75-e32",
            "latch_retention": 0.75,
            "latch_input_gain": 0.25,
        }
    )
    k4_model = _load_k4_model(stage6n_root)
    hamming = copy.deepcopy(medoid)
    hamming.update(
        {
            "candidate_id": "stage6q-torus-medoid-k4-hamming8",
            "model": k4_model,
            "codec_kind": "extended-hamming-8-4",
            "threefold_polarity_bit": False,
            "payload_bits": 8,
        }
    )
    candidates = [baseline, wrap, augmented, medoid, medoid75, hamming]
    if profile_name == "smoke":
        candidates = [baseline, medoid, hamming]
    if len(candidates) > 8:
        raise AssertionError("Stage-6Q candidate ladder exceeds eight")
    return candidates, {
        "candidate_count": len(candidates),
        "augmented_model": augmented_metadata,
        "stage6p_parent_model_selection_reused": True,
    }


def _torus_visible_orientation(
    history: Sequence[np.ndarray],
    endpoint: int,
    retention: float,
    fallback: int,
) -> tuple[int, dict[str, Any]]:
    endpoint = min(int(endpoint), len(history) - 1)
    state = np.zeros(2, dtype=np.float32)
    observations = 0
    endpoints = list(range(min(endpoint, 16), endpoint + 1, 4))
    if not endpoints or endpoints[-1] != endpoint:
        endpoints.append(endpoint)
    for current in endpoints:
        detection = _detect_mover_torus(history[: current + 1])
        if detection is None:
            continue
        evidence = np.asarray(detection["displacement_yx"], dtype=np.float32)
        evidence /= np.float32(max(1.0, float(np.max(np.abs(evidence)))))
        state = np.float32(retention) * state + np.float32(1.0 - retention) * evidence
        observations += 1
    if observations == 0 or float(np.max(np.abs(state))) < 1e-6:
        return int(fallback), {
            "torus_velocity_detected": False,
            "torus_latch_state_yx": state.tolist(),
            "torus_latch_observations": observations,
        }
    return lm._orientation_from_velocity(state), {
        "torus_velocity_detected": True,
        "torus_latch_state_yx": state.tolist(),
        "torus_latch_observations": observations,
    }


def _nearest_medoid_shape(
    model: dict[str, Any],
    history: Sequence[np.ndarray],
    orientation: int,
    rule: int,
    endpoint: int,
) -> int:
    codebook = cn._medoid_for_rule(model, rule)
    selected = history[max(0, endpoint - 7) : endpoint + 1]
    observed = [pc._wrap_crop_centered(state) for state in selected]
    scores: list[float] = []
    for shape in range(len(codebook)):
        patch = cn._decode_motion_code(model, shape, orientation, rule) >= 0.0
        scores.append(
            min(
                float(np.mean(np.asarray(frame, dtype=np.bool_) != patch))
                for frame in observed
            )
        )
    return int(np.argmin(scores))


def _predict_candidate(
    candidate: dict[str, Any], history: Sequence[np.ndarray], rule: int
) -> tuple[int, int, dict[str, Any]]:
    if str(candidate.get("writer_kind")) != "torus-medoid-latch":
        return pc._predict_candidate(candidate, history, rule)
    base = dict(candidate)
    base["writer_kind"] = "ridge-head"
    raw_shape, raw_orientation, raw_metadata = pc._predict_candidate(
        base, history, rule
    )
    endpoint = min(len(history) - 1, int(candidate.get("endpoint", 32)))
    orientation, torus_metadata = _torus_visible_orientation(
        history,
        endpoint,
        float(candidate.get("latch_retention", 0.90)),
        raw_orientation,
    )
    shape = _nearest_medoid_shape(
        candidate["model"], history, orientation, rule, endpoint
    )
    return shape, orientation, {
        **raw_metadata,
        **torus_metadata,
        "raw_shape_code": raw_shape,
        "visible_nearest_medoid_shape": shape,
        "writer_kind": "torus-medoid-latch",
    }


def _hamming84_encode(data: Sequence[int]) -> np.ndarray:
    values = [int(value) & 1 for value in data]
    if len(values) != 4:
        raise ValueError("extended Hamming carrier requires four data bits")
    bits = np.zeros(8, dtype=np.uint8)
    bits[[2, 4, 5, 6]] = values
    bits[0] = bits[2] ^ bits[4] ^ bits[6]
    bits[1] = bits[2] ^ bits[5] ^ bits[6]
    bits[3] = bits[4] ^ bits[5] ^ bits[6]
    bits[7] = np.bitwise_xor.reduce(bits[:7])
    return bits


def _hamming84_decode(bits: Sequence[int]) -> tuple[np.ndarray, dict[str, Any]]:
    values = np.asarray(bits, dtype=np.uint8).reshape(8).copy() & 1
    syndrome = int(values[0] ^ values[2] ^ values[4] ^ values[6])
    syndrome |= int(values[1] ^ values[2] ^ values[5] ^ values[6]) << 1
    syndrome |= int(values[3] ^ values[4] ^ values[5] ^ values[6]) << 2
    overall = int(np.bitwise_xor.reduce(values))
    corrected = None
    uncorrectable = False
    if syndrome and overall:
        values[syndrome - 1] ^= np.uint8(1)
        corrected = syndrome - 1
    elif not syndrome and overall:
        values[7] ^= np.uint8(1)
        corrected = 7
    elif syndrome and not overall:
        uncorrectable = True
    data = values[[2, 4, 5, 6]].astype(np.uint8)
    return data, {
        "syndrome": syndrome,
        "overall_parity": overall,
        "corrected_bit": corrected,
        "uncorrectable_double_error": uncorrectable,
    }


def _encode_payload(
    candidate: dict[str, Any], shape: int, orientation: int
) -> np.ndarray:
    if str(candidate.get("codec_kind", "")) != "extended-hamming-8-4":
        return pc._payload_bits(candidate, shape, orientation)
    if int(candidate["model"]["shape_bits"]) != 2:
        raise ValueError("Hamming carrier requires a four-shape model")
    orientation = int(orientation) % 4
    data = (
        int(shape) & 1,
        (int(shape) >> 1) & 1,
        orientation & 1,
        (orientation >> 1) & 1,
    )
    return _hamming84_encode(data)


def _decode_payload(
    candidate: dict[str, Any], bits: np.ndarray
) -> tuple[int, int, dict[str, Any]]:
    if str(candidate.get("codec_kind", "")) != "extended-hamming-8-4":
        return pc._payload_code(candidate, bits)
    data, diagnostics = _hamming84_decode(bits)
    shape = int(data[0]) | (int(data[1]) << 1)
    orientation = int(data[2]) | (int(data[3]) << 1)
    return shape, orientation, diagnostics


SPATIAL_PLACEMENTS = ("center", "translation", "seam")
SPATIAL_COMMANDS = ("original_seed", "opposite_seed")
NOISE_LEVELS = {"zero": 0.0, "standard": 0.01}
CAUSAL_CONDITIONS = (
    "intact",
    "zero",
    "no_renewal",
    "matching_rescue",
    "opposite_rescue",
)


def _placement_center(pair_id: str, direction: str, placement: str) -> tuple[int, int]:
    if placement == "center":
        return (16, 16)
    if placement == "seam":
        return (0, 31)
    if placement != "translation":
        raise ValueError(f"unknown placement {placement!r}")
    rng = np.random.default_rng(
        ar._hash_seed("stage6q-fixed-translation", pair_id, direction)
    )
    choices = np.asarray((7, 9, 11, 21, 23, 25), dtype=np.int16)
    return (int(rng.choice(choices)), int(rng.choice(choices)))


def _aligned_history_digest(
    history: Sequence[np.ndarray], center: Sequence[int]
) -> str:
    shift = (16 - int(center[0]), 16 - int(center[1]))
    packed = np.packbits(
        np.stack(
            [np.roll(np.asarray(state, dtype=np.bool_), shift, axis=(0, 1)) for state in history]
        ).reshape(-1)
    )
    return hashlib.sha256(packed.tobytes()).hexdigest()


def _common_copy_seed(
    pair_id: str,
    direction: str,
    condition: str,
    generation: int,
    noise_name: str,
) -> int:
    """A placement-free key implements registered common random numbers."""

    return ar._hash_seed(
        "stage6q-common-copy",
        pair_id,
        direction,
        condition,
        int(generation),
        noise_name,
    )


def _spatial_lineage(
    candidate: dict[str, Any],
    pair: dict[str, Any],
    direction: str,
    condition: str,
    placement: str,
    noise_name: str,
    *,
    generations: int = 8,
) -> dict[str, Any]:
    """Run a visibly reset daughter lineage with a placement-invariant noise key."""

    if noise_name not in NOISE_LEVELS:
        raise ValueError(f"unknown noise level {noise_name!r}")
    model = candidate["model"]
    specification = pair[direction]
    rule = int(pair["rule"])
    initial = wc._unpack_state_hex(specification["initial_hex"], (32, 32))
    original_history = wc._simulate_history(initial, rule, 64)
    history = original_history[:49]
    frozen_shape, frozen_original = cn._oracle_motion_code(
        model, original_history, specification, rule
    )
    original_displacement = tuple(
        int(value) for value in specification["displacement_yx"]
    )
    diagonal = all(abs(float(value)) > 1e-6 for value in original_displacement)
    frozen_opposite = lm._opposite_orientation(frozen_original, diagonal)
    center = _placement_center(str(pair["pair_id"]), direction, placement)
    generation_rows: list[dict[str, Any]] = []
    corruption = float(NOISE_LEVELS[noise_name])
    for generation in range(1, generations + 1):
        raw_shape, raw_orientation, raw_metadata = _predict_candidate(
            candidate, history, rule
        )
        write_shape, write_orientation = raw_shape, raw_orientation
        active = True
        intervention = "learned-write"
        if condition == "original_seed" and generation == 1:
            write_shape, write_orientation = frozen_shape, frozen_original
            intervention = "frozen-original-seed-once"
        elif condition == "opposite_seed" and generation == 1:
            write_shape, write_orientation = frozen_shape, frozen_opposite
            intervention = "frozen-opposite-seed-once"
        elif condition in ("matching_rescue", "opposite_rescue") and generation == 2:
            active = False
            intervention = "carrier-ablated"
        elif condition == "matching_rescue" and generation == 3:
            write_shape, write_orientation = frozen_shape, frozen_original
            intervention = "frozen-parent-matching-rescue"
        elif condition == "opposite_rescue" and generation == 3:
            write_shape, write_orientation = frozen_shape, frozen_opposite
            intervention = "frozen-parent-opposite-rescue"
        elif condition == "zero":
            active = False
            intervention = "zero-carrier"
        elif condition == "no_renewal" and generation > 1:
            active = False
            intervention = "renewal-disabled-after-first-boundary"

        written = _encode_payload(candidate, write_shape, write_orientation)
        incoming = written.copy()
        if not active:
            incoming.fill(0)
        copy_seed = _common_copy_seed(
            str(pair["pair_id"]), direction, condition, generation, noise_name
        )
        copied, copy_exact = lm._bit_codec_roundtrip(
            incoming, copy_seed, corruption=corruption
        )
        decoded_shape, decoded_orientation, codec = _decode_payload(
            candidate, copied
        )
        patch = cn._decode_motion_code(
            model, decoded_shape, decoded_orientation, rule
        )
        if not active:
            patch = np.zeros_like(patch)
        reset = lm._install_motion_patch_at(patch, center)
        new_history = wc._simulate_history(reset, rule, 48)
        target_orientation = pc._condition_target(
            condition, generation, frozen_original, frozen_opposite
        )
        instructed = original_displacement
        if target_orientation == frozen_opposite:
            instructed = (-original_displacement[0], -original_displacement[1])
        torus_metrics = _torus_motion_metrics(
            new_history, original_history, instructed, original_displacement
        )
        legacy_metrics = co._counterfactual_motion_metrics(
            new_history, original_history, instructed, original_displacement
        )
        outgoing_shape, outgoing_orientation, outgoing_metadata = _predict_candidate(
            candidate, new_history, rule
        )
        outgoing_payload = _encode_payload(
            candidate, outgoing_shape, outgoing_orientation
        )
        generation_rows.append(
            {
                "generation": generation,
                "placement": placement,
                "translation_center": list(center),
                "noise_name": noise_name,
                "copy_corruption": corruption,
                "copy_seed": int(copy_seed),
                "intervention": intervention,
                "carrier_active": active,
                "daughter_rewrite_active": condition != "no_renewal",
                "frozen_parent_shape_code": frozen_shape,
                "frozen_parent_original_orientation": frozen_original,
                "frozen_parent_opposite_orientation": frozen_opposite,
                "target_orientation": target_orientation,
                "raw_writer_shape_code": raw_shape,
                "raw_writer_orientation": raw_orientation,
                "raw_writer_metadata": raw_metadata,
                "written_shape_code": write_shape,
                "written_orientation": write_orientation,
                "written_payload": written.astype(int).tolist(),
                "copied_payload": copied.astype(int).tolist(),
                "copy_exact": bool(copy_exact),
                "decoded_shape_code": decoded_shape,
                "decoded_orientation": decoded_orientation,
                "codec_diagnostics": codec,
                "outgoing_writer_shape_code": outgoing_shape,
                "outgoing_writer_orientation": outgoing_orientation,
                "outgoing_payload": outgoing_payload.astype(int).tolist(),
                "outgoing_polarity_correct": bool(
                    outgoing_orientation == target_orientation
                ),
                "aligned_history_sha256": _aligned_history_digest(
                    new_history, center
                ),
                "visible_reset_zero_before_carrier_read": True,
                "instructed_displacement_yx": list(instructed),
                "original_displacement_yx": list(original_displacement),
                "legacy_mover_detected": bool(legacy_metrics["mover_detected"]),
                "legacy_foreground_f1": float(legacy_metrics["foreground_f1"]),
                **torus_metrics,
            }
        )
        history = new_history
    return {
        "candidate_id": candidate["candidate_id"],
        "pair_id": pair["pair_id"],
        "rule": rule,
        "direction": direction,
        "condition": condition,
        "placement": placement,
        "noise_name": noise_name,
        "generations": generation_rows,
        "common_random_numbers_across_placement": True,
        "absolute_command_semantics": True,
        "all_boundaries_visibly_reset": True,
    }


def _public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    model = candidate["model"]
    return {
        **{
            key: copy.deepcopy(value)
            for key, value in candidate.items()
            if key not in ("model", "fold_models", "fold_calibrations")
        },
        "model_id": model["model_id"],
        "model_digest": model["model_digest"],
        "shape_bits": int(model["shape_bits"]),
        "payload_bits": int(candidate["payload_bits"]),
    }


def _lineage_metric_summary(
    lineages: Sequence[dict[str, Any]], generation: int
) -> dict[str, float]:
    selected = [
        lineage["generations"][generation - 1]
        for lineage in lineages
        if len(lineage["generations"]) >= generation
    ]
    if not selected:
        return {
            "count": 0,
            "mover_detection_fraction": 0.0,
            "form_success_fraction": 0.0,
            "instruction_direction_fraction": 0.0,
            "joint_success_fraction": 0.0,
            "foreground_f1_mean": 0.0,
            "signed_original_direction_similarity_mean": 0.0,
            "outgoing_polarity_accuracy": 0.0,
        }
    return {
        "count": len(selected),
        "mover_detection_fraction": float(
            np.mean([row["mover_detected"] for row in selected])
        ),
        "form_success_fraction": float(
            np.mean([row["form_success"] for row in selected])
        ),
        "instruction_direction_fraction": float(
            np.mean([row["correct_instruction_direction"] for row in selected])
        ),
        "joint_success_fraction": float(
            np.mean(
                [
                    row["form_success"] and row["correct_instruction_direction"]
                    for row in selected
                ]
            )
        ),
        "foreground_f1_mean": float(
            np.mean([row["foreground_f1"] for row in selected])
        ),
        "signed_original_direction_similarity_mean": float(
            np.mean(
                [row["signed_original_direction_similarity"] for row in selected]
            )
        ),
        "outgoing_polarity_accuracy": float(
            np.mean([row["outgoing_polarity_correct"] for row in selected])
        ),
    }


def _select_lineages(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    *,
    condition: str | None = None,
    placement: str | None = None,
    noise_name: str | None = None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        if row["candidate_id"] != candidate_id:
            continue
        for lineage in row["lineages"]:
            if condition is not None and lineage["condition"] != condition:
                continue
            if placement is not None and lineage["placement"] != placement:
                continue
            if noise_name is not None and lineage["noise_name"] != noise_name:
                continue
            selected.append(lineage)
    return selected


def _paired_placement_summary(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    placement: str,
    noise_name: str,
    generation: int,
) -> dict[str, float]:
    indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for lineage in _select_lineages(
        rows, candidate_id, noise_name=noise_name
    ):
        if lineage["condition"] not in SPATIAL_COMMANDS:
            continue
        key = (
            str(lineage["pair_id"]),
            str(lineage["direction"]),
            str(lineage["condition"]),
        )
        if len(lineage["generations"]) >= generation:
            indexed[(str(lineage["placement"]), *key)] = lineage["generations"][
                generation - 1
            ]
    comparisons: list[dict[str, Any]] = []
    for key, translated in indexed.items():
        if key[0] != placement:
            continue
        center = indexed.get(("center", *key[1:]))
        if center is None:
            continue
        comparisons.append(
            {
                "decoded": (
                    center["decoded_shape_code"], center["decoded_orientation"]
                )
                == (
                    translated["decoded_shape_code"],
                    translated["decoded_orientation"],
                ),
                "outgoing": (
                    center["outgoing_writer_shape_code"],
                    center["outgoing_writer_orientation"],
                )
                == (
                    translated["outgoing_writer_shape_code"],
                    translated["outgoing_writer_orientation"],
                ),
                "bitwise": center["aligned_history_sha256"]
                == translated["aligned_history_sha256"],
            }
        )
    if not comparisons:
        return {
            "count": 0,
            "decoded_code_agreement": 0.0,
            "outgoing_code_agreement": 0.0,
            "aligned_bitwise_agreement": 0.0,
        }
    return {
        "count": len(comparisons),
        "decoded_code_agreement": float(
            np.mean([row["decoded"] for row in comparisons])
        ),
        "outgoing_code_agreement": float(
            np.mean([row["outgoing"] for row in comparisons])
        ),
        "aligned_bitwise_agreement": float(
            np.mean([row["bitwise"] for row in comparisons])
        ),
    }


def _screen_pair(
    candidate: dict[str, Any],
    pair: dict[str, Any],
    fold: int,
    generations: int,
) -> dict[str, Any]:
    local = dict(candidate)
    if str(fold) in candidate.get("fold_models", {}):
        local["model"] = candidate["fold_models"][str(fold)]
    return {
        "candidate_id": candidate["candidate_id"],
        "pair_id": pair["pair_id"],
        "rule": pair["rule"],
        "fold": int(fold),
        "lineages": [
            _spatial_lineage(
                local,
                pair,
                direction,
                condition,
                placement,
                noise_name,
                generations=generations,
            )
            for direction in ("forward", "opposite")
            for condition in SPATIAL_COMMANDS
            for placement in SPATIAL_PLACEMENTS
            for noise_name in NOISE_LEVELS
        ],
    }


def _screen_candidate_summary(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
) -> dict[str, Any]:
    candidate_id = str(candidate["candidate_id"])
    recovery: dict[str, Any] = {}
    for noise_name in NOISE_LEVELS:
        recovery[noise_name] = {}
        for placement in SPATIAL_PLACEMENTS:
            recovery[noise_name][placement] = {}
            for condition in SPATIAL_COMMANDS:
                recovery[noise_name][placement][condition] = _lineage_metric_summary(
                    _select_lineages(
                        rows,
                        candidate_id,
                        condition=condition,
                        placement=placement,
                        noise_name=noise_name,
                    ),
                    generation,
                )
    paired = {
        noise_name: {
            placement: _paired_placement_summary(
                rows, candidate_id, placement, noise_name, generation
            )
            for placement in ("translation", "seam")
        }
        for noise_name in NOISE_LEVELS
    }
    standard_joint = min(
        recovery["standard"][placement][condition]["joint_success_fraction"]
        for placement in SPATIAL_PLACEMENTS
        for condition in SPATIAL_COMMANDS
    )
    zero_joint = min(
        recovery["zero"][placement][condition]["joint_success_fraction"]
        for placement in SPATIAL_PLACEMENTS
        for condition in SPATIAL_COMMANDS
    )
    form = min(
        recovery[noise][placement][condition]["foreground_f1_mean"]
        for noise in NOISE_LEVELS
        for placement in SPATIAL_PLACEMENTS
        for condition in SPATIAL_COMMANDS
    )
    outgoing = min(
        paired[noise][placement]["outgoing_code_agreement"]
        for noise in NOISE_LEVELS
        for placement in ("translation", "seam")
    )
    bitwise = min(
        paired[noise][placement]["aligned_bitwise_agreement"]
        for noise in NOISE_LEVELS
        for placement in ("translation", "seam")
    )
    placement_difference = max(
        abs(
            recovery["standard"]["center"][condition]["joint_success_fraction"]
            - recovery["standard"][placement][condition]["joint_success_fraction"]
        )
        for condition in SPATIAL_COMMANDS
        for placement in ("translation", "seam")
    )
    score = float(
        0.30 * standard_joint
        + 0.15 * zero_joint
        + 0.15 * min(1.0, form)
        + 0.20 * outgoing
        + 0.20 * bitwise
    )
    return {
        "candidate": _public_candidate(candidate),
        "screen_generation": generation,
        "recovery": recovery,
        "paired_equivariance": paired,
        "minimum_standard_joint": float(standard_joint),
        "minimum_zero_joint": float(zero_joint),
        "minimum_foreground_f1": float(form),
        "maximum_standard_placement_difference": float(placement_difference),
        "minimum_outgoing_code_agreement": float(outgoing),
        "minimum_aligned_bitwise_agreement": float(bitwise),
        "selection_score": score,
        "target_labels_used_at_runtime": False,
        "placement_labels_used_at_runtime": False,
        "common_random_numbers_across_placement": True,
        "fit_exposure": "development-only",
    }


def _run_spatial_screen(
    stage_root: Path,
    candidates: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile: TorusClosureProfile,
    profile_name: str,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Callable[..., None],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "paired-spatial-screen"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    fold_map = pc._pair_fold_map(pairs)
    generations = int(profile.screen_generations)
    jobs: list[tuple[dict[str, Any], dict[str, Any], int, Path]] = []
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        for pair in pairs[: profile.motion_screen_pairs]:
            path = checkpoints / f"{candidate['candidate_id']}-{pair['pair_id']}.json"
            if resume and path.exists():
                rows.append(_load_json(path)["row"])
            else:
                jobs.append((candidate, pair, fold_map[str(pair["pair_id"])], path))
    registered = len(candidates) * min(profile.motion_screen_pairs, len(pairs))
    completed = len(rows)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_screen_pair, candidate, pair, fold, generations): path
            for candidate, pair, fold, path in jobs
            if time.time() < deadline
        }
        for future in as_completed(futures):
            row = future.result()
            ar._atomic_json(
                futures[future], {"design_digest": design_digest, "row": row}
            )
            rows.append(row)
            completed += 1
            status(
                "running",
                "paired-center-translation-seam-screen",
                completed=completed,
                total=registered,
                candidate_id=row["candidate_id"],
            )
    complete = completed == registered
    summaries: dict[str, Any] = {}
    ranked: list[tuple[float, str, dict[str, Any]]] = []
    for candidate in candidates:
        summary = _screen_candidate_summary(rows, candidate, generations)
        summaries[str(candidate["candidate_id"])] = summary
        ranked.append(
            (
                float(summary["selection_score"]),
                str(candidate["candidate_id"]),
                candidate,
            )
        )
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    selected = [
        row[2]
        for row in ranked[: min(profile.maximum_advanced_candidates, len(ranked))]
    ]
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and selected),
        "registered_pair_candidate_tasks": registered,
        "completed_pair_candidate_tasks": completed,
        "candidate_count": len(candidates),
        "screen_pair_count": min(profile.motion_screen_pairs, len(pairs)),
        "six_pair_blocked_folds": profile_name == "reference",
        "maximum_advanced_candidates": profile.maximum_advanced_candidates,
        "selected_candidate_ids": [row["candidate_id"] for row in selected],
        "candidate_summaries": summaries,
        "common_random_numbers_across_placement": True,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, selected


def _fresh_motion_bank(
    stage_root: Path,
    stage6p_root: Path,
    stage6o_root: Path,
    stage6n_root: Path,
    stage6m_root: Path,
    stage6l_root: Path,
    stage6k_root: Path,
    profile_name: str,
    profile: TorusClosureProfile,
    contract: TorusClosureContract,
    *,
    deadline: float,
    status: Callable[..., None],
) -> dict[str, Any]:
    path = stage_root / "MOTION_VALIDATION_BANK.json"
    if path.exists():
        return _load_json(path)
    stage6p_bank = _load_json(stage6p_root / "stage6p/MOTION_VALIDATION_BANK.json")
    if profile_name == "smoke":
        pairs = list(stage6p_bank.get("pairs", []))[: profile.motion_validation_pairs]
        result = {
            "state": "complete",
            "stage_gate": len(pairs) == profile.motion_validation_pairs,
            "pairs": pairs,
            "validation_pair_count": len(pairs),
            "role": "smoke-exposed-only",
            "scientific_holdout": False,
            "frozen_before_stage6q_selection": True,
            "final_audit_trajectory_state": "untouched",
        }
        ar._atomic_json(path, result)
        return result

    banks: list[dict[str, Any]] = [
        _load_json(stage6m_root / "stage6m/MOTION_BANK.json"),
        _load_json(stage6l_root / "stage6l/MOTION_BANK.json"),
        _load_json(stage6o_root / "stage6o/MOTION_VALIDATION_BANK.json"),
        stage6p_bank,
    ]
    optional_stage6n = stage6n_root / "stage6n/MOTION_VALIDATION_BANK.json"
    if optional_stage6n.exists():
        banks.append(_load_json(optional_stage6n))
    panel = _load_json(stage6k_root / "stage6k/MOVER_PANEL.json")
    excluded: set[str] = set()
    for bank in (*banks, panel):
        excluded.update(pc._motion_launch_hex(bank))

    by_rule: dict[int, list[dict[str, Any]]] = {}
    per_rule: dict[str, Any] = {}
    for index, rule in enumerate(wc.MOVER_RULES, start=1):
        if time.time() >= deadline:
            break
        discoveries = il._scan_motion_rule(
            rule, profile.motion_scan_per_rule, contract.namespace
        )
        pairs: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for row in sorted(
            discoveries,
            key=lambda value: (
                ar._hash_seed(
                    contract.namespace, "balanced-holdout", value["mover_id"]
                ),
                value["mover_id"],
            ),
        ):
            if str(row["initial_hex"]) in excluded:
                continue
            copied = dict(row)
            copied["mover_id"] = str(row["mover_id"]).replace(
                "stage6l-", "stage6q-"
            )
            copied["source"] = "stage6q-fresh-deterministic-5x5-scan"
            pair = wc._discovered_pair(copied)
            if pair is None:
                continue
            launch_hex = pc._motion_launch_hex({"pairs": [pair]})
            if launch_hex & excluded:
                continue
            key = (
                int(pair["rule"]),
                int(pair["forward"]["period"]),
                tuple(pair["forward"]["displacement_yx"]),
                str(pair["forward"]["initial_hex"]),
            )
            if key in seen:
                continue
            seen.add(key)
            pairs.append(pair)
        by_rule[int(rule)] = pairs
        per_rule[str(rule)] = {
            "notation": life_rule_notation(rule),
            "scanned": profile.motion_scan_per_rule,
            "fresh_detected_pairs": len(pairs),
        }
        status(
            "running",
            "allocate-rule-balanced-stage6q-motion-bank",
            completed=index,
            total=len(wc.MOVER_RULES),
            fresh_pairs=sum(len(values) for values in by_rule.values()),
        )

    selected: list[dict[str, Any]] = []
    cursor = 0
    rules = sorted(by_rule)
    while len(selected) < profile.motion_validation_pairs:
        changed = False
        for rule in rules:
            values = by_rule[rule]
            if cursor < len(values) and len(selected) < profile.motion_validation_pairs:
                selected.append(values[cursor])
                changed = True
        if not changed:
            break
        cursor += 1
    counts = {
        str(rule): sum(int(pair["rule"]) == int(rule) for pair in selected)
        for rule in rules
    }
    available = {str(rule): len(by_rule[rule]) for rule in rules}
    balanced = pc._capacity_balance_verified(counts, available)
    complete = bool(
        len(selected) == profile.motion_validation_pairs
        and len(per_rule) == len(wc.MOVER_RULES)
        and balanced
    )
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "pairs": selected,
        "rules": per_rule,
        "selected_per_rule": counts,
        "available_per_rule": available,
        "validation_pair_count": len(selected),
        "scientific_holdout": True,
        "rule_balanced": True,
        "balance_definition": "max-min-round-robin-subject-to-rule-pool-capacity",
        "capacity_balance_verified": balanced,
        "zero_yield_rules_retained_in_ledger": [
            rule for rule, count in available.items() if count == 0
        ],
        "capacity_exhausted_rules": [
            rule
            for rule, count in counts.items()
            if count == available[rule]
            and count < max(counts.values(), default=0)
        ],
        "stage6k_through_stage6p_launch_states_excluded": True,
        "frozen_before_stage6q_selection": True,
        "allocation_digest": _digest([pair["pair_id"] for pair in selected]),
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(path, result)
    return result


def _validation_pair(
    candidate: dict[str, Any],
    pair: dict[str, Any],
    generations: int,
) -> dict[str, Any]:
    spatial = [
        _spatial_lineage(
            candidate,
            pair,
            direction,
            condition,
            placement,
            noise_name,
            generations=generations,
        )
        for direction in ("forward", "opposite")
        for condition in SPATIAL_COMMANDS
        for placement in SPATIAL_PLACEMENTS
        for noise_name in NOISE_LEVELS
    ]
    causal = [
        _spatial_lineage(
            candidate,
            pair,
            direction,
            condition,
            "center",
            "standard",
            generations=generations,
        )
        for direction in ("forward", "opposite")
        for condition in CAUSAL_CONDITIONS
    ]
    return {
        "candidate_id": candidate["candidate_id"],
        "pair_id": pair["pair_id"],
        "rule": pair["rule"],
        "lineages": spatial + causal,
        "spatial_lineage_count": len(spatial),
        "causal_lineage_count": len(causal),
    }


def _recovery(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    placement: str,
    noise_name: str,
    generation: int,
) -> dict[str, float]:
    return _lineage_metric_summary(
        _select_lineages(
            rows,
            candidate_id,
            condition=condition,
            placement=placement,
            noise_name=noise_name,
        ),
        generation,
    )


def _validation_gate(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    complete: bool,
    contract: TorusClosureContract,
) -> tuple[bool, dict[str, Any]]:
    candidate_id = str(candidate["candidate_id"])
    generations = (1, 3, 4, 8)
    spatial_recovery = {
        noise: {
            placement: {
                condition: {
                    f"generation{generation}": _recovery(
                        rows,
                        candidate_id,
                        condition,
                        placement,
                        noise,
                        generation,
                    )
                    for generation in generations
                }
                for condition in SPATIAL_COMMANDS
            }
            for placement in SPATIAL_PLACEMENTS
        }
        for noise in NOISE_LEVELS
    }
    causal_recovery = {
        condition: {
            f"generation{generation}": _recovery(
                rows,
                candidate_id,
                condition,
                "center",
                "standard",
                generation,
            )
            for generation in generations
        }
        for condition in CAUSAL_CONDITIONS
    }
    paired = {
        noise: {
            placement: {
                f"generation{generation}": _paired_placement_summary(
                    rows,
                    candidate_id,
                    placement,
                    noise,
                    generation,
                )
                for generation in (4, 8)
            }
            for placement in ("translation", "seam")
        }
        for noise in NOISE_LEVELS
    }

    standard_joints = [
        spatial_recovery["standard"][placement][condition][
            f"generation{generation}"
        ]["joint_success_fraction"]
        for placement in SPATIAL_PLACEMENTS
        for condition in SPATIAL_COMMANDS
        for generation in (4, 8)
    ]
    standard_generation4 = min(
        spatial_recovery["standard"][placement][condition]["generation4"][
            "joint_success_fraction"
        ]
        for placement in SPATIAL_PLACEMENTS
        for condition in SPATIAL_COMMANDS
    )
    standard_generation8 = min(
        spatial_recovery["standard"][placement][condition]["generation8"][
            "joint_success_fraction"
        ]
        for placement in SPATIAL_PLACEMENTS
        for condition in SPATIAL_COMMANDS
    )
    zero_minimum = min(
        spatial_recovery["zero"][placement][condition][f"generation{generation}"][
            "joint_success_fraction"
        ]
        for placement in SPATIAL_PLACEMENTS
        for condition in SPATIAL_COMMANDS
        for generation in (4, 8)
    )
    minimum_form = min(
        spatial_recovery[noise][placement][condition][f"generation{generation}"][
            "foreground_f1_mean"
        ]
        for noise in NOISE_LEVELS
        for placement in SPATIAL_PLACEMENTS
        for condition in SPATIAL_COMMANDS
        for generation in (4, 8)
    )
    placement_difference = max(
        abs(
            spatial_recovery["standard"]["center"][condition][
                f"generation{generation}"
            ]["joint_success_fraction"]
            - spatial_recovery["standard"][placement][condition][
                f"generation{generation}"
            ]["joint_success_fraction"]
        )
        for placement in ("translation", "seam")
        for condition in SPATIAL_COMMANDS
        for generation in (4, 8)
    )
    outgoing_agreement = min(
        paired[noise][placement][f"generation{generation}"][
            "outgoing_code_agreement"
        ]
        for noise in NOISE_LEVELS
        for placement in ("translation", "seam")
        for generation in (4, 8)
    )
    bitwise_agreement = min(
        paired[noise][placement][f"generation{generation}"][
            "aligned_bitwise_agreement"
        ]
        for noise in NOISE_LEVELS
        for placement in ("translation", "seam")
        for generation in (4, 8)
    )
    signed_separation: dict[str, float] = {}
    for generation in (4, 8):
        original = np.mean(
            [
                spatial_recovery["standard"][placement]["original_seed"][
                    f"generation{generation}"
                ]["signed_original_direction_similarity_mean"]
                for placement in SPATIAL_PLACEMENTS
            ]
        )
        opposite = np.mean(
            [
                spatial_recovery["standard"][placement]["opposite_seed"][
                    f"generation{generation}"
                ]["signed_original_direction_similarity_mean"]
                for placement in SPATIAL_PLACEMENTS
            ]
        )
        signed_separation[f"generation{generation}"] = float(original - opposite)
    rescue_immediate = min(
        causal_recovery[condition]["generation3"]["joint_success_fraction"]
        for condition in ("matching_rescue", "opposite_rescue")
    )
    rescue_rewrite = min(
        causal_recovery[condition]["generation4"]["joint_success_fraction"]
        for condition in ("matching_rescue", "opposite_rescue")
    )
    null_maximum = max(
        causal_recovery[condition]["generation8"]["mover_detection_fraction"]
        for condition in ("zero", "no_renewal")
    )
    renewal_advantage = (
        causal_recovery["intact"]["generation8"]["joint_success_fraction"]
        - causal_recovery["no_renewal"]["generation8"]["joint_success_fraction"]
    )
    degradation = max(
        0.0,
        *[
            spatial_recovery["zero"][placement][condition][
                f"generation{generation}"
            ]["joint_success_fraction"]
            - spatial_recovery["standard"][placement][condition][
                f"generation{generation}"
            ]["joint_success_fraction"]
            for placement in SPATIAL_PLACEMENTS
            for condition in SPATIAL_COMMANDS
            for generation in (4, 8)
        ],
    )
    gate = bool(
        complete
        and int(candidate["payload_bits"]) <= 8
        and minimum_form >= contract.motion_foreground_f1_minimum
        and standard_generation4 >= contract.placement_generation4_minimum
        and standard_generation8 >= contract.placement_generation8_minimum
        and zero_minimum >= contract.zero_noise_placement_minimum
        and placement_difference <= contract.placement_difference_maximum
        and outgoing_agreement >= contract.outgoing_code_agreement_minimum
        and bitwise_agreement >= contract.bitwise_equivariance_minimum
        and signed_separation["generation4"]
        >= contract.motion_signed_generation4_minimum
        and signed_separation["generation8"]
        >= contract.motion_signed_generation8_minimum
        and rescue_immediate >= contract.motion_rescue_immediate_minimum
        and rescue_rewrite >= contract.motion_rescue_rewrite_minimum
        and null_maximum <= contract.metric_null_maximum
        and renewal_advantage >= contract.compact_control_advantage_minimum
        and degradation <= contract.standard_noise_degradation_maximum
    )
    score = float(
        0.20 * min(standard_joints)
        + 0.10 * zero_minimum
        + 0.10 * min(1.0, minimum_form)
        + 0.15 * outgoing_agreement
        + 0.15 * bitwise_agreement
        + 0.10 * rescue_rewrite
        + 0.10 * min(1.0, max(0.0, signed_separation["generation8"]) / 2.0)
        + 0.10 * min(1.0, max(0.0, renewal_advantage))
    )
    return gate, {
        "candidate": _public_candidate(candidate),
        "spatial_recovery": spatial_recovery,
        "causal_recovery": causal_recovery,
        "paired_equivariance": paired,
        "minimum_standard_joint_generation4": float(standard_generation4),
        "minimum_standard_joint_generation8": float(standard_generation8),
        "minimum_zero_noise_joint_generation4_or_8": float(zero_minimum),
        "minimum_torus_foreground_f1": float(minimum_form),
        "maximum_center_placement_joint_difference": float(placement_difference),
        "minimum_outgoing_code_agreement": float(outgoing_agreement),
        "minimum_inverse_shifted_bitwise_agreement": float(bitwise_agreement),
        "signed_original_opposite_separation_generation4": signed_separation[
            "generation4"
        ],
        "signed_original_opposite_separation_generation8": signed_separation[
            "generation8"
        ],
        "rescue_immediate_joint_minimum": float(rescue_immediate),
        "rescue_after_one_rewrite_joint_minimum": float(rescue_rewrite),
        "maximum_null_mover_detection_generation8": float(null_maximum),
        "active_renewal_joint_advantage_generation8": float(renewal_advantage),
        "maximum_standard_noise_degradation": float(degradation),
        "selection_score": score,
        "stage_gate": gate,
    }


def _run_fresh_validation(
    stage_root: Path,
    candidates: Sequence[dict[str, Any]],
    bank: dict[str, Any],
    profile: TorusClosureProfile,
    profile_name: str,
    contract: TorusClosureContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Callable[..., None],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "fresh-spatial-validation"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    pairs = list(bank.get("pairs", []))
    rows: list[dict[str, Any]] = []
    jobs: list[tuple[dict[str, Any], dict[str, Any], Path]] = []
    for candidate in candidates:
        for pair in pairs:
            path = checkpoints / f"{candidate['candidate_id']}-{pair['pair_id']}.json"
            if resume and path.exists():
                rows.append(_load_json(path)["row"])
            else:
                jobs.append((candidate, pair, path))
    registered = len(candidates) * len(pairs)
    completed = len(rows)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _validation_pair,
                candidate,
                pair,
                int(profile.validation_generations),
            ): path
            for candidate, pair, path in jobs
            if time.time() < deadline
        }
        for future in as_completed(futures):
            row = future.result()
            ar._atomic_json(
                futures[future], {"design_digest": design_digest, "row": row}
            )
            rows.append(row)
            completed += 1
            status(
                "running",
                "fresh-paired-torus-validation",
                completed=completed,
                total=registered,
                candidate_id=row["candidate_id"],
            )
    complete = bool(completed == registered and bank.get("stage_gate", False))
    summaries: dict[str, Any] = {}
    qualified: list[tuple[float, dict[str, Any]]] = []
    for candidate in candidates:
        candidate_rows = [
            row for row in rows if row["candidate_id"] == candidate["candidate_id"]
        ]
        candidate_complete = len(candidate_rows) == len(pairs)
        if profile_name == "smoke":
            gate = candidate_complete
            summary = {
                "candidate": _public_candidate(candidate),
                "smoke_pair_count": len(candidate_rows),
                "scientific_gate_evaluated": False,
                "selection_score": 0.0,
                "stage_gate": gate,
            }
        else:
            gate, summary = _validation_gate(
                rows, candidate, candidate_complete, contract
            )
            summary["scientific_gate_evaluated"] = True
        summaries[str(candidate["candidate_id"])] = summary
        if gate:
            qualified.append((float(summary["selection_score"]), candidate))
    qualified.sort(key=lambda row: row[0], reverse=True)
    models = [row[1] for row in qualified]
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and models),
        "registered_pair_candidate_tasks": registered,
        "completed_pair_candidate_tasks": completed,
        "validation_pair_count": len(pairs),
        "selected_candidate_ids": [row["candidate_id"] for row in candidates],
        "qualified_candidate_ids": [row["candidate_id"] for row in models],
        "candidate_summaries": summaries,
        "common_random_numbers_across_placement": True,
        "torus_observer_used_for_scientific_gate": True,
        "legacy_observer_retained_as_diagnostic_only": True,
        "visible_reset_every_boundary": True,
        "absolute_seed_once_then_visible_renewal": True,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, models


def _endurance_pair(
    candidate: dict[str, Any], pair: dict[str, Any]
) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "pair_id": pair["pair_id"],
        "rule": pair["rule"],
        "lineages": [
            _spatial_lineage(
                candidate,
                pair,
                direction,
                condition,
                placement,
                "standard",
                generations=16,
            )
            for direction in ("forward", "opposite")
            for condition in SPATIAL_COMMANDS
            for placement in SPATIAL_PLACEMENTS
        ],
    }


def _run_spatial_endurance(
    stage_root: Path,
    candidates: Sequence[dict[str, Any]],
    bank: dict[str, Any],
    profile_name: str,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Callable[..., None],
) -> dict[str, Any]:
    if not candidates:
        return _empty("no generation-eight torus qualifier")
    if profile_name == "smoke":
        return {
            "state": "complete",
            "stage_gate": True,
            "scientific_endurance_run": False,
            "skipped_reason": "smoke profile",
            "final_audit_trajectory_state": "untouched",
        }
    root = stage_root / "spatial-endurance"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    pairs = list(bank.get("pairs", []))
    rows: list[dict[str, Any]] = []
    jobs: list[tuple[dict[str, Any], dict[str, Any], Path]] = []
    for candidate in candidates:
        for pair in pairs:
            path = checkpoints / f"{candidate['candidate_id']}-{pair['pair_id']}.json"
            if resume and path.exists():
                rows.append(_load_json(path)["row"])
            else:
                jobs.append((candidate, pair, path))
    registered = len(candidates) * len(pairs)
    completed = len(rows)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_endurance_pair, candidate, pair): path
            for candidate, pair, path in jobs
            if time.time() < deadline
        }
        for future in as_completed(futures):
            row = future.result()
            ar._atomic_json(
                futures[future], {"design_digest": design_digest, "row": row}
            )
            rows.append(row)
            completed += 1
            status(
                "running",
                "generation-twelve-sixteen-torus-endurance",
                completed=completed,
                total=registered,
                candidate_id=row["candidate_id"],
            )
    complete = completed == registered
    summaries: dict[str, Any] = {}
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        summaries[candidate_id] = {
            f"generation{generation}": {
                placement: {
                    condition: _recovery(
                        rows,
                        candidate_id,
                        condition,
                        placement,
                        "standard",
                        generation,
                    )
                    for condition in SPATIAL_COMMANDS
                }
                for placement in SPATIAL_PLACEMENTS
            }
            for generation in (12, 16)
        }
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "registered_pair_candidate_tasks": registered,
        "completed_pair_candidate_tasks": completed,
        "generations": [12, 16],
        "candidate_summaries": summaries,
        "generation8_gate_required_before_open": True,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6p_root: Path,
    stage6o_root: Path,
    stage6n_root: Path,
    stage6m_root: Path,
    stage6l_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[
    TorusClosureContract,
    TorusClosureProfile,
    dict[str, Any],
    str,
    dict[str, Any],
]:
    contract = TorusClosureContract()
    profile = PROFILES[profile_name]
    integrity = _parent_integrity(
        stage6p_root, stage6o_root, stage6n_root, stage6m_root, stage6l_root
    )
    design = {
        "experiment": "ca_motif_torus_closure_stage_6q",
        "prospective_followup_to": PARENT_STAGE6P_DIGEST,
        "stage6p_verdict_immutable": True,
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(profile),
        "stage6p_root": str(stage6p_root.resolve()),
        "stage6o_root": str(stage6o_root.resolve()),
        "stage6n_root": str(stage6n_root.resolve()),
        "stage6m_root": str(stage6m_root.resolve()),
        "stage6l_root": str(stage6l_root.resolve()),
        "stage6p_required_hashes": integrity["stage6p_required_hashes"],
        "registered_phases": PHASES,
        "observer_audit": {
            "signature": "largest-empty-circular-gap",
            "displacement": "signed-modular",
            "form": "toroidal-translation-plus-d4",
            "legacy_observer": "diagnostic-only",
        },
        "candidate_ladder": {
            "maximum_candidates": 8,
            "maximum_advanced": profile.maximum_advanced_candidates,
            "payload_maximum_bits": 8,
            "pair_blocked_folds": 6,
            "runtime_inputs": "daughter-visible-spacetime-and-zero-born-latch-only",
        },
        "cohort_route": {
            "development": (
                f"first {profile.motion_development_pairs} already-exposed "
                "Stage-6M mover pairs"
            ),
            "screen": (
                f"first {profile.motion_screen_pairs} of that exposed development set"
            ),
            "validation": (
                f"{profile.motion_validation_pairs} fresh Stage-6Q rule-balanced movers"
            ),
            "final": "62-pair protected reserve unreachable",
        },
        "compute": {
            "hard_hours": max_hours,
            "exploration_cutoff_hours": min(
                max_hours, contract.exploration_stop_hours
            ),
            "worker_cap": 4,
            "detached_and_resumable": True,
        },
        "protocol_sha256": ar._sha256(PROTOCOL_PATH),
        "implementation_hashes": {
            "motif_torus_closure.py": ar._sha256(Path(__file__)),
            "motif_polarity_closure.py": ar._sha256(Path(pc.__file__)),
            "motif_counterfactual_carrier.py": ar._sha256(Path(co.__file__)),
            "motif_causal_attractor.py": ar._sha256(Path(cn.__file__)),
            "motif_latent_regeneration.py": ar._sha256(Path(lm.__file__)),
        },
    }
    design_digest = _digest(design)
    design["design_digest"] = design_digest
    design_path = output / "DESIGN.json"
    if resume and design_path.exists():
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6Q resume design changed")
    else:
        ar._atomic_json(design_path, design)
    started_path = output / "STARTED.json"
    if resume and started_path.exists():
        started = float(_load_json(started_path)["started_unix"])
    else:
        started = time.time()
        ar._atomic_json(started_path, {"started_unix": started})
    campaign = {
        "started_unix": started,
        "exploration_deadline_unix": started
        + min(max_hours, contract.exploration_stop_hours) * 3600.0,
        "hard_deadline_unix": started + max_hours * 3600.0,
        "max_hours": max_hours,
    }
    ar._atomic_json(output / "CAMPAIGN.json", campaign)
    ar._atomic_json(
        output / "MANIFEST.json",
        {
            "experiment": design["experiment"],
            "design_digest": design_digest,
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "protocol_sha256": design["protocol_sha256"],
            "parent_sha256": integrity["parent_result_sha256"],
            "stage6p_result_reinterpreted": False,
            "cleanroom_forbidden_code_imported": False,
            "final_audit_trajectory_state": "untouched",
        },
    )
    return contract, profile, campaign, design_digest, integrity


def _status_writer(
    output: Path,
    profile_name: str,
    campaign: dict[str, Any],
    active: list[str],
    workers: int,
) -> Callable[..., None]:
    def update(state: str, message: str, **extra: Any) -> None:
        now = time.time()
        payload = {
            "experiment": "ca_motif_torus_closure_stage_6q",
            "state": state,
            "phase": active[0],
            "message": message,
            "profile": profile_name,
            "pid": os.getpid(),
            "workers": int(workers),
            "worker_cap": 4,
            "started_unix": float(campaign["started_unix"]),
            "updated_unix": now,
            "elapsed_seconds": max(0.0, now - float(campaign["started_unix"])),
            "hard_deadline_unix": float(campaign["hard_deadline_unix"]),
            "remaining_seconds": max(
                0.0, float(campaign["hard_deadline_unix"]) - now
            ),
            "final_audit_trajectory_state": "untouched",
            **extra,
        }
        if (
            "eta_seconds" not in extra
            and int(extra.get("completed", 0)) > 0
            and "total" in extra
        ):
            phase_rate = payload["elapsed_seconds"] / int(extra["completed"])
            payload["eta_seconds"] = max(
                0.0,
                phase_rate * (int(extra["total"]) - int(extra["completed"])),
            )
        ar._atomic_json(output / "STATUS.json", payload)
        print(f"[{state}] {active[0]}: {message}", flush=True)

    return update


def _write_phase(
    output: Path,
    phase: str,
    design_digest: str,
    result: dict[str, Any],
    report: str,
    lay: str,
) -> None:
    root = output / phase
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment": "ca_motif_torus_closure_stage_6q",
        "design_digest": design_digest,
        "phase": phase,
        **result,
    }
    ar._atomic_json(root / "RESULTS.json", payload)
    ar._atomic_json(
        root / "STAGE_DECISION.json",
        {
            "experiment": payload["experiment"],
            "design_digest": design_digest,
            "phase": phase,
            "state": payload.get("state", "complete"),
            "stage_gate": bool(payload.get("stage_gate", False)),
            "next_phase": payload.get("next_phase"),
            "final_audit_trajectory_state": "untouched",
        },
    )
    ar._atomic_text(root / "REPORT.md", report.rstrip() + "\n")
    ar._atomic_text(root / "LAY_SUMMARY.md", lay.rstrip() + "\n")
    ar._atomic_text(root / "COMPLETE", "complete\n")


def _campaign_result(
    output: Path,
    design_digest: str,
    profile_name: str,
    audit: dict[str, Any],
    fit: dict[str, Any],
    screen: dict[str, Any],
    validation: dict[str, Any],
    endurance: dict[str, Any],
) -> dict[str, Any]:
    validation_gate = bool(validation.get("stage_gate", False))
    observer_gate = bool(audit.get("stage_gate", False))
    spatial_equivariance = any(
        float(summary.get("minimum_inverse_shifted_bitwise_agreement", 0.0))
        >= 0.90
        and float(summary.get("maximum_center_placement_joint_difference", 1.0))
        <= 0.05
        for summary in validation.get("candidate_summaries", {}).values()
    )
    if profile_name == "smoke":
        verdict = "SMOKE_PATH_VALIDATED"
        scientific_claim = False
    elif validation_gate:
        verdict = "TORUS_EQUIVARIANT_ABSTRACT_MOTION_PH"
        scientific_claim = True
    elif observer_gate and spatial_equivariance:
        verdict = "TORUS_INVARIANCE_RESCUED_CARRIER_GATE_FAILED"
        scientific_claim = True
    elif observer_gate:
        verdict = "OBSERVER_SEAM_ARTIFACT_CONFIRMED_NO_TORUS_CARRIER_CLOSURE"
        scientific_claim = True
    else:
        verdict = "NO_TORUS_MOTION_CLOSURE"
        scientific_claim = True
    result = {
        "experiment": "ca_motif_torus_closure_stage_6q",
        "design_digest": design_digest,
        "profile_name": profile_name,
        "state": "complete",
        "stage_gate": validation_gate,
        "verdict": verdict,
        "scientific_claim": scientific_claim,
        "observer_artifact_confirmed": observer_gate,
        "spatial_equivariance_recovered": spatial_equivariance,
        "candidate_fit_gate": bool(fit.get("stage_gate", False)),
        "paired_spatial_screen_gate": bool(screen.get("stage_gate", False)),
        "torus_equivariant_abstract_motion_ph_gate": validation_gate,
        "endurance_completed": bool(endurance.get("stage_gate", False)),
        "qualified_candidate_ids": validation.get("qualified_candidate_ids", []),
        "stage6p_verdict_reinterpreted": False,
        "claim_boundary": (
            "Engineered synthetic cellular automata only. No result implies "
            "biology, human memory, consciousness, or agency, and no result "
            "weakens the independently positive Wagner or GARD findings."
        ),
        "original_final_reserve_opened": False,
        "final_audit_pair_count": 62,
        "final_audit_trajectory_state": "untouched",
        "phase_results": {
            "observer_audit": audit,
            "spatial_writer_fit": fit,
            "paired_spatial_screen": screen,
            "fresh_spatial_validation": validation,
            "spatial_endurance": endurance,
        },
    }
    ar._atomic_json(output / "RESULTS.json", result)
    next_step = (
        "independently replicate the qualifying torus carrier in new Life-like rules"
        if validation_gate
        else "localize the first failing carrier interface using the paired trace packet"
    )
    ar._atomic_json(
        output / "STAGE_DECISION.json",
        {
            "experiment": result["experiment"],
            "design_digest": design_digest,
            "state": "complete",
            "stage_gate": validation_gate,
            "verdict": verdict,
            "next_step": next_step,
            "final_audit_trajectory_state": "untouched",
        },
    )
    report = (
        "# Stage 6Q torus-equivariant motion closure\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"Legacy seam-observer artifact confirmed: `{observer_gate}`. "
        f"Prospective spatial equivariance recovered: `{spatial_equivariance}`. "
        f"Full causal Plastic Heredity gate: `{validation_gate}`. The Stage 6P "
        "verdict remains immutable, and the protected 62-pair reserve was not opened.\n"
    )
    lay = (
        "# Lay summary\n\n"
        "The earlier test may have confused a creature crossing the edge of a "
        "wraparound world with a creature disappearing. This round uses an "
        "edge-aware observer and gives exact center, shifted, and edge copies "
        "the same random copying mistakes. It then asks whether daughters can "
        "still rebuild the same moving form and rewrite the tiny inherited "
        "direction note for later daughters.\n\n"
        f"The registered outcome is **{verdict}**.\n"
    )
    ar._atomic_text(output / "REPORT.md", report)
    ar._atomic_text(output / "LAY_SUMMARY.md", lay)
    ar._atomic_text(output / "COMPLETE", "complete\n")
    return result


def _update_discovery_log(result: dict[str, Any]) -> None:
    if result.get("profile_name") != "reference":
        return
    entry = (
        "\n\n## Stage 6Q: torus-equivariant motion closure\n\n"
        f"Stage 6Q design `{result['design_digest']}` completed with verdict "
        f"**{result['verdict']}**. It prospectively audited the seam-blind "
        "observer, paired center/translation/seam copy noise, and tested fresh "
        "daughter-written motion carriers. Stage 6P remained immutable and the "
        "protected 62-pair reserve remained untouched.\n"
    )
    existing = (
        DISCOVERY_LOG.read_text(encoding="utf-8")
        if DISCOVERY_LOG.exists()
        else "# Discovery log\n"
    )
    marker = f"Stage 6Q design `{result['design_digest']}`"
    if marker not in existing:
        ar._atomic_text(DISCOVERY_LOG, existing.rstrip() + entry)


def run_motif_torus_closure(
    output: Path,
    *,
    stage6p_root: Path = DEFAULT_STAGE6P_ROOT,
    stage6o_root: Path = DEFAULT_STAGE6O_ROOT,
    stage6n_root: Path = DEFAULT_STAGE6N_ROOT,
    stage6m_root: Path = DEFAULT_STAGE6M_ROOT,
    stage6l_root: Path = DEFAULT_STAGE6L_ROOT,
    stage6k_root: Path = DEFAULT_STAGE6K_ROOT,
    profile_name: str = "reference",
    workers: int = 4,
    max_hours: float = 8.0,
    resume: bool = False,
) -> dict[str, Any]:
    """Run Stage 6Q without loading or exposing the protected final reserve."""

    ar.require_pinned_numpy()
    if profile_name not in PROFILES:
        raise ValueError(f"unknown Stage-6Q profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6Q workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6Q max-hours must be in (0, 8]")
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)

    stage6p_root = stage6p_root.resolve()
    stage6o_root = stage6o_root.resolve()
    stage6n_root = stage6n_root.resolve()
    stage6m_root = stage6m_root.resolve()
    stage6l_root = stage6l_root.resolve()
    stage6k_root = stage6k_root.resolve()
    _parent_integrity(
        stage6p_root, stage6o_root, stage6n_root, stage6m_root, stage6l_root
    )
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ar._atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
    active = ["prepare"]
    status: Callable[..., None] | None = None
    try:
        contract, profile, campaign, design_digest, integrity = _prepare_campaign(
            output,
            profile_name,
            stage6p_root,
            stage6o_root,
            stage6n_root,
            stage6m_root,
            stage6l_root,
            max_hours,
            resume=resume,
        )
        status = _status_writer(output, profile_name, campaign, active, workers)
        status("running", "frozen-stage6p-parent-and-reserves-verified")
        active[0] = "integrity"
        _write_phase(
            output,
            "integrity",
            design_digest,
            integrity | {"next_phase": "observer-audit"},
            "# Stage 6Q integrity\n\nThe completed Stage 6P artifacts and inherited reserve boundaries were hash-verified.",
            "# Lay summary\n\nThe previous result stays fixed; this is a new test with new movers.",
        )

        active[0] = "observer-audit"
        audit = _run_observer_audit(stage6p_root)
        _write_phase(
            output,
            "observer-audit",
            design_digest,
            audit | {"next_phase": "allocation"},
            "# Stage 6Q observer audit\n\nExact translations were compared with legacy and torus-aware finite-object observers.",
            "# Lay summary\n\nThe old ruler loses an object at the wraparound edge; the new ruler follows it across that edge.",
        )
        status("running", "torus-observer-audit-complete", gate=audit["stage_gate"])

        stage_root = output / "stage6q"
        stage_root.mkdir(parents=True, exist_ok=True)
        active[0] = "allocation"
        bank = _fresh_motion_bank(
            stage_root,
            stage6p_root,
            stage6o_root,
            stage6n_root,
            stage6m_root,
            stage6l_root,
            stage6k_root,
            profile_name,
            profile,
            contract,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
        )
        motion_source = _load_json(stage6m_root / "stage6m/MOTION_BANK.json")
        development = list(motion_source.get("pairs", []))[
            : profile.motion_development_pairs
        ]
        allocation = {
            "state": bank.get("state", "complete"),
            "stage_gate": bool(
                bank.get("stage_gate")
                and len(development) == profile.motion_development_pairs
            ),
            "development_pair_count": len(development),
            "development_pair_ids_sha256": _digest(
                [pair["pair_id"] for pair in development]
            ),
            "validation_pair_count": bank.get("validation_pair_count", 0),
            "validation_allocation_digest": bank.get("allocation_digest"),
            "validation_frozen_before_candidate_selection": True,
            "procedural_trajectories_simulated": False,
            "final_pair_count": 62,
            "final_pair_ids_sha256": integrity["final_pair_ids_sha256"],
            "final_audit_trajectory_state": "untouched",
            "next_phase": "spatial-writer-fit",
        }
        ar._atomic_json(
            stage_root / "COHORTS.json",
            {
                "design_digest": design_digest,
                "development_pair_ids": [pair["pair_id"] for pair in development],
                "validation_pair_ids": [
                    pair["pair_id"] for pair in bank.get("pairs", [])
                ],
                "validation_frozen_before_candidate_selection": True,
                "final_audit_pair_count": 62,
                "final_audit_pair_ids_sha256": integrity["final_pair_ids_sha256"],
                "final_audit_trajectories_not_loaded": True,
                "final_audit_trajectory_state": "untouched",
            },
        )
        _write_phase(
            output,
            "allocation",
            design_digest,
            allocation,
            "# Stage 6Q allocation\n\nThe fresh rule-balanced mover bank was frozen before candidate selection.",
            "# Lay summary\n\nNew exam questions were sealed before choosing the best memory design.",
        )

        active[0] = "spatial-writer-fit"
        model_path = stage_root / "spatial-writer-fit/MODELS.json"
        if resume and model_path.exists():
            fitted = _load_json(model_path)
            candidates = fitted["candidates"]
            fit = fitted["result"]
        else:
            candidates, metadata = _candidate_ladder(
                stage6p_root, stage6n_root, development, profile_name
            )
            fit = {
                "state": "complete",
                "stage_gate": bool(candidates),
                "registered_candidate_count": len(candidates),
                "candidate_ids": [row["candidate_id"] for row in candidates],
                "candidate_public": [_public_candidate(row) for row in candidates],
                "fit_metadata": metadata,
                "payload_maximum_bits": max(
                    int(row["payload_bits"]) for row in candidates
                ),
                "runtime_target_labels": False,
                "runtime_placement_labels": False,
                "final_audit_trajectory_state": "untouched",
            }
            ar._atomic_json(
                model_path,
                {
                    "design_digest": design_digest,
                    "result": fit,
                    "candidates": candidates,
                },
            )
        status(
            "running",
            "spatial-writer-ladder-fitted",
            completed=len(candidates),
            total=len(candidates),
        )
        _write_phase(
            output,
            "spatial-writer-fit",
            design_digest,
            fit | {"next_phase": "paired-spatial-screen"},
            "# Stage 6Q writer fit\n\nLegacy, wrap-aware, translation-augmented, torus-medoid, and error-corrected compact writers were frozen.",
            "# Lay summary\n\nSix ways of reading and copying the direction note were prepared without seeing the new exam movers.",
        )

        active[0] = "paired-spatial-screen"
        screen, selected = _run_spatial_screen(
            stage_root,
            candidates,
            development,
            profile,
            profile_name,
            design_digest,
            workers=workers,
            resume=resume,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
        )
        selected_ids = set(screen.get("selected_candidate_ids", []))
        selected = [row for row in candidates if row["candidate_id"] in selected_ids]
        _write_phase(
            output,
            "paired-spatial-screen",
            design_digest,
            screen | {"next_phase": "fresh-spatial-validation"},
            "# Stage 6Q paired screen\n\nCenter, translated, and seam trajectories shared copy-noise draws and were inverse-shifted for exact comparison.",
            "# Lay summary\n\nEach candidate answered the same question in the middle and at the edge, with the same random copying mistakes.",
        )

        active[0] = "fresh-spatial-validation"
        if allocation.get("stage_gate") and screen.get("stage_gate") and selected:
            validation, qualified = _run_fresh_validation(
                stage_root,
                selected,
                bank,
                profile,
                profile_name,
                contract,
                design_digest,
                workers=workers,
                resume=resume,
                deadline=float(campaign["hard_deadline_unix"]),
                status=status,
            )
        else:
            validation, qualified = _empty(
                "allocation, writer fit, or paired screen failed"
            ), []
            validation["qualified_candidate_ids"] = []
        _write_phase(
            output,
            "fresh-spatial-validation",
            design_digest,
            validation | {"next_phase": "spatial-endurance"},
            "# Stage 6Q fresh validation\n\nFresh movers faced paired spatial commands, zero and standard noise, ablation, no-renewal, and frozen-parent rescue tests.",
            "# Lay summary\n\nUnfamiliar moving forms had to inherit, rebuild, and rewrite the note—and fail when the note was removed.",
        )

        active[0] = "spatial-endurance"
        endurance = _run_spatial_endurance(
            stage_root,
            qualified,
            bank,
            profile_name,
            design_digest,
            workers=workers,
            resume=resume,
            deadline=float(campaign["hard_deadline_unix"]),
            status=status,
        )
        _write_phase(
            output,
            "spatial-endurance",
            design_digest,
            endurance | {"next_phase": "adjudicate"},
            "# Stage 6Q endurance\n\nOnly a generation-eight qualifier could open generations twelve and sixteen.",
            "# Lay summary\n\nOnly a carrier that passed the main exam was followed for twice as many daughter generations.",
        )

        active[0] = "adjudicate"
        result = _campaign_result(
            output,
            design_digest,
            profile_name,
            audit,
            fit,
            screen,
            validation,
            endurance,
        )
        _write_phase(
            output,
            "adjudicate",
            design_digest,
            result,
            "# Stage 6Q adjudication\n\nObserver artifacts, spatial equivariance, and causal carrier renewal were adjudicated separately.",
            "# Lay summary\n\nThe round separates a broken ruler from a broken inherited memory.",
        )
        _update_discovery_log(result)
        status("complete", "campaign-complete", verdict=result["verdict"])
        return result
    except BaseException as error:
        if status is not None:
            status("failed", "campaign-failed", error=repr(error))
        ar._atomic_json(
            output / "FAILURE.json",
            {
                "experiment": "ca_motif_torus_closure_stage_6q",
                "state": "failed",
                "phase": active[0],
                "error": repr(error),
                "final_audit_trajectory_state": "untouched",
            },
        )
        raise


def reanalyze_completed_torus_closure(output: Path) -> dict[str, Any]:
    """Correct the v1 placement-index typo using only frozen checkpoints.

    The original registered artifacts remain untouched.  This emits a
    hash-bound corrigendum and corrected result beside them; no trajectory is
    simulated and no additional cohort is opened.
    """

    output = output.resolve()
    if not (output / "COMPLETE").exists():
        raise ValueError("Stage-6Q campaign is not complete")
    design = _load_json(output / "DESIGN.json")
    original = _load_json(output / "RESULTS.json")
    if design.get("design_digest") != original.get("design_digest"):
        raise ValueError("Stage-6Q design/result binding changed")
    if original.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6Q final reserve boundary changed")

    stage_root = output / "stage6q"
    model_payload = _load_json(stage_root / "spatial-writer-fit/MODELS.json")
    candidates = list(model_payload["candidates"])
    screen_paths = sorted(
        (stage_root / "paired-spatial-screen/checkpoints").glob("*.json")
    )
    validation_paths = sorted(
        (stage_root / "fresh-spatial-validation/checkpoints").glob("*.json")
    )
    screen_rows = [_load_json(path)["row"] for path in screen_paths]
    validation_rows = [_load_json(path)["row"] for path in validation_paths]
    profile = PROFILES[str(original["profile_name"])]
    contract = TorusClosureContract()

    screen_summaries = {
        str(candidate["candidate_id"]): _screen_candidate_summary(
            screen_rows, candidate, int(profile.screen_generations)
        )
        for candidate in candidates
    }
    ranked = sorted(
        (
            float(screen_summaries[str(candidate["candidate_id"])][
                "selection_score"
            ]),
            str(candidate["candidate_id"]),
        )
        for candidate in candidates
    )
    corrected_selected = [
        candidate_id
        for _, candidate_id in reversed(ranked)
    ][: profile.maximum_advanced_candidates]
    original_screen = _load_json(
        stage_root / "paired-spatial-screen/RESULTS.json"
    )
    original_selected = list(original_screen.get("selected_candidate_ids", []))
    if corrected_selected != original_selected:
        raise ValueError(
            "placement-index correction changes candidate selection; fresh "
            "validation would be required"
        )

    by_id = {str(candidate["candidate_id"]): candidate for candidate in candidates}
    validation_summaries: dict[str, Any] = {}
    qualified: list[tuple[float, str]] = []
    expected_per_candidate = int(profile.motion_validation_pairs)
    for candidate_id in corrected_selected:
        candidate_rows = [
            row for row in validation_rows if row["candidate_id"] == candidate_id
        ]
        gate, summary = _validation_gate(
            validation_rows,
            by_id[candidate_id],
            len(candidate_rows) == expected_per_candidate,
            contract,
        )
        summary["scientific_gate_evaluated"] = True
        validation_summaries[candidate_id] = summary
        if gate:
            qualified.append((float(summary["selection_score"]), candidate_id))
    qualified.sort(reverse=True)
    qualified_ids = [candidate_id for _, candidate_id in qualified]
    audit = _load_json(output / "observer-audit/RESULTS.json")
    observer_gate = bool(audit.get("stage_gate", False))
    validation_gate = bool(qualified_ids)
    spatial_equivariance = any(
        float(summary["minimum_inverse_shifted_bitwise_agreement"])
        >= contract.bitwise_equivariance_minimum
        and float(summary["maximum_center_placement_joint_difference"])
        <= contract.placement_difference_maximum
        for summary in validation_summaries.values()
    )
    if validation_gate:
        verdict = "TORUS_EQUIVARIANT_ABSTRACT_MOTION_PH"
    elif observer_gate and spatial_equivariance:
        verdict = "TORUS_INVARIANCE_RESCUED_CARRIER_GATE_FAILED"
    elif observer_gate:
        verdict = "OBSERVER_SEAM_ARTIFACT_CONFIRMED_NO_TORUS_CARRIER_CLOSURE"
    else:
        verdict = "NO_TORUS_MOTION_CLOSURE"

    checkpoint_hashes = {
        str(path.relative_to(output)): ar._sha256(path)
        for path in (*screen_paths, *validation_paths)
    }
    corrected = {
        "experiment": "ca_motif_torus_closure_stage_6q_reanalysis",
        "state": "complete",
        "original_design_digest": design["design_digest"],
        "original_results_sha256": ar._sha256(output / "RESULTS.json"),
        "frozen_checkpoint_count": len(checkpoint_hashes),
        "frozen_checkpoints_digest": _digest(checkpoint_hashes),
        "correction": (
            "paired placement aggregation now indexes each lineage by its "
            "actual placement instead of the function's requested placement"
        ),
        "new_trajectories_simulated": False,
        "candidate_selection_changed": False,
        "original_selected_candidate_ids": original_selected,
        "corrected_selected_candidate_ids": corrected_selected,
        "qualified_candidate_ids": qualified_ids,
        "stage_gate": validation_gate,
        "verdict": verdict,
        "verdict_changed": verdict != original.get("verdict"),
        "observer_artifact_confirmed": observer_gate,
        "spatial_equivariance_recovered": spatial_equivariance,
        "screen_candidate_summaries": screen_summaries,
        "validation_candidate_summaries": validation_summaries,
        "original_artifacts_preserved": True,
        "original_final_reserve_opened": False,
        "final_audit_pair_count": 62,
        "final_audit_trajectory_state": "untouched",
        "reanalysis_implementation_sha256": ar._sha256(Path(__file__)),
    }
    corrected["reanalysis_digest"] = _digest(corrected)
    ar._atomic_json(output / "CORRECTED_RESULTS.json", corrected)
    ar._atomic_json(
        output / "AGGREGATION_CORRIGENDUM.json",
        {
            key: corrected[key]
            for key in (
                "state",
                "original_design_digest",
                "original_results_sha256",
                "frozen_checkpoint_count",
                "frozen_checkpoints_digest",
                "correction",
                "new_trajectories_simulated",
                "candidate_selection_changed",
                "corrected_selected_candidate_ids",
                "qualified_candidate_ids",
                "stage_gate",
                "verdict",
                "verdict_changed",
                "observer_artifact_confirmed",
                "spatial_equivariance_recovered",
                "original_artifacts_preserved",
                "final_audit_trajectory_state",
                "reanalysis_implementation_sha256",
                "reanalysis_digest",
            )
        },
    )
    ar._atomic_text(
        output / "CORRIGENDUM.md",
        "# Stage 6Q aggregation corrigendum\n\n"
        "The registered CA trajectories were correct, but the placement-pair "
        "aggregator used the requested placement as the dictionary key for "
        "every lineage. This made outgoing-code and aligned-bitwise agreement "
        "appear to be zero. The corrected analysis uses each lineage's actual "
        "placement and simulates no new trajectories. Candidate selection and "
        f"the final verdict are unchanged: **{verdict}**. The original "
        "artifacts remain preserved.\n",
    )
    return corrected


__all__ = [
    "DEFAULT_STAGE6P_ROOT",
    "PHASES",
    "PROFILES",
    "TorusClosureContract",
    "TorusClosureProfile",
    "_common_copy_seed",
    "_detect_mover_torus",
    "_hamming84_decode",
    "_hamming84_encode",
    "_parent_integrity",
    "_spatial_lineage",
    "_torus_foreground_overlap",
    "_torus_translation_signature",
    "reanalyze_completed_torus_closure",
    "run_motif_torus_closure",
]
