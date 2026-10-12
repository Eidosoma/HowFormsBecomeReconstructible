"""Stage-6E-R/6F acquisition repair and causal write-back ladder.

The campaign first replays the registered Stage-6E experiment after repairing
its founder-write gate.  Only if no repaired Stage-6E design passes screening
does it inspect carrier-free observability and seal a bounded family of
temporal or zero-born somatic writers.  The protected reserve remains behind
the inherited Stage-6E qualification, endurance, and adjudication gates.
"""

from __future__ import annotations

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
from . import motif_phenotype_bridge as pb


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_WRITEBACK_LADDER_PROTOCOL.md"
DEFAULT_STAGE6E_ROOT = ROOT / "results/ca-motif-phenotype-bridge-stage-6e"
PHASES = (
    "integrity",
    "replay",
    "observability",
    "discover",
    "screen",
    "qualify",
    "endurance",
    "adjudicate",
)


@dataclass(frozen=True)
class WritebackLadderContract(pb.PhenotypeBridgeContract):
    implementation_version: str = "ca-motif-writeback-ladder-v1"
    namespace: str = "plastic-ca-motif-writeback-ladder-v1"
    observability_accuracy_minimum: float = 0.60
    observability_effect_minimum: float = 0.05
    maximum_promotable_writers: int = 12
    exploration_stop_hours: float = 5.5
    max_hours: float = 8.0

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "observability_accuracy_minimum": self.observability_accuracy_minimum,
                "observability_effect_minimum": self.observability_effect_minimum,
                "maximum_promotable_writers": self.maximum_promotable_writers,
                "adaptive_route": "corrected-stage6e-first; stage6f-only-after-screen-failure",
                "confirmatory_claims": (
                    "strict-form-mediated",
                    "somatically-mediated",
                ),
            }
        )
        return payload


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _required_hashes(root: Path) -> dict[str, str]:
    names = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "COHORTS.json",
        "screen/RESULTS.json",
        "COMPLETE",
    )
    missing = [root / name for name in names if not (root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing invalidated Stage-6E artifacts: {missing}")
    result = _load_json(root / "RESULTS.json")
    status = _load_json(root / "STATUS.json")
    cohorts = _load_json(root / "COHORTS.json")
    design = _load_json(root / "DESIGN.json")
    if result.get("verdict") != "DIRECT_ECHO_ONLY" or status.get("state") != "complete":
        raise ValueError("the frozen Stage-6E result no longer matches the invalidated run")
    if design.get("contract", {}).get("implementation_version") != "ca-motif-phenotype-bridge-v1":
        raise ValueError("the invalidated Stage-6E implementation version changed")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("the protected Stage-6E reserve is no longer untouched")
    return {name: ar._sha256(root / name) for name in names}


def _prepare_top_level(
    output: Path,
    profile_name: str,
    stage6e_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[WritebackLadderContract, dict[str, Any], str]:
    contract = WritebackLadderContract()
    invalidated_hashes = _required_hashes(stage6e_root)
    design = {
        "experiment": "ca_motif_writeback_ladder_stage_6f",
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(pb.PHENOTYPE_BRIDGE_PROFILES[profile_name]),
        "invalidated_stage6e_root": str(stage6e_root.resolve()),
        "invalidated_stage6e_hashes": invalidated_hashes,
        "repair": {
            "fault": "acquisition writer incorrectly gated by absent incoming reader",
            "only_dynamic_change": "generation-four founder write precedes reader-valid gate",
            "semantic_namespace_retained": pb.PhenotypeBridgeContract().namespace,
        },
        "proposal_grid": {
            "strict": {
                "features": ("endpoint", "transition", "autocorrelation", "temporal-mix"),
                "clearance": (1, 2, 4),
                "windows": (2, 4, 8, 16),
                "frontends": 2,
                "maximum": 96,
            },
            "somatic": {
                "architectures": (
                    "multi-timescale-ema",
                    "transition-eligibility",
                    "local-reservoir",
                ),
                "channels": (2, 4, 8),
                "acquisition_windows": (4, 8),
                "writer_inputs": ("visible", "somatic"),
                "maximum": 36,
            },
        },
        "limits": {
            "workers": 4,
            "max_hours": max_hours,
            "exploration_stop_hours": max_hours * 5.5 / 8.0,
        },
        "implementation_hashes": {
            "motif_writeback_ladder.py": ar._sha256(Path(__file__)),
            "motif_phenotype_bridge.py": ar._sha256(Path(pb.__file__)),
            "protocol": ar._sha256(PROTOCOL_PATH),
        },
        "cleanroom": {
            "excluded_code": ("Wagner implementation", "Fable implementation"),
            "excluded_code_read_import_hash_execute": True,
        },
    }
    digest = _canonical_digest(design)
    design["design_digest"] = digest
    existing = output / "DESIGN.json"
    if existing.exists():
        if not resume:
            raise ValueError("Stage-6F output exists; use --resume")
        if _load_json(existing).get("design_digest") != digest:
            raise ValueError("Stage-6F design changed during resume")
    else:
        ar._atomic_json(existing, design)
        ar._atomic_json(
            output / "CLEANROOM_PROVENANCE.json",
            {"design_digest": digest, **design["cleanroom"]},
        )
    campaign_path = output / "CAMPAIGN.json"
    if campaign_path.exists():
        campaign = _load_json(campaign_path)
        if not math.isclose(float(campaign["max_hours"]), max_hours):
            raise ValueError("Stage-6F max-hours changed during resume")
    else:
        started = time.time()
        campaign = {
            "experiment": design["experiment"],
            "design_digest": digest,
            "started_unix": started,
            "max_hours": max_hours,
            "exploration_deadline_unix": started + max_hours * 5.5 / 8.0 * 3600.0,
            "hard_deadline_unix": started + max_hours * 3600.0,
            "final_audit_reserve_hours": max_hours * 2.5 / 8.0,
            "deadline_persists_across_resume": True,
        }
        ar._atomic_json(campaign_path, campaign)
    return contract, campaign, digest


def _status_writer(
    output: Path,
    profile_name: str,
    campaign: dict[str, Any],
    active_phase: list[str],
) -> Any:
    def write(state: str, current: str, **extra: Any) -> None:
        payload = {
            "state": state,
            "stage": "ca_motif_writeback_ladder_stage_6f",
            "profile": profile_name,
            "phase": active_phase[0],
            "current": current,
            "pid": os.getpid(),
            "workers_hard_max": 4,
            "started_unix": campaign["started_unix"],
            "updated_unix": time.time(),
            "elapsed_seconds": time.time() - float(campaign["started_unix"]),
            "deadline_remaining_seconds": max(
                0.0, float(campaign["hard_deadline_unix"]) - time.time()
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
        print(f"[{state}] stage6f-{active_phase[0]}:{current}{progress}", flush=True)

    return write


def _write_phase(
    output: Path,
    phase: str,
    digest: str,
    result: dict[str, Any],
    report: str,
    lay: str,
) -> None:
    root = output / phase
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment": "ca_motif_writeback_ladder_stage_6f",
        "design_digest": digest,
        "phase": phase,
        **result,
    }
    ar._atomic_json(root / "RESULTS.json", payload)
    ar._atomic_json(
        root / "STAGE_DECISION.json",
        {
            "experiment": payload["experiment"],
            "design_digest": digest,
            "phase": phase,
            "state": payload.get("state", "complete"),
            "stage_gate": bool(payload.get("stage_gate", False)),
            "decision": payload.get("decision", "advance" if payload.get("stage_gate") else "stop"),
            "next_phase": payload.get("next_phase"),
            "final_audit_trajectory_state": payload.get(
                "final_audit_trajectory_state", "untouched"
            ),
        },
    )
    ar._atomic_text(root / "REPORT.md", report.rstrip() + "\n")
    ar._atomic_text(root / "LAY_SUMMARY.md", lay.rstrip() + "\n")
    ar._atomic_text(root / "COMPLETE", "complete\n")


def _integrity_audit(stage6e_root: Path) -> dict[str, Any]:
    paths = sorted(
        (stage6e_root / "bridge-traces-stage6e/checkpoints").glob("*.json")
    )
    if not paths:
        raise FileNotFoundError("invalidated Stage-6E bridge checkpoints are missing")
    founder_flags: list[bool] = []
    identical: list[bool] = []
    examples: list[dict[str, Any]] = []
    for path in paths:
        row = _load_json(path)["result"]
        intact = row["conditions"]["intact"]
        sham = row["conditions"]["sham"]
        fresh = bool(intact["writer_history"]["4"]["fresh_carrier_written"])
        same = (
            intact["bridge_trace"]["5"]["patches_after_read"]
            == sham["bridge_trace"]["5"]["patches_after_read"]
        )
        founder_flags.append(fresh)
        identical.append(same)
        if len(examples) < 3:
            examples.append(
                {
                    "checkpoint": path.stem,
                    "fresh_carrier_written_generation4": fresh,
                    "generation5_intact_equals_sham": same,
                    "checkpoint_sha256": ar._sha256(path),
                }
            )
    gate = bool(founder_flags and not any(founder_flags) and all(identical))
    return {
        "state": "complete",
        "stage_gate": gate,
        "invalidated_verdict": "DIRECT_ECHO_ONLY",
        "replacement_status": "INVALID_ACQUISITION_GATE",
        "checkpoint_count": len(paths),
        "generation4_founder_write_true_count": int(sum(founder_flags)),
        "generation5_intact_sham_identical_count": int(sum(identical)),
        "examples": examples,
        "final_audit_trajectory_state": "untouched",
    }


def _trace_rows(replay_root: Path) -> list[dict[str, Any]]:
    paths = sorted((replay_root / "bridge-traces-stage6e/checkpoints").glob("*.json"))
    rows = [_load_json(path)["result"] for path in paths]
    if not rows:
        raise FileNotFoundError("corrected replay bridge traces are missing")
    return rows


def _unpack_state(value: str, shape: Sequence[int]) -> np.ndarray:
    count = int(shape[0]) * int(shape[1])
    bits = np.unpackbits(np.frombuffer(bytes.fromhex(value), dtype=np.uint8))[:count]
    return bits.reshape(int(shape[0]), int(shape[1])).astype(np.float32) * 2.0 - 1.0


def _crop(state: np.ndarray, center: Sequence[int], radius: int) -> np.ndarray:
    extent = state.shape[0]
    offsets = np.arange(-radius, radius + 1, dtype=np.int64)
    ys = (int(center[0]) + offsets) % extent
    xs = (int(center[1]) + offsets) % extent
    return state[np.ix_(ys, xs)]


def _ridge_predict(
    train_x: np.ndarray,
    train_y: np.ndarray,
    test_x: np.ndarray,
    ridge: float = 1.0,
) -> np.ndarray:
    mean = np.mean(train_x, axis=0)
    scale = np.std(train_x, axis=0)
    scale[scale < 1e-6] = 1.0
    x = (train_x - mean) / scale
    z = (test_x - mean) / scale
    x = np.concatenate((x, np.ones((len(x), 1), dtype=np.float64)), axis=1)
    z = np.concatenate((z, np.ones((len(z), 1), dtype=np.float64)), axis=1)
    if x.shape[1] <= x.shape[0]:
        weights = np.linalg.solve(
            x.T @ x + ridge * np.eye(x.shape[1], dtype=np.float64), x.T @ train_y
        )
    else:
        weights = x.T @ np.linalg.solve(
            x @ x.T + ridge * np.eye(x.shape[0], dtype=np.float64), train_y
        )
    return z @ weights


def _observability_entries(
    rows: Sequence[dict[str, Any]],
    source: int,
    start: int,
    length: int,
    radius: str,
) -> dict[str, list[tuple[str, np.ndarray, np.ndarray]]]:
    result: dict[str, list[tuple[str, np.ndarray, np.ndarray]]] = {
        "intact": [],
        "sham": [],
    }
    sweeps = [str(value) for value in range(start, start + length)]
    source_id = f"source-q4-d{source:02d}"
    for row in rows:
        if row["candidate_id"] != source_id:
            continue
        for condition in ("intact", "sham"):
            trace = row["conditions"][condition]["bridge_trace"]["5"]
            if any(key not in trace.get("patches_all", {}) for key in sweeps):
                continue
            targets = np.asarray(trace["environment"], dtype=np.float64).reshape(-1, 16)
            centers = trace["centers"]
            shape = trace["state_shape"]
            for sample in range(len(targets)):
                pieces: list[np.ndarray] = []
                for sweep in sweeps:
                    if radius == "patch":
                        value = np.asarray(trace["patches_all"][sweep][sample], dtype=np.float64)
                    else:
                        value = _unpack_state(trace["full_state_hex"][sweep][sample], shape)
                        if radius != "full":
                            value = _crop(value, centers[sample], int(radius))
                    pieces.append(value.reshape(-1))
                result[condition].append(
                    (str(row["pair_id"]), np.concatenate(pieces), targets[sample])
                )
    return result


def _oracle_summary(
    entries: dict[str, list[tuple[str, np.ndarray, np.ndarray]]],
    contract: WritebackLadderContract,
    seed_key: str,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    groups = sorted({row[0] for row in entries["intact"]})
    intact_by_group: dict[str, list[float]] = {group: [] for group in groups}
    sham_by_group: dict[str, list[float]] = {group: [] for group in groups}
    fold_mode = "leave-one-pair-out"
    if len(groups) == 1:
        # Smoke has one exposed bridge pair.  Exercise the complete numerical
        # path with leave-one-sample-out folds, but label it explicitly as a
        # software-only fallback; reference inference always has pair folds.
        fold_mode = "smoke-leave-one-sample-out"
        group = groups[0]
        intact_rows = entries["intact"]
        sham_rows = entries["sham"]
        for held_index in range(len(intact_rows)):
            train = [row for index, row in enumerate(intact_rows) if index != held_index]
            if not train:
                continue
            train_x = np.stack([row[1] for row in train])
            train_y = np.stack([row[2] for row in train])
            for rows, destination in (
                (intact_rows, intact_by_group),
                (sham_rows, sham_by_group),
            ):
                test = rows[held_index : held_index + 1]
                prediction = _ridge_predict(
                    train_x, train_y, np.stack([row[1] for row in test])
                )
                target = np.stack([row[2] for row in test])
                accuracy = float(
                    np.mean(np.where(prediction >= 0.0, 1.0, -1.0) == target)
                )
                destination[group].append(accuracy)
    else:
        for held in groups:
            train = [row for row in entries["intact"] if row[0] != held]
            if not train:
                continue
            train_x = np.stack([row[1] for row in train])
            train_y = np.stack([row[2] for row in train])
            for condition, destination in (
                ("intact", intact_by_group),
                ("sham", sham_by_group),
            ):
                test = [row for row in entries[condition] if row[0] == held]
                if not test:
                    continue
                prediction = _ridge_predict(
                    train_x, train_y, np.stack([row[1] for row in test])
                )
                target = np.stack([row[2] for row in test])
                accuracy = float(
                    np.mean(np.where(prediction >= 0.0, 1.0, -1.0) == target)
                )
                destination[held].append(accuracy)
    intact = [float(np.mean(intact_by_group[group])) for group in groups]
    sham = [float(np.mean(sham_by_group[group])) for group in groups]
    effects = [left - right for left, right in zip(intact, sham)]
    resamples = max(100, min(bootstrap_resamples, 1_000))
    return {
        "pair_count": len(groups),
        "fold_mode": fold_mode,
        "intact_accuracy": ar._bootstrap(
            intact,
            resamples,
            ar._hash_seed(contract.namespace, seed_key, "intact"),
            contract.strict_alpha,
        ),
        "sham_accuracy": ar._bootstrap(
            sham,
            resamples,
            ar._hash_seed(contract.namespace, seed_key, "sham"),
            contract.strict_alpha,
        ),
        "intact_minus_sham": ar._bootstrap(
            effects,
            resamples,
            ar._hash_seed(contract.namespace, seed_key, "effect"),
            contract.strict_alpha,
        ),
    }


def _lower(summary: dict[str, Any]) -> float:
    value = summary.get("ci", [None, None])[0]
    return float(summary.get("mean") or 0.0) if value is None else float(value)


def _run_observability(
    rows: Sequence[dict[str, Any]],
    profile: pb.PhenotypeBridgeProfile,
    contract: WritebackLadderContract,
    status: Any,
    deadline: float,
) -> dict[str, Any]:
    configurations: list[dict[str, Any]] = []
    registered: list[tuple[int, str, int, int, str]] = []
    for source in (40, 48):
        for length in (4, 8):
            registered.append((source, "supported", source - length + 1, length, "patch"))
        for clearance in (1, 2, 4):
            for length in (1, 2, 4, 8, 16):
                start = source + clearance
                if start + length - 1 > 64:
                    continue
                for radius in ("patch", "2", "4", "6"):
                    registered.append((source, "carrier-free", start, length, radius))
                if clearance in (1, 4) and length in (1, 4, 8):
                    registered.append((source, "carrier-free", start, length, "full"))
    for index, (source, period, start, length, radius) in enumerate(registered):
        if time.time() >= deadline:
            break
        entries = _observability_entries(rows, source, start, length, radius)
        summary = _oracle_summary(
            entries,
            contract,
            f"oracle-{source}-{period}-{start}-{length}-{radius}",
            profile.bootstrap_resamples,
        )
        configurations.append(
            {
                "source_read_sweeps": source,
                "period": period,
                "start_sweep": start,
                "length": length,
                "radius": radius,
                **summary,
            }
        )
        status(
            "running",
            "observability-grid",
            completed=index + 1,
            total=len(registered),
        )
    bounded = [
        row
        for row in configurations
        if row["period"] == "carrier-free" and row["radius"] != "full"
    ]
    local = [row for row in bounded if row["radius"] == "patch"]
    full = [
        row
        for row in configurations
        if row["period"] == "carrier-free" and row["radius"] == "full"
    ]
    supported = [row for row in configurations if row["period"] == "supported"]
    ranking = lambda row: (
        _lower(row["intact_minus_sham"]),
        _lower(row["intact_accuracy"]),
    )
    best_local = max(local, key=ranking) if local else None
    best_bounded = max(bounded, key=ranking) if bounded else None
    best_full = max(full, key=ranking) if full else None
    best_supported = max(supported, key=ranking) if supported else None
    strict_eligible = bool(
        best_local
        and _lower(best_local["intact_accuracy"])
        >= contract.observability_accuracy_minimum
        and _lower(best_local["intact_minus_sham"])
        > contract.observability_effect_minimum
    )
    complete = len(configurations) == len(registered)
    return {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(best_supported),
        "registered_configurations": len(registered),
        "completed_configurations": len(configurations),
        "strict_branch_eligible": strict_eligible,
        "best_local_carrier_free": best_local,
        "best_bounded_carrier_free": best_bounded,
        "best_full_board_ceiling": best_full,
        "best_carrier_supported": best_supported,
        "configurations": configurations,
        "final_audit_trajectory_state": "untouched",
    }


def _writer_feature(stack: np.ndarray, feature: str) -> np.ndarray:
    if feature == "endpoint":
        return stack[-1]
    if feature == "transition":
        return stack[-1] - stack[0]
    if feature == "autocorrelation" and len(stack) > 1:
        return np.mean(stack[1:] * stack[:-1], axis=0)
    weights = np.linspace(-1.0, 1.0, len(stack), dtype=np.float32)
    return np.tensordot(weights / np.sum(np.abs(weights)), stack, axes=(0, 0))


def _strict_proxy(
    rows: Sequence[dict[str, Any]],
    source: int,
    clearance: int,
    length: int,
    feature: str,
    contract: WritebackLadderContract,
    profile: pb.PhenotypeBridgeProfile,
) -> dict[str, Any]:
    source_id = f"source-q4-d{source:02d}"
    start = source + clearance
    effects: list[float] = []
    intact_values: list[float] = []
    sham_values: list[float] = []
    for row in rows:
        if row["candidate_id"] != source_id:
            continue
        values: dict[str, float] = {}
        for condition in ("intact", "sham"):
            trace = row["conditions"][condition]["bridge_trace"]["5"]
            patches = trace["patches_all"]
            keys = [str(value) for value in range(start, start + length)]
            if any(key not in patches for key in keys):
                values[condition] = 0.0
                continue
            stack = np.stack([np.asarray(patches[key], dtype=np.float32) for key in keys])
            representation = _writer_feature(stack, feature)
            target = np.asarray(trace["environment"], dtype=np.float32)
            values[condition] = float(np.mean(representation * target))
        intact_values.append(values["intact"])
        sham_values.append(values["sham"])
        effects.append(values["intact"] - values["sham"])
    return {
        "intact_mean": float(np.mean(intact_values)) if intact_values else 0.0,
        "sham_mean": float(np.mean(sham_values)) if sham_values else 0.0,
        "effect": ar._bootstrap(
            effects,
            max(100, min(profile.bootstrap_resamples, 1_000)),
            ar._hash_seed(
                contract.namespace, "strict-proxy", source, clearance, length, feature
            ),
            contract.strict_alpha,
        ),
    }


def _proposal_grid(
    rows: Sequence[dict[str, Any]],
    frontends: Sequence[dict[str, Any]],
    observability: dict[str, Any],
    profile: pb.PhenotypeBridgeProfile,
    contract: WritebackLadderContract,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    strict: list[dict[str, Any]] = []
    for frontend in frontends:
        source = int(frontend["read_sweeps"])
        for feature in ("endpoint", "transition", "autocorrelation", "temporal-mix"):
            for clearance in (1, 2, 4):
                for length in (2, 4, 8, 16):
                    if source + clearance + length - 1 > 64:
                        continue
                    proxy = _strict_proxy(
                        rows, source, clearance, length, feature, contract, profile
                    )
                    frozen_frontend = dict(frontend)
                    frozen_frontend.update(
                        {
                            "frontend_id": (
                                f"stage6f-{frontend['encoder_id']}-d{source:02d}-"
                                f"c{clearance:02d}-t{length:02d}-{feature}"
                            ),
                            "clearance_updates": clearance,
                            "trace_sweeps": length,
                        }
                    )
                    strict.append(
                        {
                            "candidate_id": f"stage6f-strict-{len(strict):03d}",
                            "claim_tier": "strict",
                            "writer_source": "visible",
                            "writer_input_contract": "visible-only",
                            "writer_feature": feature,
                            "somatic_architecture": "none",
                            "somatic_channels": 1,
                            "somatic_retention": 0.0,
                            "somatic_bias": 0.0,
                            "frontend": frozen_frontend,
                            "proxy": proxy,
                        }
                    )
    best_supported = observability.get("best_carrier_supported") or {}
    support_effect = best_supported.get("intact_minus_sham", {"mean": 0.0, "ci": [0.0, 0.0]})
    preferred = max(
        frontends,
        key=lambda row: (
            -int(row["bits"]),
            -int(row["trace_sweeps"]),
            str(row["frontend_id"]),
        ),
    )
    somatic: list[dict[str, Any]] = []
    for writer_source in ("visible", "somatic"):
        for architecture in (
            "multi-timescale-ema",
            "transition-eligibility",
            "local-reservoir",
        ):
            for channels in (2, 4, 8):
                for acquisition_window in (4, 8):
                    frontend = dict(preferred)
                    frontend.update(
                        {
                            "frontend_id": (
                                f"stage6f-{architecture}-c{channels:02d}-"
                                f"a{acquisition_window:02d}-{writer_source}"
                            ),
                            "clearance_updates": 1,
                            "trace_sweeps": min(8, 64 - int(frontend["read_sweeps"]) - 8),
                        }
                    )
                    somatic.append(
                        {
                            "candidate_id": f"stage6f-somatic-{len(somatic):03d}",
                            "claim_tier": "broad",
                            "writer_source": writer_source,
                            "writer_input_contract": (
                                "field-readable" if writer_source == "somatic" else "visible-only"
                            ),
                            "writer_feature": "temporal-mix" if writer_source == "somatic" else "mean",
                            "somatic_architecture": architecture,
                            "somatic_channels": channels,
                            "somatic_retention": 0.90 if acquisition_window == 4 else 0.95,
                            "somatic_bias": 0.60 if channels <= 4 else 0.80,
                            "somatic_readout": "slow" if architecture == "multi-timescale-ema" else "mean",
                            "somatic_acquisition_window": acquisition_window,
                            "somatic_support_sweeps": 8,
                            "frontend": frontend,
                            "proxy": {
                                "observability_effect": support_effect,
                                "complexity_penalty": channels / 10_000.0,
                            },
                        }
                    )
    proposals = [*strict, *somatic]
    selected: list[dict[str, Any]] = []
    if observability.get("strict_branch_eligible"):
        ranked = sorted(
            strict,
            key=lambda row: (
                -_lower(row["proxy"]["effect"]),
                -float(row["proxy"]["effect"].get("mean") or 0.0),
                int(row["frontend"]["bits"]),
                int(row["frontend"]["trace_sweeps"]),
                row["candidate_id"],
            ),
        )
        used_features: set[str] = set()
        for row in ranked:
            if row["writer_feature"] in used_features:
                continue
            selected.append(row)
            used_features.add(row["writer_feature"])
            if len(used_features) == 4:
                break
    for writer_source in ("visible", "somatic"):
        pool = [row for row in somatic if row["writer_source"] == writer_source]
        pool.sort(
            key=lambda row: (
                int(row["somatic_channels"]),
                -int(row["somatic_acquisition_window"]),
                str(row["somatic_architecture"]),
            )
        )
        used_architectures: set[str] = set()
        chosen = 0
        for row in pool:
            architecture = str(row["somatic_architecture"])
            if architecture in used_architectures and chosen < 3:
                continue
            selected.append(row)
            used_architectures.add(architecture)
            chosen += 1
            if chosen == 4:
                break
    if len(proposals) > 132 or len(selected) > contract.maximum_promotable_writers:
        raise AssertionError("Stage-6F proposal or sealed-candidate cap changed")
    return proposals, selected


def _prepare_stage6f_subcampaign(
    stage_root: Path,
    profile_name: str,
    specs: Sequence[dict[str, Any]],
    digest: str,
    roots: dict[str, Path],
    *,
    auto_final_audit: bool,
) -> tuple[
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    pb.PhenotypeBridgeProfile,
    WritebackLadderContract,
    ar.MotifContract,
    list[dict[str, Any]],
]:
    frozen, cohorts, profile, _, writer_contract, templates, parent_digest = pb._prepare_stage6e(
        stage_root,
        profile_name,
        auto_final_audit=auto_final_audit,
        **roots,
    )
    ar._atomic_json(
        stage_root / "PARENT_PREPARATION.json",
        {"parent_design_digest": parent_digest, "campaign_design_digest": digest},
    )
    selection_digest = _canonical_digest(list(specs))
    ar._atomic_json(
        stage_root / "WRITEBACK_CANDIDATES.json",
        {
            "design_digest": digest,
            "selection_digest": selection_digest,
            "selection_frozen_before_screen": True,
            "promotable_count": len(specs),
            "candidates": list(specs),
        },
    )
    bridge_result = {
        "experiment": "ca_motif_phenotype_bridge_stage_6e",
        "design_digest": digest,
        "phase": "bridge",
        "state": "complete",
        "stage_gate": True,
        "selected_frontends": [specs[0]["frontend"]],
        "selection_digest": selection_digest,
        "adaptive_stage6f_registry": True,
        "final_audit_trajectory_state": "untouched",
    }
    bridge_root = stage_root / "bridge"
    bridge_root.mkdir(parents=True, exist_ok=True)
    ar._atomic_json(bridge_root / "RESULTS.json", bridge_result)
    ar._atomic_text(bridge_root / "COMPLETE", "complete\n")
    return (
        frozen,
        cohorts,
        profile,
        WritebackLadderContract(),
        writer_contract,
        templates,
    )


def _run_stage6f_development(
    output: Path,
    profile_name: str,
    specs: Sequence[dict[str, Any]],
    digest: str,
    roots: dict[str, Path],
    campaign: dict[str, Any],
    status: Any,
    *,
    workers: int,
    resume: bool,
    auto_final_audit: bool,
) -> dict[str, Any]:
    stage_root = output / "stage6f"
    frozen, cohorts, profile, contract, writer_contract, templates = _prepare_stage6f_subcampaign(
        stage_root,
        profile_name,
        specs,
        digest,
        roots,
        auto_final_audit=auto_final_audit,
    )
    common = dict(
        output=stage_root,
        frozen=frozen,
        cohorts=cohorts,
        profile=profile,
        contract=contract,
        writer_contract=writer_contract,
        templates=templates,
        design_digest=digest,
        stage6br_root=roots["stage6br_root"],
        workers=workers,
        resume=resume,
        scientific=profile_name == "reference",
        status=status,
    )
    screen_conditions = tuple(
        dict.fromkeys(
            (*pb.SCREEN_CONDITIONS, "trace_write_disabled", "trace_read_disabled")
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
            )
        )
    )
    audit_conditions = tuple(
        dict.fromkeys(
            (
                *pb.AUDIT_CONDITIONS,
                "trace_ablation",
                "trace_same_rescue",
                "trace_opposite_rescue",
                "writer_temporal_reverse",
            )
        )
    )
    screen = pb._run_screen(
        **common,
        deadline=float(campaign["exploration_deadline_unix"]),
        conditions=screen_conditions,
    )
    qualify = pb._run_qualification(
        **common,
        deadline=float(campaign["exploration_deadline_unix"]),
        conditions=qualification_conditions,
    )
    endurance = pb._run_endurance(
        **common,
        deadline=float(campaign["exploration_deadline_unix"]),
    )
    adjudicate = pb._run_adjudication(
        **common,
        deadline=float(campaign["hard_deadline_unix"]),
        auto_final_audit=auto_final_audit,
        conditions=audit_conditions,
    )
    return {
        "screen": screen,
        "qualify": qualify,
        "endurance": endurance,
        "adjudicate": adjudicate,
    }


def _campaign_result(
    output: Path,
    digest: str,
    profile_name: str,
    replay: dict[str, Any],
    observability: dict[str, Any] | None,
    development: dict[str, Any] | None,
) -> dict[str, Any]:
    if replay.get("selected_candidate_ids"):
        verdict = str(replay.get("verdict"))
        route = "corrected-stage6e"
        selected = list(replay.get("selected_candidate_ids", []))
        qualified = list(replay.get("qualified_candidate_ids", []))
        enduring = list(replay.get("enduring_candidate_ids", []))
        confirmed = list(replay.get("confirmed_candidate_ids", []))
        reserve = str(replay.get("final_audit_trajectory_state", "untouched"))
    elif development is None:
        verdict = (
            "INCONCLUSIVE_RESOURCE_LIMIT"
            if replay.get("verdict") == "INCONCLUSIVE_RESOURCE_LIMIT"
            else "NO_STAGE6F_ROUTE"
        )
        route = "corrected-stage6e"
        selected = qualified = enduring = confirmed = []
        reserve = "untouched"
    else:
        adjudicate = development["adjudicate"]
        tiers = set(adjudicate.get("confirmed_tiers", []))
        if "strict" in tiers:
            verdict = "STRICT_FORM_MEDIATED_PH_CONFIRMED"
        elif "broad" in tiers:
            verdict = "SOMATICALLY_MEDIATED_PH_CONFIRMED"
        elif development["endurance"].get("state") == "budget_truncated":
            verdict = "INCONCLUSIVE_RESOURCE_LIMIT"
        elif development["qualify"].get("qualified_candidate_ids"):
            verdict = "ONE_GENERATION_CLOSURE_ONLY"
        elif development["screen"].get("selected_candidate_ids"):
            verdict = "OBSERVABLE_NOT_ENDURING"
        elif observability and not observability.get("strict_branch_eligible"):
            verdict = "POST_ERASURE_INFORMATION_LOST"
        else:
            verdict = "OBSERVABLE_NOT_WRITABLE"
        route = "stage6f-writeback-ladder"
        selected = list(development["screen"].get("selected_candidate_ids", []))
        qualified = list(development["qualify"].get("qualified_candidate_ids", []))
        enduring = list(development["endurance"].get("enduring_candidate_ids", []))
        confirmed = list(adjudicate.get("confirmed_candidate_ids", []))
        reserve = str(adjudicate.get("final_audit_trajectory_state", "untouched"))
    result = {
        "experiment": "ca_motif_writeback_ladder_stage_6f",
        "design_digest": digest,
        "state": "complete",
        "profile_name": profile_name,
        "verdict": verdict,
        "adaptive_route": route,
        "invalidated_stage6e_verdict": "DIRECT_ECHO_ONLY",
        "invalidated_stage6e_status": "INVALID_ACQUISITION_GATE",
        "selected_candidate_ids": selected,
        "qualified_candidate_ids": qualified,
        "enduring_candidate_ids": enduring,
        "confirmed_candidate_ids": confirmed,
        "stage_gate": bool(confirmed),
        "final_audit_opened": reserve == "opened",
        "final_audit_trajectory_state": reserve,
    }
    ar._atomic_json(output / "RESULTS.json", result)
    ar._atomic_json(
        output / "STAGE_DECISION.json",
        {
            "experiment": result["experiment"],
            "design_digest": digest,
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
        "# Stage 6E-R/6F repair and causal write-back ladder\n\n"
        f"Verdict: **{verdict}**.\n\n"
        "The original Stage-6E verdict was invalidated because its founder carrier was never written.\n\n"
        f"Adaptive route: {route}.\n\n"
        f"Selected: {selected}\n\nQualified: {qualified}\n\n"
        f"Enduring: {enduring}\n\nConfirmed: {confirmed}\n",
    )
    if verdict in (
        "STRICT_FORM_MEDIATED_PH_CONFIRMED",
        "SOMATICALLY_MEDIATED_PH_CONFIRMED",
    ):
        lay = "After repairing the missing founder note, a daughter repeatedly rebuilt and renewed history-specific memory under the full causal controls."
    elif verdict == "POST_ERASURE_INFORMATION_LOST":
        lay = "The repaired parent could write the first note, but once that note stopped guiding the cells, too little local history remained to copy into a fresh note."
    elif verdict == "OBSERVABLE_NOT_WRITABLE":
        lay = "Some history remained visible after erasure, but none of the bounded daughter writers could turn it into renewable inherited memory."
    elif verdict == "INCONCLUSIVE_RESOURCE_LIMIT":
        lay = "The corrected campaign exhausted its registered compute window before the decisive tests finished."
    else:
        lay = "The founder-write bug was repaired and the valid campaign narrowed where the form-to-memory loop still breaks."
    ar._atomic_text(output / "LAY_SUMMARY.md", "# Lay summary\n\n" + lay + "\n")
    ar._atomic_json(
        output / "MANIFEST.json",
        {
            "experiment": result["experiment"],
            "design_digest": digest,
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "result_sha256": ar._sha256(output / "RESULTS.json"),
            "protocol_sha256": ar._sha256(PROTOCOL_PATH),
            "implementation_sha256": ar._sha256(Path(__file__)),
            "repaired_stage6e_sha256": ar._sha256(Path(pb.__file__)),
        },
    )
    ar._atomic_text(output / "COMPLETE", "complete\n")
    return result


def run_motif_writeback_ladder(
    output: Path,
    *,
    stage6e_root: Path = DEFAULT_STAGE6E_ROOT,
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
    """Run the repair-first, adaptively gated Stage-6F campaign."""

    ar.require_pinned_numpy()
    if profile_name not in pb.PUBLIC_PROFILES:
        raise ValueError(f"unknown Stage-6F profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6F workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6F max-hours must be in (0, 8]")
    if profile_name == "reference" and not auto_final_audit:
        raise ValueError("reference Stage-6F requires automatic final-audit authorization")
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
    active_phase = ["prepare"]
    campaign: dict[str, Any] | None = None
    status: Any = None
    try:
        contract, campaign, digest = _prepare_top_level(
            output,
            profile_name,
            stage6e_root.resolve(),
            max_hours,
            resume=resume,
        )
        status = _status_writer(output, profile_name, campaign, active_phase)
        status("running", "frozen-design-verified")

        active_phase[0] = "integrity"
        if resume and (output / "integrity/COMPLETE").exists():
            integrity = _load_json(output / "integrity/RESULTS.json")
        else:
            integrity = _integrity_audit(stage6e_root.resolve())
            ar._atomic_json(output / "INVALIDATION.json", integrity)
            _write_phase(
                output,
                "integrity",
                digest,
                integrity | {"next_phase": "replay"},
                "# Stage 6E integrity audit\n\nThe registered Stage-6E founder write was suppressed in every saved bridge trace; its verdict is invalid.",
                "# Lay summary\n\nThe previous experiment accidentally prevented the very first inherited note from being written.",
            )
        if not integrity.get("stage_gate"):
            raise ValueError("Stage-6E invalidation evidence did not reproduce")

        active_phase[0] = "replay"
        replay_root = output / "replay"
        status(
            "running",
            "corrected-stage6e",
            child_status_path=str(replay_root / "STATUS.json"),
        )
        if resume and (replay_root / "COMPLETE").exists():
            replay = _load_json(replay_root / "RESULTS.json")
        else:
            child_campaign_path = replay_root / "CAMPAIGN.json"
            if child_campaign_path.exists():
                child_max_hours = float(_load_json(child_campaign_path)["max_hours"])
            else:
                child_max_hours = min(
                    8.0,
                    max(
                        0.01,
                        (float(campaign["hard_deadline_unix"]) - time.time()) / 3600.0,
                    ),
                )
            replay = pb.run_motif_phenotype_bridge(
                replay_root,
                phase="all",
                profile_name=profile_name,
                workers=workers,
                max_hours=child_max_hours,
                resume=resume and (replay_root / "CAMPAIGN.json").exists(),
                auto_final_audit=auto_final_audit,
                **roots,
            )
        replay_selected = list(replay.get("selected_candidate_ids", []))
        _write_phase(
            output,
            "replay",
            digest,
            {
                "state": "complete",
                "stage_gate": True,
                "corrected_result": replay,
                "adaptive_route": (
                    "corrected-stage6e-confirmation" if replay_selected else "stage6f-observability"
                ),
                "next_phase": None if replay_selected else "observability",
                "final_audit_trajectory_state": replay.get(
                    "final_audit_trajectory_state", "untouched"
                ),
            },
            "# Corrected Stage 6E-R replay\n\nThe acquisition writer was repaired and the registered experiment was replayed with unchanged semantic random streams.",
            "# Lay summary\n\nThe daughter was finally allowed to write the first note, so subsequent failures or successes are now meaningful.",
        )

        observability: dict[str, Any] | None = None
        development: dict[str, Any] | None = None
        exercise_stage6f = not replay_selected or profile_name == "smoke"
        if exercise_stage6f and replay.get("verdict") != "INCONCLUSIVE_RESOURCE_LIMIT":
            active_phase[0] = "observability"
            rows = _trace_rows(replay_root)
            observability_path = output / "observability/RESULTS.json"
            if resume and (output / "observability/COMPLETE").exists():
                observability = _load_json(observability_path)
            else:
                observability = _run_observability(
                    rows,
                    pb.PHENOTYPE_BRIDGE_PROFILES[profile_name],
                    contract,
                    status,
                    float(campaign["exploration_deadline_unix"]),
                )
                _write_phase(
                    output,
                    "observability",
                    digest,
                    observability | {"next_phase": "discover"},
                    "# Stage 6F observability ladder\n\nCarrier-free local, bounded-neighbourhood, and full-board diagnostic ceilings were measured with pair-blocked folds.",
                    "# Lay summary\n\nThis asks whether any trace of the old note remains in the daughter's behaviour after the note is destroyed.",
                )
            if time.time() < float(campaign["exploration_deadline_unix"]):
                active_phase[0] = "discover"
                registry_path = output / "discover/RESULTS.json"
                if resume and (output / "discover/COMPLETE").exists():
                    discovery = _load_json(registry_path)
                    selected_specs = list(discovery["selected_candidates"])
                else:
                    frontends = _load_json(replay_root / "SEALED_FRONTENDS.json")["frontends"]
                    proposals, selected_specs = _proposal_grid(
                        rows,
                        frontends,
                        observability,
                        pb.PHENOTYPE_BRIDGE_PROFILES[profile_name],
                        contract,
                    )
                    ar._atomic_json(
                        output / "PROPOSAL_GRID.json",
                        {
                            "design_digest": digest,
                            "registered_count": len(proposals),
                            "proposals": proposals,
                        },
                    )
                    discovery = {
                        "state": "complete",
                        "stage_gate": bool(selected_specs),
                        "proposal_count": len(proposals),
                        "selected_count": len(selected_specs),
                        "selection_frozen_before_screen": True,
                        "selection_digest": _canonical_digest(selected_specs),
                        "selected_candidates": selected_specs,
                        "next_phase": "screen" if selected_specs else None,
                        "final_audit_trajectory_state": "untouched",
                    }
                    ar._atomic_json(output / "SEALED_WRITERS.json", discovery)
                    _write_phase(
                        output,
                        "discover",
                        digest,
                        discovery,
                        "# Stage 6F writer discovery\n\nUp to twelve diverse writers were sealed from the 132-cell offline ladder before full-CA screening.",
                        "# Lay summary\n\nThe most promising ways of watching development and writing a fresh note were frozen before testing them on the next cohort.",
                    )
                if selected_specs:
                    active_phase[0] = "screen"
                    development = _run_stage6f_development(
                        output,
                        profile_name,
                        selected_specs,
                        digest,
                        roots,
                        campaign,
                        status,
                        workers=workers,
                        resume=resume,
                        auto_final_audit=auto_final_audit,
                    )
                    for phase in ("screen", "qualify", "endurance", "adjudicate"):
                        source = output / "stage6f" / phase / "RESULTS.json"
                        if source.exists():
                            summary = _load_json(source)
                            _write_phase(
                                output,
                                phase,
                                digest,
                                {
                                    "state": summary.get("state", "complete"),
                                    "stage_gate": bool(summary.get("stage_gate")),
                                    "subcampaign_result": summary,
                                    "next_phase": None,
                                    "final_audit_trajectory_state": summary.get(
                                        "final_audit_trajectory_state", "untouched"
                                    ),
                                },
                                f"# Stage 6F {phase}\n\nSee the nested frozen subcampaign result for the complete causal statistics.",
                                "# Lay summary\n\nOnly candidates that passed the preceding causal gate reached this stage.",
                            )

        active_phase[0] = "complete"
        result = _campaign_result(
            output, digest, profile_name, replay, observability, development
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
            {"error": repr(error), "phase": active_phase[0], "updated_unix": time.time()},
        )
        raise


__all__ = (
    "DEFAULT_STAGE6E_ROOT",
    "PHASES",
    "WritebackLadderContract",
    "run_motif_writeback_ladder",
)
