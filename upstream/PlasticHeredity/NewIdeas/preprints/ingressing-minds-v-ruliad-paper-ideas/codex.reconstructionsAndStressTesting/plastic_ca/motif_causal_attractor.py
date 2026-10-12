"""Stage-6N compact causal carriers, attractor renewal, and motion polarity.

The stage is deliberately downstream of immutable Stage-6L/6M artifacts.  It
has no code path to the protected 62-pair reserve.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Sequence

import numpy as np

from . import motif_acquisition_repair as ar
from . import motif_inverse_distillation as il
from . import motif_latent_regeneration as lm
from . import motif_phenotype_bridge as pb
from . import motif_writer_closure as wc
from .life_family import life_rule_notation


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_CAUSAL_ATTRACTOR_PROTOCOL.md"
DISCOVERY_LOG = ROOT / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"
DEFAULT_STAGE6M_ROOT = ROOT / "results/ca-motif-latent-regeneration-stage-6m"
DEFAULT_STAGE6L_ROOT = lm.DEFAULT_STAGE6L_ROOT
PHASES = (
    "integrity",
    "metric-calibration",
    "narrow-oracle",
    "attractor-fit",
    "contraction-screen",
    "closed-loop",
    "narrow-validation",
    "motion-oracle",
    "motion-writer",
    "motion-validation",
    "adjudicate",
)


@dataclass(frozen=True)
class CausalAttractorProfile:
    development_pairs: int
    procedural_validation_pairs: int
    trace_replicates: int
    validation_replicates: int
    rollout_rounds: int
    maximum_frozen_writers: int
    oracle_pairs: int
    latent_dimensions: tuple[int, ...]
    attractor_kinds: tuple[str, ...]
    support_lengths: tuple[int, ...]
    writer_endpoints: tuple[int, ...]
    motion_scan_per_rule: int
    motion_development_pairs: int
    motion_validation_pairs: int
    motion_oracle_pairs: int
    motion_codebook_sizes: tuple[int, ...]
    bootstrap_resamples: int


PROFILES = {
    "smoke": CausalAttractorProfile(
        6,
        2,
        1,
        1,
        1,
        1,
        2,
        (4,),
        ("leaky",),
        (8,),
        (16,),
        512,
        4,
        2,
        2,
        (4,),
        100,
    ),
    "reference": CausalAttractorProfile(
        56,
        16,
        2,
        4,
        3,
        2,
        8,
        (2, 4, 8, 16),
        ("leaky", "contractive-tanh", "prototype"),
        (8, 16),
        (16, 24),
        8192,
        40,
        16,
        8,
        (2, 4, 8, 16, 32),
        10_000,
    ),
}


@dataclass(frozen=True)
class CausalAttractorContract(lm.LatentRegenerationContract):
    implementation_version: str = "ca-motif-causal-attractor-v1"
    namespace: str = "plastic-ca-motif-causal-attractor-v1"
    compact_recovery_minimum: float = 0.70
    compact_control_advantage_minimum: float = 0.20
    contraction_ratio_maximum: float = 0.80
    clean_degradation_maximum: float = 0.05
    rollout_degradation_maximum: float = 0.03
    motion_foreground_f1_minimum: float = 0.70
    motion_generation1_minimum: float = 0.75
    motion_generation4_minimum: float = 0.60
    motion_direction_margin_minimum: float = 0.20
    metric_positive_minimum: float = 0.90
    metric_null_maximum: float = 0.10
    exploration_stop_hours: float = 6.5

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "compact_recovery_minimum": self.compact_recovery_minimum,
                "compact_control_advantage_minimum": self.compact_control_advantage_minimum,
                "contraction_ratio_maximum": self.contraction_ratio_maximum,
                "clean_degradation_maximum": self.clean_degradation_maximum,
                "rollout_degradation_maximum": self.rollout_degradation_maximum,
                "motion_foreground_f1_minimum": self.motion_foreground_f1_minimum,
                "motion_generation1_minimum": self.motion_generation1_minimum,
                "motion_generation4_minimum": self.motion_generation4_minimum,
                "motion_direction_margin_minimum": self.motion_direction_margin_minimum,
                "compact_payload_dimensions": (2, 4, 8, 16),
                "compact_payload_bits_per_value": 4,
                "compact_runtime_inputs": (
                    "radius-four visible spacetime",
                    "zero-born compact state",
                ),
                "runtime_parent_field": False,
                "runtime_incoming_payload": False,
                "runtime_target_labels": False,
                "final_reserve_policy": "unreachable-and-never-open-in-stage-6n",
            }
        )
        return payload


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _parent_integrity(
    stage6m_root: Path = DEFAULT_STAGE6M_ROOT,
    stage6l_root: Path = DEFAULT_STAGE6L_ROOT,
) -> dict[str, Any]:
    required_m = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "MANIFEST.json",
        "STAGE_DECISION.json",
        "stage6m/COHORTS.json",
        "stage6m/MOTION_BANK.json",
        "COMPLETE",
    )
    missing = [str(stage6m_root / value) for value in required_m if not (stage6m_root / value).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6M artifacts: {missing}")
    result = _load_json(stage6m_root / "RESULTS.json")
    status = _load_json(stage6m_root / "STATUS.json")
    cohorts = _load_json(stage6m_root / "stage6m/COHORTS.json")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6N requires a complete Stage-6M parent")
    if result.get("verdict") != "LATENT_AND_ABSTRACT_REGENERATION_NOT_CAUSAL":
        raise ValueError("Stage-6N requires the registered Stage-6M boundary")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6M final reserve is not untouched")
    if not bool(cohorts.get("procedural_validation_trajectories_not_simulated_before_freeze")):
        raise ValueError("Stage-6M procedural cohort is not sealed")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6M cohort ledger reports a touched reserve")
    parent_l = lm._parent_integrity(stage6l_root)
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "parent_result_sha256": ar._sha256(stage6m_root / "RESULTS.json"),
        "stage6m_required_hashes": {
            value: ar._sha256(stage6m_root / value) for value in required_m
        },
        "stage6l_parent_result_sha256": parent_l["parent_result_sha256"],
        "retained_trace_registry_sha256": parent_l[
            "retained_trace_registry_sha256"
        ],
        "procedural_pair_ids_sha256": cohorts["procedural_pair_ids_sha256"],
        "procedural_trajectories_sealed": True,
        "final_pair_count": 62,
        "final_pair_ids_sha256": cohorts["final_audit_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
    }


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6m_root: Path,
    stage6l_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[
    CausalAttractorContract,
    CausalAttractorProfile,
    dict[str, Any],
    str,
    dict[str, Any],
]:
    contract = CausalAttractorContract()
    profile = PROFILES[profile_name]
    integrity = _parent_integrity(stage6m_root, stage6l_root)
    design = {
        "experiment": "ca_motif_causal_attractor_stage_6n",
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(profile),
        "stage6m_root": str(stage6m_root.resolve()),
        "stage6l_root": str(stage6l_root.resolve()),
        "stage6m_required_hashes": integrity["stage6m_required_hashes"],
        "cohort_route": {
            "narrow_development": "56 already-exposed Stage-6L/6M pairs",
            "narrow_validation": "16 sealed Stage-6M procedural pairs",
            "motion_development": "40 exposed Stage-6M mover pairs",
            "motion_validation": "fresh Stage-6N deterministic namespace",
            "final": "62-pair protected reserve unreachable",
        },
        "registered_phases": PHASES,
        "compact_oracle": {
            "dimensions": profile.latent_dimensions,
            "q_bits": 4,
            "shares": 4,
        },
        "attractor_grid": {
            "kinds": profile.attractor_kinds,
            "support_lengths": profile.support_lengths,
            "writer_endpoints": profile.writer_endpoints,
            "radius": 4,
            "pair_blocked_folds": 6,
        },
        "motion": {
            "codebook_sizes": profile.motion_codebook_sizes,
            "decoder_families": ("global-medoid", "rule-conditioned-medoid"),
            "direction_bits": 3,
            "payload_bits_maximum": 8,
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
            "motif_causal_attractor.py": ar._sha256(Path(__file__)),
            "motif_latent_regeneration.py": ar._sha256(Path(lm.__file__)),
            "motif_phenotype_bridge.py": ar._sha256(Path(pb.__file__)),
        },
    }
    design_digest = _digest(design)
    design["design_digest"] = design_digest
    design_path = output / "DESIGN.json"
    if resume and design_path.exists():
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6N resume design changed")
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
) -> Any:
    def update(state: str, message: str, **extra: Any) -> None:
        now = time.time()
        payload = {
            "experiment": "ca_motif_causal_attractor_stage_6n",
            "state": state,
            "phase": active[0],
            "message": message,
            "profile": profile_name,
            "pid": os.getpid(),
            "workers": int(workers),
            "worker_cap": 4,
            "started_unix": float(campaign["started_unix"]),
            "updated_unix": now,
            "elapsed_seconds": max(
                0.0, now - float(campaign["started_unix"])
            ),
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
                rate
                * (int(extra["total"]) - int(extra["completed"])),
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
        "experiment": "ca_motif_causal_attractor_stage_6n",
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


def _empty(reason: str) -> dict[str, Any]:
    return {
        "state": "complete",
        "stage_gate": False,
        "skipped_reason": reason,
        "final_audit_trajectory_state": "untouched",
    }


def _foreground_overlap(
    observed: np.ndarray, target: np.ndarray
) -> dict[str, float]:
    left = wc._translation_signature(np.asarray(observed, dtype=np.bool_))
    right = wc._translation_signature(np.asarray(target, dtype=np.bool_))
    if left is None or right is None:
        return {"foreground_f1": 0.0, "foreground_iou": 0.0, "mass_ratio": 0.0}
    observed_set = set(left[0])
    target_set = set(right[0])
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
        "mass_ratio": float(len(observed_set) / len(target_set))
        if target_set
        else 0.0,
    }


def _object_motion_metrics(
    observed_history: Sequence[np.ndarray],
    target_history: Sequence[np.ndarray],
    expected_displacement: Sequence[int],
) -> dict[str, Any]:
    detection = wc._detect_mover(observed_history)
    target_detection = wc._detect_mover(target_history)
    if detection is None or target_detection is None:
        return {
            "mover_detected": False,
            "foreground_f1": 0.0,
            "foreground_iou": 0.0,
            "mass_ratio": 0.0,
            "direction_similarity": 0.0,
            "correct_direction": False,
            "form_success": False,
        }
    best = {"foreground_f1": 0.0, "foreground_iou": 0.0, "mass_ratio": 0.0}
    observed_start = int(detection["detection_start"])
    target_start = int(target_detection["detection_start"])
    phase_count = max(int(detection["period"]), int(target_detection["period"]))
    for left_phase in range(phase_count):
        left_index = min(len(observed_history) - 1, observed_start + left_phase)
        for right_phase in range(phase_count):
            right_index = min(len(target_history) - 1, target_start + right_phase)
            score = _foreground_overlap(
                observed_history[left_index], target_history[right_index]
            )
            if (score["foreground_f1"], score["foreground_iou"]) > (
                best["foreground_f1"],
                best["foreground_iou"],
            ):
                best = score
    similarity = wc._velocity_similarity(
        detection["displacement_yx"], expected_displacement
    )
    form_success = bool(
        best["foreground_f1"] >= 0.70
        and 0.5 <= best["mass_ratio"] <= 2.0
    )
    return {
        "mover_detected": True,
        **best,
        "direction_similarity": float(similarity),
        "correct_direction": bool(similarity > 0.5),
        "form_success": form_success,
        "detected_period": int(detection["period"]),
        "detected_displacement_yx": list(detection["displacement_yx"]),
    }


def _run_metric_calibration(
    stage6m_root: Path,
    stage6l_root: Path,
    contract: CausalAttractorContract,
) -> dict[str, Any]:
    positive = _load_json(stage6l_root / "stage6l/MOTION_RESULTS.json")
    negative = _load_json(stage6m_root / "motion-abstraction/RESULTS.json")
    intact = [
        bool(result["generations"][-1]["mover_detected"])
        for row in positive.get("pair_results", [])
        for key, result in row["conditions"].items()
        if key.endswith(":intact")
    ]
    null = [
        bool(result["generations"][-1]["mover_detected"])
        for row in positive.get("pair_results", [])
        for key, result in row["conditions"].items()
        if any(key.endswith(f":{condition}") for condition in ("zero", "read_disabled"))
    ]
    stage6m_null = [
        bool(result["generations"][-1]["mover_detected"])
        for row in negative.get("pair_results", [])
        for key, result in row["conditions"].items()
        if any(key.endswith(f":{condition}") for condition in ("zero", "read_disabled"))
    ]
    blank = [np.zeros((32, 32), dtype=np.bool_) for _ in range(49)]
    blank_metrics = _object_motion_metrics(blank, blank, (0, 1))
    positive_fraction = float(np.mean(intact)) if intact else 0.0
    null_fraction = float(np.mean([*null, *stage6m_null])) if (null or stage6m_null) else 1.0
    gate = bool(
        positive_fraction >= contract.metric_positive_minimum
        and null_fraction <= contract.metric_null_maximum
        and not blank_metrics["mover_detected"]
        and blank_metrics["foreground_f1"] == 0.0
    )
    return {
        "state": "complete",
        "stage_gate": gate,
        "stage6l_intact_detection_fraction": positive_fraction,
        "null_detection_fraction": null_fraction,
        "blank_metrics": blank_metrics,
        "background_pixels_excluded": True,
        "absent_mover_scores_zero": True,
        "stage6m_pixel_form_accuracy_reference": negative.get(
            "form_accuracy_mean"
        ),
        "final_audit_trajectory_state": "untouched",
    }


def _compact_spec(
    latent_size: int,
    attractor_kind: str = "leaky",
    support: int = 8,
    endpoint: int = 16,
) -> dict[str, Any]:
    return {
        "spec_id": (
            f"compact-r4-w16-e{endpoint}-z{latent_size}-"
            f"{attractor_kind}-s{support}"
        ),
        "mode": "local",
        "radius": 4,
        "window": 16,
        "endpoint": int(endpoint),
        "symmetry": "none",
        "latent_size": int(latent_size),
        "attractor_kind": str(attractor_kind),
        "support": int(support),
        "writer_steps": max(1, int(endpoint) - 1),
        "promotable": True,
    }


def _compact_design(
    features: np.ndarray, model: dict[str, Any]
) -> np.ndarray:
    mean = np.asarray(model["input_mean"], dtype=np.float32)
    scale = np.asarray(model["input_scale"], dtype=np.float32)
    design = np.divide(
        features - mean,
        scale,
        out=np.zeros_like(features),
        where=scale > np.float32(1e-6),
    )
    if "projection" in model:
        design = design @ np.asarray(model["projection"], dtype=np.float32)
    return design.astype(np.float32)


def _fit_compact_arrays(
    features: np.ndarray,
    targets: np.ndarray,
    spec: dict[str, Any],
    train: np.ndarray,
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
    target_mean = np.mean(targets[train], axis=0).astype(np.float32)
    _, _, right = np.linalg.svd(
        targets[train] - target_mean, full_matrices=False
    )
    decoder = right[:latent_size].astype(np.float32)
    raw_codes = (targets[train] - target_mean) @ decoder.T
    latent_scale = np.percentile(
        np.abs(raw_codes), 95.0, axis=0
    ).astype(np.float32)
    latent_scale = np.where(latent_scale > 1e-3, latent_scale, 1.0).astype(
        np.float32
    )
    codes = np.clip(raw_codes / latent_scale, -1.0, 1.0).astype(np.float32)
    weights, bias = wc._ridge_fit(design, codes, 0.30)
    prototype_count = min(4, max(2, len(codes) // 32), len(codes))
    prototypes, _ = lm._kmeans(
        codes,
        prototype_count,
        ar._hash_seed("stage6n-prototypes", spec["spec_id"], int(np.sum(train))),
    )
    model: dict[str, Any] = {
        "kind": "compact-attractor-ridge",
        "architecture": f"compact-{spec['attractor_kind']}",
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


def _compact_predict(model: dict[str, Any], features: np.ndarray) -> np.ndarray:
    design = _compact_design(np.asarray(features, dtype=np.float32), model)
    return np.clip(
        design @ np.asarray(model["latent_weights"], dtype=np.float32)
        + np.asarray(model["latent_bias"], dtype=np.float32),
        -1.0,
        1.0,
    ).astype(np.float32)


def _compact_target_codes(
    model: dict[str, Any], targets: np.ndarray
) -> np.ndarray:
    decoder = np.asarray(model["latent_decoder"], dtype=np.float32)
    target_mean = np.asarray(model["latent_target_mean"], dtype=np.float32)
    scale = np.asarray(model["latent_scale"], dtype=np.float32)
    raw = (np.asarray(targets, dtype=np.float32) - target_mean) @ decoder.T
    return np.clip(
        np.divide(raw, scale, out=np.zeros_like(raw), where=scale > 1e-6),
        -1.0,
        1.0,
    ).astype(np.float32)


def _compact_decode_coefficients(
    model: dict[str, Any], codes: np.ndarray
) -> np.ndarray:
    values = np.asarray(codes, dtype=np.float32)
    scale = np.asarray(model["latent_scale"], dtype=np.float32)
    decoder = np.asarray(model["latent_decoder"], dtype=np.float32)
    mean = np.asarray(model["latent_target_mean"], dtype=np.float32)
    return np.clip((values * scale) @ decoder + mean, -1.0, 1.0).astype(
        np.float32
    )


def _iterate_attractor(
    model: dict[str, Any],
    initial: np.ndarray,
    predicted: np.ndarray,
    steps: int,
) -> np.ndarray:
    state = np.asarray(initial, dtype=np.float32).copy()
    for _ in range(max(1, int(steps))):
        state = pb._compact_attractor_update(state, predicted, model)
    return state


def _fit_compact_model(
    rows: Sequence[dict[str, Any]],
    spec: dict[str, Any],
    contract: CausalAttractorContract,
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
        model = _fit_compact_arrays(features, targets, spec, train)
        predicted = _compact_predict(model, features[test])
        clean = _iterate_attractor(
            model,
            np.zeros_like(predicted),
            predicted,
            int(spec["writer_steps"]),
        )
        coefficients = _compact_decode_coefficients(model, clean)
        metrics = il._coefficient_metrics(coefficients, targets[test])
        damaged = predicted.copy()
        damaged[:, 0] = np.clip(damaged[:, 0] + np.float32(1.0 / 7.0), -1.0, 1.0)
        repaired = _iterate_attractor(model, damaged, predicted, 3)
        denominator = np.linalg.norm(damaged - predicted, axis=1)
        numerator = np.linalg.norm(repaired - predicted, axis=1)
        ratios = np.divide(
            numerator,
            denominator,
            out=np.zeros_like(numerator),
            where=denominator > 1e-8,
        )
        one_shot = il._coefficient_metrics(
            _compact_decode_coefficients(model, predicted), targets[test]
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
            model["model_id"] = f"stage6n-{spec['spec_id']}-fold{fold}"
            model["spec"] = dict(spec)
            model["model_digest"] = _digest(model)
            fold_models.append(model)
    full = np.ones(len(features), dtype=np.bool_)
    model = _fit_compact_arrays(features, targets, spec, full)
    model["model_id"] = f"stage6n-{spec['spec_id']}"
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
    score = float(
        0.50 * np.mean(history)
        + 0.20 * np.min(history)
        + 0.15 * np.mean(form)
        + 0.15 * (1.0 - min(1.0, np.median(contraction)))
    ) if history else 0.0
    return {
        "state": "complete",
        "stage_gate": gate,
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


def _compact_candidate(
    source: dict[str, Any],
    model: dict[str, Any],
    *,
    suffix: str,
    oracle: bool = False,
) -> dict[str, Any]:
    spec = model.get("spec", {})
    endpoint = int(spec.get("endpoint", model.get("endpoint", 16)))
    support = int(spec.get("support", 8))
    row = copy.deepcopy(source)
    row.update(
        {
            "candidate_id": f"{model['model_id']}-{suffix}",
            "mechanism": "inherited-field",
            "mechanism_tier": "inherited-field",
            "claim_tier": "broad",
            "adaptive_claim_tier": (
                "compact-causal-oracle" if oracle else "compact-attractor-renewal"
            ),
            "adaptive_architecture": str(model["architecture"]),
            "writer_source": "visible",
            "writer_input_contract": "radius-four-visible-spacetime-and-zero-born-state-only",
            "training_mode": "compact-attractor-regeneration",
            "read_sweeps": 1,
            "field_rank": 16,
            "field_channels": 2,
            "field_bias": 0.70,
            "field_support_sweeps": support,
            "daughter_writer_start_offset": 1,
            "daughter_writer_sweeps": max(1, endpoint - 1),
            "daughter_write_rate": 1.0,
            "adapter_learning_rate": 1.0,
            "adapter_retention": 0.0,
            "two_buffer_handoff": True,
            "compact_latent_carrier": True,
            "compact_oracle_mode": bool(oracle),
            "closure_model": copy.deepcopy(model),
            "closure_self_rehearsal": False,
            "closure_disable_texture_carrier": True,
            "runtime_local_adaptation": True,
            "runtime_target_labels": bool(oracle),
            "runtime_generation_index": False,
            "runtime_pair_identity": False,
            "parent_field_exposed_to_writer": False,
            "promotable": not oracle,
        }
    )
    return row


def _metric_mean(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    key: str,
    generation: int,
) -> float:
    values = wc._lineage_metric_values(
        rows, candidate_id, condition, generation, key
    )
    return float(np.mean(values)) if values else 0.0


def _run_narrow_oracle(
    stage_root: Path,
    source: dict[str, Any],
    rows: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile_name: str,
    profile: CausalAttractorProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: CausalAttractorContract,
    design_digest: str,
    stage6l_root: Path,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[int], dict[int, dict[str, Any]]]:
    root = stage_root / "compact-oracle"
    root.mkdir(parents=True, exist_ok=True)
    models: dict[int, dict[str, Any]] = {}
    summaries: dict[str, Any] = {}
    candidates: list[dict[str, Any]] = []
    for index, latent_size in enumerate(profile.latent_dimensions, start=1):
        spec = _compact_spec(latent_size, "leaky", 8, 16)
        path = root / f"rank-{latent_size:02d}.json"
        if resume and path.exists():
            fitted = _load_json(path)["fitted"]
        else:
            fitted = _fit_compact_model(rows, spec, contract)
            ar._atomic_json(path, {"design_digest": design_digest, "fitted": fitted})
        models[latent_size] = fitted["model"]
        candidates.append(
            _compact_candidate(
                source, fitted["model"], suffix=f"oracle-r{latent_size}", oracle=True
            )
        )
        status(
            "running",
            "fit-compact-oracle-decoders",
            completed=index,
            total=len(profile.latent_dimensions),
            latent_size=latent_size,
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
        list(pairs[: profile.oracle_pairs]),
        candidates,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="stage6n-compact-causal-oracle",
        replicates=profile.trace_replicates,
        generations=8,
        conditions=("intact", *conditions),
        analysis_kind="stage6n-nonpromotable-compact-oracle",
    )
    trajectory_rows, complete = ar._run_json_checkpoints(
        stage_root,
        "compact-oracle-trajectories",
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
    passing: list[int] = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        latent_size = int(candidate["closure_model"]["latent_size"])
        intact = _metric_mean(
            trajectory_rows, candidate_id, "intact", "post_washout_match_mean", 8
        )
        controls = {
            condition: _metric_mean(
                trajectory_rows,
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
        matching = _metric_mean(
            trajectory_rows,
            candidate_id,
            "inherited_field_same_rescue",
            "post_washout_match_mean",
            6,
        )
        opposite = _metric_mean(
            trajectory_rows,
            candidate_id,
            "inherited_field_opposite_rescue",
            "post_washout_match_mean",
            6,
        )
        minimum_advantage = min(
            (intact - value for value in controls.values()), default=-1.0
        )
        gate = bool(
            complete
            and intact >= contract.compact_recovery_minimum
            and minimum_advantage >= contract.compact_control_advantage_minimum
            and matching - opposite
            >= contract.compact_control_advantage_minimum
        )
        if profile_name == "smoke":
            gate = bool(complete)
        if gate:
            passing.append(latent_size)
        summaries[str(latent_size)] = {
            "candidate_id": candidate_id,
            "latent_size": latent_size,
            "offline_cross_validation": models[latent_size].get("training_example_count"),
            "intact_generation8_post_washout": intact,
            "controls_generation8": controls,
            "minimum_intact_control_advantage": minimum_advantage,
            "matching_rescue_generation6": matching,
            "opposite_rescue_generation6": opposite,
            "matching_minus_opposite_rescue": matching - opposite,
            "stage_gate": gate,
        }
    passing = sorted(passing)[:2]
    parent_measurement = _load_json(stage6l_root / "RESULTS.json")[
        "phase_results"
    ]["measurement"]
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and passing),
        "registered_dimensions": list(profile.latent_dimensions),
        "qualified_dimensions": passing,
        "candidate_summaries": summaries,
        "completed_trajectories": len(trajectory_rows),
        "registered_trajectories": len(items),
        "stage6l_full_teacher_measurement_gate": bool(
            parent_measurement.get("stage_gate", False)
        ),
        "stage6l_full_support_effect_ceiling": parent_measurement.get(
            "stage6k_full_support_effect_ceiling"
        ),
        "oracle_target_access": True,
        "oracle_promotable": False,
        "procedural_validation_opened": False,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, passing, models


def _attractor_specs(
    dimensions: Sequence[int], profile: CausalAttractorProfile
) -> list[dict[str, Any]]:
    specs = [
        _compact_spec(dimension, kind, support, endpoint)
        for dimension in dimensions
        for kind in profile.attractor_kinds
        for support in profile.support_lengths
        for endpoint in profile.writer_endpoints
    ]
    if len(specs) > 24:
        raise AssertionError("Stage-6N attractor grid exceeds 24 candidates")
    return specs


def _run_attractor_fit(
    stage_root: Path,
    rows: Sequence[dict[str, Any]],
    dimensions: Sequence[int],
    profile_name: str,
    profile: CausalAttractorProfile,
    contract: CausalAttractorContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "attractor-fit"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    specs = _attractor_specs(dimensions, profile)
    fitted: dict[str, Any] = {}
    for index, spec in enumerate(specs, start=1):
        path = checkpoints / f"{spec['spec_id']}.json"
        if resume and path.exists():
            value = _load_json(path)["result"]
        else:
            if time.time() >= deadline:
                break
            value = _fit_compact_model(rows, spec, contract)
            saved = copy.deepcopy(value)
            saved.pop("fold_models", None)
            ar._atomic_json(path, {"design_digest": design_digest, "result": saved})
        fitted[str(spec["spec_id"])] = value
        status(
            "running",
            "fit-compact-attractor-grid",
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
            int(value["spec"]["latent_size"]),
            value["spec"]["spec_id"],
        ),
    )
    selected_specs = [
        dict(value["spec"])
        for value in ranked[: profile.maximum_frozen_writers]
    ]
    public = {
        key: {
            subkey: subvalue
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
        "selected_spec_ids": [row["spec_id"] for row in selected_specs],
        "candidate_summaries": public,
        "runtime_inputs": "local-visible-spacetime-and-zero-born-state-only",
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, selected_specs


def _run_contraction_screen(
    attractor: dict[str, Any],
    selected_specs: Sequence[dict[str, Any]],
    contract: CausalAttractorContract,
) -> dict[str, Any]:
    summaries = attractor.get("candidate_summaries", {})
    selected: list[str] = []
    diagnostics: dict[str, Any] = {}
    for spec in selected_specs:
        candidate = summaries[str(spec["spec_id"])]
        cv = candidate["cross_validation"]
        gate = bool(
            float(cv["contraction_ratio_median"])
            <= contract.contraction_ratio_maximum
            and float(cv["clean_degradation_maximum"])
            <= contract.clean_degradation_maximum
        )
        diagnostics[str(spec["spec_id"])] = {
            "contraction_ratio_median": cv["contraction_ratio_median"],
            "clean_degradation_maximum": cv["clean_degradation_maximum"],
            "stage_gate": gate,
        }
        if gate:
            selected.append(str(spec["spec_id"]))
    return {
        "state": "complete",
        "stage_gate": bool(selected),
        "selected_spec_ids": selected,
        "candidate_summaries": diagnostics,
        "damage_conditions": ("one-q4-bin", "five-percent-copy-noise"),
        "final_audit_trajectory_state": "untouched",
    }


def _run_closed_loop(
    stage_root: Path,
    source: dict[str, Any],
    base_rows: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    specs: Sequence[dict[str, Any]],
    profile_name: str,
    profile: CausalAttractorProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: CausalAttractorContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "closed-loop-fit"
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
                str(spec["spec_id"]): _fit_compact_model(
                    datasets[str(spec["spec_id"])],
                    spec,
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
            }
            for key, value in fitted.items()
        }
        round_row: dict[str, Any] = {
            "round": round_index,
            "dataset_rows": {key: len(value) for key, value in datasets.items()},
            "writer_summaries": summaries,
            "out_of_fold_rollout": True,
            "teacher_targets_remain_original": True,
        }
        if round_index == profile.rollout_rounds or time.time() >= deadline:
            rounds.append(round_row)
            break
        assignments: list[tuple[dict[str, Any], Sequence[dict[str, Any]]]] = []
        candidate_to_spec: dict[str, str] = {}
        for spec_id, fitted_row in fitted.items():
            for model in fitted_row["fold_models"]:
                fold = int(model["fold"])
                fold_pairs = [
                    pair
                    for pair in pairs
                    if fold_map[str(pair["pair_id"])] == fold
                ]
                candidate = _compact_candidate(
                    source,
                    model,
                    suffix=f"rollout-r{round_index + 1}-oof",
                )
                assignments.append((candidate, fold_pairs))
                candidate_to_spec[str(candidate["candidate_id"])] = spec_id
        trace_rows, complete, total = il._collect_traces(
            stage_root,
            f"compact-rollout-round-{round_index + 1}-traces",
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
        # Keep clean teacher examples at exactly half or more of each round.
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
                "rollout_complete": complete,
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
            "compact-closed-loop-aggregation",
            completed=round_index + 1,
            total=profile.rollout_rounds,
            rollout_trajectories=len(trace_rows),
        )
        if not complete:
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
            -float(
                latest[str(model["spec"]["spec_id"])]["selection_score"]
            ),
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
        "clean_teacher_fraction_minimum": 0.5,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, qualified


def _condition_metric(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
) -> float:
    return _metric_mean(
        rows,
        candidate_id,
        condition,
        "post_washout_match_mean",
        generation,
    )


def _run_narrow_validation(
    stage_root: Path,
    source: dict[str, Any],
    models: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile_name: str,
    profile: CausalAttractorProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: CausalAttractorContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = [
        _compact_candidate(source, model, suffix="sealed") for model in models
    ]
    ar._atomic_json(
        stage_root / "SEALED_STAGE6N_WRITERS.json",
        {
            "design_digest": design_digest,
            "frozen_before_procedural_validation": True,
            "candidate_ids": [row["candidate_id"] for row in candidates],
            "candidates": [pb._candidate_public(row) for row in candidates],
            "runtime_target_labels": False,
            "runtime_parent_field": False,
            "runtime_incoming_payload": False,
            "final_audit_trajectory_state": "untouched",
        },
    )
    conditions = (
        "intact",
        "inherited_field_zero",
        "inherited_field_shuffle",
        "inherited_field_coefficient_shuffle",
        "inherited_field_read_disabled",
        "inherited_field_write_disabled",
        "inherited_field_no_renewal",
        "inherited_field_ablation",
        "inherited_field_same_rescue",
        "inherited_field_opposite_rescue",
        "handoff_visible_scrub",
        "inherited_field_one_bin_damage",
        "inherited_field_copy_noise_5",
    )
    items = ar._make_items(
        list(pairs),
        candidates,
        ar._template_pairs(templates, "qualification"),
        frozen["stage4"]["configuration"],
        phase="stage6n-sealed-procedural-validation",
        replicates=profile.validation_replicates,
        generations=8,
        conditions=conditions,
        analysis_kind="stage6n-frozen-compact-attractor-validation",
    )
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        "narrow-validation-trajectories",
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
    qualified: list[str] = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        intact4 = _condition_metric(rows, candidate_id, "intact", 4)
        intact8 = _condition_metric(rows, candidate_id, "intact", 8)
        controls = {
            condition: _condition_metric(rows, candidate_id, condition, 8)
            for condition in (
                "inherited_field_zero",
                "inherited_field_shuffle",
                "inherited_field_coefficient_shuffle",
                "inherited_field_read_disabled",
                "inherited_field_write_disabled",
                "inherited_field_no_renewal",
                "inherited_field_ablation",
            )
        }
        matching = _condition_metric(
            rows, candidate_id, "inherited_field_same_rescue", 6
        )
        opposite = _condition_metric(
            rows, candidate_id, "inherited_field_opposite_rescue", 6
        )
        minimum_advantage = min(
            (intact8 - value for value in controls.values()), default=-1.0
        )
        gate = bool(
            complete
            and intact4 >= contract.motion_generation4_minimum
            and intact8 >= contract.motion_generation4_minimum
            and minimum_advantage
            >= contract.compact_control_advantage_minimum
            and matching - opposite
            >= contract.compact_control_advantage_minimum
        )
        if profile_name == "smoke":
            gate = bool(complete)
        if gate:
            qualified.append(candidate_id)
        summaries[candidate_id] = {
            "candidate": pb._candidate_public(candidate),
            "generation4_recovery": intact4,
            "generation8_recovery": intact8,
            "controls_generation8": controls,
            "minimum_intact_control_advantage": minimum_advantage,
            "matching_rescue_generation6": matching,
            "opposite_rescue_generation6": opposite,
            "matching_minus_opposite_rescue": matching - opposite,
            "stage_gate": gate,
        }
    endurance: dict[str, Any] = _empty("no generation-eight qualifier")
    if qualified and time.time() < deadline:
        endurance_candidates = [
            candidate
            for candidate in candidates
            if candidate["candidate_id"] in set(qualified)
        ]
        endurance_items = ar._make_items(
            list(pairs),
            endurance_candidates,
            ar._template_pairs(templates, "qualification"),
            frozen["stage4"]["configuration"],
            phase="stage6n-descriptive-endurance",
            replicates=profile.validation_replicates,
            generations=16,
            conditions=("intact", "inherited_field_no_renewal", "inherited_field_ablation"),
            analysis_kind="stage6n-descriptive-endurance",
        )
        endurance_rows, endurance_complete = ar._run_json_checkpoints(
            stage_root,
            "narrow-endurance-trajectories",
            endurance_items,
            endurance_candidates,
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
        endurance = {
            "state": "complete" if endurance_complete else "budget_truncated",
            "stage_gate": bool(endurance_complete),
            "candidate_generation16_recovery": {
                candidate_id: _condition_metric(
                    endurance_rows, candidate_id, "intact", 16
                )
                for candidate_id in qualified
            },
            "descriptive_only": True,
            "final_audit_trajectory_state": "untouched",
        }
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and qualified),
        "candidate_summaries": summaries,
        "qualified_candidate_ids": qualified,
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "procedural_pairs_frozen_before_simulation": True,
        "procedural_validation_opened": bool(items),
        "endurance": endurance,
        "original_final_reserve_used": False,
        "final_audit_trajectory_state": "untouched",
    }
    return result, rows


def _binary_medoid_codebook(
    values: np.ndarray, count: int, seed: int, iterations: int = 16
) -> tuple[np.ndarray, np.ndarray]:
    data = np.where(np.asarray(values, dtype=np.float32) >= 0.0, 1.0, -1.0)
    count = min(max(1, int(count)), len(data))
    rng = np.random.default_rng(seed)
    chosen = [int(rng.integers(0, len(data)))]
    while len(chosen) < count:
        distances = np.min(
            np.stack(
                [np.mean(data != data[index], axis=1) for index in chosen]
            ),
            axis=0,
        )
        for index in chosen:
            distances[index] = -1.0
        chosen.append(int(np.argmax(distances)))
    medoids = data[chosen].copy()
    labels = np.zeros(len(data), dtype=np.int16)
    for _ in range(iterations):
        distances = np.mean(data[:, None] != medoids[None], axis=2)
        updated = np.argmin(distances, axis=1).astype(np.int16)
        if np.array_equal(updated, labels):
            labels = updated
            break
        labels = updated
        for cluster in range(count):
            members = np.flatnonzero(labels == cluster)
            if not len(members):
                continue
            within = np.mean(
                data[members, None] != data[None, members], axis=2
            )
            chosen_member = members[int(np.argmin(np.sum(within, axis=1)))]
            medoids[cluster] = data[chosen_member]
    return medoids.astype(np.float32), labels


def _motion_training_data(
    pairs: Sequence[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    features, shapes, orientations, groups, _ = lm._motion_training_rows(pairs)
    rule_by_pair = {str(pair["pair_id"]): int(pair["rule"]) for pair in pairs}
    rules = np.asarray([rule_by_pair[str(group)] for group in groups], dtype=np.int64)
    return features, shapes, orientations, groups, rules


def _motion_design(features: np.ndarray, model: dict[str, Any]) -> np.ndarray:
    mean = np.asarray(model["input_mean"], dtype=np.float32)
    scale = np.asarray(model["input_scale"], dtype=np.float32)
    normalized = (np.asarray(features, dtype=np.float32) - mean) / scale
    return normalized @ np.asarray(model["projection"], dtype=np.float32)


def _medoid_for_rule(
    model: dict[str, Any], rule: int
) -> np.ndarray:
    if str(model["decoder_family"]) == "rule-conditioned-medoid":
        table = model.get("rule_codebooks", {})
        if str(rule) in table:
            return np.asarray(table[str(rule)], dtype=np.float32)
    return np.asarray(model["shape_codebook"], dtype=np.float32)


def _fit_motion_medoid_arrays(
    features: np.ndarray,
    shapes: np.ndarray,
    orientations: np.ndarray,
    rules: np.ndarray,
    train: np.ndarray,
    count: int,
    family: str,
    seed: int,
) -> dict[str, Any]:
    mean = np.mean(features[train], axis=0).astype(np.float32)
    scale = np.std(features[train], axis=0).astype(np.float32)
    scale = np.where(scale > 1e-6, scale, 1.0).astype(np.float32)
    rng = np.random.default_rng(seed)
    projection = rng.normal(
        0.0,
        1.0 / math.sqrt(features.shape[1]),
        size=(features.shape[1], 192),
    ).astype(np.float32)
    design = ((features[train] - mean) / scale) @ projection
    global_codebook, global_labels = _binary_medoid_codebook(
        shapes[train], count, ar._hash_seed(seed, "global")
    )
    rule_codebooks: dict[str, Any] = {}
    labels = global_labels.copy()
    if family == "rule-conditioned-medoid":
        train_rules = rules[train]
        for rule in sorted(set(train_rules.tolist())):
            local = train_rules == rule
            codebook, local_labels = _binary_medoid_codebook(
                shapes[train][local],
                count,
                ar._hash_seed(seed, "rule", int(rule)),
            )
            if len(codebook) < count:
                codebook = np.concatenate(
                    (codebook, np.repeat(codebook[-1:], count - len(codebook), axis=0))
                )
            rule_codebooks[str(int(rule))] = codebook.tolist()
            labels[local] = local_labels
    label_count = count
    shape_weights, shape_bias = wc._ridge_fit(
        design, np.eye(label_count, dtype=np.float32)[labels], 0.30
    )
    orientation_weights, orientation_bias = wc._ridge_fit(
        design,
        np.eye(8, dtype=np.float32)[orientations[train]],
        0.30,
    )
    return {
        "kind": "sketched-ridge-binary-medoid",
        "decoder_family": family,
        "input_mean": mean.tolist(),
        "input_scale": scale.tolist(),
        "projection": projection.tolist(),
        "shape_weights": shape_weights.tolist(),
        "shape_bias": shape_bias.tolist(),
        "orientation_weights": orientation_weights.tolist(),
        "orientation_bias": orientation_bias.tolist(),
        "shape_codebook": global_codebook.tolist(),
        "rule_codebooks": rule_codebooks,
        "shape_codebook_size": count,
        "shape_bits": int(math.ceil(math.log2(max(2, count)))),
        "direction_bits": 3,
        "payload_bits": int(math.ceil(math.log2(max(2, count)))) + 3,
        "literal_occupancy_payload": False,
        "binary_medoids": True,
        "separate_shape_and_polarity_heads": True,
        "d4_counterfactual_training": True,
        "model_frozen": True,
        "runtime_target_labels": False,
    }


def _foreground_vector_f1(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left) >= 0.0
    b = np.asarray(right) >= 0.0
    intersection = float(np.sum(a & b))
    denominator = float(np.sum(a) + np.sum(b))
    return 2.0 * intersection / denominator if denominator > 0 else 0.0


def _fit_motion_medoid(
    pairs: Sequence[dict[str, Any]], count: int, family: str
) -> dict[str, Any]:
    features, shapes, orientations, groups, rules = _motion_training_data(pairs)
    fold_count = min(6, len(set(groups.tolist())))
    folds = wc._pair_blocked_folds(groups, fold_count)
    fold_rows: list[dict[str, float]] = []
    for fold in range(fold_count):
        train = folds != fold
        test = folds == fold
        model = _fit_motion_medoid_arrays(
            features,
            shapes,
            orientations,
            rules,
            train,
            count,
            family,
            ar._hash_seed("stage6n-motion-medoid", count, family, fold),
        )
        design = _motion_design(features[test], model)
        shape_prediction = np.argmax(
            design @ np.asarray(model["shape_weights"], dtype=np.float32)
            + np.asarray(model["shape_bias"], dtype=np.float32),
            axis=1,
        )
        direction_prediction = np.argmax(
            design @ np.asarray(model["orientation_weights"], dtype=np.float32)
            + np.asarray(model["orientation_bias"], dtype=np.float32),
            axis=1,
        )
        decoded = np.stack(
            [
                _medoid_for_rule(model, int(rule))[int(code) % count]
                for code, rule in zip(
                    shape_prediction.tolist(), rules[test].tolist(), strict=True
                )
            ]
        )
        form = float(
            np.mean(
                [
                    _foreground_vector_f1(left, right)
                    for left, right in zip(decoded, shapes[test], strict=True)
                ]
            )
        )
        direction = float(np.mean(direction_prediction == orientations[test]))
        fold_rows.append(
            {"foreground_f1": form, "direction_accuracy": direction}
        )
    full = np.ones(len(features), dtype=np.bool_)
    model = _fit_motion_medoid_arrays(
        features,
        shapes,
        orientations,
        rules,
        full,
        count,
        family,
        ar._hash_seed("stage6n-motion-medoid", count, family, "full"),
    )
    model["model_id"] = f"stage6n-motion-{family}-k{count}"
    model["model_digest"] = _digest(model)
    form = float(np.mean([row["foreground_f1"] for row in fold_rows]))
    direction = float(np.mean([row["direction_accuracy"] for row in fold_rows]))
    return {
        "model": model,
        "cross_validation": {
            "foreground_f1_mean": form,
            "direction_accuracy_mean": direction,
            "folds": fold_rows,
        },
        "selection_score": 0.55 * form + 0.45 * direction,
    }


def _predict_motion_code(
    model: dict[str, Any], history: Sequence[np.ndarray]
) -> tuple[int, int]:
    feature = il._motion_features(history, len(history) - 1)[None]
    design = _motion_design(feature, model)
    shape = np.argmax(
        design @ np.asarray(model["shape_weights"], dtype=np.float32)
        + np.asarray(model["shape_bias"], dtype=np.float32),
        axis=1,
    )
    orientation = np.argmax(
        design @ np.asarray(model["orientation_weights"], dtype=np.float32)
        + np.asarray(model["orientation_bias"], dtype=np.float32),
        axis=1,
    )
    return int(shape[0]), int(orientation[0])


def _oracle_motion_code(
    model: dict[str, Any],
    history: Sequence[np.ndarray],
    specification: dict[str, Any],
    rule: int,
) -> tuple[int, int]:
    canonical, orientation = lm._canonicalize_motion_phase(
        history,
        16,
        int(specification["period"]),
        specification["displacement_yx"],
    )
    codebook = _medoid_for_rule(model, rule)
    distances = np.mean(
        (codebook >= 0.0) != (canonical.reshape(1, -1) >= 0.0), axis=1
    )
    return int(np.argmin(distances)), int(orientation)


def _decode_motion_code(
    model: dict[str, Any], shape_code: int, orientation: int, rule: int
) -> np.ndarray:
    codebook = _medoid_for_rule(model, rule)
    canonical = codebook[int(shape_code) % len(codebook)].reshape(8, 8)
    return il._d4_blocks(canonical, int(orientation) % 8)


def _motion_lineage(
    model: dict[str, Any],
    pair: dict[str, Any],
    direction: str,
    condition: str,
    *,
    oracle: bool,
    generations: int = 4,
) -> dict[str, Any]:
    specification = pair[direction]
    rule = int(pair["rule"])
    initial = wc._unpack_state_hex(specification["initial_hex"], (32, 32))
    original_history = wc._simulate_history(initial, rule, 64)
    history = original_history[:49]
    stored: np.ndarray | None = None
    generation_rows: list[dict[str, Any]] = []
    shape_bits = int(model["shape_bits"])
    diagonal = all(
        abs(float(value)) > 1e-6 for value in specification["displacement_yx"]
    )
    for generation in range(1, generations + 1):
        if oracle:
            shape_code, orientation = _oracle_motion_code(
                model, original_history, specification, rule
            )
        else:
            shape_code, orientation = _predict_motion_code(model, history)
        written = lm._bits_for_code(shape_code, orientation, shape_bits)
        if generation == 1 or condition not in ("no_renewal", "write_disabled"):
            stored = written.copy()
        if stored is None:
            stored = np.zeros_like(written)
        incoming = stored.copy()
        active = True
        if condition in ("zero", "read_disabled"):
            incoming.fill(0)
            active = False
        elif condition == "shuffle":
            rng = np.random.default_rng(
                ar._hash_seed(
                    "stage6n-motion-shuffle",
                    pair["pair_id"],
                    direction,
                    generation,
                )
            )
            incoming = incoming[rng.permutation(len(incoming))]
        elif condition == "shape_only":
            incoming[shape_bits:] = 0
        elif condition == "polarity_only":
            incoming[:shape_bits] = 0
        elif condition == "opposite_polarity":
            incoming[shape_bits:] = lm._bits_for_code(
                0, lm._opposite_orientation(orientation, diagonal), 0
            )
        elif condition in ("matching_rescue", "opposite_rescue") and generation == 2:
            incoming.fill(0)
            active = False
        elif condition == "matching_rescue" and generation == 3:
            incoming = lm._bits_for_code(shape_code, orientation, shape_bits)
        elif condition == "opposite_rescue" and generation == 3:
            incoming = lm._bits_for_code(
                shape_code,
                lm._opposite_orientation(orientation, diagonal),
                shape_bits,
            )
        elif condition in ("no_renewal", "write_disabled") and generation > 1:
            incoming.fill(0)
            active = False
        elif condition == "ablation" and generation >= 3:
            incoming.fill(0)
            active = False
        copied, exact = lm._bit_codec_roundtrip(
            incoming,
            ar._hash_seed(
                "stage6n-motion-copy",
                pair["pair_id"],
                direction,
                condition,
                generation,
            ),
        )
        decoded_shape, decoded_orientation = lm._code_from_bits(
            copied, shape_bits
        )
        patch = _decode_motion_code(
            model, decoded_shape, decoded_orientation, rule
        )
        if not active or condition == "polarity_only":
            patch = np.zeros_like(patch)
        center = (16, 16)
        if condition == "translation_scrub":
            rng = np.random.default_rng(
                ar._hash_seed(
                    "stage6n-motion-translation",
                    pair["pair_id"],
                    direction,
                    generation,
                )
            )
            center = (int(rng.integers(8, 25)), int(rng.integers(8, 25)))
        reset = lm._install_motion_patch_at(patch, center)
        phase_advance = 0
        if condition == "phase_scrub":
            phase_advance = int(
                ar._hash_seed(
                    "stage6n-motion-phase",
                    pair["pair_id"],
                    direction,
                    generation,
                )
                % max(1, int(specification["period"]))
            )
            if phase_advance:
                reset = wc._simulate_history(reset, rule, phase_advance)[-1]
        new_history = wc._simulate_history(reset, rule, 48)
        expected = specification["displacement_yx"]
        if condition in ("opposite_polarity", "opposite_rescue") and (
            condition == "opposite_polarity" or generation == 3
        ):
            expected = (-int(expected[0]), -int(expected[1]))
        metrics = _object_motion_metrics(new_history, original_history, expected)
        generation_rows.append(
            {
                "generation": generation,
                "visible_reset_zero_before_carrier_read": True,
                "payload_bits": len(incoming),
                "copy_exact": exact,
                "phase_advance": phase_advance,
                "translation_center": list(center),
                **metrics,
            }
        )
        history = new_history
    return {
        "condition": condition,
        "direction": direction,
        "oracle": oracle,
        "generations": generation_rows,
        "final_form_success": bool(generation_rows[-1]["form_success"]),
        "final_correct_direction": bool(generation_rows[-1]["correct_direction"]),
        "all_boundaries_visibly_reset": True,
        "daughter_rewrites_from_visible_history": bool(
            not oracle and condition not in ("write_disabled", "no_renewal")
        ),
    }


def _fresh_motion_validation_bank(
    stage_root: Path,
    stage6m_root: Path,
    stage6l_root: Path,
    profile_name: str,
    profile: CausalAttractorProfile,
    contract: CausalAttractorContract,
    *,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    path = stage_root / "MOTION_VALIDATION_BANK.json"
    if path.exists():
        return _load_json(path)
    exposed_m = _load_json(stage6m_root / "stage6m/MOTION_BANK.json")
    if profile_name == "smoke":
        pairs = list(exposed_m.get("pairs", []))[: profile.motion_validation_pairs]
        result = {
            "state": "complete",
            "stage_gate": bool(len(pairs) == profile.motion_validation_pairs),
            "pairs": pairs,
            "validation_pair_count": len(pairs),
            "role": "smoke-exposed-only",
            "scientific_holdout": False,
            "stage6k_stage6l_stage6m_initial_states_excluded": False,
            "final_audit_trajectory_state": "untouched",
        }
        ar._atomic_json(path, result)
        return result
    excluded_hex = {
        str(specification["initial_hex"])
        for pair in exposed_m.get("pairs", [])
        for specification in (pair["forward"], pair["opposite"])
    }
    exposed_l = _load_json(stage6l_root / "stage6l/MOTION_BANK.json")
    excluded_hex.update(
        str(specification["initial_hex"])
        for pair in exposed_l.get("pairs", [])
        for specification in (pair["forward"], pair["opposite"])
    )
    stage6k_root = Path(_load_json(stage6l_root / "DESIGN.json")["stage6k_root"])
    exposed_k = _load_json(stage6k_root / "stage6k/MOVER_PANEL.json")
    excluded_hex.update(
        str(specification["initial_hex"])
        for pair in exposed_k.get("pairs", [])
        for specification in (pair["forward"], pair["opposite"])
    )
    discoveries: list[dict[str, Any]] = []
    per_rule: dict[str, Any] = {}
    for index, rule in enumerate(wc.MOVER_RULES, start=1):
        if time.time() >= deadline:
            break
        rows = il._scan_motion_rule(
            rule, profile.motion_scan_per_rule, contract.namespace
        )
        fresh: list[dict[str, Any]] = []
        for row in rows:
            if str(row["initial_hex"]) in excluded_hex:
                continue
            copied = dict(row)
            copied["mover_id"] = str(row["mover_id"]).replace(
                "stage6l-", "stage6n-"
            )
            copied["source"] = "stage6n-fresh-deterministic-5x5-scan"
            fresh.append(copied)
        discoveries.extend(fresh)
        per_rule[str(rule)] = {
            "notation": life_rule_notation(rule),
            "scanned": profile.motion_scan_per_rule,
            "fresh_detected": len(fresh),
        }
        status(
            "running",
            "scan-stage6n-motion-validation-bank",
            completed=index,
            total=len(wc.MOVER_RULES),
            fresh_discoveries=len(discoveries),
        )
    ordered = sorted(
        discoveries,
        key=lambda row: (
            ar._hash_seed(contract.namespace, "motion-holdout", row["mover_id"]),
            row["mover_id"],
        ),
    )
    pairs: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in ordered:
        key = (
            int(row["rule"]),
            int(row["period"]),
            tuple(row["displacement_yx"]),
            str(row["initial_hex"]),
        )
        if key in seen:
            continue
        pair = wc._discovered_pair(row)
        if pair is None:
            continue
        seen.add(key)
        pairs.append(pair)
        if len(pairs) >= profile.motion_validation_pairs:
            break
    complete = bool(
        len(pairs) == profile.motion_validation_pairs
        and len(per_rule) == len(wc.MOVER_RULES)
    )
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "rules": per_rule,
        "pairs": pairs,
        "validation_pair_count": len(pairs),
        "scientific_holdout": True,
        "frozen_before_model_selection": True,
        "d4_families_not_split": True,
        "stage6k_stage6l_stage6m_initial_states_excluded": True,
        "allocation_digest": _digest([pair["pair_id"] for pair in pairs]),
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(path, result)
    return result


def _motion_recovery(
    pair_rows: Sequence[dict[str, Any]], condition: str, generation: int
) -> dict[str, float]:
    selected = [
        result["generations"][generation - 1]
        for row in pair_rows
        for key, result in row["conditions"].items()
        if key.endswith(f":{condition}") and len(result["generations"]) >= generation
    ]
    return {
        "form_success_fraction": float(
            np.mean([row["form_success"] for row in selected])
        )
        if selected
        else 0.0,
        "correct_direction_fraction": float(
            np.mean([row["correct_direction"] for row in selected])
        )
        if selected
        else 0.0,
        "foreground_f1_mean": float(
            np.mean([row["foreground_f1"] for row in selected])
        )
        if selected
        else 0.0,
        "direction_similarity_mean": float(
            np.mean([row["direction_similarity"] for row in selected])
        )
        if selected
        else 0.0,
    }


def _run_motion_oracle(
    stage_root: Path,
    development_pairs: Sequence[dict[str, Any]],
    profile_name: str,
    profile: CausalAttractorProfile,
    contract: CausalAttractorContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    root = stage_root / "motion-medoid-fit"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    fits: list[dict[str, Any]] = []
    families = ("global-medoid", "rule-conditioned-medoid")
    total = len(families) * len(profile.motion_codebook_sizes)
    for family in families:
        for count in profile.motion_codebook_sizes:
            path = checkpoints / f"{family}-k{count}.json"
            if resume and path.exists():
                fitted = _load_json(path)["fitted"]
            else:
                if time.time() >= deadline:
                    break
                fitted = _fit_motion_medoid(development_pairs, count, family)
                ar._atomic_json(
                    path, {"design_digest": design_digest, "fitted": fitted}
                )
            fits.append(fitted)
            status(
                "running",
                "fit-binary-medoid-motion-decoders",
                completed=len(fits),
                total=total,
                latest_checkpoint=f"{family}-k{count}",
            )
    conditions = (
        "intact",
        "zero",
        "opposite_polarity",
        "matching_rescue",
        "opposite_rescue",
    )
    oracle_summaries: dict[str, Any] = {}
    qualified: list[dict[str, Any]] = []
    oracle_pairs = list(development_pairs[: profile.motion_oracle_pairs])
    for model_index, fitted in enumerate(fits, start=1):
        model = fitted["model"]
        path = root / f"oracle-{model['model_id']}.json"
        if resume and path.exists():
            pair_rows = _load_json(path)["pair_rows"]
        else:
            pair_rows = []
            for pair in oracle_pairs:
                results = {
                    f"{direction}:{condition}": _motion_lineage(
                        model,
                        pair,
                        direction,
                        condition,
                        oracle=True,
                    )
                    for direction in ("forward", "opposite")
                    for condition in conditions
                }
                pair_rows.append(
                    {
                        "pair_id": pair["pair_id"],
                        "rule": pair["rule"],
                        "conditions": results,
                    }
                )
            ar._atomic_json(
                path, {"design_digest": design_digest, "pair_rows": pair_rows}
            )
        intact1 = _motion_recovery(pair_rows, "intact", 1)
        intact4 = _motion_recovery(pair_rows, "intact", 4)
        zero4 = _motion_recovery(pair_rows, "zero", 4)
        opposite4 = _motion_recovery(pair_rows, "opposite_polarity", 4)
        matching3 = _motion_recovery(pair_rows, "matching_rescue", 3)
        wrong3 = _motion_recovery(pair_rows, "opposite_rescue", 3)
        gate = bool(
            intact1["foreground_f1_mean"]
            >= contract.motion_foreground_f1_minimum
            and intact1["correct_direction_fraction"]
            >= contract.motion_generation1_minimum
            and intact4["correct_direction_fraction"]
            >= contract.motion_generation4_minimum
            and opposite4["correct_direction_fraction"]
            >= contract.motion_generation4_minimum
            and zero4["correct_direction_fraction"]
            <= contract.metric_null_maximum
            and matching3["correct_direction_fraction"]
            - wrong3["correct_direction_fraction"]
            >= contract.compact_control_advantage_minimum
            and int(model["payload_bits"]) <= 8
        )
        if profile_name == "smoke":
            gate = True
        if gate:
            qualified.append(fitted)
        oracle_summaries[model["model_id"]] = {
            "payload_bits": model["payload_bits"],
            "decoder_family": model["decoder_family"],
            "cross_validation": fitted["cross_validation"],
            "intact_generation1": intact1,
            "intact_generation4": intact4,
            "zero_generation4": zero4,
            "opposite_polarity_generation4": opposite4,
            "matching_rescue_generation3": matching3,
            "opposite_rescue_generation3": wrong3,
            "stage_gate": gate,
        }
        status(
            "running",
            "test-motion-oracle-controllability",
            completed=model_index,
            total=len(fits),
            latest_model=model["model_id"],
        )
    qualified = sorted(
        qualified,
        key=lambda value: (
            -float(value["selection_score"]),
            int(value["model"]["payload_bits"]),
            value["model"]["model_id"],
        ),
    )
    selected = qualified[0]["model"] if qualified else None
    result = {
        "state": "complete" if len(fits) == total else "budget_truncated",
        "stage_gate": bool(selected is not None and len(fits) == total),
        "registered_models": total,
        "completed_models": len(fits),
        "candidate_summaries": oracle_summaries,
        "selected_model_id": selected.get("model_id") if selected else None,
        "selected_model_digest": selected.get("model_digest") if selected else None,
        "oracle_target_access": True,
        "oracle_promotable": False,
        "foreground_only_measurement": True,
        "final_audit_trajectory_state": "untouched",
    }
    return result, selected, fits


def _run_motion_validation(
    stage_root: Path,
    model: dict[str, Any] | None,
    bank: dict[str, Any],
    profile_name: str,
    contract: CausalAttractorContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    if model is None:
        return _empty("no abstract motion decoder passed oracle controllability")
    conditions = (
        "intact",
        "phase_scrub",
        "translation_scrub",
        "zero",
        "shuffle",
        "shape_only",
        "polarity_only",
        "opposite_polarity",
        "read_disabled",
        "write_disabled",
        "no_renewal",
        "ablation",
        "matching_rescue",
        "opposite_rescue",
    )
    root = stage_root / "motion-validation"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    pair_rows: list[dict[str, Any]] = []
    pairs = list(bank.get("pairs", []))
    for index, pair in enumerate(pairs, start=1):
        path = checkpoints / f"{pair['pair_id']}.json"
        if resume and path.exists():
            row = _load_json(path)["row"]
        else:
            if time.time() >= deadline:
                break
            results = {
                f"{direction}:{condition}": _motion_lineage(
                    model,
                    pair,
                    direction,
                    condition,
                    oracle=False,
                )
                for direction in ("forward", "opposite")
                for condition in conditions
            }
            row = {
                "pair_id": pair["pair_id"],
                "rule": pair["rule"],
                "conditions": results,
            }
            ar._atomic_json(path, {"design_digest": design_digest, "row": row})
        pair_rows.append(row)
        status(
            "running",
            "validate-object-centred-motion-writer",
            completed=index,
            total=len(pairs),
            payload_bits=model["payload_bits"],
        )
    complete = len(pair_rows) == len(pairs) and bool(bank.get("stage_gate"))
    recovery = {
        condition: {
            "generation1": _motion_recovery(pair_rows, condition, 1),
            "generation3": _motion_recovery(pair_rows, condition, 3),
            "generation4": _motion_recovery(pair_rows, condition, 4),
        }
        for condition in conditions
    }
    intact1 = recovery["intact"]["generation1"]
    intact4 = recovery["intact"]["generation4"]
    opposite4 = recovery["opposite_polarity"]["generation4"]
    phase4 = recovery["phase_scrub"]["generation4"]
    translation4 = recovery["translation_scrub"]["generation4"]
    matching3 = recovery["matching_rescue"]["generation3"]
    wrong3 = recovery["opposite_rescue"]["generation3"]
    null_maximum = max(
        recovery[condition]["generation4"]["correct_direction_fraction"]
        for condition in (
            "zero",
            "read_disabled",
            "write_disabled",
            "no_renewal",
            "ablation",
        )
    )
    direction_margin = (
        intact4["direction_similarity_mean"]
        - recovery["opposite_rescue"]["generation4"][
            "direction_similarity_mean"
        ]
    )
    gate = bool(
        complete
        and intact1["foreground_f1_mean"]
        >= contract.motion_foreground_f1_minimum
        and intact1["correct_direction_fraction"]
        >= contract.motion_generation1_minimum
        and intact4["correct_direction_fraction"]
        >= contract.motion_generation4_minimum
        and opposite4["correct_direction_fraction"]
        >= contract.motion_generation4_minimum
        and direction_margin >= contract.motion_direction_margin_minimum
        and phase4["correct_direction_fraction"]
        >= contract.motion_generation4_minimum
        and translation4["correct_direction_fraction"]
        >= contract.motion_generation4_minimum
        and matching3["correct_direction_fraction"]
        - wrong3["correct_direction_fraction"]
        >= contract.compact_control_advantage_minimum
        and null_maximum <= contract.metric_null_maximum
        and int(model["payload_bits"]) <= 8
    )
    if profile_name == "smoke":
        gate = bool(complete)
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": gate,
        "validation_pair_count": len(pair_rows),
        "selected_model_id": model["model_id"],
        "selected_model_digest": model["model_digest"],
        "decoder_family": model["decoder_family"],
        "meaningful_payload_bits": model["payload_bits"],
        "recovery": recovery,
        "direction_margin": direction_margin,
        "maximum_null_direction_recovery": null_maximum,
        "causal_specificity_gate": bool(
            intact4["correct_direction_fraction"] > null_maximum
            and matching3["correct_direction_fraction"]
            > wrong3["correct_direction_fraction"]
        ),
        "foreground_background_excluded": True,
        "shape_and_polarity_heads_separate": True,
        "literal_occupancy_payload_removed": True,
        "visible_reset_every_boundary": True,
        "pair_results": pair_rows,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result


def _campaign_result(
    output: Path,
    design_digest: str,
    profile_name: str,
    metric: dict[str, Any],
    oracle: dict[str, Any],
    attractor: dict[str, Any],
    contraction: dict[str, Any],
    closed_loop: dict[str, Any],
    narrow: dict[str, Any],
    motion_oracle: dict[str, Any],
    motion: dict[str, Any],
) -> dict[str, Any]:
    narrow_gate = bool(narrow.get("stage_gate", False))
    motion_gate = bool(motion.get("stage_gate", False))
    if profile_name == "smoke":
        verdict = "SMOKE_PATH_VALIDATED"
        scientific_claim = False
    elif not metric.get("stage_gate", False):
        verdict = "INCONCLUSIVE_OBJECT_MEASUREMENT_FAILURE"
        scientific_claim = False
    elif narrow_gate and motion_gate:
        verdict = "NARROW_ATTRACTOR_PH_AND_ABSTRACT_MOTION"
        scientific_claim = True
    elif narrow_gate:
        verdict = "NARROW_ATTRACTOR_PH_ONLY"
        scientific_claim = True
    elif motion_gate:
        verdict = "ABSTRACT_MOTION_CARRIER_ONLY"
        scientific_claim = True
    elif oracle.get("stage_gate", False):
        verdict = "COMPACT_CAUSAL_ORACLE_CONTROL_ONLY"
        scientific_claim = True
    else:
        verdict = "NO_CAUSAL_COMPACT_OR_ABSTRACT_CARRIER"
        scientific_claim = True
    result = {
        "experiment": "ca_motif_causal_attractor_stage_6n",
        "design_digest": design_digest,
        "profile_name": profile_name,
        "state": "complete",
        "stage_gate": bool(narrow_gate or motion_gate),
        "verdict": verdict,
        "scientific_claim": scientific_claim,
        "metric_calibration_gate": bool(metric.get("stage_gate", False)),
        "compact_oracle_gate": bool(oracle.get("stage_gate", False)),
        "attractor_fit_gate": bool(attractor.get("stage_gate", False)),
        "contraction_gate": bool(contraction.get("stage_gate", False)),
        "closed_loop_gate": bool(closed_loop.get("stage_gate", False)),
        "narrow_attractor_ph_gate": narrow_gate,
        "motion_oracle_gate": bool(motion_oracle.get("stage_gate", False)),
        "abstract_motion_gate": motion_gate,
        "mechanism_level_generality_gate": bool(narrow_gate and motion_gate),
        "qualified_narrow_candidate_ids": narrow.get(
            "qualified_candidate_ids", []
        ),
        "claim_boundary": (
            "Engineered synthetic CA heredity only. Motion alone is a carrier "
            "result. No outcome implies biological life, human memory, "
            "consciousness, or agency."
        ),
        "original_final_reserve_opened": False,
        "final_audit_pair_count": 62,
        "final_audit_trajectory_state": "untouched",
        "phase_results": {
            "metric_calibration": metric,
            "narrow_oracle": oracle,
            "attractor_fit": attractor,
            "contraction_screen": contraction,
            "closed_loop": closed_loop,
            "narrow_validation": narrow,
            "motion_oracle": motion_oracle,
            "motion_validation": motion,
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
                "open no reserve; follow the first failed causal gate"
                if not result["stage_gate"]
                else "replicate the qualifying mechanism in a fresh registered stage"
            ),
            "final_audit_trajectory_state": "untouched",
        },
    )
    report = (
        "# Stage 6N causal controllability and attractor renewal\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"Compact oracle gate: `{result['compact_oracle_gate']}`; "
        f"closed-loop renewal gate: `{result['closed_loop_gate']}`; "
        f"narrow causal gate: `{narrow_gate}`; abstract motion gate: "
        f"`{motion_gate}`. The protected 62-pair reserve was neither loaded "
        "nor simulated.\n"
    )
    lay = (
        "# Lay summary\n\n"
        "This round first asked whether a perfect short note can actually "
        "control a reset daughter, then whether daughters can repair and "
        "rewrite that note without seeing it directly. Moving patterns were "
        "scored as objects rather than mostly empty pictures, with shape and "
        "direction tested separately.\n\n"
        f"The registered outcome is **{verdict}**.\n"
    )
    ar._atomic_text(output / "REPORT.md", report)
    ar._atomic_text(output / "LAY_SUMMARY.md", lay)
    ar._atomic_text(output / "COMPLETE", "complete\n")
    return result


def _update_discovery_log(result: dict[str, Any]) -> None:
    # Smoke runs establish only that the execution path is healthy.  Keeping
    # them out of the scientific discovery log prevents a deliberately
    # non-inferential result from looking like a registered campaign result.
    if result.get("profile_name") != "reference":
        return
    entry = (
        "\n\n## Stage 6N: causal controllability and attractor renewal\n\n"
        f"Stage 6N design `{result['design_digest']}` completed with verdict "
        f"**{result['verdict']}**. The campaign calibrated object-centred mover "
        "metrics, tested direct compact-field controllability, tested a "
        "zero-born local attractor writer through closed-loop renewal, and "
        "separately tested binary-medoid shape plus polarity carriers. The "
        "protected 62-pair reserve remained untouched.\n"
    )
    existing = DISCOVERY_LOG.read_text(encoding="utf-8") if DISCOVERY_LOG.exists() else "# Discovery log\n"
    marker = f"Stage 6N design `{result['design_digest']}`"
    if marker not in existing:
        ar._atomic_text(DISCOVERY_LOG, existing.rstrip() + entry)


def run_motif_causal_attractor(
    output: Path,
    *,
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
    """Run Stage 6N without exposing the protected final reserve."""

    ar.require_pinned_numpy()
    if profile_name not in PROFILES:
        raise ValueError(f"unknown Stage-6N profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6N workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6N max-hours must be in (0, 8]")
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    stage6m_root = stage6m_root.resolve()
    stage6l_root = stage6l_root.resolve()
    _parent_integrity(stage6m_root, stage6l_root)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ar._atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
    roots = {
        "stage6d_root": stage6d_root.resolve(),
        "stage6c_root": stage6c_root.resolve(),
        "stage6br_root": stage6br_root.resolve(),
        "stage5r_root": stage5r_root.resolve(),
        "stage5_root": stage5_root.resolve(),
        "stage4_root": stage4_root.resolve(),
        "stage3r_root": stage3r_root.resolve(),
        "stage3_root": stage3_root.resolve(),
        "stage2_root": stage2_root.resolve(),
        "stage1_root": stage1_root.resolve(),
    }
    active = ["prepare"]
    status: Any = None
    try:
        contract, profile, campaign, design_digest, integrity = _prepare_campaign(
            output,
            profile_name,
            stage6m_root,
            stage6l_root,
            max_hours,
            resume=resume,
        )
        status = _status_writer(output, profile_name, campaign, active, workers)
        status("running", "frozen-stage6m-design-and-reserves-verified")
        active[0] = "integrity"
        _write_phase(
            output,
            "integrity",
            design_digest,
            integrity | {"next_phase": "metric-calibration"},
            "# Stage 6N integrity\n\nStage 6M, Stage 6L, the sealed procedural cohort, and the untouched final reserve were hash-verified.",
            "# Lay summary\n\nEvery reused result and every unopened test set was accounted for before the new experiment began.",
        )

        stage_root = output / "stage6n"
        ancestry = il._parent_integrity(
            stage6k_root.resolve(),
            stage6j_root.resolve(),
            stage6i_root.resolve(),
            stage6h_root.resolve(),
        )
        il_profile = il.InverseDistillationProfile(
            profile.development_pairs,
            profile.procedural_validation_pairs,
            profile.trace_replicates,
            profile.validation_replicates,
            profile.rollout_rounds,
            profile.maximum_frozen_writers,
            profile.motion_scan_per_rule,
            profile.motion_development_pairs,
            profile.motion_validation_pairs,
            profile.bootstrap_resamples,
        )
        frozen, cohorts, _, writer_contract, templates = il._reconstruct_cohorts(
            stage_root,
            profile_name,
            il_profile,
            ancestry,
            stage6j_root.resolve(),
            stage6i_root.resolve(),
            stage6h_root.resolve(),
            roots,
        )
        cohort_ledger = _load_json(stage_root / "COHORTS.json")
        if profile_name == "reference":
            if (
                cohort_ledger["procedural_pair_ids_sha256"]
                != integrity["procedural_pair_ids_sha256"]
            ):
                raise ValueError("Stage-6N procedural identities changed from Stage 6M")
        else:
            cohorts["procedural_validation"] = list(
                cohorts["development"][-profile.procedural_validation_pairs :]
            )
            cohort_ledger.update(
                {
                    "procedural_validation_role": "smoke-exposed-only",
                    "procedural_validation_trajectories_not_simulated_before_freeze": False,
                    "scientific_procedural_pair_ids_loaded": False,
                }
            )
            ar._atomic_json(stage_root / "COHORTS.json", cohort_ledger)
        source = wc._materialize_source_candidate(
            stage_root,
            stage6h_root.resolve(),
            stage6br_root.resolve(),
            design_digest,
        )
        retained = lm._retained_rows(stage6l_root)
        wanted = {
            str(pair["pair_id"])
            for pair in cohorts["development"][: profile.development_pairs]
        }
        base_rows = [
            row for row in retained if str(row["pair_id"]) in wanted
        ]
        development_pairs = [
            pair
            for pair in cohorts["development"]
            if str(pair["pair_id"])
            in {str(row["pair_id"]) for row in base_rows}
        ]
        if len(development_pairs) != profile.development_pairs:
            raise ValueError("Stage-6N retained trace/pair reconstruction mismatch")

        active[0] = "metric-calibration"
        metric = _run_metric_calibration(stage6m_root, stage6l_root, contract)
        _write_phase(
            output,
            "metric-calibration",
            design_digest,
            metric | {"next_phase": "narrow-oracle"},
            "# Stage 6N object metric calibration\n\nForeground object detection replaced blank-background pixel agreement and was calibrated against the Stage-6L positive carrier and null controls.",
            "# Lay summary\n\nAn empty board can no longer look successful merely because most pixels in the target picture were also empty.",
        )

        active[0] = "narrow-oracle"
        oracle, dimensions, _ = _run_narrow_oracle(
            stage_root,
            source,
            base_rows,
            development_pairs,
            profile_name,
            profile,
            templates,
            frozen,
            writer_contract,
            contract,
            design_digest,
            stage6l_root,
            workers=workers,
            resume=resume,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
        )
        _write_phase(
            output,
            "narrow-oracle",
            design_digest,
            oracle | {"next_phase": "attractor-fit"},
            "# Stage 6N compact causal oracle\n\nExact teacher-derived compact values crossed the physical q4 bottleneck before any learned renewal writer was considered.",
            "# Lay summary\n\nWe first handed daughters a perfect short note to check whether the note itself could control them.",
        )

        active[0] = "attractor-fit"
        if oracle.get("stage_gate") and dimensions:
            attractor, selected_specs = _run_attractor_fit(
                stage_root,
                base_rows,
                dimensions,
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
                "no compact dimension passed causal oracle control"
            ), []
        _write_phase(
            output,
            "attractor-fit",
            design_digest,
            attractor | {"next_phase": "contraction-screen"},
            "# Stage 6N early local attractor fitting\n\nLocal radius-four writers integrated early daughter-visible activity into leaky, contractive, or prototype compact states.",
            "# Lay summary\n\nThe daughter tried three ways of rewriting the short note while seeing only its own early activity.",
        )

        active[0] = "contraction-screen"
        contraction = (
            _run_contraction_screen(attractor, selected_specs, contract)
            if selected_specs
            else _empty("no attractor candidate reached contraction screening")
        )
        selected_ids = set(contraction.get("selected_spec_ids", []))
        selected_specs = [
            spec for spec in selected_specs if spec["spec_id"] in selected_ids
        ]
        _write_phase(
            output,
            "contraction-screen",
            design_digest,
            contraction | {"next_phase": "closed-loop"},
            "# Stage 6N contraction screen\n\nOne-bin and copy-noise damage had to shrink without degrading an already clean compact state.",
            "# Lay summary\n\nA useful memory must make a smudged note clearer rather than copying the smudge.",
        )

        active[0] = "closed-loop"
        if contraction.get("stage_gate") and selected_specs:
            closed_loop, models = _run_closed_loop(
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
            closed_loop, models = _empty("no compact writer contracted damage"), []
        _write_phase(
            output,
            "closed-loop",
            design_digest,
            closed_loop | {"next_phase": "narrow-validation"},
            "# Stage 6N closed-loop renewal\n\nFold-specific daughters generated only held-out rollouts while clean teacher examples remained at least half of every refit.",
            "# Lay summary\n\nWe repeatedly photocopied the note and checked whether its meaning stayed stable rather than fading each generation.",
        )

        active[0] = "narrow-validation"
        if closed_loop.get("stage_gate") and models:
            narrow, _ = _run_narrow_validation(
                stage_root,
                source,
                models,
                cohorts["procedural_validation"],
                profile_name,
                profile,
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
            narrow = _empty("no frozen compact writer reached procedural validation")
            narrow["qualified_candidate_ids"] = []
            narrow["procedural_validation_opened"] = False
        _write_phase(
            output,
            "narrow-validation",
            design_digest,
            narrow | {"next_phase": "motion-oracle"},
            "# Stage 6N narrow causal validation\n\nFrozen writers faced the intervention ladder on the sealed donor-disjoint procedural cohort.",
            "# Lay summary\n\nA real inherited note had to disappear when erased, return with the matching rescue, and renew across unfamiliar daughters.",
        )

        active[0] = "motion-oracle"
        exposed_motion = _load_json(stage6m_root / "stage6m/MOTION_BANK.json")
        motion_development = list(exposed_motion.get("pairs", []))[
            : profile.motion_development_pairs
        ]
        if metric.get("stage_gate") and motion_development:
            motion_oracle, motion_model, motion_fits = _run_motion_oracle(
                stage_root,
                motion_development,
                profile_name,
                profile,
                contract,
                design_digest,
                resume=resume,
                deadline=float(campaign["hard_deadline_unix"]),
                status=status,
            )
        else:
            motion_oracle, motion_model, motion_fits = (
                _empty("object metric calibration or motion development failed"),
                None,
                [],
            )
        _write_phase(
            output,
            "motion-oracle",
            design_digest,
            motion_oracle | {"next_phase": "motion-writer"},
            "# Stage 6N motion oracle\n\nExact binary medoid shape and D4 polarity codes had to control reset daughters before a visible writer was eligible.",
            "# Lay summary\n\nWe checked that a perfect shape name and direction arrow could actually make a moving object before asking daughters to infer them.",
        )

        active[0] = "motion-writer"
        motion_writer = {
            "state": "complete",
            "stage_gate": bool(motion_model is not None),
            "selected_model_id": motion_model.get("model_id") if motion_model else None,
            "selected_model_digest": motion_model.get("model_digest") if motion_model else None,
            "separate_shape_and_polarity_heads": True,
            "d4_counterfactual_training": True,
            "candidate_count": len(motion_fits),
            "final_audit_trajectory_state": "untouched",
        }
        _write_phase(
            output,
            "motion-writer",
            design_digest,
            motion_writer | {"next_phase": "motion-validation"},
            "# Stage 6N motion writer\n\nA frozen visible-spacetime model used separate shape and polarity heads with D4 counterfactual augmentation.",
            "# Lay summary\n\nThe daughter learned the object's identity separately from the arrow telling it which way to travel.",
        )

        active[0] = "motion-validation"
        bank = _fresh_motion_validation_bank(
            stage_root,
            stage6m_root,
            stage6l_root,
            profile_name,
            profile,
            contract,
            deadline=float(campaign["hard_deadline_unix"]),
            status=status,
        ) if motion_model is not None else _empty("no motion oracle qualifier")
        motion = _run_motion_validation(
            stage_root,
            motion_model,
            bank,
            profile_name,
            contract,
            design_digest,
            resume=resume,
            deadline=float(campaign["hard_deadline_unix"]),
            status=status,
        )
        motion["validation_bank"] = {
            key: value
            for key, value in bank.items()
            if key not in ("pairs", "rules")
        }
        _write_phase(
            output,
            "motion-validation",
            design_digest,
            motion | {"next_phase": "adjudicate"},
            "# Stage 6N object-centred motion validation\n\nThe frozen shape/polarity carrier faced fresh movers, visible reset, phase and translation scrub, ablations, and rescues.",
            "# Lay summary\n\nSuccess required a real moving object going the instructed way—not merely a mostly correct empty picture.",
        )

        active[0] = "adjudicate"
        result = _campaign_result(
            output,
            design_digest,
            profile_name,
            metric,
            oracle,
            attractor,
            contraction,
            closed_loop,
            narrow,
            motion_oracle,
            motion,
        )
        _write_phase(
            output,
            "adjudicate",
            design_digest,
            result,
            "# Stage 6N adjudication\n\nCompact controllability, narrow attractor heredity, and abstract motion are reported as independent causal gates.",
            "# Lay summary\n\nThe conclusion separates a readable trace, a controllable note, a self-renewing memory, and a moving carrier.",
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
    "DEFAULT_STAGE6M_ROOT",
    "DEFAULT_STAGE6L_ROOT",
    "PHASES",
    "PROFILES",
    "CausalAttractorContract",
    "CausalAttractorProfile",
    "_binary_medoid_codebook",
    "_compact_candidate",
    "_fit_compact_model",
    "_foreground_overlap",
    "_object_motion_metrics",
    "_parent_integrity",
    "run_motif_causal_attractor",
]
