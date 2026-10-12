"""Stage-6J adaptive two-buffer handoff and directed-trajectory heredity.

The campaign follows the negative Stage-6I boundary.  It first validates that
the temporal target has an identifiable arrow of time, then maps the physical
loss boundary, develops local adaptive handoffs on exposed pairs, and freezes
at most one candidate for each training-tier/form claim before held-out work.
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
from . import motif_consumptive_renewal as cr
from . import motif_phenotype_bridge as pb
from . import motif_trajectory_stabilization as ts


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_ADAPTIVE_HANDOFF_PROTOCOL.md"
DEFAULT_STAGE6I_ROOT = ROOT / "results/ca-motif-trajectory-stabilization-stage-6i"
DEFAULT_STAGE6H_ROOT = ROOT / "results/ca-motif-generational-transduction-stage-6h"
PHASES = (
    "integrity",
    "metric-audit",
    "forensics",
    "develop",
    "screen",
    "qualify",
    "endurance",
    "adjudicate",
)
TRAINING_TIERS = ("label-free", "rulebook-assisted")
FORM_CLAIMS = ("static", "dynamic")
CLAIM_GROUPS = tuple(
    f"{tier}-{claim}" for tier in TRAINING_TIERS for claim in FORM_CLAIMS
)
ARCHITECTURES = (
    "phase-latch-distiller",
    "dual-timescale-predictive-reservoir",
    "event-canonicalized-eligibility",
)

SCREEN_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
    "acquisition_write_disabled",
    "phenotype_scrub",
    "handoff_visible_scrub",
    "inherited_field_zero",
    "inherited_field_read_disabled",
    "inherited_field_write_disabled",
    "inherited_field_coefficient_shuffle",
    "inherited_field_copy_noise_5",
    "orbit_phase_shift",
    "orbit_temporal_reverse",
    "orbit_temporal_shuffle",
    "translator_ablation",
)
QUALIFICATION_CONDITIONS = tuple(
    dict.fromkeys(
        (
            *SCREEN_CONDITIONS,
            "inherited_field_no_renewal",
            "inherited_field_ablation",
            "inherited_field_same_rescue",
            "inherited_field_opposite_rescue",
            "translator_history_shuffle",
            "translator_weight_shuffle",
            "translator_bit_permutation",
            "writer_spatial_shift",
        )
    )
)
ENDURANCE_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
    "acquisition_write_disabled",
    "handoff_visible_scrub",
    "inherited_field_ablation",
    "inherited_field_no_renewal",
    "inherited_field_copy_noise_5",
    "orbit_phase_shift",
    "orbit_temporal_reverse",
    "orbit_temporal_shuffle",
)
AUDIT_CONDITIONS = tuple(
    dict.fromkeys(
        (
            *ENDURANCE_CONDITIONS,
            "inherited_field_zero",
            "inherited_field_read_disabled",
            "inherited_field_write_disabled",
            "inherited_field_coefficient_shuffle",
            "inherited_field_same_rescue",
            "inherited_field_opposite_rescue",
            "translator_ablation",
            "translator_history_shuffle",
        )
    )
)


@dataclass(frozen=True)
class AdaptiveHandoffProfile:
    development_pairs: int
    screen_pairs: int
    screen_replicates: int
    qualification_pairs: int
    qualification_replicates: int
    endurance_pairs: int
    endurance_replicates: int
    final_pairs: int
    final_replicates: int
    bootstrap_resamples: int
    candidate_limit: int


PROFILES = {
    "smoke": AdaptiveHandoffProfile(4, 2, 1, 2, 1, 1, 1, 2, 1, 100, 6),
    "reference": AdaptiveHandoffProfile(40, 8, 4, 8, 8, 8, 4, 62, 4, 10_000, 24),
}


@dataclass(frozen=True)
class AdaptiveHandoffContract(ts.TrajectoryStabilizationContract):
    implementation_version: str = "ca-motif-adaptive-handoff-v1"
    namespace: str = "plastic-ca-motif-adaptive-handoff-v1"
    maximum_promotable_writers: int = 24
    temporal_identifiability_minimum: float = 0.25
    temporal_identifiable_fraction_minimum: float = 0.75
    exploration_stop_hours: float = 4.5
    strict_alpha: float = 0.025
    final_strict_alpha: float = 0.0125

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "claim_groups": CLAIM_GROUPS,
                "training_tiers": TRAINING_TIERS,
                "adaptive_architectures": ARCHITECTURES,
                "two_buffer_handoff": True,
                "field_channels": ("form", "directed-transition"),
                "temporal_identifiability_minimum": self.temporal_identifiability_minimum,
                "temporal_identifiable_fraction_minimum": self.temporal_identifiable_fraction_minimum,
                "runtime_local_adaptation": True,
                "runtime_target_access": False,
                "runtime_generation_index": False,
                "parent_field_excluded_from_writer": True,
            }
        )
        return payload


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _phase_result_path(stage_root: Path, phase: str) -> Path:
    """Return the public phase result path from the private stage workspace."""
    return stage_root.parent / phase / "RESULTS.json"


def _parent_integrity(stage6i_root: Path, stage6h_root: Path) -> dict[str, Any]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "MANIFEST.json",
        "stage6i/COHORTS.json",
        "screen/RESULTS.json",
        "forensics/RESULTS.json",
        "COMPLETE",
    )
    missing = [stage6i_root / name for name in required if not (stage6i_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6I artifacts: {missing}")
    result = _load_json(stage6i_root / "RESULTS.json")
    status = _load_json(stage6i_root / "STATUS.json")
    cohorts = _load_json(stage6i_root / "stage6i/COHORTS.json")
    screen = _load_json(stage6i_root / "screen/RESULTS.json")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6I is incomplete")
    if result.get("verdict") != "NO_TRAJECTORY_OR_FIELD_HEREDITY":
        raise ValueError("Stage-6J requires the registered Stage-6I negative boundary")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6I protected reserve is no longer untouched")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6I cohort reserve is no longer untouched")
    if int(screen.get("completed_trajectories", 0)) != 320:
        raise ValueError("Stage-6J requires the complete 320-trajectory Stage-6I screen")
    parent_h = ts._parent_integrity(stage6h_root)
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "required_hashes": {name: ar._sha256(stage6i_root / name) for name in required},
        "stage6h_integrity": parent_h,
        "stage6i_screen_trajectory_count": 320,
        "final_pair_count": 62,
        "final_pair_ids_sha256": parent_h["final_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
    }


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6i_root: Path,
    stage6h_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[AdaptiveHandoffContract, AdaptiveHandoffProfile, dict[str, Any], str, dict[str, Any]]:
    contract = AdaptiveHandoffContract()
    profile = PROFILES[profile_name]
    integrity = _parent_integrity(stage6i_root, stage6h_root)
    design = {
        "experiment": "ca_motif_adaptive_handoff_stage_6j",
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(profile),
        "stage6i_root": str(stage6i_root.resolve()),
        "stage6h_root": str(stage6h_root.resolve()),
        "stage6i_required_hashes": integrity["required_hashes"],
        "cohort_route": {
            "development": "40 exposed Stage-6G/6H/6I pairs",
            "screen_and_qualification": "same eight frozen, previously unused pairs; no post-screen replacement",
            "endurance": "eight separate previously unused pairs",
            "adjudication": "62-pair protected reserve",
        },
        "candidate_factorial": {
            "architectures": ARCHITECTURES,
            "training_tiers": TRAINING_TIERS,
            "field_base_ranks": (8, 16),
            "handoff_schedules": ("short", "long"),
            "total": 24,
        },
        "limits": {
            "workers": 4,
            "max_hours": max_hours,
            "exploration_stop_hours": max_hours * 4.5 / 8.0,
            "protected_reserve_hours": max_hours * 3.5 / 8.0,
        },
        "implementation_hashes": {
            "motif_adaptive_handoff.py": ar._sha256(Path(__file__)),
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
            raise ValueError("Stage-6J output exists; use --resume")
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6J design changed during resume")
    else:
        ar._atomic_json(design_path, design)
        ar._atomic_json(
            output / "CLEANROOM_PROVENANCE.json",
            design["cleanroom"] | {"design_digest": design_digest},
        )
    campaign_path = output / "CAMPAIGN.json"
    if campaign_path.exists():
        campaign = _load_json(campaign_path)
        if not math.isclose(float(campaign["max_hours"]), max_hours):
            raise ValueError("Stage-6J max-hours changed during resume")
    else:
        started = time.time()
        campaign = {
            "experiment": design["experiment"],
            "design_digest": design_digest,
            "started_unix": started,
            "max_hours": max_hours,
            "exploration_deadline_unix": started + max_hours * 4.5 / 8.0 * 3600.0,
            "hard_deadline_unix": started + max_hours * 3600.0,
            "final_audit_reserve_hours": max_hours * 3.5 / 8.0,
            "deadline_persists_across_resume": True,
        }
        ar._atomic_json(campaign_path, campaign)
    return contract, profile, campaign, design_digest, integrity


def _status_writer(output: Path, profile_name: str, campaign: dict[str, Any], active: list[str]) -> Any:
    def write(state: str, current: str, **extra: Any) -> None:
        now = time.time()
        payload = {
            "state": state,
            "stage": "ca_motif_adaptive_handoff_stage_6j",
            "profile": profile_name,
            "phase": active[0],
            "current": current,
            "pid": os.getpid(),
            "workers_hard_max": 4,
            "started_unix": campaign["started_unix"],
            "updated_unix": now,
            "elapsed_seconds": now - float(campaign["started_unix"]),
            "deadline_remaining_seconds": max(0.0, float(campaign["hard_deadline_unix"]) - now),
            "exploration_deadline_unix": campaign["exploration_deadline_unix"],
            "hard_deadline_unix": campaign["hard_deadline_unix"],
            "final_audit_trajectory_state": "untouched",
            **extra,
        }
        ar._atomic_json(output / "STATUS.json", payload)
        progress = f" {extra['completed']}/{extra['total']}" if "completed" in extra else ""
        print(f"[{state}] stage6j-{active[0]}:{current}{progress}", flush=True)

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
        "experiment": "ca_motif_adaptive_handoff_stage_6j",
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
    profile: AdaptiveHandoffProfile,
    integrity: dict[str, Any],
    roots: dict[str, Path],
    *,
    auto_final_audit: bool,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], pb.PhenotypeBridgeProfile, ar.MotifContract, list[dict[str, Any]]]:
    frozen, base, nested, writer_contract, templates = ts._reconstruct_cohorts(
        stage_root,
        ts.PROFILES["reference"],
        integrity["stage6h_integrity"],
        roots,
        auto_final_audit=auto_final_audit,
    )
    exposed = [*base["development"], *base["screen"]]
    validation = list(base["qualification"])
    cohorts = {
        "development": exposed[: profile.development_pairs],
        "screen": validation[: profile.screen_pairs],
        "qualification": validation[: profile.qualification_pairs],
        "endurance": list(base["endurance"][: profile.endurance_pairs]),
        "final": [],
    }
    if len(cohorts["development"]) != profile.development_pairs:
        raise ValueError("Stage-6J exposed development cohort is incomplete")
    if [str(row["pair_id"]) for row in cohorts["screen"]] != [
        str(row["pair_id"]) for row in cohorts["qualification"]
    ]:
        raise AssertionError("Stage-6J frozen screen/qualification cohort changed")
    development_ids = {str(row["pair_id"]) for row in cohorts["development"]}
    validation_ids = {str(row["pair_id"]) for row in cohorts["screen"]}
    endurance_ids = {str(row["pair_id"]) for row in cohorts["endurance"]}
    if development_ids & validation_ids or development_ids & endurance_ids or validation_ids & endurance_ids:
        raise AssertionError("Stage-6J cohort evidential roles overlap")
    nested = replace(
        nested,
        screen_pairs=len(cohorts["screen"]),
        screen_replicates=profile.screen_replicates,
        qualification_pairs=len(cohorts["qualification"]),
        qualification_replicates=profile.qualification_replicates,
        endurance_pairs=len(cohorts["endurance"]),
        endurance_replicates=profile.endurance_replicates,
        final_pairs=profile.final_pairs,
        final_replicates=profile.final_replicates,
        bootstrap_resamples=profile.bootstrap_resamples,
        candidate_limit=profile.candidate_limit,
    )
    payload = {
        "development_pair_ids": {
            key: [str(pair["pair_id"]) for pair in rows]
            for key, rows in cohorts.items()
            if key != "final"
        },
        "development_pair_count": len(cohorts["development"]),
        "screen_and_qualification_same_frozen_pairs": True,
        "no_candidate_replacement_after_screen": True,
        "endurance_disjoint": True,
        "final_audit_pair_count": 62,
        "final_audit_pair_ids_sha256": integrity["final_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
        "final_audit_trajectories_not_loaded": True,
    }
    ar._atomic_json(stage_root / "STAGE6J_COHORTS.json", payload)
    ar._atomic_json(stage_root / "COHORTS.json", payload)
    return frozen, cohorts, nested, writer_contract, templates


def _candidate_specs(stage6h_root: Path) -> list[dict[str, Any]]:
    parent = _load_json(stage6h_root / "SEALED_GENERATIONAL_TRANSDUCERS.json")["candidates"]
    by_id = {str(row["candidate_id"]): row for row in parent}
    sources = {
        ("label-free", "phase-latch-distiller"): by_id["stage6h-label-free-full-temporal-median"],
        ("label-free", "dual-timescale-predictive-reservoir"): by_id["stage6h-label-free-full-multiscale-confidence"],
        ("label-free", "event-canonicalized-eligibility"): by_id["stage6h-label-free-full-transition-vote"],
        ("rulebook-assisted", "phase-latch-distiller"): by_id["stage6h-assisted-full-dagger"],
        ("rulebook-assisted", "dual-timescale-predictive-reservoir"): by_id["stage6h-assisted-full-rff"],
        ("rulebook-assisted", "event-canonicalized-eligibility"): by_id["stage6h-assisted-full-equivariant"],
    }
    field_architecture = {
        "phase-latch-distiller": "local-latch",
        "dual-timescale-predictive-reservoir": "local-reservoir",
        "event-canonicalized-eligibility": "transition-eligibility",
    }
    specs: list[dict[str, Any]] = []
    for tier in TRAINING_TIERS:
        for architecture in ARCHITECTURES:
            for rank in (8, 16):
                for schedule, support, write_sweeps in (
                    ("short", 8, 8),
                    ("long", 12, 12),
                ):
                    row = copy.deepcopy(sources[(tier, architecture)])
                    transform = row.get("writer_transform")
                    if transform and str(transform.get("input_mode", "stack")) == "stack":
                        input_dimension = len(transform.get("input_mean", ()))
                        if input_dimension <= 0 or input_dimension % 16:
                            raise ValueError(
                                "Stage-6J stack translator has no 4 by 4 temporal contract"
                            )
                        transform["temporal_view"] = "tail-trained-window"
                        transform["trained_trace_sweeps"] = input_dimension // 16
                    row.update(
                        {
                            "candidate_id": (
                                f"stage6j-{tier}-{architecture}-r{rank:02d}-{schedule}"
                            ),
                            "mechanism": "inherited-field",
                            "mechanism_tier": "inherited-field",
                            "adaptive_claim_tier": tier,
                            "selection_group": tier,
                            "claim_tier": "broad",
                            "writer_source": "visible",
                            "writer_input_contract": "visible-only-two-buffer",
                            "adaptive_architecture": architecture,
                            "field_architecture": field_architecture[architecture],
                            "field_rank": rank,
                            "field_channels": 2,
                            "field_retention": 0.95,
                            "field_bias": 0.65,
                            "field_support_sweeps": support,
                            "daughter_writer_start_offset": 5,
                            "daughter_writer_sweeps": write_sweeps,
                            "daughter_write_rate": 0.35,
                            "adapter_learning_rate": 0.35,
                            "adapter_retention": 0.80,
                            "event_threshold": 0.20,
                            "support_schedule": schedule,
                            "field_copy_corruption": 0.01,
                            "orbit_window_sweeps": 16,
                            "two_buffer_handoff": True,
                            "runtime_local_adaptation": True,
                            "runtime_generation_index": False,
                            "runtime_target_labels": False,
                            "parent_field_exposed_to_writer": False,
                            "promotable": True,
                        }
                    )
                    specs.append(row)
    if len(specs) != 24 or len({row["candidate_id"] for row in specs}) != 24:
        raise AssertionError("Stage-6J candidate factorial changed")
    return specs


def _seal_registry(stage_root: Path, specs: Sequence[dict[str, Any]], design_digest: str) -> None:
    selection_digest = _digest(list(specs))
    ar._atomic_json(
        stage_root / "WRITEBACK_CANDIDATES.json",
        {
            "design_digest": design_digest,
            "selection_digest": selection_digest,
            "selection_frozen_before_screen": True,
            "selection_frozen_before_validation": True,
            "promotable_count": len(specs),
            "maximum_candidates": 24,
            "runtime_local_adaptation": True,
            "runtime_target_labels": False,
            "runtime_generation_index": False,
            "parent_field_exposed_to_writer": False,
            "candidates": list(specs),
        },
    )
    bridge = stage_root / "bridge"
    bridge.mkdir(parents=True, exist_ok=True)
    ar._atomic_json(
        bridge / "RESULTS.json",
        {
            "experiment": "ca_motif_adaptive_handoff_stage_6j",
            "design_digest": design_digest,
            "phase": "bridge",
            "state": "complete",
            "stage_gate": True,
            "selection_digest": selection_digest,
            "final_audit_trajectory_state": "untouched",
        },
    )
    ar._atomic_text(bridge / "COMPLETE", "complete\n")


def _models(stage_root: Path, stage6br_root: Path) -> dict[str, dict[str, Any]]:
    rows, _ = pb._load_models(stage_root, stage6br_root)
    return {str(row["candidate_id"]): row for row in rows if row.get("promotable")}


def _metric_audit(contract: AdaptiveHandoffContract) -> dict[str, Any]:
    rng = np.random.default_rng(ar._hash_seed(contract.namespace, "metric-audit"))
    random = np.where(rng.random((13, 4, 4, 4)) < 0.4, 1.0, -1.0).astype(np.float32)
    base = random[0]
    travelling = np.stack(
        [np.roll(base, shift=index, axis=2) for index in range(13)], axis=0
    )
    constant = np.repeat(base[None], 13, axis=0)
    period2 = np.stack([base if index % 2 == 0 else -base for index in range(13)], axis=0)
    sequences = {
        "random-directed": random,
        "travelling": travelling,
        "constant-degenerate": constant,
        "period2-potentially-degenerate": period2,
    }
    diagnostics: dict[str, Any] = {}
    for name, sequence in sequences.items():
        opposite = -sequence
        seed = ar._hash_seed(contract.namespace, "metric-audit", name)
        intact = pb._directed_orbit_metrics(sequence, sequence, opposite, "intact", seed)
        shifted = pb._directed_orbit_metrics(
            np.roll(sequence, 3, axis=0), sequence, opposite, "intact", seed
        )
        reverse = pb._directed_orbit_metrics(
            sequence, sequence, opposite, "orbit_temporal_reverse", seed
        )
        shuffled = pb._directed_orbit_metrics(
            sequence, sequence, opposite, "orbit_temporal_shuffle", seed
        )
        reference = pb._directed_reference_diagnostic(sequence, opposite, seed)
        diagnostics[name] = {
            "intact": intact,
            "cyclic_shift": shifted,
            "reverse": reverse,
            "shuffle": shuffled,
            "reference": reference,
            "cyclic_invariance_error": abs(
                float(intact["directed_margin_mean"])
                - float(shifted["directed_margin_mean"])
            ),
        }
    gate = bool(
        diagnostics["random-directed"]["cyclic_invariance_error"] <= 1e-6
        and diagnostics["travelling"]["cyclic_invariance_error"] <= 1e-6
        and diagnostics["random-directed"]["reference"]["reference_directed_separation"]
        >= contract.temporal_identifiability_minimum
        and not diagnostics["constant-degenerate"]["reference"][
            "reference_temporally_identifiable"
        ]
    )
    return {
        "state": "complete",
        "stage_gate": gate,
        "dynamic_metric_gate": gate,
        "primary_metric": "directed-frame-plus-signed-transition-v1",
        "diagnostics": diagnostics,
        "stationary_or_symmetric_targets_flagged": True,
        "next_phase": "forensics",
        "final_audit_trajectory_state": "untouched",
    }


def _forensics(
    stage6i_root: Path,
    stage_root: Path,
    models: dict[str, dict[str, Any]],
    contract: AdaptiveHandoffContract,
) -> dict[str, Any]:
    parent = _load_json(stage6i_root / "screen/RESULTS.json")
    transient: list[dict[str, Any]] = []
    for candidate_id, bundle in parent.get("candidate_summaries", {}).items():
        static = bundle.get("static", {})
        if static.get("mechanism_tier") != "transient-field":
            continue
        transient.append(
            {
                "candidate_id": candidate_id,
                "read_effect": static.get("read_acquisition", {}).get("mean"),
                "post_washout_effect": static.get("post_washout_acquisition", {}).get("mean"),
                "active_rewrite_advantage": static.get("active_rewrite_advantage", {}).get("mean"),
                "joint_decoder": static.get("joint_decoder", {}).get("mean"),
            }
        )
    codec: dict[str, Any] = {}
    for base_rank in (8, 16):
        candidate = next(
            row
            for row in models.values()
            if int(row["field_rank"]) == base_rank
        )
        field_candidate = pb._field_codec_candidate(candidate)
        total_rank = int(field_candidate["rank"])
        rng = np.random.default_rng(
            ar._hash_seed(contract.namespace, "two-channel-codec", base_rank)
        )
        values = rng.uniform(-1.0, 1.0, size=(64, total_rank)).astype(np.float32)
        quantized, clipping = pb._quantize_frontend(values, field_candidate)
        shares, active = pb._encode_carrier(
            quantized, field_candidate, contract, "synthetic-two-channel", 5, "forensics"
        )
        copied, uncorrectable = pb._copy_carrier(
            shares,
            "synthetic-two-channel",
            5,
            32,
            contract,
            purpose="stage6j-two-channel-copy",
            corruption=0.01,
        )
        restored, valid = pb._joint_payload(copied, active, field_candidate)
        codec[f"two-channel-rank{base_rank}"] = {
            "valid_fraction": float(np.mean(valid)),
            "mean_absolute_error": float(np.mean(np.abs(restored - quantized))),
            "uncorrectable_fraction": float(uncorrectable),
            "quantizer_clipping": float(clipping),
        }
    best_transient = sorted(
        transient,
        key=lambda row: -float(row.get("read_effect") or 0.0),
    )[:6]
    loss_boundary = {
        "source": "Stage-6I exposed screen plus Stage-6J synthetic codec",
        "parent_field_copy": "operational" if all(row["valid_fraction"] == 1.0 for row in codec.values()) else "failed",
        "temporary_visible_support": "present" if any(float(row.get("read_effect") or 0.0) >= 0.25 for row in transient) else "absent",
        "post_support_internalization": "failed" if all(float(row.get("post_washout_effect") or 0.0) < 0.10 for row in transient) else "unresolved",
        "leading_transient_designs": best_transient,
        "codec_diagnostics": codec,
        "registered_tomography_offsets": (0, 2, 4, 8, "writer-end", "next-birth"),
    }
    ar._atomic_json(stage_root / "LOSS_BOUNDARY.json", loss_boundary)
    return {
        "state": "complete",
        "stage_gate": all(row["valid_fraction"] == 1.0 for row in codec.values()),
        "loss_boundary": loss_boundary,
        "next_phase": "develop",
        "final_audit_trajectory_state": "untouched",
    }


def _checkpoint_rows(root: Path) -> list[dict[str, Any]]:
    return ts._checkpoint_rows(root)


def _augment_static(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
    profile: pb.PhenotypeBridgeProfile,
    contract: AdaptiveHandoffContract,
    phase: str,
) -> dict[str, Any]:
    summary = ts._augment_static_summary(rows, candidate, generation, profile, contract, phase)
    candidate_id = str(candidate["candidate_id"])
    read_mean = float(summary["read_acquisition"].get("mean") or 0.0)
    handoff = cr._effect_values(
        rows, candidate_id, "handoff_visible_scrub", generation, "read_match_mean"
    )
    if handoff:
        summary["control_retention"]["handoff_visible_scrub"] = ts._retention(
            handoff, read_mean
        )
    relevant = [
        row["conditions"]["intact"]
        for row in rows
        if row.get("candidate_id") == candidate_id and "intact" in row.get("conditions", {})
    ]
    for key in (
        "daughter_field_zero_at_every_birth",
        "adaptive_state_zero_at_every_birth",
        "adaptive_state_zero_at_every_exit",
        "parent_field_erased_before_every_finalize",
        "parent_daughter_buffers_always_distinct",
    ):
        summary[f"{key}_fraction"] = float(
            np.mean([bool(row.get(key, False)) for row in relevant])
        ) if relevant else 0.0
    summary["adaptive_claim_tier"] = str(candidate["adaptive_claim_tier"])
    summary["adaptive_architecture"] = str(candidate["adaptive_architecture"])
    summary["two_buffer_handoff"] = bool(candidate.get("two_buffer_handoff"))
    return summary


def _directed_summary(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
    profile: pb.PhenotypeBridgeProfile,
    contract: AdaptiveHandoffContract,
    phase: str,
    static: dict[str, Any],
) -> dict[str, Any]:
    candidate_id = str(candidate["candidate_id"])
    intact = ts._effect_values(
        rows,
        candidate_id,
        "intact",
        generation,
        family="orbit_history",
        key="directed_margin_mean",
    )
    no_rewrite = ts._effect_values(
        rows,
        candidate_id,
        "no_rewrite",
        generation,
        family="orbit_history",
        key="directed_margin_mean",
    )
    active = [left - right for left, right in zip(intact, no_rewrite, strict=False)]
    intact_mean = float(np.mean(intact)) if intact else 0.0
    controls: dict[str, float] = {}
    control_effects: dict[str, Any] = {}
    for condition in QUALIFICATION_CONDITIONS:
        if condition in ("intact", "sham"):
            continue
        values = ts._effect_values(
            rows,
            candidate_id,
            condition,
            generation,
            family="orbit_history",
            key="directed_margin_mean",
        )
        if values:
            controls[condition] = ts._retention(values, intact_mean)
            control_effects[condition] = ts._bootstrap(
                values,
                profile,
                contract,
                phase,
                candidate_id,
                generation,
                condition,
            )
    opposite = ts._effect_values(
        rows,
        candidate_id,
        "inherited_field_opposite_rescue",
        generation,
        family="orbit_history",
        key="directed_margin_mean",
    )
    identifiable: list[float] = []
    separations: list[float] = []
    carrier_free: list[float] = []
    for row in rows:
        if row.get("candidate_id") != candidate_id:
            continue
        history = row.get("conditions", {}).get("intact", {}).get("orbit_history", {}).get(str(generation), {})
        if history:
            identifiable.append(float(bool(history.get("reference_temporally_identifiable", False))))
            separations.append(float(history.get("reference_directed_separation", 0.0)))
            carrier_free.append(float(history.get("carrier_erased_before_window", False)))
    return {
        "candidate_id": candidate_id,
        "adaptive_claim_tier": str(candidate["adaptive_claim_tier"]),
        "adaptive_architecture": str(candidate["adaptive_architecture"]),
        "directed_orbit_acquisition": ts._bootstrap(
            intact, profile, contract, phase, candidate_id, generation, "directed-orbit"
        ),
        "active_rewrite_advantage": ts._bootstrap(
            active, profile, contract, phase, candidate_id, generation, "directed-active"
        ),
        "opposite_rescue": ts._bootstrap(
            opposite, profile, contract, phase, candidate_id, generation, "directed-opposite"
        ),
        "control_retention": controls,
        "control_effects": control_effects,
        "temporal_identifiable_fraction": float(np.mean(identifiable)) if identifiable else 0.0,
        "reference_separation_mean": float(np.mean(separations)) if separations else 0.0,
        "joint_decoder": static["joint_decoder"],
        "proper_subset_decoder": static["proper_subset_decoder"],
        "survival_mean": static["survival_mean"],
        "carrier_free_window_fraction": float(np.mean(carrier_free)) if carrier_free else 0.0,
        "inherited_field_birth_valid_fraction": static["inherited_field_birth_valid_fraction"],
        "inherited_field_exit_valid_fraction": static["inherited_field_exit_valid_fraction"],
    }


def _lower(summary: dict[str, Any]) -> float:
    return ts._lower(summary)


def _upper(summary: dict[str, Any]) -> float:
    return ts._upper(summary)


def _buffer_invariants(summary: dict[str, Any]) -> bool:
    return bool(
        summary.get("two_buffer_handoff")
        and summary.get("daughter_field_zero_at_every_birth_fraction") == 1.0
        and summary.get("adaptive_state_zero_at_every_birth_fraction") == 1.0
        and summary.get("adaptive_state_zero_at_every_exit_fraction") == 1.0
        and summary.get("parent_field_erased_before_every_finalize_fraction") == 1.0
        and summary.get("parent_daughter_buffers_always_distinct_fraction") == 1.0
        and summary.get("inherited_field_birth_valid_fraction", 0.0) >= 0.90
        and summary.get("inherited_field_exit_valid_fraction", 0.0) >= 0.90
    )


def _static_gate(
    summary: dict[str, Any],
    contract: AdaptiveHandoffContract,
    *,
    qualification: bool = False,
) -> bool:
    controls = summary["control_retention"]
    gate = bool(
        float(summary["read_acquisition"].get("mean") or 0.0) >= contract.screen_read_minimum
        and _lower(summary["read_acquisition"]) > 0.0
        and float(summary["post_washout_acquisition"].get("mean") or 0.0) >= contract.screen_post_washout_minimum
        and float(summary["active_rewrite_advantage"].get("mean") or 0.0) >= contract.active_rewrite_minimum
        and _lower(summary["active_rewrite_advantage"]) > 0.0
        and _lower(summary["joint_decoder"]) >= contract.joint_accuracy_minimum
        and _upper(summary["proper_subset_decoder"]) <= contract.subset_accuracy_maximum
        and summary["survival_mean"] >= contract.survival_minimum
        and controls.get("no_rewrite", 1.0) <= 0.30
        and controls.get("read_disabled", 1.0) <= 0.30
        and controls.get("acquisition_write_disabled", 1.0) <= 0.30
        and controls.get("inherited_field_read_disabled", 1.0) <= 0.30
        and controls.get("inherited_field_write_disabled", 1.0) <= 0.30
        and controls.get("handoff_visible_scrub", 1.0) <= 0.30
        and _buffer_invariants(summary)
    )
    if qualification:
        opposite = summary.get("inherited_field_opposite_rescue", {})
        gate = bool(
            gate
            and float(summary["terminal_acquisition"].get("mean") or 0.0) >= 0.05
            and controls.get("inherited_field_ablation", 1.0) <= 0.30
            and controls.get("inherited_field_no_renewal", 1.0) <= 0.30
            and controls.get("inherited_field_same_rescue", 0.0) >= 0.70
            and float(opposite.get("mean") or 0.0) < 0.0
            and (
                summary["adaptive_claim_tier"] == "label-free"
                or controls.get("translator_ablation", 1.0) <= 0.30
            )
        )
    return gate


def _dynamic_gate(
    summary: dict[str, Any],
    static: dict[str, Any],
    contract: AdaptiveHandoffContract,
    *,
    qualification: bool = False,
) -> bool:
    controls = summary["control_retention"]
    effect = summary["directed_orbit_acquisition"]
    minimum = contract.orbit_generation16_minimum if qualification else contract.orbit_screen_effect_minimum
    gate = bool(
        float(effect.get("mean") or 0.0) >= minimum
        and _lower(effect) > 0.0
        and float(summary["active_rewrite_advantage"].get("mean") or 0.0) >= contract.active_rewrite_minimum
        and _lower(summary["active_rewrite_advantage"]) > 0.0
        and _lower(summary["joint_decoder"]) >= contract.joint_accuracy_minimum
        and _upper(summary["proper_subset_decoder"]) <= contract.subset_accuracy_maximum
        and summary["survival_mean"] >= contract.survival_minimum
        and summary["carrier_free_window_fraction"] == 1.0
        and summary["temporal_identifiable_fraction"] >= contract.temporal_identifiable_fraction_minimum
        and controls.get("no_rewrite", 1.0) <= 0.30
        and controls.get("read_disabled", 1.0) <= 0.30
        and controls.get("inherited_field_read_disabled", 1.0) <= 0.30
        and controls.get("inherited_field_write_disabled", 1.0) <= 0.30
        and controls.get("handoff_visible_scrub", 1.0) <= 0.30
        and controls.get("orbit_phase_shift", 0.0) >= contract.cyclic_phase_retention_minimum
        and controls.get("orbit_temporal_reverse", 1.0) <= contract.temporal_disruption_retention_maximum
        and controls.get("orbit_temporal_shuffle", 1.0) <= contract.temporal_disruption_retention_maximum
        and _buffer_invariants(static)
    )
    if qualification:
        gate = bool(
            gate
            and controls.get("inherited_field_ablation", 1.0) <= 0.30
            and controls.get("inherited_field_no_renewal", 1.0) <= 0.30
            and controls.get("inherited_field_same_rescue", 0.0) >= 0.70
            and float(summary["opposite_rescue"].get("mean") or 0.0) < 0.0
            and (
                static["adaptive_claim_tier"] == "label-free"
                or controls.get("translator_ablation", 1.0) <= 0.30
            )
        )
    return gate


def _bundle(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
    profile: pb.PhenotypeBridgeProfile,
    contract: AdaptiveHandoffContract,
    phase: str,
    *,
    qualification: bool = False,
    scientific: bool = True,
    metric_gate: bool = True,
) -> dict[str, Any]:
    static = _augment_static(rows, candidate, generation, profile, contract, f"{phase}-static")
    dynamic = _directed_summary(rows, candidate, generation, profile, contract, f"{phase}-dynamic", static)
    return {
        "candidate": pb._candidate_public(candidate),
        "static": static,
        "dynamic": dynamic,
        "static_gate": _static_gate(static, contract, qualification=qualification) if scientific else True,
        "dynamic_gate": (
            metric_gate
            and (_dynamic_gate(dynamic, static, contract, qualification=qualification) if scientific else True)
        ),
    }


def _ranking_score(bundle: dict[str, Any]) -> float:
    static = bundle["static"]
    dynamic = bundle["dynamic"]
    controls = static["control_retention"]
    causal = 1.0 - max(
        controls.get("inherited_field_read_disabled", 1.0),
        controls.get("inherited_field_write_disabled", 1.0),
        controls.get("handoff_visible_scrub", 1.0),
    )
    values = (
        float(static["post_washout_acquisition"].get("mean") or 0.0) / 0.10,
        float(dynamic["directed_orbit_acquisition"].get("mean") or 0.0) / 0.25,
        float(static["active_rewrite_advantage"].get("mean") or 0.0) / 0.15,
        causal / 0.70,
        float(static["survival_mean"]) / 0.90,
    )
    return float(min(values))


def _balanced_select(
    bundles: dict[str, dict[str, Any]],
    models: dict[str, dict[str, Any]],
    per_tier: int,
) -> list[str]:
    selected: list[str] = []
    for tier in TRAINING_TIERS:
        ids = [candidate_id for candidate_id in bundles if models[candidate_id]["adaptive_claim_tier"] == tier]
        architecture_best: list[str] = []
        for architecture in ARCHITECTURES:
            candidates = [candidate_id for candidate_id in ids if models[candidate_id]["adaptive_architecture"] == architecture]
            if candidates:
                architecture_best.append(
                    sorted(candidates, key=lambda cid: (-_ranking_score(bundles[cid]), cid))[0]
                )
        chosen = architecture_best[:per_tier]
        remaining = sorted(
            [candidate_id for candidate_id in ids if candidate_id not in chosen],
            key=lambda cid: (-_ranking_score(bundles[cid]), cid),
        )
        chosen.extend(remaining[: max(0, per_tier - len(chosen))])
        selected.extend(chosen[:per_tier])
    return sorted(selected)


def _run_items(
    stage_root: Path,
    name: str,
    phase: str,
    pairs: Sequence[dict[str, Any]],
    models: Sequence[dict[str, Any]],
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: AdaptiveHandoffContract,
    design_digest: str,
    *,
    replicates: int,
    generations: int,
    conditions: Sequence[str],
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
    analysis_kind: str = "lineage",
    extent: int = 16,
    scale_mode: str = "fixed",
    rule: int | None = None,
) -> tuple[list[dict[str, Any]], bool, int]:
    items = ar._make_items(
        pairs,
        models,
        ar._template_pairs(templates, "development" if phase.startswith("develop") else "qualification"),
        frozen["stage4"]["configuration"],
        phase=phase,
        replicates=replicates,
        generations=generations,
        conditions=conditions,
        extent=extent,
        scale_mode=scale_mode,
        analysis_kind=analysis_kind,
    )
    if rule is not None:
        for item in items:
            item["rule"] = int(rule)
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        name,
        items,
        models,
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


def _development_funnel(
    stage_root: Path,
    all_models: dict[str, dict[str, Any]],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: pb.PhenotypeBridgeProfile,
    profile_name: str,
    contract: AdaptiveHandoffContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
    metric_gate: bool,
) -> dict[str, Any]:
    if profile_name == "smoke":
        initial_ids = sorted(
            candidate_id
            for candidate_id, model in all_models.items()
            if int(model["field_rank"]) == 8 and model["support_schedule"] == "short"
        )
    else:
        initial_ids = sorted(all_models)
    round_specs = (
        ("round1", initial_ids, cohorts["development"][: min(8, len(cohorts["development"]))], 1, 8, 6),
        ("round2", None, cohorts["development"][: min(24, len(cohorts["development"]))], 2, 8, 3),
        ("round3", None, cohorts["development"], 4 if profile_name == "reference" else 1, 16, 3),
    )
    current = initial_ids
    rounds: dict[str, Any] = {}
    last_bundles: dict[str, Any] = {}
    for name, fixed_ids, pairs, replicates, generations, per_tier in round_specs:
        if fixed_ids is not None:
            current = list(fixed_ids)
        models = [all_models[candidate_id] for candidate_id in current]
        rows, complete, registered = _run_items(
            stage_root,
            f"development-{name}-trajectories-stage6j",
            f"develop-{name}",
            pairs,
            models,
            templates,
            frozen,
            writer_contract,
            contract,
            design_digest,
            replicates=replicates,
            generations=generations,
            conditions=SCREEN_CONDITIONS,
            workers=workers,
            resume=resume,
            deadline=deadline,
            status=status,
        )
        bundles = {
            str(model["candidate_id"]): _bundle(
                rows,
                model,
                generations,
                profile,
                contract,
                f"development-{name}",
                qualification=generations >= 16,
                scientific=False,
                metric_gate=metric_gate,
            )
            for model in models
        }
        for bundle in bundles.values():
            bundle["ranking_score"] = _ranking_score(bundle)
        selected = _balanced_select(bundles, all_models, min(per_tier, len(current)))
        if not complete:
            selected = []
        rounds[name] = {
            "state": "complete" if complete else "budget_truncated",
            "input_candidate_ids": current,
            "selected_candidate_ids": selected,
            "candidate_summaries": bundles,
            "completed_trajectories": len(rows),
            "registered_trajectories": registered,
        }
        current = selected
        last_bundles = bundles
        if not current:
            break
    winners: dict[str, str] = {}
    for tier in TRAINING_TIERS:
        tier_ids = [candidate_id for candidate_id in current if all_models[candidate_id]["adaptive_claim_tier"] == tier]
        if not tier_ids:
            continue
        for claim in FORM_CLAIMS:
            if claim == "static":
                key = lambda cid: (-float(last_bundles[cid]["static"]["post_washout_acquisition"].get("mean") or 0.0), cid)
            else:
                key = lambda cid: (-float(last_bundles[cid]["dynamic"]["directed_orbit_acquisition"].get("mean") or 0.0), cid)
            winners[f"{tier}-{claim}"] = sorted(tier_ids, key=key)[0]
    finalists = sorted(set(winners.values()))
    identifiable_values = [
        float(last_bundles[candidate_id]["dynamic"]["temporal_identifiable_fraction"])
        for candidate_id in finalists
        if candidate_id in last_bundles
    ]
    actual_identifiable_fraction = float(np.mean(identifiable_values)) if identifiable_values else 0.0
    dynamic_target_gate = bool(
        metric_gate
        and actual_identifiable_fraction >= contract.temporal_identifiable_fraction_minimum
    )
    if profile_name == "smoke":
        dynamic_target_gate = True
    frozen_payload = {
        "design_digest": design_digest,
        "winner_ids_by_claim_group": winners,
        "finalist_candidate_ids": finalists,
        "frozen_before_heldout_screen": True,
        "no_post_screen_replacement": True,
        "dynamic_target_gate": dynamic_target_gate,
        "actual_temporal_identifiable_fraction": actual_identifiable_fraction,
    }
    ar._atomic_json(stage_root / "FROZEN_FINALISTS.json", frozen_payload)
    ar._atomic_json(stage_root / "CANDIDATE_FUNNEL.json", {"rounds": rounds, **frozen_payload})
    ar._atomic_json(
        stage_root / "TEMPORAL_IDENTIFIABILITY.json",
        {
            "metric_gate": metric_gate,
            "actual_temporal_identifiable_fraction": actual_identifiable_fraction,
            "minimum": contract.temporal_identifiable_fraction_minimum,
            "dynamic_target_gate": dynamic_target_gate,
            "source": "Stage-6J exposed development trajectories",
        },
    )
    return {
        "state": "complete" if finalists else "budget_truncated",
        "stage_gate": bool(finalists),
        "rounds": rounds,
        "frozen_winner_ids": winners,
        "finalist_candidate_ids": finalists,
        "dynamic_target_gate": dynamic_target_gate,
        "actual_temporal_identifiable_fraction": actual_identifiable_fraction,
        "next_phase": "screen",
        "final_audit_trajectory_state": "untouched",
    }


def _skip_result(reason: str, id_key: str) -> dict[str, Any]:
    return {
        "state": "complete",
        "stage_gate": False,
        id_key: [],
        "candidate_summaries": {},
        "skipped_reason": reason,
        "final_audit_trajectory_state": "untouched",
    }


def _screen(
    stage_root: Path,
    all_models: dict[str, dict[str, Any]],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: pb.PhenotypeBridgeProfile,
    contract: AdaptiveHandoffContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
    scientific: bool,
) -> dict[str, Any]:
    development = _load_json(stage_root / "FROZEN_FINALISTS.json")
    finalists = list(development.get("finalist_candidate_ids", []))
    if not finalists:
        return _skip_result("development funnel failed", "selected_candidate_ids")
    models = [all_models[candidate_id] for candidate_id in finalists]
    rows, complete, registered = _run_items(
        stage_root,
        "screen-trajectories-stage6j",
        "screen",
        cohorts["screen"],
        models,
        templates,
        frozen,
        writer_contract,
        contract,
        design_digest,
        replicates=profile.screen_replicates,
        generations=8,
        conditions=SCREEN_CONDITIONS,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    bundles = {
        str(model["candidate_id"]): _bundle(
            rows,
            model,
            8,
            profile,
            contract,
            "screen",
            scientific=scientific,
            metric_gate=bool(development["dynamic_target_gate"]),
        )
        for model in models
    }
    winners: dict[str, str] = {}
    for group, candidate_id in development["winner_ids_by_claim_group"].items():
        claim = group.rsplit("-", 1)[1]
        if candidate_id in bundles and bundles[candidate_id][f"{claim}_gate"]:
            winners[group] = candidate_id
    selected = sorted(set(winners.values())) if complete else []
    return {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(selected),
        "candidate_summaries": bundles,
        "selected_candidate_ids": selected,
        "selected_by_claim_group": winners,
        "frozen_before_screen": True,
        "no_replacement": True,
        "completed_trajectories": len(rows),
        "registered_trajectories": registered,
        "final_audit_trajectory_state": "untouched",
    }


def _qualification(
    stage_root: Path,
    all_models: dict[str, dict[str, Any]],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: pb.PhenotypeBridgeProfile,
    contract: AdaptiveHandoffContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
    scientific: bool,
) -> dict[str, Any]:
    screen = _load_json(_phase_result_path(stage_root, "screen"))
    selected = list(screen.get("selected_candidate_ids", []))
    if not selected:
        return _skip_result("screen gate failed", "qualified_candidate_ids")
    models = [all_models[candidate_id] for candidate_id in selected]
    rows, complete, registered = _run_items(
        stage_root,
        "qualification-trajectories-stage6j",
        "qualification",
        cohorts["qualification"],
        models,
        templates,
        frozen,
        writer_contract,
        contract,
        design_digest,
        replicates=profile.qualification_replicates,
        generations=16,
        conditions=QUALIFICATION_CONDITIONS,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    bundles = {
        str(model["candidate_id"]): _bundle(
            rows,
            model,
            16,
            profile,
            contract,
            "qualification",
            qualification=True,
            scientific=scientific,
            metric_gate=True,
        )
        for model in models
    }
    winners: dict[str, str] = {}
    for group, candidate_id in screen.get("selected_by_claim_group", {}).items():
        claim = group.rsplit("-", 1)[1]
        if candidate_id in bundles and bundles[candidate_id][f"{claim}_gate"]:
            winners[group] = candidate_id
    qualified = sorted(set(winners.values())) if complete else []
    return {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(qualified),
        "qualification_candidate_ids": selected,
        "qualified_candidate_ids": qualified,
        "qualified_by_claim_group": winners,
        "candidate_summaries": bundles,
        "same_pairs_as_screen": True,
        "no_retuning_or_reselection": True,
        "completed_trajectories": len(rows),
        "registered_trajectories": registered,
        "final_audit_trajectory_state": "untouched",
    }


def _endurance(
    stage_root: Path,
    all_models: dict[str, dict[str, Any]],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: pb.PhenotypeBridgeProfile,
    contract: AdaptiveHandoffContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
    scientific: bool,
) -> dict[str, Any]:
    qualification = _load_json(_phase_result_path(stage_root, "qualify"))
    qualified = list(qualification.get("qualified_candidate_ids", []))
    if not qualified:
        return _skip_result("qualification gate failed", "enduring_candidate_ids")
    models = [all_models[candidate_id] for candidate_id in qualified]
    all_rows: list[dict[str, Any]] = []
    registered = 0
    rows, complete, count = _run_items(
        stage_root,
        "endurance-lineage-trajectories-stage6j",
        "endurance",
        cohorts["endurance"],
        models,
        templates,
        frozen,
        writer_contract,
        contract,
        design_digest,
        replicates=profile.endurance_replicates,
        generations=64,
        conditions=ENDURANCE_CONDITIONS,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    all_rows.extend(rows)
    registered += count
    scale_rows: dict[str, list[dict[str, Any]]] = {}
    rule_rows: dict[str, list[dict[str, Any]]] = {}
    for extent in (16, 32, 64):
        for mode in ("fixed", "diameter"):
            key = f"extent{extent}-{mode}"
            values, done, count = _run_items(
                stage_root,
                f"endurance-scale-{key}-stage6j",
                f"scale-{key}",
                cohorts["endurance"],
                models,
                templates,
                frozen,
                writer_contract,
                contract,
                design_digest,
                replicates=profile.endurance_replicates,
                generations=16,
                conditions=ENDURANCE_CONDITIONS,
                workers=workers,
                resume=resume,
                deadline=deadline,
                status=status,
                analysis_kind="scale",
                extent=extent,
                scale_mode=mode,
            )
            scale_rows[key] = values
            complete = complete and done
            registered += count
    for rule in pb.RULE_STRESS_PANEL:
        values, done, count = _run_items(
            stage_root,
            f"endurance-rule-{rule}-stage6j",
            f"rule-{rule}",
            cohorts["endurance"],
            models,
            templates,
            frozen,
            writer_contract,
            contract,
            design_digest,
            replicates=profile.endurance_replicates,
            generations=16,
            conditions=("intact", "sham", "no_rewrite"),
            workers=workers,
            resume=resume,
            deadline=deadline,
            status=status,
            analysis_kind="rule-stress",
            rule=rule,
        )
        rule_rows[str(rule)] = values
        complete = complete and done
        registered += count
    bundles: dict[str, Any] = {}
    for model in models:
        candidate_id = str(model["candidate_id"])
        static32 = _augment_static(rows, model, 32, profile, contract, "endurance-g32")
        static64 = _augment_static(rows, model, 64, profile, contract, "endurance-g64")
        dynamic32 = _directed_summary(rows, model, 32, profile, contract, "endurance-g32", static32)
        dynamic64 = _directed_summary(rows, model, 64, profile, contract, "endurance-g64", static64)
        scales: dict[str, Any] = {}
        static_scale_passes = 0
        dynamic_scale_passes = 0
        qualification_bundle = qualification["candidate_summaries"][candidate_id]
        q_static = float(qualification_bundle["static"]["post_washout_acquisition"].get("mean") or 0.0)
        q_dynamic = float(qualification_bundle["dynamic"]["directed_orbit_acquisition"].get("mean") or 0.0)
        for key, values in scale_rows.items():
            static = _augment_static(values, model, 16, profile, contract, f"scale-{key}")
            dynamic = _directed_summary(values, model, 16, profile, contract, f"scale-{key}", static)
            static_pass = float(static["post_washout_acquisition"].get("mean") or 0.0) >= 0.70 * q_static
            dynamic_pass = float(dynamic["directed_orbit_acquisition"].get("mean") or 0.0) >= 0.70 * q_dynamic
            static_scale_passes += int(static_pass)
            dynamic_scale_passes += int(dynamic_pass)
            scales[key] = {"static": static, "dynamic": dynamic, "static_pass": static_pass, "dynamic_pass": dynamic_pass}
        rules: dict[str, Any] = {}
        related_static = 0
        related_dynamic = 0
        for rule, values in rule_rows.items():
            static = _augment_static(values, model, 16, profile, contract, f"rule-{rule}")
            dynamic = _directed_summary(values, model, 16, profile, contract, f"rule-{rule}", static)
            s_pass = int(rule) != 70366 and float(static["read_acquisition"].get("mean") or 0.0) >= 0.70 * float(qualification_bundle["static"]["read_acquisition"].get("mean") or 0.0)
            d_pass = int(rule) != 70366 and float(dynamic["directed_orbit_acquisition"].get("mean") or 0.0) >= 0.70 * q_dynamic
            related_static += int(s_pass)
            related_dynamic += int(d_pass)
            rules[rule] = {"static": static, "dynamic": dynamic, "static_pass": s_pass, "dynamic_pass": d_pass}
        static_gate = bool(
            float(static32["post_washout_acquisition"].get("mean") or 0.0) >= 0.08
            and float(static64["post_washout_acquisition"].get("mean") or 0.0) >= 0.05
            and _lower(static64["post_washout_acquisition"]) > 0.0
            and static_scale_passes >= 4
            and related_static >= 4
            and _buffer_invariants(static64)
        ) if scientific else True
        dynamic_gate = bool(
            float(dynamic32["directed_orbit_acquisition"].get("mean") or 0.0) >= contract.orbit_generation32_minimum
            and _lower(dynamic32["directed_orbit_acquisition"]) > 0.0
            and float(dynamic64["directed_orbit_acquisition"].get("mean") or 0.0) >= contract.orbit_generation64_minimum
            and _lower(dynamic64["directed_orbit_acquisition"]) > 0.0
            and dynamic_scale_passes >= 4
            and related_dynamic >= 4
            and _buffer_invariants(static64)
        ) if scientific else True
        bundles[candidate_id] = {
            "candidate": pb._candidate_public(model),
            "static_generation32": static32,
            "static_generation64": static64,
            "dynamic_generation32": dynamic32,
            "dynamic_generation64": dynamic64,
            "scales": scales,
            "rules": rules,
            "static_scale_passes": static_scale_passes,
            "dynamic_scale_passes": dynamic_scale_passes,
            "static_related_rules_passed": related_static,
            "dynamic_related_rules_passed": related_dynamic,
            "static_gate": static_gate,
            "dynamic_gate": dynamic_gate,
        }
    winners: dict[str, str] = {}
    for group, candidate_id in qualification.get("qualified_by_claim_group", {}).items():
        claim = group.rsplit("-", 1)[1]
        if candidate_id in bundles and bundles[candidate_id][f"{claim}_gate"]:
            winners[group] = candidate_id
    enduring = sorted(set(winners.values())) if complete else []
    return {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(enduring),
        "endurance_candidate_ids": qualified,
        "enduring_candidate_ids": enduring,
        "enduring_by_claim_group": winners,
        "candidate_summaries": bundles,
        "completed_trajectories": len(all_rows) + sum(len(v) for v in scale_rows.values()) + sum(len(v) for v in rule_rows.values()),
        "registered_trajectories": registered,
        "final_audit_trajectory_state": "untouched",
    }


def _adjudication(
    stage_root: Path,
    all_models: dict[str, dict[str, Any]],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: pb.PhenotypeBridgeProfile,
    contract: AdaptiveHandoffContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
    scientific: bool,
    auto_final_audit: bool,
) -> dict[str, Any]:
    endurance = _load_json(_phase_result_path(stage_root, "endurance"))
    winners = dict(endurance.get("enduring_by_claim_group", {}))
    if not winners:
        return _skip_result("endurance gate failed", "confirmed_candidate_ids") | {
            "confirmed_claim_groups": [],
            "final_audit_opened": False,
        }
    if scientific and not auto_final_audit:
        raise ValueError("reference Stage-6J final audit lacks authorization")
    winner_ids = sorted(set(winners.values()))
    models = [all_models[candidate_id] for candidate_id in winner_ids]
    pair_digest = hashlib.sha256("\n".join(frozen["later_ids"]).encode()).hexdigest()
    ar._atomic_json(
        stage_root / "FINAL_AUDIT_DESIGN.json",
        {
            "design_digest": design_digest,
            "winner_ids_by_claim_group": winners,
            "winners_frozen_before_pair_loading": True,
            "pair_count": 62 if scientific else profile.final_pairs,
            "pair_ids_sha256": pair_digest if scientific else None,
            "conditions": AUDIT_CONDITIONS,
            "generations": 64,
            "final_alpha": contract.final_strict_alpha,
            "retuning": False,
        },
    )
    if scientific:
        final_pairs = ar.select_synergy_cohorts(
            frozen, ar.SYNERGY_PROFILES["reference"], "reference", open_final=True
        )["final"]
        if len(final_pairs) != 62:
            raise ValueError("Stage-6J final reserve is incomplete")
        pb._update_reserve_state(stage_root, "opened")
        reserve_state = "opened"
    else:
        final_pairs = cohorts["qualification"][: profile.final_pairs]
        reserve_state = "smoke-exposed-only"
    rows, complete, registered = _run_items(
        stage_root,
        "final-audit-trajectories-stage6j",
        "final-audit",
        final_pairs,
        models,
        templates,
        frozen,
        writer_contract,
        contract,
        design_digest,
        replicates=profile.final_replicates,
        generations=64,
        conditions=AUDIT_CONDITIONS,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
        analysis_kind="final",
    )
    final_contract = replace(contract, strict_alpha=contract.final_strict_alpha)
    bundles: dict[str, Any] = {}
    for model in models:
        candidate_id = str(model["candidate_id"])
        generations: dict[int, Any] = {}
        for generation in (8, 16, 64):
            generations[generation] = _bundle(
                rows,
                model,
                generation,
                profile,
                final_contract,
                f"final-g{generation}",
                qualification=generation >= 16,
                scientific=scientific,
                metric_gate=True,
            )
        bundles[candidate_id] = {
            "candidate": pb._candidate_public(model),
            "generation8": generations[8],
            "generation16": generations[16],
            "generation64": generations[64],
            "static_gate": bool(
                generations[8]["static_gate"]
                and generations[16]["static_gate"]
                and generations[64]["static_gate"]
                and float(generations[64]["static"]["post_washout_acquisition"].get("mean") or 0.0) >= 0.05
            ),
            "dynamic_gate": bool(
                generations[8]["dynamic_gate"]
                and generations[16]["dynamic_gate"]
                and generations[64]["dynamic_gate"]
                and float(generations[64]["dynamic"]["directed_orbit_acquisition"].get("mean") or 0.0) >= final_contract.orbit_generation64_minimum
            ),
        }
    confirmed_groups = [
        group
        for group, candidate_id in winners.items()
        if complete and bundles[candidate_id][f"{group.rsplit('-', 1)[1]}_gate"]
    ]
    confirmed_ids = sorted({winners[group] for group in confirmed_groups})
    final_digest = _digest({"winners": winners, "confirmed": confirmed_groups, "summaries": bundles})
    if scientific:
        reserve_state = "complete" if complete else "partial"
        pb._update_reserve_state(stage_root, reserve_state, final_digest=final_digest)
    return {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(confirmed_groups),
        "finalist_candidate_ids": winner_ids,
        "frozen_winner_ids": winners,
        "confirmed_candidate_ids": confirmed_ids,
        "confirmed_claim_groups": confirmed_groups,
        "candidate_summaries": bundles,
        "completed_trajectories": len(rows),
        "registered_trajectories": registered,
        "final_audit_opened": scientific,
        "final_audit_digest": final_digest,
        "final_audit_trajectory_state": reserve_state,
    }


def _campaign_result(
    output: Path,
    design_digest: str,
    profile_name: str,
    metric: dict[str, Any],
    development: dict[str, Any],
    screen: dict[str, Any],
    qualification: dict[str, Any],
    endurance: dict[str, Any],
    adjudication: dict[str, Any],
) -> dict[str, Any]:
    confirmed = list(adjudication.get("confirmed_claim_groups", []))
    claim_verdicts = {group: "confirmed" if group in confirmed else "not-confirmed" for group in CLAIM_GROUPS}
    states = [screen.get("state"), qualification.get("state"), endurance.get("state"), adjudication.get("state")]
    if profile_name == "smoke":
        verdict = "SMOKE_PATH_VALIDATED"
    elif "budget_truncated" in states:
        verdict = "INCONCLUSIVE_RESOURCE_LIMIT"
    elif confirmed:
        verdict = "ADAPTIVE_HANDOFF_PH_CONFIRMED"
    elif endurance.get("enduring_candidate_ids"):
        verdict = "FINAL_AUDIT_NOT_CONFIRMED"
    elif qualification.get("qualified_candidate_ids"):
        verdict = "ADAPTIVE_HANDOFF_NOT_ENDURING"
    elif screen.get("selected_candidate_ids"):
        verdict = "ONE_GENERATION_ADAPTIVE_HANDOFF"
    elif not development.get("dynamic_target_gate") and not screen.get("selected_candidate_ids"):
        verdict = "DYNAMIC_TARGET_NOT_IDENTIFIABLE_AND_NO_STATIC_HANDOFF"
    else:
        verdict = "NO_ADAPTIVE_HANDOFF_HEREDITY"
    result = {
        "experiment": "ca_motif_adaptive_handoff_stage_6j",
        "design_digest": design_digest,
        "profile_name": profile_name,
        "state": "complete",
        "stage_gate": bool(confirmed),
        "verdict": verdict,
        "claim_verdicts": claim_verdicts,
        "metric_gate": bool(metric.get("stage_gate")),
        "dynamic_target_gate": bool(development.get("dynamic_target_gate")),
        "selected_candidate_ids": screen.get("selected_candidate_ids", []),
        "qualified_candidate_ids": qualification.get("qualified_candidate_ids", []),
        "enduring_candidate_ids": endurance.get("enduring_candidate_ids", []),
        "confirmed_candidate_ids": adjudication.get("confirmed_candidate_ids", []),
        "confirmed_claim_groups": confirmed,
        "static_dynamic_claims_separate": True,
        "training_tiers_separate": True,
        "runtime_target_exposure": False,
        "runtime_local_adaptation": True,
        "two_buffer_handoff": True,
        "final_audit_opened": bool(adjudication.get("final_audit_opened", False)),
        "final_audit_trajectory_state": adjudication.get("final_audit_trajectory_state", "untouched"),
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
            "final_audit_trajectory_state": result["final_audit_trajectory_state"],
        },
    )
    report = [
        "# Stage 6J adaptive handoff and directed-trajectory heredity",
        "",
        f"Verdict: **{verdict}**.",
        "",
        "| Claim group | Verdict |",
        "|---|---|",
        *[f"| {group} | {claim_verdicts[group]} |" for group in CLAIM_GROUPS],
    ]
    ar._atomic_text(output / "REPORT.md", "\n".join(report) + "\n")
    if confirmed:
        lay = "At least one two-buffer daughter repeatedly internalized, renewed, and causally used inherited history after the visible lattice was reset."
    elif verdict == "INCONCLUSIVE_RESOURCE_LIMIT":
        lay = "The registered clock ended before the decisive adaptive-handoff tests finished."
    else:
        lay = "The copied parent field and the daughter's fresh field were kept physically separate, but no frozen mechanism completed the full internalization, renewal, rescue, and generational ladder."
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


def _update_discovery_log(result: dict[str, Any], output: Path) -> None:
    path = ROOT / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"
    marker = "<!-- CA_MOTIF_STAGE6J_RESULT -->"
    prior = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in prior:
        return
    entry = (
        "\n\n"
        + marker
        + "\n## CA motif-lineage Stage 6J — adaptive handoff and directed trajectories\n\n"
        + f"The registered campaign completed with verdict `{result['verdict']}`. "
        + "Label-free and rulebook-assisted local adaptation, and static and dynamic form, were adjudicated separately. "
        + f"Confirmed claim groups: {result.get('confirmed_claim_groups', [])}. "
        + f"The protected reserve ended in state `{result['final_audit_trajectory_state']}`.\n\n"
        + f"Pollable artifacts: `{output.relative_to(ROOT)}`. Protocol: "
        + "`CA_MOTIF_ADAPTIVE_HANDOFF_PROTOCOL.md`. Implementation: "
        + "`plastic_ca/motif_adaptive_handoff.py`.\n"
    )
    ar._atomic_text(path, prior.rstrip() + entry)


def run_motif_adaptive_handoff(
    output: Path,
    *,
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
    auto_final_audit: bool = False,
) -> dict[str, Any]:
    """Run the sealed Stage-6J adaptive handoff campaign."""

    ar.require_pinned_numpy()
    if profile_name not in PROFILES:
        raise ValueError(f"unknown Stage-6J profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6J workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6J max-hours must be in (0, 8]")
    if profile_name == "reference" and not auto_final_audit:
        raise ValueError("reference Stage-6J requires automatic final-audit authorization")
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
    campaign: dict[str, Any] | None = None
    status: Any = None
    try:
        contract, stage_profile, campaign, design_digest, integrity = _prepare_campaign(
            output,
            profile_name,
            stage6i_root.resolve(),
            stage6h_root.resolve(),
            max_hours,
            resume=resume,
        )
        status = _status_writer(output, profile_name, campaign, active)
        status("running", "frozen-design-verified")
        active[0] = "integrity"
        _write_phase(
            output,
            "integrity",
            design_digest,
            integrity | {"next_phase": "metric-audit"},
            "# Stage 6J integrity\n\nStage 6I, its exposed screen, and the untouched reserve boundary were hash-verified.",
            "# Lay summary\n\nThe new campaign starts exactly where the previous negative result stopped.",
        )
        stage_root = output / "stage6j"
        frozen, cohorts, profile, writer_contract, templates = _reconstruct_cohorts(
            stage_root,
            stage_profile,
            integrity,
            roots,
            auto_final_audit=auto_final_audit,
        )
        specs = _candidate_specs(stage6h_root.resolve())
        _seal_registry(stage_root, specs, design_digest)
        models = _models(stage_root, roots["stage6br_root"])

        active[0] = "metric-audit"
        metric = _metric_audit(contract)
        ar._atomic_json(stage_root / "METRIC_AUDIT.json", metric)
        _write_phase(
            output,
            "metric-audit",
            design_digest,
            metric,
            "# Stage 6J directed metric audit\n\nThe primary metric is phase invariant, direction sensitive, and explicitly flags degenerate temporal targets.",
            "# Lay summary\n\nA stationary picture is no longer mistaken for an ordered dance.",
        )

        active[0] = "forensics"
        forensics = _forensics(stage6i_root.resolve(), stage_root, models, contract)
        _write_phase(
            output,
            "forensics",
            design_digest,
            forensics,
            "# Stage 6J loss-boundary forensics\n\nThe inherited medium, temporary support, and post-support failure were adjudicated separately.",
            "# Lay summary\n\nCopying works and temporary guidance works; the suspected failure remains the daughter's internal handoff.",
        )

        scientific = profile_name == "reference"
        active[0] = "develop"
        development = _development_funnel(
            stage_root,
            models,
            cohorts,
            profile,
            profile_name,
            contract,
            writer_contract,
            templates,
            frozen,
            design_digest,
            workers=workers,
            resume=resume,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
            metric_gate=bool(metric["dynamic_metric_gate"]),
        )
        _write_phase(
            output,
            "develop",
            design_digest,
            development,
            "# Stage 6J adaptive development\n\nTwenty-four registered cells entered a three-round exposed-data funnel; finalists were frozen before held-out work.",
            "# Lay summary\n\nThe search narrowed local handoff designs without looking at any protected case.",
        )

        active[0] = "screen"
        screen = _screen(
            stage_root,
            models,
            cohorts,
            profile,
            contract,
            writer_contract,
            templates,
            frozen,
            design_digest,
            workers=workers,
            resume=resume,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
            scientific=scientific,
        )
        _write_phase(
            output,
            "screen",
            design_digest,
            screen | {"next_phase": "qualify"},
            "# Stage 6J held-out screen\n\nFrozen static/dynamic and label-free/assisted claims were tested without replacement.",
            "# Lay summary\n\nA design advanced only if its fresh daughter field mattered after the parent field vanished.",
        )

        active[0] = "qualify"
        qualification = _qualification(
            stage_root,
            models,
            cohorts,
            profile,
            contract,
            writer_contract,
            templates,
            frozen,
            design_digest,
            workers=workers,
            resume=resume,
            deadline=float(campaign["hard_deadline_unix"]),
            status=status,
            scientific=scientific,
        )
        _write_phase(
            output,
            "qualify",
            design_digest,
            qualification | {"next_phase": "endurance"},
            "# Stage 6J causal qualification\n\nGeneration-16 ablation, renewal, rescue, opposite-history, and translator controls were applied.",
            "# Lay summary\n\nRemoving the claimed cause had to remove the memory, and restoring the matching history had to bring it back.",
        )

        active[0] = "endurance"
        endurance = _endurance(
            stage_root,
            models,
            cohorts,
            profile,
            contract,
            writer_contract,
            templates,
            frozen,
            design_digest,
            workers=workers,
            resume=resume,
            deadline=float(campaign["hard_deadline_unix"]),
            status=status,
            scientific=scientific,
        )
        _write_phase(
            output,
            "endurance",
            design_digest,
            endurance | {"next_phase": "adjudicate"},
            "# Stage 6J endurance\n\nSurvivors faced generations 32/64, three extents, two scaling modes, and six rule transfers.",
            "# Lay summary\n\nA short-lived laboratory trick was not counted as heredity.",
        )

        active[0] = "adjudicate"
        adjudication = _adjudication(
            stage_root,
            models,
            cohorts,
            profile,
            contract,
            writer_contract,
            templates,
            frozen,
            design_digest,
            workers=workers,
            resume=resume,
            deadline=float(campaign["hard_deadline_unix"]),
            status=status,
            scientific=scientific,
            auto_final_audit=auto_final_audit,
        )
        _write_phase(
            output,
            "adjudicate",
            design_digest,
            adjudication,
            "# Stage 6J adjudication\n\nOnly completely qualified frozen claims could open the protected reserve.",
            "# Lay summary\n\nThe protected cases stayed hidden unless every earlier causal test succeeded.",
        )

        active[0] = "complete"
        result = _campaign_result(
            output,
            design_digest,
            profile_name,
            metric,
            development,
            screen,
            qualification,
            endurance,
            adjudication,
        )
        _update_discovery_log(result, output)
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
            status = _status_writer(output, profile_name, campaign, active)
        status("failed", "campaign-failed", error=repr(error))
        ar._atomic_json(
            output / "ERROR.json",
            {"error": repr(error), "phase": active[0], "updated_unix": time.time()},
        )
        raise


__all__ = (
    "AdaptiveHandoffContract",
    "AdaptiveHandoffProfile",
    "ARCHITECTURES",
    "CLAIM_GROUPS",
    "FORM_CLAIMS",
    "PHASES",
    "PROFILES",
    "TRAINING_TIERS",
    "run_motif_adaptive_handoff",
)
