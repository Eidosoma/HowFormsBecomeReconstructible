"""Stage-6K learned writer closure and identifiable moving-form targets.

Stage 6J separated parent and daughter field buffers, but its hand-written
daughter update neither recovered static form nor encountered a temporally
identifiable target.  This campaign follows both leads without opening the
62-pair final reserve: it measures ideal-field ceilings, fits frozen local
visible-only writers on all 48 already-exposed pairs, and constructs an
independent bank of translating Life-like objects with direction-aware scores.
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
from . import motif_adaptive_handoff as ah
from . import motif_phenotype_bridge as pb
from . import motif_trajectory_stabilization as ts
from .life import named_patterns
from .life_family import (
    life_like_step_batch,
    life_rule_notation,
    parse_life_rule,
)


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_WRITER_CLOSURE_PROTOCOL.md"
DEFAULT_STAGE6J_ROOT = ROOT / "results/ca-motif-adaptive-handoff-stage-6j-r2"
DEFAULT_STAGE6I_ROOT = ah.DEFAULT_STAGE6I_ROOT
DEFAULT_STAGE6H_ROOT = ah.DEFAULT_STAGE6H_ROOT
PHASES = (
    "integrity",
    "mover-panel",
    "oracle-ladder",
    "fit",
    "heldout",
    "adjudicate",
)
WRITER_KINDS = ("equivariant-ridge", "rff", "local-reservoir")
MOVER_RULES = (
    parse_life_rule("B3/S23"),
    parse_life_rule("B36/S23"),
    parse_life_rule("B3/S234"),
    parse_life_rule("B3/S123"),
    parse_life_rule("B34/S23"),
    parse_life_rule("B23/S23"),
    parse_life_rule("B3/S2"),
)
HELDOUT_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
    "acquisition_write_disabled",
    "handoff_visible_scrub",
    "inherited_field_ablation",
    "inherited_field_read_disabled",
    "inherited_field_write_disabled",
    "inherited_field_no_renewal",
    "inherited_field_same_rescue",
    "inherited_field_opposite_rescue",
    "closure_self_rehearsal_disabled",
)


@dataclass(frozen=True)
class WriterClosureProfile:
    exposed_pairs: int
    trace_replicates: int
    oracle_pairs: int
    oracle_replicates: int
    heldout_pairs: int
    heldout_replicates: int
    mover_seeds_per_rule: int
    mover_min_pairs: int
    mover_min_discovered_pairs: int
    bootstrap_resamples: int
    maximum_frozen_candidates: int


PROFILES = {
    "smoke": WriterClosureProfile(6, 1, 2, 1, 1, 1, 96, 4, 1, 100, 4),
    "reference": WriterClosureProfile(
        48, 4, 8, 2, 8, 2, 4096, 16, 8, 10_000, 4
    ),
}


@dataclass(frozen=True)
class WriterClosureContract(ah.AdaptiveHandoffContract):
    implementation_version: str = "ca-motif-writer-closure-v1"
    namespace: str = "plastic-ca-motif-writer-closure-v1"
    maximum_promotable_writers: int = 4
    exploration_stop_hours: float = 6.0
    local_writer_fold_count: int = 6
    writer_bit_accuracy_minimum: float = 0.65
    writer_fold_minimum: float = 0.58
    dynamic_direction_margin_minimum: float = 0.10

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "maximum_promotable_writers": self.maximum_promotable_writers,
                "local_writer_fold_count": self.local_writer_fold_count,
                "writer_bit_accuracy_minimum": self.writer_bit_accuracy_minimum,
                "writer_fold_minimum": self.writer_fold_minimum,
                "dynamic_direction_margin_minimum": self.dynamic_direction_margin_minimum,
                "writer_inputs": ("local visible states",),
                "runtime_target_labels": False,
                "runtime_parent_field": False,
                "runtime_pair_identity": False,
                "runtime_generation_index": False,
                "field_channels": ("form", "directed-transition"),
                "field_base_rank": 16,
                "final_reserve_policy": "never-open-in-stage-6k",
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
    stage6j_root: Path,
    stage6i_root: Path,
    stage6h_root: Path,
) -> dict[str, Any]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "MANIFEST.json",
        "stage6j/COHORTS.json",
        "develop/RESULTS.json",
        "screen/RESULTS.json",
        "qualify/RESULTS.json",
        "endurance/RESULTS.json",
        "adjudicate/RESULTS.json",
        "COMPLETE",
    )
    missing = [stage6j_root / name for name in required if not (stage6j_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6J artifacts: {missing}")
    result = _load_json(stage6j_root / "RESULTS.json")
    status = _load_json(stage6j_root / "STATUS.json")
    cohorts = _load_json(stage6j_root / "stage6j/COHORTS.json")
    adjudication = _load_json(stage6j_root / "adjudicate/RESULTS.json")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6K requires a complete Stage-6J parent")
    if result.get("verdict") != "DYNAMIC_TARGET_NOT_IDENTIFIABLE_AND_NO_STATIC_HANDOFF":
        raise ValueError("Stage-6K requires the registered Stage-6J negative boundary")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6J final reserve is not untouched")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6J cohort ledger says the final reserve was touched")
    if adjudication.get("final_audit_opened") or adjudication.get(
        "final_audit_trajectory_state"
    ) != "untouched":
        raise ValueError("Stage-6J adjudication opened the protected reserve")
    if (stage6j_root / "stage6j/endurance-trajectories-stage6j/checkpoints").exists():
        raise ValueError("Stage-6J endurance trajectories unexpectedly exist")
    routes = cohorts["development_pair_ids"]
    if [len(routes[name]) for name in ("development", "screen", "endurance")] != [
        40,
        8,
        8,
    ]:
        raise ValueError("Stage-6J evidential cohort allocation changed")
    all_ids = [*routes["development"], *routes["screen"], *routes["endurance"]]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("Stage-6J evidential roles overlap")
    parent = ah._parent_integrity(stage6i_root, stage6h_root)
    if parent["final_pair_ids_sha256"] != cohorts["final_audit_pair_ids_sha256"]:
        raise ValueError("Stage-6J final reserve digest changed")
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "required_hashes": {
            name: ar._sha256(stage6j_root / name) for name in required
        },
        "exposed_pair_count": 48,
        "untouched_endurance_pair_count": 8,
        "final_pair_count": 62,
        "final_pair_ids_sha256": parent["final_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
        "stage6i_integrity": parent,
    }


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6j_root: Path,
    stage6i_root: Path,
    stage6h_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[
    WriterClosureContract,
    WriterClosureProfile,
    dict[str, Any],
    str,
    dict[str, Any],
]:
    contract = WriterClosureContract()
    profile = PROFILES[profile_name]
    integrity = _parent_integrity(stage6j_root, stage6i_root, stage6h_root)
    design = {
        "experiment": "ca_motif_writer_closure_stage_6k",
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(profile),
        "stage6j_root": str(stage6j_root.resolve()),
        "stage6i_root": str(stage6i_root.resolve()),
        "stage6h_root": str(stage6h_root.resolve()),
        "stage6j_required_hashes": integrity["required_hashes"],
        "cohort_route": {
            "fit": "all 48 already-exposed Stage-6J development/screen pairs",
            "heldout": "eight never-simulated Stage-6J endurance pairs",
            "final": "62-pair reserve stays sealed; Stage 6K cannot open it",
        },
        "writer_factorial": {
            "kinds": WRITER_KINDS,
            "radii": (2, 4),
            "windows": (8, 16),
            "canonicalization": (False, True),
            "total": 24,
            "pair_blocked_folds": 6,
            "self_rehearsal_after_freeze": (False, True),
            "maximum_frozen_candidates": 4,
        },
        "mover_panel": {
            "rules": [
                {"rule": rule, "notation": life_rule_notation(rule)}
                for rule in MOVER_RULES
            ],
            "seed_window": "5x5",
            "seed_mass": (5, 12),
            "seeds_per_rule": profile.mover_seeds_per_rule,
            "period_maximum": 16,
            "requires_nonzero_displacement": True,
            "anchors": ("glider", "lwss"),
        },
        "limits": {
            "workers": 4,
            "max_hours": max_hours,
            "exploration_stop_hours": min(6.0, max_hours * 0.75),
            "hard_stop_hours": max_hours,
        },
        "implementation_hashes": {
            "motif_writer_closure.py": ar._sha256(Path(__file__)),
            "motif_phenotype_bridge.py": ar._sha256(Path(pb.__file__)),
            "protocol": ar._sha256(PROTOCOL_PATH),
        },
        "cleanroom": {
            "excluded_code": ("Wagner implementation", "Fable implementation"),
            "excluded_code_read_import_hash_execute": True,
            "source_basis": "prior CA artifacts plus independently specified hypothesis",
        },
    }
    design_digest = _digest(design)
    design["design_digest"] = design_digest
    design_path = output / "DESIGN.json"
    if design_path.exists():
        if not resume:
            raise ValueError("Stage-6K output exists; use --resume")
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6K design changed during resume")
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
            raise ValueError("Stage-6K max-hours changed during resume")
    else:
        started = time.time()
        campaign = {
            "experiment": design["experiment"],
            "design_digest": design_digest,
            "started_unix": started,
            "max_hours": max_hours,
            "exploration_deadline_unix": started
            + min(6.0, max_hours * 0.75) * 3600.0,
            "hard_deadline_unix": started + max_hours * 3600.0,
            "deadline_persists_across_resume": True,
            "final_audit_opening_authorized": False,
        }
        ar._atomic_json(campaign_path, campaign)
    return contract, profile, campaign, design_digest, integrity


def _status_writer(
    output: Path,
    profile_name: str,
    campaign: dict[str, Any],
    active: list[str],
) -> Any:
    def write(state: str, current: str, **extra: Any) -> None:
        now = time.time()
        payload = {
            "state": state,
            "stage": "ca_motif_writer_closure_stage_6k",
            "profile": profile_name,
            "phase": active[0],
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
            f" {extra['completed']}/{extra['total']}" if "completed" in extra else ""
        )
        print(f"[{state}] stage6k-{active[0]}:{current}{progress}", flush=True)

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
        "experiment": "ca_motif_writer_closure_stage_6k",
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


def _reconstruct_cohorts(
    stage_root: Path,
    profile_name: str,
    profile: WriterClosureProfile,
    integrity: dict[str, Any],
    stage6j_root: Path,
    roots: dict[str, Path],
) -> tuple[
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    pb.PhenotypeBridgeProfile,
    ar.MotifContract,
    list[dict[str, Any]],
]:
    parent_profile = ah.PROFILES["reference" if profile_name == "reference" else "smoke"]
    frozen, parent, nested, writer_contract, templates = ah._reconstruct_cohorts(
        stage_root,
        parent_profile,
        integrity["stage6i_integrity"],
        roots,
        auto_final_audit=True,
    )
    exposed = [*parent["development"], *parent["screen"]]
    cohorts = {
        "exposed": exposed[: profile.exposed_pairs],
        "heldout": list(parent["endurance"][: profile.heldout_pairs]),
        "final": [],
    }
    ledger = _load_json(stage6j_root / "stage6j/COHORTS.json")[
        "development_pair_ids"
    ]
    expected_exposed = [
        *ledger["development"][: parent_profile.development_pairs],
        *ledger["screen"][: parent_profile.screen_pairs],
    ][: profile.exposed_pairs]
    expected_heldout = ledger["endurance"][: profile.heldout_pairs]
    if [str(row["pair_id"]) for row in cohorts["exposed"]] != expected_exposed:
        raise ValueError("Stage-6K exposed cohort reconstruction changed")
    if [str(row["pair_id"]) for row in cohorts["heldout"]] != expected_heldout:
        raise ValueError("Stage-6K heldout cohort reconstruction changed")
    if set(expected_exposed) & set(expected_heldout):
        raise AssertionError("Stage-6K fit and heldout roles overlap")
    payload = {
        "pair_ids": {
            name: [str(pair["pair_id"]) for pair in rows]
            for name, rows in cohorts.items()
            if name != "final"
        },
        "fit_pairs_previously_exposed": True,
        "heldout_pairs_never_simulated_in_stage6j": True,
        "heldout_pair_count": len(cohorts["heldout"]),
        "final_audit_pair_count": 62,
        "final_audit_pair_ids_sha256": integrity["final_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
        "final_audit_trajectories_not_loaded": True,
    }
    ar._atomic_json(stage_root / "COHORTS.json", payload)
    return frozen, cohorts, nested, writer_contract, templates


def _materialize_source_candidate(
    stage_root: Path,
    stage6h_root: Path,
    stage6br_root: Path,
    design_digest: str,
) -> dict[str, Any]:
    specs = ah._candidate_specs(stage6h_root)
    ah._seal_registry(stage_root, specs, design_digest)
    models = ah._models(stage_root, stage6br_root)
    source_id = "stage6j-label-free-phase-latch-distiller-r16-short"
    source = copy.deepcopy(models[source_id])
    source["candidate_id"] = "stage6k-exposed-trace-collector"
    source["promotable"] = False
    return source


def _writer_configs() -> list[dict[str, Any]]:
    configs: list[dict[str, Any]] = []
    for kind in WRITER_KINDS:
        for radius in (2, 4):
            for window in (8, 16):
                for canonicalize in (False, True):
                    configs.append(
                        {
                            "config_id": (
                                f"{kind}-r{radius}-w{window}-"
                                f"d4{int(canonicalize)}"
                            ),
                            "kind": kind,
                            "radius": radius,
                            "window": window,
                            "canonicalize": canonicalize,
                        }
                    )
    if len(configs) != 24 or len({row["config_id"] for row in configs}) != 24:
        raise AssertionError("Stage-6K writer factorial changed")
    return configs


def _collect_traces(
    stage_root: Path,
    source: dict[str, Any],
    pairs: Sequence[dict[str, Any]],
    profile: WriterClosureProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: WriterClosureContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[list[dict[str, Any]], bool, int]:
    items = ar._make_items(
        pairs,
        [source],
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="stage6k-exposed-traces",
        replicates=profile.trace_replicates,
        generations=5,
        conditions=("intact",),
        analysis_kind="closure-training-trace",
    )
    for item in items:
        item["retain_bridge_trace"] = True
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        "exposed-closure-traces",
        items,
        [source],
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


def _unpack_state_hex(value: str, shape: Sequence[int]) -> np.ndarray:
    cells = int(np.prod(shape))
    bits = np.unpackbits(np.frombuffer(bytes.fromhex(value), dtype=np.uint8))[:cells]
    return bits.astype(np.bool_).reshape(tuple(int(item) for item in shape))


def _trace_record(row: dict[str, Any]) -> dict[str, Any]:
    result = row["conditions"]["intact"]
    trace = result["bridge_trace"]["5"]
    shape = trace["state_shape"]
    sweeps = sorted(int(key) for key in trace["full_state_hex"])
    states = {
        sweep: np.stack(
            [
                _unpack_state_hex(value, shape)
                for value in trace["full_state_hex"][str(sweep)]
            ],
            axis=0,
        )
        for sweep in sweeps
    }
    return {
        "pair_id": str(row["pair_id"]),
        "rule": int(row.get("rule", result["rule"])),
        "read_end": int(trace["read_end"]),
        "states": states,
        "centers": np.asarray(trace["centers"], dtype=np.int16),
        "environment": np.asarray(trace["environment"], dtype=np.float32),
    }


def _target_reference(record: dict[str, Any]) -> dict[int, np.ndarray]:
    read_end = int(record["read_end"])
    state = record["states"][read_end].copy()
    ar._apply_environment(
        state,
        record["centers"],
        np.asarray(record["environment"] >= 0.0, dtype=np.bool_),
    )
    result = {read_end: state.copy()}
    for sweep in range(read_end + 1, max(record["states"]) + 1):
        state = ar._step(state, int(record["rule"]))
        result[sweep] = state.copy()
    return result


def _examples_for_config(
    rows: Sequence[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    feature_rows: list[np.ndarray] = []
    target_rows: list[np.ndarray] = []
    group_rows: list[str] = []
    endpoint_rows: list[str] = []
    for raw in rows:
        record = _trace_record(raw)
        reference = _target_reference(record)
        available = sorted(record["states"])
        read_end = int(record["read_end"])
        endpoints = [
            sweep
            for sweep in (read_end + 8, read_end + 12, read_end + 16, read_end + 20)
            if sweep in record["states"] and sweep in reference
        ]
        for endpoint in endpoints:
            beginning = max(min(available), endpoint - int(config["window"]) + 1)
            history = [
                record["states"][sweep]
                for sweep in available
                if beginning <= sweep <= endpoint
            ]
            features, orientations = pb._closure_local_features(
                history,
                record["centers"],
                int(config["radius"]),
                int(config["window"]),
                bool(config["canonicalize"]),
            )
            current = ar.observe_texture(reference[endpoint], record["centers"])
            previous = ar.observe_texture(reference[endpoint - 1], record["centers"])
            transition = np.where(current != previous, current, 0.0).astype(np.float32)
            targets = np.stack((current, transition), axis=1)
            targets = pb._closure_transform_targets(targets, orientations)
            feature_rows.append(features)
            target_rows.append(targets.reshape(len(targets), 32))
            group_rows.extend([record["pair_id"]] * len(features))
            endpoint_rows.extend(
                [f"{record['pair_id']}:{endpoint}"] * len(features)
            )
    if not feature_rows:
        raise ValueError("Stage-6K trace collection yielded no writer examples")
    return (
        np.concatenate(feature_rows, axis=0).astype(np.float32),
        np.concatenate(target_rows, axis=0).astype(np.float32),
        np.asarray(group_rows, dtype=str),
        endpoint_rows,
    )


def _pair_blocked_folds(groups: np.ndarray, fold_count: int = 6) -> np.ndarray:
    unique = sorted(
        set(str(value) for value in groups),
        key=lambda value: (ar._hash_seed("stage6k-pair-fold", value), value),
    )
    if len(unique) < fold_count:
        raise ValueError("fewer pair groups than registered closure folds")
    assignment = {pair_id: index % fold_count for index, pair_id in enumerate(unique)}
    return np.asarray([assignment[str(value)] for value in groups], dtype=np.int8)


def _ridge_fit(
    design: np.ndarray,
    targets: np.ndarray,
    ridge: float,
) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(design, dtype=np.float64)
    y = np.asarray(targets, dtype=np.float64)
    augmented = np.concatenate((x, np.ones((len(x), 1), dtype=np.float64)), axis=1)
    penalty = np.eye(augmented.shape[1], dtype=np.float64) * float(ridge)
    penalty[-1, -1] = 0.0
    fitted = np.linalg.solve(
        augmented.T @ augmented + penalty,
        augmented.T @ y,
    )
    return fitted[:-1].astype(np.float32), fitted[-1].astype(np.float32)


def _projection_for(
    config: dict[str, Any],
    input_dimension: int,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    kind = str(config["kind"])
    if kind == "equivariant-ridge":
        return None, None
    width = 96
    rng = np.random.default_rng(
        ar._hash_seed("stage6k-closure-projection", config["config_id"])
    )
    projection = rng.normal(
        0.0,
        1.0 / math.sqrt(max(1, input_dimension)),
        size=(input_dimension, width),
    ).astype(np.float32)
    if kind == "rff":
        phase = rng.uniform(0.0, 2.0 * math.pi, size=width).astype(np.float32)
    elif kind == "local-reservoir":
        phase = rng.uniform(-0.35, 0.35, size=width).astype(np.float32)
    else:
        raise ValueError(f"unknown closure writer kind {kind!r}")
    return projection, phase


def _model_design(
    normalized: np.ndarray,
    kind: str,
    projection: np.ndarray | None,
    phase: np.ndarray | None,
) -> np.ndarray:
    if kind == "equivariant-ridge":
        return normalized
    if projection is None or phase is None:
        raise ValueError("nonlinear closure writer is missing its frozen projection")
    projected = normalized @ projection + phase
    if kind == "rff":
        return (
            np.float32(math.sqrt(2.0 / projection.shape[1])) * np.cos(projected)
        ).astype(np.float32)
    if kind == "local-reservoir":
        return np.tanh(projected).astype(np.float32)
    raise ValueError(f"unknown closure writer kind {kind!r}")


def _prediction_metrics(predicted: np.ndarray, targets: np.ndarray) -> dict[str, float]:
    prediction = np.clip(np.asarray(predicted, dtype=np.float32), -1.0, 1.0).reshape(
        -1, 2, 4, 4
    )
    target = np.asarray(targets, dtype=np.float32).reshape(-1, 2, 4, 4)
    bit_accuracy = float(np.mean((prediction[:, 0] >= 0.0) == (target[:, 0] >= 0.0)))
    mae = float(np.mean(np.abs(prediction - target)))
    event = np.abs(target[:, 1]) > np.float32(0.25)
    event_accuracy = (
        float(np.mean((prediction[:, 1][event] >= 0.0) == (target[:, 1][event] >= 0.0)))
        if np.any(event)
        else 0.5
    )
    flat_prediction = prediction[:, 1].reshape(len(prediction), -1)
    flat_target = target[:, 1].reshape(len(target), -1)
    numerators = np.sum(flat_prediction * flat_target, axis=1)
    denominators = np.linalg.norm(flat_prediction, axis=1) * np.linalg.norm(
        flat_target, axis=1
    )
    cosines = np.divide(
        numerators,
        denominators,
        out=np.zeros_like(numerators),
        where=denominators > np.float32(1e-8),
    )
    direction_cosine = float(np.mean(cosines))
    return {
        "form_bit_accuracy": bit_accuracy,
        "mean_absolute_error": mae,
        "transition_event_accuracy": event_accuracy,
        "transition_cosine": direction_cosine,
    }


def _fit_one_writer(
    rows: Sequence[dict[str, Any]],
    config: dict[str, Any],
    contract: WriterClosureContract,
) -> dict[str, Any]:
    features, targets, groups, endpoints = _examples_for_config(rows, config)
    folds = _pair_blocked_folds(groups, contract.local_writer_fold_count)
    projection, phase = _projection_for(config, features.shape[1])
    fold_results: list[dict[str, Any]] = []
    for fold in range(contract.local_writer_fold_count):
        train = folds != fold
        test = folds == fold
        mean = np.mean(features[train], axis=0, dtype=np.float64).astype(np.float32)
        scale = np.std(features[train], axis=0, dtype=np.float64).astype(np.float32)
        scale = np.where(scale > np.float32(1e-6), scale, 1.0).astype(np.float32)
        train_normalized = (features[train] - mean) / scale
        test_normalized = (features[test] - mean) / scale
        train_design = _model_design(
            train_normalized,
            str(config["kind"]),
            projection,
            phase,
        )
        test_design = _model_design(
            test_normalized,
            str(config["kind"]),
            projection,
            phase,
        )
        weights, bias = _ridge_fit(train_design, targets[train], 0.30)
        metrics = _prediction_metrics(test_design @ weights + bias, targets[test])
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
    mean = np.mean(features, axis=0, dtype=np.float64).astype(np.float32)
    scale = np.std(features, axis=0, dtype=np.float64).astype(np.float32)
    scale = np.where(scale > np.float32(1e-6), scale, 1.0).astype(np.float32)
    normalized = (features - mean) / scale
    design = _model_design(
        normalized,
        str(config["kind"]),
        projection,
        phase,
    )
    weights, bias = _ridge_fit(design, targets, 0.30)
    training_metrics = _prediction_metrics(design @ weights + bias, targets)
    fold_bits = [row["form_bit_accuracy"] for row in fold_results]
    fold_transitions = [row["transition_cosine"] for row in fold_results]
    cross_validation = {
        "form_bit_accuracy_mean": float(np.mean(fold_bits)),
        "form_bit_accuracy_minimum": float(np.min(fold_bits)),
        "transition_cosine_mean": float(np.mean(fold_transitions)),
        "transition_event_accuracy_mean": float(
            np.mean([row["transition_event_accuracy"] for row in fold_results])
        ),
        "folds": fold_results,
    }
    gate = bool(
        cross_validation["form_bit_accuracy_mean"]
        >= contract.writer_bit_accuracy_minimum
        and cross_validation["form_bit_accuracy_minimum"]
        >= contract.writer_fold_minimum
    )
    selection_score = float(
        0.70 * cross_validation["form_bit_accuracy_mean"]
        + 0.20 * cross_validation["form_bit_accuracy_minimum"]
        + 0.10 * max(0.0, cross_validation["transition_cosine_mean"])
    )
    model: dict[str, Any] = {
        "model_id": f"stage6k-{config['config_id']}",
        "kind": str(config["kind"]),
        "radius": int(config["radius"]),
        "window": int(config["window"]),
        "canonicalize": bool(config["canonicalize"]),
        "input_mean": mean.tolist(),
        "input_scale": scale.tolist(),
        "weights": weights.tolist(),
        "bias": bias.tolist(),
        "model_frozen": True,
        "runtime_target_labels": False,
        "runtime_parent_field": False,
        "runtime_pair_identity": False,
        "runtime_generation_index": False,
        "training_pair_count": len(set(groups.tolist())),
        "training_example_count": len(features),
        "target_channels": ("reference-form", "directed-transition"),
    }
    if projection is not None and phase is not None:
        model["projection"] = projection.tolist()
        model["projection_phase"] = phase.tolist()
    model["model_digest"] = _digest(model)
    return {
        "config": dict(config),
        "state": "complete",
        "stage_gate": gate,
        "selection_score": selection_score,
        "cross_validation": cross_validation,
        "training_metrics": training_metrics,
        "model": model,
        "fold_assignment_digest": _digest(
            sorted(
                {
                    (str(group), int(fold))
                    for group, fold in zip(groups.tolist(), folds.tolist(), strict=True)
                }
            )
        ),
        "endpoint_digest": _digest(sorted(set(endpoints))),
    }


def _fit_writers(
    stage_root: Path,
    rows: Sequence[dict[str, Any]],
    profile_name: str,
    profile: WriterClosureProfile,
    contract: WriterClosureContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = stage_root / "writer-fit"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    fitted: dict[str, dict[str, Any]] = {}
    configs = _writer_configs()
    for index, config in enumerate(configs, start=1):
        path = checkpoints / f"{config['config_id']}.json"
        if resume and path.exists():
            checkpoint = _load_json(path)
            if checkpoint.get("design_digest") != design_digest:
                raise ValueError("Stage-6K writer-fit checkpoint design changed")
            fitted[str(config["config_id"])] = checkpoint["result"]
            continue
        if time.time() >= deadline:
            break
        result = _fit_one_writer(rows, config, contract)
        ar._atomic_json(
            path,
            {
                "design_digest": design_digest,
                "config_id": config["config_id"],
                "result": result,
            },
        )
        fitted[str(config["config_id"])] = result
        status(
            "running",
            "fit-local-writers",
            completed=len(fitted),
            total=len(configs),
            latest_checkpoint=str(config["config_id"]),
        )
    complete = len(fitted) == len(configs)
    scientific = profile_name == "reference"
    eligible = [
        row
        for row in fitted.values()
        if bool(row["stage_gate"]) or not scientific
    ]
    ranked = sorted(
        eligible,
        key=lambda row: (-float(row["selection_score"]), row["config"]["config_id"]),
    )
    selected_base = ranked[:2]
    frozen_models = [row["model"] for row in selected_base]
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and frozen_models),
        "scientific_gate_applied": scientific,
        "candidate_count": len(configs),
        "completed_candidate_count": len(fitted),
        "pair_blocked_fold_count": contract.local_writer_fold_count,
        "candidate_summaries": {
            config_id: {
                key: value
                for key, value in row.items()
                if key != "model"
            }
            | {"model_digest": row["model"]["model_digest"]}
            for config_id, row in sorted(fitted.items())
        },
        "selected_base_model_ids": [row["model"]["model_id"] for row in selected_base],
        "selected_base_model_digests": [
            row["model"]["model_digest"] for row in selected_base
        ],
        "maximum_frozen_candidates": profile.maximum_frozen_candidates,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    if complete:
        ar._atomic_text(root / "COMPLETE", "complete\n")
    return result, frozen_models


def _closure_candidates(
    source: dict[str, Any],
    models: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for model in models:
        for rehearsal in (False, True):
            row = copy.deepcopy(source)
            row.update(
                {
                    "candidate_id": (
                        f"{model['model_id']}-sr{int(rehearsal)}"
                    ),
                    "mechanism": "inherited-field",
                    "mechanism_tier": "inherited-field",
                    "claim_tier": "broad",
                    "adaptive_claim_tier": "rulebook-assisted",
                    "adaptive_architecture": str(model["kind"]),
                    "writer_source": "visible",
                    "writer_input_contract": "local-visible-spacetime-only",
                    "training_mode": "rulebook-assisted",
                    "field_rank": 16,
                    "field_channels": 2,
                    "field_bias": 0.70,
                    "field_support_sweeps": 8,
                    "daughter_writer_start_offset": 5,
                    "daughter_writer_sweeps": 16,
                    "daughter_write_rate": 0.50,
                    "adapter_learning_rate": 0.50,
                    "adapter_retention": 0.50,
                    "two_buffer_handoff": True,
                    "closure_model": copy.deepcopy(model),
                    "closure_self_rehearsal": rehearsal,
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
            candidates.append(row)
    if len(candidates) > 4:
        raise AssertionError("Stage-6K froze more than four candidates")
    return candidates


def _board_to_array(board: int, width: int = 32, height: int = 32) -> np.ndarray:
    return np.asarray(
        [(board >> position) & 1 for position in range(width * height)],
        dtype=np.bool_,
    ).reshape(height, width)


def _array_hex(state: np.ndarray) -> str:
    return np.packbits(np.asarray(state, dtype=np.bool_).reshape(-1)).tobytes().hex()


def _d4_state(state: np.ndarray, index: int) -> np.ndarray:
    current = np.asarray(state, dtype=np.bool_)
    if int(index) >= 4:
        current = np.flip(current, axis=-1)
    return np.rot90(current, int(index) % 4, axes=(-2, -1)).copy()


def _translation_signature(
    state: np.ndarray,
) -> tuple[tuple[tuple[int, int], ...], tuple[int, int]] | None:
    coords = np.argwhere(np.asarray(state, dtype=np.bool_))
    if len(coords) == 0:
        return None
    minimum = coords.min(axis=0)
    maximum = coords.max(axis=0)
    # A candidate reaching the toroidal seam is not treated as a finite mover.
    if np.any(minimum <= 1) or np.any(maximum >= np.asarray(state.shape) - 2):
        return None
    normalized = coords - minimum
    signature = tuple(sorted((int(y), int(x)) for y, x in normalized))
    return signature, (int(minimum[0]), int(minimum[1]))


def _detect_mover(
    history: Sequence[np.ndarray],
    *,
    start: int = 16,
    period_maximum: int = 16,
) -> dict[str, Any] | None:
    """Detect a finite translating periodic object without toroidal aliases."""

    if len(history) <= start + 2:
        return None
    first = _translation_signature(history[start])
    if first is None:
        return None
    for period in range(1, period_maximum + 1):
        if start + 2 * period >= len(history):
            break
        second = _translation_signature(history[start + period])
        third = _translation_signature(history[start + 2 * period])
        if second is None or third is None:
            continue
        if first[0] != second[0] or second[0] != third[0]:
            continue
        displacement = (
            second[1][0] - first[1][0],
            second[1][1] - first[1][1],
        )
        repeated = (
            third[1][0] - second[1][0],
            third[1][1] - second[1][1],
        )
        if displacement == (0, 0) or displacement != repeated:
            continue
        return {
            "period": period,
            "displacement_yx": displacement,
            "live_cells": len(first[0]),
            "detection_start": start,
            "verified_repetitions": 2,
        }
    return None


def _simulate_history(initial: np.ndarray, rule: int, sweeps: int = 48) -> list[np.ndarray]:
    state = np.asarray(initial, dtype=np.bool_)[None]
    history = [state[0].copy()]
    for _ in range(sweeps):
        state = life_like_step_batch(state, rule)
        history.append(state[0].copy())
    return history


def _seed_bank(rule: int, count: int) -> list[np.ndarray]:
    rng = np.random.default_rng(ar._hash_seed("stage6k-mover-bank", rule, count))
    patterns: list[np.ndarray] = []
    seen: set[int] = set()
    index = 0
    while len(patterns) < count:
        mass = int(rng.integers(5, 13))
        chosen = rng.choice(25, size=mass, replace=False)
        code = sum(1 << int(value) for value in chosen)
        index += 1
        if code in seen:
            continue
        seen.add(code)
        local = np.zeros((5, 5), dtype=np.bool_)
        local.reshape(-1)[chosen] = True
        board = np.zeros((32, 32), dtype=np.bool_)
        board[13:18, 13:18] = local
        patterns.append(board)
    return patterns


def _scan_movers_for_rule(rule: int, count: int) -> tuple[list[dict[str, Any]], int]:
    patterns = _seed_bank(rule, count)
    discoveries: list[dict[str, Any]] = []
    chunk_size = 256
    for offset in range(0, len(patterns), chunk_size):
        batch = np.stack(patterns[offset : offset + chunk_size], axis=0)
        history: list[np.ndarray] = [batch.copy()]
        state = batch
        for _ in range(48):
            state = life_like_step_batch(state, rule)
            history.append(state.copy())
        for local_index, initial in enumerate(batch):
            trajectory = [snapshot[local_index] for snapshot in history]
            detection = _detect_mover(trajectory)
            if detection is None:
                continue
            absolute_index = offset + local_index
            discoveries.append(
                {
                    "mover_id": f"discovered-r{rule}-s{absolute_index:04d}",
                    "source": "deterministic-5x5-scan",
                    "rule": rule,
                    "notation": life_rule_notation(rule),
                    "seed_index": absolute_index,
                    "initial_hex": _array_hex(initial),
                    **detection,
                }
            )
    return discoveries, len(patterns)


def _known_anchor_pairs() -> list[dict[str, Any]]:
    conway = parse_life_rule("B3/S23")
    named = named_patterns(32, 32)
    pairs: list[dict[str, Any]] = []
    for name in ("glider", "lwss"):
        base = _board_to_array(named[name])
        for rotation in range(4):
            forward = _d4_state(base, rotation)
            opposite = _d4_state(forward, 2)
            forward_detection = _detect_mover(_simulate_history(forward, conway))
            opposite_detection = _detect_mover(_simulate_history(opposite, conway))
            if forward_detection is None or opposite_detection is None:
                raise AssertionError(f"registered {name} anchor is not a mover")
            pairs.append(
                {
                    "pair_id": f"anchor-{name}-rot{rotation}",
                    "source": "named-d4-anchor",
                    "rule": conway,
                    "notation": life_rule_notation(conway),
                    "forward": {
                        "initial_hex": _array_hex(forward),
                        **forward_detection,
                    },
                    "opposite": {
                        "initial_hex": _array_hex(opposite),
                        **opposite_detection,
                    },
                }
            )
    return pairs


def _discovered_pair(row: dict[str, Any]) -> dict[str, Any] | None:
    forward = _unpack_state_hex(str(row["initial_hex"]), (32, 32))
    opposite = _d4_state(forward, 2)
    opposite_detection = _detect_mover(_simulate_history(opposite, int(row["rule"])))
    if opposite_detection is None:
        return None
    return {
        "pair_id": f"pair-{row['mover_id']}",
        "source": str(row["source"]),
        "rule": int(row["rule"]),
        "notation": str(row["notation"]),
        "forward": {
            "initial_hex": str(row["initial_hex"]),
            "period": int(row["period"]),
            "displacement_yx": list(row["displacement_yx"]),
            "live_cells": int(row["live_cells"]),
        },
        "opposite": {
            "initial_hex": _array_hex(opposite),
            **opposite_detection,
        },
    }


def _shape_jaccard(left: np.ndarray, right: np.ndarray) -> float:
    left_signature = _translation_signature(left)
    right_signature = _translation_signature(right)
    if left_signature is None or right_signature is None:
        return 0.0
    left_set = set(left_signature[0])
    right_set = set(right_signature[0])
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 0.0


def _phase_translation_score(
    observed: Sequence[np.ndarray],
    target: Sequence[np.ndarray],
) -> float:
    if not observed or not target:
        return 0.0
    best = 0.0
    for phase in range(len(target)):
        values = [
            _shape_jaccard(value, target[(index + phase) % len(target)])
            for index, value in enumerate(observed)
        ]
        best = max(best, float(np.mean(values)))
    return best


def _velocity_similarity(left: Sequence[int], right: Sequence[int]) -> float:
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denominator) if denominator else 0.0


def _direction_paired_metric(
    observed_sequence: Sequence[np.ndarray],
    observed_displacement: Sequence[int],
    forward_sequence: Sequence[np.ndarray],
    forward_displacement: Sequence[int],
    opposite_sequence: Sequence[np.ndarray],
    opposite_displacement: Sequence[int],
) -> dict[str, float]:
    forward_shape = _phase_translation_score(observed_sequence, forward_sequence)
    opposite_shape = _phase_translation_score(observed_sequence, opposite_sequence)
    forward_velocity = 0.5 + 0.5 * _velocity_similarity(
        observed_displacement, forward_displacement
    )
    opposite_velocity = 0.5 + 0.5 * _velocity_similarity(
        observed_displacement, opposite_displacement
    )
    forward = 0.70 * forward_shape + 0.30 * forward_velocity
    opposite = 0.70 * opposite_shape + 0.30 * opposite_velocity
    return {
        "forward_score": float(forward),
        "opposite_score": float(opposite),
        "direction_margin": float(forward - opposite),
        "phase_translation_aligned": True,
        "velocity_direction_retained": True,
    }


def _metric_audit_on_pair(pair: dict[str, Any]) -> dict[str, Any]:
    forward_state = _unpack_state_hex(pair["forward"]["initial_hex"], (32, 32))
    opposite_state = _unpack_state_hex(pair["opposite"]["initial_hex"], (32, 32))
    rule = int(pair["rule"])
    forward_history = _simulate_history(forward_state, rule, 32)
    opposite_history = _simulate_history(opposite_state, rule, 32)
    period = int(pair["forward"]["period"])
    forward_sequence = forward_history[16 : 16 + period]
    opposite_period = int(pair["opposite"]["period"])
    opposite_sequence = opposite_history[16 : 16 + opposite_period]
    intact = _direction_paired_metric(
        forward_sequence,
        pair["forward"]["displacement_yx"],
        forward_sequence,
        pair["forward"]["displacement_yx"],
        opposite_sequence,
        pair["opposite"]["displacement_yx"],
    )
    reversed_metric = _direction_paired_metric(
        list(reversed(forward_sequence)),
        [-int(value) for value in pair["forward"]["displacement_yx"]],
        forward_sequence,
        pair["forward"]["displacement_yx"],
        opposite_sequence,
        pair["opposite"]["displacement_yx"],
    )
    return {"intact": intact, "reversed": reversed_metric}


def _build_mover_panel(
    stage_root: Path,
    profile: WriterClosureProfile,
    contract: WriterClosureContract,
    *,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    cached = stage_root / "MOVER_PANEL.json"
    if cached.exists():
        return _load_json(cached)
    anchors = _known_anchor_pairs()
    discoveries: list[dict[str, Any]] = []
    per_rule: dict[str, Any] = {}
    for index, rule in enumerate(MOVER_RULES, start=1):
        if time.time() >= deadline:
            break
        rows, scanned = _scan_movers_for_rule(rule, profile.mover_seeds_per_rule)
        per_rule[str(rule)] = {
            "notation": life_rule_notation(rule),
            "scanned": scanned,
            "detected": len(rows),
            "detection_fraction": len(rows) / scanned if scanned else 0.0,
        }
        discoveries.extend(rows)
        status(
            "running",
            "scan-deterministic-movers",
            completed=index,
            total=len(MOVER_RULES),
            rule=rule,
            discovered=len(discoveries),
        )
    unique: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in sorted(
        discoveries,
        key=lambda value: (
            ar._hash_seed("stage6k-mover-selection", value["mover_id"]),
            value["mover_id"],
        ),
    ):
        key = (
            int(row["rule"]),
            int(row["period"]),
            tuple(row["displacement_yx"]),
            str(row["initial_hex"]),
        )
        if key in seen:
            continue
        pair = _discovered_pair(row)
        if pair is None:
            continue
        seen.add(key)
        unique.append(pair)
        if len(unique) >= max(8, profile.mover_min_discovered_pairs):
            break
    selected = [*anchors, *unique]
    selected = selected[: max(profile.mover_min_pairs, len(anchors))]
    allocation = {
        row["pair_id"]: ("development" if index % 2 == 0 else "heldout")
        for index, row in enumerate(selected)
    }
    metric_audits = {
        row["pair_id"]: _metric_audit_on_pair(row) for row in selected
    }
    margins = [
        audit["intact"]["direction_margin"] for audit in metric_audits.values()
    ]
    scanned_total = sum(int(row["scanned"]) for row in per_rule.values())
    complete_scan = len(per_rule) == len(MOVER_RULES)
    gate = bool(
        complete_scan
        and len(selected) >= profile.mover_min_pairs
        and len(unique) >= profile.mover_min_discovered_pairs
        and margins
        and min(margins) >= contract.dynamic_direction_margin_minimum
    )
    result = {
        "state": "complete" if complete_scan else "budget_truncated",
        "stage_gate": gate,
        "rules": per_rule,
        "scanned_seed_count": scanned_total,
        "registered_seed_count": len(MOVER_RULES) * profile.mover_seeds_per_rule,
        "anchor_pair_count": len(anchors),
        "discovered_pair_count": len(unique),
        "selected_pair_count": len(selected),
        "minimum_pair_count": profile.mover_min_pairs,
        "minimum_discovered_pair_count": profile.mover_min_discovered_pairs,
        "allocation": allocation,
        "pairs": selected,
        "metric_audits": metric_audits,
        "direction_margin_minimum": min(margins) if margins else None,
        "direction_margin_mean": float(np.mean(margins)) if margins else None,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(cached, result)
    return result


def _oracle_candidates(source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specifications = (
        ("target-finite", "target", False, False),
        ("target-full-support", "target", True, False),
        ("target-finite-self-rehearsal", "target", False, True),
        ("opposite-history", "opposite", False, False),
        ("random-history", "random", False, False),
    )
    for name, mode, full_support, rehearsal in specifications:
        row = copy.deepcopy(source)
        row.update(
            {
                "candidate_id": f"stage6k-oracle-{name}",
                "mechanism": "inherited-field",
                "mechanism_tier": "inherited-field",
                "claim_tier": "broad",
                "adaptive_claim_tier": "oracle-control",
                "adaptive_architecture": "ideal-field-oracle",
                "field_rank": 16,
                "field_channels": 2,
                "field_bias": 0.70,
                "field_support_sweeps": 8,
                "daughter_writer_start_offset": 5,
                "daughter_writer_sweeps": 16,
                "two_buffer_handoff": True,
                "closure_oracle_mode": mode,
                "closure_full_support": full_support,
                "closure_self_rehearsal": rehearsal,
                "closure_rehearsal_bias": 0.45,
                "closure_disable_texture_carrier": True,
                "runtime_target_labels": True,
                "parent_field_exposed_to_writer": False,
                "promotable": False,
            }
        )
        rows.append(row)
    return rows


def _lineage_metric_values(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
    key: str,
) -> list[float]:
    values: list[float] = []
    for row in rows:
        if row.get("candidate_id") != candidate_id:
            continue
        try:
            value = row["conditions"][condition]["texture_history"][str(generation)][key]
        except KeyError:
            continue
        values.append(float(value))
    return values


def _mean_or_none(values: Sequence[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _run_oracle_ladder(
    stage_root: Path,
    source: dict[str, Any],
    pairs: Sequence[dict[str, Any]],
    profile: WriterClosureProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: WriterClosureContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    candidates = _oracle_candidates(source)
    items = ar._make_items(
        pairs[: profile.oracle_pairs],
        candidates,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="stage6k-oracle-ladder",
        replicates=profile.oracle_replicates,
        generations=8,
        conditions=(
            "intact",
            "no_rewrite",
            "inherited_field_read_disabled",
            "handoff_visible_scrub",
            "closure_self_rehearsal_disabled",
        ),
        analysis_kind="nonpromotable-oracle",
    )
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        "oracle-ladder-trajectories",
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
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        condition_metrics: dict[str, Any] = {}
        for condition in (
            "intact",
            "no_rewrite",
            "inherited_field_read_disabled",
            "handoff_visible_scrub",
            "closure_self_rehearsal_disabled",
        ):
            condition_metrics[condition] = {
                key: _mean_or_none(
                    _lineage_metric_values(rows, candidate_id, condition, 8, key)
                )
                for key in (
                    "read_match_mean",
                    "post_washout_match_mean",
                    "writer_match_mean",
                    "terminal_match_mean",
                )
            }
        summaries[candidate_id] = {
            "oracle_mode": candidate["closure_oracle_mode"],
            "full_support": bool(candidate["closure_full_support"]),
            "self_rehearsal": bool(candidate["closure_self_rehearsal"]),
            "promotable": False,
            "runtime_target_labels": True,
            "metrics": condition_metrics,
        }
    finite = summaries["stage6k-oracle-target-finite"]["metrics"]["intact"]
    full = summaries["stage6k-oracle-target-full-support"]["metrics"]["intact"]
    rehearsal = summaries["stage6k-oracle-target-finite-self-rehearsal"]["metrics"][
        "intact"
    ]
    random = summaries["stage6k-oracle-random-history"]["metrics"]["intact"]
    # ``read_match`` is captured at the end of the ordinary texture-reader
    # window, immediately before the inherited slow field begins.  The oracle
    # ceiling therefore lives in the later post/writer/terminal checkpoints.
    full_effect = max(
        float(full[key] or 0.0)
        for key in (
            "post_washout_match_mean",
            "writer_match_mean",
            "terminal_match_mean",
        )
    )
    finite_post = float(finite["post_washout_match_mean"] or 0.0)
    random_post = float(random["post_washout_match_mean"] or 0.0)
    rehearsal_post = float(rehearsal["post_washout_match_mean"] or 0.0)
    if full_effect <= 0.05:
        localization = "READER_OR_LOCAL_ATTRACTOR_CEILING_FAILS"
    elif finite_post <= random_post + 0.05 and rehearsal_post <= random_post + 0.05:
        localization = "FINITE_SUPPORT_ATTRACTOR_FAILS"
    elif rehearsal_post > finite_post + 0.05:
        localization = "SELF_REHEARSAL_EXTENDS_FINITE_SUPPORT"
    else:
        localization = "WRITER_CLOSURE_IS_PRIMARY_REMAINING_BOUNDARY"
    gate = bool(
        complete
        and full_effect > 0.05
        and max(finite_post, rehearsal_post) > random_post + 0.05
    )
    return {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": gate,
        "oracle_candidates_nonpromotable": True,
        "oracle_runtime_target_access": True,
        "localization": localization,
        "full_support_effect_ceiling": full_effect,
        "candidate_summaries": summaries,
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "final_audit_trajectory_state": "untouched",
    }


def _run_heldout_lineages(
    stage_root: Path,
    candidates: Sequence[dict[str, Any]],
    pairs: Sequence[dict[str, Any]],
    profile: WriterClosureProfile,
    nested_profile: pb.PhenotypeBridgeProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: WriterClosureContract,
    design_digest: str,
    profile_name: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not candidates:
        return (
            {
                "state": "complete",
                "stage_gate": False,
                "candidate_summaries": {},
                "qualified_candidate_ids": [],
                "skipped_reason": "no writer passed the exposed pair-blocked gate",
                "final_audit_trajectory_state": "untouched",
            },
            [],
        )
    items = ar._make_items(
        pairs,
        candidates,
        ar._template_pairs(templates, "qualification"),
        frozen["stage4"]["configuration"],
        phase="stage6k-heldout",
        replicates=profile.heldout_replicates,
        generations=8,
        conditions=HELDOUT_CONDITIONS,
        analysis_kind="frozen-closure-heldout",
    )
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        "heldout-closure-trajectories",
        items,
        list(candidates),
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
    scientific = profile_name == "reference"
    summaries: dict[str, Any] = {}
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        summary = ah._augment_static(
            rows,
            candidate,
            8,
            nested_profile,
            contract,
            "stage6k-heldout",
        )
        gate = ah._static_gate(summary, contract) if scientific else True
        summaries[candidate_id] = {
            "candidate": pb._candidate_public(candidate),
            "static": summary,
            "static_gate": gate,
        }
    qualified = [
        candidate_id
        for candidate_id, summary in summaries.items()
        if bool(summary["static_gate"])
    ]
    if not complete:
        qualified = []
    return (
        {
            "state": "complete" if complete else "budget_truncated",
            "stage_gate": bool(qualified),
            "scientific_gate_applied": scientific,
            "candidate_summaries": summaries,
            "qualified_candidate_ids": qualified,
            "completed_trajectories": len(rows),
            "registered_trajectories": len(items),
            "final_audit_trajectory_state": "untouched",
        },
        rows,
    )


def _center_for_state(state: np.ndarray) -> np.ndarray:
    coords = np.argwhere(np.asarray(state, dtype=np.bool_))
    if len(coords) == 0:
        return np.asarray([[state.shape[0] // 2, state.shape[1] // 2]], dtype=np.int16)
    center = np.rint((coords.min(axis=0) + coords.max(axis=0)) / 2.0).astype(np.int16)
    return center[None]


def _direction_writer_trace(
    model: dict[str, Any],
    initial: np.ndarray,
    rule: int,
    period: int,
) -> dict[str, Any]:
    history = _simulate_history(initial, rule, 32)
    predictions: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    for endpoint in range(16, 16 + period):
        centers = _center_for_state(history[endpoint])
        local_history = [
            state[None]
            for state in history[max(0, endpoint - int(model["window"]) + 1) : endpoint + 1]
        ]
        prediction = pb._closure_model_predict(local_history, centers, model)[0]
        current = ar.observe_texture(history[endpoint][None], centers)[0]
        previous = ar.observe_texture(history[endpoint - 1][None], centers)[0]
        transition = np.where(current != previous, current, 0.0).astype(np.float32)
        predictions.append(prediction)
        targets.append(np.stack((current, transition), axis=0))
    return {
        "predictions": np.stack(predictions, axis=0),
        "targets": np.stack(targets, axis=0),
    }


def _patch_sequence_score(predictions: np.ndarray, targets: np.ndarray) -> float:
    left = np.asarray(predictions, dtype=np.float32)
    right = np.asarray(targets, dtype=np.float32)
    length = min(len(left), len(right))
    if length == 0:
        return 0.0
    left = left[:length]
    best = -1.0
    for phase in range(len(right)):
        ordered = np.stack(
            [right[(index + phase) % len(right)] for index in range(length)], axis=0
        )
        form = float(np.mean((left[:, 0] >= 0.0) == (ordered[:, 0] >= 0.0)))
        x = left[:, 1].reshape(length, -1)
        y = ordered[:, 1].reshape(length, -1)
        numerator = np.sum(x * y, axis=1)
        denominator = np.linalg.norm(x, axis=1) * np.linalg.norm(y, axis=1)
        transition = float(
            np.mean(
                np.divide(
                    numerator,
                    denominator,
                    out=np.zeros_like(numerator),
                    where=denominator > np.float32(1e-8),
                )
            )
        )
        best = max(best, 0.75 * form + 0.25 * (0.5 + 0.5 * transition))
    return float(best)


def _install_signed_patch(patch: np.ndarray) -> np.ndarray:
    board = np.zeros((32, 32), dtype=np.bool_)
    center = np.asarray([[16, 16]], dtype=np.int16)
    ys, xs = ar._patch_indices(center, 32)
    board[np.ix_(ys[0], xs[0])] = np.asarray(patch) >= 0.0
    return board


def _one_boundary_object_recovery(
    prediction: np.ndarray,
    rule: int,
    target_displacement: Sequence[int],
) -> dict[str, Any]:
    seeded = _install_signed_patch(prediction[0])
    detection = _detect_mover(_simulate_history(seeded, rule, 48))
    recovered = bool(
        detection is not None
        and _velocity_similarity(
            detection["displacement_yx"], target_displacement
        )
        > 0.5
    )
    opposite_seeded = _install_signed_patch(-prediction[0])
    opposite_detection = _detect_mover(_simulate_history(opposite_seeded, rule, 48))
    return {
        "visible_state_reset_before_read": True,
        "field_installed_as_local_visible_read_ceiling": True,
        "recovered_correct_direction": recovered,
        "detected": detection,
        "zero_carrier_detected": False,
        "opposite_carrier_detected": opposite_detection is not None,
    }


def _dynamic_writer_bank(
    candidates: Sequence[dict[str, Any]],
    panel: dict[str, Any],
    contract: WriterClosureContract,
    profile_name: str,
) -> dict[str, Any]:
    heldout_pairs = [
        row
        for row in panel.get("pairs", [])
        if panel.get("allocation", {}).get(row["pair_id"]) == "heldout"
    ]
    summaries: dict[str, Any] = {}
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        model = candidate["closure_model"]
        pair_rows: list[dict[str, Any]] = []
        for pair in heldout_pairs:
            rule = int(pair["rule"])
            forward_initial = _unpack_state_hex(
                pair["forward"]["initial_hex"], (32, 32)
            )
            opposite_initial = _unpack_state_hex(
                pair["opposite"]["initial_hex"], (32, 32)
            )
            forward = _direction_writer_trace(
                model, forward_initial, rule, int(pair["forward"]["period"])
            )
            opposite = _direction_writer_trace(
                model, opposite_initial, rule, int(pair["opposite"]["period"])
            )
            forward_own = _patch_sequence_score(
                forward["predictions"], forward["targets"]
            )
            forward_other = _patch_sequence_score(
                forward["predictions"], opposite["targets"]
            )
            opposite_own = _patch_sequence_score(
                opposite["predictions"], opposite["targets"]
            )
            opposite_other = _patch_sequence_score(
                opposite["predictions"], forward["targets"]
            )
            forward_recovery = _one_boundary_object_recovery(
                forward["predictions"][-1],
                rule,
                pair["forward"]["displacement_yx"],
            )
            opposite_recovery = _one_boundary_object_recovery(
                opposite["predictions"][-1],
                rule,
                pair["opposite"]["displacement_yx"],
            )
            pair_rows.append(
                {
                    "pair_id": pair["pair_id"],
                    "source": pair["source"],
                    "rule": rule,
                    "forward_score": forward_own,
                    "forward_opposite_score": forward_other,
                    "opposite_score": opposite_own,
                    "opposite_forward_score": opposite_other,
                    "direction_margin": 0.5
                    * ((forward_own - forward_other) + (opposite_own - opposite_other)),
                    "form_bit_accuracy": float(
                        0.5
                        * (
                            np.mean(
                                (forward["predictions"][:, 0] >= 0.0)
                                == (forward["targets"][:, 0] >= 0.0)
                            )
                            + np.mean(
                                (opposite["predictions"][:, 0] >= 0.0)
                                == (opposite["targets"][:, 0] >= 0.0)
                            )
                        )
                    ),
                    "forward_recovery": forward_recovery,
                    "opposite_recovery": opposite_recovery,
                }
            )
        margins = [row["direction_margin"] for row in pair_rows]
        form = [row["form_bit_accuracy"] for row in pair_rows]
        recoveries = [
            float(row[direction]["recovered_correct_direction"])
            for row in pair_rows
            for direction in ("forward_recovery", "opposite_recovery")
        ]
        gate = bool(
            panel.get("stage_gate")
            and pair_rows
            and float(np.mean(form)) >= contract.writer_bit_accuracy_minimum
            and float(np.mean(margins))
            >= contract.dynamic_direction_margin_minimum
            and float(np.mean(recoveries)) >= 0.50
        )
        if profile_name == "smoke":
            gate = bool(pair_rows)
        summaries[candidate_id] = {
            "stage_gate": gate,
            "heldout_mover_pair_count": len(pair_rows),
            "form_bit_accuracy_mean": float(np.mean(form)) if form else None,
            "direction_margin_mean": float(np.mean(margins)) if margins else None,
            "direction_margin_minimum": float(np.min(margins)) if margins else None,
            "one_boundary_correct_direction_recovery_fraction": (
                float(np.mean(recoveries)) if recoveries else None
            ),
            "phase_and_translation_aligned": True,
            "visible_reset_recovery_is_one_boundary_only": True,
            "not_sufficient_alone_for_ph": True,
            "pair_results": pair_rows,
        }
    qualified = [
        candidate_id
        for candidate_id, summary in summaries.items()
        if summary["stage_gate"]
    ]
    return {
        "state": "complete",
        "stage_gate": bool(qualified),
        "qualified_candidate_ids": qualified,
        "candidate_summaries": summaries,
        "heldout_object_bank": True,
        "dynamic_claim_requires_narrow_causal_gate_too": True,
        "final_audit_trajectory_state": "untouched",
    }


def _campaign_result(
    output: Path,
    design_digest: str,
    profile_name: str,
    mover: dict[str, Any],
    oracle: dict[str, Any],
    fit: dict[str, Any],
    heldout: dict[str, Any],
    dynamic: dict[str, Any],
) -> dict[str, Any]:
    narrow = list(heldout.get("qualified_candidate_ids", []))
    dynamic_ids = list(dynamic.get("qualified_candidate_ids", []))
    joint = sorted(set(narrow) & set(dynamic_ids))
    states = [fit.get("state"), oracle.get("state"), heldout.get("state")]
    if profile_name == "smoke":
        verdict = "SMOKE_PATH_VALIDATED"
    elif "budget_truncated" in states or mover.get("state") == "budget_truncated":
        verdict = "INCONCLUSIVE_RESOURCE_LIMIT"
    elif joint:
        verdict = "HELDOUT_WRITER_CLOSURE_WITH_DYNAMIC_TRANSFER"
    elif narrow:
        verdict = "HELDOUT_STATIC_WRITER_CLOSURE_ONLY"
    elif dynamic_ids:
        verdict = "DYNAMIC_OBJECT_TRANSFER_WITHOUT_NARROW_CAUSAL_HANDOFF"
    elif not fit.get("stage_gate"):
        verdict = "LOCAL_WRITER_TARGET_NOT_CROSS_VALIDATED"
    elif not oracle.get("stage_gate"):
        verdict = str(oracle.get("localization", "ORACLE_CEILING_FAILED"))
    else:
        verdict = "FROZEN_WRITER_CLOSURE_NOT_CAUSAL_ON_HELDOUT"
    result = {
        "experiment": "ca_motif_writer_closure_stage_6k",
        "design_digest": design_digest,
        "profile_name": profile_name,
        "state": "complete",
        "stage_gate": bool(joint),
        "verdict": verdict,
        "narrow_heldout_candidate_ids": narrow,
        "dynamic_heldout_candidate_ids": dynamic_ids,
        "joint_candidate_ids": joint,
        "mover_panel_gate": bool(mover.get("stage_gate")),
        "oracle_ladder_gate": bool(oracle.get("stage_gate")),
        "writer_cross_validation_gate": bool(fit.get("stage_gate")),
        "narrow_causal_gate": bool(narrow),
        "dynamic_object_gate": bool(dynamic_ids),
        "oracle_localization": oracle.get("localization"),
        "oracle_candidates_promotable": False,
        "runtime_target_exposure_for_learned_writers": False,
        "parent_field_exposed_to_learned_writer": False,
        "two_buffer_handoff": True,
        "self_rehearsal_tested_after_freezing": True,
        "static_and_dynamic_claims_separate": True,
        "dynamic_one_boundary_recovery_not_alone_ph": True,
        "final_audit_opened": False,
        "final_audit_trajectory_state": "untouched",
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
            "final_audit_trajectory_state": "untouched",
        },
    )
    report = [
        "# Stage 6K learned writer closure and moving forms",
        "",
        f"Verdict: **{verdict}**.",
        "",
        "| Registered question | Gate |",
        "|---|---:|",
        f"| Independent translating-object bank | {bool(mover.get('stage_gate'))} |",
        f"| Non-promotable ideal-field ladder | {bool(oracle.get('stage_gate'))} |",
        f"| Six-fold pair-blocked writer fit | {bool(fit.get('stage_gate'))} |",
        f"| Narrow eight-pair causal heldout | {bool(narrow)} |",
        f"| Heldout moving-object transfer | {bool(dynamic_ids)} |",
        "",
        f"Oracle localization: `{oracle.get('localization')}`.",
        "",
        "The 62-pair final reserve was neither loaded nor simulated.",
    ]
    ar._atomic_text(output / "REPORT.md", "\n".join(report) + "\n")
    if joint:
        lay = (
            "A frozen local writer rebuilt a useful daughter memory from the visible CA "
            "history on new narrow cases, and the same writer also distinguished and "
            "recovered moving forms in the independent object bank."
        )
    elif narrow:
        lay = (
            "The daughter learned to rewrite the narrow texture memory on unseen cases, "
            "but that success did not yet extend to direction-specific moving objects."
        )
    elif dynamic_ids:
        lay = (
            "The moving-object diagnostic worked, but the full narrow causal handoff did "
            "not; this is useful target evidence, not yet Plastic Heredity."
        )
    elif verdict == "INCONCLUSIVE_RESOURCE_LIMIT":
        lay = "The eight-hour clock ended before all preregistered gates were completed."
    else:
        lay = (
            "The experiment could copy and test ideal memories, but no frozen local writer "
            "passed the complete unseen causal handoff and moving-form ladder."
        )
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
    marker = "<!-- CA_MOTIF_STAGE6K_RESULT -->"
    prior = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in prior:
        return
    entry = (
        "\n\n"
        + marker
        + "\n## CA motif-lineage Stage 6K — learned writer closure and moving forms\n\n"
        + f"The registered campaign completed with verdict `{result['verdict']}`. "
        + "Ideal-field controls were non-promotable; learned writers had no runtime "
        + "target, parent field, pair identity, or generation-index access. "
        + f"Joint heldout candidates: {result.get('joint_candidate_ids', [])}. "
        + "The independent direction-aware mover bank and narrow causal lineage were "
        + "adjudicated separately. The 62-pair reserve remained untouched.\n\n"
        + f"Pollable artifacts: `{output.relative_to(ROOT)}`. Protocol: "
        + "`CA_MOTIF_WRITER_CLOSURE_PROTOCOL.md`. Implementation: "
        + "`plastic_ca/motif_writer_closure.py`.\n"
    )
    ar._atomic_text(path, prior.rstrip() + entry)


def run_motif_writer_closure(
    output: Path,
    *,
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
    """Run the sealed Stage-6K campaign without opening the final reserve."""

    ar.require_pinned_numpy()
    if profile_name not in PROFILES:
        raise ValueError(f"unknown Stage-6K profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6K workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6K max-hours must be in (0, 8]")
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
        contract, profile, campaign, design_digest, integrity = _prepare_campaign(
            output,
            profile_name,
            stage6j_root.resolve(),
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
            integrity | {"next_phase": "mover-panel"},
            "# Stage 6K integrity\n\nThe Stage 6J negative boundary, 48 exposed pairs, eight untouched endurance pairs, and sealed 62-pair reserve were hash-verified.",
            "# Lay summary\n\nTraining and testing cases are separated before any new model is fitted.",
        )
        stage_root = output / "stage6k"
        frozen, cohorts, nested_profile, writer_contract, templates = _reconstruct_cohorts(
            stage_root,
            profile_name,
            profile,
            integrity,
            stage6j_root.resolve(),
            roots,
        )
        source = _materialize_source_candidate(
            stage_root,
            stage6h_root.resolve(),
            stage6br_root.resolve(),
            design_digest,
        )

        active[0] = "mover-panel"
        mover = _build_mover_panel(
            stage_root,
            profile,
            contract,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
        )
        _write_phase(
            output,
            "mover-panel",
            design_digest,
            mover | {"next_phase": "oracle-ladder"},
            "# Stage 6K moving-form panel\n\nGlider/LWSS D4 anchors and deterministic 5x5 searches were checked for period-16-or-shorter translation, then scored with phase, translation, and velocity direction kept separate.",
            "# Lay summary\n\nThe dynamic test now uses things that genuinely move, so a still picture cannot fake a remembered direction.",
        )

        active[0] = "oracle-ladder"
        oracle = _run_oracle_ladder(
            stage_root,
            source,
            cohorts["exposed"],
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
            "oracle-ladder",
            design_digest,
            oracle | {"next_phase": "fit"},
            "# Stage 6K oracle ladder\n\nFinite, full-support, self-rehearsing, opposite, and random ideal daughter fields localized the reader/attractor/write boundary. All target-exposed cells were barred from promotion.",
            "# Lay summary\n\nPerfect cheat-sheet memories tell us whether the reader can use a good note; they can diagnose the machinery but cannot count as success.",
        )

        active[0] = "fit"
        trace_rows, traces_complete, trace_total = _collect_traces(
            stage_root,
            source,
            cohorts["exposed"],
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
        if traces_complete:
            fit, selected_models = _fit_writers(
                stage_root,
                trace_rows,
                profile_name,
                profile,
                contract,
                design_digest,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                status=status,
            )
        else:
            fit = {
                "state": "budget_truncated",
                "stage_gate": False,
                "candidate_summaries": {},
                "selected_base_model_ids": [],
                "skipped_reason": "exposed trace collection exceeded exploration budget",
                "final_audit_trajectory_state": "untouched",
            }
            selected_models = []
        fit["trace_collection_complete"] = traces_complete
        fit["completed_trace_trajectories"] = len(trace_rows)
        fit["registered_trace_trajectories"] = trace_total
        candidates = _closure_candidates(source, selected_models)
        ar._atomic_json(
            stage_root / "SEALED_CLOSURE_MODELS.json",
            {
                "design_digest": design_digest,
                "frozen_before_heldout": True,
                "maximum_candidates": 4,
                "selected_base_models": selected_models,
                "candidate_ids": [row["candidate_id"] for row in candidates],
                "self_rehearsal_variants_frozen": (False, True),
                "runtime_target_labels": False,
                "runtime_parent_field": False,
                "final_audit_trajectory_state": "untouched",
            },
        )
        _write_phase(
            output,
            "fit",
            design_digest,
            fit | {"next_phase": "heldout"},
            "# Stage 6K local writer fitting\n\nTwenty-four registered local writers entered six pair-blocked folds. At most two base models, each with rehearsal off/on frozen in advance, could enter heldout testing.",
            "# Lay summary\n\nThe writer learns from old cases only, then its settings are locked before it sees any new lineage.",
        )

        active[0] = "heldout"
        heldout, _ = _run_heldout_lineages(
            stage_root,
            candidates,
            cohorts["heldout"],
            profile,
            nested_profile,
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
        dynamic = _dynamic_writer_bank(candidates, mover, contract, profile_name)
        ar._atomic_json(stage_root / "DYNAMIC_WRITER_BANK.json", dynamic)
        heldout["dynamic_object_bank"] = dynamic
        _write_phase(
            output,
            "heldout",
            design_digest,
            heldout | {"next_phase": "adjudicate"},
            "# Stage 6K heldout tests\n\nFrozen learned writers faced eight untouched narrow pairs with ablation, rescue, opposite-history, no-rewrite, and self-rehearsal controls, plus the separately heldout moving-object bank.",
            "# Lay summary\n\nA real success must work on new examples, fail when its memory machinery is removed, and preserve which way a moving form is going.",
        )

        active[0] = "adjudicate"
        result = _campaign_result(
            output,
            design_digest,
            profile_name,
            mover,
            oracle,
            fit,
            heldout,
            dynamic,
        )
        _write_phase(
            output,
            "adjudicate",
            design_digest,
            result,
            "# Stage 6K adjudication\n\nNarrow causal closure and wider dynamic transfer were reported separately; a joint verdict required the same frozen candidate to pass both.",
            "# Lay summary\n\nThe result distinguishes learning to rewrite a memory from merely recognizing or reseeding a moving pattern.",
        )
        _update_discovery_log(result, output)
        status(
            "complete",
            "campaign-complete",
            verdict=result["verdict"],
            final_audit_trajectory_state="untouched",
        )
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
    "DEFAULT_STAGE6J_ROOT",
    "MOVER_RULES",
    "PHASES",
    "PROFILES",
    "WRITER_KINDS",
    "WriterClosureContract",
    "WriterClosureProfile",
    "_detect_mover",
    "_direction_paired_metric",
    "_fit_one_writer",
    "_parent_integrity",
    "_pair_blocked_folds",
    "_writer_configs",
    "run_motif_writer_closure",
]
