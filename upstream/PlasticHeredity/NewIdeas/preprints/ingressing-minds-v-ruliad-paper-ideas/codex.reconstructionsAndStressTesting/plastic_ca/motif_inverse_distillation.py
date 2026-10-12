"""Stage-6L inverse-carrier distillation and generational dialect closure.

Stage 6K showed that the inherited slow field and its reader are usable when
the correct field is supplied, but a daughter-trained writer loses
history-specific information after the founder boundary.  This stage targets
the causally effective, stable carrier directly, trains on its own out-of-fold
rollouts, and keeps the original 62-pair audit reserve unreachable.
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
from typing import Any, Iterable, Sequence

import numpy as np

from . import motif_acquisition_repair as ar
from . import motif_adaptive_handoff as ah
from . import motif_minimality as mm
from . import motif_phenotype_bridge as pb
from . import motif_writer_closure as wc
from .life_family import life_like_step_batch, life_rule_notation


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_INVERSE_DISTILLATION_PROTOCOL.md"
DEFAULT_STAGE6K_ROOT = ROOT / "results/ca-motif-writer-closure-stage-6k"
DEFAULT_STAGE6J_ROOT = wc.DEFAULT_STAGE6J_ROOT
DEFAULT_STAGE6I_ROOT = wc.DEFAULT_STAGE6I_ROOT
DEFAULT_STAGE6H_ROOT = wc.DEFAULT_STAGE6H_ROOT
PHASES = (
    "integrity",
    "measurement",
    "cohorts",
    "initial-fit",
    "closed-loop",
    "support-screen",
    "narrow-validation",
    "motion",
    "adjudicate",
)
WRITER_KINDS = ("temporal-ridge", "rff", "gated-local-reservoir")
TEACHER_KINDS = ("stable-oracle", "inverse-control")


@dataclass(frozen=True)
class InverseDistillationProfile:
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


PROFILES = {
    "smoke": InverseDistillationProfile(6, 2, 1, 1, 1, 1, 1024, 2, 2, 100),
    "reference": InverseDistillationProfile(
        56, 16, 2, 4, 3, 2, 8192, 24, 16, 10_000
    ),
}


@dataclass(frozen=True)
class InverseDistillationContract(wc.WriterClosureContract):
    implementation_version: str = "ca-motif-inverse-distillation-v1"
    namespace: str = "plastic-ca-motif-inverse-distillation-v1"
    exploration_stop_hours: float = 6.5
    writer_bit_accuracy_minimum: float = 0.65
    writer_fold_minimum: float = 0.58
    coefficient_cosine_minimum: float = 0.10
    calibration_joint_minimum: float = 0.95
    calibration_subset_maximum: float = 0.60
    lineage_field_decoder_minimum: float = 0.70
    dynamic_form_minimum: float = 0.70
    dynamic_direction_margin_minimum: float = 0.15
    dynamic_recovery_minimum: float = 0.60

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "writer_kinds": WRITER_KINDS,
                "teacher_kinds": TEACHER_KINDS,
                "writer_radii": (4, 6),
                "writer_windows": (16, 32),
                "writer_output": "two rank-16 q4 coefficient channels",
                "d4_policy": "augmentation-and-consistency; no canonicalization",
                "runtime_inputs": ("local visible spacetime", "zero-born adapter"),
                "runtime_target_labels": False,
                "runtime_parent_field": False,
                "runtime_pair_identity": False,
                "runtime_generation_index": False,
                "final_reserve_policy": "unreachable-and-never-open-in-stage-6l",
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
    stage6k_root: Path,
    stage6j_root: Path,
    stage6i_root: Path,
    stage6h_root: Path,
) -> dict[str, Any]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "MANIFEST.json",
        "stage6k/COHORTS.json",
        "measurement/RESULTS.json",
        "oracle-ladder/RESULTS.json",
        "fit/RESULTS.json",
        "heldout/RESULTS.json",
        "adjudicate/RESULTS.json",
        "COMPLETE",
    )
    # The first Stage-6K campaign called this phase ``integrity`` rather than
    # ``measurement``.  Measurement repair is new in Stage 6L.
    required = tuple(
        "integrity/RESULTS.json" if value == "measurement/RESULTS.json" else value
        for value in required
    )
    missing = [stage6k_root / value for value in required if not (stage6k_root / value).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6K artifacts: {missing}")
    result = _load_json(stage6k_root / "RESULTS.json")
    status = _load_json(stage6k_root / "STATUS.json")
    cohorts = _load_json(stage6k_root / "stage6k/COHORTS.json")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6L requires a complete Stage-6K parent")
    if result.get("verdict") != "FROZEN_WRITER_CLOSURE_NOT_CAUSAL_ON_HELDOUT":
        raise ValueError("Stage-6L requires the registered Stage-6K writer boundary")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6K final reserve is not untouched")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6K cohort ledger reports a touched reserve")
    ancestry = wc._parent_integrity(stage6j_root, stage6i_root, stage6h_root)
    if ancestry["final_pair_ids_sha256"] != cohorts["final_audit_pair_ids_sha256"]:
        raise ValueError("Stage-6K and Stage-6J final reserve digests disagree")
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "required_hashes": {
            value: ar._sha256(stage6k_root / value) for value in required
        },
        "stage6k_result_sha256": ar._sha256(stage6k_root / "RESULTS.json"),
        "exposed_pair_count": 56,
        "final_pair_count": 62,
        "final_pair_ids_sha256": ancestry["final_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
        "stage6j_integrity": ancestry,
    }


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6k_root: Path,
    stage6j_root: Path,
    stage6i_root: Path,
    stage6h_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[
    InverseDistillationContract,
    InverseDistillationProfile,
    dict[str, Any],
    str,
    dict[str, Any],
]:
    contract = InverseDistillationContract()
    profile = PROFILES[profile_name]
    integrity = _parent_integrity(stage6k_root, stage6j_root, stage6i_root, stage6h_root)
    design = {
        "experiment": "ca_motif_inverse_distillation_stage_6l",
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(profile),
        "stage6k_root": str(stage6k_root.resolve()),
        "stage6k_required_hashes": integrity["required_hashes"],
        "cohort_route": {
            "development": "all 56 Stage-6K-exposed narrow pairs",
            "procedural_validation": "16 newly recombined, donor-disjoint pair identities",
            "final": "62-pair protected reserve is unreachable",
        },
        "writer_factorial": {
            "kinds": WRITER_KINDS,
            "radii": (4, 6),
            "windows": (16, 32),
            "teachers": TEACHER_KINDS,
            "total": 24,
            "folds": 6,
            "dagger_rounds": profile.dagger_rounds,
        },
        "motion_carrier": {
            "shape": (4, 8, 8),
            "channels": ("occupancy", "change", "velocity-y", "velocity-x"),
            "development_pairs": profile.mover_development_pairs,
            "validation_pairs": profile.mover_validation_pairs,
        },
        "compute": {
            "hard_hours": max_hours,
            "exploration_cutoff_hours": min(contract.exploration_stop_hours, max_hours),
            "worker_cap": 4,
            "detached_and_resumable": True,
        },
        "protocol_sha256": ar._sha256(PROTOCOL_PATH),
        "implementation_hashes": {
            "motif_inverse_distillation.py": ar._sha256(Path(__file__)),
            "motif_phenotype_bridge.py": ar._sha256(Path(pb.__file__)),
            "motif_writer_closure.py": ar._sha256(Path(wc.__file__)),
        },
    }
    design_digest = _digest(design)
    design["design_digest"] = design_digest
    path = output / "DESIGN.json"
    if resume and path.exists():
        prior = _load_json(path)
        if prior.get("design_digest") != design_digest:
            raise ValueError("Stage-6L resume design changed")
    else:
        ar._atomic_json(path, design)
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
            "parent_sha256": integrity["stage6k_result_sha256"],
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
            "experiment": "ca_motif_inverse_distillation_stage_6l",
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
        if (
            "eta_seconds" not in extra
            and "completed" in extra
            and "total" in extra
            and int(extra["completed"]) > 0
        ):
            rate = payload["elapsed_seconds"] / int(extra["completed"])
            payload["eta_seconds"] = max(
                0.0, rate * (int(extra["total"]) - int(extra["completed"]))
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
        "experiment": "ca_motif_inverse_distillation_stage_6l",
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


def _pair_targets(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in sorted(set(left["targets"]) & set(right["targets"])):
        a = left["targets"][key]
        b = right["targets"][key]
        if isinstance(a, dict) and isinstance(b, dict) and "A" in a and "B" in b:
            result[key] = {"A": copy.deepcopy(a["A"]), "B": copy.deepcopy(b["B"])}
    if "primary" not in result:
        raise ValueError("procedural pair lacks primary A/B targets")
    return result


def _procedural_pairs(
    all_pairs: Sequence[dict[str, Any]],
    excluded_pair_ids: set[str],
    excluded_donor_ids: set[str],
    count: int,
    namespace: str,
) -> list[dict[str, Any]]:
    """Construct identities that never occurred in the frozen pair atlas.

    A-side and B-side donors are recombined only within a launch block, where
    the registered visible reset is bitwise identical.  Donors used by the
    Stage-6K cohort or protected reserve are excluded as an additional guard.
    """

    by_launch: dict[int, list[dict[str, Any]]] = {}
    for pair in all_pairs:
        if str(pair["pair_id"]) in excluded_pair_ids:
            continue
        donor_ids = {
            str(pair["donor_a"]["donor_id"]),
            str(pair["donor_b"]["donor_id"]),
        }
        if donor_ids & excluded_donor_ids:
            continue
        by_launch.setdefault(int(pair["launch_index"]), []).append(pair)
    selected: list[dict[str, Any]] = []
    used_donors: set[str] = set()
    launches = sorted(by_launch)
    quota = {launch: count // len(launches) for launch in launches}
    for launch in launches[: count % max(1, len(launches))]:
        quota[launch] += 1
    for launch in launches:
        if quota[launch] <= 0:
            continue
        rows = sorted(
            by_launch[launch],
            key=lambda row: (
                ar._hash_seed(namespace, "procedural-source", row["pair_id"]),
                row["pair_id"],
            ),
        )
        a_rows = rows
        b_rows = rows[1:] + rows[:1]
        for left, right in zip(a_rows, b_rows, strict=True):
            donor_a = str(left["donor_a"]["donor_id"])
            donor_b = str(right["donor_b"]["donor_id"])
            if donor_a == donor_b or {donor_a, donor_b} & used_donors:
                continue
            reset_a = str(left["donor_a"]["initial_state_hex"])
            reset_b = str(right["donor_b"]["initial_state_hex"])
            if reset_a != reset_b:
                continue
            pair_id = f"stage6l-procedural-{launch}-{donor_a}-{donor_b}"
            if any(str(row["pair_id"]) == pair_id for row in all_pairs):
                continue
            selected.append(
                {
                    "pair_id": pair_id,
                    "substrate": "life",
                    "rule": int(left["rule"]),
                    "family": "local-procedural-recombination",
                    "launch_index": launch,
                    "density_delta": float(right["donor_b"]["density"])
                    - float(left["donor_a"]["density"]),
                    "donor_a": copy.deepcopy(left["donor_a"]),
                    "donor_b": copy.deepcopy(right["donor_b"]),
                    "targets": _pair_targets(left, right),
                    "procedural_sources": (str(left["pair_id"]), str(right["pair_id"])),
                }
            )
            used_donors.update((donor_a, donor_b))
            if sum(int(row["launch_index"] == launch) for row in selected) >= quota[launch]:
                break
    if len(selected) != count:
        raise ValueError(f"could construct only {len(selected)} of {count} procedural pairs")
    return sorted(
        selected,
        key=lambda row: (ar._hash_seed(namespace, "validation-order", row["pair_id"]), row["pair_id"]),
    )


def _reconstruct_cohorts(
    stage_root: Path,
    profile_name: str,
    profile: InverseDistillationProfile,
    integrity: dict[str, Any],
    stage6j_root: Path,
    stage6i_root: Path,
    stage6h_root: Path,
    roots: dict[str, Path],
) -> tuple[
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    pb.PhenotypeBridgeProfile,
    ar.MotifContract,
    list[dict[str, Any]],
]:
    ancestry_root = stage_root / "ancestry"
    frozen, old, nested, writer_contract, templates = wc._reconstruct_cohorts(
        ancestry_root,
        "reference" if profile_name == "reference" else "smoke",
        wc.PROFILES["reference" if profile_name == "reference" else "smoke"],
        integrity["stage6j_integrity"],
        stage6j_root,
        roots,
    )
    development = [*old["exposed"], *old["heldout"]][: profile.development_pairs]
    all_pairs = mm.load_round3_pairs()[mm.RULE]
    by_id = {str(pair["pair_id"]): pair for pair in all_pairs}
    final_ids = set(str(value) for value in frozen["later_ids"])
    excluded_ids = final_ids | {str(pair["pair_id"]) for pair in development}
    excluded_donors: set[str] = set()
    for pair_id in excluded_ids:
        pair = by_id[pair_id]
        excluded_donors.update(
            (str(pair["donor_a"]["donor_id"]), str(pair["donor_b"]["donor_id"]))
        )
    validation = _procedural_pairs(
        all_pairs,
        excluded_ids,
        excluded_donors,
        profile.procedural_validation_pairs,
        InverseDistillationContract().namespace,
    )
    cohorts = {"development": development, "procedural_validation": validation, "final": []}
    development_ids = {str(row["pair_id"]) for row in development}
    validation_ids = {str(row["pair_id"]) for row in validation}
    validation_donors = {
        str(row[side]["donor_id"])
        for row in validation
        for side in ("donor_a", "donor_b")
    }
    if development_ids & validation_ids or validation_ids & final_ids:
        raise AssertionError("Stage-6L evidential pair roles overlap")
    if validation_donors & excluded_donors:
        raise AssertionError("Stage-6L procedural validation reuses a protected/exposed donor")
    payload = {
        "pair_ids": {
            "development": sorted(development_ids),
            "procedural_validation": [str(row["pair_id"]) for row in validation],
        },
        "procedural_source_pair_ids_sha256": _digest(
            sorted(value for row in validation for value in row["procedural_sources"])
        ),
        "procedural_pair_ids_sha256": _digest(sorted(validation_ids)),
        "procedural_donors_disjoint_from_stage6k_and_final": True,
        "procedural_visible_resets_bitwise_identical": True,
        "development_previously_exposed": True,
        "procedural_validation_trajectories_not_simulated_before_freeze": True,
        "final_audit_pair_count": 62,
        "final_audit_pair_ids_sha256": integrity["final_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
        "final_audit_trajectories_not_loaded": True,
    }
    ar._atomic_json(stage_root / "COHORTS.json", payload)
    return frozen, cohorts, nested, writer_contract, templates


def _nearest_centroid_ba(features: np.ndarray, labels: np.ndarray, folds: int = 8) -> float:
    values = np.asarray(features, dtype=np.float64).reshape(len(features), -1)
    target = np.asarray(labels, dtype=np.int8)
    predictions = np.zeros(len(values), dtype=np.int8)
    for fold in range(folds):
        test = np.arange(len(values)) % folds == fold
        train = ~test
        a = np.mean(values[train & (target == 1)], axis=0)
        b = np.mean(values[train & (target == -1)], axis=0)
        da = np.sum((values[test] - a) ** 2, axis=1)
        db = np.sum((values[test] - b) ** 2, axis=1)
        predictions[test] = np.where(da <= db, 1, -1)
    recalls = [float(np.mean(predictions[target == label] == label)) for label in (1, -1)]
    return float(np.mean(recalls))


def _measurement_calibration(
    source: dict[str, Any],
    stage6k_root: Path,
    contract: InverseDistillationContract,
) -> dict[str, Any]:
    codec = pb._field_codec_candidate(
        source | {"field_rank": 16, "field_channels": 2}
    )
    samples = 256
    labels = np.concatenate(
        (np.ones(samples // 2, dtype=np.int8), -np.ones(samples // 2, dtype=np.int8))
    )
    rng = np.random.default_rng(ar._hash_seed(contract.namespace, "calibration-patches"))
    base = np.where(rng.random((4, 4)) < 0.5, 1.0, -1.0).astype(np.float32)
    patches = labels[:, None, None].astype(np.float32) * base[None]
    payload = np.concatenate(
        (ar.texture_encode(patches, 16), np.zeros((samples, 16), dtype=np.float32)),
        axis=1,
    )
    shares, active = pb._encode_carrier(
        payload, codec, contract, "stage6l-calibration", 1, "exact"
    )
    decoded, valid = pb._joint_payload(shares, active, codec)
    full_ba = _nearest_centroid_ba(decoded, labels)
    subset_bas = [
        _nearest_centroid_ba(shares[:, subset].astype(np.float32) / 15.0, labels)
        for subset in ((0,), (1,), (2,), (3,), (0, 1), (0, 2), (1, 3), (0, 1, 2))
    ]
    opposite_ba = _nearest_centroid_ba(-decoded, labels)
    random_payload = rng.uniform(-1.0, 1.0, size=payload.shape).astype(np.float32)
    random_ba = _nearest_centroid_ba(random_payload, labels)
    copied, uncorrectable = pb._copy_carrier(
        shares,
        "stage6l-calibration",
        2,
        samples // 2,
        contract,
        purpose="calibration-copy",
        corruption=0.01,
    )
    copied_payload, copied_valid = pb._joint_payload(copied, active, codec)
    copied_ba = _nearest_centroid_ba(copied_payload, labels)
    oracle = _load_json(stage6k_root / "oracle-ladder/RESULTS.json")
    gate = bool(
        np.all(valid)
        and np.all(copied_valid)
        and full_ba >= contract.calibration_joint_minimum
        and copied_ba >= contract.calibration_joint_minimum
        and max(subset_bas) <= contract.calibration_subset_maximum
        and float(oracle.get("full_support_effect_ceiling", 0.0)) > 0.05
        and bool(oracle.get("stage_gate", False))
    )
    return {
        "state": "complete",
        "stage_gate": gate,
        "sample_count": samples,
        "joint_balanced_accuracy": full_ba,
        "copied_joint_balanced_accuracy": copied_ba,
        "proper_subset_balanced_accuracies": subset_bas,
        "proper_subset_max_balanced_accuracy": max(subset_bas),
        "opposite_field_balanced_accuracy": opposite_ba,
        "random_field_balanced_accuracy": random_ba,
        "copy_uncorrectable_fraction": uncorrectable,
        "stage6k_oracle_gate": bool(oracle.get("stage_gate", False)),
        "stage6k_oracle_localization": oracle.get("localization"),
        "stage6k_full_support_effect_ceiling": oracle.get("full_support_effect_ceiling"),
        "decoder_scope": "two-channel inherited field; not ordinary texture carrier",
        "final_audit_trajectory_state": "untouched",
    }


def _writer_configs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for kind in WRITER_KINDS:
        for radius in (4, 6):
            for window in (16, 32):
                for teacher in TEACHER_KINDS:
                    rows.append(
                        {
                            "config_id": f"{kind}-r{radius}-w{window}-{teacher}",
                            "kind": kind,
                            "runtime_kind": {
                                "temporal-ridge": "sketched-ridge",
                                "rff": "rff",
                                "gated-local-reservoir": "local-reservoir",
                            }[kind],
                            "radius": radius,
                            "window": window,
                            "teacher": teacher,
                            "canonicalize": False,
                        }
                    )
    if len(rows) != 24 or len({row["config_id"] for row in rows}) != 24:
        raise AssertionError("Stage-6L writer factorial changed")
    return rows


def _collect_traces(
    stage_root: Path,
    phase: str,
    candidates_and_pairs: Sequence[tuple[dict[str, Any], Sequence[dict[str, Any]]]],
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: InverseDistillationContract,
    design_digest: str,
    *,
    replicates: int,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[list[dict[str, Any]], bool, int]:
    candidates = [candidate for candidate, _ in candidates_and_pairs]
    items: list[dict[str, Any]] = []
    for candidate, pairs in candidates_and_pairs:
        made = ar._make_items(
            list(pairs),
            [candidate],
            ar._template_pairs(templates, "development"),
            frozen["stage4"]["configuration"],
            phase=phase,
            replicates=replicates,
            generations=10,
            conditions=("intact",),
            analysis_kind="stage6l-visible-dialect-trace",
        )
        for item in made:
            item["checkpoint"] = (
                f"{candidate['candidate_id']}-{item['checkpoint']}"
            )
            item["retain_bridge_trace"] = True
            item["retain_bridge_generations"] = (5, 6, 7, 8, 9, 10)
        items.extend(made)
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        phase,
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
    return rows, complete, len(items)


def _trace_records(raw: dict[str, Any]) -> list[dict[str, Any]]:
    result = raw["conditions"]["intact"]
    records: list[dict[str, Any]] = []
    for generation_text, trace in sorted(
        result.get("bridge_trace", {}).items(), key=lambda item: int(item[0])
    ):
        shape = trace["state_shape"]
        states = {
            int(sweep): np.stack(
                [wc._unpack_state_hex(value, shape) for value in values], axis=0
            )
            for sweep, values in trace["full_state_hex"].items()
        }
        records.append(
            {
                "pair_id": str(raw["pair_id"]),
                "candidate_id": str(raw["candidate_id"]),
                "generation": int(generation_text),
                "rule": int(raw.get("rule", result["rule"])),
                "read_end": int(trace["read_end"]),
                "states": states,
                "centers": np.asarray(trace["centers"], dtype=np.int16),
                "environment": np.asarray(trace["environment"], dtype=np.float32),
            }
        )
    return records


def _d4_blocks(values: np.ndarray, symmetry: int) -> np.ndarray:
    blocks = np.asarray(values, dtype=np.float32)
    if int(symmetry) >= 4:
        blocks = np.flip(blocks, axis=-1)
    return np.rot90(blocks, int(symmetry) % 4, axes=(-2, -1)).copy()


def _teacher_patches(record: dict[str, Any], endpoint: int, teacher: str) -> np.ndarray:
    target = np.asarray(record["environment"], dtype=np.float32)
    if teacher == "stable-oracle":
        second = np.zeros_like(target)
    elif teacher == "inverse-control":
        state = record["states"][endpoint]
        unassisted = ar._step(state, int(record["rule"]))
        observed = ar.observe_texture(unassisted, record["centers"])
        second = np.where(
            (observed >= 0.0) != (target >= 0.0), target, 0.0
        ).astype(np.float32)
    else:
        raise ValueError(f"unknown Stage-6L teacher {teacher!r}")
    return np.stack((target, second), axis=1)


def _examples_for_config(
    rows: Sequence[dict[str, Any]],
    config: dict[str, Any],
    *,
    augment: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    feature_rows: list[np.ndarray] = []
    target_rows: list[np.ndarray] = []
    groups: list[str] = []
    endpoints: list[str] = []
    symmetries = range(8) if augment else range(1)
    for raw in rows:
        for record in _trace_records(raw):
            available = sorted(record["states"])
            if not available:
                continue
            endpoint = max(available)
            beginning = max(min(available), endpoint - int(config["window"]) + 1)
            history = [
                record["states"][sweep]
                for sweep in available
                if beginning <= sweep <= endpoint
            ]
            features, _ = pb._closure_local_features(
                history,
                record["centers"],
                int(config["radius"]),
                int(config["window"]),
                False,
            )
            side = 2 * int(config["radius"]) + 1
            blocks = features[:, :-1].reshape(len(features), 4, side, side)
            target_patches = _teacher_patches(record, endpoint, str(config["teacher"]))
            for symmetry in symmetries:
                transformed_blocks = _d4_blocks(blocks, symmetry)
                transformed_target = pb._d4_patch(target_patches, symmetry)
                transformed_features = np.concatenate(
                    (
                        transformed_blocks.reshape(len(features), -1),
                        np.ones((len(features), 1), dtype=np.float32),
                    ),
                    axis=1,
                )
                coefficients = np.concatenate(
                    (
                        ar.texture_encode(transformed_target[:, 0], 16),
                        ar.texture_encode(transformed_target[:, 1], 16),
                    ),
                    axis=1,
                )
                feature_rows.append(transformed_features)
                target_rows.append(coefficients)
                groups.extend([str(record["pair_id"])] * len(features))
                endpoints.extend(
                    [
                        f"{record['pair_id']}:g{record['generation']}:s{endpoint}:d4{symmetry}"
                    ]
                    * len(features)
                )
    if not feature_rows:
        raise ValueError("Stage-6L trace collection yielded no writer examples")
    return (
        np.concatenate(feature_rows).astype(np.float32),
        np.concatenate(target_rows).astype(np.float32),
        np.asarray(groups, dtype=str),
        endpoints,
    )


def _projection_for(
    config: dict[str, Any], input_dimension: int
) -> tuple[np.ndarray | None, np.ndarray | None]:
    kind = str(config["runtime_kind"])
    if kind == "equivariant-ridge":
        return None, None
    width = 96
    rng = np.random.default_rng(
        ar._hash_seed("stage6l-writer-projection", config["config_id"])
    )
    projection = rng.normal(
        0.0,
        1.0 / math.sqrt(max(1, input_dimension)),
        size=(input_dimension, width),
    ).astype(np.float32)
    phase = (
        np.zeros(width, dtype=np.float32)
        if kind == "sketched-ridge"
        else
        rng.uniform(0.0, 2.0 * math.pi, size=width)
        if kind == "rff"
        else rng.uniform(-0.35, 0.35, size=width)
    ).astype(np.float32)
    return projection, phase


def _design_matrix(
    normalized: np.ndarray,
    runtime_kind: str,
    projection: np.ndarray | None,
    phase: np.ndarray | None,
) -> np.ndarray:
    if runtime_kind == "equivariant-ridge":
        return normalized
    if projection is None or phase is None:
        raise ValueError("nonlinear Stage-6L writer lacks its projection")
    projected = normalized @ projection + phase
    if runtime_kind == "sketched-ridge":
        return projected.astype(np.float32)
    if runtime_kind == "rff":
        return (
            np.float32(math.sqrt(2.0 / projection.shape[1])) * np.cos(projected)
        ).astype(np.float32)
    if runtime_kind == "local-reservoir":
        return np.tanh(projected).astype(np.float32)
    raise ValueError(f"unknown runtime writer kind {runtime_kind!r}")


def _coefficient_metrics(predicted: np.ndarray, targets: np.ndarray) -> dict[str, float]:
    prediction = np.clip(np.asarray(predicted, dtype=np.float32), -1.0, 1.0)
    target = np.asarray(targets, dtype=np.float32)
    pred_patch = ar.texture_decode(prediction[:, :16], 16)
    target_patch = ar.texture_decode(target[:, :16], 16)
    bit_accuracy = float(np.mean((pred_patch >= 0.0) == (target_patch >= 0.0)))
    numerator = np.sum(prediction * target, axis=1)
    denominator = np.linalg.norm(prediction, axis=1) * np.linalg.norm(target, axis=1)
    cosine = float(
        np.mean(
            np.divide(
                numerator,
                denominator,
                out=np.zeros_like(numerator),
                where=denominator > np.float32(1e-8),
            )
        )
    )
    alignment = np.mean(pred_patch * target_patch, axis=(1, 2))
    history_ba = float(np.mean(alignment > 0.0))
    return {
        "form_bit_accuracy": bit_accuracy,
        "coefficient_cosine": cosine,
        "history_specific_accuracy": history_ba,
        "coefficient_mae": float(np.mean(np.abs(prediction - target))),
        "decoded_field_energy": float(np.mean(np.abs(pred_patch))),
    }


def _fit_arrays(
    features: np.ndarray,
    targets: np.ndarray,
    config: dict[str, Any],
    train: np.ndarray,
) -> dict[str, Any]:
    mean = np.mean(features[train], axis=0, dtype=np.float64).astype(np.float32)
    scale = np.std(features[train], axis=0, dtype=np.float64).astype(np.float32)
    scale = np.where(scale > np.float32(1e-6), scale, 1.0).astype(np.float32)
    projection, phase = _projection_for(config, features.shape[1])
    normalized = (features[train] - mean) / scale
    design = _design_matrix(
        normalized, str(config["runtime_kind"]), projection, phase
    )
    weights, bias = wc._ridge_fit(design, targets[train], 0.30)
    model: dict[str, Any] = {
        "kind": str(config["runtime_kind"]),
        "architecture": str(config["kind"]),
        "radius": int(config["radius"]),
        "window": int(config["window"]),
        "teacher": str(config["teacher"]),
        "canonicalize": False,
        "input_mean": mean.tolist(),
        "input_scale": scale.tolist(),
        "weights": weights.tolist(),
        "bias": bias.tolist(),
        "output_space": "q4-coefficients",
        "output_rank": 16,
        "confidence_threshold": 0.08,
        "model_frozen": True,
        "runtime_target_labels": False,
        "runtime_parent_field": False,
        "runtime_pair_identity": False,
        "runtime_generation_index": False,
    }
    if projection is not None and phase is not None:
        model["projection"] = projection.tolist()
        model["projection_phase"] = phase.tolist()
    return model


def _predict_arrays(model: dict[str, Any], features: np.ndarray) -> np.ndarray:
    mean = np.asarray(model["input_mean"], dtype=np.float32)
    scale = np.asarray(model["input_scale"], dtype=np.float32)
    normalized = (features - mean) / scale
    projection = (
        np.asarray(model["projection"], dtype=np.float32)
        if "projection" in model
        else None
    )
    phase = (
        np.asarray(model["projection_phase"], dtype=np.float32)
        if "projection_phase" in model
        else None
    )
    design = _design_matrix(normalized, str(model["kind"]), projection, phase)
    return np.clip(
        design @ np.asarray(model["weights"], dtype=np.float32)
        + np.asarray(model["bias"], dtype=np.float32),
        -1.0,
        1.0,
    )


def _fit_one_writer(
    rows: Sequence[dict[str, Any]],
    config: dict[str, Any],
    contract: InverseDistillationContract,
    *,
    retain_fold_models: bool = False,
) -> dict[str, Any]:
    features, targets, groups, endpoints = _examples_for_config(rows, config)
    folds = wc._pair_blocked_folds(groups, contract.local_writer_fold_count)
    fold_results: list[dict[str, Any]] = []
    fold_models: list[dict[str, Any]] = []
    for fold in range(contract.local_writer_fold_count):
        train = folds != fold
        test = folds == fold
        model = _fit_arrays(features, targets, config, train)
        metrics = _coefficient_metrics(_predict_arrays(model, features[test]), targets[test])
        fold_results.append(
            {
                "fold": fold,
                "training_pair_count": len(set(groups[train].tolist())),
                "test_pair_count": len(set(groups[test].tolist())),
                "training_example_count": int(np.count_nonzero(train)),
                "test_example_count": int(np.count_nonzero(test)),
                **metrics,
            }
        )
        if retain_fold_models:
            model["fold"] = fold
            model["model_id"] = f"stage6l-{config['config_id']}-fold{fold}"
            model["model_digest"] = _digest(model)
            fold_models.append(model)
    full = np.ones(len(features), dtype=np.bool_)
    model = _fit_arrays(features, targets, config, full)
    model["model_id"] = f"stage6l-{config['config_id']}"
    model["training_pair_count"] = len(set(groups.tolist()))
    model["training_example_count"] = len(features)
    model["model_digest"] = _digest(model)
    training = _coefficient_metrics(_predict_arrays(model, features), targets)
    mean_bit = float(np.mean([row["form_bit_accuracy"] for row in fold_results]))
    minimum_bit = float(np.min([row["form_bit_accuracy"] for row in fold_results]))
    cosine = float(np.mean([row["coefficient_cosine"] for row in fold_results]))
    history = float(np.mean([row["history_specific_accuracy"] for row in fold_results]))
    gate = bool(
        mean_bit >= contract.writer_bit_accuracy_minimum
        and minimum_bit >= contract.writer_fold_minimum
        and cosine >= contract.coefficient_cosine_minimum
    )
    score = float(0.45 * mean_bit + 0.20 * minimum_bit + 0.20 * max(0.0, cosine) + 0.15 * history)
    return {
        "config": dict(config),
        "state": "complete",
        "stage_gate": gate,
        "selection_score": score,
        "cross_validation": {
            "form_bit_accuracy_mean": mean_bit,
            "form_bit_accuracy_minimum": minimum_bit,
            "coefficient_cosine_mean": cosine,
            "history_specific_accuracy_mean": history,
            "folds": fold_results,
        },
        "training_metrics": training,
        "model": model,
        "fold_models": fold_models,
        "fold_assignment_digest": _digest(
            sorted(
                {(str(group), int(fold)) for group, fold in zip(groups.tolist(), folds.tolist(), strict=True)}
            )
        ),
        "endpoint_digest": _digest(sorted(set(endpoints))),
    }


def _fit_factorial(
    stage_root: Path,
    rows: Sequence[dict[str, Any]],
    profile_name: str,
    profile: InverseDistillationProfile,
    contract: InverseDistillationContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "initial-writer-fit"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    fitted: dict[str, dict[str, Any]] = {}
    configs = _writer_configs()
    for config in configs:
        path = checkpoints / f"{config['config_id']}.json"
        if resume and path.exists():
            saved = _load_json(path)
            if saved.get("design_digest") != design_digest:
                raise ValueError("Stage-6L writer checkpoint design changed")
            fitted[str(config["config_id"])] = saved["result"]
            continue
        if time.time() >= deadline:
            break
        result = _fit_one_writer(rows, config, contract)
        # Fold models are generated only for the selected DAgger cells.
        result.pop("fold_models", None)
        ar._atomic_json(path, {"design_digest": design_digest, "result": result})
        fitted[str(config["config_id"])] = result
        status(
            "running",
            "fit-inverse-carrier-factorial",
            completed=len(fitted),
            total=len(configs),
            latest_checkpoint=config["config_id"],
        )
    complete = len(fitted) == len(configs)
    eligible = [
        value
        for value in fitted.values()
        if value["stage_gate"] or profile_name == "smoke"
    ]
    ranked = sorted(
        eligible,
        key=lambda value: (-float(value["selection_score"]), value["config"]["config_id"]),
    )
    selected_configs = [value["config"] for value in ranked[: profile.dagger_base_models]]
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and selected_configs),
        "candidate_count": len(configs),
        "completed_candidate_count": len(fitted),
        "pair_blocked_fold_count": contract.local_writer_fold_count,
        "selected_config_ids": [row["config_id"] for row in selected_configs],
        "candidate_summaries": {
            key: {k: v for k, v in value.items() if k != "model"}
            | {"model_digest": value["model"]["model_digest"]}
            for key, value in sorted(fitted.items())
        },
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, selected_configs


def _candidate_from_model(
    source: dict[str, Any],
    model: dict[str, Any],
    *,
    suffix: str,
    support: int = 8,
    rehearsal: bool = False,
) -> dict[str, Any]:
    row = copy.deepcopy(source)
    row.update(
        {
            "candidate_id": f"{model['model_id']}-{suffix}",
            "mechanism": "inherited-field",
            "mechanism_tier": "inherited-field",
            "claim_tier": "broad",
            "adaptive_claim_tier": "rulebook-assisted",
            "adaptive_architecture": str(model["architecture"]),
            "writer_source": "visible",
            "writer_input_contract": "local-visible-spacetime-and-zero-born-adapter-only",
            "training_mode": "rulebook-assisted-inverse-distillation",
            "field_rank": 16,
            "field_channels": 2,
            "field_bias": 0.70,
            "field_support_sweeps": int(support),
            "daughter_writer_start_offset": 5,
            "daughter_writer_sweeps": 16,
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
    ids = np.asarray(
        [str(pair["pair_id"]) for pair in pairs for _ in range(2)], dtype=str
    )
    folds = wc._pair_blocked_folds(ids, fold_count)
    return {
        str(pair_id): int(fold)
        for pair_id, fold in zip(ids[::2].tolist(), folds[::2].tolist(), strict=True)
    }


def _closed_loop_fit(
    stage_root: Path,
    source: dict[str, Any],
    base_rows: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    selected_configs: Sequence[dict[str, Any]],
    profile: InverseDistillationProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: InverseDistillationContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "closed-loop-fit"
    root.mkdir(parents=True, exist_ok=True)
    datasets: dict[str, list[dict[str, Any]]] = {
        str(config["config_id"]): list(base_rows) for config in selected_configs
    }
    latest: dict[str, dict[str, Any]] = {}
    rounds: list[dict[str, Any]] = []
    fold_map = _pair_fold_map(pairs, contract.local_writer_fold_count)
    for round_index in range(profile.dagger_rounds + 1):
        round_root = root / f"round-{round_index:02d}"
        models_path = round_root / "MODELS.json"
        if resume and models_path.exists():
            saved = _load_json(models_path)
            if saved.get("design_digest") != design_digest:
                raise ValueError("Stage-6L closed-loop model checkpoint changed")
            fitted_rows = saved["fitted"]
        else:
            fitted_rows = {}
            for config in selected_configs:
                config_id = str(config["config_id"])
                fitted_rows[config_id] = _fit_one_writer(
                    datasets[config_id], config, contract, retain_fold_models=True
                )
            ar._atomic_json(
                models_path,
                {
                    "design_digest": design_digest,
                    "round": round_index,
                    "fitted": fitted_rows,
                },
            )
        latest = fitted_rows
        summaries = {
            config_id: {
                "stage_gate": bool(value["stage_gate"]),
                "selection_score": float(value["selection_score"]),
                "cross_validation": value["cross_validation"],
                "model_digest": value["model"]["model_digest"],
            }
            for config_id, value in fitted_rows.items()
        }
        round_result: dict[str, Any] = {
            "round": round_index,
            "writer_summaries": summaries,
            "dataset_rows": {key: len(value) for key, value in datasets.items()},
            "out_of_fold_rollout": True,
        }
        if round_index == profile.dagger_rounds or time.time() >= deadline:
            rounds.append(round_result)
            break
        assignments: list[tuple[dict[str, Any], Sequence[dict[str, Any]]]] = []
        candidate_to_config: dict[str, str] = {}
        for config_id, fitted in fitted_rows.items():
            for model in fitted["fold_models"]:
                fold = int(model["fold"])
                fold_pairs = [
                    pair for pair in pairs if fold_map[str(pair["pair_id"])] == fold
                ]
                candidate = _candidate_from_model(
                    source,
                    model,
                    suffix=f"dagger-r{round_index + 1}-oof",
                    support=8,
                    rehearsal=False,
                )
                assignments.append((candidate, fold_pairs))
                candidate_to_config[str(candidate["candidate_id"])] = config_id
        trace_rows, complete, total = _collect_traces(
            stage_root,
            f"dagger-round-{round_index + 1}-traces",
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
            datasets[candidate_to_config[str(row["candidate_id"])]].append(row)
        round_result.update(
            {
                "rollout_complete": complete,
                "completed_rollouts": len(trace_rows),
                "registered_rollouts": total,
                "next_round_dataset_rows": {
                    key: len(value) for key, value in datasets.items()
                },
            }
        )
        rounds.append(round_result)
        status(
            "running",
            "closed-loop-dataset-aggregation",
            completed=round_index + 1,
            total=profile.dagger_rounds,
            rollout_trajectories=len(trace_rows),
        )
        if not complete:
            break
    final_models = [
        value["model"]
        for _, value in sorted(
            latest.items(),
            key=lambda item: (-float(item[1]["selection_score"]), item[0]),
        )
        if bool(value["stage_gate"])
    ][: profile.dagger_base_models]
    if not final_models and latest and len(pairs) < contract.local_writer_fold_count * 2:
        final_models = [
            value["model"]
            for _, value in sorted(
                latest.items(), key=lambda item: (-float(item[1]["selection_score"]), item[0])
            )
        ][: profile.dagger_base_models]
    result = {
        "state": "complete" if len(rounds) == profile.dagger_rounds + 1 else "budget_truncated",
        "stage_gate": bool(final_models and len(rounds) == profile.dagger_rounds + 1),
        "registered_rounds": profile.dagger_rounds,
        "completed_rounds": max(0, len(rounds) - 1),
        "out_of_fold_rollout_generation": True,
        "pair_blocked_refitting": True,
        "rounds": rounds,
        "selected_model_ids": [model["model_id"] for model in final_models],
        "selected_model_digests": [model["model_digest"] for model in final_models],
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, final_models


def _metric_mean(
    rows: Sequence[dict[str, Any]], candidate_id: str, key: str, generation: int = 8
) -> float:
    values = wc._lineage_metric_values(rows, candidate_id, "intact", generation, key)
    return float(np.mean(values)) if values else 0.0


def _support_screen(
    stage_root: Path,
    source: dict[str, Any],
    models: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile: InverseDistillationProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: InverseDistillationContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = [
        _candidate_from_model(source, model, suffix=f"support{support}", support=support)
        for model in models
        for support in (8, 16)
    ]
    items = ar._make_items(
        list(pairs[: min(8, len(pairs))]),
        candidates,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="stage6l-support-screen",
        replicates=profile.trace_replicates,
        generations=8,
        conditions=("intact",),
        analysis_kind="stage6l-exposed-support-screen",
    )
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        "support-screen-trajectories",
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
    frozen_candidates: list[dict[str, Any]] = []
    for model in models:
        variants = [row for row in candidates if row["closure_model"]["model_id"] == model["model_id"]]
        for row in variants:
            candidate_id = str(row["candidate_id"])
            post = _metric_mean(rows, candidate_id, "post_washout_match_mean")
            terminal = _metric_mean(rows, candidate_id, "terminal_match_mean")
            summaries[candidate_id] = {
                "field_support_sweeps": int(row["field_support_sweeps"]),
                "post_washout_match_mean": post,
                "terminal_match_mean": terminal,
                "selection_score": 0.65 * post + 0.35 * terminal,
            }
        winner = max(
            variants,
            key=lambda row: (
                summaries[str(row["candidate_id"])]["selection_score"],
                -int(row["field_support_sweeps"]),
            ),
        )
        for rehearsal in (False, True):
            frozen_candidates.append(
                _candidate_from_model(
                    source,
                    model,
                    suffix=f"frozen-s{winner['field_support_sweeps']}-sr{int(rehearsal)}",
                    support=int(winner["field_support_sweeps"]),
                    rehearsal=rehearsal,
                )
            )
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and frozen_candidates),
        "screen_uses_exposed_pairs_only": True,
        "candidate_summaries": summaries,
        "frozen_candidate_ids": [row["candidate_id"] for row in frozen_candidates],
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(stage_root / "SUPPORT_SCREEN.json", result)
    ar._atomic_json(
        stage_root / "SEALED_STAGE6L_WRITERS.json",
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


def _field_decoder_summary(rows: Sequence[dict[str, Any]], candidate_id: str) -> dict[str, Any]:
    joint: list[float] = []
    subset: list[float] = []
    entry: list[float] = []
    energy: list[float] = []
    for row in rows:
        if str(row.get("candidate_id")) != candidate_id:
            continue
        result = row["conditions"]["intact"]
        for generation, field in result.get("inherited_field_history", {}).items():
            if int(generation) < 5:
                continue
            decoder = field.get("exit_decoder", {})
            if decoder.get("joint_balanced_accuracy") is not None:
                joint.append(float(decoder["joint_balanced_accuracy"]))
            if decoder.get("proper_subset_max_balanced_accuracy") is not None:
                subset.append(float(decoder["proper_subset_max_balanced_accuracy"]))
            entry.append(float(field.get("entry_payload_mean_abs", 0.0)))
            energy.append(float(field.get("field_peak_mean_abs", 0.0)))
    return {
        "joint_balanced_accuracy_mean": float(np.mean(joint)) if joint else 0.0,
        "proper_subset_balanced_accuracy_max": float(np.max(subset)) if subset else 1.0,
        "entry_payload_mean_abs": float(np.mean(entry)) if entry else 0.0,
        "field_peak_mean_abs": float(np.mean(energy)) if energy else 0.0,
        "field_specific_not_texture_decoder": True,
    }


def _narrow_validation(
    stage_root: Path,
    candidates: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile: InverseDistillationProfile,
    nested: pb.PhenotypeBridgeProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: InverseDistillationContract,
    design_digest: str,
    profile_name: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    proxy_profile = wc.WriterClosureProfile(
        exposed_pairs=profile.development_pairs,
        trace_replicates=profile.trace_replicates,
        oracle_pairs=0,
        oracle_replicates=0,
        heldout_pairs=len(pairs),
        heldout_replicates=profile.validation_replicates,
        mover_seeds_per_rule=0,
        mover_min_pairs=0,
        mover_min_discovered_pairs=0,
        bootstrap_resamples=profile.bootstrap_resamples,
        maximum_frozen_candidates=4,
    )
    heldout, rows = wc._run_heldout_lineages(
        stage_root,
        candidates,
        pairs,
        proxy_profile,
        replace(
            nested,
            qualification_pairs=len(pairs),
            qualification_replicates=profile.validation_replicates,
            bootstrap_resamples=profile.bootstrap_resamples,
        ),
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
    for candidate_id, summary in heldout["candidate_summaries"].items():
        decoder = _field_decoder_summary(rows, candidate_id)
        summary["field_decoder"] = decoder
        summary["measurement_gate"] = bool(
            decoder["joint_balanced_accuracy_mean"]
            >= contract.lineage_field_decoder_minimum
        )
        summary["joint_gate"] = bool(summary["static_gate"] and summary["measurement_gate"])
        if summary["joint_gate"]:
            qualified.append(candidate_id)
    heldout.update(
        {
            "stage_gate": bool(qualified),
            "qualified_candidate_ids": qualified,
            "procedural_recombined_validation": True,
            "procedural_pairs_frozen_before_simulation": True,
            "original_final_reserve_used": False,
        }
    )
    return heldout, rows


def _motion_seed_bank(rule: int, count: int, namespace: str) -> list[np.ndarray]:
    rng = np.random.default_rng(ar._hash_seed(namespace, "motion-seeds", rule, count))
    result: list[np.ndarray] = []
    seen: set[int] = set()
    while len(result) < count:
        mass = int(rng.integers(5, 13))
        selected = rng.choice(25, size=mass, replace=False)
        code = sum(1 << int(value) for value in selected)
        if code in seen:
            continue
        seen.add(code)
        board = np.zeros((32, 32), dtype=np.bool_)
        local = np.zeros((5, 5), dtype=np.bool_)
        local.reshape(-1)[selected] = True
        board[13:18, 13:18] = local
        result.append(board)
    return result


def _scan_motion_rule(rule: int, count: int, namespace: str) -> list[dict[str, Any]]:
    patterns = _motion_seed_bank(rule, count, namespace)
    discoveries: list[dict[str, Any]] = []
    for offset in range(0, len(patterns), 256):
        batch = np.stack(patterns[offset : offset + 256])
        history = [batch.copy()]
        state = batch
        for _ in range(48):
            state = life_like_step_batch(state, rule)
            history.append(state.copy())
        for local_index, initial in enumerate(batch):
            trajectory = [snapshot[local_index] for snapshot in history]
            detection = wc._detect_mover(trajectory)
            if detection is None:
                continue
            absolute = offset + local_index
            discoveries.append(
                {
                    "mover_id": f"stage6l-r{rule}-s{absolute:05d}",
                    "source": "stage6l-fresh-deterministic-5x5-scan",
                    "rule": int(rule),
                    "notation": life_rule_notation(rule),
                    "seed_index": absolute,
                    "initial_hex": wc._array_hex(initial),
                    **detection,
                }
            )
    return discoveries


def _motion_bank(
    stage_root: Path,
    profile: InverseDistillationProfile,
    contract: InverseDistillationContract,
    stage6k_root: Path,
    *,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    path = stage_root / "MOTION_BANK.json"
    if path.exists():
        return _load_json(path)
    exposed_panel = _load_json(stage6k_root / "stage6k/MOVER_PANEL.json")
    exposed_hex = {
        str(direction["initial_hex"])
        for pair in exposed_panel.get("pairs", [])
        for direction in (pair["forward"], pair["opposite"])
    }
    discoveries: list[dict[str, Any]] = []
    per_rule: dict[str, Any] = {}
    for index, rule in enumerate(wc.MOVER_RULES, start=1):
        if time.time() >= deadline:
            break
        rows = _scan_motion_rule(
            rule, profile.mover_seeds_per_rule, contract.namespace
        )
        rows = [row for row in rows if str(row["initial_hex"]) not in exposed_hex]
        discoveries.extend(rows)
        per_rule[str(rule)] = {
            "notation": life_rule_notation(rule),
            "scanned": profile.mover_seeds_per_rule,
            "fresh_detected": len(rows),
        }
        status(
            "running",
            "scan-fresh-motion-bank",
            completed=index,
            total=len(wc.MOVER_RULES),
            fresh_discoveries=len(discoveries),
        )
    total_needed = profile.mover_development_pairs + profile.mover_validation_pairs
    ordered = sorted(
        discoveries,
        key=lambda row: (
            ar._hash_seed(contract.namespace, "motion-allocation", row["mover_id"]),
            row["mover_id"],
        ),
    )
    pairs: list[dict[str, Any]] = []
    seen_shapes: set[tuple[Any, ...]] = set()
    for row in ordered:
        key = (
            int(row["rule"]),
            int(row["period"]),
            tuple(row["displacement_yx"]),
            str(row["initial_hex"]),
        )
        if key in seen_shapes:
            continue
        pair = wc._discovered_pair(row)
        if pair is None:
            continue
        seen_shapes.add(key)
        pairs.append(pair)
        if len(pairs) >= total_needed:
            break
    development = pairs[: profile.mover_development_pairs]
    validation = pairs[
        profile.mover_development_pairs : profile.mover_development_pairs
        + profile.mover_validation_pairs
    ]
    complete = len(pairs) == total_needed and len(per_rule) == len(wc.MOVER_RULES)
    allocation = {
        row["pair_id"]: "development" for row in development
    } | {row["pair_id"]: "validation" for row in validation}
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "rules": per_rule,
        "pairs": pairs,
        "allocation": allocation,
        "development_pair_count": len(development),
        "validation_pair_count": len(validation),
        "d4_families_not_split": True,
        "stage6k_initial_states_excluded": True,
        "allocation_digest": _digest(allocation),
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(path, result)
    return result


def _crop_centered(state: np.ndarray, size: int = 8) -> np.ndarray:
    values = np.asarray(state, dtype=np.bool_)
    coordinates = np.argwhere(values)
    if len(coordinates):
        center = np.rint((coordinates.min(axis=0) + coordinates.max(axis=0)) / 2).astype(int)
    else:
        center = np.asarray(values.shape) // 2
    offsets = np.arange(-(size // 2), size - size // 2)
    ys = (int(center[0]) + offsets) % values.shape[0]
    xs = (int(center[1]) + offsets) % values.shape[1]
    return values[np.ix_(ys, xs)].copy()


def _motion_features(history: Sequence[np.ndarray], endpoint: int) -> np.ndarray:
    selected = list(history[max(0, endpoint - 7) : endpoint + 1])
    while len(selected) < 8:
        selected.insert(0, selected[0])
    local = np.stack(
        [np.where(_crop_centered(state), 1.0, -1.0) for state in selected]
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


def _transform_velocity(displacement: Sequence[int], symmetry: int) -> tuple[float, float]:
    dy, dx = float(displacement[0]), float(displacement[1])
    if int(symmetry) >= 4:
        dx = -dx
    for _ in range(int(symmetry) % 4):
        dy, dx = -dx, dy
    scale = max(1.0, abs(dy), abs(dx))
    return dy / scale, dx / scale


def _motion_examples(pairs: Sequence[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    groups: list[str] = []
    for pair in pairs:
        for direction in ("forward", "opposite"):
            specification = pair[direction]
            initial = wc._unpack_state_hex(specification["initial_hex"], (32, 32))
            history = wc._simulate_history(initial, int(pair["rule"]), 48)
            period = int(specification["period"])
            for endpoint in range(16, 16 + period):
                feature = _motion_features(history, endpoint)
                current = np.where(_crop_centered(history[endpoint]), 1.0, -1.0).astype(np.float32)
                previous = np.where(_crop_centered(history[endpoint - 1]), 1.0, -1.0).astype(np.float32)
                change = np.float32(0.5) * (current - previous)
                for symmetry in range(8):
                    transformed_feature = feature[:-1].reshape(4, 8, 8)
                    transformed_feature = _d4_blocks(transformed_feature, symmetry)
                    transformed_current = _d4_blocks(current, symmetry)
                    transformed_change = _d4_blocks(change, symmetry)
                    vy, vx = _transform_velocity(specification["displacement_yx"], symmetry)
                    target = np.stack(
                        (
                            transformed_current,
                            transformed_change,
                            np.full((8, 8), vy, dtype=np.float32),
                            np.full((8, 8), vx, dtype=np.float32),
                        )
                    )
                    features.append(
                        np.concatenate(
                            (transformed_feature.reshape(-1), np.ones(1, dtype=np.float32))
                        )
                    )
                    targets.append(target.reshape(-1))
                    groups.append(str(pair["pair_id"]))
    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
        np.asarray(groups, dtype=str),
    )


def _fit_motion_writer(pairs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    features, targets, groups = _motion_examples(pairs)
    unique = sorted(set(groups.tolist()))
    fold_count = min(6, len(unique))
    folds = wc._pair_blocked_folds(groups, fold_count)
    candidates: list[dict[str, Any]] = []
    for kind in ("ridge", "rff"):
        fold_rows: list[dict[str, float]] = []
        for fold in range(fold_count):
            train = folds != fold
            test = folds == fold
            mean = np.mean(features[train], axis=0).astype(np.float32)
            scale = np.std(features[train], axis=0).astype(np.float32)
            scale = np.where(scale > 1e-6, scale, 1.0).astype(np.float32)
            x_train = (features[train] - mean) / scale
            x_test = (features[test] - mean) / scale
            projection: np.ndarray | None = None
            phase: np.ndarray | None = None
            if kind == "rff":
                rng = np.random.default_rng(ar._hash_seed("stage6l-motion-rff", fold))
                projection = rng.normal(0.0, 1.0 / math.sqrt(x_train.shape[1]), size=(x_train.shape[1], 192)).astype(np.float32)
                phase = rng.uniform(0.0, 2.0 * math.pi, size=192).astype(np.float32)
                x_train = np.float32(math.sqrt(2.0 / 192.0)) * np.cos(x_train @ projection + phase)
                x_test = np.float32(math.sqrt(2.0 / 192.0)) * np.cos(x_test @ projection + phase)
            weights, bias = wc._ridge_fit(x_train, targets[train], 0.30)
            prediction = np.clip(x_test @ weights + bias, -1.0, 1.0).reshape(-1, 4, 8, 8)
            wanted = targets[test].reshape(-1, 4, 8, 8)
            form = float(np.mean((prediction[:, 0] >= 0.0) == (wanted[:, 0] >= 0.0)))
            velocity = np.mean(prediction[:, 2:], axis=(2, 3))
            target_velocity = np.mean(wanted[:, 2:], axis=(2, 3))
            correct = np.sum(velocity * target_velocity, axis=1) > 0.0
            fold_rows.append({"form_accuracy": form, "direction_accuracy": float(np.mean(correct))})
        full = np.ones(len(features), dtype=np.bool_)
        mean = np.mean(features, axis=0).astype(np.float32)
        scale = np.std(features, axis=0).astype(np.float32)
        scale = np.where(scale > 1e-6, scale, 1.0).astype(np.float32)
        design = (features - mean) / scale
        model: dict[str, Any] = {"kind": kind, "input_mean": mean.tolist(), "input_scale": scale.tolist()}
        if kind == "rff":
            rng = np.random.default_rng(ar._hash_seed("stage6l-motion-rff", "full"))
            projection = rng.normal(0.0, 1.0 / math.sqrt(design.shape[1]), size=(design.shape[1], 192)).astype(np.float32)
            phase = rng.uniform(0.0, 2.0 * math.pi, size=192).astype(np.float32)
            design = np.float32(math.sqrt(2.0 / 192.0)) * np.cos(design @ projection + phase)
            model.update({"projection": projection.tolist(), "phase": phase.tolist()})
        weights, bias = wc._ridge_fit(design, targets, 0.30)
        model.update(
            {
                "weights": weights.tolist(),
                "bias": bias.tolist(),
                "output_shape": (4, 8, 8),
                "runtime_inputs": "visible-spacetime-only",
                "model_frozen": True,
                "runtime_target_labels": False,
            }
        )
        model["model_id"] = f"stage6l-motion-{kind}"
        model["model_digest"] = _digest(model)
        form_mean = float(np.mean([row["form_accuracy"] for row in fold_rows]))
        direction_mean = float(np.mean([row["direction_accuracy"] for row in fold_rows]))
        candidates.append(
            {
                "model": model,
                "folds": fold_rows,
                "form_accuracy_mean": form_mean,
                "direction_accuracy_mean": direction_mean,
                "selection_score": 0.65 * form_mean + 0.35 * direction_mean,
            }
        )
    return max(candidates, key=lambda row: (row["selection_score"], row["model"]["model_id"]))


def _predict_motion(model: dict[str, Any], history: Sequence[np.ndarray]) -> np.ndarray:
    feature = _motion_features(history, len(history) - 1)[None]
    mean = np.asarray(model["input_mean"], dtype=np.float32)
    scale = np.asarray(model["input_scale"], dtype=np.float32)
    design = (feature - mean) / scale
    if model["kind"] == "rff":
        projection = np.asarray(model["projection"], dtype=np.float32)
        phase = np.asarray(model["phase"], dtype=np.float32)
        design = np.float32(math.sqrt(2.0 / projection.shape[1])) * np.cos(design @ projection + phase)
    return np.clip(
        design @ np.asarray(model["weights"], dtype=np.float32)
        + np.asarray(model["bias"], dtype=np.float32),
        -1.0,
        1.0,
    ).reshape(4, 8, 8)


def _motion_codec_roundtrip(
    field: np.ndarray, seed: int, *, subset: bool = False
) -> tuple[np.ndarray, bool]:
    values = np.asarray(field, dtype=np.float32)
    codes = np.clip(np.rint(values * 7.0) + 7.0, 0, 15).astype(np.uint8).reshape(-1)
    rng = np.random.default_rng(seed)
    shares = rng.integers(0, 16, size=(4, len(codes)), dtype=np.uint8)
    shares[-1] = np.bitwise_xor.reduce(shares[:-1], axis=0) ^ codes
    if subset:
        shares = shares[:-1]
        valid = False
    else:
        valid = True
    reconstructed = np.bitwise_xor.reduce(shares, axis=0)
    decoded = np.clip((reconstructed.astype(np.float32) - 7.0) / 7.0, -1.0, 1.0)
    return decoded.reshape(values.shape), valid


def _install_motion_patch(patch: np.ndarray) -> np.ndarray:
    board = np.zeros((32, 32), dtype=np.bool_)
    board[12:20, 12:20] = np.asarray(patch) > 0.0
    return board


def _motion_condition_lineage(
    model: dict[str, Any],
    pair: dict[str, Any],
    direction: str,
    condition: str,
    generations: int = 4,
) -> dict[str, Any]:
    specification = pair[direction]
    opposite_name = "opposite" if direction == "forward" else "forward"
    opposite_specification = pair[opposite_name]
    initial = wc._unpack_state_hex(specification["initial_hex"], (32, 32))
    opposite_initial = wc._unpack_state_hex(opposite_specification["initial_hex"], (32, 32))
    history = wc._simulate_history(initial, int(pair["rule"]), 32)
    opposite_history = wc._simulate_history(opposite_initial, int(pair["rule"]), 32)
    stored: np.ndarray | None = None
    generation_rows: list[dict[str, Any]] = []
    for generation in range(1, generations + 1):
        written = _predict_motion(model, history)
        opposite_written = _predict_motion(model, opposite_history)
        if generation == 1 or condition != "no_renewal":
            stored = written.copy()
        if condition in ("zero", "read_disabled", "write_disabled"):
            incoming = np.zeros_like(written)
        elif condition == "shuffle":
            rng = np.random.default_rng(ar._hash_seed("stage6l-motion-shuffle", pair["pair_id"], direction, generation))
            incoming = stored.reshape(-1)[rng.permutation(stored.size)].reshape(stored.shape)
        elif condition == "opposite_direction":
            incoming = opposite_written
        elif condition == "phase_only":
            incoming = stored.copy()
            incoming[2:] = 0.0
        elif condition == "velocity_only":
            incoming = stored.copy()
            incoming[:2] = 0.0
        elif condition == "ablation" and generation >= 3:
            incoming = np.zeros_like(stored)
        elif condition == "matching_rescue" and generation == 3:
            incoming = written
        elif condition == "opposite_rescue" and generation == 3:
            incoming = opposite_written
        elif condition == "no_renewal" and generation > 1:
            incoming = np.zeros_like(stored)
        else:
            incoming = stored
        decoded, valid = _motion_codec_roundtrip(
            incoming,
            ar._hash_seed("stage6l-motion-codec", pair["pair_id"], direction, condition, generation),
        )
        reset = np.zeros((32, 32), dtype=np.bool_)
        if condition != "read_disabled" and valid:
            reset = _install_motion_patch(decoded[0])
        new_history = wc._simulate_history(reset, int(pair["rule"]), 48)
        detection = wc._detect_mover(new_history)
        direction_similarity = (
            wc._velocity_similarity(detection["displacement_yx"], specification["displacement_yx"])
            if detection is not None
            else 0.0
        )
        target_patch = np.where(_crop_centered(history[-1]), 1.0, -1.0)
        form_accuracy = float(np.mean((decoded[0] > 0.0) == (target_patch > 0.0)))
        generation_rows.append(
            {
                "generation": generation,
                "visible_reset_zero_before_carrier_read": True,
                "carrier_valid": valid,
                "form_accuracy": form_accuracy,
                "mover_detected": detection is not None,
                "correct_direction": bool(detection is not None and direction_similarity > 0.5),
                "direction_similarity": direction_similarity,
                "field_energy": float(np.mean(np.abs(decoded))),
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


def _run_motion_track(
    stage_root: Path,
    bank: dict[str, Any],
    profile: InverseDistillationProfile,
    contract: InverseDistillationContract,
    *,
    deadline: float,
) -> dict[str, Any]:
    development = [
        pair for pair in bank.get("pairs", []) if bank["allocation"].get(pair["pair_id"]) == "development"
    ]
    validation = [
        pair for pair in bank.get("pairs", []) if bank["allocation"].get(pair["pair_id"]) == "validation"
    ]
    if not development or not validation:
        return {
            "state": "budget_truncated",
            "stage_gate": False,
            "skipped_reason": "fresh motion bank incomplete",
            "final_audit_trajectory_state": "untouched",
        }
    if time.time() >= deadline:
        return {
            "state": "budget_truncated",
            "stage_gate": False,
            "skipped_reason": "hard deadline reached before motion fitting",
            "final_audit_trajectory_state": "untouched",
        }
    fitted = _fit_motion_writer(development)
    model = fitted["model"]
    conditions = (
        "intact",
        "zero",
        "shuffle",
        "opposite_direction",
        "phase_only",
        "velocity_only",
        "read_disabled",
        "write_disabled",
        "no_renewal",
        "ablation",
        "matching_rescue",
        "opposite_rescue",
    )
    pair_rows: list[dict[str, Any]] = []
    for pair in validation:
        if time.time() >= deadline:
            break
        results = {
            f"{direction}:{condition}": _motion_condition_lineage(
                model, pair, direction, condition
            )
            for direction in ("forward", "opposite")
            for condition in conditions
        }
        pair_rows.append({"pair_id": pair["pair_id"], "rule": pair["rule"], "conditions": results})
    if not pair_rows:
        return {
            "state": "budget_truncated",
            "stage_gate": False,
            "skipped_reason": "hard deadline reached before motion validation",
            "model": model,
            "final_audit_trajectory_state": "untouched",
        }
    complete = len(pair_rows) == len(validation) and time.time() < deadline
    intact = [
        result
        for row in pair_rows
        for key, result in row["conditions"].items()
        if key.endswith(":intact")
    ]
    final_recovery = float(np.mean([row["final_correct_direction"] for row in intact]))
    form = float(
        np.mean(
            [generation["form_accuracy"] for row in intact for generation in row["generations"]]
        )
    )
    margins: list[float] = []
    for row in pair_rows:
        for direction in ("forward", "opposite"):
            correct = row["conditions"][f"{direction}:intact"]["generations"][-1]["direction_similarity"]
            opposite = row["conditions"][f"{direction}:opposite_direction"]["generations"][-1]["direction_similarity"]
            margins.append(float(correct - opposite))
    direction_margin = float(np.mean(margins))
    control_recovery = {
        condition: float(
            np.mean(
                [
                    result["final_correct_direction"]
                    for row in pair_rows
                    for key, result in row["conditions"].items()
                    if key.endswith(f":{condition}")
                ]
            )
        )
        for condition in conditions
    }
    causal_specificity = bool(
        control_recovery["intact"] > control_recovery["zero"]
        and control_recovery["intact"] > control_recovery["read_disabled"]
        and control_recovery["matching_rescue"] > control_recovery["opposite_rescue"]
        and control_recovery["intact"] > control_recovery["no_renewal"]
    )
    gate = bool(
        complete
        and
        bank.get("stage_gate")
        and form >= contract.dynamic_form_minimum
        and direction_margin >= contract.dynamic_direction_margin_minimum
        and final_recovery >= contract.dynamic_recovery_minimum
        and causal_specificity
    )
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": gate,
        "development_pair_count": len(development),
        "validation_pair_count": len(validation),
        "model": model,
        "cross_validation": {key: value for key, value in fitted.items() if key != "model"},
        "form_accuracy_mean": form,
        "direction_margin_mean": direction_margin,
        "four_generation_correct_direction_recovery_fraction": final_recovery,
        "control_recovery": control_recovery,
        "causal_specificity_gate": causal_specificity,
        "carrier_shape": (4, 8, 8),
        "codec": "four-share q4 xor bottleneck",
        "visible_reset_every_boundary": True,
        "pair_results": pair_rows,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(stage_root / "MOTION_RESULTS.json", result)
    return result


def _campaign_result(
    output: Path,
    design_digest: str,
    profile_name: str,
    measurement: dict[str, Any],
    initial_fit: dict[str, Any],
    closed_loop: dict[str, Any],
    support: dict[str, Any],
    narrow: dict[str, Any],
    motion: dict[str, Any],
) -> dict[str, Any]:
    complete = all(
        stage.get("state") == "complete"
        for stage in (measurement, initial_fit, closed_loop, support, narrow, motion)
    )
    narrow_gate = bool(narrow.get("stage_gate", False))
    motion_gate = bool(motion.get("stage_gate", False))
    if not measurement.get("stage_gate", False):
        verdict = "INCONCLUSIVE_MEASUREMENT_FAILURE"
    elif not complete:
        verdict = "INCONCLUSIVE_RESOURCE_LIMIT"
    elif narrow_gate and motion_gate:
        verdict = "NARROW_AND_DYNAMIC_CA_WRITER_CLOSURE"
    elif narrow_gate:
        verdict = "NARROW_CA_WRITER_CLOSURE_ONLY"
    elif motion_gate:
        verdict = "DYNAMIC_CA_CARRIER_CLOSURE_ONLY"
    else:
        verdict = "STABLE_CARRIER_DISTILLATION_NOT_CAUSAL"
    qualified_narrow = list(narrow.get("qualified_candidate_ids", ()))
    result = {
        "experiment": "ca_motif_inverse_distillation_stage_6l",
        "design_digest": design_digest,
        "profile_name": profile_name,
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(narrow_gate or motion_gate),
        "verdict": verdict,
        "measurement_gate": bool(measurement.get("stage_gate", False)),
        "initial_writer_gate": bool(initial_fit.get("stage_gate", False)),
        "closed_loop_gate": bool(closed_loop.get("stage_gate", False)),
        "support_screen_gate": bool(support.get("stage_gate", False)),
        "narrow_writer_closure_gate": narrow_gate,
        "dynamic_multigeneration_gate": motion_gate,
        "mechanism_level_generality_gate": bool(narrow_gate and motion_gate),
        "qualified_narrow_candidate_ids": qualified_narrow,
        "original_final_reserve_opened": False,
        "final_audit_pair_count": 62,
        "final_audit_trajectory_state": "untouched",
        "claim_boundary": (
            "Synthetic cellular-automaton Plastic Heredity only when the narrow "
            "causal intervention ladder passes. Motion transfer alone is a "
            "carrier result, not biological life, memory, or agency."
        ),
        "phase_results": {
            "measurement": measurement,
            "initial_fit": initial_fit,
            "closed_loop": closed_loop,
            "support_screen": support,
            "narrow_validation": narrow,
            "motion": motion,
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
                "independent final-reserve adjudication requires a separately authorized stage"
                if narrow_gate
                else "retain the negative writer boundary and inspect the calibrated trace decomposition"
            ),
            "final_audit_trajectory_state": "untouched",
        },
    )
    report = (
        "# Stage 6L inverse-carrier distillation\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"The calibrated field measurement gate was `{result['measurement_gate']}`; "
        f"closed-loop narrow writer closure was `{narrow_gate}`; four-generation "
        f"moving-form transfer was `{motion_gate}`. The 62-pair final reserve was "
        "neither loaded nor simulated.\n"
    )
    lay = (
        "# Lay summary\n\n"
        "This round taught each daughter to write the durable instruction that a "
        "perfect carrier used successfully, then trained it on mistakes made by its "
        "own descendants. A success must still disappear when that note is erased or "
        "unreadable and return only with the matching note. Moving patterns were tested "
        "separately through repeated visible resets.\n\n"
        f"The registered outcome is **{verdict}**.\n"
    )
    ar._atomic_text(output / "REPORT.md", report)
    ar._atomic_text(output / "LAY_SUMMARY.md", lay)
    ar._atomic_text(output / "COMPLETE", "complete\n")
    return result


def _update_discovery_log(result: dict[str, Any], output: Path) -> None:
    path = ROOT / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"
    if not path.exists():
        return
    marker = f"Stage 6L design `{result['design_digest']}`"
    prior = path.read_text(encoding="utf-8")
    if marker in prior:
        return
    entry = (
        "\n\n## Stage 6L: inverse-carrier distillation and dialect closure\n\n"
        f"{marker} completed with verdict **{result['verdict']}**. The campaign "
        "calibrated the inherited-field decoder, trained stable q4 carrier targets, "
        "performed out-of-fold closed-loop dataset aggregation, tested newly "
        "recombined narrow pairs, and ran a separate four-generation moving-object "
        "track. The protected 62-pair reserve remained untouched.\n\n"
        f"Artifacts: `{output}`. Protocol: `CA_MOTIF_INVERSE_DISTILLATION_PROTOCOL.md`. "
        "Implementation: `plastic_ca/motif_inverse_distillation.py`.\n"
    )
    ar._atomic_text(path, prior.rstrip() + entry)


def run_motif_inverse_distillation(
    output: Path,
    *,
    stage6k_root: Path = DEFAULT_STAGE6K_ROOT,
    stage6j_root: Path = DEFAULT_STAGE6J_ROOT,
    stage6i_root: Path = DEFAULT_STAGE6I_ROOT,
    stage6h_root: Path = DEFAULT_STAGE6H_ROOT,
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
    """Run Stage 6L without any route to the original final reserve."""

    ar.require_pinned_numpy()
    if profile_name not in PROFILES:
        raise ValueError(f"unknown Stage-6L profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6L workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6L max-hours must be in (0, 8]")
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
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
            stage6k_root.resolve(),
            stage6j_root.resolve(),
            stage6i_root.resolve(),
            stage6h_root.resolve(),
            max_hours,
            resume=resume,
        )
        status = _status_writer(output, profile_name, campaign, active, workers)
        status("running", "frozen-design-verified")
        active[0] = "integrity"
        _write_phase(
            output,
            "integrity",
            design_digest,
            integrity | {"next_phase": "measurement"},
            "# Stage 6L integrity\n\nStage 6K and its untouched final-reserve boundary were hash-verified.",
            "# Lay summary\n\nThe previous result and the sealed final test set are accounted for before any new fitting.",
        )
        stage_root = output / "stage6l"
        frozen, cohorts, nested, writer_contract, templates = _reconstruct_cohorts(
            stage_root,
            profile_name,
            profile,
            integrity,
            stage6j_root.resolve(),
            stage6i_root.resolve(),
            stage6h_root.resolve(),
            roots,
        )
        source = wc._materialize_source_candidate(
            stage_root,
            stage6h_root.resolve(),
            stage6br_root.resolve(),
            design_digest,
        )

        active[0] = "measurement"
        measurement = _measurement_calibration(source, stage6k_root.resolve(), contract)
        _write_phase(
            output,
            "measurement",
            design_digest,
            measurement | {"next_phase": "cohorts"},
            "# Stage 6L measurement calibration\n\nThe two-channel slow-field codec was calibrated against exact, copied, opposite, random, and proper-subset payloads, then tied back to the positive Stage-6K oracle ceiling.",
            "# Lay summary\n\nWe first checked that the memory note can be read as a whole and cannot be reconstructed from a missing secret share.",
        )
        if not measurement["stage_gate"]:
            empty = {"state": "skipped", "stage_gate": False, "final_audit_trajectory_state": "untouched"}
            result = _campaign_result(
                output, design_digest, profile_name, measurement, empty, empty, empty, empty, empty
            )
            status("complete", "measurement-failure", verdict=result["verdict"])
            return result

        active[0] = "cohorts"
        cohort_payload = _load_json(stage_root / "COHORTS.json")
        _write_phase(
            output,
            "cohorts",
            design_digest,
            cohort_payload | {"state": "complete", "stage_gate": True, "next_phase": "initial-fit"},
            "# Stage 6L cohorts\n\nAll 56 exposed narrow pairs are developmental. Sixteen new donor-disjoint recombinations were frozen before their trajectories were simulated.",
            "# Lay summary\n\nThe writer learns from old cases and is then checked on newly assembled parent pairs it has never encountered.",
        )

        active[0] = "initial-fit"
        base_rows, trace_complete, trace_total = _collect_traces(
            stage_root,
            "initial-visible-traces",
            [(source, cohorts["development"])],
            templates,
            frozen,
            writer_contract,
            contract,
            design_digest,
            replicates=profile.trace_replicates,
            workers=workers,
            resume=resume,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
        )
        if trace_complete:
            initial_fit, selected_configs = _fit_factorial(
                stage_root,
                base_rows,
                profile_name,
                profile,
                contract,
                design_digest,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                status=status,
            )
        else:
            initial_fit = {
                "state": "budget_truncated",
                "stage_gate": False,
                "selected_config_ids": [],
                "final_audit_trajectory_state": "untouched",
            }
            selected_configs = []
        initial_fit.update(
            {
                "trace_collection_complete": trace_complete,
                "completed_trace_trajectories": len(base_rows),
                "registered_trace_trajectories": trace_total,
            }
        )
        _write_phase(
            output,
            "initial-fit",
            design_digest,
            initial_fit | {"next_phase": "closed-loop"},
            "# Stage 6L initial fitting\n\nTwenty-four q4 coefficient writers compared stable-oracle and inverse-control targets with D4 augmentation in pair-blocked folds.",
            "# Lay summary\n\nInstead of copying a fleeting picture, the writer tries to infer the stable instruction that actually helped the next daughter recover.",
        )

        active[0] = "closed-loop"
        if initial_fit.get("stage_gate") and selected_configs:
            closed_loop, models = _closed_loop_fit(
                stage_root,
                source,
                base_rows,
                cohorts["development"],
                selected_configs,
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
            closed_loop = {
                "state": "complete",
                "stage_gate": False,
                "skipped_reason": "no initial writer passed",
                "final_audit_trajectory_state": "untouched",
            }
            models = []
        _write_phase(
            output,
            "closed-loop",
            design_digest,
            closed_loop | {"next_phase": "support-screen"},
            "# Stage 6L closed-loop fitting\n\nThree out-of-fold dataset-aggregation rounds exposed each writer to visible histories caused by earlier versions of itself.",
            "# Lay summary\n\nThe writer practises on the imperfect descendants it actually creates, so small errors cannot hide behind perfect training examples.",
        )

        active[0] = "support-screen"
        if closed_loop.get("stage_gate") and models:
            support, candidates = _support_screen(
                stage_root,
                source,
                models,
                cohorts["development"],
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
            support = {
                "state": "complete",
                "stage_gate": False,
                "skipped_reason": "no closed-loop model passed",
                "final_audit_trajectory_state": "untouched",
            }
            candidates = []
        _write_phase(
            output,
            "support-screen",
            design_digest,
            support | {"next_phase": "narrow-validation"},
            "# Stage 6L support screen\n\nEight- and sixteen-sweep support were compared on exposed pairs; each selected support was frozen with rehearsal off and on.",
            "# Lay summary\n\nWe chose how long the inherited note should guide development before testing any new pair.",
        )

        active[0] = "narrow-validation"
        if support.get("stage_gate") and candidates:
            narrow, _ = _narrow_validation(
                stage_root,
                candidates,
                cohorts["procedural_validation"],
                profile,
                nested,
                templates,
                frozen,
                writer_contract,
                contract,
                design_digest,
                profile_name,
                workers=workers,
                resume=resume,
                deadline=float(campaign["hard_deadline_unix"]),
                status=status,
            )
        else:
            narrow = {
                "state": "complete",
                "stage_gate": False,
                "skipped_reason": "no frozen writer candidate",
                "qualified_candidate_ids": [],
                "final_audit_trajectory_state": "untouched",
            }
        _write_phase(
            output,
            "narrow-validation",
            design_digest,
            narrow | {"next_phase": "motion"},
            "# Stage 6L narrow validation\n\nFrozen writers faced new donor-disjoint pair identities and the full ablation, no-renewal, read/write-disable, matching-rescue, and opposite-rescue ladder.",
            "# Lay summary\n\nA genuine memory must help new daughters, stop helping when removed, and be restored by the right history rather than the wrong one.",
        )

        active[0] = "motion"
        bank = _motion_bank(
            stage_root,
            profile,
            contract,
            stage6k_root.resolve(),
            deadline=float(campaign["hard_deadline_unix"]),
            status=status,
        )
        motion = _run_motion_track(
            stage_root,
            bank,
            profile,
            contract,
            deadline=float(campaign["hard_deadline_unix"]),
        )
        _write_phase(
            output,
            "motion",
            design_digest,
            motion | {"next_phase": "adjudicate"},
            "# Stage 6L moving-form track\n\nA fresh mover bank trained a four-channel 8x8 carrier and tested direction through four visible-reset/rewrite boundaries under twelve interventions.",
            "# Lay summary\n\nMoving forms must preserve not just what they look like but which way their unfolding history is going.",
        )

        active[0] = "adjudicate"
        result = _campaign_result(
            output,
            design_digest,
            profile_name,
            measurement,
            initial_fit,
            closed_loop,
            support,
            narrow,
            motion,
        )
        _write_phase(
            output,
            "adjudicate",
            design_digest,
            result,
            "# Stage 6L adjudication\n\nNarrow causal closure, moving-form transfer, and mechanism-level generality are reported separately. No outcome opens the protected final reserve.",
            "# Lay summary\n\nThe conclusion separates a usable memory mechanism from pattern recognition and from a one-time reseeding trick.",
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
    "DEFAULT_STAGE6K_ROOT",
    "PHASES",
    "PROFILES",
    "InverseDistillationContract",
    "InverseDistillationProfile",
    "_measurement_calibration",
    "_motion_codec_roundtrip",
    "_procedural_pairs",
    "_writer_configs",
    "run_motif_inverse_distillation",
]
