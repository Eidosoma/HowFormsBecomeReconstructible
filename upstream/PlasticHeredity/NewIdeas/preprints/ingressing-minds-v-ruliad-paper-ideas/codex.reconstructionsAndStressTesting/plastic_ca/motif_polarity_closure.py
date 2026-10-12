"""Stage-6P polarity closure and causal compact-basis experiment.

This is a prospective child of immutable Stage 6O artifacts.  It fixes the
seed-versus-toggle and frozen-rescue semantics in a new namespace, audits the
motion writer, and independently compares variance and causal-contrast bases.
The protected final reserve is deliberately unreachable from this module.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
import math
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
from . import motif_writer_closure as wc
from .life_family import life_rule_notation


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_POLARITY_CLOSURE_PROTOCOL.md"
DISCOVERY_LOG = ROOT / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"
DEFAULT_STAGE6O_ROOT = ROOT / "results/ca-motif-counterfactual-carrier-stage-6o"
DEFAULT_STAGE6N_ROOT = co.DEFAULT_STAGE6N_ROOT
DEFAULT_STAGE6M_ROOT = co.DEFAULT_STAGE6M_ROOT
DEFAULT_STAGE6L_ROOT = co.DEFAULT_STAGE6L_ROOT
PARENT_STAGE6O_DIGEST = (
    "c0c8822730c7f050a168560f1a370bd351e8b58c45b4cce9480a0c6e993e9ff4"
)
PHASES = (
    "integrity",
    "allocation",
    "motion-fit",
    "motion-transition-audit",
    "motion-validation",
    "motion-endurance",
    "compact-basis-fit",
    "compact-causal-screen",
    "compact-attractor-fit",
    "compact-contraction",
    "compact-closed-loop",
    "compact-validation",
    "adjudicate",
)


@dataclass(frozen=True)
class PolarityClosureProfile:
    development_pairs: int
    procedural_validation_pairs: int
    trace_replicates: int
    validation_replicates: int
    rollout_rounds: int
    maximum_frozen_writers: int
    compact_start: int
    compact_pairs: int
    motion_scan_per_rule: int
    motion_development_pairs: int
    motion_validation_pairs: int
    motion_transition_pairs: int
    motion_generations: int
    bootstrap_resamples: int

    def stage6o_profile(self) -> co.CounterfactualCarrierProfile:
        smoke = self.development_pairs <= 6
        return co.CounterfactualCarrierProfile(
            self.development_pairs,
            self.procedural_validation_pairs,
            self.trace_replicates,
            self.validation_replicates,
            self.rollout_rounds,
            self.maximum_frozen_writers,
            self.compact_start,
            self.compact_pairs,
            (4, 16),
            ("leaky",) if smoke else ("leaky", "contractive-tanh", "prototype"),
            (8,) if smoke else (8, 16),
            (16,) if smoke else (16, 24),
            self.motion_scan_per_rule,
            self.motion_development_pairs,
            self.motion_validation_pairs,
            min(8, self.motion_development_pairs),
            (2, 4, 8, 16, 32),
            self.bootstrap_resamples,
        )

    def causal_profile(self) -> cn.CausalAttractorProfile:
        return self.stage6o_profile().causal_profile()


PROFILES = {
    "smoke": PolarityClosureProfile(
        6, 2, 1, 1, 1, 1, 0, 2, 512, 4, 2, 1, 2, 100
    ),
    "reference": PolarityClosureProfile(
        56, 16, 2, 4, 3, 2, 24, 16, 8192, 40, 24, 8, 8, 10_000
    ),
}


@dataclass(frozen=True)
class PolarityClosureContract(co.CounterfactualCarrierContract):
    implementation_version: str = "ca-motif-polarity-closure-v1"
    namespace: str = "plastic-ca-motif-polarity-closure-v1"
    motion_generation8_minimum: float = 0.55
    motion_signed_generation4_minimum: float = 0.40
    motion_signed_generation8_minimum: float = 0.30
    motion_rescue_immediate_minimum: float = 0.75
    motion_rescue_rewrite_minimum: float = 0.60
    motion_invariance_generation4_minimum: float = 0.60
    outgoing_polarity_generation4_minimum: float = 0.60
    outgoing_polarity_worst_fold_minimum: float = 0.55

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "motion_generation8_minimum": self.motion_generation8_minimum,
                "motion_signed_generation4_minimum": self.motion_signed_generation4_minimum,
                "motion_signed_generation8_minimum": self.motion_signed_generation8_minimum,
                "motion_rescue_immediate_minimum": self.motion_rescue_immediate_minimum,
                "motion_rescue_rewrite_minimum": self.motion_rescue_rewrite_minimum,
                "motion_invariance_generation4_minimum": self.motion_invariance_generation4_minimum,
                "outgoing_polarity_generation4_minimum": self.outgoing_polarity_generation4_minimum,
                "outgoing_polarity_worst_fold_minimum": self.outgoing_polarity_worst_fold_minimum,
                "motion_payload_maximum_bits": 8,
                "motion_semantics": "absolute-seed-once-then-visible-renewal",
                "rescue_target": "frozen-parental-code",
                "compact_basis_families": (
                    "frozen-pca",
                    "paired-history-contrast-svd",
                    "hybrid-pca8-contrast8",
                    "supervised-reduced-rank-regression",
                ),
                "final_reserve_policy": "unreachable-and-never-open-in-stage-6p",
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
        "stage6o/COHORTS.json",
        "stage6o/MOTION_VALIDATION_BANK.json",
        "stage6o/motion-counterfactual-oracle/RESULTS.json",
        "stage6o/motion-renewal-validation/RESULTS.json",
        "compact-confirmation/RESULTS.json",
        "COMPLETE",
    )
    missing = [str(stage6o_root / name) for name in required if not (stage6o_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6O artifacts: {missing}")
    result = _load_json(stage6o_root / "RESULTS.json")
    status = _load_json(stage6o_root / "STATUS.json")
    design = _load_json(stage6o_root / "DESIGN.json")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6P requires a complete Stage-6O parent")
    if result.get("design_digest") != PARENT_STAGE6O_DIGEST:
        raise ValueError("Stage-6P parent Stage-6O design is not the frozen run")
    if result.get("verdict") != "MOTION_COMMAND_CONTROL_ONLY":
        raise ValueError("Stage-6P requires the registered Stage-6O boundary")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6O final reserve was touched")
    expected = design.get("implementation_hashes", {}).get(
        "motif_counterfactual_carrier.py"
    )
    if expected != ar._sha256(Path(co.__file__)):
        raise ValueError("Stage-6O implementation changed after its frozen run")
    ancestry = co._parent_integrity(stage6n_root, stage6m_root, stage6l_root)
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "parent_result_sha256": ar._sha256(stage6o_root / "RESULTS.json"),
        "stage6o_required_hashes": {
            name: ar._sha256(stage6o_root / name) for name in required
        },
        "procedural_pair_ids_sha256": ancestry["procedural_pair_ids_sha256"],
        "procedural_trajectories_sealed": True,
        "final_pair_count": 62,
        "final_pair_ids_sha256": ancestry["final_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
    }


def _circular_center(coordinates: np.ndarray, extent: int) -> int:
    """Center the shortest circular arc containing the occupied coordinates."""

    values = np.unique(np.asarray(coordinates, dtype=np.int64) % int(extent))
    if not len(values):
        return int(extent // 2)
    if len(values) == 1:
        return int(values[0])
    gaps = np.diff(np.concatenate((values, values[:1] + int(extent))))
    gap_index = int(np.argmax(gaps))
    start = int(values[(gap_index + 1) % len(values)])
    unwrapped = ((values - start) % int(extent)) + start
    return int(np.rint((unwrapped.min() + unwrapped.max()) / 2.0)) % int(extent)


def _wrap_crop_centered(state: np.ndarray, size: int = 8) -> np.ndarray:
    values = np.asarray(state, dtype=np.bool_)
    coordinates = np.argwhere(values)
    if len(coordinates):
        center = (
            _circular_center(coordinates[:, 0], values.shape[0]),
            _circular_center(coordinates[:, 1], values.shape[1]),
        )
    else:
        center = (values.shape[0] // 2, values.shape[1] // 2)
    offsets = np.arange(-(size // 2), size - size // 2)
    ys = (int(center[0]) + offsets) % values.shape[0]
    xs = (int(center[1]) + offsets) % values.shape[1]
    return values[np.ix_(ys, xs)].copy()


def _wrap_motion_features(
    history: Sequence[np.ndarray], endpoint: int
) -> np.ndarray:
    selected = list(history[max(0, endpoint - 7) : endpoint + 1])
    while len(selected) < 8:
        selected.insert(0, selected[0])
    local = np.stack(
        [np.where(_wrap_crop_centered(state), 1.0, -1.0) for state in selected]
    ).astype(np.float32)
    blocks = np.stack(
        (
            local[-1],
            np.mean(local, axis=0),
            np.float32(0.5) * (local[-1] - local[0]),
            np.mean(np.float32(0.5) * np.abs(np.diff(local, axis=0)), axis=0),
        )
    )
    return np.concatenate((blocks.reshape(-1), np.ones(1, dtype=np.float32)))


def _motion_training_rows(
    pairs: Sequence[dict[str, Any]], *, wrap_aware: bool
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    feature_rows: list[np.ndarray] = []
    shapes: list[np.ndarray] = []
    orientations: list[int] = []
    groups: list[str] = []
    rules: list[int] = []
    feature_fn = _wrap_motion_features if wrap_aware else il._motion_features
    for pair in pairs:
        rule = int(pair["rule"])
        for direction in ("forward", "opposite"):
            specification = pair[direction]
            initial = wc._unpack_state_hex(specification["initial_hex"], (32, 32))
            history = wc._simulate_history(initial, rule, 64)
            period = int(specification["period"])
            for endpoint in range(16, 16 + period):
                base = feature_fn(history, endpoint)
                canonical, _ = lm._canonicalize_motion_phase(
                    history,
                    endpoint,
                    period,
                    specification["displacement_yx"],
                )
                for symmetry in range(8):
                    blocks = il._d4_blocks(base[:-1].reshape(4, 8, 8), symmetry)
                    feature_rows.append(
                        np.concatenate(
                            (blocks.reshape(-1), np.ones(1, dtype=np.float32))
                        )
                    )
                    displacement = il._transform_velocity(
                        specification["displacement_yx"], symmetry
                    )
                    orientations.append(lm._orientation_from_velocity(displacement))
                    shapes.append(canonical.reshape(-1))
                    groups.append(str(pair["pair_id"]))
                    rules.append(rule)
    return (
        np.asarray(feature_rows, dtype=np.float32),
        np.asarray(shapes, dtype=np.float32),
        np.asarray(orientations, dtype=np.int8),
        np.asarray(groups, dtype=str),
        np.asarray(rules, dtype=np.int64),
    )


def _best_bijection(raw: np.ndarray, target: np.ndarray) -> list[int]:
    confusion = np.zeros((8, 8), dtype=np.int64)
    for left, right in zip(raw.tolist(), target.tolist(), strict=True):
        confusion[int(left) % 8, int(right) % 8] += 1
    best_score = -1
    best = tuple(range(8))
    for permutation in itertools.permutations(range(8)):
        score = sum(confusion[index, permutation[index]] for index in range(8))
        if score > best_score:
            best_score = int(score)
            best = permutation
    return [int(value) for value in best]


def _predict_head(model: dict[str, Any], features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    design = cn._motion_design(np.asarray(features, dtype=np.float32), model)
    shapes = np.argmax(
        design @ np.asarray(model["shape_weights"], dtype=np.float32)
        + np.asarray(model["shape_bias"], dtype=np.float32),
        axis=1,
    )
    orientations = np.argmax(
        design @ np.asarray(model["orientation_weights"], dtype=np.float32)
        + np.asarray(model["orientation_bias"], dtype=np.float32),
        axis=1,
    )
    return shapes.astype(np.int16), orientations.astype(np.int8)


def _load_parent_motion_model(stage6n_root: Path) -> dict[str, Any]:
    path = (
        stage6n_root
        / "stage6n/motion-medoid-fit/checkpoints/"
        "rule-conditioned-medoid-k8.json"
    )
    payload = _load_json(path)
    fitted = payload["fitted"]
    model = copy.deepcopy(fitted["model"])
    if model.get("model_digest") != (
        "8fbcdce8a10be1330b2d19e1d281818e99f4b207e085f06a066d53d41546f606"
    ):
        raise ValueError("Stage-6P selected Stage-6O motion model changed")
    return model


def _fit_wrap_model(
    features: np.ndarray,
    shapes: np.ndarray,
    orientations: np.ndarray,
    groups: np.ndarray,
    rules: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    folds = wc._pair_blocked_folds(groups, min(6, len(set(groups.tolist()))))
    fold_rows: list[dict[str, Any]] = []
    fold_models: dict[str, dict[str, Any]] = {}
    for fold in sorted(set(folds.tolist())):
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
            ar._hash_seed("stage6p-wrap-motion", int(fold)),
        )
        model["model_id"] = f"stage6p-wrap-aware-fold{int(fold)}"
        model["feature_mode"] = "wrap-aware-shortest-circular-arc"
        model["model_digest"] = _digest(model)
        fold_models[str(int(fold))] = model
        shape_prediction, direction_prediction = _predict_head(model, features[test])
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
                "fold": int(fold),
                "test_pair_count": len(set(groups[test].tolist())),
                "foreground_f1": float(
                    np.mean(
                        [
                            cn._foreground_vector_f1(left, right)
                            for left, right in zip(decoded, shapes[test], strict=True)
                        ]
                    )
                ),
                "orientation_accuracy": float(
                    np.mean(direction_prediction == orientations[test])
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
        ar._hash_seed("stage6p-wrap-motion", "full"),
    )
    model["model_id"] = "stage6p-wrap-aware-rule-conditioned-medoid-k8"
    model["feature_mode"] = "wrap-aware-shortest-circular-arc"
    model["model_digest"] = _digest(model)
    return model, fold_rows, fold_models


def _fit_calibrations(
    model: dict[str, Any],
    features: np.ndarray,
    orientations: np.ndarray,
    rules: np.ndarray,
    train: np.ndarray | None = None,
) -> tuple[list[int], dict[str, list[int]]]:
    mask = np.ones(len(features), dtype=np.bool_) if train is None else train
    _, raw = _predict_head(model, features[mask])
    target = orientations[mask]
    global_map = _best_bijection(raw, target)
    rule_maps: dict[str, list[int]] = {}
    selected_rules = rules[mask]
    for rule in sorted(set(selected_rules.tolist())):
        local = selected_rules == rule
        rule_maps[str(int(rule))] = _best_bijection(raw[local], target[local])
    return global_map, rule_maps


def _orientation_after_calibration(
    candidate: dict[str, Any], orientation: int, rule: int
) -> int:
    kind = str(candidate.get("calibration_kind", "none"))
    if kind == "global":
        return int(candidate["global_orientation_map"][int(orientation) % 8])
    if kind == "rule-conditioned":
        mapping = candidate.get("rule_orientation_maps", {}).get(str(int(rule)))
        if mapping is not None:
            return int(mapping[int(orientation) % 8])
    return int(orientation) % 8


def _visible_orientation(
    history: Sequence[np.ndarray],
    endpoint: int,
    retention: float | None,
    fallback: int,
) -> tuple[int, dict[str, Any]]:
    final_endpoint = min(len(history) - 1, int(endpoint))
    if retention is None:
        detection = wc._detect_mover(list(history[: final_endpoint + 1]))
        if detection is None:
            return int(fallback), {
                "visible_velocity_detected": False,
                "latch_state_yx": [0.0, 0.0],
            }
        displacement = tuple(float(value) for value in detection["displacement_yx"])
        return lm._orientation_from_velocity(displacement), {
            "visible_velocity_detected": True,
            "visible_displacement_yx": list(displacement),
            "latch_state_yx": list(displacement),
        }
    state = np.zeros(2, dtype=np.float32)
    observations = 0
    start = min(final_endpoint, 16)
    endpoints = list(range(start, final_endpoint + 1, 4))
    if not endpoints or endpoints[-1] != final_endpoint:
        endpoints.append(final_endpoint)
    for current in endpoints:
        detection = wc._detect_mover(list(history[: current + 1]))
        if detection is None:
            continue
        evidence = np.asarray(detection["displacement_yx"], dtype=np.float32)
        scale = max(1.0, float(np.max(np.abs(evidence))))
        evidence /= np.float32(scale)
        state = np.float32(retention) * state + np.float32(
            1.0 - retention
        ) * evidence
        observations += 1
    if observations == 0 or float(np.max(np.abs(state))) < 1e-6:
        return int(fallback), {
            "visible_velocity_detected": False,
            "latch_retention": float(retention),
            "latch_observations": observations,
            "latch_state_yx": state.tolist(),
        }
    return lm._orientation_from_velocity(state), {
        "visible_velocity_detected": True,
        "latch_retention": float(retention),
        "latch_observations": observations,
        "latch_state_yx": state.tolist(),
    }


def _predict_candidate(
    candidate: dict[str, Any], history: Sequence[np.ndarray], rule: int
) -> tuple[int, int, dict[str, Any]]:
    model = candidate["model"]
    endpoint = min(len(history) - 1, int(candidate.get("endpoint", len(history) - 1)))
    if str(candidate.get("feature_mode", "legacy")) == "wrap-aware":
        feature = _wrap_motion_features(history, endpoint)[None]
        shape_rows, orientation_rows = _predict_head(model, feature)
        shape = int(shape_rows[0])
        raw_orientation = int(orientation_rows[0])
    else:
        feature = il._motion_features(history, endpoint)[None]
        shape_rows, orientation_rows = _predict_head(model, feature)
        shape = int(shape_rows[0])
        raw_orientation = int(orientation_rows[0])
    calibrated = _orientation_after_calibration(candidate, raw_orientation, rule)
    writer_kind = str(candidate.get("writer_kind", "ridge-head"))
    metadata: dict[str, Any] = {
        "head_orientation": raw_orientation,
        "calibrated_orientation": calibrated,
        "writer_kind": writer_kind,
        "writer_endpoint": endpoint,
    }
    orientation = calibrated
    if writer_kind == "factorized-visible-velocity":
        orientation, detected = _visible_orientation(
            history, endpoint, None, calibrated
        )
        metadata.update(detected)
    elif writer_kind == "slow-polarity-latch":
        orientation, detected = _visible_orientation(
            history,
            endpoint,
            float(candidate["latch_retention"]),
            calibrated,
        )
        metadata.update(detected)
    return shape, int(orientation), metadata


def _candidate_public(candidate: dict[str, Any]) -> dict[str, Any]:
    model = candidate["model"]
    return {
        key: copy.deepcopy(value)
        for key, value in candidate.items()
        if key not in ("model", "fold_models", "fold_calibrations")
    } | {
        "model_id": model["model_id"],
        "model_digest": model["model_digest"],
        "decoder_family": model["decoder_family"],
        "shape_bits": int(model["shape_bits"]),
        "payload_bits": int(candidate["payload_bits"]),
    }


def _motion_candidate_ladder(
    development_pairs: Sequence[dict[str, Any]],
    stage6n_root: Path,
    profile_name: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parent = _load_parent_motion_model(stage6n_root)
    legacy = _motion_training_rows(development_pairs, wrap_aware=False)
    wrapped = _motion_training_rows(development_pairs, wrap_aware=True)
    features, shapes, orientations, groups, rules = legacy
    wrap_features, wrap_shapes, wrap_orientations, wrap_groups, wrap_rules = wrapped
    wrap_model, wrap_folds, wrap_fold_models = _fit_wrap_model(
        wrap_features, wrap_shapes, wrap_orientations, wrap_groups, wrap_rules
    )
    global_map, rule_maps = _fit_calibrations(
        parent, features, orientations, rules
    )
    example_folds = wc._pair_blocked_folds(
        groups, min(6, len(set(groups.tolist())))
    )
    fold_calibrations: dict[str, dict[str, Any]] = {}
    for fold in sorted(set(example_folds.tolist())):
        train = example_folds != fold
        fold_global, fold_rules = _fit_calibrations(
            parent, features, orientations, rules, train
        )
        fold_calibrations[str(int(fold))] = {
            "global_orientation_map": fold_global,
            "rule_orientation_maps": fold_rules,
        }
    base = {
        "candidate_id": "stage6p-frozen-stage6o-baseline",
        "model": parent,
        "feature_mode": "legacy",
        "writer_kind": "ridge-head",
        "calibration_kind": "none",
        "endpoint": 48,
        "payload_bits": int(parent["payload_bits"]),
        "frozen_stage6o_baseline": True,
    }
    candidates: list[dict[str, Any]] = [base]
    candidates.append(
        {
            **base,
            "candidate_id": "stage6p-wrap-aware-refit",
            "model": wrap_model,
            "feature_mode": "wrap-aware",
            "frozen_stage6o_baseline": False,
            "fold_models": wrap_fold_models,
        }
    )
    candidates.append(
        {
            **base,
            "candidate_id": "stage6p-global-d4-calibration",
            "calibration_kind": "global",
            "global_orientation_map": global_map,
            "fold_calibrations": fold_calibrations,
        }
    )
    candidates.append(
        {
            **base,
            "candidate_id": "stage6p-rule-conditioned-d4-calibration",
            "calibration_kind": "rule-conditioned",
            "global_orientation_map": global_map,
            "rule_orientation_maps": rule_maps,
            "fold_calibrations": fold_calibrations,
        }
    )
    candidates.append(
        {
            **base,
            "candidate_id": "stage6p-factorized-axis-polarity",
            "writer_kind": "factorized-visible-velocity",
            "endpoint": 32,
            "payload_bits": 7,
            "threefold_polarity_bit": True,
        }
    )
    latch_grid = tuple(
        (retention, endpoint)
        for endpoint in (24, 32)
        for retention in (0.50, 0.75, 0.90)
    )
    if profile_name == "smoke":
        latch_grid = ((0.75, 24),)
    for retention, endpoint in latch_grid:
        candidates.append(
            {
                **base,
                "candidate_id": (
                    f"stage6p-slow-latch-r{int(round(retention * 100)):02d}-"
                    f"e{endpoint}"
                ),
                "writer_kind": "slow-polarity-latch",
                "endpoint": endpoint,
                "latch_retention": retention,
                "latch_input_gain": 1.0 - retention,
                "zero_born_latch": True,
                "threefold_polarity_bit": True,
                "payload_bits": 7,
            }
        )
    if len(candidates) > 12:
        raise AssertionError("Stage-6P motion ladder exceeds twelve candidates")
    metadata = {
        "legacy_training_examples": len(features),
        "wrap_training_examples": len(wrap_features),
        "training_pair_count": len(set(groups.tolist())),
        "wrap_cross_validation": wrap_folds,
        "calibration_fit_is_out_of_fold": True,
        "global_orientation_map": global_map,
        "rule_orientation_maps": rule_maps,
        "candidate_count": len(candidates),
    }
    return candidates, metadata


def _pair_fold_map(pairs: Sequence[dict[str, Any]]) -> dict[str, int]:
    groups = np.asarray([str(pair["pair_id"]) for pair in pairs], dtype=str)
    folds = wc._pair_blocked_folds(groups, min(6, len(groups)))
    return {
        str(pair["pair_id"]): int(fold)
        for pair, fold in zip(pairs, folds.tolist(), strict=True)
    }


def _screen_motion_candidates(
    candidates: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    fold_map = _pair_fold_map(pairs)
    summaries: dict[str, Any] = {}
    ranked: list[tuple[float, str, dict[str, Any]]] = []
    for candidate in candidates:
        fold_values: dict[int, list[dict[str, float]]] = {}
        for pair in pairs:
            pair_id = str(pair["pair_id"])
            rule = int(pair["rule"])
            fold = fold_map[pair_id]
            local_candidate = dict(candidate)
            fold_models = candidate.get("fold_models", {})
            if str(fold) in fold_models:
                local_candidate["model"] = fold_models[str(fold)]
            calibrations = candidate.get("fold_calibrations", {})
            if str(fold) in calibrations:
                local_candidate.update(calibrations[str(fold)])
            for direction in ("forward", "opposite"):
                specification = pair[direction]
                initial = wc._unpack_state_hex(
                    specification["initial_hex"], (32, 32)
                )
                history = wc._simulate_history(initial, rule, 64)
                shape, orientation, _ = _predict_candidate(
                    local_candidate, history, rule
                )
                target_shape, target_orientation = cn._oracle_motion_code(
                    local_candidate["model"], history, specification, rule
                )
                predicted_patch = cn._decode_motion_code(
                    local_candidate["model"], shape, orientation, rule
                )
                target_patch = cn._decode_motion_code(
                    local_candidate["model"], target_shape, target_orientation, rule
                )
                form = co._d4_foreground_overlap(
                    predicted_patch >= 0.0, target_patch >= 0.0
                )["foreground_f1"]
                fold_values.setdefault(fold, []).append(
                    {
                        "form": float(form),
                        "orientation": float(orientation == target_orientation),
                    }
                )
        fold_rows: list[dict[str, Any]] = []
        for fold in sorted(fold_values):
            values = fold_values[fold]
            fold_rows.append(
                {
                    "fold": fold,
                    "foreground_f1": float(np.mean([row["form"] for row in values])),
                    "orientation_accuracy": float(
                        np.mean([row["orientation"] for row in values])
                    ),
                }
            )
        form_mean = float(np.mean([row["foreground_f1"] for row in fold_rows]))
        orientation_mean = float(
            np.mean([row["orientation_accuracy"] for row in fold_rows])
        )
        orientation_worst = float(
            np.min([row["orientation_accuracy"] for row in fold_rows])
        )
        score = 0.45 * form_mean + 0.40 * orientation_mean + 0.15 * orientation_worst
        candidate_id = str(candidate["candidate_id"])
        summaries[candidate_id] = {
            "candidate": _candidate_public(candidate),
            "pair_blocked_fold_count": len(fold_rows),
            "folds": fold_rows,
            "foreground_f1_mean": form_mean,
            "orientation_accuracy_mean": orientation_mean,
            "orientation_accuracy_worst_fold": orientation_worst,
            "selection_score": score,
            "target_labels_used_at_runtime": False,
            "fit_exposure": "development-only",
            "out_of_fold_fit_used_when_candidate_has_stage6p_parameters": True,
        }
        ranked.append((score, candidate_id, candidate))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    selected = [row[2] for row in ranked[: min(2, len(ranked))]]
    result = {
        "state": "complete",
        "stage_gate": bool(selected),
        "registered_candidate_count": len(candidates),
        "completed_candidate_count": len(summaries),
        "selected_candidate_ids": [row["candidate_id"] for row in selected],
        "candidate_summaries": summaries,
        "six_pair_blocked_folds": profile_name == "reference",
        "maximum_advanced_candidates": 2,
        "final_audit_trajectory_state": "untouched",
    }
    return result, selected


def _payload_bits(candidate: dict[str, Any], shape: int, orientation: int) -> np.ndarray:
    shape_bits = int(candidate["model"]["shape_bits"])
    if not bool(candidate.get("threefold_polarity_bit", False)):
        return lm._bits_for_code(shape, orientation, shape_bits)
    values = [int(shape >> bit) & 1 for bit in range(shape_bits)]
    normalized = int(orientation) % 4
    axis = normalized & 1
    sign = (normalized >> 1) & 1
    values.extend((axis, sign, sign, sign))
    return np.asarray(values, dtype=np.uint8)


def _payload_code(
    candidate: dict[str, Any], bits: np.ndarray
) -> tuple[int, int, dict[str, Any]]:
    values = np.asarray(bits, dtype=np.uint8).reshape(-1)
    shape_bits = int(candidate["model"]["shape_bits"])
    if not bool(candidate.get("threefold_polarity_bit", False)):
        shape, orientation = lm._code_from_bits(values, shape_bits)
        return shape, orientation, {"polarity_vote": None}
    shape = sum(int(values[bit]) << bit for bit in range(shape_bits))
    axis = int(values[shape_bits])
    votes = values[shape_bits + 1 : shape_bits + 4]
    sign = int(np.sum(votes) >= 2)
    return shape, axis + 2 * sign, {
        "polarity_vote": votes.astype(int).tolist(),
        "polarity_majority": sign,
    }


def _condition_target(
    condition: str,
    generation: int,
    original_orientation: int,
    opposite_orientation: int,
) -> int:
    if condition in ("opposite_seed", "opposite_clamped"):
        return opposite_orientation
    if condition == "opposite_rescue" and generation >= 3:
        return opposite_orientation
    return original_orientation


def _corrected_motion_lineage(
    candidate: dict[str, Any],
    pair: dict[str, Any],
    direction: str,
    condition: str,
    *,
    generations: int = 8,
    corruption: float = 0.01,
) -> dict[str, Any]:
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
    generation_rows: list[dict[str, Any]] = []
    for generation in range(1, generations + 1):
        raw_shape, raw_orientation, raw_metadata = _predict_candidate(
            candidate, history, rule
        )
        write_shape, write_orientation = raw_shape, raw_orientation
        intervention = "learned-write"
        active = True
        if condition == "original_seed" and generation == 1:
            write_shape, write_orientation = frozen_shape, frozen_original
            intervention = "frozen-original-seed-once"
        elif condition == "opposite_seed" and generation == 1:
            write_shape, write_orientation = frozen_shape, frozen_opposite
            intervention = "frozen-opposite-seed-once"
        elif condition == "original_clamped":
            write_shape, write_orientation = frozen_shape, frozen_original
            intervention = "frozen-original-oracle-clamp"
        elif condition == "opposite_clamped":
            write_shape, write_orientation = frozen_shape, frozen_opposite
            intervention = "frozen-opposite-oracle-clamp"
        elif condition == "repeated_toggle":
            write_orientation = lm._opposite_orientation(raw_orientation, diagonal)
            intervention = "diagnostic-toggle-current-prediction"
        elif condition == "learned_shape_oracle_polarity":
            write_orientation = frozen_original
            intervention = "oracle-polarity-head-only"
        elif condition == "oracle_shape_learned_polarity":
            write_shape = frozen_shape
            intervention = "oracle-shape-head-only"
        elif condition in ("matching_rescue", "opposite_rescue") and generation == 2:
            active = False
            intervention = "carrier-ablated"
        elif condition == "matching_rescue" and generation == 3:
            write_shape, write_orientation = frozen_shape, frozen_original
            intervention = "frozen-parent-matching-rescue"
        elif condition == "opposite_rescue" and generation == 3:
            write_shape, write_orientation = frozen_shape, frozen_opposite
            intervention = "frozen-parent-opposite-rescue"
        elif condition in ("zero", "read_disabled", "write_disabled"):
            active = False
            intervention = condition
        elif condition == "no_renewal" and generation > 1:
            active = False
            intervention = "renewal-disabled-after-first-boundary"
        elif condition == "ablation" and generation >= 3:
            active = False
            intervention = "carrier-ablated-from-generation-three"
        written = _payload_bits(candidate, write_shape, write_orientation)
        incoming = written.copy()
        if condition == "shuffle" and active:
            rng = np.random.default_rng(
                ar._hash_seed(
                    "stage6p-motion-shuffle",
                    pair["pair_id"],
                    direction,
                    generation,
                )
            )
            incoming = incoming[rng.permutation(len(incoming))]
            intervention = "payload-shuffle"
        if not active:
            incoming.fill(0)
        copied, exact = lm._bit_codec_roundtrip(
            incoming,
            ar._hash_seed(
                "stage6p-motion-copy",
                pair["pair_id"],
                direction,
                condition,
                generation,
            ),
            corruption=corruption,
        )
        decoded_shape, decoded_orientation, codec = _payload_code(candidate, copied)
        patch = cn._decode_motion_code(
            model, decoded_shape, decoded_orientation, rule
        )
        if not active:
            patch = np.zeros_like(patch)
        center = (16, 16)
        if condition == "translation_scrub":
            rng = np.random.default_rng(
                ar._hash_seed(
                    "stage6p-motion-translation",
                    pair["pair_id"],
                    direction,
                    generation,
                )
            )
            center = (int(rng.integers(8, 25)), int(rng.integers(8, 25)))
        elif condition == "seam_scrub":
            center = (
                0 if generation % 2 else 31,
                31 if generation % 2 else 0,
            )
        reset = lm._install_motion_patch_at(patch, center)
        phase_advance = 0
        if condition == "phase_scrub":
            phase_advance = int(
                ar._hash_seed(
                    "stage6p-motion-phase",
                    pair["pair_id"],
                    direction,
                    generation,
                )
                % max(1, int(specification["period"]))
            )
            if phase_advance:
                reset = wc._simulate_history(reset, rule, phase_advance)[-1]
        new_history = wc._simulate_history(reset, rule, 48)
        target_orientation = _condition_target(
            condition, generation, frozen_original, frozen_opposite
        )
        instructed = original_displacement
        if target_orientation == frozen_opposite:
            instructed = (-original_displacement[0], -original_displacement[1])
        metrics = co._counterfactual_motion_metrics(
            new_history, original_history, instructed, original_displacement
        )
        outgoing_shape, outgoing_orientation, outgoing_metadata = _predict_candidate(
            candidate, new_history, rule
        )
        generation_rows.append(
            {
                "generation": generation,
                "frozen_parent_shape_code": frozen_shape,
                "frozen_parent_original_orientation": frozen_original,
                "frozen_parent_opposite_orientation": frozen_opposite,
                "target_orientation": target_orientation,
                "raw_writer_shape_code": raw_shape,
                "raw_writer_orientation": raw_orientation,
                "raw_writer_metadata": raw_metadata,
                "intervention": intervention,
                "written_shape_code": write_shape,
                "written_orientation": write_orientation,
                "written_payload": written.astype(int).tolist(),
                "copied_payload": copied.astype(int).tolist(),
                "copy_exact": exact,
                "copy_corruption": float(corruption),
                "decoded_shape_code": decoded_shape,
                "decoded_orientation": decoded_orientation,
                "codec_diagnostics": codec,
                "outgoing_writer_shape_code": outgoing_shape,
                "outgoing_writer_orientation": outgoing_orientation,
                "outgoing_writer_metadata": outgoing_metadata,
                "outgoing_polarity_correct": bool(
                    outgoing_orientation == target_orientation
                ),
                "carrier_active": active,
                "daughter_rewrite_active": bool(
                    condition not in ("write_disabled", "no_renewal")
                    and not (condition == "ablation" and generation >= 3)
                ),
                "visible_reset_zero_before_carrier_read": True,
                "translation_center": list(center),
                "phase_advance": phase_advance,
                "instructed_displacement_yx": list(instructed),
                "original_displacement_yx": list(original_displacement),
                **metrics,
            }
        )
        history = new_history
    return {
        "candidate_id": candidate["candidate_id"],
        "pair_id": pair["pair_id"],
        "condition": condition,
        "direction": direction,
        "generations": generation_rows,
        "absolute_command_semantics": True,
        "opposite_seed_applied_once": condition == "opposite_seed",
        "rescue_uses_frozen_parent_code": condition in (
            "matching_rescue",
            "opposite_rescue",
        ),
        "all_boundaries_visibly_reset": True,
    }


def _run_transition_audit(
    stage_root: Path,
    candidates: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile: PolarityClosureProfile,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Callable[..., None],
) -> dict[str, Any]:
    root = stage_root / "motion-transition-audit"
    root.mkdir(parents=True, exist_ok=True)
    selected_pairs = list(pairs[: profile.motion_transition_pairs])
    graph_summaries: dict[str, Any] = {}
    completed = 0
    registered = len(candidates) * len(selected_pairs)
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        matrices: dict[str, np.ndarray] = {}
        row_count = 0
        for pair in selected_pairs:
            checkpoint = root / f"{candidate_id}-{pair['pair_id']}.json"
            if resume and checkpoint.exists():
                payload = _load_json(checkpoint)
                rows = payload["rows"]
            else:
                if time.time() >= deadline:
                    break
                rows: list[dict[str, Any]] = []
                rule = int(pair["rule"])
                for direction in ("forward", "opposite"):
                    specification = pair[direction]
                    initial = wc._unpack_state_hex(
                        specification["initial_hex"], (32, 32)
                    )
                    original = wc._simulate_history(initial, rule, 64)
                    shape, _ = cn._oracle_motion_code(
                        candidate["model"], original, specification, rule
                    )
                    for phase in range(max(1, int(specification["period"]))):
                        for incoming_orientation in range(8):
                            for noise_name, corruption in (
                                ("zero", 0.0),
                                ("standard", 0.01),
                            ):
                                bits = _payload_bits(
                                    candidate, shape, incoming_orientation
                                )
                                copied, exact = lm._bit_codec_roundtrip(
                                    bits,
                                    ar._hash_seed(
                                        "stage6p-transition",
                                        candidate_id,
                                        pair["pair_id"],
                                        direction,
                                        phase,
                                        incoming_orientation,
                                        noise_name,
                                    ),
                                    corruption=corruption,
                                )
                                decoded_shape, decoded_orientation, _ = _payload_code(
                                    candidate, copied
                                )
                                patch = cn._decode_motion_code(
                                    candidate["model"],
                                    decoded_shape,
                                    decoded_orientation,
                                    rule,
                                )
                                reset = lm._install_motion_patch_at(patch, (16, 16))
                                if phase:
                                    reset = wc._simulate_history(reset, rule, phase)[-1]
                                history = wc._simulate_history(reset, rule, 48)
                                _, outgoing, metadata = _predict_candidate(
                                    candidate, history, rule
                                )
                                detection = wc._detect_mover(history)
                                rows.append(
                                    {
                                        "rule": rule,
                                        "shape_code": shape,
                                        "pair_id": pair["pair_id"],
                                        "direction": direction,
                                        "phase": phase,
                                        "noise": noise_name,
                                        "incoming_orientation": incoming_orientation,
                                        "decoded_orientation": decoded_orientation,
                                        "outgoing_orientation": outgoing,
                                        "copy_exact": exact,
                                        "mover_detected": detection is not None,
                                        "observed_displacement_yx": (
                                            list(detection["displacement_yx"])
                                            if detection is not None
                                            else None
                                        ),
                                        "writer_metadata": metadata,
                                    }
                                )
                ar._atomic_json(
                    checkpoint,
                    {"design_digest": design_digest, "rows": rows},
                )
            completed += 1
            row_count += len(rows)
            for row in rows:
                key = (
                    f"r{row['rule']}|s{row['shape_code']}|p{row['phase']}|"
                    f"{row['noise']}"
                )
                matrix = matrices.setdefault(
                    key, np.zeros((8, 8), dtype=np.int64)
                )
                matrix[
                    int(row["incoming_orientation"]),
                    int(row["outgoing_orientation"]),
                ] += 1
            status(
                "running",
                "map-eight-orientation-transitions",
                completed=completed,
                total=registered,
                candidate_id=candidate_id,
            )
        graph_summaries[candidate_id] = {
            "row_count": row_count,
            "matrix_count": len(matrices),
            "matrices": {
                key: value.astype(int).tolist() for key, value in matrices.items()
            },
        }
    complete = completed == registered
    return {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "candidate_count": len(graph_summaries),
        "pair_count": len(selected_pairs),
        "noise_levels": {"zero": 0.0, "standard": 0.01},
        "orientation_count": 8,
        "graphs": graph_summaries,
        "translation_centering": "shortest-occupied-toroidal-arc",
        "final_audit_trajectory_state": "untouched",
    }


MOTION_CONDITIONS = (
    "intact",
    "original_seed",
    "opposite_seed",
    "original_clamped",
    "opposite_clamped",
    "repeated_toggle",
    "phase_scrub",
    "translation_scrub",
    "seam_scrub",
    "zero",
    "shuffle",
    "read_disabled",
    "write_disabled",
    "no_renewal",
    "ablation",
    "matching_rescue",
    "opposite_rescue",
    "learned_shape_oracle_polarity",
    "oracle_shape_learned_polarity",
)


def _motion_rows_at(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
) -> list[dict[str, Any]]:
    return [
        lineage["generations"][generation - 1]
        for row in rows
        if row["candidate_id"] == candidate_id
        for key, lineage in row["conditions"].items()
        if key.endswith(f":{condition}")
        and len(lineage["generations"]) >= generation
    ]


def _motion_summary(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
) -> dict[str, float]:
    selected = _motion_rows_at(rows, candidate_id, condition, generation)
    if not selected:
        return {
            "mover_detection_fraction": 0.0,
            "form_success_fraction": 0.0,
            "instruction_direction_fraction": 0.0,
            "joint_success_fraction": 0.0,
            "foreground_f1_mean": 0.0,
            "instruction_direction_similarity_mean": 0.0,
            "signed_original_direction_similarity_mean": 0.0,
            "outgoing_polarity_accuracy": 0.0,
        }
    return {
        "mover_detection_fraction": float(
            np.mean([value["mover_detected"] for value in selected])
        ),
        "form_success_fraction": float(
            np.mean([value["form_success"] for value in selected])
        ),
        "instruction_direction_fraction": float(
            np.mean([value["correct_instruction_direction"] for value in selected])
        ),
        "joint_success_fraction": float(
            np.mean(
                [
                    value["form_success"]
                    and value["correct_instruction_direction"]
                    for value in selected
                ]
            )
        ),
        "foreground_f1_mean": float(
            np.mean([value["foreground_f1"] for value in selected])
        ),
        "instruction_direction_similarity_mean": float(
            np.mean([value["instruction_direction_similarity"] for value in selected])
        ),
        "signed_original_direction_similarity_mean": float(
            np.mean(
                [value["signed_original_direction_similarity"] for value in selected]
            )
        ),
        "outgoing_polarity_accuracy": float(
            np.mean([value["outgoing_polarity_correct"] for value in selected])
        ),
    }


def _outgoing_worst_fold(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    conditions: Sequence[str],
    generation: int,
) -> float:
    pair_rows = [row for row in rows if row["candidate_id"] == candidate_id]
    if not pair_rows:
        return 0.0
    pair_ids = sorted(set(str(row["pair_id"]) for row in pair_rows))
    groups = np.asarray(pair_ids, dtype=str)
    folds = wc._pair_blocked_folds(groups, min(6, len(groups)))
    fold_by_pair = dict(zip(pair_ids, folds.tolist(), strict=True))
    values: dict[int, list[float]] = {}
    for row in pair_rows:
        fold = int(fold_by_pair[str(row["pair_id"])])
        for key, lineage in row["conditions"].items():
            if not any(key.endswith(f":{condition}") for condition in conditions):
                continue
            if len(lineage["generations"]) < generation:
                continue
            values.setdefault(fold, []).append(
                float(lineage["generations"][generation - 1]["outgoing_polarity_correct"])
            )
    return min((float(np.mean(value)) for value in values.values()), default=0.0)


def _motion_gate(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    complete: bool,
    profile_name: str,
    contract: PolarityClosureContract,
) -> tuple[bool, dict[str, Any]]:
    candidate_id = str(candidate["candidate_id"])
    recovery = {
        condition: {
            f"generation{generation}": _motion_summary(
                rows, candidate_id, condition, generation
            )
            for generation in (1, 3, 4, 8)
        }
        for condition in MOTION_CONDITIONS
    }
    original1 = recovery["original_seed"]["generation1"]
    opposite1 = recovery["opposite_seed"]["generation1"]
    original4 = recovery["original_seed"]["generation4"]
    opposite4 = recovery["opposite_seed"]["generation4"]
    original8 = recovery["original_seed"]["generation8"]
    opposite8 = recovery["opposite_seed"]["generation8"]
    signed4 = (
        original4["signed_original_direction_similarity_mean"]
        - opposite4["signed_original_direction_similarity_mean"]
    )
    signed8 = (
        original8["signed_original_direction_similarity_mean"]
        - opposite8["signed_original_direction_similarity_mean"]
    )
    matching3 = recovery["matching_rescue"]["generation3"]
    opposite3 = recovery["opposite_rescue"]["generation3"]
    matching4 = recovery["matching_rescue"]["generation4"]
    opposite_rescue4 = recovery["opposite_rescue"]["generation4"]
    rescue_immediate = min(
        matching3["joint_success_fraction"], opposite3["joint_success_fraction"]
    )
    rescue_rewrite = min(
        matching4["joint_success_fraction"],
        opposite_rescue4["joint_success_fraction"],
    )
    invariance4 = min(
        recovery[condition]["generation4"]["joint_success_fraction"]
        for condition in ("phase_scrub", "translation_scrub", "seam_scrub")
    )
    null_maximum = max(
        recovery[condition]["generation8"]["mover_detection_fraction"]
        for condition in (
            "zero",
            "read_disabled",
            "write_disabled",
            "no_renewal",
            "ablation",
        )
    )
    renewal_advantage = (
        recovery["intact"]["generation8"]["joint_success_fraction"]
        - recovery["no_renewal"]["generation8"]["joint_success_fraction"]
    )
    outgoing4 = float(
        np.mean(
            [
                original4["outgoing_polarity_accuracy"],
                opposite4["outgoing_polarity_accuracy"],
            ]
        )
    )
    worst_fold = _outgoing_worst_fold(
        rows, candidate_id, ("original_seed", "opposite_seed"), 4
    )
    required_forms = [
        row["foreground_f1_mean"]
        for row in (original1, opposite1, original4, opposite4, original8, opposite8)
    ]
    gate = bool(
        complete
        and int(candidate["payload_bits"]) <= 8
        and min(required_forms) >= contract.motion_foreground_f1_minimum
        and min(
            original1["instruction_direction_fraction"],
            opposite1["instruction_direction_fraction"],
        )
        >= contract.motion_generation1_minimum
        and min(
            original4["instruction_direction_fraction"],
            opposite4["instruction_direction_fraction"],
        )
        >= contract.motion_generation4_minimum
        and min(
            original8["instruction_direction_fraction"],
            opposite8["instruction_direction_fraction"],
        )
        >= contract.motion_generation8_minimum
        and signed4 >= contract.motion_signed_generation4_minimum
        and signed8 >= contract.motion_signed_generation8_minimum
        and rescue_immediate >= contract.motion_rescue_immediate_minimum
        and rescue_rewrite >= contract.motion_rescue_rewrite_minimum
        and invariance4 >= contract.motion_invariance_generation4_minimum
        and null_maximum <= contract.metric_null_maximum
        and renewal_advantage >= contract.compact_control_advantage_minimum
        and outgoing4 >= contract.outgoing_polarity_generation4_minimum
        and worst_fold >= contract.outgoing_polarity_worst_fold_minimum
    )
    if profile_name == "smoke":
        gate = complete
    score = float(
        0.25 * min(required_forms)
        + 0.20
        * min(
            original8["instruction_direction_fraction"],
            opposite8["instruction_direction_fraction"],
        )
        + 0.15 * min(1.0, max(0.0, signed8) / 2.0)
        + 0.15 * rescue_rewrite
        + 0.10 * invariance4
        + 0.15 * outgoing4
    )
    return gate, {
        "candidate": _candidate_public(candidate),
        "recovery": recovery,
        "signed_original_opposite_separation_generation4": float(signed4),
        "signed_original_opposite_separation_generation8": float(signed8),
        "rescue_immediate_joint_minimum": float(rescue_immediate),
        "rescue_after_one_rewrite_joint_minimum": float(rescue_rewrite),
        "phase_translation_seam_joint_minimum_generation4": float(invariance4),
        "maximum_null_mover_detection_generation8": float(null_maximum),
        "active_renewal_joint_advantage_generation8": float(renewal_advantage),
        "outgoing_polarity_accuracy_generation4": outgoing4,
        "outgoing_polarity_accuracy_worst_fold_generation4": float(worst_fold),
        "selection_score": score,
        "stage_gate": gate,
    }


def _run_motion_validation(
    stage_root: Path,
    candidates: Sequence[dict[str, Any]],
    bank: dict[str, Any],
    profile_name: str,
    contract: PolarityClosureContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Callable[..., None],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "motion-validation"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    pairs = list(bank.get("pairs", []))
    rows: list[dict[str, Any]] = []
    registered = len(candidates) * len(pairs)
    completed = 0
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        for pair in pairs:
            path = checkpoints / f"{candidate_id}-{pair['pair_id']}.json"
            if resume and path.exists():
                row = _load_json(path)["row"]
            else:
                if time.time() >= deadline:
                    break
                conditions = {
                    f"{direction}:{condition}": _corrected_motion_lineage(
                        candidate,
                        pair,
                        direction,
                        condition,
                        generations=profile_name == "smoke" and 2 or 8,
                    )
                    for direction in ("forward", "opposite")
                    for condition in MOTION_CONDITIONS
                }
                row = {
                    "candidate_id": candidate_id,
                    "pair_id": pair["pair_id"],
                    "rule": pair["rule"],
                    "conditions": conditions,
                }
                ar._atomic_json(path, {"design_digest": design_digest, "row": row})
            rows.append(row)
            completed += 1
            status(
                "running",
                "validate-corrected-motion-lineages",
                completed=completed,
                total=registered,
                candidate_id=candidate_id,
            )
    complete = bool(completed == registered and bank.get("stage_gate"))
    summaries: dict[str, Any] = {}
    qualified: list[tuple[float, dict[str, Any]]] = []
    for candidate in candidates:
        candidate_complete = complete
        if profile_name == "smoke":
            # The smoke profile deliberately runs only two generations; its
            # scientific gate is never interpreted.
            candidate_complete = completed == registered
            summary = {
                "candidate": _candidate_public(candidate),
                "smoke_trajectory_count": len(
                    [row for row in rows if row["candidate_id"] == candidate["candidate_id"]]
                ),
                "selection_score": 0.0,
                "stage_gate": candidate_complete,
                "scientific_gate_evaluated": False,
            }
            gate = candidate_complete
        else:
            gate, summary = _motion_gate(
                rows, candidate, candidate_complete, profile_name, contract
            )
            summary["scientific_gate_evaluated"] = True
        summaries[str(candidate["candidate_id"])] = summary
        if gate:
            qualified.append((float(summary["selection_score"]), candidate))
    qualified.sort(key=lambda value: value[0], reverse=True)
    models = [row[1] for row in qualified]
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and models),
        "registered_trajectories": registered,
        "completed_trajectories": completed,
        "validation_pair_count": len(pairs),
        "selected_candidate_ids": [candidate["candidate_id"] for candidate in candidates],
        "qualified_candidate_ids": [candidate["candidate_id"] for candidate in models],
        "candidate_summaries": summaries,
        "absolute_command_semantics": True,
        "opposite_seed_repeated_toggle_separated": True,
        "frozen_parent_rescue_semantics": True,
        "head_isolation_registered": True,
        "visible_reset_every_boundary": True,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, models


def _run_motion_endurance(
    stage_root: Path,
    candidates: Sequence[dict[str, Any]],
    bank: dict[str, Any],
    profile_name: str,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Callable[..., None],
) -> dict[str, Any]:
    if not candidates:
        return _empty("no generation-eight motion qualifier")
    if profile_name == "smoke":
        return {
            "state": "complete",
            "stage_gate": True,
            "scientific_endurance_run": False,
            "skipped_reason": "smoke profile",
            "final_audit_trajectory_state": "untouched",
        }
    root = stage_root / "motion-endurance"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    pairs = list(bank.get("pairs", []))
    conditions = ("original_seed", "opposite_seed", "no_renewal", "ablation")
    rows: list[dict[str, Any]] = []
    registered = len(candidates) * len(pairs)
    for candidate in candidates:
        for pair in pairs:
            path = checkpoints / f"{candidate['candidate_id']}-{pair['pair_id']}.json"
            if resume and path.exists():
                row = _load_json(path)["row"]
            else:
                if time.time() >= deadline:
                    break
                row = {
                    "candidate_id": candidate["candidate_id"],
                    "pair_id": pair["pair_id"],
                    "rule": pair["rule"],
                    "conditions": {
                        f"{direction}:{condition}": _corrected_motion_lineage(
                            candidate,
                            pair,
                            direction,
                            condition,
                            generations=16,
                        )
                        for direction in ("forward", "opposite")
                        for condition in conditions
                    },
                }
                ar._atomic_json(path, {"design_digest": design_digest, "row": row})
            rows.append(row)
            status(
                "running",
                "run-conditional-motion-endurance",
                completed=len(rows),
                total=registered,
                candidate_id=candidate["candidate_id"],
            )
    complete = len(rows) == registered
    summaries: dict[str, Any] = {}
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        summaries[candidate_id] = {
            condition: {
                f"generation{generation}": _motion_summary(
                    rows, candidate_id, condition, generation
                )
                for generation in (12, 16)
            }
            for condition in conditions
        }
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "candidate_summaries": summaries,
        "generation8_gate_required_before_open": True,
        "generations": (12, 16),
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result


def _motion_launch_hex(bank: dict[str, Any]) -> set[str]:
    return {
        str(specification["initial_hex"])
        for pair in bank.get("pairs", [])
        for specification in (pair["forward"], pair["opposite"])
    }


def _capacity_balance_verified(
    selected: dict[str, int], available: dict[str, int]
) -> bool:
    """Verify max-min balance while allowing a rule's pool to be exhausted."""

    rules = sorted(available)
    for lower in rules:
        for higher in rules:
            if (
                int(selected.get(lower, 0)) + 1
                < int(selected.get(higher, 0))
                and int(selected.get(lower, 0)) < int(available[lower])
            ):
                return False
    return True


def _fresh_motion_bank(
    stage_root: Path,
    stage6o_root: Path,
    stage6n_root: Path,
    stage6m_root: Path,
    stage6l_root: Path,
    stage6k_root: Path,
    profile_name: str,
    profile: PolarityClosureProfile,
    contract: PolarityClosureContract,
    *,
    deadline: float,
    status: Callable[..., None],
) -> dict[str, Any]:
    path = stage_root / "MOTION_VALIDATION_BANK.json"
    if path.exists():
        return _load_json(path)
    stage6o_bank = _load_json(stage6o_root / "stage6o/MOTION_VALIDATION_BANK.json")
    if profile_name == "smoke":
        pairs = list(stage6o_bank.get("pairs", []))[: profile.motion_validation_pairs]
        result = {
            "state": "complete",
            "stage_gate": len(pairs) == profile.motion_validation_pairs,
            "pairs": pairs,
            "validation_pair_count": len(pairs),
            "role": "smoke-exposed-only",
            "scientific_holdout": False,
            "frozen_before_stage6p_selection": True,
            "final_audit_trajectory_state": "untouched",
        }
        ar._atomic_json(path, result)
        return result
    banks = [
        _load_json(stage6m_root / "stage6m/MOTION_BANK.json"),
        _load_json(stage6l_root / "stage6l/MOTION_BANK.json"),
        stage6o_bank,
    ]
    optional_stage6n_bank = stage6n_root / "stage6n/MOTION_VALIDATION_BANK.json"
    if optional_stage6n_bank.exists():
        banks.append(_load_json(optional_stage6n_bank))
    panel = _load_json(stage6k_root / "stage6k/MOVER_PANEL.json")
    excluded: set[str] = set()
    for bank in (*banks, panel):
        excluded.update(_motion_launch_hex(bank))
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
                "stage6l-", "stage6p-"
            )
            copied["source"] = "stage6p-fresh-deterministic-5x5-scan"
            pair = wc._discovered_pair(copied)
            if pair is None:
                continue
            launch_hex = _motion_launch_hex({"pairs": [pair]})
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
            "allocate-rule-balanced-stage6p-motion-bank",
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
    available_counts = {
        str(rule): len(by_rule[rule]) for rule in rules
    }
    capacity_balanced = _capacity_balance_verified(counts, available_counts)
    complete = bool(
        len(selected) == profile.motion_validation_pairs
        and len(per_rule) == len(wc.MOVER_RULES)
        and capacity_balanced
    )
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "pairs": selected,
        "rules": per_rule,
        "selected_per_rule": counts,
        "available_per_rule": available_counts,
        "validation_pair_count": len(selected),
        "scientific_holdout": True,
        "rule_balanced": True,
        "balance_definition": "max-min-round-robin-subject-to-rule-pool-capacity",
        "capacity_balance_verified": capacity_balanced,
        "zero_yield_rules_retained_in_ledger": [
            rule for rule, count in available_counts.items() if count == 0
        ],
        "capacity_exhausted_rules": [
            rule
            for rule, count in counts.items()
            if count == available_counts[rule]
            and count < max(counts.values(), default=0)
        ],
        "stage6k_through_stage6o_launch_states_excluded": True,
        "frozen_before_stage6p_selection": True,
        "allocation_digest": _digest([pair["pair_id"] for pair in selected]),
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(path, result)
    return result


def _orthonormal_rows(rows: np.ndarray, count: int) -> np.ndarray:
    values = np.asarray(rows, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("basis rows must be a matrix")
    q, _ = np.linalg.qr(values.T)
    result = q[:, : min(count, q.shape[1])].T
    if len(result) < count:
        raise ValueError("causal compact basis is rank deficient")
    return result[:count].astype(np.float32)


def _compact_decoder(
    kind: str,
    targets: np.ndarray,
    groups: np.ndarray,
    design: np.ndarray,
    train: np.ndarray,
    latent_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    selected_targets = np.asarray(targets[train], dtype=np.float32)
    target_mean = np.mean(selected_targets, axis=0).astype(np.float32)
    centered = selected_targets - target_mean
    _, _, pca_right = np.linalg.svd(centered, full_matrices=False)
    if kind == "paired-history-contrast-svd":
        selected_groups = groups[train]
        contrast = centered.copy()
        for group in sorted(set(selected_groups.tolist())):
            local = selected_groups == group
            contrast[local] -= np.mean(contrast[local], axis=0)
        _, _, right = np.linalg.svd(contrast, full_matrices=False)
        decoder = right[:latent_size]
    elif kind == "hybrid-pca8-contrast8":
        selected_groups = groups[train]
        contrast = centered.copy()
        for group in sorted(set(selected_groups.tolist())):
            local = selected_groups == group
            contrast[local] -= np.mean(contrast[local], axis=0)
        _, _, contrast_right = np.linalg.svd(contrast, full_matrices=False)
        joined = np.concatenate(
            (pca_right[: latent_size // 2], contrast_right[: latent_size // 2]),
            axis=0,
        )
        decoder = _orthonormal_rows(joined, latent_size)
    elif kind == "supervised-reduced-rank-regression":
        weights, bias = wc._ridge_fit(design, selected_targets, 0.30)
        predicted = design @ weights + bias
        _, _, right = np.linalg.svd(
            predicted - np.mean(predicted, axis=0), full_matrices=False
        )
        decoder = right[:latent_size]
    elif kind == "pca":
        decoder = pca_right[:latent_size]
    else:
        raise ValueError(f"unknown compact basis {kind!r}")
    decoder = _orthonormal_rows(decoder, latent_size)
    return decoder, target_mean


def _fit_compact_basis_arrays(
    features: np.ndarray,
    targets: np.ndarray,
    groups: np.ndarray,
    spec: dict[str, Any],
    train: np.ndarray,
    basis_kind: str,
) -> dict[str, Any]:
    mean = np.mean(features[train], axis=0, dtype=np.float64).astype(np.float32)
    scale = np.std(features[train], axis=0, dtype=np.float64).astype(np.float32)
    scale = np.where(scale > np.float32(1e-6), scale, 1.0).astype(np.float32)
    use_projection = features.shape[1] > 700
    projection = lm._projection(spec, features.shape[1]) if use_projection else None
    design = (features[train] - mean) / scale
    if projection is not None:
        design = design @ projection
    latent_size = int(spec["latent_size"])
    decoder, target_mean = _compact_decoder(
        basis_kind, targets, groups, design, train, latent_size
    )
    raw_codes = (targets[train] - target_mean) @ decoder.T
    latent_scale = np.percentile(np.abs(raw_codes), 95.0, axis=0).astype(np.float32)
    latent_scale = np.where(latent_scale > 1e-3, latent_scale, 1.0).astype(np.float32)
    codes = np.clip(raw_codes / latent_scale, -1.0, 1.0).astype(np.float32)
    weights, bias = wc._ridge_fit(design, codes, 0.30)
    prototype_count = min(4, max(2, len(codes) // 32), len(codes))
    prototypes, _ = lm._kmeans(
        codes,
        prototype_count,
        ar._hash_seed(
            "stage6p-compact-prototypes",
            basis_kind,
            spec["spec_id"],
            int(np.sum(train)),
        ),
    )
    model: dict[str, Any] = {
        "kind": "compact-attractor-ridge",
        "architecture": f"compact-{spec['attractor_kind']}",
        "basis_kind": basis_kind,
        "radius": int(spec["radius"]),
        "window": int(spec["window"]),
        "endpoint": int(spec["endpoint"]),
        "canonicalize": False,
        "input_mean": mean.tolist(),
        "input_scale": scale.tolist(),
        "latent_weights": weights.astype(np.float32).tolist(),
        "latent_bias": bias.astype(np.float32).tolist(),
        "latent_size": latent_size,
        "latent_decoder": decoder.tolist(),
        "latent_target_mean": target_mean.tolist(),
        "latent_scale": latent_scale.tolist(),
        "latent_prototypes": prototypes.tolist(),
        "attractor_kind": str(spec["attractor_kind"]),
        "attractor_retention": 0.65,
        "recurrent_gain": 0.55,
        "input_gain": 0.75,
        "prototype_strength": 0.35,
        "output_space": "compact-latent",
        "field_output_space": "q4-coefficients",
        "field_output_rank": 16,
        "model_frozen": True,
        "runtime_target_labels": False,
        "runtime_parent_field": False,
        "runtime_incoming_payload": False,
        "runtime_pair_identity": False,
        "runtime_generation_index": False,
    }
    if projection is not None:
        model["projection"] = projection.tolist()
    return model


def _fit_compact_basis_model(
    rows: Sequence[dict[str, Any]],
    spec: dict[str, Any],
    basis_kind: str,
    contract: PolarityClosureContract,
    *,
    retain_fold_models: bool = False,
) -> dict[str, Any]:
    example_spec = {
        "spec_id": spec["spec_id"],
        "mode": "local",
        "radius": int(spec["radius"]),
        "window": int(spec["window"]),
        "endpoint": int(spec["endpoint"]),
        "symmetry": "none",
    }
    features, targets, groups, endpoints = lm._examples(rows, example_spec)
    fold_count = min(contract.local_writer_fold_count, len(set(groups.tolist())))
    folds = wc._pair_blocked_folds(groups, fold_count)
    fold_rows: list[dict[str, Any]] = []
    fold_models: list[dict[str, Any]] = []
    for fold in range(fold_count):
        train = folds != fold
        test = folds == fold
        model = _fit_compact_basis_arrays(
            features, targets, groups, spec, train, basis_kind
        )
        predicted = cn._compact_predict(model, features[test])
        clean = cn._iterate_attractor(
            model,
            np.zeros_like(predicted),
            predicted,
            int(spec["writer_steps"]),
        )
        coefficients = cn._compact_decode_coefficients(model, clean)
        metrics = il._coefficient_metrics(coefficients, targets[test])
        damaged = predicted.copy()
        damaged[:, 0] = np.clip(
            damaged[:, 0] + np.float32(1.0 / 7.0), -1.0, 1.0
        )
        repaired = cn._iterate_attractor(model, damaged, predicted, 3)
        denominator = np.linalg.norm(damaged - predicted, axis=1)
        numerator = np.linalg.norm(repaired - predicted, axis=1)
        ratios = np.divide(
            numerator,
            denominator,
            out=np.zeros_like(numerator),
            where=denominator > 1e-8,
        )
        one_shot = il._coefficient_metrics(
            cn._compact_decode_coefficients(model, predicted), targets[test]
        )
        degradation = max(
            0.0,
            float(one_shot["history_specific_accuracy"])
            - float(metrics["history_specific_accuracy"]),
        )
        fold_rows.append(
            {
                "fold": fold,
                "training_pair_count": len(set(groups[train].tolist())),
                "test_pair_count": len(set(groups[test].tolist())),
                **metrics,
                "contraction_ratio_median": float(np.median(ratios)),
                "clean_degradation": degradation,
            }
        )
        if retain_fold_models:
            model["fold"] = fold
            model["model_id"] = (
                f"stage6p-{basis_kind}-{spec['spec_id']}-fold{fold}"
            )
            model["spec"] = dict(spec)
            model["model_digest"] = _digest(model)
            fold_models.append(model)
    full = np.ones(len(features), dtype=np.bool_)
    model = _fit_compact_basis_arrays(
        features, targets, groups, spec, full, basis_kind
    )
    model["model_id"] = f"stage6p-{basis_kind}-{spec['spec_id']}"
    model["spec"] = dict(spec)
    model["training_pair_count"] = len(set(groups.tolist()))
    model["training_example_count"] = len(features)
    model["model_digest"] = _digest(model)
    history = [float(row["history_specific_accuracy"]) for row in fold_rows]
    form = [float(row["form_bit_accuracy"]) for row in fold_rows]
    contraction = [float(row["contraction_ratio_median"]) for row in fold_rows]
    degradation = [float(row["clean_degradation"]) for row in fold_rows]
    gate = bool(
        history
        and float(np.mean(history)) >= contract.history_accuracy_minimum
        and float(np.min(history)) >= contract.history_fold_minimum
        and float(np.median(contraction)) <= contract.contraction_ratio_maximum
        and float(np.max(degradation)) <= contract.clean_degradation_maximum
    )
    score = (
        float(
            0.50 * np.mean(history)
            + 0.20 * np.min(history)
            + 0.15 * np.mean(form)
            + 0.15 * (1.0 - min(1.0, np.median(contraction)))
        )
        if history
        else 0.0
    )
    return {
        "state": "complete",
        "stage_gate": gate,
        "basis_kind": basis_kind,
        "spec": dict(spec),
        "selection_score": score,
        "cross_validation": {
            "history_specific_accuracy_mean": float(np.mean(history)) if history else 0.0,
            "history_specific_accuracy_minimum": float(np.min(history)) if history else 0.0,
            "form_bit_accuracy_mean": float(np.mean(form)) if form else 0.0,
            "contraction_ratio_median": float(np.median(contraction)) if contraction else 1.0,
            "clean_degradation_maximum": float(np.max(degradation)) if degradation else 1.0,
            "folds": fold_rows,
        },
        "model": model,
        "fold_models": fold_models,
        "endpoint_digest": _digest(sorted(set(endpoints))),
    }


def _load_frozen_compact_model(stage6n_root: Path, dimension: int) -> dict[str, Any]:
    path = stage6n_root / f"stage6n/compact-oracle/rank-{dimension:02d}.json"
    payload = _load_json(path)
    if payload.get("design_digest") != co.PARENT_STAGE6N_DIGEST:
        raise ValueError(f"Stage-6N compact rank {dimension} digest mismatch")
    model = copy.deepcopy(payload["fitted"]["model"])
    model["parent_model_id"] = model["model_id"]
    model["model_id"] = f"stage6p-frozen-pca-r{dimension}"
    model["basis_kind"] = "frozen-pca"
    model["model_digest"] = _digest(model)
    return model


def _run_compact_basis_fit(
    stage_root: Path,
    stage6n_root: Path,
    base_rows: Sequence[dict[str, Any]],
    profile_name: str,
    contract: PolarityClosureContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Callable[..., None],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "compact-basis-fit"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    basis_kinds = (
        "paired-history-contrast-svd",
        "hybrid-pca8-contrast8",
        "supervised-reduced-rank-regression",
    )
    if profile_name == "smoke":
        basis_kinds = ("paired-history-contrast-svd",)
    fitted: list[dict[str, Any]] = []
    frozen16 = _load_frozen_compact_model(stage6n_root, 16)
    fitted.append(
        {
            "state": "complete",
            "stage_gate": True,
            "basis_kind": "frozen-pca",
            "spec": dict(frozen16["spec"]),
            "selection_score": float(
                _load_json(stage6n_root / "stage6n/compact-oracle/rank-16.json")[
                    "fitted"
                ].get("selection_score", 0.0)
            ),
            "cross_validation": _load_json(
                stage6n_root / "stage6n/compact-oracle/rank-16.json"
            )["fitted"]["cross_validation"],
            "model": frozen16,
            "fold_models": [],
            "frozen_parent_model": True,
        }
    )
    for index, basis_kind in enumerate(basis_kinds, start=1):
        path = checkpoints / f"{basis_kind}.json"
        if resume and path.exists():
            value = _load_json(path)["result"]
        else:
            if time.time() >= deadline:
                break
            spec = cn._compact_spec(16, "leaky", 8, 16)
            spec["spec_id"] = f"stage6p-{basis_kind}-r16-e16"
            value = _fit_compact_basis_model(
                base_rows, spec, basis_kind, contract
            )
            saved = copy.deepcopy(value)
            saved.pop("fold_models", None)
            ar._atomic_json(path, {"design_digest": design_digest, "result": saved})
        fitted.append(value)
        status(
            "running",
            "fit-causal-compact-bases",
            completed=index,
            total=len(basis_kinds),
            basis_kind=basis_kind,
        )
    expected = 1 + len(basis_kinds)
    complete = len(fitted) == expected
    public = {
        value["basis_kind"]: {
            key: copy.deepcopy(item)
            for key, item in value.items()
            if key not in ("model", "fold_models")
        }
        | {"model_id": value["model"]["model_id"], "model_digest": value["model"]["model_digest"]}
        for value in fitted
    }
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "registered_rank16_basis_count": expected,
        "completed_rank16_basis_count": len(fitted),
        "candidate_summaries": public,
        "rank4_negative_control_registered": True,
        "six_pair_blocked_folds": profile_name == "reference",
        "runtime_target_access": False,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, fitted


def _run_compact_causal_screen(
    stage_root: Path,
    stage6n_root: Path,
    source: dict[str, Any],
    fitted: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile_name: str,
    profile: PolarityClosureProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: PolarityClosureContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Callable[..., None],
) -> tuple[dict[str, Any], list[tuple[str, dict[str, Any]]]]:
    rank4 = _load_frozen_compact_model(stage6n_root, 4)
    models: list[tuple[str, dict[str, Any], bool]] = [
        ("frozen-pca-r4-negative-control", rank4, True)
    ] + [
        (str(value["basis_kind"]), value["model"], False) for value in fitted
    ]
    candidates = [
        cn._compact_candidate(
            source,
            model,
            suffix=f"stage6p-causal-basis-{basis_kind}",
            oracle=True,
        )
        for basis_kind, model, _ in models
    ]
    compact_pairs = list(
        pairs[profile.compact_start : profile.compact_start + profile.compact_pairs]
    )
    conditions = (
        "inherited_field_zero",
        "inherited_field_shuffle",
        "inherited_field_coefficient_shuffle",
        "inherited_field_read_disabled",
        "inherited_field_write_disabled",
        "inherited_field_no_renewal",
        "inherited_field_one_bin_damage",
        "inherited_field_copy_noise_5",
        "inherited_field_same_rescue",
        "inherited_field_opposite_rescue",
    )
    items = ar._make_items(
        compact_pairs,
        candidates,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="stage6p-compact-causal-basis",
        replicates=profile.trace_replicates,
        generations=8,
        conditions=("intact", *conditions),
        analysis_kind="stage6p-nonpromotable-exact-compact-carrier",
    )
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        "compact-causal-basis-trajectories",
        items,
        candidates,
        pb._phenotype_pair_task,
        writer_contract,
        contract,
        frozen["stage4"]["reference"],
        design_digest,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    summaries: dict[str, Any] = {}
    passing: list[tuple[float, str, dict[str, Any]]] = []
    for (basis_kind, model, negative_control), candidate in zip(
        models, candidates, strict=True
    ):
        candidate_id = str(candidate["candidate_id"])
        intact = cn._metric_mean(
            rows, candidate_id, "intact", "post_washout_match_mean", 8
        )
        control_values = {
            condition: cn._metric_mean(
                rows,
                candidate_id,
                condition,
                "post_washout_match_mean",
                8,
            )
            for condition in (
                "inherited_field_zero",
                "inherited_field_shuffle",
                "inherited_field_coefficient_shuffle",
                "inherited_field_read_disabled",
                "inherited_field_no_renewal",
            )
        }
        matching = cn._metric_mean(
            rows,
            candidate_id,
            "inherited_field_same_rescue",
            "post_washout_match_mean",
            6,
        )
        opposite = cn._metric_mean(
            rows,
            candidate_id,
            "inherited_field_opposite_rescue",
            "post_washout_match_mean",
            6,
        )
        minimum_advantage = min(
            (intact - value for value in control_values.values()), default=-1.0
        )
        gate = bool(
            complete
            and not negative_control
            and intact >= contract.compact_recovery_minimum
            and minimum_advantage >= contract.compact_control_advantage_minimum
            and matching - opposite >= contract.compact_control_advantage_minimum
        )
        if profile_name == "smoke" and not negative_control:
            gate = complete
        score = float(
            0.60 * intact
            + 0.25 * max(-1.0, minimum_advantage)
            + 0.15 * (matching - opposite)
        )
        if gate:
            passing.append((score, basis_kind, model))
        summaries[basis_kind] = {
            "candidate_id": candidate_id,
            "model_id": model["model_id"],
            "model_digest": model["model_digest"],
            "basis_kind": basis_kind,
            "latent_size": int(model["latent_size"]),
            "negative_control": negative_control,
            "intact_generation8_post_washout": intact,
            "intact_pair_block_bootstrap_95": co._pair_block_bootstrap_interval(
                rows,
                candidate_id,
                "intact",
                8,
                profile.bootstrap_resamples,
                ar._hash_seed(contract.namespace, "basis-bootstrap", basis_kind),
            ),
            "controls_generation8": control_values,
            "minimum_intact_control_advantage": minimum_advantage,
            "matching_rescue_generation6": matching,
            "opposite_rescue_generation6": opposite,
            "matching_minus_opposite_rescue": matching - opposite,
            "selection_score": score,
            "stage_gate": gate,
        }
    passing.sort(key=lambda value: (value[0], value[1]), reverse=True)
    selected = [(row[1], row[2]) for row in passing[:2]]
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and selected),
        "candidate_summaries": summaries,
        "qualified_basis_kinds": [row[0] for row in selected],
        "compact_pair_ids": [pair["pair_id"] for pair in compact_pairs],
        "compact_pair_ids_sha256": _digest(
            [pair["pair_id"] for pair in compact_pairs]
        ),
        "compact_pair_slice": [
            profile.compact_start,
            profile.compact_start + profile.compact_pairs,
        ],
        "fit_exposed_slice_disclosed": True,
        "claim": "causal-reliability-not-model-generality",
        "threshold_lowered": False,
        "oracle_target_access": True,
        "oracle_promotable": False,
        "registered_trajectories": len(items),
        "completed_trajectories": len(rows),
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(stage_root / "compact-causal-screen/RESULTS.json", result)
    return result, selected


def _basis_fit_name(basis_kind: str) -> str:
    return "pca" if basis_kind == "frozen-pca" else basis_kind


def _basis_attractor_specs(
    selected: Sequence[tuple[str, dict[str, Any]]],
    profile: PolarityClosureProfile,
) -> list[dict[str, Any]]:
    causal = profile.causal_profile()
    specs: list[dict[str, Any]] = []
    for basis_kind, _ in selected:
        for attractor_kind in causal.attractor_kinds:
            for support in causal.support_lengths:
                for endpoint in causal.writer_endpoints:
                    spec = cn._compact_spec(16, attractor_kind, support, endpoint)
                    spec["basis_kind"] = basis_kind
                    spec["spec_id"] = (
                        f"stage6p-{basis_kind}-r16-{attractor_kind}-"
                        f"s{support}-e{endpoint}"
                    )
                    specs.append(spec)
    if len(specs) > 24:
        raise AssertionError("Stage-6P basis attractor grid exceeds 24 candidates")
    return specs


def _run_basis_attractor_fit(
    stage_root: Path,
    base_rows: Sequence[dict[str, Any]],
    selected: Sequence[tuple[str, dict[str, Any]]],
    profile_name: str,
    profile: PolarityClosureProfile,
    contract: PolarityClosureContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Callable[..., None],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not selected:
        return _empty("no causal compact basis qualifier"), []
    root = stage_root / "compact-basis-attractor-fit"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    specs = _basis_attractor_specs(selected, profile)
    fitted: dict[str, Any] = {}
    for index, spec in enumerate(specs, start=1):
        path = checkpoints / f"{spec['spec_id']}.json"
        if resume and path.exists():
            value = _load_json(path)["result"]
        else:
            if time.time() >= deadline:
                break
            value = _fit_compact_basis_model(
                base_rows,
                spec,
                _basis_fit_name(str(spec["basis_kind"])),
                contract,
            )
            saved = copy.deepcopy(value)
            saved.pop("fold_models", None)
            ar._atomic_json(path, {"design_digest": design_digest, "result": saved})
        fitted[str(spec["spec_id"])] = value
        status(
            "running",
            "fit-causal-basis-attractor-grid",
            completed=index,
            total=len(specs),
            latest_checkpoint=spec["spec_id"],
        )
    complete = len(fitted) == len(specs)
    eligible = [
        value
        for value in fitted.values()
        if value.get("stage_gate") or profile_name == "smoke"
    ]
    ranked = sorted(
        eligible,
        key=lambda value: (
            -float(value["selection_score"]),
            str(value["spec"]["spec_id"]),
        ),
    )
    selected_specs = [
        dict(value["spec"])
        for value in ranked[: profile.maximum_frozen_writers]
    ]
    public = {
        key: {
            subkey: copy.deepcopy(subvalue)
            for subkey, subvalue in value.items()
            if subkey not in ("model", "fold_models")
        }
        | {"model_digest": value["model"]["model_digest"]}
        for key, value in fitted.items()
    }
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and selected_specs),
        "registered_candidates": len(specs),
        "completed_candidates": len(fitted),
        "selected_spec_ids": [spec["spec_id"] for spec in selected_specs],
        "candidate_summaries": public,
        "basis_family_preserved": True,
        "runtime_inputs": "local-visible-spacetime-and-zero-born-state-only",
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, selected_specs


def _run_basis_closed_loop(
    stage_root: Path,
    source: dict[str, Any],
    base_rows: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    specs: Sequence[dict[str, Any]],
    profile_name: str,
    profile: PolarityClosureProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: PolarityClosureContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Callable[..., None],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not specs:
        return _empty("no compact basis survived contraction"), []
    root = stage_root / "compact-basis-closed-loop"
    root.mkdir(parents=True, exist_ok=True)
    datasets = {str(spec["spec_id"]): list(base_rows) for spec in specs}
    fold_count = min(contract.local_writer_fold_count, len(pairs))
    fold_map = lm._pair_fold_map(pairs, fold_count)
    rounds: list[dict[str, Any]] = []
    first_history: dict[str, float] = {}
    latest: dict[str, dict[str, Any]] = {}
    for round_index in range(profile.rollout_rounds + 1):
        round_root = root / f"round-{round_index:02d}"
        models_path = round_root / "MODELS.json"
        if resume and models_path.exists():
            fitted = _load_json(models_path)["fitted"]
        else:
            fitted = {
                str(spec["spec_id"]): _fit_compact_basis_model(
                    datasets[str(spec["spec_id"])],
                    spec,
                    _basis_fit_name(str(spec["basis_kind"])),
                    contract,
                    retain_fold_models=True,
                )
                for spec in specs
            }
            ar._atomic_json(
                models_path,
                {
                    "design_digest": design_digest,
                    "round": round_index,
                    "fitted": fitted,
                },
            )
        latest = fitted
        if round_index == 0:
            first_history = {
                key: float(
                    value["cross_validation"]["history_specific_accuracy_mean"]
                )
                for key, value in fitted.items()
            }
        summaries = {
            key: {
                "stage_gate": bool(value["stage_gate"]),
                "selection_score": value["selection_score"],
                "cross_validation": value["cross_validation"],
                "model_digest": value["model"]["model_digest"],
                "basis_kind": value["basis_kind"],
            }
            for key, value in fitted.items()
        }
        round_row: dict[str, Any] = {
            "round": round_index,
            "dataset_rows": {key: len(value) for key, value in datasets.items()},
            "writer_summaries": summaries,
            "out_of_fold_rollout": True,
            "teacher_targets_remain_original": True,
            "basis_family_preserved": True,
        }
        if round_index == profile.rollout_rounds or time.time() >= deadline:
            rounds.append(round_row)
            break
        assignments: list[
            tuple[dict[str, Any], Sequence[dict[str, Any]]]
        ] = []
        candidate_to_spec: dict[str, str] = {}
        for spec_id, fitted_row in fitted.items():
            for model in fitted_row["fold_models"]:
                fold = int(model["fold"])
                fold_pairs = [
                    pair
                    for pair in pairs
                    if fold_map[str(pair["pair_id"])] == fold
                ]
                candidate = cn._compact_candidate(
                    source,
                    model,
                    suffix=f"stage6p-rollout-r{round_index + 1}-oof",
                )
                assignments.append((candidate, fold_pairs))
                candidate_to_spec[str(candidate["candidate_id"])] = spec_id
        trace_rows, trace_complete, total = il._collect_traces(
            stage_root,
            f"stage6p-compact-rollout-round-{round_index + 1}-traces",
            assignments,
            templates,
            frozen,
            writer_contract,
            contract,
            design_digest,
            replicates=profile.trace_replicates,
            workers=workers,
            resume=resume,
            deadline=deadline,
            status=status,
        )
        grouped: dict[str, list[dict[str, Any]]] = {
            str(spec["spec_id"]): [] for spec in specs
        }
        for row in trace_rows:
            grouped[candidate_to_spec[str(row["candidate_id"])]].append(row)
        for spec_id in grouped:
            ordered = sorted(
                grouped[spec_id],
                key=lambda row: (
                    str(row.get("pair_id")),
                    str(row.get("checkpoint")),
                ),
            )[: len(base_rows)]
            datasets[spec_id] = [*base_rows, *ordered]
        round_row.update(
            {
                "rollout_complete": trace_complete,
                "completed_rollouts": len(trace_rows),
                "registered_rollouts": total,
                "next_round_dataset_rows": {
                    key: len(value) for key, value in datasets.items()
                },
                "clean_teacher_fraction_minimum": 0.5,
            }
        )
        rounds.append(round_row)
        status(
            "running",
            "compact-causal-basis-closed-loop",
            completed=round_index + 1,
            total=profile.rollout_rounds,
            rollout_trajectories=len(trace_rows),
        )
        if not trace_complete:
            break
    qualified: list[dict[str, Any]] = []
    final_summaries: dict[str, Any] = {}
    for spec_id, value in latest.items():
        history = float(
            value["cross_validation"]["history_specific_accuracy_mean"]
        )
        degradation = max(0.0, first_history.get(spec_id, history) - history)
        gate = bool(
            value.get("stage_gate", False)
            and degradation <= contract.rollout_degradation_maximum
        )
        if profile_name == "smoke":
            gate = True
        final_summaries[spec_id] = {
            "basis_kind": value["basis_kind"],
            "round_zero_history_accuracy": first_history.get(spec_id),
            "final_history_accuracy": history,
            "rollout_degradation": degradation,
            "stage_gate": gate,
        }
        if gate:
            qualified.append(value["model"])
    qualified = sorted(
        qualified,
        key=lambda model: (
            -float(latest[str(model["spec"]["spec_id"])]["selection_score"]),
            model["model_id"],
        ),
    )[: profile.maximum_frozen_writers]
    complete = len(rounds) == profile.rollout_rounds + 1
    if not complete:
        qualified = []
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and qualified),
        "registered_rounds": profile.rollout_rounds,
        "completed_rounds": max(0, len(rounds) - 1),
        "rounds": rounds,
        "final_candidate_summaries": final_summaries,
        "selected_model_ids": [model["model_id"] for model in qualified],
        "selected_model_digests": [model["model_digest"] for model in qualified],
        "out_of_fold_rollout_generation": True,
        "basis_family_preserved": True,
        "clean_teacher_fraction_minimum": 0.5,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, qualified


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6o_root: Path,
    stage6n_root: Path,
    stage6m_root: Path,
    stage6l_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[
    PolarityClosureContract,
    PolarityClosureProfile,
    dict[str, Any],
    str,
    dict[str, Any],
]:
    contract = PolarityClosureContract()
    profile = PROFILES[profile_name]
    integrity = _parent_integrity(
        stage6o_root, stage6n_root, stage6m_root, stage6l_root
    )
    design = {
        "experiment": "ca_motif_polarity_closure_stage_6p",
        "prospective_followup_to": PARENT_STAGE6O_DIGEST,
        "stage6o_verdict_immutable": True,
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(profile),
        "stage6o_root": str(stage6o_root.resolve()),
        "stage6n_root": str(stage6n_root.resolve()),
        "stage6m_root": str(stage6m_root.resolve()),
        "stage6l_root": str(stage6l_root.resolve()),
        "stage6o_required_hashes": integrity["stage6o_required_hashes"],
        "registered_phases": PHASES,
        "motion_track": {
            "fresh_rule_balanced_pairs": profile.motion_validation_pairs,
            "corrected_seed_semantics": "absolute-once-then-learned-renewal",
            "rescue_semantics": "frozen-parental-code",
            "transition_graph": "8x8-by-rule-shape-phase-noise",
            "maximum_candidates": 12,
            "maximum_advanced": 2,
            "payload_maximum_bits": 8,
        },
        "compact_track": {
            "pair_slice": [
                profile.compact_start,
                profile.compact_start + profile.compact_pairs,
            ],
            "rank4_pca_negative_control": True,
            "rank16_basis_families": (
                "frozen-pca",
                "paired-history-contrast-svd",
                "hybrid-pca8-contrast8",
                "supervised-reduced-rank-regression",
            ),
            "q_bits": 4,
            "xor_shares": 4,
            "threshold_lowered": False,
            "claim": "causal-reliability-not-model-generality",
        },
        "cohort_route": {
            "motion_development": "40 already-exposed Stage-6M mover pairs",
            "motion_validation": "24 fresh Stage-6P rule-balanced mover pairs",
            "compact_development": "already-exposed pairs 24:40",
            "compact_validation": "16 sealed procedural pairs; conditional",
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
            "motif_polarity_closure.py": ar._sha256(Path(__file__)),
            "motif_counterfactual_carrier.py": ar._sha256(Path(co.__file__)),
            "motif_causal_attractor.py": ar._sha256(Path(cn.__file__)),
            "motif_latent_regeneration.py": ar._sha256(Path(lm.__file__)),
            "motif_phenotype_bridge.py": ar._sha256(Path(pb.__file__)),
        },
    }
    design_digest = _digest(design)
    design["design_digest"] = design_digest
    design_path = output / "DESIGN.json"
    if resume and design_path.exists():
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6P resume design changed")
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
            "stage6o_result_reinterpreted": False,
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
            "experiment": "ca_motif_polarity_closure_stage_6p",
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
            rate = payload["elapsed_seconds"] / int(extra["completed"])
            payload["eta_seconds"] = max(
                0.0,
                rate * (int(extra["total"]) - int(extra["completed"])),
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
        "experiment": "ca_motif_polarity_closure_stage_6p",
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
    motion_fit: dict[str, Any],
    transition: dict[str, Any],
    motion: dict[str, Any],
    endurance: dict[str, Any],
    basis_fit: dict[str, Any],
    compact: dict[str, Any],
    attractor: dict[str, Any],
    contraction: dict[str, Any],
    closed_loop: dict[str, Any],
    narrow: dict[str, Any],
) -> dict[str, Any]:
    motion_gate = bool(motion.get("stage_gate", False))
    narrow_gate = bool(narrow.get("stage_gate", False))
    compact_gate = bool(compact.get("stage_gate", False))
    if profile_name == "smoke":
        verdict = "SMOKE_PATH_VALIDATED"
        scientific_claim = False
    elif motion_gate and narrow_gate:
        verdict = "POLARITY_CLOSED_MOTION_AND_CAUSAL_COMPACT_PH"
        scientific_claim = True
    elif motion_gate:
        verdict = "POLARITY_CLOSED_ABSTRACT_MOTION_PH"
        scientific_claim = True
    elif narrow_gate:
        verdict = "CAUSAL_COMPACT_BASIS_PH_ONLY"
        scientific_claim = True
    elif compact_gate:
        verdict = "CAUSAL_COMPACT_BASIS_CONTROL_ONLY"
        scientific_claim = True
    else:
        verdict = "NO_POLARITY_OR_COMPACT_CLOSURE"
        scientific_claim = True
    result = {
        "experiment": "ca_motif_polarity_closure_stage_6p",
        "design_digest": design_digest,
        "profile_name": profile_name,
        "state": "complete",
        "stage_gate": bool(motion_gate or narrow_gate),
        "verdict": verdict,
        "scientific_claim": scientific_claim,
        "motion_candidate_fit_gate": bool(motion_fit.get("stage_gate", False)),
        "motion_transition_audit_gate": bool(transition.get("stage_gate", False)),
        "polarity_closed_motion_ph_gate": motion_gate,
        "motion_endurance_completed": bool(endurance.get("stage_gate", False)),
        "compact_basis_fit_gate": bool(basis_fit.get("stage_gate", False)),
        "compact_causal_basis_gate": compact_gate,
        "compact_attractor_fit_gate": bool(attractor.get("stage_gate", False)),
        "compact_contraction_gate": bool(contraction.get("stage_gate", False)),
        "compact_closed_loop_gate": bool(closed_loop.get("stage_gate", False)),
        "causal_compact_basis_ph_gate": narrow_gate,
        "qualified_motion_candidate_ids": motion.get(
            "qualified_candidate_ids", []
        ),
        "qualified_compact_basis_kinds": compact.get(
            "qualified_basis_kinds", []
        ),
        "qualified_compact_candidate_ids": narrow.get(
            "qualified_candidate_ids", []
        ),
        "stage6o_verdict_reinterpreted": False,
        "claim_boundary": (
            "Engineered synthetic cellular automata only. No result implies "
            "biology, human memory, consciousness, or agency."
        ),
        "original_final_reserve_opened": False,
        "final_audit_pair_count": 62,
        "final_audit_trajectory_state": "untouched",
        "phase_results": {
            "motion_fit": motion_fit,
            "motion_transition_audit": transition,
            "motion_validation": motion,
            "motion_endurance": endurance,
            "compact_basis_fit": basis_fit,
            "compact_causal_screen": compact,
            "compact_attractor_fit": attractor,
            "compact_contraction": contraction,
            "compact_closed_loop": closed_loop,
            "compact_validation": narrow,
        },
    }
    ar._atomic_json(output / "RESULTS.json", result)
    ar._atomic_json(
        output / "STAGE_DECISION.json",
        {
            "experiment": result["experiment"],
            "design_digest": design_digest,
            "state": "complete",
            "stage_gate": result["stage_gate"],
            "verdict": verdict,
            "next_step": (
                "independently replicate the qualifying carrier in new CA rules"
                if result["stage_gate"]
                else "prepare a code-free question packet from the first failed interface"
            ),
            "final_audit_trajectory_state": "untouched",
        },
    )
    report = (
        "# Stage 6P polarity closure and causal compact bases\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"Corrected learned motion renewal: `{motion_gate}`; causal compact "
        f"basis screen: `{compact_gate}`; sealed compact PH: `{narrow_gate}`. "
        "Stage 6O remains immutable and the protected 62-pair reserve was "
        "neither loaded nor simulated.\n"
    )
    lay = (
        "# Lay summary\n\n"
        "This round asks whether a direction note should be reversed once and "
        "then recopied by each daughter, rather than reversed again and again. "
        "It also asks whether a small memory should preserve the differences "
        "that cause history-specific recovery instead of merely preserving the "
        "most common variation.\n\n"
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
        "\n\n## Stage 6P: polarity closure and causal compact bases\n\n"
        f"Stage 6P design `{result['design_digest']}` completed with verdict "
        f"**{result['verdict']}**. It prospectively separated an absolute "
        "opposite seed from repeated toggling, used frozen parental rescue "
        "codes, mapped eight-orientation transitions, and compared PCA with "
        "paired-contrast, hybrid, and supervised compact bases. Stage 6O "
        "remained immutable and the protected 62-pair reserve remained "
        "untouched.\n"
    )
    existing = (
        DISCOVERY_LOG.read_text(encoding="utf-8")
        if DISCOVERY_LOG.exists()
        else "# Discovery log\n"
    )
    marker = f"Stage 6P design `{result['design_digest']}`"
    if marker not in existing:
        ar._atomic_text(DISCOVERY_LOG, existing.rstrip() + entry)


def run_motif_polarity_closure(
    output: Path,
    *,
    stage6o_root: Path = DEFAULT_STAGE6O_ROOT,
    stage6n_root: Path = DEFAULT_STAGE6N_ROOT,
    stage6m_root: Path = DEFAULT_STAGE6M_ROOT,
    stage6l_root: Path = DEFAULT_STAGE6L_ROOT,
    stage6k_root: Path = il.DEFAULT_STAGE6K_ROOT,
    stage6j_root: Path = il.DEFAULT_STAGE6J_ROOT,
    stage6i_root: Path = il.DEFAULT_STAGE6I_ROOT,
    stage6h_root: Path = il.DEFAULT_STAGE6H_ROOT,
    stage6d_root: Path = pb.DEFAULT_STAGE6D_ROOT,
    stage6c_root: Path = ar.DEFAULT_STAGE6C_ROOT,
    stage6br_root: Path = ar.DEFAULT_STAGE6BR_ROOT,
    stage5r_root: Path = ar.DEFAULT_STAGE5R_ROOT,
    stage5_root: Path = ar.DEFAULT_STAGE5_ROOT,
    stage4_root: Path = ar.DEFAULT_STAGE4_ROOT,
    stage3r_root: Path = ar.DEFAULT_STAGE3R_ROOT,
    stage3_root: Path = ar.DEFAULT_STAGE3_ROOT,
    stage2_root: Path = ar.DEFAULT_STAGE2_ROOT,
    stage1_root: Path = ar.DEFAULT_STAGE1_ROOT,
    profile_name: str = "reference",
    workers: int = 4,
    max_hours: float = 8.0,
    resume: bool = False,
) -> dict[str, Any]:
    """Run Stage 6P without any path to the protected final reserve."""

    ar.require_pinned_numpy()
    if profile_name not in PROFILES:
        raise ValueError(f"unknown Stage-6P profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6P workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6P max-hours must be in (0, 8]")
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    stage6o_root = stage6o_root.resolve()
    stage6n_root = stage6n_root.resolve()
    stage6m_root = stage6m_root.resolve()
    stage6l_root = stage6l_root.resolve()
    stage6k_root = stage6k_root.resolve()
    _parent_integrity(stage6o_root, stage6n_root, stage6m_root, stage6l_root)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ar._atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
    stage6j_root = stage6j_root.resolve()
    stage6i_root = stage6i_root.resolve()
    stage6h_root = stage6h_root.resolve()
    stage6br_root = stage6br_root.resolve()
    roots = {
        "stage6d_root": stage6d_root.resolve(),
        "stage6c_root": stage6c_root.resolve(),
        "stage6br_root": stage6br_root,
        "stage5r_root": stage5r_root.resolve(),
        "stage5_root": stage5_root.resolve(),
        "stage4_root": stage4_root.resolve(),
        "stage3r_root": stage3r_root.resolve(),
        "stage3_root": stage3_root.resolve(),
        "stage2_root": stage2_root.resolve(),
        "stage1_root": stage1_root.resolve(),
    }
    active = ["prepare"]
    status: Callable[..., None] | None = None
    try:
        contract, profile, campaign, design_digest, integrity = _prepare_campaign(
            output,
            profile_name,
            stage6o_root,
            stage6n_root,
            stage6m_root,
            stage6l_root,
            max_hours,
            resume=resume,
        )
        status = _status_writer(output, profile_name, campaign, active, workers)
        status("running", "frozen-stage6o-parent-and-reserves-verified")
        active[0] = "integrity"
        _write_phase(
            output,
            "integrity",
            design_digest,
            integrity | {"next_phase": "allocation"},
            "# Stage 6P integrity\n\nThe completed Stage 6O artifacts and every inherited reserve boundary were hash-verified.",
            "# Lay summary\n\nThe earlier result stays fixed; this is a new experiment with new exam questions.",
        )

        stage_root = output / "stage6p"
        (
            frozen,
            cohorts,
            templates,
            writer_contract,
            base_rows,
            source,
            development_pairs,
            procedural_pairs,
        ) = co._reconstruct_context(
            stage_root,
            profile_name,
            profile.stage6o_profile(),
            design_digest,
            integrity,
            stage6l_root,
            stage6k_root,
            stage6j_root,
            stage6i_root,
            stage6h_root,
            stage6br_root,
            roots,
        )
        active[0] = "allocation"
        assert status is not None
        motion_bank = _fresh_motion_bank(
            stage_root,
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
        compact_pairs = development_pairs[
            profile.compact_start : profile.compact_start + profile.compact_pairs
        ]
        allocation = {
            "state": (
                "complete" if motion_bank.get("stage_gate") else motion_bank.get("state")
            ),
            "stage_gate": bool(
                motion_bank.get("stage_gate")
                and len(compact_pairs) == profile.compact_pairs
            ),
            "motion_validation_pair_count": motion_bank.get(
                "validation_pair_count", 0
            ),
            "motion_validation_allocation_digest": motion_bank.get(
                "allocation_digest"
            ),
            "motion_validation_rule_balanced": motion_bank.get(
                "rule_balanced", False
            ),
            "motion_validation_frozen_before_selection": True,
            "compact_pair_count": len(compact_pairs),
            "compact_pair_ids_sha256": _digest(
                [pair["pair_id"] for pair in compact_pairs]
            ),
            "compact_slice_frozen_before_basis_fit": True,
            "compact_slice_fit_exposed": True,
            "procedural_trajectories_simulated": False,
            "final_audit_trajectory_state": "untouched",
            "next_phase": "motion-fit",
        }
        _write_phase(
            output,
            "allocation",
            design_digest,
            allocation,
            "# Stage 6P allocation\n\nThe fresh rule-balanced mover bank and compact causal-reliability slice were frozen before candidate fitting or selection.",
            "# Lay summary\n\nThe test cases were sealed before choosing which repaired memory would answer them.",
        )

        active[0] = "motion-fit"
        motion_source = _load_json(stage6m_root / "stage6m/MOTION_BANK.json")
        motion_development = list(motion_source.get("pairs", []))[
            : profile.motion_development_pairs
        ]
        motion_fit_path = stage_root / "motion-fit/MODELS.json"
        if resume and motion_fit_path.exists():
            fit_payload = _load_json(motion_fit_path)
            motion_candidates = fit_payload["candidates"]
            selected_ids = set(fit_payload["result"]["selected_candidate_ids"])
            selected_motion = [
                candidate
                for candidate in motion_candidates
                if candidate["candidate_id"] in selected_ids
            ]
            motion_fit = fit_payload["result"]
        else:
            motion_candidates, fit_metadata = _motion_candidate_ladder(
                motion_development, stage6n_root, profile_name
            )
            motion_fit, selected_motion = _screen_motion_candidates(
                motion_candidates, motion_development, profile_name
            )
            motion_fit["fit_metadata"] = fit_metadata
            persisted_candidates = [
                {
                    key: value
                    for key, value in candidate.items()
                    if key not in ("fold_models", "fold_calibrations")
                }
                for candidate in motion_candidates
            ]
            selected_ids = set(motion_fit["selected_candidate_ids"])
            selected_motion = [
                candidate
                for candidate in persisted_candidates
                if candidate["candidate_id"] in selected_ids
            ]
            ar._atomic_json(
                motion_fit_path,
                {
                    "design_digest": design_digest,
                    "result": motion_fit,
                    "candidates": persisted_candidates,
                },
            )
        status(
            "running",
            "motion-repair-ladder-fitted",
            completed=len(motion_candidates),
            total=len(motion_candidates),
        )
        _write_phase(
            output,
            "motion-fit",
            design_digest,
            motion_fit | {"next_phase": "motion-transition-audit"},
            "# Stage 6P motion fit\n\nThe registered baseline, torus-aware, label-calibrated, factorized, and zero-born latch writers were compared in pair-blocked development folds.",
            "# Lay summary\n\nSeveral ways of reading and rewriting the tiny direction note were compared before touching the new movers.",
        )

        active[0] = "motion-transition-audit"
        transition = _run_transition_audit(
            stage_root,
            selected_motion,
            motion_development,
            profile,
            design_digest,
            resume=resume,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
        )
        _write_phase(
            output,
            "motion-transition-audit",
            design_digest,
            transition | {"next_phase": "motion-validation"},
            "# Stage 6P transition audit\n\nEight-by-eight incoming-to-outgoing orientation graphs were measured by rule, shape, phase, and copy-noise level.",
            "# Lay summary\n\nThis map shows which arrow a daughter writes after receiving each possible arrow.",
        )

        active[0] = "motion-validation"
        if allocation.get("stage_gate") and selected_motion:
            motion, qualified_motion = _run_motion_validation(
                stage_root,
                selected_motion,
                motion_bank,
                profile_name,
                contract,
                design_digest,
                resume=resume,
                deadline=float(campaign["hard_deadline_unix"]),
                status=status,
            )
        else:
            motion, qualified_motion = _empty(
                "allocation or motion selection failed"
            ), []
        _write_phase(
            output,
            "motion-validation",
            design_digest,
            motion | {"next_phase": "motion-endurance"},
            "# Stage 6P motion validation\n\nFresh movers faced corrected seed-once commands, frozen-parent rescues, head isolation, scrubs, ablations, nulls, and active-renewal controls through generation eight.",
            "# Lay summary\n\nA reversed note was applied once; daughters then had to observe what they became and keep copying that direction themselves.",
        )

        active[0] = "motion-endurance"
        endurance = _run_motion_endurance(
            stage_root,
            qualified_motion,
            motion_bank,
            profile_name,
            design_digest,
            resume=resume,
            deadline=float(campaign["hard_deadline_unix"]),
            status=status,
        )
        _write_phase(
            output,
            "motion-endurance",
            design_digest,
            endurance | {"next_phase": "compact-basis-fit"},
            "# Stage 6P motion endurance\n\nOnly generation-eight qualifiers could open descriptive generations twelve and sixteen.",
            "# Lay summary\n\nOnly a note that survived the main exam was followed for extra generations.",
        )

        active[0] = "compact-basis-fit"
        basis_fit, compact_fits = _run_compact_basis_fit(
            stage_root,
            stage6n_root,
            base_rows,
            profile_name,
            contract,
            design_digest,
            resume=resume,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
        )
        _write_phase(
            output,
            "compact-basis-fit",
            design_digest,
            basis_fit | {"next_phase": "compact-causal-screen"},
            "# Stage 6P compact basis fit\n\nRank-sixteen PCA, paired-history contrast, hybrid, and supervised reduced-rank bases were fit without runtime targets.",
            "# Lay summary\n\nThe short memory was redesigned to retain differences that matter to a particular history, not just the largest common variations.",
        )

        active[0] = "compact-causal-screen"
        compact, qualified_bases = _run_compact_causal_screen(
            stage_root,
            stage6n_root,
            source,
            compact_fits,
            development_pairs,
            profile_name,
            profile,
            templates,
            frozen,
            writer_contract,
            contract,
            design_digest,
            workers=workers,
            resume=resume,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
        )
        _write_phase(
            output,
            "compact-causal-screen",
            design_digest,
            compact | {"next_phase": "compact-attractor-fit"},
            "# Stage 6P compact causal screen\n\nExact q4 four-share carriers faced intact, destructive-control, damage, and history-specific rescue trajectories on the registered fit-exposed slice.",
            "# Lay summary\n\nEach kind of short note was tested to see whether its information actually caused recovery and whether the right note rescued the right history.",
        )

        active[0] = "compact-attractor-fit"
        if compact.get("stage_gate") and qualified_bases:
            attractor, selected_specs = _run_basis_attractor_fit(
                stage_root,
                base_rows,
                qualified_bases,
                profile_name,
                profile,
                contract,
                design_digest,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                status=status,
            )
        else:
            attractor, selected_specs = _empty(
                "no causal compact basis passed the unchanged screen"
            ), []
        _write_phase(
            output,
            "compact-attractor-fit",
            design_digest,
            attractor | {"next_phase": "compact-contraction"},
            "# Stage 6P compact attractor fit\n\nOnly a causally qualifying basis entered the unchanged radius-four attractor grid.",
            "# Lay summary\n\nOnly a short note that already mattered was allowed to try learning how to rewrite itself.",
        )

        active[0] = "compact-contraction"
        contraction = (
            cn._run_contraction_screen(attractor, selected_specs, contract)
            if selected_specs
            else _empty("no compact basis attractor reached contraction")
        )
        selected_spec_ids = set(contraction.get("selected_spec_ids", []))
        selected_specs = [
            spec for spec in selected_specs if spec["spec_id"] in selected_spec_ids
        ]
        _write_phase(
            output,
            "compact-contraction",
            design_digest,
            contraction | {"next_phase": "compact-closed-loop"},
            "# Stage 6P compact contraction\n\nRegistered damage had to shrink without degrading a clean carrier.",
            "# Lay summary\n\nA hereditary note had to correct a smudge while leaving an undamaged note alone.",
        )

        active[0] = "compact-closed-loop"
        if contraction.get("stage_gate") and selected_specs:
            closed_loop, compact_models = _run_basis_closed_loop(
                stage_root,
                source,
                base_rows,
                development_pairs,
                selected_specs,
                profile_name,
                profile,
                templates,
                frozen,
                writer_contract,
                contract,
                design_digest,
                workers=workers,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                status=status,
            )
        else:
            closed_loop, compact_models = _empty(
                "no causal compact basis contracted registered damage"
            ), []
        _write_phase(
            output,
            "compact-closed-loop",
            design_digest,
            closed_loop | {"next_phase": "compact-validation"},
            "# Stage 6P compact closed loop\n\nThe qualifying basis family was preserved through three out-of-fold daughter-generated refit rounds.",
            "# Lay summary\n\nDaughters repeatedly rewrote the note from their own visible lives, while the test kept the original history as the answer key.",
        )

        active[0] = "compact-validation"
        if closed_loop.get("stage_gate") and compact_models:
            narrow, _ = cn._run_narrow_validation(
                stage_root,
                source,
                compact_models,
                procedural_pairs,
                profile_name,
                profile.causal_profile(),
                templates,
                frozen,
                writer_contract,
                contract,
                design_digest,
                workers=workers,
                resume=resume,
                deadline=float(campaign["hard_deadline_unix"]),
                status=status,
            )
        else:
            narrow = _empty(
                "no causal compact basis writer reached sealed validation"
            )
            narrow["qualified_candidate_ids"] = []
            narrow["procedural_validation_opened"] = False
        _write_phase(
            output,
            "compact-validation",
            design_digest,
            narrow | {"next_phase": "adjudicate"},
            "# Stage 6P compact validation\n\nFrozen causal-basis writers could open the sealed procedural intervention ladder only after every preceding gate.",
            "# Lay summary\n\nA surviving self-copying note finally had to work in unfamiliar daughters and fail for the right reasons when erased.",
        )

        active[0] = "adjudicate"
        result = _campaign_result(
            output,
            design_digest,
            profile_name,
            motion_fit,
            transition,
            motion,
            endurance,
            basis_fit,
            compact,
            attractor,
            contraction,
            closed_loop,
            narrow,
        )
        _write_phase(
            output,
            "adjudicate",
            design_digest,
            result,
            "# Stage 6P adjudication\n\nPolarity closure and compact causal-basis Plastic Heredity were adjudicated independently under their registered gates.",
            "# Lay summary\n\nThe experiment separately asks whether daughters can preserve a direction note and whether a compressed history note can actively renew itself.",
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
                "state": "failed",
                "phase": active[0],
                "error": repr(error),
                "final_audit_trajectory_state": "untouched",
            },
        )
        raise


__all__ = [
    "DEFAULT_STAGE6O_ROOT",
    "DEFAULT_STAGE6N_ROOT",
    "DEFAULT_STAGE6M_ROOT",
    "DEFAULT_STAGE6L_ROOT",
    "PHASES",
    "PROFILES",
    "PolarityClosureContract",
    "PolarityClosureProfile",
    "_best_bijection",
    "_capacity_balance_verified",
    "_corrected_motion_lineage",
    "_parent_integrity",
    "_payload_bits",
    "_payload_code",
    "_wrap_crop_centered",
    "run_motif_polarity_closure",
]
