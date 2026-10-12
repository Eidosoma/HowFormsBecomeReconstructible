"""Stage-6I phase-tolerant form and encoded slow-field heredity.

This clean-room follow-up treats a stable snapshot and an ordered local orbit
as separate claims.  It compares visible-only feedback, a zero-born transient
field, and a second field that physically crosses the reproduction bottleneck.
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
from . import motif_generational_transduction as gt
from . import motif_phenotype_bridge as pb


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_TRAJECTORY_STABILIZATION_PROTOCOL.md"
DEFAULT_STAGE6H_ROOT = ROOT / "results/ca-motif-generational-transduction-stage-6h"
PHASES = (
    "integrity",
    "forensics",
    "develop",
    "screen",
    "qualify",
    "endurance",
    "adjudicate",
)
MECHANISM_TIERS = ("visible-only", "transient-field", "inherited-field")
FORM_CLAIMS = ("static", "dynamic")
CLAIM_GROUPS = tuple(
    f"{tier}-{claim}" for tier in MECHANISM_TIERS for claim in FORM_CLAIMS
)

SCREEN_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
    "acquisition_write_disabled",
    "phenotype_scrub",
    "somatic_write_disabled",
    "somatic_bias_disabled",
    "inherited_field_zero",
    "inherited_field_read_disabled",
    "inherited_field_write_disabled",
    "inherited_field_coefficient_shuffle",
    "inherited_field_copy_noise_5",
    "orbit_phase_shift",
    "orbit_temporal_reverse",
    "orbit_temporal_shuffle",
    "translator_ablation",
    "writer_spatial_shift",
)
QUALIFICATION_CONDITIONS = tuple(
    dict.fromkeys(
        (
            *SCREEN_CONDITIONS,
            "zero_every_boundary",
            "shuffle_every_boundary",
            "ablate_after_g5",
            "rescue_same_enter_g6",
            "rescue_opposite_enter_g6",
            "somatic_ablation",
            "somatic_shuffle",
            "somatic_same_rescue",
            "somatic_opposite_rescue",
            "inherited_field_shuffle",
            "inherited_field_no_renewal",
            "inherited_field_ablation",
            "inherited_field_same_rescue",
            "inherited_field_opposite_rescue",
            "trace_write_disabled",
            "trace_read_disabled",
            "translator_history_shuffle",
            "translator_weight_shuffle",
            "translator_bit_permutation",
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
    "phenotype_scrub",
    "somatic_ablation",
    "inherited_field_ablation",
    "inherited_field_no_renewal",
    "inherited_field_copy_noise_5",
    "orbit_phase_shift",
    "orbit_temporal_reverse",
    "orbit_temporal_shuffle",
    "translator_ablation",
)
AUDIT_CONDITIONS = tuple(
    dict.fromkeys(
        (
            *ENDURANCE_CONDITIONS,
            "ablate_after_g5",
            "rescue_same_enter_g6",
            "rescue_opposite_enter_g6",
            "somatic_same_rescue",
            "somatic_opposite_rescue",
            "inherited_field_same_rescue",
            "inherited_field_opposite_rescue",
            "inherited_field_coefficient_shuffle",
            "translator_history_shuffle",
        )
    )
)


@dataclass(frozen=True)
class TrajectoryProfile:
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
    "smoke": TrajectoryProfile(4, 2, 1, 2, 1, 1, 1, 2, 1, 100, 18),
    "reference": TrajectoryProfile(32, 8, 4, 8, 8, 8, 4, 62, 4, 10_000, 18),
}


@dataclass(frozen=True)
class TrajectoryStabilizationContract(gt.GenerationalTransductionContract):
    implementation_version: str = "ca-motif-trajectory-stabilization-v1"
    namespace: str = "plastic-ca-motif-trajectory-stabilization-v1"
    maximum_promotable_writers: int = 18
    orbit_window_sweeps: int = 16
    orbit_screen_effect_minimum: float = 0.25
    orbit_post_carrier_minimum: float = 0.15
    orbit_generation16_minimum: float = 0.15
    orbit_generation32_minimum: float = 0.10
    orbit_generation64_minimum: float = 0.05
    cyclic_phase_retention_minimum: float = 0.70
    temporal_disruption_retention_maximum: float = 0.30
    exploration_stop_hours: float = 5.25

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "claim_groups": CLAIM_GROUPS,
                "mechanism_tiers": MECHANISM_TIERS,
                "static_and_dynamic_claims_independent": True,
                "orbit_window_sweeps": self.orbit_window_sweeps,
                "orbit_screen_effect_minimum": self.orbit_screen_effect_minimum,
                "orbit_post_carrier_minimum": self.orbit_post_carrier_minimum,
                "orbit_generation16_minimum": self.orbit_generation16_minimum,
                "orbit_generation32_minimum": self.orbit_generation32_minimum,
                "orbit_generation64_minimum": self.orbit_generation64_minimum,
                "cyclic_phase_retention_minimum": self.cyclic_phase_retention_minimum,
                "temporal_disruption_retention_maximum": self.temporal_disruption_retention_maximum,
                "inherited_field_copy": "q4-xor-four-share-hamming84-noisy",
                "visible_reset": True,
                "runtime_target_access": False,
            }
        )
        return payload


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _parent_integrity(stage6h_root: Path) -> dict[str, Any]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "MANIFEST.json",
        "SEALED_GENERATIONAL_TRANSDUCERS.json",
        "GENERATIONAL_DIALECT_MATRIX.json",
        "forensics/RESULTS.json",
        "stage6h/STAGE6H_COHORTS.json",
        "stage6h/screen/RESULTS.json",
        "COMPLETE",
    )
    missing = [stage6h_root / name for name in required if not (stage6h_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6H artifacts: {missing}")
    result = _load_json(stage6h_root / "RESULTS.json")
    status = _load_json(stage6h_root / "STATUS.json")
    cohorts = _load_json(stage6h_root / "stage6h/STAGE6H_COHORTS.json")
    screen = _load_json(stage6h_root / "stage6h/screen/RESULTS.json")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6H is incomplete")
    if result.get("verdict") != "GENERATIONAL_DIALECT_NOT_CORRECTED":
        raise ValueError("Stage-6I requires the registered Stage-6H negative boundary")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6H protected reserve is no longer untouched")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6H cohort reserve is no longer untouched")
    checkpoint_paths = sorted(
        (stage6h_root / "stage6h/screen-trajectories-stage6e/checkpoints").glob("*.json")
    )
    if len(checkpoint_paths) != 576 or screen.get("completed_trajectories") != 576:
        raise ValueError("Stage-6I requires all 576 Stage-6H validation checkpoints")
    inventory = [
        (path.name, path.stat().st_size, ar._sha256(path)) for path in checkpoint_paths
    ]
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "required_hashes": {name: ar._sha256(stage6h_root / name) for name in required},
        "validation_checkpoint_count": len(checkpoint_paths),
        "validation_checkpoint_inventory_sha256": _digest(inventory),
        "development_pair_ids": cohorts["development_pair_ids"],
        "final_pair_count": int(cohorts["final_audit_pair_count"]),
        "final_pair_ids_sha256": cohorts["final_audit_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
    }


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6h_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[TrajectoryStabilizationContract, TrajectoryProfile, dict[str, Any], str, dict[str, Any]]:
    contract = TrajectoryStabilizationContract()
    profile = PROFILES[profile_name]
    integrity = _parent_integrity(stage6h_root)
    design = {
        "experiment": "ca_motif_trajectory_stabilization_stage_6i",
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(profile),
        "stage6h_root": str(stage6h_root.resolve()),
        "stage6h_required_hashes": integrity["required_hashes"],
        "checkpoint_inventory_sha256": integrity["validation_checkpoint_inventory_sha256"],
        "cohort_route": {
            "development": "32 already exposed Stage-6G/6H pairs",
            "screen": "first eight still-unused Stage-6H qualification pairs",
            "qualification": "remaining eight still-unused qualification pairs",
            "endurance": "eight still-unused endurance pairs",
            "adjudication": "62-pair protected reserve",
        },
        "candidate_allocation": {
            "visible_only": 6,
            "transient_field": 6,
            "inherited_field": 6,
            "total": 18,
        },
        "limits": {
            "workers": 4,
            "max_hours": max_hours,
            "exploration_stop_hours": max_hours * 5.25 / 8.0,
            "final_reserve_hours": max_hours * 2.75 / 8.0,
        },
        "implementation_hashes": {
            "motif_trajectory_stabilization.py": ar._sha256(Path(__file__)),
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
            raise ValueError("Stage-6I output exists; use --resume")
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6I design changed during resume")
    else:
        ar._atomic_json(design_path, design)
        ar._atomic_json(output / "CLEANROOM_PROVENANCE.json", design["cleanroom"] | {"design_digest": design_digest})
    campaign_path = output / "CAMPAIGN.json"
    if campaign_path.exists():
        campaign = _load_json(campaign_path)
        if not math.isclose(float(campaign["max_hours"]), max_hours):
            raise ValueError("Stage-6I max-hours changed during resume")
    else:
        started = time.time()
        campaign = {
            "experiment": design["experiment"],
            "design_digest": design_digest,
            "started_unix": started,
            "max_hours": max_hours,
            "exploration_deadline_unix": started + max_hours * 5.25 / 8.0 * 3600.0,
            "hard_deadline_unix": started + max_hours * 3600.0,
            "final_audit_reserve_hours": max_hours * 2.75 / 8.0,
            "deadline_persists_across_resume": True,
        }
        ar._atomic_json(campaign_path, campaign)
    return contract, profile, campaign, design_digest, integrity


def _status_writer(output: Path, profile_name: str, campaign: dict[str, Any], active: list[str]) -> Any:
    def write(state: str, current: str, **extra: Any) -> None:
        now = time.time()
        payload = {
            "state": state,
            "stage": "ca_motif_trajectory_stabilization_stage_6i",
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
        print(f"[{state}] stage6i-{active[0]}:{current}{progress}", flush=True)

    return write


def _write_phase(output: Path, phase: str, design_digest: str, result: dict[str, Any], report: str, lay: str) -> None:
    root = output / phase
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment": "ca_motif_trajectory_stabilization_stage_6i",
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
            "final_audit_trajectory_state": payload.get("final_audit_trajectory_state", "untouched"),
        },
    )
    ar._atomic_text(root / "REPORT.md", report.rstrip() + "\n")
    ar._atomic_text(root / "LAY_SUMMARY.md", lay.rstrip() + "\n")
    ar._atomic_text(root / "COMPLETE", "complete\n")


def _reconstruct_cohorts(
    stage_root: Path,
    profile: TrajectoryProfile,
    integrity: dict[str, Any],
    roots: dict[str, Path],
    *,
    auto_final_audit: bool,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], pb.PhenotypeBridgeProfile, ar.MotifContract, list[dict[str, Any]]]:
    frozen, original, base_profile, _, writer_contract, templates, _ = pb._prepare_stage6e(
        stage_root,
        "reference",
        auto_final_audit=auto_final_audit,
        **roots,
    )
    parent_ids = integrity["development_pair_ids"]
    expected_routes = {
        "screen": list(parent_ids["training"]),
        "qualification-first": list(parent_ids["screen"]),
        "qualification-second": list(parent_ids["qualification"]),
        "endurance": list(parent_ids["endurance"]),
    }
    observed_routes = {
        "screen": [str(pair["pair_id"]) for pair in original["screen"]],
        "qualification-first": [
            str(pair["pair_id"]) for pair in original["qualification"][:16]
        ],
        "qualification-second": [
            str(pair["pair_id"]) for pair in original["qualification"][16:]
        ],
        "endurance": [str(pair["pair_id"]) for pair in original["endurance"]],
    }
    for name, observed in observed_routes.items():
        if observed != expected_routes[name]:
            raise ValueError(f"Stage-6I reconstructed {name} cohort changed")
    exposed_development = [*original["screen"], *original["qualification"][:16]]
    unused = original["qualification"][16:]
    cohorts = {
        "development": exposed_development[: profile.development_pairs],
        "screen": unused[: profile.screen_pairs],
        "qualification": unused[8 : 8 + profile.qualification_pairs],
        "endurance": original["endurance"][: profile.endurance_pairs],
        "final": [],
    }
    heldout = [str(pair["pair_id"]) for key in ("screen", "qualification", "endurance") for pair in cohorts[key]]
    if len(heldout) != len(set(heldout)):
        raise AssertionError("Stage-6I held-out cohorts overlap")
    if set(heldout) & set(frozen["later_ids"]):
        raise AssertionError("Stage-6I development touched the protected reserve")
    nested_profile = replace(
        base_profile,
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
    cohort_payload = {
        "development_pair_ids": {key: [str(pair["pair_id"]) for pair in rows] for key, rows in cohorts.items() if key != "final"},
        "development_previously_exposed": True,
        "screen_previously_unopened": True,
        "qualification_previously_unopened": True,
        "endurance_previously_unopened": True,
        "final_audit_pair_count": 62,
        "final_audit_pair_ids_sha256": integrity["final_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
        "final_audit_trajectories_not_loaded": True,
    }
    ar._atomic_json(stage_root / "STAGE6I_COHORTS.json", cohort_payload)
    ar._atomic_json(stage_root / "COHORTS.json", cohort_payload)
    return frozen, cohorts, nested_profile, writer_contract, templates


def _candidate_specs(stage6h_root: Path) -> list[dict[str, Any]]:
    parent = _load_json(stage6h_root / "SEALED_GENERATIONAL_TRANSDUCERS.json")["candidates"]
    by_id = {str(row["candidate_id"]): row for row in parent}
    visible_source = by_id["stage6h-assisted-full-dagger"]
    transient_sources = {
        "multi-timescale-ema": by_id["stage6h-assisted-full-somatic-multi-timescale-ema"],
        "local-reservoir": by_id["stage6h-assisted-full-somatic-local-reservoir"],
        "transition-eligibility": by_id["stage6h-assisted-full-somatic-transition-eligibility"],
    }
    specs: list[dict[str, Any]] = []
    for controller in ("hysteresis", "local-basin", "phase-compensator"):
        for schedule, support in (("short", 4), ("annealed", 8)):
            row = copy.deepcopy(visible_source)
            row.update(
                {
                    "candidate_id": f"stage6i-visible-{controller}-{schedule}",
                    "mechanism": "visible-stabilizer",
                    "mechanism_tier": "visible-only",
                    "selection_group": "visible-only",
                    "claim_tier": "strict",
                    "visible_controller": controller,
                    "visible_strength": 0.55,
                    "support_schedule": schedule,
                    "clearance_updates": support + 1,
                    "orbit_window_sweeps": 16,
                    "promotable": True,
                }
            )
            specs.append(row)
    for architecture, source in transient_sources.items():
        for schedule, support in (("short", 4), ("annealed", 8)):
            row = copy.deepcopy(source)
            row.update(
                {
                    "candidate_id": f"stage6i-transient-{architecture}-{schedule}",
                    "mechanism": "somatic-field",
                    "mechanism_tier": "transient-field",
                    "selection_group": "transient-field",
                    "claim_tier": "broad",
                    "support_schedule": schedule,
                    "somatic_support_sweeps": support,
                    "orbit_window_sweeps": 16,
                    "promotable": True,
                }
            )
            specs.append(row)
    for architecture in ("local-latch", "diffusing-phase"):
        for rank in (16, 8, 4):
            row = copy.deepcopy(visible_source)
            row.update(
                {
                    "candidate_id": f"stage6i-inherited-{architecture}-r{rank:02d}",
                    "mechanism": "inherited-field",
                    "mechanism_tier": "inherited-field",
                    "selection_group": "inherited-field",
                    "claim_tier": "broad",
                    "writer_source": "visible",
                    "writer_input_contract": "visible-only-plus-inherited-field-bias",
                    "field_architecture": architecture,
                    "field_rank": rank,
                    "field_retention": 0.95,
                    "field_bias": 0.65,
                    "field_support_sweeps": 4 if architecture == "local-latch" else 8,
                    "support_schedule": "short" if architecture == "local-latch" else "annealed",
                    "field_copy_corruption": 0.01,
                    "orbit_window_sweeps": 16,
                    "promotable": True,
                }
            )
            specs.append(row)
    if len(specs) != 18 or len({row["candidate_id"] for row in specs}) != 18:
        raise AssertionError("Stage-6I candidate allocation changed")
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
            "promotable_count": 18,
            "maximum_candidates": 18,
            "runtime_retraining": False,
            "runtime_target_labels": False,
            "runtime_generation_index": False,
            "candidates": list(specs),
        },
    )
    bridge = stage_root / "bridge"
    bridge.mkdir(parents=True, exist_ok=True)
    ar._atomic_json(
        bridge / "RESULTS.json",
        {
            "experiment": "ca_motif_trajectory_stabilization_stage_6i",
            "design_digest": design_digest,
            "phase": "bridge",
            "state": "complete",
            "stage_gate": True,
            "selection_digest": selection_digest,
            "final_audit_trajectory_state": "untouched",
        },
    )
    ar._atomic_text(bridge / "COMPLETE", "complete\n")


def _checkpoint_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "checkpoints").glob("*.json")):
        rows.append(_load_json(path)["result"])
    return rows


def _lower(summary: dict[str, Any]) -> float:
    interval = summary.get("ci", [None, None])
    return float(summary.get("mean") or 0.0) if interval[0] is None else float(interval[0])


def _upper(summary: dict[str, Any]) -> float:
    interval = summary.get("ci", [None, None])
    return float(summary.get("mean") or 0.0) if interval[1] is None else float(interval[1])


def _effect_values(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
    *,
    family: str,
    key: str,
) -> list[float]:
    values: list[float] = []
    for row in rows:
        if row.get("candidate_id") != candidate_id:
            continue
        conditions = row.get("conditions", {})
        if condition not in conditions or "sham" not in conditions:
            continue
        try:
            tested = float(conditions[condition][family][str(generation)][key])
            sham = float(conditions["sham"][family][str(generation)][key])
        except KeyError:
            continue
        values.append(tested - sham)
    return values


def _bootstrap(
    values: Sequence[float],
    profile: pb.PhenotypeBridgeProfile,
    contract: TrajectoryStabilizationContract,
    *key: Any,
) -> dict[str, Any]:
    return ar._bootstrap(
        list(values),
        profile.bootstrap_resamples,
        ar._hash_seed(contract.namespace, *key),
        contract.strict_alpha,
    )


def _retention(values: Sequence[float], intact_mean: float) -> float:
    return cr._ratio(float(np.mean(values)), intact_mean) if values else 1.0


def _augment_static_summary(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
    profile: pb.PhenotypeBridgeProfile,
    contract: TrajectoryStabilizationContract,
    phase: str,
) -> dict[str, Any]:
    summary = pb._summary(rows, candidate, generation, profile, contract, phase)
    candidate_id = str(candidate["candidate_id"])
    read_mean = float(summary["read_acquisition"].get("mean") or 0.0)
    for condition in (
        "inherited_field_zero",
        "inherited_field_read_disabled",
        "inherited_field_write_disabled",
        "inherited_field_no_renewal",
        "inherited_field_ablation",
        "inherited_field_coefficient_shuffle",
        "inherited_field_same_rescue",
        "inherited_field_copy_noise_5",
        "orbit_phase_shift",
        "orbit_temporal_reverse",
        "orbit_temporal_shuffle",
    ):
        values = cr._effect_values(
            rows, candidate_id, condition, generation, "read_match_mean"
        )
        if values:
            summary["control_retention"][condition] = _retention(values, read_mean)
    opposite = cr._effect_values(
        rows,
        candidate_id,
        "inherited_field_opposite_rescue",
        generation,
        "read_match_mean",
    )
    if opposite:
        summary["inherited_field_opposite_rescue"] = _bootstrap(
            opposite, profile, contract, phase, candidate_id, generation, "field-opposite"
        )
    relevant = [row for row in rows if row.get("candidate_id") == candidate_id]
    summary["inherited_field_birth_valid_fraction"] = float(
        np.mean(
            [
                row["conditions"]["intact"].get(
                    "inherited_field_birth_valid_fraction", 0.0
                )
                for row in relevant
            ]
        )
    ) if relevant else 0.0
    summary["inherited_field_exit_valid_fraction"] = float(
        np.mean(
            [
                row["conditions"]["intact"].get(
                    "inherited_field_exit_valid_fraction", 0.0
                )
                for row in relevant
            ]
        )
    ) if relevant else 0.0
    summary["mechanism_tier"] = str(candidate["mechanism_tier"])
    return summary


def _dynamic_summary(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
    profile: pb.PhenotypeBridgeProfile,
    contract: TrajectoryStabilizationContract,
    phase: str,
    static: dict[str, Any],
) -> dict[str, Any]:
    candidate_id = str(candidate["candidate_id"])
    intact = _effect_values(
        rows,
        candidate_id,
        "intact",
        generation,
        family="orbit_history",
        key="margin_mean",
    )
    no_rewrite = _effect_values(
        rows,
        candidate_id,
        "no_rewrite",
        generation,
        family="orbit_history",
        key="margin_mean",
    )
    active = [left - right for left, right in zip(intact, no_rewrite, strict=False)]
    intact_mean = float(np.mean(intact)) if intact else 0.0
    controls: dict[str, float] = {}
    control_bootstraps: dict[str, dict[str, Any]] = {}
    for condition in (
        "no_rewrite",
        "proper_subset",
        "read_disabled",
        "acquisition_write_disabled",
        "phenotype_scrub",
        "somatic_write_disabled",
        "somatic_bias_disabled",
        "somatic_ablation",
        "somatic_shuffle",
        "somatic_same_rescue",
        "inherited_field_zero",
        "inherited_field_read_disabled",
        "inherited_field_write_disabled",
        "inherited_field_no_renewal",
        "inherited_field_ablation",
        "inherited_field_coefficient_shuffle",
        "inherited_field_same_rescue",
        "inherited_field_copy_noise_5",
        "rescue_same_enter_g6",
        "orbit_phase_shift",
        "orbit_temporal_reverse",
        "orbit_temporal_shuffle",
        "translator_ablation",
        "translator_history_shuffle",
    ):
        values = _effect_values(
            rows,
            candidate_id,
            condition,
            generation,
            family="orbit_history",
            key="margin_mean",
        )
        if values:
            controls[condition] = _retention(values, intact_mean)
            control_bootstraps[condition] = _bootstrap(
                values,
                profile,
                contract,
                phase,
                candidate_id,
                generation,
                condition,
            )
    opposite_condition = {
        "visible-only": "rescue_opposite_enter_g6",
        "transient-field": "somatic_opposite_rescue",
        "inherited-field": "inherited_field_opposite_rescue",
    }[str(candidate["mechanism_tier"])]
    opposite = _effect_values(
        rows,
        candidate_id,
        opposite_condition,
        generation,
        family="orbit_history",
        key="margin_mean",
    )
    carrier_free: list[float] = []
    for row in rows:
        if row.get("candidate_id") != candidate_id:
            continue
        try:
            carrier_free.append(
                float(
                    row["conditions"]["intact"]["orbit_history"][str(generation)][
                        "carrier_erased_before_window"
                    ]
                )
            )
        except KeyError:
            continue
    return {
        "candidate_id": candidate_id,
        "mechanism_tier": str(candidate["mechanism_tier"]),
        "orbit_acquisition": _bootstrap(
            intact, profile, contract, phase, candidate_id, generation, "orbit"
        ),
        "active_rewrite_advantage": _bootstrap(
            active, profile, contract, phase, candidate_id, generation, "active"
        ),
        "opposite_rescue": _bootstrap(
            opposite, profile, contract, phase, candidate_id, generation, "opposite"
        ),
        "control_retention": controls,
        "control_effects": control_bootstraps,
        "joint_decoder": static["joint_decoder"],
        "proper_subset_decoder": static["proper_subset_decoder"],
        "survival_mean": static["survival_mean"],
        "carrier_free_window_fraction": float(np.mean(carrier_free)) if carrier_free else 0.0,
        "inherited_field_birth_valid_fraction": static["inherited_field_birth_valid_fraction"],
        "inherited_field_exit_valid_fraction": static["inherited_field_exit_valid_fraction"],
    }


def _tier_control_gate(summary: dict[str, Any], *, qualification: bool) -> bool:
    tier = str(summary["mechanism_tier"])
    controls = summary["control_retention"]
    if tier == "visible-only":
        gate = controls.get("phenotype_scrub", 1.0) <= 0.30
        if qualification:
            gate = gate and controls.get("rescue_same_enter_g6", 0.0) >= 0.70
    elif tier == "transient-field":
        gate = bool(
            controls.get("somatic_write_disabled", 1.0) <= 0.30
            and controls.get("somatic_bias_disabled", 1.0) <= 0.30
        )
        if qualification:
            gate = bool(
                gate
                and controls.get("somatic_ablation", 1.0) <= 0.30
                and controls.get("somatic_same_rescue", 0.0) >= 0.70
            )
    else:
        gate = bool(
            controls.get("inherited_field_read_disabled", 1.0) <= 0.30
            and controls.get("inherited_field_write_disabled", 1.0) <= 0.30
            and summary.get("inherited_field_birth_valid_fraction", 0.0) >= 0.90
            and summary.get("inherited_field_exit_valid_fraction", 0.0) >= 0.90
        )
        if qualification:
            gate = bool(
                gate
                and controls.get("inherited_field_ablation", 1.0) <= 0.30
                and controls.get("inherited_field_no_renewal", 1.0) <= 0.30
                and controls.get("inherited_field_same_rescue", 0.0) >= 0.70
            )
    return bool(gate)


def _static_screen_gate(summary: dict[str, Any], contract: TrajectoryStabilizationContract) -> bool:
    return bool(
        float(summary["read_acquisition"].get("mean") or 0.0) >= contract.screen_read_minimum
        and _lower(summary["read_acquisition"]) > 0.0
        and float(summary["post_washout_acquisition"].get("mean") or 0.0) >= contract.screen_post_washout_minimum
        and float(summary["active_rewrite_advantage"].get("mean") or 0.0) >= contract.active_rewrite_minimum
        and _lower(summary["active_rewrite_advantage"]) > 0.0
        and _lower(summary["joint_decoder"]) >= contract.joint_accuracy_minimum
        and _upper(summary["proper_subset_decoder"]) <= contract.subset_accuracy_maximum
        and summary["survival_mean"] >= contract.survival_minimum
        and summary["control_retention"].get("no_rewrite", 1.0) <= 0.30
        and summary["control_retention"].get("read_disabled", 1.0) <= 0.30
        and summary["control_retention"].get("acquisition_write_disabled", 1.0) <= 0.30
        and summary["control_retention"].get("translator_ablation", 1.0) <= 0.30
        and _tier_control_gate(summary, qualification=False)
    )


def _dynamic_screen_gate(summary: dict[str, Any], contract: TrajectoryStabilizationContract) -> bool:
    controls = summary["control_retention"]
    return bool(
        float(summary["orbit_acquisition"].get("mean") or 0.0) >= contract.orbit_screen_effect_minimum
        and _lower(summary["orbit_acquisition"]) > 0.0
        and float(summary["active_rewrite_advantage"].get("mean") or 0.0) >= contract.active_rewrite_minimum
        and _lower(summary["active_rewrite_advantage"]) > 0.0
        and _lower(summary["joint_decoder"]) >= contract.joint_accuracy_minimum
        and _upper(summary["proper_subset_decoder"]) <= contract.subset_accuracy_maximum
        and summary["survival_mean"] >= contract.survival_minimum
        and summary["carrier_free_window_fraction"] == 1.0
        and controls.get("no_rewrite", 1.0) <= 0.30
        and controls.get("read_disabled", 1.0) <= 0.30
        and controls.get("acquisition_write_disabled", 1.0) <= 0.30
        and controls.get("translator_ablation", 1.0) <= 0.30
        and controls.get("orbit_phase_shift", 0.0) >= contract.cyclic_phase_retention_minimum
        and controls.get("orbit_temporal_reverse", 1.0) <= contract.temporal_disruption_retention_maximum
        and controls.get("orbit_temporal_shuffle", 1.0) <= contract.temporal_disruption_retention_maximum
        and _tier_control_gate(summary, qualification=False)
    )


def _static_qualification_gate(summary: dict[str, Any], contract: TrajectoryStabilizationContract) -> bool:
    opposite = summary.get("inherited_field_opposite_rescue", summary.get("somatic_opposite_rescue", {}))
    tier = str(summary["mechanism_tier"])
    opposite_ok = True if tier == "visible-only" else float(opposite.get("mean") or 0.0) < 0.0
    return bool(
        _static_screen_gate(summary, contract)
        and float(summary["read_acquisition"].get("mean") or 0.0) >= 0.20
        and float(summary["post_washout_acquisition"].get("mean") or 0.0) >= 0.08
        and float(summary["terminal_acquisition"].get("mean") or 0.0) >= 0.05
        and _tier_control_gate(summary, qualification=True)
        and opposite_ok
    )


def _dynamic_qualification_gate(summary: dict[str, Any], contract: TrajectoryStabilizationContract) -> bool:
    return bool(
        float(summary["orbit_acquisition"].get("mean") or 0.0) >= contract.orbit_generation16_minimum
        and _lower(summary["orbit_acquisition"]) > 0.0
        and float(summary["active_rewrite_advantage"].get("mean") or 0.0) >= contract.active_rewrite_minimum
        and _lower(summary["active_rewrite_advantage"]) > 0.0
        and summary["carrier_free_window_fraction"] == 1.0
        and _tier_control_gate(summary, qualification=True)
        and float(summary["opposite_rescue"].get("mean") or 0.0) < 0.0
    )


def _select_by_claim(
    bundles: dict[str, dict[str, Any]],
    models: dict[str, dict[str, Any]],
    *,
    smoke: bool,
) -> dict[str, str]:
    winners: dict[str, str] = {}
    for tier in MECHANISM_TIERS:
        ids = sorted(candidate_id for candidate_id in bundles if models[candidate_id]["mechanism_tier"] == tier)
        for claim in FORM_CLAIMS:
            eligible = [candidate_id for candidate_id in ids if bundles[candidate_id][f"{claim}_gate"]]
            if not eligible and smoke and ids:
                eligible = ids[:1]
            if not eligible:
                continue
            metric = "post_washout_acquisition" if claim == "static" else "orbit_acquisition"
            winners[f"{tier}-{claim}"] = sorted(
                eligible,
                key=lambda candidate_id: (
                    -float(bundles[candidate_id][claim][metric].get("mean") or 0.0),
                    candidate_id,
                ),
            )[0]
    return winners


def _materialized_map(
    stage_root: Path, stage6br_root: Path, specs: Sequence[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    candidates, _ = pb._load_models(stage_root, stage6br_root)
    allowed = {str(row["candidate_id"]) for row in specs}
    return {
        str(candidate["candidate_id"]): candidate
        for candidate in candidates
        if str(candidate["candidate_id"]) in allowed
    }


def _run_screen(
    stage_root: Path,
    specs: Sequence[dict[str, Any]],
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: pb.PhenotypeBridgeProfile,
    contract: TrajectoryStabilizationContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    design_digest: str,
    stage6br_root: Path,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    scientific: bool,
    status: Any,
) -> dict[str, Any]:
    base = pb._run_screen(
        output=stage_root,
        frozen=frozen,
        cohorts=cohorts,
        profile=profile,
        contract=contract,
        writer_contract=writer_contract,
        templates=templates,
        design_digest=design_digest,
        stage6br_root=stage6br_root,
        workers=workers,
        resume=resume,
        deadline=deadline,
        scientific=scientific,
        status=status,
        conditions=SCREEN_CONDITIONS,
    )
    rows = _checkpoint_rows(stage_root / "screen-trajectories-stage6e")
    models = _materialized_map(stage_root, stage6br_root, specs)
    bundles: dict[str, dict[str, Any]] = {}
    for candidate_id, candidate in models.items():
        static = _augment_static_summary(
            rows, candidate, 8, profile, contract, "screen-static"
        )
        dynamic = _dynamic_summary(
            rows, candidate, 8, profile, contract, "screen-dynamic", static
        )
        bundles[candidate_id] = {
            "candidate": pb._candidate_public(candidate),
            "static": static,
            "dynamic": dynamic,
            "static_gate": _static_screen_gate(static, contract) if scientific else True,
            "dynamic_gate": _dynamic_screen_gate(dynamic, contract) if scientific else True,
        }
    winners = _select_by_claim(bundles, models, smoke=not scientific)
    selected = sorted(set(winners.values())) if base.get("state") == "complete" else []
    result = {
        **base,
        "stage_gate": bool(selected),
        "candidate_summaries": bundles,
        "selected_candidate_ids": selected,
        "selected_by_claim_group": winners,
        "static_dynamic_claims_separate": True,
        "stage6i_scientific_gate_applied": scientific,
    }
    ar._atomic_json(stage_root / "screen/RESULTS.json", result)
    return result


def _run_qualification(
    stage_root: Path,
    specs: Sequence[dict[str, Any]],
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: pb.PhenotypeBridgeProfile,
    contract: TrajectoryStabilizationContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    design_digest: str,
    stage6br_root: Path,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    scientific: bool,
    status: Any,
) -> dict[str, Any]:
    base = pb._run_qualification(
        output=stage_root,
        frozen=frozen,
        cohorts=cohorts,
        profile=profile,
        contract=contract,
        writer_contract=writer_contract,
        templates=templates,
        design_digest=design_digest,
        stage6br_root=stage6br_root,
        workers=workers,
        resume=resume,
        deadline=deadline,
        scientific=scientific,
        status=status,
        conditions=QUALIFICATION_CONDITIONS,
    )
    selected = list(
        _load_json(stage_root / "screen/RESULTS.json").get(
            "selected_candidate_ids", []
        )
    )
    if not selected or base.get("state") != "complete":
        return base
    rows = _checkpoint_rows(stage_root / "qualification-trajectories-stage6e")
    all_models = _materialized_map(stage_root, stage6br_root, specs)
    models = {candidate_id: all_models[candidate_id] for candidate_id in selected}
    bundles: dict[str, dict[str, Any]] = {}
    for candidate_id, candidate in models.items():
        static8 = _augment_static_summary(
            rows, candidate, 8, profile, contract, "qualification-static-g8"
        )
        static16 = _augment_static_summary(
            rows, candidate, 16, profile, contract, "qualification-static-g16"
        )
        dynamic8 = _dynamic_summary(
            rows, candidate, 8, profile, contract, "qualification-dynamic-g8", static8
        )
        dynamic16 = _dynamic_summary(
            rows,
            candidate,
            16,
            profile,
            contract,
            "qualification-dynamic-g16",
            static16,
        )
        bundles[candidate_id] = {
            "candidate": pb._candidate_public(candidate),
            "static_generation8": static8,
            "static_generation16": static16,
            "generation8": static8,
            "generation16": static16,
            "dynamic_generation8": dynamic8,
            "dynamic_generation16": dynamic16,
            "static": static16,
            "dynamic": dynamic16,
            "static_gate": _static_qualification_gate(static16, contract) if scientific else True,
            "dynamic_gate": _dynamic_qualification_gate(dynamic16, contract) if scientific else True,
        }
    screen_winners = _load_json(stage_root / "screen/RESULTS.json").get(
        "selected_by_claim_group", {}
    )
    winners: dict[str, str] = {}
    for group, candidate_id in screen_winners.items():
        claim = group.rsplit("-", 1)[1]
        if candidate_id in bundles and (
            bundles[candidate_id][f"{claim}_gate"] or not scientific
        ):
            winners[group] = candidate_id
    qualified = sorted(set(winners.values()))
    result = {
        **base,
        "stage_gate": bool(qualified),
        "qualification_candidate_ids": selected,
        "qualified_candidate_ids": qualified,
        "qualified_by_claim_group": winners,
        "candidate_summaries": bundles,
        "stage6i_scientific_gate_applied": scientific,
    }
    ar._atomic_json(stage_root / "qualify/RESULTS.json", result)
    return result


def _run_endurance(
    stage_root: Path,
    specs: Sequence[dict[str, Any]],
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: pb.PhenotypeBridgeProfile,
    contract: TrajectoryStabilizationContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    design_digest: str,
    stage6br_root: Path,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    scientific: bool,
    status: Any,
) -> dict[str, Any]:
    base = pb._run_endurance(
        output=stage_root,
        frozen=frozen,
        cohorts=cohorts,
        profile=profile,
        contract=contract,
        writer_contract=writer_contract,
        templates=templates,
        design_digest=design_digest,
        stage6br_root=stage6br_root,
        workers=workers,
        resume=resume,
        deadline=deadline,
        scientific=scientific,
        status=status,
        conditions=ENDURANCE_CONDITIONS,
    )
    qualification = _load_json(stage_root / "qualify/RESULTS.json")
    qualified = list(qualification.get("qualified_candidate_ids", []))
    if not qualified or base.get("state") != "complete":
        return base
    rows = _checkpoint_rows(stage_root / "endurance-trajectories-stage6e")
    all_models = _materialized_map(stage_root, stage6br_root, specs)
    models = {candidate_id: all_models[candidate_id] for candidate_id in qualified}
    bundles: dict[str, dict[str, Any]] = {}
    for candidate_id, candidate in models.items():
        lineage = [
            row
            for row in rows
            if row.get("analysis_kind") == "lineage"
            and row.get("candidate_id") == candidate_id
        ]
        static32 = _augment_static_summary(
            lineage, candidate, 32, profile, contract, "endurance-static-g32"
        )
        static64 = _augment_static_summary(
            lineage, candidate, 64, profile, contract, "endurance-static-g64"
        )
        dynamic32 = _dynamic_summary(
            lineage, candidate, 32, profile, contract, "endurance-dynamic-g32", static32
        )
        dynamic64 = _dynamic_summary(
            lineage, candidate, 64, profile, contract, "endurance-dynamic-g64", static64
        )
        static_scales: dict[str, Any] = {}
        dynamic_scales: dict[str, Any] = {}
        scale_passes = 0
        qualification_effect = float(
            qualification["candidate_summaries"][candidate_id]["dynamic_generation16"][
                "orbit_acquisition"
            ].get("mean")
            or 0.0
        )
        for extent in (16, 32, 64):
            for scale_mode in ("fixed", "diameter"):
                key = f"extent{extent}-{scale_mode}"
                selected_rows = [
                    row
                    for row in rows
                    if row.get("analysis_kind") == "scale"
                    and row.get("candidate_id") == candidate_id
                    and int(row.get("extent")) == extent
                    and row.get("scale_mode") == scale_mode
                ]
                static_scale = _augment_static_summary(
                    selected_rows,
                    candidate,
                    16,
                    profile,
                    contract,
                    f"endurance-static-{key}",
                )
                dynamic_scale = _dynamic_summary(
                    selected_rows,
                    candidate,
                    16,
                    profile,
                    contract,
                    f"endurance-dynamic-{key}",
                    static_scale,
                )
                static_scales[key] = static_scale
                dynamic_scales[key] = dynamic_scale
                scale_passes += int(
                    float(dynamic_scale["orbit_acquisition"].get("mean") or 0.0)
                    >= 0.70 * qualification_effect
                    and _lower(dynamic_scale["orbit_acquisition"]) > 0.0
                )
        related_rules_passed = 0
        rule_dynamic: dict[str, Any] = {}
        for rule in pb.RULE_STRESS_PANEL:
            rule_rows = [
                row
                for row in rows
                if row.get("analysis_kind") == "rule-stress"
                and row.get("candidate_id") == candidate_id
                and int(row.get("rule")) == rule
            ]
            rule_static = _augment_static_summary(
                rule_rows,
                candidate,
                16,
                profile,
                contract,
                f"endurance-rule-static-{rule}",
            )
            rule_summary = _dynamic_summary(
                rule_rows,
                candidate,
                16,
                profile,
                contract,
                f"endurance-rule-dynamic-{rule}",
                rule_static,
            )
            passed = bool(
                rule != 70366
                and float(rule_summary["orbit_acquisition"].get("mean") or 0.0)
                >= 0.70 * qualification_effect
                and _lower(rule_summary["orbit_acquisition"]) > 0.0
            )
            related_rules_passed += int(passed)
            rule_dynamic[str(rule)] = {"summary": rule_summary, "pass": passed}
        base_bundle = base.get("candidate_summaries", {}).get(candidate_id, {})
        static_gate = bool(base_bundle.get("endurance_gate")) if scientific else True
        dynamic_gate = bool(
            float(dynamic32["orbit_acquisition"].get("mean") or 0.0)
            >= contract.orbit_generation32_minimum
            and _lower(dynamic32["orbit_acquisition"]) > 0.0
            and float(dynamic64["orbit_acquisition"].get("mean") or 0.0)
            >= contract.orbit_generation64_minimum
            and _lower(dynamic64["orbit_acquisition"]) > 0.0
            and _tier_control_gate(dynamic64, qualification=True)
            and scale_passes >= 4
            and related_rules_passed >= 4
        ) if scientific else True
        bundles[candidate_id] = {
            "candidate": pb._candidate_public(candidate),
            "static_generation32": static32,
            "static_generation64": static64,
            "dynamic_generation32": dynamic32,
            "dynamic_generation64": dynamic64,
            "static_scales": static_scales,
            "dynamic_scales": dynamic_scales,
            "dynamic_scale_passes": scale_passes,
            "dynamic_rule_stress": rule_dynamic,
            "dynamic_related_rules_passed": related_rules_passed,
            "static": static64,
            "dynamic": dynamic64,
            "static_gate": static_gate,
            "dynamic_gate": dynamic_gate,
        }
    qualified_groups = qualification.get("qualified_by_claim_group", {})
    winners: dict[str, str] = {}
    for group, candidate_id in qualified_groups.items():
        claim = group.rsplit("-", 1)[1]
        if candidate_id in bundles and (
            bundles[candidate_id][f"{claim}_gate"] or not scientific
        ):
            winners[group] = candidate_id
    enduring = sorted(set(winners.values()))
    result = {
        **base,
        "stage_gate": bool(enduring),
        "endurance_candidate_ids": qualified,
        "enduring_candidate_ids": enduring,
        "enduring_by_claim_group": winners,
        "candidate_summaries": bundles,
        "stage6i_scientific_gate_applied": scientific,
    }
    ar._atomic_json(stage_root / "endurance/RESULTS.json", result)
    return result


def _run_adjudication(
    stage_root: Path,
    specs: Sequence[dict[str, Any]],
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: pb.PhenotypeBridgeProfile,
    contract: TrajectoryStabilizationContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    design_digest: str,
    stage6br_root: Path,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    scientific: bool,
    auto_final_audit: bool,
    status: Any,
) -> dict[str, Any]:
    endurance = _load_json(stage_root / "endurance/RESULTS.json")
    winners = dict(endurance.get("enduring_by_claim_group", {}))
    if not winners:
        result = {
            "state": "complete",
            "stage_gate": False,
            "finalist_candidate_ids": [],
            "frozen_winner_ids": {},
            "confirmed_candidate_ids": [],
            "confirmed_claim_groups": [],
            "candidate_summaries": {},
            "final_audit_opened": False,
            "skipped_reason": "endurance gate failed",
            "final_audit_trajectory_state": "untouched",
        }
        pb._write_phase_result(
            stage_root,
            "adjudicate",
            design_digest,
            result,
            "# Stage 6I adjudication\n\nThe final reserve remained sealed.",
            "# Lay summary\n\nNo mechanism passed every exposed-data test, so the protected cases were not inspected.",
            next_phase=None,
        )
        return result
    if scientific and not auto_final_audit:
        raise ValueError("reference Stage-6I final audit lacks authorization")
    winner_ids = sorted(set(winners.values()))
    all_models = _materialized_map(stage_root, stage6br_root, specs)
    models = [all_models[candidate_id] for candidate_id in winner_ids]
    pair_digest = hashlib.sha256("\n".join(frozen["later_ids"]).encode()).hexdigest()
    ar._atomic_json(
        stage_root / "FINAL_AUDIT_DESIGN.json",
        {
            "design_digest": design_digest,
            "winner_ids_by_claim_group": winners,
            "winners_frozen_before_pair_loading": True,
            "unique_candidate_count": len(winner_ids),
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
            raise ValueError("Stage-6I final reserve is incomplete")
        pb._update_reserve_state(stage_root, "opened")
        reserve_state = "opened"
    else:
        final_pairs = cohorts["qualification"][: profile.final_pairs]
        reserve_state = "smoke-exposed-only"
    items = ar._make_items(
        final_pairs,
        models,
        ar._template_pairs(templates, "audit"),
        frozen["stage4"]["configuration"],
        phase="final-audit",
        replicates=profile.final_replicates,
        generations=64,
        conditions=AUDIT_CONDITIONS,
        analysis_kind="final",
    )
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        "final-audit-trajectories-stage6i",
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
    final_contract = replace(contract, strict_alpha=contract.final_strict_alpha)
    bundles: dict[str, dict[str, Any]] = {}
    for candidate in models:
        candidate_id = str(candidate["candidate_id"])
        static: dict[int, dict[str, Any]] = {}
        dynamic: dict[int, dict[str, Any]] = {}
        for generation in (8, 16, 64):
            static[generation] = _augment_static_summary(
                rows,
                candidate,
                generation,
                profile,
                final_contract,
                f"final-static-g{generation}",
            )
            dynamic[generation] = _dynamic_summary(
                rows,
                candidate,
                generation,
                profile,
                final_contract,
                f"final-dynamic-g{generation}",
                static[generation],
            )
        static_gate = bool(
            _static_screen_gate(static[8], final_contract)
            and _static_qualification_gate(static[16], final_contract)
            and _static_qualification_gate(static[64], final_contract)
            and float(static[64]["post_washout_acquisition"].get("mean") or 0.0)
            >= 0.05
        )
        dynamic_gate = bool(
            _dynamic_screen_gate(dynamic[8], final_contract)
            and _dynamic_qualification_gate(dynamic[16], final_contract)
            and float(dynamic[64]["orbit_acquisition"].get("mean") or 0.0)
            >= final_contract.orbit_generation64_minimum
            and _lower(dynamic[64]["orbit_acquisition"]) > 0.0
            and _tier_control_gate(dynamic[64], qualification=True)
        )
        bundles[candidate_id] = {
            "candidate": pb._candidate_public(candidate),
            "static_generation8": static[8],
            "static_generation16": static[16],
            "static_generation64": static[64],
            "dynamic_generation8": dynamic[8],
            "dynamic_generation16": dynamic[16],
            "dynamic_generation64": dynamic[64],
            "static_gate": static_gate,
            "dynamic_gate": dynamic_gate,
        }
    confirmed_claims = [
        group
        for group, candidate_id in winners.items()
        if complete
        and bundles[candidate_id][f"{group.rsplit('-', 1)[1]}_gate"]
    ]
    confirmed_ids = sorted({winners[group] for group in confirmed_claims})
    final_digest = _digest(
        {"winners": winners, "confirmed_claims": confirmed_claims, "summaries": bundles}
    )
    if scientific:
        reserve_state = "complete" if complete else "partial"
        pb._update_reserve_state(stage_root, reserve_state, final_digest=final_digest)
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(confirmed_claims),
        "scientific_gate_applied": scientific,
        "finalist_candidate_ids": winner_ids,
        "frozen_winner_ids": winners,
        "confirmed_candidate_ids": confirmed_ids,
        "confirmed_claim_groups": confirmed_claims,
        "candidate_summaries": bundles,
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "final_audit_opened": scientific,
        "final_audit_digest": final_digest,
        "final_audit_trajectory_state": reserve_state,
    }
    pb._write_phase_result(
        stage_root,
        "adjudicate",
        design_digest,
        result,
        "# Stage 6I adjudication\n\nConfirmed claim groups: "
        + (", ".join(confirmed_claims) if confirmed_claims else "none"),
        "# Lay summary\n\nStatic pictures and phase-tolerant trajectories were judged separately for each memory mechanism.",
        next_phase=None,
    )
    return result


def _forensics(
    stage6h_root: Path,
    stage_root: Path,
    specs: Sequence[dict[str, Any]],
    stage6br_root: Path,
    contract: TrajectoryStabilizationContract,
) -> dict[str, Any]:
    parent = _load_json(stage6h_root / "forensics/RESULTS.json")
    models = _materialized_map(stage_root, stage6br_root, specs)
    codec_diagnostics: dict[str, Any] = {}
    inherited = [
        candidate for candidate in models.values() if candidate["mechanism_tier"] == "inherited-field"
    ]
    for candidate in inherited:
        field_candidate = pb._field_codec_candidate(candidate)
        rank = int(field_candidate["rank"])
        rng = np.random.default_rng(ar._hash_seed(contract.namespace, "field-codec", rank))
        values = rng.uniform(-1.0, 1.0, size=(64, rank)).astype(np.float32)
        quantized, clipping = pb._quantize_frontend(values, field_candidate)
        shares, active = pb._encode_carrier(
            quantized, field_candidate, contract, "synthetic-field", 5, "forensic"
        )
        copied, uncorrectable = pb._copy_carrier(
            shares,
            "synthetic-field",
            5,
            32,
            contract,
            purpose="forensic-slow-field-copy",
            corruption=0.01,
        )
        reconstructed, valid = pb._joint_payload(copied, active, field_candidate)
        codec_diagnostics[f"rank{rank}"] = {
            "valid_fraction": float(np.mean(valid)),
            "mean_absolute_error": float(np.mean(np.abs(reconstructed - quantized))),
            "uncorrectable_fraction": float(uncorrectable),
            "quantizer_clipping": float(clipping),
        }
    simple = np.ones((8, 4, 4, 4), dtype=np.float32)
    simple[:, 2:] *= -1.0
    orbit_diagnostic = {
        condition: pb._orbit_metrics(
            list(simple),
            list(simple),
            list(-simple),
            condition,
            ar._hash_seed(contract.namespace, "orbit-self-test", condition),
        )
        for condition in (
            "intact",
            "orbit_phase_shift",
            "orbit_temporal_reverse",
            "orbit_temporal_shuffle",
        )
    }
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_generation_curve": parent["parent_generation_curve"],
        "generational_dialect": parent["generational_dialect"],
        "teacher_proposal_curve": parent["teacher_proposal_curve"],
        "zero_noise_proposal_curve": parent["zero_noise_proposal_curve"],
        "slow_field_codec_diagnostics": codec_diagnostics,
        "orbit_metric_self_test": orbit_diagnostic,
        "nonpromotable_ceiling_sources": (
            "Stage-6H target-forced writer",
            "Stage-6H zero-noise writer",
            "Stage-6I synthetic noiseless codec self-test",
        ),
        "final_audit_trajectory_state": "untouched",
        "next_phase": "develop",
    }


def _campaign_result(
    output: Path,
    design_digest: str,
    profile_name: str,
    screen: dict[str, Any],
    qualification: dict[str, Any],
    endurance: dict[str, Any],
    adjudication: dict[str, Any],
) -> dict[str, Any]:
    confirmed = list(adjudication.get("confirmed_claim_groups", []))
    claim_verdicts = {
        group: "confirmed" if group in confirmed else "not-confirmed"
        for group in CLAIM_GROUPS
    }
    states = [
        screen.get("state"),
        qualification.get("state"),
        endurance.get("state"),
        adjudication.get("state"),
    ]
    if profile_name == "smoke":
        verdict = "SMOKE_PATH_VALIDATED"
    elif "budget_truncated" in states:
        verdict = "INCONCLUSIVE_RESOURCE_LIMIT"
    elif confirmed:
        verdict = "TRAJECTORY_STABILIZATION_CONFIRMED"
        if any(group.startswith("inherited-field") for group in confirmed):
            verdict = "INHERITED_SLOW_FIELD_PH_CONFIRMED"
    elif endurance.get("enduring_candidate_ids"):
        verdict = "FINAL_AUDIT_NOT_CONFIRMED"
    elif qualification.get("qualified_candidate_ids"):
        verdict = "NON_ENDURING_TRAJECTORY_OR_FIELD_EFFECT"
    elif screen.get("selected_candidate_ids"):
        verdict = "ONE_GENERATION_TRAJECTORY_OR_FIELD_EFFECT"
    else:
        verdict = "NO_TRAJECTORY_OR_FIELD_HEREDITY"
    result = {
        "experiment": "ca_motif_trajectory_stabilization_stage_6i",
        "design_digest": design_digest,
        "profile_name": profile_name,
        "state": "complete",
        "stage_gate": bool(confirmed),
        "verdict": verdict,
        "claim_verdicts": claim_verdicts,
        "selected_candidate_ids": screen.get("selected_candidate_ids", []),
        "qualified_candidate_ids": qualification.get("qualified_candidate_ids", []),
        "enduring_candidate_ids": endurance.get("enduring_candidate_ids", []),
        "confirmed_candidate_ids": adjudication.get("confirmed_candidate_ids", []),
        "confirmed_claim_groups": confirmed,
        "static_dynamic_claims_separate": True,
        "runtime_target_exposure": False,
        "runtime_adaptation_promotable": False,
        "final_audit_opened": bool(adjudication.get("final_audit_opened", False)),
        "final_audit_trajectory_state": adjudication.get(
            "final_audit_trajectory_state", "untouched"
        ),
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
    report_lines = [
        "# Stage 6I dynamic form and slow-field heredity",
        "",
        f"Verdict: **{verdict}**.",
        "",
        "Static snapshots and ordered, phase-tolerant trajectories were adjudicated independently.",
        "",
        "| Claim group | Verdict |",
        "|---|---|",
    ]
    report_lines.extend(
        f"| {group} | {claim_verdicts[group]} |" for group in CLAIM_GROUPS
    )
    ar._atomic_text(output / "REPORT.md", "\n".join(report_lines) + "\n")
    if confirmed:
        lay = "At least one daughter-memory mechanism repeatedly recovered the learned history after visible reset and passed the registered causal tests. Static pictures and moving forms are listed separately in the full report."
    elif verdict == "INCONCLUSIVE_RESOURCE_LIMIT":
        lay = "The fixed eight-hour clock ended before all decisive tests completed."
    else:
        lay = "None of the visible, temporary-field, or inherited-field designs passed the complete causal and generational ladder. A moving form was not counted as a stable picture."
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
    marker = "<!-- CA_MOTIF_STAGE6I_RESULT -->"
    prior = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in prior:
        return
    entry = (
        "\n\n"
        + marker
        + "\n## CA motif-lineage Stage 6I — dynamic form and slow-field heredity\n\n"
        + f"The registered campaign completed with verdict `{result['verdict']}`. "
        + "Static form and phase-tolerant dynamic form were judged independently "
        + "for visible-only, zero-born transient-field, and encoded inherited-field mechanisms. "
        + f"Confirmed claim groups: {result.get('confirmed_claim_groups', [])}. "
        + f"The protected reserve ended in state `{result['final_audit_trajectory_state']}`.\n\n"
        + f"Pollable artifacts: `{output.relative_to(ROOT)}`. Protocol: "
        + "`CA_MOTIF_TRAJECTORY_STABILIZATION_PROTOCOL.md`. Implementation: "
        + "`plastic_ca/motif_trajectory_stabilization.py`.\n"
    )
    ar._atomic_text(path, prior.rstrip() + entry)


def run_motif_trajectory_stabilization(
    output: Path,
    *,
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
    """Run the sealed Stage-6I trajectory/slow-field campaign."""

    ar.require_pinned_numpy()
    if profile_name not in PROFILES:
        raise ValueError(f"unknown Stage-6I profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6I workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6I max-hours must be in (0, 8]")
    if profile_name == "reference" and not auto_final_audit:
        raise ValueError("reference Stage-6I requires automatic final-audit authorization")
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ar._atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
    stage6h_root = stage6h_root.resolve()
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
            output, profile_name, stage6h_root, max_hours, resume=resume
        )
        status = _status_writer(output, profile_name, campaign, active)
        status("running", "frozen-design-verified")
        active[0] = "integrity"
        _write_phase(
            output,
            "integrity",
            design_digest,
            integrity | {"next_phase": "forensics"},
            "# Stage 6I integrity\n\nStage 6H and all 576 exposed validation checkpoints were verified; the 62-pair reserve remained untouched.",
            "# Lay summary\n\nThe new test starts from the exact previous boundary without changing its evidence.",
        )
        stage_root = output / "stage6i"
        frozen, cohorts, profile, writer_contract, templates = _reconstruct_cohorts(
            stage_root,
            stage_profile,
            integrity,
            roots,
            auto_final_audit=auto_final_audit,
        )
        specs = _candidate_specs(stage6h_root)
        _seal_registry(stage_root, specs, design_digest)
        active[0] = "forensics"
        forensics = _forensics(
            stage6h_root, stage_root, specs, roots["stage6br_root"], contract
        )
        _write_phase(
            output,
            "forensics",
            design_digest,
            forensics,
            "# Stage 6I forensics\n\nThe phase-flip boundary, orbit metric, and independent noisy field codec were checked on exposed or synthetic data only.",
            "# Lay summary\n\nThis checks that we can distinguish the same motion at a different phase from a scrambled motion, and that the second memory can physically survive copying.",
        )
        active[0] = "develop"
        development = {
            "state": "complete",
            "stage_gate": len(specs) == 18,
            "candidate_count": len(specs),
            "candidate_allocation": {
                tier: sum(row["mechanism_tier"] == tier for row in specs)
                for tier in MECHANISM_TIERS
            },
            "selection_digest": _digest(specs),
            "selection_frozen_before_screen": True,
            "runtime_retraining": False,
            "runtime_target_exposure": False,
            "next_phase": "screen",
            "final_audit_trajectory_state": "untouched",
        }
        _write_phase(
            output,
            "develop",
            design_digest,
            development,
            "# Stage 6I frozen mechanisms\n\nEighteen visible, transient, and inherited-field candidates were sealed before screening.",
            "# Lay summary\n\nAll candidate rulebooks were locked before any unused case was examined.",
        )
        scientific = profile_name == "reference"
        active[0] = "screen"
        screen = _run_screen(
            stage_root,
            specs,
            frozen,
            cohorts,
            profile,
            contract,
            writer_contract,
            templates,
            design_digest,
            roots["stage6br_root"],
            workers=workers,
            resume=resume,
            deadline=float(campaign["exploration_deadline_unix"]),
            scientific=scientific,
            status=status,
        )
        _write_phase(
            output,
            "screen",
            design_digest,
            screen | {"next_phase": "qualify"},
            "# Stage 6I screen\n\nStatic and dynamic winners were selected independently in each mechanism tier.",
            "# Lay summary\n\nEach design had to recover the right picture or the right ordered motion after the incoming note was erased.",
        )
        active[0] = "qualify"
        qualification = _run_qualification(
            stage_root,
            specs,
            frozen,
            cohorts,
            profile,
            contract,
            writer_contract,
            templates,
            design_digest,
            roots["stage6br_root"],
            workers=workers,
            resume=resume,
            deadline=float(campaign["exploration_deadline_unix"]),
            scientific=scientific,
            status=status,
        )
        _write_phase(
            output,
            "qualify",
            design_digest,
            qualification | {"next_phase": "endurance"},
            "# Stage 6I qualification\n\nSurvivors faced ablation, rescue, opposite-history, ordering, and renewal tests through generation 16.",
            "# Lay summary\n\nA memory only advanced if removing the proposed cause removed the effect and restoring the matching history brought it back.",
        )
        active[0] = "endurance"
        endurance = _run_endurance(
            stage_root,
            specs,
            frozen,
            cohorts,
            profile,
            contract,
            writer_contract,
            templates,
            design_digest,
            roots["stage6br_root"],
            workers=workers,
            resume=resume,
            deadline=float(campaign["hard_deadline_unix"]),
            scientific=scientific,
            status=status,
        )
        _write_phase(
            output,
            "endurance",
            design_digest,
            endurance | {"next_phase": "adjudicate"},
            "# Stage 6I endurance\n\nQualified mechanisms were tested through generation 64, at three extents and across the registered rule panel.",
            "# Lay summary\n\nThe remaining designs had to keep rebuilding memory for many births and under larger worlds and related rules.",
        )
        active[0] = "adjudicate"
        adjudication = _run_adjudication(
            stage_root,
            specs,
            frozen,
            cohorts,
            profile,
            contract,
            writer_contract,
            templates,
            design_digest,
            roots["stage6br_root"],
            workers=workers,
            resume=resume,
            deadline=float(campaign["hard_deadline_unix"]),
            scientific=scientific,
            auto_final_audit=auto_final_audit,
            status=status,
        )
        _write_phase(
            output,
            "adjudicate",
            design_digest,
            adjudication,
            "# Stage 6I adjudication\n\nThe protected result, if opened, contains separately adjudicated static and dynamic claims.",
            "# Lay summary\n\nOnly mechanisms passing every earlier test were allowed to see the protected cases.",
        )
        active[0] = "complete"
        result = _campaign_result(
            output,
            design_digest,
            profile_name,
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
    "CLAIM_GROUPS",
    "DEFAULT_STAGE6H_ROOT",
    "FORM_CLAIMS",
    "MECHANISM_TIERS",
    "PHASES",
    "PROFILES",
    "TrajectoryProfile",
    "TrajectoryStabilizationContract",
    "run_motif_trajectory_stabilization",
)
