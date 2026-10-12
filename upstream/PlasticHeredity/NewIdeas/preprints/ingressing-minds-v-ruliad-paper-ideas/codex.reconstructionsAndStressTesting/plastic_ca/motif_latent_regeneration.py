"""Stage-6M latent history codes and abstract moving-form regeneration.

The narrow track deliberately reuses Stage-6L's retained, already-exposed
visible traces.  Its promotable models receive only local visible spacetime.
The dynamic track uses a fresh mover namespace and replaces literal occupancy
payloads with a direction-neutral shape code plus a three-bit orientation.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, replace
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
from . import motif_adaptive_handoff as ah
from . import motif_inverse_distillation as il
from . import motif_phenotype_bridge as pb
from . import motif_writer_closure as wc
from .life_family import life_rule_notation


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_LATENT_REGENERATION_PROTOCOL.md"
DEFAULT_STAGE6L_ROOT = ROOT / "results/ca-motif-inverse-distillation-stage-6l"
PHASES = (
    "integrity",
    "localization",
    "latent-fit",
    "closed-loop",
    "support-screen",
    "narrow-validation",
    "motion-abstraction",
    "adjudicate",
)


@dataclass(frozen=True)
class LatentRegenerationProfile:
    development_pairs: int
    procedural_validation_pairs: int
    trace_replicates: int
    validation_replicates: int
    dagger_rounds: int
    dagger_base_models: int
    mover_seeds_per_rule: int
    mover_development_pairs: int
    mover_validation_pairs: int
    bootstrap_resamples: int
    localization_endpoints: tuple[int, ...]


PROFILES = {
    "smoke": LatentRegenerationProfile(
        6, 2, 1, 1, 1, 1, 1024, 2, 2, 100, (32,)
    ),
    "reference": LatentRegenerationProfile(
        56, 16, 2, 4, 3, 2, 8192, 24, 16, 10_000,
        (16, 24, 32, 40, 48, 64),
    ),
}


@dataclass(frozen=True)
class LatentRegenerationContract(il.InverseDistillationContract):
    implementation_version: str = "ca-motif-latent-regeneration-v1"
    namespace: str = "plastic-ca-motif-latent-regeneration-v1"
    history_accuracy_minimum: float = 0.70
    history_fold_minimum: float = 0.62
    one_boundary_advantage_minimum: float = 0.15
    narrow_control_advantage_minimum: float = 0.20
    abstract_payload_bits_maximum: int = 8
    exploration_stop_hours: float = 6.5

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "history_accuracy_minimum": self.history_accuracy_minimum,
                "history_fold_minimum": self.history_fold_minimum,
                "one_boundary_advantage_minimum": self.one_boundary_advantage_minimum,
                "narrow_control_advantage_minimum": self.narrow_control_advantage_minimum,
                "latent_continuous_ranks": (1, 2, 4, 8),
                "latent_codebook_sizes": (2, 4, 8, 16),
                "motion_codebook_sizes": (2, 4, 8, 16, 32),
                "motion_direction_bits": 3,
                "abstract_payload_bits_maximum": self.abstract_payload_bits_maximum,
                "runtime_inputs": ("local visible spacetime", "zero-born adapter"),
                "runtime_target_labels": False,
                "runtime_parent_field": False,
                "runtime_incoming_payload": False,
                "final_reserve_policy": "unreachable-and-never-open-in-stage-6m",
            }
        )
        return payload


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _parent_integrity(stage6l_root: Path) -> dict[str, Any]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "MANIFEST.json",
        "STAGE_DECISION.json",
        "stage6l/COHORTS.json",
        "stage6l/initial-visible-traces/stage_summary.json",
        "stage6l/initial-writer-fit/RESULTS.json",
        "stage6l/MOTION_BANK.json",
        "stage6l/MOTION_RESULTS.json",
        "COMPLETE",
    )
    missing = [str(stage6l_root / value) for value in required if not (stage6l_root / value).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6L artifacts: {missing}")
    result = _load_json(stage6l_root / "RESULTS.json")
    status = _load_json(stage6l_root / "STATUS.json")
    cohorts = _load_json(stage6l_root / "stage6l/COHORTS.json")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6M requires a complete Stage-6L parent")
    if result.get("verdict") != "DYNAMIC_CA_CARRIER_CLOSURE_ONLY":
        raise ValueError("Stage-6M requires the registered Stage-6L boundary")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6L final reserve is not untouched")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6L cohort ledger reports a touched reserve")
    checkpoints = sorted(
        (stage6l_root / "stage6l/initial-visible-traces/checkpoints").glob("*.json")
    )
    if len(checkpoints) != 112:
        raise ValueError(f"expected 112 retained Stage-6L traces, found {len(checkpoints)}")
    checkpoint_registry = [
        (path.name, ar._sha256(path)) for path in checkpoints
    ]
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "parent_result_sha256": ar._sha256(stage6l_root / "RESULTS.json"),
        "required_hashes": {value: ar._sha256(stage6l_root / value) for value in required},
        "retained_trace_count": len(checkpoints),
        "retained_trace_registry_sha256": _digest(checkpoint_registry),
        "final_pair_count": 62,
        "final_pair_ids_sha256": cohorts["final_audit_pair_ids_sha256"],
        "procedural_pair_ids_sha256": cohorts["procedural_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
    }


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6l_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[LatentRegenerationContract, LatentRegenerationProfile, dict[str, Any], str, dict[str, Any]]:
    contract = LatentRegenerationContract()
    profile = PROFILES[profile_name]
    integrity = _parent_integrity(stage6l_root)
    design = {
        "experiment": "ca_motif_latent_regeneration_stage_6m",
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(profile),
        "stage6l_root": str(stage6l_root.resolve()),
        "stage6l_required_hashes": integrity["required_hashes"],
        "retained_trace_registry_sha256": integrity["retained_trace_registry_sha256"],
        "cohort_route": {
            "development": "56 Stage-6L-exposed pairs and retained traces",
            "procedural_validation": "16 Stage-6L-frozen donor-disjoint pairs",
            "motion": "fresh Stage-6M seed namespace, Stage-6K/6L launch states excluded",
            "final": "62-pair protected reserve unreachable",
        },
        "localization": {
            "endpoints": profile.localization_endpoints,
            "radii": (4, 6),
            "symmetry_policies": ("none", "soft-d4", "full-d4"),
            "diagnostic_modes": ("shift-consensus", "whole-board"),
            "pair_blocked_folds": 6,
        },
        "latent_search": {
            "continuous_ranks": (1, 2, 4, 8),
            "codebook_sizes": (2, 4, 8, 16),
            "maximum_promotable": 4,
            "dagger_rounds": profile.dagger_rounds,
        },
        "motion_abstraction": {
            "shape_codebook_sizes": (2, 4, 8, 16, 32),
            "direction_bits": 3,
            "canonical_phase": True,
            "canonical_translation": True,
            "literal_occupancy_payload_excluded": True,
        },
        "compute": {
            "hard_hours": max_hours,
            "exploration_cutoff_hours": min(contract.exploration_stop_hours, max_hours),
            "worker_cap": 4,
            "detached_and_resumable": True,
        },
        "protocol_sha256": ar._sha256(PROTOCOL_PATH),
        "implementation_hashes": {
            "motif_latent_regeneration.py": ar._sha256(Path(__file__)),
            "motif_inverse_distillation.py": ar._sha256(Path(il.__file__)),
            "motif_phenotype_bridge.py": ar._sha256(Path(pb.__file__)),
        },
    }
    design_digest = _digest(design)
    design["design_digest"] = design_digest
    design_path = output / "DESIGN.json"
    if resume and design_path.exists():
        prior = _load_json(design_path)
        if prior.get("design_digest") != design_digest:
            raise ValueError("Stage-6M resume design changed")
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
        deadline = float(campaign["hard_deadline_unix"])
        payload = {
            "experiment": "ca_motif_latent_regeneration_stage_6m",
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
            "hard_deadline_unix": deadline,
            "remaining_seconds": max(0.0, deadline - now),
            "final_audit_trajectory_state": "untouched",
            **extra,
        }
        if "eta_seconds" not in extra and int(extra.get("completed", 0)) > 0 and "total" in extra:
            rate = payload["elapsed_seconds"] / int(extra["completed"])
            payload["eta_seconds"] = max(0.0, rate * (int(extra["total"]) - int(extra["completed"])))
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
        "experiment": "ca_motif_latent_regeneration_stage_6m",
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


def _retained_rows(stage6l_root: Path, limit_pairs: int | None = None) -> list[dict[str, Any]]:
    paths = sorted((stage6l_root / "stage6l/initial-visible-traces/checkpoints").glob("*.json"))
    rows = [_load_json(path)["result"] for path in paths]
    if limit_pairs is None:
        return rows
    allowed = sorted({str(row["pair_id"]) for row in rows})[:limit_pairs]
    return [row for row in rows if str(row["pair_id"]) in set(allowed)]


def _symmetries(policy: str) -> tuple[int, ...]:
    if policy == "none":
        return (0,)
    if policy == "soft-d4":
        return (0, 1, 2, 3)
    if policy == "full-d4":
        return tuple(range(8))
    raise ValueError(f"unknown symmetry policy {policy!r}")


def _global_features(history: Sequence[np.ndarray]) -> np.ndarray:
    stack = np.stack(history).astype(np.float32) * np.float32(2.0) - np.float32(1.0)
    current = stack[-1]
    mean = np.mean(stack, axis=0, dtype=np.float32)
    displacement = current - stack[0]
    activity = (
        np.mean(np.abs(np.diff(stack, axis=0)), axis=0, dtype=np.float32)
        if len(stack) > 1 else np.zeros_like(current)
    )
    return np.concatenate(
        (
            current.reshape(len(current), -1),
            mean.reshape(len(mean), -1),
            displacement.reshape(len(displacement), -1),
            activity.reshape(len(activity), -1),
            np.ones((len(current), 1), dtype=np.float32),
        ),
        axis=1,
    )


def _examples(
    rows: Sequence[dict[str, Any]],
    spec: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    feature_rows: list[np.ndarray] = []
    target_rows: list[np.ndarray] = []
    groups: list[str] = []
    endpoints: list[str] = []
    endpoint = int(spec["endpoint"])
    window = int(spec.get("window", 32))
    radius = int(spec.get("radius", 4))
    mode = str(spec.get("mode", "local"))
    for raw in rows:
        for record in il._trace_records(raw):
            available = [sweep for sweep in sorted(record["states"]) if sweep <= endpoint]
            if not available:
                continue
            selected = available[-window:]
            history = [record["states"][sweep] for sweep in selected]
            if mode == "whole-board":
                features = _global_features(history)
            elif mode == "shift-consensus":
                offsets = ((0, 0), (-2, 0), (2, 0), (0, -2), (0, 2))
                shifted = []
                for dy, dx in offsets:
                    centers = np.asarray(record["centers"], dtype=np.int16).copy()
                    centers[:, 0] = (centers[:, 0] + dy) % history[-1].shape[1]
                    centers[:, 1] = (centers[:, 1] + dx) % history[-1].shape[2]
                    local, _ = pb._closure_local_features(history, centers, radius, window, False)
                    shifted.append(local)
                features = np.mean(np.stack(shifted), axis=0, dtype=np.float32)
            else:
                features, _ = pb._closure_local_features(
                    history, record["centers"], radius, window, False
                )
            target_patches = il._teacher_patches(record, max(available), "stable-oracle")
            side = 2 * radius + 1
            for symmetry in _symmetries(str(spec.get("symmetry", "none"))):
                transformed_features = features
                if mode in ("local", "shift-consensus") and symmetry:
                    blocks = features[:, :-1].reshape(len(features), 4, side, side)
                    transformed_features = np.concatenate(
                        (
                            il._d4_blocks(blocks, symmetry).reshape(len(features), -1),
                            np.ones((len(features), 1), dtype=np.float32),
                        ),
                        axis=1,
                    )
                transformed_target = pb._d4_patch(target_patches, symmetry)
                coefficients = np.concatenate(
                    (
                        ar.texture_encode(transformed_target[:, 0], 16),
                        ar.texture_encode(transformed_target[:, 1], 16),
                    ),
                    axis=1,
                )
                feature_rows.append(transformed_features.astype(np.float32))
                target_rows.append(coefficients.astype(np.float32))
                groups.extend([str(record["pair_id"])] * len(features))
                endpoints.extend(
                    [f"{record['pair_id']}:g{record['generation']}:s{endpoint}:d4{symmetry}"] * len(features)
                )
    if not feature_rows:
        raise ValueError("Stage-6M retained traces yielded no examples")
    return (
        np.concatenate(feature_rows),
        np.concatenate(target_rows),
        np.asarray(groups, dtype=str),
        endpoints,
    )


def _projection(spec: dict[str, Any], dimension: int) -> np.ndarray:
    rng = np.random.default_rng(ar._hash_seed("stage6m-projection", spec["spec_id"]))
    return rng.normal(0.0, 1.0 / math.sqrt(max(1, dimension)), size=(dimension, 96)).astype(np.float32)


def _kmeans(values: np.ndarray, count: int, seed: int, iterations: int = 24) -> tuple[np.ndarray, np.ndarray]:
    data = np.asarray(values, dtype=np.float32)
    count = min(count, len(data))
    rng = np.random.default_rng(seed)
    centers = [data[int(rng.integers(0, len(data)))].copy()]
    while len(centers) < count:
        distance = np.min(
            np.stack([np.sum((data - center) ** 2, axis=1) for center in centers]), axis=0
        )
        total = float(np.sum(distance))
        index = int(rng.integers(0, len(data))) if total <= 1e-12 else int(rng.choice(len(data), p=distance / total))
        centers.append(data[index].copy())
    codebook = np.stack(centers)
    labels = np.zeros(len(data), dtype=np.int16)
    for _ in range(iterations):
        distances = np.sum((data[:, None] - codebook[None]) ** 2, axis=2)
        new_labels = np.argmin(distances, axis=1).astype(np.int16)
        if np.array_equal(new_labels, labels):
            labels = new_labels
            break
        labels = new_labels
        for index in range(count):
            members = data[labels == index]
            if len(members):
                codebook[index] = np.mean(members, axis=0)
    return codebook.astype(np.float32), labels


def _fit_latent_arrays(
    features: np.ndarray,
    targets: np.ndarray,
    spec: dict[str, Any],
    train: np.ndarray,
) -> dict[str, Any]:
    mean = np.mean(features[train], axis=0, dtype=np.float64).astype(np.float32)
    scale = np.std(features[train], axis=0, dtype=np.float64).astype(np.float32)
    scale = np.where(scale > np.float32(1e-6), scale, 1.0).astype(np.float32)
    use_projection = features.shape[1] > 700
    projection = _projection(spec, features.shape[1]) if use_projection else None
    normalized = (features[train] - mean) / scale
    design = normalized @ projection if projection is not None else normalized
    family = str(spec["latent_family"])
    model: dict[str, Any] = {
        "kind": "sketched-ridge" if projection is not None else "equivariant-ridge",
        "architecture": f"latent-{family}",
        "radius": int(spec["radius"]),
        "window": int(spec.get("window", 32)),
        "endpoint": int(spec["endpoint"]),
        "symmetry_policy": str(spec["symmetry"]),
        "canonicalize": False,
        "input_mean": mean.tolist(),
        "input_scale": scale.tolist(),
        "output_space": "q4-coefficients",
        "output_rank": 16,
        "confidence_threshold": 0.08,
        "model_frozen": True,
        "runtime_target_labels": False,
        "runtime_parent_field": False,
        "runtime_incoming_payload": False,
        "runtime_pair_identity": False,
        "runtime_generation_index": False,
    }
    if projection is not None:
        model["projection"] = projection.tolist()
        model["projection_phase"] = np.zeros(
            projection.shape[1], dtype=np.float32
        ).tolist()
    if family == "continuous":
        rank = int(spec["latent_size"])
        target_mean = np.mean(targets[train], axis=0).astype(np.float32)
        _, _, right = np.linalg.svd(targets[train] - target_mean, full_matrices=False)
        decoder = right[:rank].astype(np.float32)
        codes = (targets[train] - target_mean) @ decoder.T
        encoder_weights, encoder_bias = wc._ridge_fit(design, codes, 0.30)
        weights = encoder_weights @ decoder
        bias = encoder_bias @ decoder + target_mean
        model.update(
            {
                "latent_kind": "continuous",
                "latent_size": rank,
                "latent_decoder": decoder.tolist(),
                "latent_target_mean": target_mean.tolist(),
                "weights": weights.astype(np.float32).tolist(),
                "bias": bias.astype(np.float32).tolist(),
            }
        )
    elif family == "codebook":
        count = int(spec["latent_size"])
        codebook, labels = _kmeans(
            targets[train], count, ar._hash_seed("stage6m-codebook", spec["spec_id"], int(np.sum(train)))
        )
        one_hot = np.eye(len(codebook), dtype=np.float32)[labels]
        weights, bias = wc._ridge_fit(design, one_hot, 0.30)
        model.update(
            {
                "latent_kind": "codebook",
                "latent_size": len(codebook),
                "latent_codebook": codebook.tolist(),
                "weights": weights.astype(np.float32).tolist(),
                "bias": bias.astype(np.float32).tolist(),
            }
        )
    else:
        raise ValueError(f"unknown latent family {family!r}")
    return model


def _predict_latent(model: dict[str, Any], features: np.ndarray) -> np.ndarray:
    mean = np.asarray(model["input_mean"], dtype=np.float32)
    scale = np.asarray(model["input_scale"], dtype=np.float32)
    design = (features - mean) / scale
    if "projection" in model:
        design = design @ np.asarray(model["projection"], dtype=np.float32)
    raw = design @ np.asarray(model["weights"], dtype=np.float32) + np.asarray(model["bias"], dtype=np.float32)
    if model.get("latent_kind") == "codebook":
        codebook = np.asarray(model["latent_codebook"], dtype=np.float32)
        return codebook[np.argmax(raw, axis=1)]
    return np.clip(raw, -1.0, 1.0)


def _fit_latent_model(
    rows: Sequence[dict[str, Any]],
    spec: dict[str, Any],
    contract: LatentRegenerationContract,
    *,
    retain_fold_models: bool = False,
) -> dict[str, Any]:
    features, targets, groups, endpoints = _examples(rows, spec)
    unique = sorted(set(groups.tolist()))
    fold_count = min(contract.local_writer_fold_count, len(unique))
    folds = wc._pair_blocked_folds(groups, fold_count)
    fold_rows: list[dict[str, Any]] = []
    fold_models: list[dict[str, Any]] = []
    for fold in range(fold_count):
        train = folds != fold
        test = folds == fold
        model = _fit_latent_arrays(features, targets, spec, train)
        metrics = il._coefficient_metrics(_predict_latent(model, features[test]), targets[test])
        fold_rows.append({"fold": fold, "training_pair_count": len(set(groups[train].tolist())), "test_pair_count": len(set(groups[test].tolist())), **metrics})
        if retain_fold_models:
            model["fold"] = fold
            model["model_id"] = f"stage6m-{spec['spec_id']}-fold{fold}"
            model["model_digest"] = _digest(model)
            fold_models.append(model)
    full = np.ones(len(features), dtype=np.bool_)
    model = _fit_latent_arrays(features, targets, spec, full)
    model["model_id"] = f"stage6m-{spec['spec_id']}"
    model["spec"] = dict(spec)
    model["training_pair_count"] = len(unique)
    model["training_example_count"] = len(features)
    model["model_digest"] = _digest(model)
    training = il._coefficient_metrics(_predict_latent(model, features), targets)
    history = [float(row["history_specific_accuracy"]) for row in fold_rows]
    form = [float(row["form_bit_accuracy"]) for row in fold_rows]
    cosine = [float(row["coefficient_cosine"]) for row in fold_rows]
    gate = bool(
        float(np.mean(history)) >= contract.history_accuracy_minimum
        and float(np.min(history)) >= contract.history_fold_minimum
    )
    score = float(0.50 * np.mean(history) + 0.25 * np.min(history) + 0.20 * np.mean(form) + 0.05 * max(0.0, np.mean(cosine)))
    return {
        "state": "complete",
        "stage_gate": gate,
        "spec": dict(spec),
        "selection_score": score,
        "cross_validation": {
            "history_specific_accuracy_mean": float(np.mean(history)),
            "history_specific_accuracy_minimum": float(np.min(history)),
            "form_bit_accuracy_mean": float(np.mean(form)),
            "form_bit_accuracy_minimum": float(np.min(form)),
            "coefficient_cosine_mean": float(np.mean(cosine)),
            "folds": fold_rows,
        },
        "training_metrics": training,
        "model": model,
        "fold_models": fold_models,
        "endpoint_digest": _digest(sorted(set(endpoints))),
    }


def _localization_specs(profile: LatentRegenerationProfile) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for endpoint in profile.localization_endpoints:
        for radius in (4, 6):
            for symmetry in ("none", "soft-d4", "full-d4"):
                rows.append(
                    {
                        "spec_id": f"local-r{radius}-s{endpoint}-{symmetry}-continuous-r4",
                        "mode": "local",
                        "radius": radius,
                        "window": 32,
                        "endpoint": endpoint,
                        "symmetry": symmetry,
                        "latent_family": "continuous",
                        "latent_size": 4,
                        "promotable": True,
                    }
                )
        for mode in ("shift-consensus", "whole-board"):
            rows.append(
                {
                    "spec_id": f"{mode}-s{endpoint}-continuous-r4",
                    "mode": mode,
                    "radius": 4,
                    "window": 32,
                    "endpoint": endpoint,
                    "symmetry": "none",
                    "latent_family": "continuous",
                    "latent_size": 4,
                    "promotable": False,
                }
            )
    return rows


def _run_localization(
    stage_root: Path,
    rows: Sequence[dict[str, Any]],
    profile: LatentRegenerationProfile,
    contract: LatentRegenerationContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "localization-fit"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    specs = _localization_specs(profile)
    fitted: dict[str, dict[str, Any]] = {}
    for spec in specs:
        path = checkpoints / f"{spec['spec_id']}.json"
        if resume and path.exists():
            saved = _load_json(path)
            if saved.get("design_digest") != design_digest:
                raise ValueError("Stage-6M localization checkpoint design changed")
            fitted[str(spec["spec_id"])] = saved["result"]
            continue
        if time.time() >= deadline:
            break
        result = _fit_latent_model(rows, spec, contract)
        result.pop("fold_models", None)
        result.pop("model", None)
        ar._atomic_json(path, {"design_digest": design_digest, "result": result})
        fitted[str(spec["spec_id"])] = result
        status(
            "running",
            "localize-visible-history-signal",
            completed=len(fitted),
            total=len(specs),
            latest_checkpoint=spec["spec_id"],
        )
    complete = len(fitted) == len(specs)
    scientific = profile.development_pairs >= 12
    promotable = [
        value for value in fitted.values()
        if value["spec"].get("promotable")
        and (value.get("stage_gate") or not scientific)
    ]
    ranked = sorted(
        promotable,
        key=lambda value: (-float(value["selection_score"]), value["spec"]["spec_id"]),
    )
    selected_limit = 3 if scientific else 1
    selected = [dict(value["spec"]) for value in ranked[:selected_limit]]
    all_ranked = sorted(
        fitted.values(),
        key=lambda value: (-float(value["selection_score"]), value["spec"]["spec_id"]),
    )
    best_local = next(
        (value for value in all_ranked if value["spec"].get("promotable")), None
    )
    best_ceiling = next(
        (value for value in all_ranked if not value["spec"].get("promotable")), None
    )
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and selected),
        "registered_cells": len(specs),
        "completed_cells": len(fitted),
        "selected_setting_ids": [row["spec_id"] for row in selected],
        "best_local": best_local,
        "best_nonpromotable_ceiling": best_ceiling,
        "candidate_summaries": fitted,
        "whole_board_and_consensus_nonpromotable": True,
        "scientific_gate_applied": scientific,
        "retained_stage6l_traces_only": True,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, selected


def _latent_specs(settings: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for setting in settings:
        base = {
            key: setting[key]
            for key in ("mode", "radius", "window", "endpoint", "symmetry")
        }
        for family, sizes in (("continuous", (1, 2, 4, 8)), ("codebook", (2, 4, 8, 16))):
            for size in sizes:
                spec = {
                    **base,
                    "latent_family": family,
                    "latent_size": size,
                    "promotable": True,
                }
                spec["spec_id"] = (
                    f"{base['mode']}-r{base['radius']}-s{base['endpoint']}-"
                    f"{base['symmetry']}-{family}-{size}"
                )
                rows.append(spec)
    unique = {str(row["spec_id"]): row for row in rows}
    return [unique[key] for key in sorted(unique)]


def _run_latent_search(
    stage_root: Path,
    rows: Sequence[dict[str, Any]],
    settings: Sequence[dict[str, Any]],
    profile_name: str,
    profile: LatentRegenerationProfile,
    contract: LatentRegenerationContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "latent-search"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    specs = _latent_specs(settings)
    fitted: dict[str, dict[str, Any]] = {}
    full_models: dict[str, dict[str, Any]] = {}
    for spec in specs:
        path = checkpoints / f"{spec['spec_id']}.json"
        if resume and path.exists():
            saved = _load_json(path)
            if saved.get("design_digest") != design_digest:
                raise ValueError("Stage-6M latent checkpoint design changed")
            result = saved["result"]
        else:
            if time.time() >= deadline:
                break
            result = _fit_latent_model(rows, spec, contract)
            save_result = copy.deepcopy(result)
            save_result.pop("fold_models", None)
            ar._atomic_json(path, {"design_digest": design_digest, "result": save_result})
        fitted[str(spec["spec_id"])] = {
            key: value for key, value in result.items() if key not in ("model", "fold_models")
        } | {"model_digest": result["model"]["model_digest"]}
        full_models[str(spec["spec_id"])] = result["model"]
        status(
            "running",
            "fit-latent-encoder-decoders",
            completed=len(fitted),
            total=len(specs),
            latest_checkpoint=spec["spec_id"],
        )
    complete = len(fitted) == len(specs)
    eligible = [
        value for value in fitted.values()
        if value.get("stage_gate") or profile_name == "smoke"
    ]
    ranked = sorted(
        eligible,
        key=lambda value: (-float(value["selection_score"]), value["spec"]["spec_id"]),
    )
    selected_specs = [dict(value["spec"]) for value in ranked[: profile.dagger_base_models]]
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and selected_specs),
        "registered_candidates": len(specs),
        "completed_candidates": len(fitted),
        "selected_spec_ids": [row["spec_id"] for row in selected_specs],
        "candidate_summaries": fitted,
        "selection_uses_history_code_not_exact_carrier_gate": True,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, selected_specs


def _candidate_from_latent_model(
    source: dict[str, Any],
    model: dict[str, Any],
    *,
    suffix: str,
    support: int = 8,
    write_offset: int = 1,
    write_span: int = 8,
    rehearsal: bool = False,
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    row.update(
        {
            "candidate_id": f"{model['model_id']}-{suffix}",
            "mechanism": "inherited-field",
            "mechanism_tier": "inherited-field",
            "claim_tier": "broad",
            "adaptive_claim_tier": "rulebook-assisted-latent",
            "adaptive_architecture": str(model["architecture"]),
            "writer_source": "visible",
            "writer_input_contract": "local-visible-spacetime-and-zero-born-adapter-only",
            "training_mode": "rulebook-assisted-latent-regeneration",
            "field_rank": 16,
            "field_channels": 2,
            "field_bias": 0.70,
            "field_support_sweeps": int(support),
            "daughter_writer_start_offset": int(write_offset),
            "daughter_writer_sweeps": int(write_span),
            "daughter_write_rate": 0.65,
            "adapter_learning_rate": 0.55,
            "adapter_retention": 0.65,
            "two_buffer_handoff": True,
            "closure_model": copy.deepcopy(model),
            "closure_self_rehearsal": bool(rehearsal),
            "closure_rehearsal_bias": 0.45,
            "closure_disable_texture_carrier": True,
            "runtime_local_adaptation": False,
            "runtime_target_labels": False,
            "runtime_generation_index": False,
            "runtime_pair_identity": False,
            "parent_field_exposed_to_writer": False,
            "promotable": True,
        }
    )
    return row


def _pair_fold_map(pairs: Sequence[dict[str, Any]], fold_count: int) -> dict[str, int]:
    ids = np.asarray([str(pair["pair_id"]) for pair in pairs], dtype=str)
    repeated = np.repeat(ids, 2)
    folds = wc._pair_blocked_folds(repeated, fold_count)
    return {pair_id: int(fold) for pair_id, fold in zip(ids.tolist(), folds[::2].tolist(), strict=True)}


def _run_closed_loop(
    stage_root: Path,
    source: dict[str, Any],
    base_rows: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    specs: Sequence[dict[str, Any]],
    profile_name: str,
    profile: LatentRegenerationProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: LatentRegenerationContract,
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
    fold_map = _pair_fold_map(pairs, fold_count)
    rounds: list[dict[str, Any]] = []
    latest: dict[str, dict[str, Any]] = {}
    for round_index in range(profile.dagger_rounds + 1):
        round_root = root / f"round-{round_index:02d}"
        models_path = round_root / "MODELS.json"
        if resume and models_path.exists():
            saved = _load_json(models_path)
            if saved.get("design_digest") != design_digest:
                raise ValueError("Stage-6M closed-loop checkpoint design changed")
            fitted = saved["fitted"]
        else:
            fitted = {
                str(spec["spec_id"]): _fit_latent_model(
                    datasets[str(spec["spec_id"])], spec, contract, retain_fold_models=True
                )
                for spec in specs
            }
            ar._atomic_json(models_path, {"design_digest": design_digest, "round": round_index, "fitted": fitted})
        latest = fitted
        round_row: dict[str, Any] = {
            "round": round_index,
            "dataset_rows": {key: len(value) for key, value in datasets.items()},
            "writer_summaries": {
                key: {
                    "stage_gate": bool(value["stage_gate"]),
                    "selection_score": value["selection_score"],
                    "cross_validation": value["cross_validation"],
                    "model_digest": value["model"]["model_digest"],
                }
                for key, value in fitted.items()
            },
            "out_of_fold_rollout": True,
        }
        if round_index == profile.dagger_rounds or time.time() >= deadline:
            rounds.append(round_row)
            break
        assignments: list[tuple[dict[str, Any], Sequence[dict[str, Any]]]] = []
        candidate_to_spec: dict[str, str] = {}
        for spec_id, fitted_row in fitted.items():
            for model in fitted_row["fold_models"]:
                fold = int(model["fold"])
                fold_pairs = [pair for pair in pairs if fold_map[str(pair["pair_id"])] == fold]
                candidate = _candidate_from_latent_model(
                    source, model, suffix=f"dagger-r{round_index + 1}-oof",
                    support=8, write_offset=1, write_span=8,
                )
                assignments.append((candidate, fold_pairs))
                candidate_to_spec[str(candidate["candidate_id"])] = spec_id
        trace_rows, complete, total = il._collect_traces(
            stage_root,
            f"latent-dagger-round-{round_index + 1}-traces",
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
        for row in trace_rows:
            datasets[candidate_to_spec[str(row["candidate_id"])]].append(row)
        round_row.update(
            {
                "rollout_complete": complete,
                "completed_rollouts": len(trace_rows),
                "registered_rollouts": total,
                "next_round_dataset_rows": {key: len(value) for key, value in datasets.items()},
            }
        )
        rounds.append(round_row)
        status("running", "latent-closed-loop-aggregation", completed=round_index + 1, total=profile.dagger_rounds, rollout_trajectories=len(trace_rows))
        if not complete:
            break
    eligible = [
        value for value in latest.values()
        if value.get("stage_gate") or profile_name == "smoke"
    ]
    ranked = sorted(eligible, key=lambda value: (-float(value["selection_score"]), value["spec"]["spec_id"]))
    models = [value["model"] for value in ranked[: profile.dagger_base_models]]
    complete = len(rounds) == profile.dagger_rounds + 1
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and models),
        "registered_rounds": profile.dagger_rounds,
        "completed_rounds": max(0, len(rounds) - 1),
        "rounds": rounds,
        "selected_model_ids": [model["model_id"] for model in models],
        "selected_model_digests": [model["model_digest"] for model in models],
        "out_of_fold_rollout_generation": True,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, models


def _metric_mean(
    rows: Sequence[dict[str, Any]], candidate_id: str, condition: str,
    key: str, generation: int,
) -> float:
    values = wc._lineage_metric_values(rows, candidate_id, condition, generation, key)
    return float(np.mean(values)) if values else 0.0


def _run_support_screen(
    stage_root: Path,
    source: dict[str, Any],
    models: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile_name: str,
    profile: LatentRegenerationProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: LatentRegenerationContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    variants = [
        _candidate_from_latent_model(
            source, model,
            suffix=f"screen-s{support}-o{offset}-w{span}",
            support=support, write_offset=offset, write_span=span,
        )
        for model in models
        for support in (8, 16)
        for offset in (1, 5)
        for span in (1, 8, 16)
        if 32 + offset + span - 1 <= 64
    ]
    items = ar._make_items(
        list(pairs[: min(8, len(pairs))]),
        variants,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="stage6m-latent-support-screen",
        replicates=profile.trace_replicates,
        generations=8,
        conditions=("intact", "no_rewrite", "inherited_field_read_disabled"),
        analysis_kind="stage6m-exposed-latent-screen",
    )
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        "latent-support-screen-trajectories",
        items,
        variants,
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
    frozen_candidates: list[dict[str, Any]] = []
    for model in models:
        model_variants = [row for row in variants if row["closure_model"]["model_id"] == model["model_id"]]
        for row in model_variants:
            candidate_id = str(row["candidate_id"])
            intact = _metric_mean(rows, candidate_id, "intact", "post_washout_match_mean", 6)
            no_rewrite = _metric_mean(rows, candidate_id, "no_rewrite", "post_washout_match_mean", 6)
            read_disabled = _metric_mean(rows, candidate_id, "inherited_field_read_disabled", "post_washout_match_mean", 6)
            terminal = _metric_mean(rows, candidate_id, "intact", "terminal_match_mean", 8)
            advantage = intact - max(no_rewrite, read_disabled)
            summaries[candidate_id] = {
                "field_support_sweeps": int(row["field_support_sweeps"]),
                "write_offset": int(row["daughter_writer_start_offset"]),
                "write_span": int(row["daughter_writer_sweeps"]),
                "intact_generation6_post_washout": intact,
                "no_rewrite_generation6_post_washout": no_rewrite,
                "read_disabled_generation6_post_washout": read_disabled,
                "one_boundary_causal_advantage": advantage,
                "generation8_terminal_match": terminal,
                "selection_score": 0.45 * intact + 0.30 * advantage + 0.25 * terminal,
            }
        winner = max(
            model_variants,
            key=lambda row: (
                summaries[str(row["candidate_id"])]["selection_score"],
                -int(row["daughter_writer_sweeps"]),
            ),
        )
        winner_summary = summaries[str(winner["candidate_id"])]
        passes = bool(
            winner_summary["one_boundary_causal_advantage"]
            >= contract.one_boundary_advantage_minimum
        )
        if passes or profile_name == "smoke":
            for rehearsal in (False, True):
                frozen_candidates.append(
                    _candidate_from_latent_model(
                        source,
                        model,
                        suffix=(
                            f"frozen-s{winner['field_support_sweeps']}-"
                            f"o{winner['daughter_writer_start_offset']}-"
                            f"w{winner['daughter_writer_sweeps']}-sr{int(rehearsal)}"
                        ),
                        support=int(winner["field_support_sweeps"]),
                        write_offset=int(winner["daughter_writer_start_offset"]),
                        write_span=int(winner["daughter_writer_sweeps"]),
                        rehearsal=rehearsal,
                    )
                )
    frozen_candidates = sorted(frozen_candidates, key=lambda row: str(row["candidate_id"]))[:4]
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and frozen_candidates),
        "candidate_summaries": summaries,
        "frozen_candidate_ids": [row["candidate_id"] for row in frozen_candidates],
        "one_boundary_advantage_minimum": contract.one_boundary_advantage_minimum,
        "screen_uses_exposed_pairs_only": True,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(stage_root / "SUPPORT_SCREEN.json", result)
    ar._atomic_json(
        stage_root / "SEALED_STAGE6M_WRITERS.json",
        {
            "design_digest": design_digest,
            "frozen_before_procedural_validation": True,
            "candidates": [pb._candidate_public(row) for row in frozen_candidates],
            "runtime_target_labels": False,
            "runtime_parent_field": False,
            "final_audit_trajectory_state": "untouched",
        },
    )
    return result, frozen_candidates


def _control_advantage(rows: Sequence[dict[str, Any]], candidate_id: str, generation: int = 8) -> dict[str, float]:
    intact = _metric_mean(rows, candidate_id, "intact", "post_washout_match_mean", generation)
    controls = {
        name: _metric_mean(rows, candidate_id, name, "post_washout_match_mean", generation)
        for name in (
            "inherited_field_read_disabled",
            "inherited_field_write_disabled",
            "inherited_field_no_renewal",
            "inherited_field_opposite_rescue",
        )
    }
    matching = _metric_mean(rows, candidate_id, "inherited_field_same_rescue", "post_washout_match_mean", generation)
    return {
        "intact": intact,
        "matching_rescue": matching,
        **controls,
        "minimum_intact_control_advantage": min(
            [intact - value for value in controls.values()] or [0.0]
        ),
        "matching_minus_opposite_rescue": matching - controls["inherited_field_opposite_rescue"],
    }


def _run_narrow_validation(
    stage_root: Path,
    candidates: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile: LatentRegenerationProfile,
    nested: pb.PhenotypeBridgeProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: LatentRegenerationContract,
    design_digest: str,
    profile_name: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    heldout, rows = il._narrow_validation(
        stage_root,
        candidates,
        pairs,
        il.InverseDistillationProfile(
            profile.development_pairs,
            profile.procedural_validation_pairs,
            profile.trace_replicates,
            profile.validation_replicates,
            profile.dagger_rounds,
            profile.dagger_base_models,
            profile.mover_seeds_per_rule,
            profile.mover_development_pairs,
            profile.mover_validation_pairs,
            profile.bootstrap_resamples,
        ),
        nested,
        templates,
        frozen,
        writer_contract,
        contract,
        design_digest,
        profile_name,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    qualified: list[str] = []
    for candidate_id, summary in heldout.get("candidate_summaries", {}).items():
        causal = _control_advantage(rows, candidate_id)
        summary["stage6m_control_advantage"] = causal
        summary["stage6m_control_gate"] = bool(
            causal["minimum_intact_control_advantage"] >= contract.narrow_control_advantage_minimum
            and causal["matching_minus_opposite_rescue"] >= contract.narrow_control_advantage_minimum
        )
        if profile_name == "smoke":
            summary["stage6m_control_gate"] = True
        summary["stage6m_joint_gate"] = bool(
            (summary.get("joint_gate", False) or profile_name == "smoke")
            and summary["stage6m_control_gate"]
        )
        if summary["stage6m_joint_gate"]:
            qualified.append(candidate_id)
    heldout["qualified_candidate_ids"] = qualified
    heldout["stage_gate"] = bool(qualified)
    heldout["control_advantage_minimum"] = contract.narrow_control_advantage_minimum
    heldout["original_final_reserve_used"] = False
    return heldout, rows


def _run_narrow_endurance(
    stage_root: Path,
    candidates: Sequence[dict[str, Any]],
    qualified_ids: Sequence[str],
    pairs: Sequence[dict[str, Any]],
    profile: LatentRegenerationProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: LatentRegenerationContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    selected = [row for row in candidates if str(row["candidate_id"]) in set(qualified_ids)][:2]
    if not selected:
        return {
            "state": "complete",
            "stage_gate": False,
            "skipped_reason": "no narrow candidate passed generation 8",
            "final_audit_trajectory_state": "untouched",
        }
    items = ar._make_items(
        list(pairs),
        selected,
        ar._template_pairs(templates, "qualification"),
        frozen["stage4"]["configuration"],
        phase="stage6m-latent-endurance",
        replicates=min(2, profile.validation_replicates),
        generations=16,
        conditions=("intact", "inherited_field_no_renewal", "inherited_field_read_disabled", "inherited_field_opposite_rescue"),
        analysis_kind="stage6m-procedural-latent-endurance",
    )
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        "latent-endurance-trajectories",
        items,
        selected,
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
    summaries = {
        str(candidate["candidate_id"]): {
            str(generation): {
                condition: _metric_mean(
                    rows, str(candidate["candidate_id"]), condition,
                    "post_washout_match_mean", generation,
                )
                for condition in ("intact", "inherited_field_no_renewal", "inherited_field_read_disabled", "inherited_field_opposite_rescue")
            }
            for generation in (8, 12, 16)
        }
        for candidate in selected
    }
    return {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete),
        "candidate_summaries": summaries,
        "descriptive_after_generation8_qualification": True,
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "final_audit_trajectory_state": "untouched",
    }


def _hadamard(size: int = 64) -> np.ndarray:
    matrix = np.asarray([[1.0]], dtype=np.float32)
    while matrix.shape[0] < size:
        matrix = np.block([[matrix, matrix], [matrix, -matrix]])
    changes = np.sum(matrix[:, 1:] != matrix[:, :-1], axis=1)
    order = np.lexsort((np.arange(size), changes))
    return matrix[order].astype(np.float32)


MOTION_BASIS = _hadamard(64)


def _normalized_velocity(displacement: Sequence[int]) -> tuple[float, float]:
    dy, dx = float(displacement[0]), float(displacement[1])
    scale = max(1.0, abs(dy), abs(dx))
    return dy / scale, dx / scale


def _canonical_velocity(displacement: Sequence[int]) -> tuple[float, float]:
    dy, dx = _normalized_velocity(displacement)
    return (1.0, 1.0) if abs(dy) > 1e-6 and abs(dx) > 1e-6 else (0.0, 1.0)


def _orientation_from_velocity(displacement: Sequence[int]) -> int:
    target = np.asarray(_normalized_velocity(displacement), dtype=np.float32)
    canonical = _canonical_velocity(displacement)
    return min(
        range(8),
        key=lambda symmetry: (
            float(np.sum((np.asarray(il._transform_velocity(canonical, symmetry)) - target) ** 2)),
            symmetry,
        ),
    )


def _canonicalize_motion_phase(
    history: Sequence[np.ndarray],
    endpoint: int,
    period: int,
    displacement: Sequence[int],
) -> tuple[np.ndarray, int]:
    orientation = _orientation_from_velocity(displacement)
    inverse = min(
        range(8),
        key=lambda symmetry: (
            float(
                np.sum(
                    (
                        np.asarray(
                            il._transform_velocity(
                                il._transform_velocity(
                                    _canonical_velocity(displacement), orientation
                                ),
                                symmetry,
                            )
                        )
                        - np.asarray(_canonical_velocity(displacement))
                    )
                    ** 2
                )
            ),
            symmetry,
        ),
    )
    candidates: list[np.ndarray] = []
    for phase in range(max(1, period)):
        index = min(len(history) - 1, endpoint + phase)
        patch = np.where(il._crop_centered(history[index]), 1.0, -1.0).astype(np.float32)
        candidates.append(il._d4_blocks(patch, inverse))
    canonical = min(candidates, key=lambda value: tuple((value > 0.0).reshape(-1).tolist()))
    return canonical.astype(np.float32), orientation


def _fresh_motion_bank(
    stage_root: Path,
    stage6l_root: Path,
    profile: LatentRegenerationProfile,
    contract: LatentRegenerationContract,
    *,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    path = stage_root / "MOTION_BANK.json"
    if path.exists():
        return _load_json(path)
    prior = _load_json(stage6l_root / "stage6l/MOTION_BANK.json")
    excluded_hex = {
        str(specification["initial_hex"])
        for pair in prior.get("pairs", [])
        for specification in (pair["forward"], pair["opposite"])
    }
    stage6k_root = Path(_load_json(stage6l_root / "DESIGN.json")["stage6k_root"])
    earlier = _load_json(stage6k_root / "stage6k/MOVER_PANEL.json")
    excluded_hex.update(
        str(specification["initial_hex"])
        for pair in earlier.get("pairs", [])
        for specification in (pair["forward"], pair["opposite"])
    )
    discoveries: list[dict[str, Any]] = []
    per_rule: dict[str, Any] = {}
    for index, rule in enumerate(wc.MOVER_RULES, start=1):
        if time.time() >= deadline:
            break
        rows = il._scan_motion_rule(rule, profile.mover_seeds_per_rule, contract.namespace)
        fresh: list[dict[str, Any]] = []
        for row in rows:
            if str(row["initial_hex"]) in excluded_hex:
                continue
            copy_row = dict(row)
            copy_row["mover_id"] = str(row["mover_id"]).replace("stage6l-", "stage6m-")
            copy_row["source"] = "stage6m-fresh-deterministic-5x5-scan"
            fresh.append(copy_row)
        discoveries.extend(fresh)
        per_rule[str(rule)] = {
            "notation": life_rule_notation(rule),
            "scanned": profile.mover_seeds_per_rule,
            "fresh_detected": len(fresh),
        }
        status(
            "running", "scan-stage6m-motion-bank", completed=index,
            total=len(wc.MOVER_RULES), fresh_discoveries=len(discoveries),
        )
    total = profile.mover_development_pairs + profile.mover_validation_pairs
    ordered = sorted(
        discoveries,
        key=lambda row: (
            ar._hash_seed(contract.namespace, "motion-allocation", row["mover_id"]),
            row["mover_id"],
        ),
    )
    pairs: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in ordered:
        key = (int(row["rule"]), int(row["period"]), tuple(row["displacement_yx"]), str(row["initial_hex"]))
        if key in seen:
            continue
        pair = wc._discovered_pair(row)
        if pair is None:
            continue
        seen.add(key)
        pairs.append(pair)
        if len(pairs) >= total:
            break
    development = pairs[: profile.mover_development_pairs]
    validation = pairs[profile.mover_development_pairs:total]
    allocation = {row["pair_id"]: "development" for row in development} | {
        row["pair_id"]: "validation" for row in validation
    }
    complete = len(pairs) == total and len(per_rule) == len(wc.MOVER_RULES)
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "rules": per_rule,
        "pairs": pairs,
        "allocation": allocation,
        "development_pair_count": len(development),
        "validation_pair_count": len(validation),
        "stage6k_and_stage6l_initial_states_excluded": True,
        "d4_families_not_split": True,
        "allocation_digest": _digest(allocation),
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(path, result)
    return result


def _motion_training_rows(
    pairs: Sequence[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    features: list[np.ndarray] = []
    shapes: list[np.ndarray] = []
    orientations: list[int] = []
    groups: list[str] = []
    periods: list[int] = []
    for pair in pairs:
        for direction in ("forward", "opposite"):
            specification = pair[direction]
            initial = wc._unpack_state_hex(specification["initial_hex"], (32, 32))
            history = wc._simulate_history(initial, int(pair["rule"]), 64)
            period = int(specification["period"])
            for endpoint in range(16, 16 + period):
                base_feature = il._motion_features(history, endpoint)
                canonical, _ = _canonicalize_motion_phase(
                    history, endpoint, period, specification["displacement_yx"]
                )
                for symmetry in range(8):
                    blocks = il._d4_blocks(base_feature[:-1].reshape(4, 8, 8), symmetry)
                    features.append(np.concatenate((blocks.reshape(-1), np.ones(1, dtype=np.float32))))
                    transformed_displacement = il._transform_velocity(specification["displacement_yx"], symmetry)
                    orientations.append(_orientation_from_velocity(transformed_displacement))
                    shapes.append(canonical.reshape(-1))
                    groups.append(str(pair["pair_id"]))
                    periods.append(period)
    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(shapes, dtype=np.float32),
        np.asarray(orientations, dtype=np.int8),
        np.asarray(groups, dtype=str),
        np.asarray(periods, dtype=np.int16),
    )


def _fit_motion_codebook_arrays(
    features: np.ndarray,
    shapes: np.ndarray,
    orientations: np.ndarray,
    train: np.ndarray,
    count: int,
    seed: int,
) -> dict[str, Any]:
    mean = np.mean(features[train], axis=0).astype(np.float32)
    scale = np.std(features[train], axis=0).astype(np.float32)
    scale = np.where(scale > 1e-6, scale, 1.0).astype(np.float32)
    rng = np.random.default_rng(seed)
    projection = rng.normal(0.0, 1.0 / math.sqrt(features.shape[1]), size=(features.shape[1], 192)).astype(np.float32)
    design = ((features[train] - mean) / scale) @ projection
    codebook, labels = _kmeans(shapes[train], count, seed)
    shape_weights, shape_bias = wc._ridge_fit(
        design, np.eye(len(codebook), dtype=np.float32)[labels], 0.30
    )
    orientation_weights, orientation_bias = wc._ridge_fit(
        design, np.eye(8, dtype=np.float32)[orientations[train]], 0.30
    )
    return {
        "kind": "sketched-ridge-discrete-code",
        "input_mean": mean.tolist(),
        "input_scale": scale.tolist(),
        "projection": projection.tolist(),
        "shape_weights": shape_weights.tolist(),
        "shape_bias": shape_bias.tolist(),
        "orientation_weights": orientation_weights.tolist(),
        "orientation_bias": orientation_bias.tolist(),
        "shape_codebook": codebook.tolist(),
        "shape_codebook_size": len(codebook),
        "shape_bits": int(math.ceil(math.log2(max(2, len(codebook))))),
        "direction_bits": 3,
        "payload_bits": int(math.ceil(math.log2(max(2, len(codebook))))) + 3,
        "canonical_phase": True,
        "canonical_translation": True,
        "literal_occupancy_payload": False,
        "runtime_inputs": "visible-spacetime-only",
        "runtime_target_labels": False,
        "model_frozen": True,
    }


def _predict_motion_code(model: dict[str, Any], history: Sequence[np.ndarray]) -> tuple[int, int]:
    feature = il._motion_features(history, len(history) - 1)[None]
    mean = np.asarray(model["input_mean"], dtype=np.float32)
    scale = np.asarray(model["input_scale"], dtype=np.float32)
    projection = np.asarray(model["projection"], dtype=np.float32)
    design = ((feature - mean) / scale) @ projection
    shape_logits = design @ np.asarray(model["shape_weights"], dtype=np.float32) + np.asarray(model["shape_bias"], dtype=np.float32)
    direction_logits = design @ np.asarray(model["orientation_weights"], dtype=np.float32) + np.asarray(model["orientation_bias"], dtype=np.float32)
    return int(np.argmax(shape_logits[0])), int(np.argmax(direction_logits[0]))


def _decode_motion_code(model: dict[str, Any], shape_code: int, orientation: int) -> np.ndarray:
    codebook = np.asarray(model["shape_codebook"], dtype=np.float32)
    canonical = codebook[int(shape_code) % len(codebook)].reshape(8, 8)
    return il._d4_blocks(canonical, int(orientation) % 8)


def _fit_motion_codebook(
    pairs: Sequence[dict[str, Any]], count: int,
) -> dict[str, Any]:
    features, shapes, orientations, groups, _ = _motion_training_rows(pairs)
    fold_count = min(6, len(set(groups.tolist())))
    folds = wc._pair_blocked_folds(groups, fold_count)
    fold_rows: list[dict[str, float]] = []
    for fold in range(fold_count):
        train = folds != fold
        test = folds == fold
        model = _fit_motion_codebook_arrays(
            features, shapes, orientations, train, count,
            ar._hash_seed("stage6m-motion-codebook", count, fold),
        )
        mean = np.asarray(model["input_mean"], dtype=np.float32)
        scale = np.asarray(model["input_scale"], dtype=np.float32)
        projection = np.asarray(model["projection"], dtype=np.float32)
        design = ((features[test] - mean) / scale) @ projection
        shape_prediction = np.argmax(
            design @ np.asarray(model["shape_weights"], dtype=np.float32) + np.asarray(model["shape_bias"], dtype=np.float32), axis=1
        )
        direction_prediction = np.argmax(
            design @ np.asarray(model["orientation_weights"], dtype=np.float32) + np.asarray(model["orientation_bias"], dtype=np.float32), axis=1
        )
        decoded = np.asarray(model["shape_codebook"], dtype=np.float32)[shape_prediction]
        form = float(np.mean((decoded >= 0.0) == (shapes[test] >= 0.0)))
        direction = float(np.mean(direction_prediction == orientations[test]))
        fold_rows.append({"form_accuracy": form, "direction_accuracy": direction})
    full = np.ones(len(features), dtype=np.bool_)
    model = _fit_motion_codebook_arrays(
        features, shapes, orientations, full, count,
        ar._hash_seed("stage6m-motion-codebook", count, "full"),
    )
    model["model_id"] = f"stage6m-motion-codebook-k{count}"
    model["model_digest"] = _digest(model)
    form = float(np.mean([row["form_accuracy"] for row in fold_rows]))
    direction = float(np.mean([row["direction_accuracy"] for row in fold_rows]))
    return {
        "model": model,
        "cross_validation": {
            "form_accuracy_mean": form,
            "direction_accuracy_mean": direction,
            "folds": fold_rows,
        },
        "selection_score": 0.60 * form + 0.40 * direction,
    }


def _bits_for_code(shape_code: int, orientation: int, shape_bits: int) -> np.ndarray:
    values = [((shape_code >> bit) & 1) for bit in range(shape_bits)]
    values.extend(((orientation >> bit) & 1) for bit in range(3))
    return np.asarray(values, dtype=np.uint8)


def _code_from_bits(bits: np.ndarray, shape_bits: int) -> tuple[int, int]:
    values = np.asarray(bits, dtype=np.uint8).reshape(-1)
    shape = sum(int(values[bit]) << bit for bit in range(shape_bits))
    orientation = sum(int(values[shape_bits + bit]) << bit for bit in range(3))
    return shape, orientation


def _bit_codec_roundtrip(bits: np.ndarray, seed: int, corruption: float = 0.01) -> tuple[np.ndarray, bool]:
    payload = np.asarray(bits, dtype=np.uint8).reshape(-1) & 1
    rng = np.random.default_rng(seed)
    shares = rng.integers(0, 2, size=(4, len(payload)), dtype=np.uint8)
    shares[-1] = np.bitwise_xor.reduce(shares[:-1], axis=0) ^ payload
    if corruption > 0.0:
        flips = rng.random(shares.shape) < corruption
        shares ^= flips.astype(np.uint8)
    decoded = np.bitwise_xor.reduce(shares, axis=0)
    return decoded.astype(np.uint8), bool(np.array_equal(decoded, payload))


def _install_motion_patch_at(patch: np.ndarray, center: tuple[int, int] = (16, 16)) -> np.ndarray:
    board = np.zeros((32, 32), dtype=np.bool_)
    offsets = np.arange(-4, 4)
    ys = (int(center[0]) + offsets) % 32
    xs = (int(center[1]) + offsets) % 32
    board[np.ix_(ys, xs)] = np.asarray(patch) > 0.0
    return board


def _opposite_orientation(orientation: int, diagonal: bool = True) -> int:
    canonical = (1.0, 1.0) if diagonal else (0.0, 1.0)
    velocity = il._transform_velocity(canonical, orientation)
    return _orientation_from_velocity((-velocity[0], -velocity[1]))


def _motion_abstract_lineage(
    model: dict[str, Any],
    pair: dict[str, Any],
    direction: str,
    condition: str,
    generations: int = 4,
) -> dict[str, Any]:
    specification = pair[direction]
    initial = wc._unpack_state_hex(specification["initial_hex"], (32, 32))
    history = wc._simulate_history(initial, int(pair["rule"]), 48)
    stored: np.ndarray | None = None
    generation_rows: list[dict[str, Any]] = []
    shape_bits = int(model["shape_bits"])
    diagonal = all(abs(float(value)) > 1e-6 for value in specification["displacement_yx"])
    for generation in range(1, generations + 1):
        shape_code, orientation = _predict_motion_code(model, history)
        written = _bits_for_code(shape_code, orientation, shape_bits)
        if generation == 1 or condition != "no_renewal":
            stored = written.copy()
        assert stored is not None
        incoming = stored.copy()
        readable = True
        active_payload = True
        if condition in ("zero", "read_disabled", "write_disabled"):
            incoming.fill(0)
            readable = condition != "read_disabled"
            active_payload = False
        elif condition == "shuffle":
            rng = np.random.default_rng(ar._hash_seed("stage6m-motion-shuffle", pair["pair_id"], direction, generation))
            incoming = incoming[rng.permutation(len(incoming))]
        elif condition == "shape_only":
            incoming[shape_bits:] = 0
        elif condition == "direction_only":
            incoming[:shape_bits] = 0
        elif condition in ("matching_rescue", "opposite_rescue") and generation == 2:
            incoming.fill(0)
            active_payload = False
        elif condition == "opposite_direction" or (condition == "opposite_rescue" and generation == 3):
            incoming[shape_bits:] = _bits_for_code(0, _opposite_orientation(orientation, diagonal), 0)
        elif condition == "no_renewal" and generation > 1:
            incoming.fill(0)
            active_payload = False
        elif condition == "ablation" and generation >= 3:
            incoming.fill(0)
            active_payload = False
        elif condition == "matching_rescue" and generation == 3:
            incoming = written.copy()
            active_payload = True
        copied, exact = _bit_codec_roundtrip(
            incoming,
            ar._hash_seed("stage6m-motion-bit-codec", pair["pair_id"], direction, condition, generation),
        )
        decoded_shape, decoded_orientation = _code_from_bits(copied, shape_bits)
        patch = _decode_motion_code(model, decoded_shape, decoded_orientation)
        if condition == "direction_only" or not readable or not active_payload:
            patch = np.zeros_like(patch)
        center = (16, 16)
        if condition == "translation_scrub":
            rng = np.random.default_rng(ar._hash_seed("stage6m-motion-translation", pair["pair_id"], direction, generation))
            center = (int(rng.integers(8, 25)), int(rng.integers(8, 25)))
        reset = _install_motion_patch_at(patch, center)
        phase_advance = 0
        if condition == "phase_scrub":
            phase_advance = int(
                ar._hash_seed("stage6m-motion-phase", pair["pair_id"], direction, generation)
                % max(1, int(specification["period"]))
            )
            if phase_advance:
                reset = wc._simulate_history(reset, int(pair["rule"]), phase_advance)[-1]
        new_history = wc._simulate_history(reset, int(pair["rule"]), 48)
        detection = wc._detect_mover(new_history)
        similarity = (
            wc._velocity_similarity(detection["displacement_yx"], specification["displacement_yx"])
            if detection is not None else 0.0
        )
        target_history = wc._simulate_history(initial, int(pair["rule"]), 64)
        target_canonical, target_orientation = _canonicalize_motion_phase(
            target_history, 16, int(specification["period"]), specification["displacement_yx"]
        )
        target_patch = il._d4_blocks(target_canonical, target_orientation)
        form_accuracy = float(np.mean((patch >= 0.0) == (target_patch >= 0.0)))
        generation_rows.append(
            {
                "generation": generation,
                "visible_reset_zero_before_carrier_read": True,
                "payload_bits": len(incoming),
                "copy_exact": exact,
                "form_accuracy": form_accuracy,
                "phase_advance": phase_advance,
                "translation_center": center,
                "mover_detected": detection is not None,
                "correct_direction": bool(detection is not None and similarity > 0.5),
                "direction_similarity": similarity,
            }
        )
        history = new_history
    return {
        "condition": condition,
        "direction": direction,
        "generations": generation_rows,
        "final_correct_direction": bool(generation_rows[-1]["correct_direction"]),
        "all_boundaries_visibly_reset": True,
        "daughter_rewrites_from_visible_history": condition not in ("write_disabled", "no_renewal"),
    }


def _run_motion_abstraction(
    stage_root: Path,
    stage6l_root: Path,
    profile: LatentRegenerationProfile,
    contract: LatentRegenerationContract,
    *,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    bank = _fresh_motion_bank(
        stage_root, stage6l_root, profile, contract, deadline=deadline, status=status
    )
    development = [
        pair for pair in bank.get("pairs", [])
        if bank.get("allocation", {}).get(pair["pair_id"]) == "development"
    ]
    validation = [
        pair for pair in bank.get("pairs", [])
        if bank.get("allocation", {}).get(pair["pair_id"]) == "validation"
    ]
    if not development or not validation:
        return {
            "state": "budget_truncated",
            "stage_gate": False,
            "skipped_reason": "fresh Stage-6M mover bank incomplete",
            "final_audit_trajectory_state": "untouched",
        }
    fit_root = stage_root / "motion-codebook-fit"
    fit_root.mkdir(parents=True, exist_ok=True)
    fits: list[dict[str, Any]] = []
    for index, count in enumerate((2, 4, 8, 16, 32), start=1):
        path = fit_root / f"k{count}.json"
        if path.exists():
            fitted = _load_json(path)
        else:
            if time.time() >= deadline:
                break
            fitted = _fit_motion_codebook(development, count)
            ar._atomic_json(path, fitted)
        fits.append(fitted)
        status(
            "running", "fit-abstract-motion-codebooks", completed=index,
            total=5, latest_checkpoint=f"k{count}",
        )
    if not fits:
        return {
            "state": "budget_truncated",
            "stage_gate": False,
            "skipped_reason": "hard deadline reached before motion fitting",
            "final_audit_trajectory_state": "untouched",
        }
    eligible = [
        fitted for fitted in fits
        if int(fitted["model"]["payload_bits"]) <= contract.abstract_payload_bits_maximum
    ]
    selected = max(
        eligible or fits,
        key=lambda row: (float(row["selection_score"]), -int(row["model"]["payload_bits"])),
    )
    model = selected["model"]
    conditions = (
        "intact",
        "phase_scrub",
        "translation_scrub",
        "zero",
        "shuffle",
        "shape_only",
        "direction_only",
        "opposite_direction",
        "read_disabled",
        "write_disabled",
        "no_renewal",
        "ablation",
        "matching_rescue",
        "opposite_rescue",
    )
    pair_rows: list[dict[str, Any]] = []
    for pair_index, pair in enumerate(validation, start=1):
        if time.time() >= deadline:
            break
        results = {
            f"{direction}:{condition}": _motion_abstract_lineage(
                model, pair, direction, condition
            )
            for direction in ("forward", "opposite")
            for condition in conditions
        }
        pair_rows.append(
            {"pair_id": pair["pair_id"], "rule": pair["rule"], "conditions": results}
        )
        status(
            "running", "validate-abstract-motion-code", completed=pair_index,
            total=len(validation), payload_bits=model["payload_bits"],
        )
    complete = len(pair_rows) == len(validation)
    recovery = {
        condition: float(
            np.mean(
                [
                    result["final_correct_direction"]
                    for row in pair_rows
                    for key, result in row["conditions"].items()
                    if key.endswith(f":{condition}")
                ]
            )
        ) if pair_rows else 0.0
        for condition in conditions
    }
    intact_rows = [
        result for row in pair_rows for key, result in row["conditions"].items()
        if key.endswith(":intact")
    ]
    form = float(
        np.mean(
            [generation["form_accuracy"] for result in intact_rows for generation in result["generations"]]
        )
    ) if intact_rows else 0.0
    final_recovery = recovery["intact"]
    phase_recovery = recovery["phase_scrub"]
    translation_recovery = recovery["translation_scrub"]
    margins: list[float] = []
    for row in pair_rows:
        for direction in ("forward", "opposite"):
            correct = row["conditions"][f"{direction}:intact"]["generations"][-1]["direction_similarity"]
            opposite = row["conditions"][f"{direction}:opposite_direction"]["generations"][-1]["direction_similarity"]
            margins.append(float(correct - opposite))
    direction_margin = float(np.mean(margins)) if margins else 0.0
    causal = bool(
        recovery["intact"] > recovery["zero"]
        and recovery["intact"] > recovery["read_disabled"]
        and recovery["intact"] > recovery["no_renewal"]
        and recovery["matching_rescue"] > recovery["opposite_rescue"]
    )
    gate = bool(
        complete
        and bank.get("stage_gate")
        and int(model["payload_bits"]) <= contract.abstract_payload_bits_maximum
        and form >= contract.dynamic_form_minimum
        and direction_margin >= contract.dynamic_direction_margin_minimum
        and final_recovery >= contract.dynamic_recovery_minimum
        and phase_recovery >= contract.dynamic_recovery_minimum
        and translation_recovery >= contract.dynamic_recovery_minimum
        and causal
    )
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": gate,
        "development_pair_count": len(development),
        "validation_pair_count": len(validation),
        "selected_model": model,
        "candidate_summaries": [
            {
                "model_id": fitted["model"]["model_id"],
                "model_digest": fitted["model"]["model_digest"],
                "payload_bits": fitted["model"]["payload_bits"],
                "cross_validation": fitted["cross_validation"],
                "selection_score": fitted["selection_score"],
            }
            for fitted in fits
        ],
        "form_accuracy_mean": form,
        "direction_margin_mean": direction_margin,
        "four_generation_correct_direction_recovery_fraction": final_recovery,
        "phase_scrub_recovery_fraction": phase_recovery,
        "translation_scrub_recovery_fraction": translation_recovery,
        "control_recovery": recovery,
        "causal_specificity_gate": causal,
        "literal_occupancy_payload_removed": True,
        "canonical_phase_every_boundary": True,
        "meaningful_payload_bits": model["payload_bits"],
        "codec": "four-share bitwise XOR",
        "pair_results": pair_rows,
        "stage6l_literal_carrier_reference": _load_json(stage6l_root / "stage6l/MOTION_RESULTS.json"),
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(stage_root / "MOTION_ABSTRACTION_RESULTS.json", result)
    return result


def _campaign_result(
    output: Path,
    design_digest: str,
    profile_name: str,
    localization: dict[str, Any],
    latent: dict[str, Any],
    closed_loop: dict[str, Any],
    support: dict[str, Any],
    narrow: dict[str, Any],
    endurance: dict[str, Any],
    motion: dict[str, Any],
) -> dict[str, Any]:
    phases = (localization, latent, closed_loop, support, narrow, motion)
    complete = all(row.get("state") == "complete" for row in phases)
    narrow_gate = bool(narrow.get("stage_gate", False))
    motion_gate = bool(motion.get("stage_gate", False))
    if profile_name == "smoke" and complete:
        verdict = "SMOKE_PATH_VALIDATED"
    elif not complete:
        verdict = "INCONCLUSIVE_RESOURCE_LIMIT"
    elif narrow_gate and motion_gate:
        verdict = "NARROW_LATENT_AND_ABSTRACT_MOTION_PH"
    elif narrow_gate:
        verdict = "NARROW_LATENT_CA_PH_ONLY"
    elif motion_gate:
        verdict = "ABSTRACT_MOTION_CA_HEREDITY_ONLY"
    elif motion.get("four_generation_correct_direction_recovery_fraction", 0.0) >= 0.60:
        verdict = "SPATIAL_MOTION_COMPRESSION_ONLY"
    else:
        verdict = "LATENT_AND_ABSTRACT_REGENERATION_NOT_CAUSAL"
    result = {
        "experiment": "ca_motif_latent_regeneration_stage_6m",
        "design_digest": design_digest,
        "profile_name": profile_name,
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(narrow_gate or motion_gate),
        "scientific_claim": profile_name == "reference",
        "verdict": verdict,
        "localization_gate": bool(localization.get("stage_gate", False)),
        "latent_code_gate": bool(latent.get("stage_gate", False)),
        "closed_loop_gate": bool(closed_loop.get("stage_gate", False)),
        "support_screen_gate": bool(support.get("stage_gate", False)),
        "narrow_latent_ph_gate": narrow_gate,
        "abstract_motion_heredity_gate": motion_gate,
        "mechanism_level_generality_gate": bool(narrow_gate and motion_gate),
        "qualified_narrow_candidate_ids": narrow.get("qualified_candidate_ids", []),
        "original_final_reserve_opened": False,
        "final_audit_pair_count": 62,
        "final_audit_trajectory_state": "untouched",
        "claim_boundary": (
            "Engineered synthetic CA heredity only. Narrow latent and abstract "
            "motion claims are independent and neither implies biological life, "
            "human memory, consciousness, or agency."
        ),
        "phase_results": {
            "localization": localization,
            "latent_fit": latent,
            "closed_loop": closed_loop,
            "support_screen": support,
            "narrow_validation": narrow,
            "narrow_endurance": endurance,
            "motion_abstraction": motion,
        },
    }
    ar._atomic_json(output / "RESULTS.json", result)
    ar._atomic_json(
        output / "STAGE_DECISION.json",
        {
            "experiment": result["experiment"],
            "design_digest": design_digest,
            "state": result["state"],
            "verdict": verdict,
            "stage_gate": result["stage_gate"],
            "next_step": (
                "a separate explicitly authorized final-reserve stage is required"
                if narrow_gate else
                "retain the sealed reserve and follow the timing/locality decomposition"
            ),
            "final_audit_trajectory_state": "untouched",
        },
    )
    best = localization.get("best_local") or {}
    best_cv = best.get("cross_validation", {})
    report = (
        "# Stage 6M latent and abstract regeneration\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"Best local history accuracy: `{best_cv.get('history_specific_accuracy_mean')}`; "
        f"narrow latent causal gate: `{narrow_gate}`; abstract motion gate: `{motion_gate}`. "
        "The protected 62-pair reserve was neither loaded nor simulated.\n"
    )
    lay = (
        "# Lay summary\n\n"
        "This round asked whether a daughter can read a short memory code from its "
        "own activity and use a fixed decoder to rebuild the useful inherited note. "
        "It separately asked whether a moving pattern can pass only an abstract shape "
        "and direction code, rather than a copied picture.\n\n"
        f"The registered outcome is **{verdict}**.\n"
    )
    ar._atomic_text(output / "REPORT.md", report)
    ar._atomic_text(output / "LAY_SUMMARY.md", lay)
    ar._atomic_text(output / "COMPLETE", "complete\n")
    return result


def _update_discovery_log(result: dict[str, Any], output: Path) -> None:
    if result.get("profile_name") != "reference":
        return
    path = ROOT / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"
    if not path.exists():
        return
    marker = f"Stage 6M design `{result['design_digest']}`"
    prior = path.read_text(encoding="utf-8")
    if marker in prior:
        return
    entry = (
        "\n\n## Stage 6M: latent memory and abstract carrier regeneration\n\n"
        f"{marker} completed with verdict **{result['verdict']}**. The campaign "
        "localized history signal in retained visible traces, fitted compact "
        "encoder/decoder writers, tested closed-loop renewal on donor-disjoint "
        "procedural pairs, and independently replaced the motion snapshot with a "
        "phase/translation-neutral discrete code. The protected 62-pair reserve "
        "remained untouched.\n\n"
        f"Artifacts: `{output}`. Protocol: `CA_MOTIF_LATENT_REGENERATION_PROTOCOL.md`. "
        "Implementation: `plastic_ca/motif_latent_regeneration.py`.\n"
    )
    ar._atomic_text(path, prior.rstrip() + entry)


def _empty(reason: str) -> dict[str, Any]:
    return {
        "state": "complete",
        "stage_gate": False,
        "skipped_reason": reason,
        "final_audit_trajectory_state": "untouched",
    }


def run_motif_latent_regeneration(
    output: Path,
    *,
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
    """Run Stage 6M with no code path to the original final reserve."""

    ar.require_pinned_numpy()
    if profile_name not in PROFILES:
        raise ValueError(f"unknown Stage-6M profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6M workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6M max-hours must be in (0, 8]")
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    stage6l_root = stage6l_root.resolve()
    # Parent truth is checked before creating an output directory.
    _parent_integrity(stage6l_root)
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
            output, profile_name, stage6l_root, max_hours, resume=resume
        )
        status = _status_writer(output, profile_name, campaign, active, workers)
        status("running", "frozen-stage6l-design-and-traces-verified")
        active[0] = "integrity"
        _write_phase(
            output,
            "integrity",
            design_digest,
            integrity | {"next_phase": "localization"},
            "# Stage 6M integrity\n\nStage 6L, all 112 retained visible traces, and the untouched final-reserve boundary were hash-verified.",
            "# Lay summary\n\nThe previous result and every reused observation were accounted for before fitting anything new.",
        )
        stage_root = output / "stage6m"
        ancestry_integrity = il._parent_integrity(
            stage6k_root.resolve(), stage6j_root.resolve(), stage6i_root.resolve(), stage6h_root.resolve()
        )
        il_profile = il.InverseDistillationProfile(
            profile.development_pairs,
            profile.procedural_validation_pairs,
            profile.trace_replicates,
            profile.validation_replicates,
            profile.dagger_rounds,
            profile.dagger_base_models,
            profile.mover_seeds_per_rule,
            profile.mover_development_pairs,
            profile.mover_validation_pairs,
            profile.bootstrap_resamples,
        )
        frozen, cohorts, nested, writer_contract, templates = il._reconstruct_cohorts(
            stage_root,
            profile_name,
            il_profile,
            ancestry_integrity,
            stage6j_root.resolve(),
            stage6i_root.resolve(),
            stage6h_root.resolve(),
            roots,
        )
        cohort_ledger = _load_json(stage_root / "COHORTS.json")
        if profile_name == "reference":
            if cohort_ledger["procedural_pair_ids_sha256"] != integrity["procedural_pair_ids_sha256"]:
                raise ValueError("Stage-6M procedural validation identities changed from Stage 6L")
        else:
            # Engineering smoke must not consume any of the 16 scientific
            # procedural identities.  Reuse already-exposed development pairs
            # solely to exercise the conditional validation route.
            cohorts["procedural_validation"] = list(
                cohorts["development"][-profile.procedural_validation_pairs:]
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
            stage_root, stage6h_root.resolve(), stage6br_root.resolve(), design_digest
        )
        all_retained_rows = _retained_rows(stage6l_root)
        wanted_ids = {
            str(pair["pair_id"]) for pair in cohorts["development"][: profile.development_pairs]
        }
        base_rows = [
            row for row in all_retained_rows if str(row["pair_id"]) in wanted_ids
        ]
        retained_ids = {str(row["pair_id"]) for row in base_rows}
        development_pairs = [
            pair for pair in cohorts["development"] if str(pair["pair_id"]) in retained_ids
        ]
        if len(development_pairs) != profile.development_pairs:
            raise ValueError("retained Stage-6L trace/pair reconstruction mismatch")

        active[0] = "localization"
        localization, settings = _run_localization(
            stage_root, base_rows, profile, contract, design_digest,
            resume=resume, deadline=float(campaign["exploration_deadline_unix"]), status=status,
        )
        _write_phase(
            output, "localization", design_digest,
            localization | {"next_phase": "latent-fit"},
            "# Stage 6M signal localization\n\nPair-blocked timing, radius, symmetry, consensus, and whole-board comparisons located the readable history signal without opening new trajectories.",
            "# Lay summary\n\nWe checked when and where the daughter carries the clearest trace of its history before choosing a memory reader.",
        )

        active[0] = "latent-fit"
        if localization.get("stage_gate") and settings:
            latent, selected_specs = _run_latent_search(
                stage_root, base_rows, settings, profile_name, profile, contract,
                design_digest, resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]), status=status,
            )
        else:
            latent, selected_specs = _empty("no local history setting passed"), []
        _write_phase(
            output, "latent-fit", design_digest,
            latent | {"next_phase": "closed-loop"},
            "# Stage 6M latent fitting\n\nReduced-rank and discrete history codes were compared by pair-blocked recognition and decoded-field behavior, not by exact carrier imitation alone.",
            "# Lay summary\n\nThe reader tried to identify a short history code and let a fixed decoder rebuild the longer instruction note.",
        )

        active[0] = "closed-loop"
        if latent.get("stage_gate") and selected_specs:
            closed_loop, models = _run_closed_loop(
                stage_root, source, base_rows, development_pairs, selected_specs,
                profile_name, profile, templates, frozen, writer_contract, contract,
                design_digest, workers=workers, resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]), status=status,
            )
        else:
            closed_loop, models = _empty("no latent model passed pair-blocked fitting"), []
        # The old exact-carrier leaders remain explicitly non-promotable.  Their
        # retained Stage-6L scores are included as a diagnostic baseline without
        # allowing them into Stage-6M validation.
        old_fit = _load_json(stage6l_root / "stage6l/initial-writer-fit/RESULTS.json")
        old_ranked = sorted(
            old_fit.get("candidate_summaries", {}).items(),
            key=lambda item: (
                -float(item[1].get("selection_score", 0.0)), item[0]
            ),
        )[:2]
        closed_loop["legacy_exact_carrier_nonpromotable"] = [
            {"candidate_id": key, "summary": value, "promotable": False}
            for key, value in old_ranked
        ]
        _write_phase(
            output, "closed-loop", design_digest,
            closed_loop | {"next_phase": "support-screen"},
            "# Stage 6M closed-loop renewal\n\nFold-specific latent writers generated only their held-out folds through three rollout-aggregation rounds. Exact-carrier leaders remained diagnostic and non-promotable.",
            "# Lay summary\n\nThe compact reader practised on the imperfect daughters it actually creates, without learning from its own test cases.",
        )

        active[0] = "support-screen"
        if closed_loop.get("stage_gate") and models:
            support, candidates = _run_support_screen(
                stage_root, source, models, development_pairs, profile_name,
                profile, templates, frozen, writer_contract, contract,
                design_digest, workers=workers, resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]), status=status,
            )
        else:
            support, candidates = _empty("no closed-loop latent writer passed"), []
        _write_phase(
            output, "support-screen", design_digest,
            support | {"next_phase": "narrow-validation"},
            "# Stage 6M support and timing screen\n\nEarly/late writing, support length, write span, and rehearsal were selected on exposed pairs with a causal one-boundary contrast.",
            "# Lay summary\n\nWe chose when the daughter should write its new note and required the note to make a measurable difference before any new pair was opened.",
        )

        active[0] = "narrow-validation"
        if support.get("stage_gate") and candidates:
            narrow, narrow_rows = _run_narrow_validation(
                stage_root, candidates, cohorts["procedural_validation"], profile,
                nested, templates, frozen, writer_contract, contract,
                design_digest, profile_name, workers=workers, resume=resume,
                deadline=float(campaign["hard_deadline_unix"]), status=status,
            )
        else:
            narrow, narrow_rows = _empty("no frozen latent writer reached procedural validation"), []
            narrow["qualified_candidate_ids"] = []
        endurance = _run_narrow_endurance(
            stage_root, candidates, narrow.get("qualified_candidate_ids", []),
            cohorts["procedural_validation"], profile, templates, frozen,
            writer_contract, contract, design_digest, workers=workers,
            resume=resume, deadline=float(campaign["hard_deadline_unix"]), status=status,
        ) if candidates else _empty("no frozen latent writer")
        narrow["endurance"] = endurance
        _write_phase(
            output, "narrow-validation", design_digest,
            narrow | {"next_phase": "motion-abstraction"},
            "# Stage 6M narrow validation\n\nSealed compact writers faced the complete intervention ladder on the 16 donor-disjoint procedural pairs, followed by descriptive generation-12/16 endurance only after qualification.",
            "# Lay summary\n\nA real inherited memory must help unfamiliar daughters, vanish when erased or unread, return with the matching rescue, and renew itself.",
        )

        active[0] = "motion-abstraction"
        motion = _run_motion_abstraction(
            stage_root, stage6l_root, profile, contract,
            deadline=float(campaign["hard_deadline_unix"]), status=status,
        )
        _write_phase(
            output, "motion-abstraction", design_digest,
            motion | {"next_phase": "adjudicate"},
            "# Stage 6M motion abstraction\n\nFresh movers inherited a direction-neutral canonical-shape index plus three orientation bits; phase, translation, ablation, rescue, and renewal controls distinguished abstraction from snapshot ferrying.",
            "# Lay summary\n\nInstead of passing a picture of the moving pattern, the parent passed a tiny shape name and direction, and the daughter rebuilt a fresh copy in a new place and phase.",
        )

        active[0] = "adjudicate"
        result = _campaign_result(
            output, design_digest, profile_name, localization, latent,
            closed_loop, support, narrow, endurance, motion,
        )
        _write_phase(
            output, "adjudicate", design_digest, result,
            "# Stage 6M adjudication\n\nNarrow latent PH and abstract moving-form heredity are reported independently. No outcome opens the original reserve.",
            "# Lay summary\n\nThe conclusion keeps compact statistical memory separate from abstract motion and from ordinary pattern copying.",
        )
        _update_discovery_log(result, output)
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
    "DEFAULT_STAGE6L_ROOT",
    "PHASES",
    "PROFILES",
    "LatentRegenerationContract",
    "LatentRegenerationProfile",
    "_bit_codec_roundtrip",
    "_canonicalize_motion_phase",
    "_fit_latent_model",
    "_localization_specs",
    "_orientation_from_velocity",
    "_parent_integrity",
    "run_motif_latent_regeneration",
]
