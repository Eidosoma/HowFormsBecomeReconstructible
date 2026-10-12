"""Stage-6H repair of generational dialect drift in the local CA transducer.

Stage 6G showed that a frozen local translator writes an accurate first
replacement carrier but that its self-generated daughters leave a different
trace.  This clean-room follow-up learns only from the already exposed Stage-6G
screen cohort, freezes every candidate, and then uses previously untouched
validation, qualification, endurance, and final cohorts.
"""

from __future__ import annotations

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
from . import motif_consumptive_renewal as cr
from . import motif_local_transduction as lt
from . import motif_phenotype_bridge as pb


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_GENERATIONAL_TRANSDUCTION_PROTOCOL.md"
DEFAULT_STAGE6G_ROOT = ROOT / "results/ca-motif-local-transduction-stage-6g"
PHASES = (
    "integrity",
    "forensics",
    "develop",
    "validate",
    "qualify",
    "endurance",
    "adjudicate",
)
CLAIM_GROUPS = (
    "label-free-full",
    "assisted-full",
    "label-free-compressed",
    "assisted-compressed",
)


@dataclass(frozen=True)
class GenerationalProfile:
    training_pairs: int
    training_replicates: int
    validation_pairs: int
    validation_replicates: int
    qualification_pairs: int
    qualification_replicates: int
    endurance_pairs: int
    endurance_replicates: int
    final_pairs: int
    final_replicates: int
    bootstrap_resamples: int
    candidate_limit: int


PROFILES = {
    # Keep all four preregistered claim groups represented even in smoke runs.
    "smoke": GenerationalProfile(2, 1, 2, 1, 2, 1, 1, 1, 2, 1, 100, 16),
    "reference": GenerationalProfile(
        16, 4, 16, 4, 16, 8, 8, 4, 62, 4, 10_000, 16
    ),
}


@dataclass(frozen=True)
class GenerationalTransductionContract(lt.LocalTransductionContract):
    implementation_version: str = "ca-motif-generational-transduction-v1"
    namespace: str = "plastic-ca-motif-generational-transduction-v1"
    training_generation_start: int = 5
    training_generation_end: int = 12
    rollout_aggregation_rounds: int = 3
    maximum_promotable_writers: int = 16
    compressed_joint_accuracy_minimum: float = 0.80
    exploration_stop_hours: float = 5.5
    max_hours: float = 8.0

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "training_generations": (
                    self.training_generation_start,
                    self.training_generation_end,
                ),
                "rollout_aggregation_rounds": self.rollout_aggregation_rounds,
                "maximum_promotable_writers": self.maximum_promotable_writers,
                "compressed_joint_accuracy_minimum": self.compressed_joint_accuracy_minimum,
                "claim_groups": CLAIM_GROUPS,
                "runtime_environment_labels": False,
                "runtime_generation_index": False,
                "runtime_pair_identity": False,
                "runtime_incoming_payload": False,
                "somatic_decoder_channel_matched": True,
                "full_and_compressed_claims_separate": True,
            }
        )
        return payload


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _checkpoint_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "checkpoints").glob("*.json")):
        rows.append(_load_json(path)["result"])
    return rows


def _parent_integrity(stage6g_root: Path) -> dict[str, Any]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "MANIFEST.json",
        "TRANSDUCER_CANDIDATES.json",
        "SEALED_TRANSLATORS.json",
        "screen/RESULTS.json",
        "stage6g/COHORTS.json",
        "stage6g/screen-trajectories-stage6e/stage_summary.json",
        "COMPLETE",
    )
    missing = [stage6g_root / name for name in required if not (stage6g_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6G artifacts: {missing}")
    result = _load_json(stage6g_root / "RESULTS.json")
    status = _load_json(stage6g_root / "STATUS.json")
    cohorts = _load_json(stage6g_root / "stage6g/COHORTS.json")
    screen = _load_json(stage6g_root / "screen/RESULTS.json")["subcampaign_result"]
    if result.get("verdict") != "DECODABLE_NOT_TRANSDUCIBLE":
        raise ValueError("Stage-6H requires DECODABLE_NOT_TRANSDUCIBLE")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6G is incomplete")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6G final reserve is not untouched")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6G cohort reserve is not untouched")
    checkpoint_paths = sorted(
        (stage6g_root / "stage6g/screen-trajectories-stage6e/checkpoints").glob(
            "*.json"
        )
    )
    if len(checkpoint_paths) != 448 or screen.get("completed_trajectories") != 448:
        raise ValueError("Stage-6H requires all 448 Stage-6G screen checkpoints")
    inventory = [
        {
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": ar._sha256(path),
        }
        for path in checkpoint_paths
    ]
    development_ids = cohorts["development_pair_ids"]
    if [len(development_ids[name]) for name in ("bridge", "screen", "qualification", "endurance")] != [8, 16, 32, 8]:
        raise ValueError("Stage-6G developmental cohort allocation changed")
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "required_hashes": {name: ar._sha256(stage6g_root / name) for name in required},
        "screen_checkpoint_count": len(inventory),
        "screen_checkpoint_inventory_digest": _digest(inventory),
        "development_pair_ids": development_ids,
        "final_pair_count": int(cohorts["final_audit_pair_count"]),
        "final_pair_ids_sha256": cohorts["final_audit_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
    }


def _parent_generation_curve(stage6g_root: Path) -> dict[str, Any]:
    screen = _load_json(stage6g_root / "screen/RESULTS.json")["subcampaign_result"]
    assisted = [
        (candidate_id, summary)
        for candidate_id, summary in screen["candidate_summaries"].items()
        if summary.get("training_mode") == "rulebook-assisted"
        and summary.get("mechanism") == "timing-only"
    ]
    if not assisted:
        raise ValueError("Stage-6G retained no visible assisted translator")
    best_id = sorted(
        assisted,
        key=lambda item: (
            -float(item[1]["read_acquisition"].get("mean") or 0.0),
            item[0],
        ),
    )[0][0]
    rows = _checkpoint_rows(
        stage6g_root / "stage6g/screen-trajectories-stage6e"
    )
    selected = [row for row in rows if row["candidate_id"] == best_id]
    curve: dict[str, Any] = {}
    for generation in range(5, 9):
        read_values: list[float] = []
        post_values: list[float] = []
        carrier_values: list[float] = []
        proposal_values: list[float] = []
        for row in selected:
            intact = row["conditions"]["intact"]
            key = str(generation)
            read_values.append(float(intact["texture_history"][key]["read_match_mean"]))
            post_values.append(
                float(intact["texture_history"][key]["post_washout_match_mean"])
            )
            carrier_values.append(
                float(intact["carrier_history"][key]["joint_balanced_accuracy"])
            )
            proposal_values.append(
                float(intact["writer_history"][key]["proposal_mean_abs"])
            )
        curve[str(generation)] = {
            "read_match_mean": float(np.mean(read_values)),
            "post_washout_match_mean": float(np.mean(post_values)),
            "carrier_balanced_accuracy_mean": float(np.mean(carrier_values)),
            "proposal_mean_abs": float(np.mean(proposal_values)),
            "trajectory_count": len(read_values),
        }
    return {"best_parent_candidate_id": best_id, "generation_curve": curve}


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6g_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[
    GenerationalTransductionContract,
    GenerationalProfile,
    dict[str, Any],
    str,
    dict[str, Any],
]:
    contract = GenerationalTransductionContract()
    profile = PROFILES[profile_name]
    integrity = _parent_integrity(stage6g_root)
    design = {
        "experiment": "ca_motif_generational_transduction_stage_6h",
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(profile),
        "stage6g_root": str(stage6g_root.resolve()),
        "stage6g_required_hashes": integrity["required_hashes"],
        "screen_checkpoint_inventory_digest": integrity[
            "screen_checkpoint_inventory_digest"
        ],
        "cohort_route": {
            "training": "already exposed Stage-6G screen cohort",
            "validation": "first 16 previously unused Stage-6G qualification pairs",
            "qualification": "second 16 previously unused Stage-6G qualification pairs",
            "endurance": "previously unused Stage-6G endurance cohort",
            "adjudication": "62-pair protected reserve",
        },
        "candidate_allocation": {
            "label_free_full": 4,
            "label_free_compressed": 2,
            "assisted_visible_full": 5,
            "assisted_somatic_full": 3,
            "assisted_compressed": 2,
            "total": 16,
        },
        "limits": {
            "workers": 4,
            "max_hours": max_hours,
            "exploration_stop_hours": max_hours * 5.5 / 8.0,
        },
        "implementation_hashes": {
            "motif_generational_transduction.py": ar._sha256(Path(__file__)),
            "motif_phenotype_bridge.py": ar._sha256(Path(pb.__file__)),
            "protocol": ar._sha256(PROTOCOL_PATH),
        },
        "cleanroom": {
            "excluded_code": ("Wagner implementation", "Fable implementation"),
            "excluded_code_read_import_hash_execute": True,
        },
    }
    design_digest = _digest(design)
    design["design_digest"] = design_digest
    design_path = output / "DESIGN.json"
    if design_path.exists():
        if not resume:
            raise ValueError("Stage-6H output exists; use --resume")
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6H design changed during resume")
    else:
        ar._atomic_json(design_path, design)
        ar._atomic_json(
            output / "CLEANROOM_PROVENANCE.json",
            {"design_digest": design_digest, **design["cleanroom"]},
        )
    campaign_path = output / "CAMPAIGN.json"
    if campaign_path.exists():
        campaign = _load_json(campaign_path)
        if not math.isclose(float(campaign["max_hours"]), max_hours):
            raise ValueError("Stage-6H max-hours changed during resume")
    else:
        started = time.time()
        campaign = {
            "experiment": design["experiment"],
            "design_digest": design_digest,
            "started_unix": started,
            "max_hours": max_hours,
            "exploration_deadline_unix": started
            + max_hours * 5.5 / 8.0 * 3600.0,
            "hard_deadline_unix": started + max_hours * 3600.0,
            "final_audit_reserve_hours": max_hours * 2.5 / 8.0,
            "deadline_persists_across_resume": True,
        }
        ar._atomic_json(campaign_path, campaign)
    return contract, profile, campaign, design_digest, integrity


def _status_writer(
    output: Path,
    profile_name: str,
    campaign: dict[str, Any],
    active_phase: list[str],
) -> Any:
    def write(state: str, current: str, **extra: Any) -> None:
        now = time.time()
        payload = {
            "state": state,
            "stage": "ca_motif_generational_transduction_stage_6h",
            "profile": profile_name,
            "phase": active_phase[0],
            "current": current,
            "pid": os.getpid(),
            "workers_hard_max": 4,
            "started_unix": campaign["started_unix"],
            "updated_unix": now,
            "elapsed_seconds": now - float(campaign["started_unix"]),
            "deadline_remaining_seconds": max(
                0.0, float(campaign["hard_deadline_unix"]) - now
            ),
            "exploration_deadline_unix": campaign["exploration_deadline_unix"],
            "hard_deadline_unix": campaign["hard_deadline_unix"],
            "final_audit_trajectory_state": "untouched",
            **extra,
        }
        ar._atomic_json(output / "STATUS.json", payload)
        progress = (
            f" {extra['completed']}/{extra['total']}"
            if "completed" in extra and "total" in extra
            else ""
        )
        print(
            f"[{state}] stage6h-{active_phase[0]}:{current}{progress}",
            flush=True,
        )

    return write


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
        "experiment": "ca_motif_generational_transduction_stage_6h",
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
            "final_audit_trajectory_state": payload.get(
                "final_audit_trajectory_state", "untouched"
            ),
        },
    )
    ar._atomic_text(root / "REPORT.md", report.rstrip() + "\n")
    ar._atomic_text(root / "LAY_SUMMARY.md", lay.rstrip() + "\n")
    ar._atomic_text(root / "COMPLETE", "complete\n")


def _reconstruct_cohorts(
    stage_root: Path,
    profile: GenerationalProfile,
    parent_integrity: dict[str, Any],
    roots: dict[str, Path],
    *,
    auto_final_audit: bool,
) -> tuple[
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    pb.PhenotypeBridgeProfile,
    GenerationalTransductionContract,
    ar.MotifContract,
    list[dict[str, Any]],
    str,
]:
    (
        frozen,
        original,
        base_profile,
        _,
        writer_contract,
        templates,
        parent_design_digest,
    ) = pb._prepare_stage6e(
        stage_root,
        "reference",
        auto_final_audit=auto_final_audit,
        **roots,
    )
    expected = parent_integrity["development_pair_ids"]
    for name in ("bridge", "screen", "qualification", "endurance"):
        observed = [str(pair["pair_id"]) for pair in original[name]]
        if observed != list(expected[name]):
            raise ValueError(f"Stage-6H reconstructed {name} cohort changed")
    training = original["screen"][: profile.training_pairs]
    qualification_pool = original["qualification"]
    validation = qualification_pool[: profile.validation_pairs]
    qualification = qualification_pool[
        profile.validation_pairs : profile.validation_pairs
        + profile.qualification_pairs
    ]
    endurance = original["endurance"][: profile.endurance_pairs]
    cohorts = {
        "training": training,
        "screen": validation,
        "qualification": qualification,
        "endurance": endurance,
        "final": [],
    }
    used = [
        str(pair["pair_id"])
        for rows in cohorts.values()
        for pair in rows
    ]
    if len(used) != len(set(used)):
        raise AssertionError("Stage-6H development cohorts overlap")
    if set(used) & set(frozen["later_ids"]):
        raise AssertionError("Stage-6H development touched the protected reserve")
    nested_profile = replace(
        base_profile,
        screen_pairs=len(validation),
        screen_replicates=profile.validation_replicates,
        qualification_pairs=len(qualification),
        qualification_replicates=profile.qualification_replicates,
        endurance_pairs=len(endurance),
        endurance_replicates=profile.endurance_replicates,
        final_pairs=profile.final_pairs,
        final_replicates=profile.final_replicates,
        bootstrap_resamples=profile.bootstrap_resamples,
        candidate_limit=profile.candidate_limit,
    )
    ar._atomic_json(
        stage_root / "STAGE6H_COHORTS.json",
        {
            "development_pair_ids": {
                key: [str(pair["pair_id"]) for pair in rows]
                for key, rows in cohorts.items()
                if key != "final"
            },
            "training_previously_exposed": True,
            "validation_trajectories_previously_unopened": True,
            "qualification_trajectories_previously_unopened": True,
            "endurance_trajectories_previously_unopened": True,
            "final_audit_pair_count": 62,
            "final_audit_pair_ids_sha256": parent_integrity[
                "final_pair_ids_sha256"
            ],
            "final_audit_trajectory_state": "untouched",
            "final_audit_trajectories_not_loaded": True,
        },
    )
    return (
        frozen,
        cohorts,
        nested_profile,
        GenerationalTransductionContract(),
        writer_contract,
        templates,
        parent_design_digest,
    )


def _best_parent_spec(stage6g_root: Path, candidate_id: str) -> dict[str, Any]:
    registry = _load_json(stage6g_root / "TRANSDUCER_CANDIDATES.json")
    by_id = {str(row["candidate_id"]): row for row in registry["candidates"]}
    if candidate_id not in by_id:
        raise ValueError("best Stage-6G candidate is absent from its sealed registry")
    spec = json.loads(json.dumps(by_id[candidate_id]))
    spec["candidate_id"] = "stage6h-seed-stage6g-translator"
    spec["promotable"] = False
    spec["frontend"]["trace_sweeps"] = 8
    spec["frontend"]["clearance_updates"] = 1
    spec["writer_feature"] = "endpoint"
    spec["writer_transform"]["input_mode"] = "feature"
    return spec


def _materialize(
    specs: Sequence[dict[str, Any]], stage6br_root: Path
) -> list[dict[str, Any]]:
    return pb.build_writeback_candidates(
        specs,
        stage6br_root,
        maximum_candidates=max(12, len(specs)),
    )[0]


def _rollout_items(
    cohorts: Sequence[dict[str, Any]],
    models: Sequence[dict[str, Any]],
    templates: Sequence[dict[str, Any]],
    frozen: dict[str, Any],
    *,
    phase: str,
    replicates: int,
    generations: int = 12,
) -> list[dict[str, Any]]:
    items = ar._make_items(
        cohorts,
        models,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase=phase,
        replicates=replicates,
        generations=generations,
        conditions=("intact",),
        analysis_kind="training-rollout",
    )
    for item in items:
        item["retain_writer_samples"] = True
    return items


def _run_rollout(
    stage_root: Path,
    phase: str,
    cohorts: Sequence[dict[str, Any]],
    specs: Sequence[dict[str, Any]],
    templates: Sequence[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: GenerationalTransductionContract,
    reference: dict[int, dict[str, np.ndarray]],
    design_digest: str,
    status: Any,
    stage6br_root: Path,
    *,
    replicates: int,
    workers: int,
    resume: bool,
    deadline: float,
    zero_noise: bool = False,
) -> list[dict[str, Any]]:
    models = _materialize(specs, stage6br_root)
    items = _rollout_items(
        cohorts,
        models,
        templates,
        frozen,
        phase=phase,
        replicates=replicates,
    )
    active_contract = contract
    if zero_noise:
        active_contract = replace(contract, process_noise=0.0, bit_corruption=0.0)
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        phase,
        items,
        models,
        pb._phenotype_pair_task,
        writer_contract,
        active_contract,
        reference,
        design_digest,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    if not complete:
        raise TimeoutError(f"Stage-6H rollout {phase} exceeded its development budget")
    return rows


def _extract_writer_dataset(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    *,
    input_mode: str,
    generations: Sequence[int] = tuple(range(5, 13)),
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    features: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    groups: list[str] = []
    generation_labels: list[int] = []
    allowed = {int(value) for value in generations}
    for row in rows:
        if row.get("candidate_id") != candidate_id:
            continue
        samples = row["conditions"]["intact"].get("writer_samples", {})
        for generation_text, sample in samples.items():
            generation = int(generation_text)
            if generation not in allowed:
                continue
            values = np.asarray(
                sample["trace_stack"]
                if input_mode == "stack"
                else sample["writer_feature"],
                dtype=np.float32,
            )
            target = np.asarray(sample["target_patch"], dtype=np.float32)
            features.extend(values.reshape(len(values), -1))
            targets.extend(target.reshape(len(target), 16))
            groups.extend([str(row["pair_id"])] * len(values))
            generation_labels.extend([generation] * len(values))
    if not features:
        raise ValueError(f"no retained writer samples for {candidate_id}")
    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
        np.asarray(groups, dtype=str),
        np.asarray(generation_labels, dtype=np.int16),
    )


def _ridge_direct(
    features: np.ndarray, targets: np.ndarray, ridge: float
) -> tuple[np.ndarray, np.ndarray]:
    design = np.concatenate(
        (
            np.asarray(features, dtype=np.float64),
            np.ones((len(features), 1), dtype=np.float64),
        ),
        axis=1,
    )
    penalty = np.eye(design.shape[1], dtype=np.float64) * float(ridge)
    penalty[-1, -1] = 1e-8
    fitted = np.linalg.solve(
        design.T @ design + penalty,
        design.T @ np.asarray(targets, dtype=np.float64),
    )
    return fitted[:-1].astype(np.float32), fitted[-1].astype(np.float32)


def _linear_transform(
    transform_id: str,
    features: np.ndarray,
    targets: np.ndarray,
    groups: np.ndarray,
    *,
    input_mode: str = "stack",
    ridge: float = 0.1,
) -> dict[str, Any]:
    model = lt._fit_linear(features, targets, ridge, "full")
    payload = {
        "transform_id": transform_id,
        "kind": "linear",
        "input_mode": input_mode,
        "target_space": "visible-bits",
        "input_mean": model["input_mean"].tolist(),
        "input_scale": model["input_scale"].tolist(),
        "weights": model["weights"].tolist(),
        "bias": model["bias"].tolist(),
        "model_frozen": True,
        "training_pair_count": len(set(groups.tolist())),
        "training_pair_ids_sha256": hashlib.sha256(
            "\n".join(sorted(set(groups.tolist()))).encode()
        ).hexdigest(),
    }
    payload["model_sha256"] = _digest(payload)
    return payload


def _rff_transform(
    transform_id: str,
    features: np.ndarray,
    targets: np.ndarray,
    groups: np.ndarray,
    seed: int,
    *,
    hidden: int = 128,
) -> dict[str, Any]:
    mean = np.mean(features, axis=0, dtype=np.float64)
    scale = np.std(features, axis=0, dtype=np.float64)
    scale[scale < 1e-6] = 1.0
    normalized = (features.astype(np.float64) - mean) / scale
    rng = np.random.default_rng(seed)
    projection = rng.normal(
        0.0, 1.0 / math.sqrt(features.shape[1]), size=(features.shape[1], hidden)
    )
    phase = rng.uniform(0.0, 2.0 * math.pi, size=hidden)
    basis = math.sqrt(2.0 / hidden) * np.cos(normalized @ projection + phase)
    weights, bias = _ridge_direct(basis, targets, 0.1)
    payload = {
        "transform_id": transform_id,
        "kind": "rff-linear",
        "input_mode": "stack",
        "target_space": "visible-bits",
        "input_mean": mean.astype(np.float32).tolist(),
        "input_scale": scale.astype(np.float32).tolist(),
        "projection": projection.astype(np.float32).tolist(),
        "phase": phase.astype(np.float32).tolist(),
        "output_weights": weights.tolist(),
        "bias": bias.tolist(),
        "model_frozen": True,
        "training_pair_count": len(set(groups.tolist())),
        "training_pair_ids_sha256": hashlib.sha256(
            "\n".join(sorted(set(groups.tolist()))).encode()
        ).hexdigest(),
    }
    payload["model_sha256"] = _digest(payload)
    return payload


def _equivariant_transform(
    transform_id: str,
    features: np.ndarray,
    targets: np.ndarray,
    groups: np.ndarray,
) -> dict[str, Any]:
    if features.shape[1] != 16:
        raise ValueError("equivariant development requires endpoint patches")
    augmented_x: list[np.ndarray] = []
    augmented_y: list[np.ndarray] = []
    patches = features.reshape(-1, 4, 4)
    target_patches = targets.reshape(-1, 4, 4)
    for symmetry in range(8):
        augmented_x.append(pb._d4_patch(patches, symmetry).reshape(-1, 16))
        augmented_y.append(pb._d4_patch(target_patches, symmetry).reshape(-1, 16))
    model = lt._fit_linear(
        np.concatenate(augmented_x), np.concatenate(augmented_y), 0.1, "full"
    )
    payload = {
        "transform_id": transform_id,
        "kind": "equivariant-linear",
        "input_mode": "feature",
        "target_space": "visible-bits",
        "input_mean": model["input_mean"].tolist(),
        "input_scale": model["input_scale"].tolist(),
        "weights": model["weights"].tolist(),
        "bias": model["bias"].tolist(),
        "model_frozen": True,
        "training_pair_count": len(set(groups.tolist())),
        "training_pair_ids_sha256": hashlib.sha256(
            "\n".join(sorted(set(groups.tolist()))).encode()
        ).hexdigest(),
    }
    payload["model_sha256"] = _digest(payload)
    return payload


def _mixture_transform(
    transform_id: str,
    features: np.ndarray,
    targets: np.ndarray,
    groups: np.ndarray,
    generations: np.ndarray,
) -> dict[str, Any]:
    mean = np.mean(features, axis=0, dtype=np.float64)
    scale = np.std(features, axis=0, dtype=np.float64)
    scale[scale < 1e-6] = 1.0
    normalized = ((features.astype(np.float64) - mean) / scale).astype(np.float32)
    bins = ((5,), (6,), (7, 8), (9, 10, 11, 12))
    centers: list[np.ndarray] = []
    weights: list[np.ndarray] = []
    biases: list[np.ndarray] = []
    for values in bins:
        selected = np.isin(generations, values)
        if not np.any(selected):
            selected = np.ones(len(generations), dtype=np.bool_)
        centers.append(np.mean(normalized[selected], axis=0, dtype=np.float64))
        weight, bias = _ridge_direct(normalized[selected], targets[selected], 0.3)
        weights.append(weight)
        biases.append(bias)
    payload = {
        "transform_id": transform_id,
        "kind": "mixture-linear",
        "input_mode": "stack",
        "target_space": "visible-bits",
        "input_mean": mean.astype(np.float32).tolist(),
        "input_scale": scale.astype(np.float32).tolist(),
        "gate_centers": np.asarray(centers, dtype=np.float32).tolist(),
        "gate_temperature": 1.0,
        "expert_weights": np.asarray(weights, dtype=np.float32).tolist(),
        "expert_bias": np.asarray(biases, dtype=np.float32).tolist(),
        "model_frozen": True,
        "runtime_generation_index": False,
        "training_pair_count": len(set(groups.tolist())),
        "training_pair_ids_sha256": hashlib.sha256(
            "\n".join(sorted(set(groups.tolist()))).encode()
        ).hexdigest(),
    }
    payload["model_sha256"] = _digest(payload)
    return payload


def _combine_datasets(
    sources: Sequence[tuple[Sequence[dict[str, Any]], str]],
    *,
    input_mode: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    datasets = [
        _extract_writer_dataset(rows, candidate_id, input_mode=input_mode)
        for rows, candidate_id in sources
    ]
    return tuple(
        np.concatenate([dataset[index] for dataset in datasets])
        for index in range(4)
    )  # type: ignore[return-value]


def _proposal_curve(
    rows: Sequence[dict[str, Any]], candidate_id: str
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for generation in range(5, 13):
        values: list[float] = []
        for row in rows:
            if row.get("candidate_id") != candidate_id:
                continue
            sample = row["conditions"]["intact"]["writer_samples"].get(
                str(generation)
            )
            if sample:
                values.append(float(sample["proposal_bit_accuracy"]))
        result[str(generation)] = {
            "mean": float(np.mean(values)) if values else None,
            "trajectory_count": len(values),
        }
    return result


def _dialect_matrix(
    features: np.ndarray,
    targets: np.ndarray,
    generations: np.ndarray,
) -> dict[str, Any]:
    labels = sorted(set(int(value) for value in generations.tolist()))
    matrix: dict[str, Any] = {}
    distribution: dict[str, Any] = {}
    global_mean = np.mean(features, axis=0, dtype=np.float64)
    global_scale = np.std(features, axis=0, dtype=np.float64)
    global_scale[global_scale < 1e-6] = 1.0
    for train_generation in labels:
        train = generations == train_generation
        model = lt._fit_linear(features[train], targets[train], 0.1, "full")
        row: dict[str, float] = {}
        train_center = np.mean(
            (features[train] - global_mean) / global_scale,
            axis=0,
            dtype=np.float64,
        )
        distances: dict[str, float] = {}
        for test_generation in labels:
            test = generations == test_generation
            predicted = lt._predict(model, features[test])
            row[str(test_generation)] = float(
                np.mean((predicted >= 0.0) == (targets[test] >= 0.0))
            )
            test_center = np.mean(
                (features[test] - global_mean) / global_scale,
                axis=0,
                dtype=np.float64,
            )
            distances[str(test_generation)] = float(
                np.sqrt(np.mean((test_center - train_center) ** 2))
            )
        matrix[str(train_generation)] = row
        distribution[str(train_generation)] = distances
    return {
        "train_generation_by_test_generation_bit_accuracy": matrix,
        "standardized_center_distance": distribution,
        "generation_labels": labels,
    }


def _frontend(
    source: dict[str, Any], identifier: str, *, rank: int = 16
) -> dict[str, Any]:
    result = json.loads(json.dumps(source))
    result.update(
        {
            "frontend_id": identifier,
            "encoder_id": f"texture-walsh-r{rank:02d}-q04-stage6h",
            "rank": rank,
            "scale": list(result.get("scale", [1.0] * 16))[:rank],
            "read_sweeps": 40,
            "clearance_updates": 1,
            "trace_sweeps": 8,
        }
    )
    return result


def _common_spec(
    candidate_id: str,
    frontend: dict[str, Any],
    *,
    claim_tier: str,
    claim_class: str,
    selection_group: str,
    training_mode: str,
    form_scope: str,
    writer_feature: str = "mean",
    writer_source: str = "visible",
    mechanism: str = "timing-only",
    transform: dict[str, Any] | None = None,
    somatic_architecture: str = "none",
    somatic_readout: str = "mean",
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "candidate_id": candidate_id,
        "claim_tier": claim_tier,
        "claim_class": claim_class,
        "selection_group": selection_group,
        "training_mode": training_mode,
        "form_scope": form_scope,
        "compression_rank": int(frontend.get("rank", 16)),
        "mechanism": mechanism,
        "writer_source": writer_source,
        "writer_input_contract": (
            "field-readable" if writer_source == "somatic" else "visible-only"
        ),
        "writer_feature": writer_feature,
        "writer_observation_radius": "patch",
        "somatic_architecture": somatic_architecture,
        "somatic_channels": 3 if mechanism == "somatic-field" else 1,
        "somatic_retention": 0.95 if mechanism == "somatic-field" else 0.0,
        "somatic_bias": 0.60 if mechanism == "somatic-field" else 0.0,
        "somatic_readout": somatic_readout,
        "somatic_acquisition_window": 8,
        "somatic_support_sweeps": 8,
        "frontend": frontend,
        "promotable": True,
    }
    if transform is not None:
        result["writer_transform"] = transform
    return result


def _candidate_specs(
    base_frontend: dict[str, Any],
    visible_transforms: dict[str, dict[str, Any]],
    somatic_transforms: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    full = _frontend(base_frontend, "stage6h-full-r16", rank=16)
    rank8 = _frontend(base_frontend, "stage6h-compressed-r08", rank=8)
    rank4 = _frontend(base_frontend, "stage6h-compressed-r04", rank=4)
    specs: list[dict[str, Any]] = []
    for name, feature in (
        ("temporal-median", "temporal-median"),
        ("transition-vote", "transition"),
        ("temporal-autocorrelation", "autocorrelation"),
        ("multiscale-confidence", "multiscale"),
    ):
        specs.append(
            _common_spec(
                f"stage6h-label-free-full-{name}",
                full,
                claim_tier="strict",
                claim_class="label-free-full",
                selection_group="label-free-full",
                training_mode="label-free",
                form_scope="full-16-bit",
                writer_feature=feature,
            )
        )
    for rank, frontend in ((8, rank8), (4, rank4)):
        specs.append(
            _common_spec(
                f"stage6h-label-free-compressed-r{rank:02d}",
                frontend,
                claim_tier="strict",
                claim_class="label-free-compressed",
                selection_group="label-free-compressed",
                training_mode="label-free",
                form_scope=f"compressed-rank-{rank}",
                writer_feature="temporal-median",
            )
        )
    for name in ("pooled", "dagger", "rff", "equivariant", "mixture"):
        specs.append(
            _common_spec(
                f"stage6h-assisted-full-{name}",
                full,
                claim_tier="broad",
                claim_class="assisted-full",
                selection_group="assisted-full",
                training_mode="rulebook-assisted",
                form_scope="full-16-bit",
                writer_feature="endpoint" if name == "equivariant" else "mean",
                transform=visible_transforms[name],
            )
        )
    for architecture, readout in (
        ("multi-timescale-ema", "slow"),
        ("local-reservoir", "mean"),
        ("transition-eligibility", "alternating"),
    ):
        specs.append(
            _common_spec(
                f"stage6h-assisted-full-somatic-{architecture}",
                full,
                claim_tier="broad",
                claim_class="assisted-full",
                selection_group="assisted-full",
                training_mode="rulebook-assisted",
                form_scope="full-16-bit",
                writer_source="somatic",
                mechanism="somatic-field",
                transform=somatic_transforms[architecture],
                somatic_architecture=architecture,
                somatic_readout=readout,
            )
        )
    for rank, frontend in ((8, rank8), (4, rank4)):
        specs.append(
            _common_spec(
                f"stage6h-assisted-compressed-r{rank:02d}",
                frontend,
                claim_tier="broad",
                claim_class="assisted-compressed",
                selection_group="assisted-compressed",
                training_mode="rulebook-assisted",
                form_scope=f"compressed-rank-{rank}",
                transform=visible_transforms["dagger"],
            )
        )
    if len(specs) != 16 or len({row["candidate_id"] for row in specs}) != 16:
        raise AssertionError("Stage-6H candidate allocation changed")
    return specs


def _run_forensics_and_development(
    output: Path,
    stage_root: Path,
    stage6g_root: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: GenerationalProfile,
    contract: GenerationalTransductionContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    design_digest: str,
    status: Any,
    roots: dict[str, Path],
    *,
    workers: int,
    resume: bool,
    deadline: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    parent_curve = _parent_generation_curve(stage6g_root)
    seed_spec = _best_parent_spec(
        stage6g_root, parent_curve["best_parent_candidate_id"]
    )
    base_frontend = json.loads(json.dumps(seed_spec["frontend"]))
    teacher_spec = json.loads(json.dumps(seed_spec))
    teacher_spec.update(
        {
            "candidate_id": "stage6h-teacher-every-generation-control",
            "training_mode": "teacher-assisted-control",
            "promotable": False,
            "writer_transform": {
                "transform_id": "stage6h-teacher-every-generation",
                "kind": "target-ceiling",
                "target_exposed": True,
            },
        }
    )
    hybrid_spec = json.loads(json.dumps(seed_spec))
    hybrid_spec.update(
        {
            "candidate_id": "stage6h-one-step-teacher-control",
            "training_mode": "teacher-assisted-control",
            "promotable": False,
            "writer_transform": {
                "transform_id": "stage6h-one-step-teacher",
                "kind": "hybrid-ceiling",
                "ceiling_generations": [5],
                "fallback": seed_spec["writer_transform"],
                "target_exposed": True,
            },
        }
    )
    training = cohorts["training"]
    common = dict(
        stage_root=stage_root,
        cohorts=training,
        templates=templates,
        frozen=frozen,
        writer_contract=writer_contract,
        contract=contract,
        reference=frozen["stage4"]["reference"],
        design_digest=design_digest,
        status=status,
        stage6br_root=roots["stage6br_root"],
        replicates=profile.training_replicates,
        workers=workers,
        resume=resume,
        deadline=deadline,
    )
    seed_rows = _run_rollout(
        phase="forensics-seed-rollout", specs=[seed_spec], **common
    )
    teacher_rows = _run_rollout(
        phase="forensics-teacher-rollout", specs=[teacher_spec], **common
    )
    hybrid_rows = _run_rollout(
        phase="forensics-one-step-rescue", specs=[hybrid_spec], **common
    )
    zero_noise_rows = _run_rollout(
        phase="forensics-zero-noise",
        specs=[seed_spec],
        zero_noise=True,
        **common,
    )

    accumulated: list[tuple[Sequence[dict[str, Any]], str]] = [
        (seed_rows, seed_spec["candidate_id"]),
        (teacher_rows, teacher_spec["candidate_id"]),
    ]
    rollout_rounds: list[dict[str, Any]] = []
    final_dagger: dict[str, Any] | None = None
    for round_index in range(1, contract.rollout_aggregation_rounds + 1):
        x, y, groups, generations = _combine_datasets(
            accumulated, input_mode="stack"
        )
        transform = _linear_transform(
            f"stage6h-dagger-round-{round_index}", x, y, groups, ridge=0.3
        )
        final_dagger = transform
        prediction = lt._predict(
            {
                key: np.asarray(transform[key], dtype=np.float32)
                for key in ("input_mean", "input_scale", "weights", "bias")
            },
            x,
        )
        round_record = {
            "round": round_index,
            "training_sample_count": len(x),
            "training_pair_count": len(set(groups.tolist())),
            "training_bit_accuracy": float(
                np.mean((prediction >= 0.0) == (y >= 0.0))
            ),
            "model_sha256": transform["model_sha256"],
        }
        if round_index < contract.rollout_aggregation_rounds:
            round_spec = json.loads(json.dumps(seed_spec))
            round_spec.update(
                {
                    "candidate_id": f"stage6h-dagger-round-{round_index}",
                    "writer_feature": "mean",
                    "writer_transform": transform,
                    "promotable": False,
                }
            )
            round_rows = _run_rollout(
                phase=f"develop-dagger-round-{round_index}",
                specs=[round_spec],
                **common,
            )
            accumulated.append((round_rows, round_spec["candidate_id"]))
            round_record["rollout_proposal_curve"] = _proposal_curve(
                round_rows, round_spec["candidate_id"]
            )
        rollout_rounds.append(round_record)
    if final_dagger is None:
        raise AssertionError("Stage-6H DAgger fit did not run")

    stack_x, stack_y, stack_groups, stack_generations = _combine_datasets(
        accumulated, input_mode="stack"
    )
    feature_x, feature_y, feature_groups, _ = _combine_datasets(
        accumulated, input_mode="feature"
    )
    visible_transforms = {
        "pooled": _linear_transform(
            "stage6h-pooled-multigeneration",
            *_combine_datasets(
                [
                    (seed_rows, seed_spec["candidate_id"]),
                    (teacher_rows, teacher_spec["candidate_id"]),
                ],
                input_mode="stack",
            )[:3],
            ridge=0.1,
        ),
        "dagger": final_dagger,
        "rff": _rff_transform(
            "stage6h-dagger-rff",
            stack_x,
            stack_y,
            stack_groups,
            ar._hash_seed(contract.namespace, "rff"),
        ),
        "equivariant": _equivariant_transform(
            "stage6h-equvariant-endpoint",
            feature_x,
            feature_y,
            feature_groups,
        ),
        "mixture": _mixture_transform(
            "stage6h-observation-gated-dialects",
            stack_x,
            stack_y,
            stack_groups,
            stack_generations,
        ),
    }

    somatic_specs: list[dict[str, Any]] = []
    somatic_settings = (
        ("multi-timescale-ema", "slow"),
        ("local-reservoir", "mean"),
        ("transition-eligibility", "alternating"),
    )
    for architecture, readout in somatic_settings:
        spec = _common_spec(
            f"stage6h-somatic-teacher-{architecture}",
            _frontend(base_frontend, f"stage6h-somatic-teacher-{architecture}"),
            claim_tier="broad",
            claim_class="teacher-control",
            selection_group="teacher-control",
            training_mode="teacher-assisted-control",
            form_scope="full-16-bit",
            writer_source="somatic",
            mechanism="somatic-field",
            transform={
                "transform_id": f"stage6h-somatic-teacher-{architecture}",
                "kind": "target-ceiling",
                "target_exposed": True,
            },
            somatic_architecture=architecture,
            somatic_readout=readout,
        )
        spec["promotable"] = False
        somatic_specs.append(spec)
    somatic_rows = _run_rollout(
        phase="develop-somatic-channel-traces", specs=somatic_specs, **common
    )
    somatic_transforms: dict[str, dict[str, Any]] = {}
    for spec in somatic_specs:
        x, y, groups, _ = _extract_writer_dataset(
            somatic_rows, spec["candidate_id"], input_mode="stack"
        )
        architecture = str(spec["somatic_architecture"])
        transform = _linear_transform(
            f"stage6h-channel-matched-{architecture}", x, y, groups, ridge=0.3
        )
        transform["training_channel"] = f"somatic:{architecture}:{spec['somatic_readout']}"
        transform["model_sha256"] = _digest(transform)
        somatic_transforms[architecture] = transform

    specs = _candidate_specs(base_frontend, visible_transforms, somatic_transforms)
    dialect = _dialect_matrix(feature_x, feature_y, stack_generations)
    forensics = {
        "state": "complete",
        "stage_gate": True,
        "parent_generation_curve": parent_curve,
        "seed_proposal_curve": _proposal_curve(seed_rows, seed_spec["candidate_id"]),
        "teacher_proposal_curve": _proposal_curve(
            teacher_rows, teacher_spec["candidate_id"]
        ),
        "one_step_rescue_proposal_curve": _proposal_curve(
            hybrid_rows, hybrid_spec["candidate_id"]
        ),
        "zero_noise_proposal_curve": _proposal_curve(
            zero_noise_rows, seed_spec["candidate_id"]
        ),
        "generational_dialect": dialect,
        "rollout_aggregation_rounds": rollout_rounds,
        "training_pair_ids_sha256": hashlib.sha256(
            "\n".join(
                sorted(str(pair["pair_id"]) for pair in cohorts["training"])
            ).encode()
        ).hexdigest(),
        "runtime_target_exposure": False,
        "runtime_generation_index": False,
        "next_phase": "develop",
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(output / "GENERATIONAL_DIALECT_MATRIX.json", dialect)
    ar._atomic_json(
        output / "BOUNDARY_AUDIT.json",
        {
            key: value
            for key, value in forensics.items()
            if key != "generational_dialect"
        },
    )
    ar._atomic_json(
        output / "SEALED_GENERATIONAL_TRANSDUCERS.json",
        {
            "design_digest": design_digest,
            "selection_frozen_before_validation": True,
            "runtime_retraining": False,
            "candidate_count": len(specs),
            "selection_digest": _digest(specs),
            "candidates": specs,
        },
    )
    return forensics, specs


def _bootstrap(
    values: Sequence[float],
    profile: pb.PhenotypeBridgeProfile,
    contract: GenerationalTransductionContract,
    *key: Any,
) -> dict[str, Any]:
    return ar._bootstrap(
        list(values),
        profile.bootstrap_resamples,
        ar._hash_seed(contract.namespace, *key),
        contract.strict_alpha,
    )


def _compressed_summary(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
    profile: pb.PhenotypeBridgeProfile,
    contract: GenerationalTransductionContract,
    phase: str,
    base: dict[str, Any],
) -> dict[str, Any]:
    candidate_id = str(candidate["candidate_id"])
    rank = int(candidate["compression_rank"])

    def effects(condition: str, prefix: str) -> list[float]:
        return cr._effect_values(
            rows,
            candidate_id,
            condition,
            generation,
            f"{prefix}_rank{rank}_match_mean",
        )

    intact_read = effects("intact", "read")
    intact_post = effects("intact", "post_washout")
    intact_terminal = effects("intact", "terminal")
    no_rewrite = effects("no_rewrite", "read")
    active = [
        left - right for left, right in zip(intact_read, no_rewrite, strict=False)
    ]
    read_mean = float(np.mean(intact_read)) if intact_read else 0.0
    controls: dict[str, float] = {}
    for condition in (
        "no_rewrite",
        "proper_subset",
        "read_disabled",
        "acquisition_write_disabled",
        "trace_write_disabled",
        "trace_read_disabled",
        "trace_ablation",
        "trace_shuffle",
        "translator_ablation",
        "translator_weight_shuffle",
        "translator_bit_permutation",
        "translator_history_shuffle",
        "writer_spatial_shift",
        "ablate_after_g5",
        "rescue_same_enter_g6",
    ):
        values = effects(condition, "read")
        if values:
            controls[condition] = cr._ratio(float(np.mean(values)), read_mean)
    opposite = effects("rescue_opposite_enter_g6", "read")
    return {
        "rank": rank,
        "read_acquisition": _bootstrap(
            intact_read, profile, contract, phase, candidate_id, generation, "read"
        ),
        "post_washout_acquisition": _bootstrap(
            intact_post, profile, contract, phase, candidate_id, generation, "post"
        ),
        "terminal_acquisition": _bootstrap(
            intact_terminal,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "terminal",
        ),
        "active_rewrite_advantage": _bootstrap(
            active, profile, contract, phase, candidate_id, generation, "active"
        ),
        "opposite_rescue": _bootstrap(
            opposite,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "opposite",
        ),
        "control_retention": controls,
        "joint_decoder": base["joint_decoder"],
        "proper_subset_decoder": base["proper_subset_decoder"],
        "survival_mean": base["survival_mean"],
        "training_mode": str(candidate.get("training_mode", "label-free")),
        "claim_class": str(candidate["claim_class"]),
        "selection_group": str(candidate["selection_group"]),
    }


def _lower(summary: dict[str, Any]) -> float:
    interval = summary.get("ci", [None, None])
    return float(summary.get("mean") or 0.0) if interval[0] is None else float(interval[0])


def _upper(summary: dict[str, Any]) -> float:
    interval = summary.get("ci", [None, None])
    return float(summary.get("mean") or 0.0) if interval[1] is None else float(interval[1])


def _compressed_gate(
    summary: dict[str, Any],
    contract: GenerationalTransductionContract,
    *,
    qualification: bool = False,
) -> bool:
    controls = summary["control_retention"]
    required = (
        "no_rewrite",
        "proper_subset",
        "read_disabled",
        "acquisition_write_disabled",
    )
    if summary["training_mode"] == "rulebook-assisted":
        required = (*required, "translator_ablation", "translator_history_shuffle")
    gate = bool(
        float(summary["read_acquisition"].get("mean") or 0.0)
        >= contract.screen_read_minimum
        and _lower(summary["read_acquisition"]) > 0.0
        and float(summary["post_washout_acquisition"].get("mean") or 0.0)
        >= contract.screen_post_washout_minimum
        and float(summary["active_rewrite_advantage"].get("mean") or 0.0)
        >= contract.active_rewrite_minimum
        and _lower(summary["active_rewrite_advantage"]) > 0.0
        and _lower(summary["joint_decoder"])
        >= contract.compressed_joint_accuracy_minimum
        and _upper(summary["proper_subset_decoder"])
        <= contract.subset_accuracy_maximum
        and all(controls.get(condition, 1.0) <= 0.30 for condition in required)
        and summary["survival_mean"] >= contract.survival_minimum
    )
    if qualification:
        gate = bool(
            gate
            and controls.get("ablate_after_g5", 1.0) <= 0.30
            and controls.get("rescue_same_enter_g6", 0.0) >= 0.70
            and float(summary["opposite_rescue"].get("mean") or 0.0) < 0.0
        )
    return gate


def _candidate_map(
    specs: Sequence[dict[str, Any]], stage6br_root: Path
) -> dict[str, dict[str, Any]]:
    return {
        str(candidate["candidate_id"]): candidate
        for candidate in _materialize(specs, stage6br_root)
    }


def _filter_validation(
    stage_root: Path,
    result: dict[str, Any],
    specs: Sequence[dict[str, Any]],
    profile: pb.PhenotypeBridgeProfile,
    contract: GenerationalTransductionContract,
    stage6br_root: Path,
    *,
    scientific: bool,
) -> dict[str, Any]:
    rows = _checkpoint_rows(stage_root / "screen-trajectories-stage6e")
    models = _candidate_map(specs, stage6br_root)
    candidates: list[tuple[str, float]] = []
    for candidate_id, candidate in models.items():
        summary = result["candidate_summaries"].get(candidate_id)
        if summary is None:
            continue
        if candidate.get("form_scope") == "full-16-bit":
            gate = bool(summary.get("screen_gate"))
            if scientific and candidate.get("training_mode") == "rulebook-assisted":
                gate = gate and lt._translator_screen_gate(summary)
            score = float(summary["post_washout_acquisition"].get("mean") or 0.0)
        else:
            compressed = _compressed_summary(
                rows,
                candidate,
                8,
                profile,
                contract,
                "validation",
                summary,
            )
            summary["compressed_generation8"] = compressed
            gate = _compressed_gate(compressed, contract) if scientific else True
            score = float(
                compressed["post_washout_acquisition"].get("mean") or 0.0
            )
        summary["stage6h_validation_gate"] = bool(gate) if scientific else True
        if summary["stage6h_validation_gate"]:
            candidates.append((candidate_id, score))
    selected: list[str] = []
    for group in CLAIM_GROUPS:
        group_rows = [
            item
            for item in candidates
            if models[item[0]]["selection_group"] == group
        ]
        if group_rows:
            selected.append(sorted(group_rows, key=lambda item: (-item[1], item[0]))[0][0])
    if not scientific:
        # Smoke is an engineering route test; force one present member per group.
        for group in CLAIM_GROUPS:
            if any(models[candidate_id]["selection_group"] == group for candidate_id in selected):
                continue
            available = sorted(
                candidate_id
                for candidate_id in result["candidate_summaries"]
                if candidate_id in models
                and models[candidate_id]["selection_group"] == group
            )
            if available:
                selected.append(available[0])
    result["selected_candidate_ids"] = selected
    result["selected_by_claim_group"] = {
        group: [candidate_id for candidate_id in selected if models[candidate_id]["selection_group"] == group]
        for group in CLAIM_GROUPS
    }
    result["stage_gate"] = bool(selected)
    result["stage6h_scientific_gate_applied"] = scientific
    ar._atomic_json(stage_root / "screen/RESULTS.json", result)
    return result


def _filter_qualification(
    stage_root: Path,
    result: dict[str, Any],
    specs: Sequence[dict[str, Any]],
    profile: pb.PhenotypeBridgeProfile,
    contract: GenerationalTransductionContract,
    stage6br_root: Path,
    *,
    scientific: bool,
) -> dict[str, Any]:
    rows = _checkpoint_rows(stage_root / "qualification-trajectories-stage6e")
    models = _candidate_map(specs, stage6br_root)
    qualified: list[str] = []
    for candidate_id, bundle in result.get("candidate_summaries", {}).items():
        candidate = models[candidate_id]
        if candidate.get("form_scope") == "full-16-bit":
            gate = bool(bundle.get("qualification_gate"))
            generation16 = bundle["generation16"]
            if scientific and candidate.get("training_mode") == "rulebook-assisted":
                controls = generation16.get("control_retention", {})
                gate = gate and all(
                    controls.get(condition, 1.0) <= limit
                    for condition, limit in (
                        ("translator_ablation", 0.30),
                        ("translator_history_shuffle", 0.30),
                        ("translator_weight_shuffle", 0.50),
                        ("translator_bit_permutation", 0.50),
                    )
                )
        else:
            compressed8 = _compressed_summary(
                rows,
                candidate,
                8,
                profile,
                contract,
                "qualification-g8",
                bundle["generation8"],
            )
            compressed16 = _compressed_summary(
                rows,
                candidate,
                16,
                profile,
                contract,
                "qualification-g16",
                bundle["generation16"],
            )
            bundle["compressed_generation8"] = compressed8
            bundle["compressed_generation16"] = compressed16
            gate = _compressed_gate(
                compressed16, contract, qualification=True
            ) and float(compressed16["read_acquisition"].get("mean") or 0.0) >= 0.70 * float(
                compressed8["read_acquisition"].get("mean") or 0.0
            )
        bundle["stage6h_qualification_gate"] = bool(gate) if scientific else True
        if bundle["stage6h_qualification_gate"]:
            qualified.append(candidate_id)
    if not scientific:
        qualified = list(result.get("qualification_candidate_ids", []))
    result["qualified_candidate_ids"] = qualified
    result["qualified_by_claim_group"] = {
        group: [candidate_id for candidate_id in qualified if models[candidate_id]["selection_group"] == group]
        for group in CLAIM_GROUPS
    }
    result["stage_gate"] = bool(qualified)
    result["stage6h_scientific_gate_applied"] = scientific
    ar._atomic_json(stage_root / "qualify/RESULTS.json", result)
    return result


def _filter_endurance(
    stage_root: Path,
    result: dict[str, Any],
    specs: Sequence[dict[str, Any]],
    profile: pb.PhenotypeBridgeProfile,
    contract: GenerationalTransductionContract,
    stage6br_root: Path,
    *,
    scientific: bool,
) -> dict[str, Any]:
    rows = _checkpoint_rows(stage_root / "endurance-trajectories-stage6e")
    models = _candidate_map(specs, stage6br_root)
    qualification = _load_json(stage_root / "qualify/RESULTS.json")
    enduring: list[str] = []
    for candidate_id, bundle in result.get("candidate_summaries", {}).items():
        candidate = models[candidate_id]
        if candidate.get("form_scope") == "full-16-bit":
            gate = bool(bundle.get("endurance_gate"))
        else:
            lineage = [
                row
                for row in rows
                if row.get("analysis_kind") == "lineage"
                and row.get("candidate_id") == candidate_id
            ]
            compressed32 = _compressed_summary(
                lineage,
                candidate,
                32,
                profile,
                contract,
                "endurance-g32",
                bundle["generation32"],
            )
            compressed64 = _compressed_summary(
                lineage,
                candidate,
                64,
                profile,
                contract,
                "endurance-g64",
                bundle["generation64"],
            )
            scale_passes = 0
            compressed_scales: dict[str, Any] = {}
            for key, base in bundle["scale"].items():
                extent_text, scale_mode = key.split("-", 1)
                extent = int(extent_text.removeprefix("extent"))
                scale_rows = [
                    row
                    for row in rows
                    if row.get("analysis_kind") == "scale"
                    and row.get("candidate_id") == candidate_id
                    and int(row.get("extent")) == extent
                    and row.get("scale_mode") == scale_mode
                ]
                summary = _compressed_summary(
                    scale_rows,
                    candidate,
                    16,
                    profile,
                    contract,
                    f"endurance-{key}",
                    base,
                )
                passed = bool(
                    float(summary["read_acquisition"].get("mean") or 0.0) > 0.0
                    and summary["control_retention"].get("no_rewrite", 1.0)
                    <= 0.30
                )
                scale_passes += int(passed)
                compressed_scales[key] = summary | {"scale_gate": passed}
            qualification_bundle = qualification["candidate_summaries"][candidate_id]
            q16 = qualification_bundle["compressed_generation16"]
            base_effect = float(q16["read_acquisition"].get("mean") or 0.0)
            rule_passes = 0
            compressed_rules: dict[str, Any] = {}
            for rule in pb.RULE_STRESS_PANEL:
                rule_rows = [
                    row
                    for row in rows
                    if row.get("analysis_kind") == "rule-stress"
                    and row.get("candidate_id") == candidate_id
                    and int(row.get("rule")) == rule
                ]
                if not rule_rows:
                    continue
                summary = _compressed_summary(
                    rule_rows,
                    candidate,
                    16,
                    profile,
                    contract,
                    f"endurance-rule-{rule}",
                    bundle["generation64"],
                )
                passed = bool(
                    rule != 70366
                    and float(summary["read_acquisition"].get("mean") or 0.0)
                    >= 0.70 * base_effect
                    and _lower(summary["read_acquisition"]) > 0.0
                )
                rule_passes += int(passed)
                compressed_rules[str(rule)] = summary | {"rule_gate": passed}
            bundle["compressed_generation32"] = compressed32
            bundle["compressed_generation64"] = compressed64
            bundle["compressed_scale"] = compressed_scales
            bundle["compressed_rule_stress"] = compressed_rules
            bundle["compressed_scale_passes"] = scale_passes
            bundle["compressed_related_rules_passed"] = rule_passes
            gate = bool(
                float(compressed32["read_acquisition"].get("mean") or 0.0)
                >= contract.endurance_generation32_minimum
                and float(compressed64["read_acquisition"].get("mean") or 0.0)
                >= contract.endurance_generation64_minimum
                and _lower(compressed64["joint_decoder"])
                >= contract.compressed_joint_accuracy_minimum
                and compressed64["control_retention"].get("no_rewrite", 1.0)
                <= contract.endurance_no_rewrite_maximum
                and scale_passes >= 5
                and rule_passes >= 4
            )
        bundle["stage6h_endurance_gate"] = bool(gate) if scientific else True
        if bundle["stage6h_endurance_gate"]:
            enduring.append(candidate_id)
    if not scientific:
        enduring = list(result.get("endurance_candidate_ids", []))
    result["enduring_candidate_ids"] = enduring
    result["enduring_by_claim_group"] = {
        group: [candidate_id for candidate_id in enduring if models[candidate_id]["selection_group"] == group]
        for group in CLAIM_GROUPS
    }
    result["stage_gate"] = bool(enduring)
    result["stage6h_scientific_gate_applied"] = scientific
    ar._atomic_json(stage_root / "endurance/RESULTS.json", result)
    return result


def _filter_adjudication(
    stage_root: Path,
    result: dict[str, Any],
    specs: Sequence[dict[str, Any]],
    profile: pb.PhenotypeBridgeProfile,
    contract: GenerationalTransductionContract,
    stage6br_root: Path,
    *,
    scientific: bool,
) -> dict[str, Any]:
    if not result.get("candidate_summaries"):
        return result
    rows = _checkpoint_rows(stage_root / "final-audit-trajectories-stage6e")
    models = _candidate_map(specs, stage6br_root)
    confirmed: list[str] = []
    final_contract = replace(contract, strict_alpha=contract.final_strict_alpha)
    for candidate_id, bundle in result["candidate_summaries"].items():
        candidate = models[candidate_id]
        if candidate.get("form_scope") == "full-16-bit":
            gate = bool(bundle.get("final_gate"))
        else:
            compressed: dict[str, Any] = {}
            for generation in (8, 16, 64):
                compressed[str(generation)] = _compressed_summary(
                    rows,
                    candidate,
                    generation,
                    profile,
                    final_contract,
                    f"final-g{generation}",
                    bundle[f"generation{generation}"],
                )
            bundle["compressed"] = compressed
            gate = bool(
                _compressed_gate(
                    compressed["64"], final_contract, qualification=True
                )
                and float(
                    compressed["64"]["read_acquisition"].get("mean") or 0.0
                )
                >= contract.endurance_generation64_minimum
                and _lower(compressed["64"]["joint_decoder"])
                >= contract.compressed_joint_accuracy_minimum
            )
        bundle["stage6h_final_gate"] = bool(gate) if scientific else True
        if bundle["stage6h_final_gate"]:
            confirmed.append(candidate_id)
    result["confirmed_candidate_ids"] = confirmed
    result["confirmed_claim_classes"] = sorted(
        {str(models[candidate_id]["claim_class"]) for candidate_id in confirmed}
    )
    result["stage_gate"] = bool(confirmed)
    result["stage6h_scientific_gate_applied"] = scientific
    ar._atomic_json(stage_root / "adjudicate/RESULTS.json", result)
    return result


def _prepare_registry(
    stage_root: Path,
    specs: Sequence[dict[str, Any]],
    design_digest: str,
) -> None:
    selection_digest = _digest(list(specs))
    ar._atomic_json(
        stage_root / "WRITEBACK_CANDIDATES.json",
        {
            "design_digest": design_digest,
            "selection_digest": selection_digest,
            "selection_frozen_before_screen": True,
            "selection_frozen_before_validation": True,
            "promotable_count": len(specs),
            "maximum_candidates": 16,
            "runtime_retraining": False,
            "runtime_target_labels": False,
            "runtime_generation_index": False,
            "candidates": list(specs),
        },
    )
    bridge_root = stage_root / "bridge"
    bridge_root.mkdir(parents=True, exist_ok=True)
    ar._atomic_json(
        bridge_root / "RESULTS.json",
        {
            "experiment": "ca_motif_phenotype_bridge_stage_6e",
            "design_digest": design_digest,
            "phase": "bridge",
            "state": "complete",
            "stage_gate": True,
            "selection_digest": selection_digest,
            "generational_transduction_registry": True,
            "final_audit_trajectory_state": "untouched",
        },
    )
    ar._atomic_text(bridge_root / "COMPLETE", "complete\n")


def _run_development(
    output: Path,
    stage_root: Path,
    profile_name: str,
    specs: Sequence[dict[str, Any]],
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: pb.PhenotypeBridgeProfile,
    contract: GenerationalTransductionContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    design_digest: str,
    roots: dict[str, Path],
    campaign: dict[str, Any],
    status: Any,
    active_phase: list[str],
    *,
    workers: int,
    resume: bool,
    auto_final_audit: bool,
) -> dict[str, Any]:
    _prepare_registry(stage_root, specs, design_digest)
    common = dict(
        output=stage_root,
        frozen=frozen,
        cohorts=cohorts,
        profile=profile,
        contract=contract,
        writer_contract=writer_contract,
        templates=templates,
        design_digest=design_digest,
        stage6br_root=roots["stage6br_root"],
        workers=workers,
        resume=resume,
        scientific=profile_name == "reference",
        status=status,
    )
    validation_conditions = tuple(
        dict.fromkeys(
            (
                *pb.SCREEN_CONDITIONS,
                "trace_write_disabled",
                "trace_read_disabled",
                "translator_ablation",
                "translator_weight_shuffle",
                "translator_bit_permutation",
                "translator_history_shuffle",
                "writer_spatial_shift",
            )
        )
    )
    qualification_conditions = tuple(
        dict.fromkeys(
            (
                *pb.QUALIFICATION_CONDITIONS,
                "trace_ablation",
                "trace_shuffle",
                "trace_same_rescue",
                "trace_opposite_rescue",
                "writer_temporal_reverse",
                "writer_temporal_shuffle",
                "translator_ablation",
                "translator_weight_shuffle",
                "translator_bit_permutation",
                "translator_history_shuffle",
                "writer_spatial_shift",
            )
        )
    )
    endurance_conditions = tuple(
        dict.fromkeys(
            (
                *pb.ENDURANCE_CONDITIONS,
                "translator_ablation",
                "translator_history_shuffle",
                "writer_spatial_shift",
            )
        )
    )
    audit_conditions = tuple(
        dict.fromkeys(
            (
                *pb.AUDIT_CONDITIONS,
                "ablate_after_g5",
                "rescue_same_enter_g6",
                "rescue_opposite_enter_g6",
                "trace_ablation",
                "trace_same_rescue",
                "trace_opposite_rescue",
                "translator_ablation",
                "translator_weight_shuffle",
                "translator_bit_permutation",
                "translator_history_shuffle",
                "writer_spatial_shift",
            )
        )
    )
    active_phase[0] = "validate"
    validation = pb._run_screen(
        **common,
        deadline=float(campaign["exploration_deadline_unix"]),
        conditions=validation_conditions,
    )
    validation = _filter_validation(
        stage_root,
        validation,
        specs,
        profile,
        contract,
        roots["stage6br_root"],
        scientific=profile_name == "reference",
    )
    active_phase[0] = "qualify"
    qualification = pb._run_qualification(
        **common,
        deadline=float(campaign["exploration_deadline_unix"]),
        conditions=qualification_conditions,
    )
    qualification = _filter_qualification(
        stage_root,
        qualification,
        specs,
        profile,
        contract,
        roots["stage6br_root"],
        scientific=profile_name == "reference",
    )
    active_phase[0] = "endurance"
    endurance = pb._run_endurance(
        **common,
        deadline=float(campaign["exploration_deadline_unix"]),
        conditions=endurance_conditions,
    )
    endurance = _filter_endurance(
        stage_root,
        endurance,
        specs,
        profile,
        contract,
        roots["stage6br_root"],
        scientific=profile_name == "reference",
    )
    active_phase[0] = "adjudicate"
    adjudication = pb._run_adjudication(
        **common,
        deadline=float(campaign["hard_deadline_unix"]),
        auto_final_audit=auto_final_audit,
        conditions=audit_conditions,
    )
    adjudication = _filter_adjudication(
        stage_root,
        adjudication,
        specs,
        profile,
        contract,
        roots["stage6br_root"],
        scientific=profile_name == "reference",
    )
    return {
        "validate": validation,
        "qualify": qualification,
        "endurance": endurance,
        "adjudicate": adjudication,
    }


def _campaign_result(
    output: Path,
    design_digest: str,
    profile_name: str,
    forensics: dict[str, Any],
    specs: Sequence[dict[str, Any]],
    development: dict[str, Any] | None,
) -> dict[str, Any]:
    by_id = {str(row["candidate_id"]): row for row in specs}
    if development is None:
        selected = qualified = enduring = confirmed = []
        reserve = "untouched"
        verdict = "INCONCLUSIVE_RESOURCE_LIMIT"
    else:
        selected = list(development["validate"].get("selected_candidate_ids", []))
        qualified = list(
            development["qualify"].get("qualified_candidate_ids", [])
        )
        enduring = list(
            development["endurance"].get("enduring_candidate_ids", [])
        )
        confirmed = list(
            development["adjudicate"].get("confirmed_candidate_ids", [])
        )
        reserve = str(
            development["adjudicate"].get(
                "final_audit_trajectory_state", "untouched"
            )
        )
        truncated = any(
            development[phase].get("state") == "budget_truncated"
            for phase in ("validate", "qualify", "endurance", "adjudicate")
        )
        confirmed_classes = {
            str(by_id[candidate_id]["claim_class"])
            for candidate_id in confirmed
            if candidate_id in by_id
        }
        if truncated:
            verdict = "INCONCLUSIVE_RESOURCE_LIMIT"
        elif profile_name == "smoke":
            verdict = "SMOKE_PATH_VALIDATED"
        elif "label-free-full" in confirmed_classes:
            verdict = "FULL_LABEL_FREE_LOCAL_PH_CONFIRMED"
        elif "assisted-full" in confirmed_classes:
            verdict = "FULL_RULEBOOK_ASSISTED_LOCAL_PH_CONFIRMED"
        elif "label-free-compressed" in confirmed_classes:
            verdict = "COMPRESSED_LABEL_FREE_LOCAL_PH_CONFIRMED"
        elif "assisted-compressed" in confirmed_classes:
            verdict = "COMPRESSED_RULEBOOK_ASSISTED_LOCAL_PH_CONFIRMED"
        elif enduring:
            verdict = "ENDURING_REPAIR_NOT_CONFIRMED"
        elif qualified:
            verdict = "ONE_GENERATION_REPAIR_ONLY"
        elif selected:
            verdict = "GENERATIONAL_REPAIR_NOT_ENDURING"
        else:
            verdict = "GENERATIONAL_DIALECT_NOT_CORRECTED"
    confirmed_classes = sorted(
        {
            str(by_id[candidate_id]["claim_class"])
            for candidate_id in confirmed
            if candidate_id in by_id
        }
    )
    claim_verdicts = {
        group: (
            "confirmed"
            if group in confirmed_classes
            else "not-confirmed"
        )
        for group in CLAIM_GROUPS
    }
    result = {
        "experiment": "ca_motif_generational_transduction_stage_6h",
        "design_digest": design_digest,
        "state": "complete",
        "profile_name": profile_name,
        "verdict": verdict,
        "parent_verdict": "DECODABLE_NOT_TRANSDUCIBLE",
        "selected_candidate_ids": selected,
        "qualified_candidate_ids": qualified,
        "enduring_candidate_ids": enduring,
        "confirmed_candidate_ids": confirmed,
        "confirmed_claim_classes": confirmed_classes,
        "claim_verdicts": claim_verdicts,
        "stage_gate": bool(confirmed),
        "final_audit_opened": reserve in ("opened", "complete", "partial"),
        "final_audit_trajectory_state": reserve,
        "runtime_adaptation_promotable": False,
        "runtime_target_exposure": False,
        "generational_dialect_matrix_sha256": ar._sha256(
            output / "GENERATIONAL_DIALECT_MATRIX.json"
        ),
        "forensic_stage_gate": bool(forensics.get("stage_gate")),
    }
    ar._atomic_json(output / "RESULTS.json", result)
    ar._atomic_json(
        output / "STAGE_DECISION.json",
        {
            "experiment": result["experiment"],
            "design_digest": design_digest,
            "state": "complete",
            "decision": "campaign_complete",
            "stage_gate": result["stage_gate"],
            "verdict": verdict,
            "next_phase": None,
            "final_audit_trajectory_state": reserve,
        },
    )
    ar._atomic_text(
        output / "REPORT.md",
        "# Stage 6H generational dialect repair\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"Selected: {selected}\n\nQualified: {qualified}\n\n"
        f"Enduring: {enduring}\n\nConfirmed: {confirmed}\n\n"
        f"Claim verdicts: {claim_verdicts}\n",
    )
    if verdict == "FULL_LABEL_FREE_LOCAL_PH_CONFIRMED":
        lay = "A daughter repeatedly rebuilt the complete inherited form using only a hand-specified local rule."
    elif verdict == "FULL_RULEBOOK_ASSISTED_LOCAL_PH_CONFIRMED":
        lay = "A frozen multigeneration dictionary repaired the changing daughter dialect and renewed the complete form."
    elif verdict.startswith("COMPRESSED_"):
        lay = "A narrower registered component of form renewed causally, while complete-form heredity remained a separate unconfirmed claim."
    elif verdict == "GENERATIONAL_DIALECT_NOT_CORRECTED":
        lay = "Later daughters speak a different local dialect, and none of the frozen repairs turned it into a self-renewing note."
    elif verdict == "INCONCLUSIVE_RESOURCE_LIMIT":
        lay = "The registered wall clock expired before the decisive repair tests completed."
    else:
        lay = "The experiment measured how far generational dialect repair carries renewable form."
    ar._atomic_text(output / "LAY_SUMMARY.md", "# Lay summary\n\n" + lay + "\n")
    ar._atomic_json(
        output / "MANIFEST.json",
        {
            "experiment": result["experiment"],
            "design_digest": design_digest,
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "result_sha256": ar._sha256(output / "RESULTS.json"),
            "protocol_sha256": ar._sha256(PROTOCOL_PATH),
            "implementation_sha256": ar._sha256(Path(__file__)),
            "simulator_sha256": ar._sha256(Path(pb.__file__)),
        },
    )
    ar._atomic_text(output / "COMPLETE", "complete\n")
    return result


def run_motif_generational_transduction(
    output: Path,
    *,
    stage6g_root: Path = DEFAULT_STAGE6G_ROOT,
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
    auto_final_audit: bool = False,
) -> dict[str, Any]:
    """Run the sealed Stage-6H generational-transduction campaign."""

    ar.require_pinned_numpy()
    if profile_name not in PROFILES:
        raise ValueError(f"unknown Stage-6H profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6H workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6H max-hours must be in (0, 8]")
    if profile_name == "reference" and not auto_final_audit:
        raise ValueError(
            "reference Stage-6H requires automatic final-audit authorization"
        )
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ar._atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
    stage6g_root = stage6g_root.resolve()
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
    active_phase = ["prepare"]
    campaign: dict[str, Any] | None = None
    status: Any = None
    try:
        contract, stage_profile, campaign, design_digest, integrity = _prepare_campaign(
            output,
            profile_name,
            stage6g_root,
            max_hours,
            resume=resume,
        )
        status = _status_writer(output, profile_name, campaign, active_phase)
        status("running", "frozen-design-verified")
        active_phase[0] = "integrity"
        _write_phase(
            output,
            "integrity",
            design_digest,
            integrity | {"next_phase": "forensics"},
            "# Stage 6H integrity\n\nThe completed Stage-6G result, all 448 exposed checkpoints, and the untouched reserve were hashed and verified.",
            "# Lay summary\n\nThe repair starts from the exact failed loop without changing its evidence.",
        )

        stage_root = output / "stage6h"
        (
            frozen,
            cohorts,
            nested_profile,
            _,
            writer_contract,
            templates,
            _,
        ) = _reconstruct_cohorts(
            stage_root,
            stage_profile,
            integrity,
            roots,
            auto_final_audit=auto_final_audit,
        )
        active_phase[0] = "forensics"
        if resume and (output / "develop/COMPLETE").exists():
            forensics = _load_json(output / "forensics/RESULTS.json")
            specs = list(
                _load_json(output / "SEALED_GENERATIONAL_TRANSDUCERS.json")[
                    "candidates"
                ]
            )
        else:
            forensics, specs = _run_forensics_and_development(
                output,
                stage_root,
                stage6g_root,
                frozen,
                cohorts,
                stage_profile,
                contract,
                writer_contract,
                templates,
                design_digest,
                status,
                roots,
                workers=workers,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
            )
            _write_phase(
                output,
                "forensics",
                design_digest,
                forensics,
                "# Stage 6H generational forensics\n\nSeed, teacher-forced, one-step-rescue, zero-noise, and cross-generation dialect boundaries were measured on exposed pairs only.",
                "# Lay summary\n\nThis shows whether the message fails in reading, rewriting, copying, or the next daughter's changed dialect.",
            )
            active_phase[0] = "develop"
            development_result = {
                "state": "complete",
                "stage_gate": len(specs) == 16,
                "candidate_count": len(specs),
                "candidate_allocation": {
                    group: sum(row["selection_group"] == group for row in specs)
                    for group in CLAIM_GROUPS
                },
                "selection_digest": _digest(specs),
                "selection_frozen_before_validation": True,
                "runtime_retraining": False,
                "runtime_target_exposure": False,
                "next_phase": "validate",
                "final_audit_trajectory_state": "untouched",
            }
            _write_phase(
                output,
                "develop",
                design_digest,
                development_result,
                "# Stage 6H frozen repairs\n\nSixteen label-free, rollout-trained, channel-matched, full, and compressed candidates were sealed before validation.",
                "# Lay summary\n\nAll repair dictionaries were locked before any unused daughter was examined.",
            )

        development: dict[str, Any] | None = None
        if time.time() < float(campaign["exploration_deadline_unix"]):
            development = _run_development(
                output,
                stage_root,
                profile_name,
                specs,
                frozen,
                cohorts,
                nested_profile,
                contract,
                writer_contract,
                templates,
                design_digest,
                roots,
                campaign,
                status,
                active_phase,
                workers=workers,
                resume=resume,
                auto_final_audit=auto_final_audit,
            )
            for phase_name in ("validate", "qualify", "endurance", "adjudicate"):
                active_phase[0] = phase_name
                nested_name = "screen" if phase_name == "validate" else phase_name
                summary = development[phase_name]
                _write_phase(
                    output,
                    phase_name,
                    design_digest,
                    {
                        "state": summary.get("state", "complete"),
                        "stage_gate": bool(summary.get("stage_gate")),
                        "nested_phase": nested_name,
                        "subcampaign_result": summary,
                        "next_phase": None,
                        "final_audit_trajectory_state": summary.get(
                            "final_audit_trajectory_state", "untouched"
                        ),
                    },
                    f"# Stage 6H {phase_name}\n\nThe sealed campaign contains the complete causal statistics.",
                    "# Lay summary\n\nOnly a repair passing every earlier unused-data test was allowed to continue.",
                )

        active_phase[0] = "complete"
        result = _campaign_result(
            output,
            design_digest,
            profile_name,
            forensics,
            specs,
            development,
        )
        status(
            "complete",
            "campaign-complete",
            verdict=result["verdict"],
            final_audit_trajectory_state=result["final_audit_trajectory_state"],
        )
        return result
    except BaseException as error:
        if campaign is None:
            now = time.time()
            campaign = {
                "started_unix": now,
                "hard_deadline_unix": now,
                "exploration_deadline_unix": now,
            }
        if status is None:
            status = _status_writer(output, profile_name, campaign, active_phase)
        status("failed", "campaign-failed", error=repr(error))
        ar._atomic_json(
            output / "ERROR.json",
            {
                "error": repr(error),
                "phase": active_phase[0],
                "updated_unix": time.time(),
            },
        )
        raise


__all__ = (
    "CLAIM_GROUPS",
    "DEFAULT_STAGE6G_ROOT",
    "GenerationalProfile",
    "GenerationalTransductionContract",
    "PHASES",
    "PROFILES",
    "run_motif_generational_transduction",
)
