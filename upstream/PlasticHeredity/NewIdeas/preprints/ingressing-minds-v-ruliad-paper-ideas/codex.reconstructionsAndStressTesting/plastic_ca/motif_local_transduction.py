"""Stage-6G local transduction and hereditary closure.

Stage 6F established that carrier-free history is locally decodable but that
the registered writers cannot renew it.  This clean-room follow-up separates
the physical carrier round trip from the missing local code translation.  It
tests label-free phase-locked writers alongside immutable translators fitted
only on the eight exposed bridge pairs.  Runtime fitting is a non-promotable
ceiling, never a positive claim.
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
from . import motif_writeback_ladder as wb


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_LOCAL_TRANSDUCTION_PROTOCOL.md"
DEFAULT_STAGE6F_ROOT = ROOT / "results/ca-motif-writeback-ladder-stage-6f"
PHASES = (
    "integrity",
    "decode",
    "decompose",
    "discover",
    "screen",
    "qualify",
    "endurance",
    "adjudicate",
)


@dataclass(frozen=True)
class LocalTransductionContract(wb.WritebackLadderContract):
    implementation_version: str = "ca-motif-local-transduction-v1"
    namespace: str = "plastic-ca-motif-local-transduction-v1"
    translator_accuracy_minimum: float = 0.70
    translator_effect_minimum: float = 0.15
    maximum_decoder_proposals: int = 144
    maximum_promotable_writers: int = 12
    exploration_stop_hours: float = 5.5
    max_hours: float = 8.0

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "translator_accuracy_minimum": self.translator_accuracy_minimum,
                "translator_effect_minimum": self.translator_effect_minimum,
                "maximum_decoder_proposals": self.maximum_decoder_proposals,
                "maximum_promotable_writers": self.maximum_promotable_writers,
                "adaptive_route": "stage6f-local-signal-to-frozen-transducer",
                "confirmatory_claims": (
                    "label-free-local-closure",
                    "rulebook-assisted-local-closure",
                ),
                "runtime_adaptation": "non-promotable control only",
                "translator_training_pairs": 8,
                "translator_frozen_before_screen": True,
            }
        )
        return payload


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _stage6f_integrity(stage6f_root: Path) -> dict[str, Any]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "COMPLETE",
        "observability/RESULTS.json",
        "replay/RESULTS.json",
        "replay/COHORTS.json",
        "replay/bridge-traces-stage6e/stage_summary.json",
    )
    missing = [stage6f_root / name for name in required if not (stage6f_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6F artifacts: {missing}")
    result = _load_json(stage6f_root / "RESULTS.json")
    status = _load_json(stage6f_root / "STATUS.json")
    observability = _load_json(stage6f_root / "observability/RESULTS.json")
    cohorts = _load_json(stage6f_root / "replay/COHORTS.json")
    if result.get("verdict") != "OBSERVABLE_NOT_WRITABLE":
        raise ValueError("Stage-6G requires the frozen OBSERVABLE_NOT_WRITABLE result")
    if status.get("state") != "complete" or result.get("state") != "complete":
        raise ValueError("Stage-6F is not complete")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6F protected reserve is not untouched")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("corrected replay reserve is not untouched")
    if not observability.get("strict_branch_eligible"):
        raise ValueError("Stage-6F did not retain the registered local signal")
    trace_paths = sorted(
        (stage6f_root / "replay/bridge-traces-stage6e/checkpoints").glob("*.json")
    )
    if len(trace_paths) != 32:
        raise ValueError("Stage-6G requires all 32 corrected bridge checkpoints")
    trace_inventory = [
        {"name": path.name, "sha256": ar._sha256(path), "bytes": path.stat().st_size}
        for path in trace_paths
    ]
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "required_hashes": {name: ar._sha256(stage6f_root / name) for name in required},
        "trace_checkpoint_count": len(trace_paths),
        "trace_inventory_digest": _digest(trace_inventory),
        "trace_inventory": trace_inventory,
        "best_local_carrier_free": observability["best_local_carrier_free"],
        "best_bounded_carrier_free": observability["best_bounded_carrier_free"],
        "final_audit_trajectory_state": "untouched",
    }


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6f_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[LocalTransductionContract, dict[str, Any], str, dict[str, Any]]:
    contract = LocalTransductionContract()
    integrity = _stage6f_integrity(stage6f_root)
    design = {
        "experiment": "ca_motif_local_transduction_stage_6g",
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(pb.PHENOTYPE_BRIDGE_PROFILES[profile_name]),
        "stage6f_root": str(stage6f_root.resolve()),
        "stage6f_required_hashes": integrity["required_hashes"],
        "trace_inventory_digest": integrity["trace_inventory_digest"],
        "decoder_grid": {
            "sources": (40, 48),
            "radii": ("patch", "2"),
            "windows": (1, 2),
            "targets": ("visible-bits", "walsh-coefficients"),
            "ridge": (0.1, 1.0, 10.0),
            "compression": ("full", "rank8", "sparse8-q8"),
            "registered_count": 144,
        },
        "candidate_allocation": {
            "label_free": 4,
            "frozen_visible_translator": 4,
            "frozen_translator_somatic": 4,
            "total": 12,
        },
        "training_contract": {
            "selection": "leave-one-pair-out on eight bridge pairs",
            "final_fit": "all eight bridge pairs after family selection",
            "screen_retraining": False,
            "runtime_labels": False,
            "runtime_carrier_values": False,
            "per_daughter_adaptation_promotable": False,
        },
        "limits": {
            "workers": 4,
            "max_hours": max_hours,
            "exploration_stop_hours": max_hours * 5.5 / 8.0,
        },
        "implementation_hashes": {
            "motif_local_transduction.py": ar._sha256(Path(__file__)),
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
            raise ValueError("Stage-6G output exists; use --resume")
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6G design changed during resume")
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
            raise ValueError("Stage-6G max-hours changed during resume")
    else:
        started = time.time()
        campaign = {
            "experiment": design["experiment"],
            "design_digest": design_digest,
            "started_unix": started,
            "max_hours": max_hours,
            "exploration_deadline_unix": started + max_hours * 5.5 / 8.0 * 3600.0,
            "hard_deadline_unix": started + max_hours * 3600.0,
            "final_audit_reserve_hours": max_hours * 2.5 / 8.0,
            "deadline_persists_across_resume": True,
        }
        ar._atomic_json(campaign_path, campaign)
    return contract, campaign, design_digest, integrity


def _status_writer(
    output: Path,
    profile_name: str,
    campaign: dict[str, Any],
    phase: list[str],
) -> Any:
    def write(state: str, current: str, **extra: Any) -> None:
        now = time.time()
        payload = {
            "state": state,
            "stage": "ca_motif_local_transduction_stage_6g",
            "profile": profile_name,
            "phase": phase[0],
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
        print(f"[{state}] stage6g-{phase[0]}:{current}{progress}", flush=True)

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
        "experiment": "ca_motif_local_transduction_stage_6g",
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


def _extract_dataset(
    rows: Sequence[dict[str, Any]],
    source: int,
    radius: str,
    length: int,
    condition: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    groups: list[str] = []
    start = source + 1
    source_id = f"source-q4-d{source:02d}"
    for row in rows:
        if row["candidate_id"] != source_id:
            continue
        trace = row["conditions"][condition]["bridge_trace"]["5"]
        sweeps = [str(value) for value in range(start, start + length)]
        if any(key not in trace["patches_all"] for key in sweeps):
            continue
        environment = np.asarray(trace["environment"], dtype=np.float32).reshape(-1, 16)
        per_sweep: list[np.ndarray] = []
        for key in sweeps:
            if radius == "patch":
                values = np.asarray(trace["patches_all"][key], dtype=np.float32)
            else:
                shape = trace["state_shape"]
                values = np.stack(
                    [
                        wb._crop(
                            wb._unpack_state(value, shape),
                            trace["centers"][sample],
                            int(radius),
                        )
                        for sample, value in enumerate(trace["full_state_hex"][key])
                    ]
                ).astype(np.float32)
            per_sweep.append(values)
        stacked = np.stack(per_sweep, axis=1).reshape(len(environment), -1)
        features.extend(stacked)
        targets.extend(environment)
        groups.extend([str(row["pair_id"])] * len(environment))
    if not features:
        raise ValueError(f"no Stage-6G dataset for {source=} {radius=} {length=}")
    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
        np.asarray(groups, dtype=str),
    )


def _compress_weights(weights: np.ndarray, mode: str) -> np.ndarray:
    values = np.asarray(weights, dtype=np.float64)
    if mode == "full":
        return values
    if mode == "rank8":
        left, singular, right = np.linalg.svd(values, full_matrices=False)
        keep = min(8, len(singular))
        return (left[:, :keep] * singular[:keep]) @ right[:keep]
    if mode == "sparse8-q8":
        result = np.zeros_like(values)
        keep = min(8, values.shape[0])
        for column in range(values.shape[1]):
            indices = np.argsort(np.abs(values[:, column]))[-keep:]
            selected = values[indices, column]
            scale = max(float(np.max(np.abs(selected))), 1e-9) / 127.0
            result[indices, column] = np.rint(selected / scale) * scale
        return result
    raise ValueError(f"unknown translator compression {mode!r}")


def _fit_linear(
    features: np.ndarray,
    targets: np.ndarray,
    ridge: float,
    compression: str,
) -> dict[str, np.ndarray]:
    mean = np.mean(features, axis=0, dtype=np.float64)
    scale = np.std(features, axis=0, dtype=np.float64)
    scale[scale < 1e-6] = 1.0
    normalized = (features.astype(np.float64) - mean) / scale
    design = np.concatenate(
        (normalized, np.ones((len(normalized), 1), dtype=np.float64)), axis=1
    )
    penalty = np.eye(design.shape[1], dtype=np.float64) * float(ridge)
    penalty[-1, -1] = 1e-8
    weights = np.linalg.solve(design.T @ design + penalty, design.T @ targets)
    return {
        "input_mean": mean.astype(np.float32),
        "input_scale": scale.astype(np.float32),
        "weights": _compress_weights(weights[:-1], compression).astype(np.float32),
        "bias": weights[-1].astype(np.float32),
    }


def _predict(model: dict[str, np.ndarray], features: np.ndarray) -> np.ndarray:
    normalized = np.divide(
        features - model["input_mean"],
        model["input_scale"],
        out=np.zeros_like(features, dtype=np.float32),
        where=model["input_scale"] > np.float32(1e-6),
    )
    return normalized @ model["weights"] + model["bias"]


def _prediction_patch(prediction: np.ndarray, target_space: str) -> np.ndarray:
    if target_space == "visible-bits":
        return np.clip(prediction, -1.0, 1.0).reshape(-1, 4, 4)
    if target_space == "walsh-coefficients":
        return ar.texture_decode(prediction, 16)
    raise ValueError(target_space)


def _frontend_runtime(frontend: dict[str, Any]) -> dict[str, Any]:
    return {
        "writer_encoder_kind": frontend["kind"],
        "agc_threshold": float(frontend.get("agc_threshold", 0.0)),
        "codec_model": pb._frontend_codec(frontend),
    }


def _roundtrip_bits(patches: np.ndarray, frontend: dict[str, Any]) -> np.ndarray:
    raw = ar.texture_encode(np.asarray(patches, dtype=np.float32), 16)
    proposal, _ = pb._quantize_frontend(raw, _frontend_runtime(frontend))
    return np.where(ar.texture_decode(proposal, 16).reshape(-1, 16) >= 0.0, 1.0, -1.0)


def _bootstrap(
    values: Sequence[float],
    profile: pb.PhenotypeBridgeProfile,
    contract: LocalTransductionContract,
    *key: Any,
) -> dict[str, Any]:
    return ar._bootstrap(
        list(values),
        max(100, min(profile.bootstrap_resamples, 1_000)),
        ar._hash_seed(contract.namespace, *key),
        contract.strict_alpha,
    )


def _cross_validate_model(
    intact_x: np.ndarray,
    sham_x: np.ndarray,
    bits: np.ndarray,
    groups: np.ndarray,
    target_space: str,
    ridge: float,
    compression: str,
    frontend: dict[str, Any],
    profile: pb.PhenotypeBridgeProfile,
    contract: LocalTransductionContract,
    key: str,
) -> dict[str, Any]:
    target = (
        bits
        if target_space == "visible-bits"
        else ar.texture_encode(bits.reshape(-1, 4, 4), 16)
    )
    intact_scores: list[float] = []
    sham_scores: list[float] = []
    roundtrip_scores: list[float] = []
    unique = sorted(set(groups.tolist()))
    for held in unique:
        train = groups != held
        test = groups == held
        model = _fit_linear(intact_x[train], target[train], ridge, compression)
        intact_patch = _prediction_patch(_predict(model, intact_x[test]), target_space)
        sham_patch = _prediction_patch(_predict(model, sham_x[test]), target_space)
        truth = bits[test]
        intact_scores.append(
            float(np.mean(np.where(intact_patch.reshape(-1, 16) >= 0.0, 1.0, -1.0) == truth))
        )
        sham_scores.append(
            float(np.mean(np.where(sham_patch.reshape(-1, 16) >= 0.0, 1.0, -1.0) == truth))
        )
        roundtrip_scores.append(float(np.mean(_roundtrip_bits(intact_patch, frontend) == truth)))
    effects = [left - right for left, right in zip(intact_scores, sham_scores)]
    return {
        "fold_mode": "leave-one-pair-out",
        "pair_count": len(unique),
        "intact_accuracy": _bootstrap(intact_scores, profile, contract, key, "intact"),
        "sham_accuracy": _bootstrap(sham_scores, profile, contract, key, "sham"),
        "intact_minus_sham": _bootstrap(effects, profile, contract, key, "effect"),
        "carrier_roundtrip_accuracy": _bootstrap(
            roundtrip_scores, profile, contract, key, "roundtrip"
        ),
    }


def _lower(summary: dict[str, Any]) -> float:
    interval = summary.get("ci", [None, None])
    return float(summary.get("mean") or 0.0) if interval[0] is None else float(interval[0])


def _decoder_grid(
    rows: Sequence[dict[str, Any]],
    frontend: dict[str, Any],
    profile: pb.PhenotypeBridgeProfile,
    contract: LocalTransductionContract,
    status: Any,
    deadline: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    proposals: list[dict[str, Any]] = []
    datasets: dict[tuple[int, str, int], tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    registered = [
        (source, radius, length, target, ridge, compression)
        for source in (40, 48)
        for radius in ("patch", "2")
        for length in (1, 2)
        for target in ("visible-bits", "walsh-coefficients")
        for ridge in (0.1, 1.0, 10.0)
        for compression in ("full", "rank8", "sparse8-q8")
    ]
    if len(registered) != contract.maximum_decoder_proposals:
        raise AssertionError("Stage-6G decoder grid changed")
    for index, (source, radius, length, target, ridge, compression) in enumerate(registered):
        if time.time() >= deadline:
            break
        dataset_key = (source, radius, length)
        if dataset_key not in datasets:
            intact_x, bits, groups = _extract_dataset(
                rows, source, radius, length, "intact"
            )
            sham_x, sham_bits, sham_groups = _extract_dataset(
                rows, source, radius, length, "sham"
            )
            if not np.array_equal(bits, sham_bits) or not np.array_equal(groups, sham_groups):
                raise AssertionError("paired intact/sham decoder rows changed")
            datasets[dataset_key] = intact_x, sham_x, bits, groups
        intact_x, sham_x, bits, groups = datasets[dataset_key]
        decoder_id = (
            f"decoder-s{source:02d}-r{radius}-w{length:02d}-"
            f"{target}-l{ridge:g}-{compression}"
        )
        summary = _cross_validate_model(
            intact_x,
            sham_x,
            bits,
            groups,
            target,
            ridge,
            compression,
            frontend,
            profile,
            contract,
            decoder_id,
        )
        proposals.append(
            {
                "decoder_id": decoder_id,
                "source_read_sweeps": source,
                "writer_observation_radius": radius,
                "trace_sweeps": length,
                "target_space": target,
                "ridge": ridge,
                "compression": compression,
                "input_dimension": int(intact_x.shape[1]),
                **summary,
            }
        )
        status("running", "decoder-grid", completed=index + 1, total=len(registered))
    ranking = lambda row: (
        _lower(row["carrier_roundtrip_accuracy"]),
        _lower(row["intact_minus_sham"]),
        _lower(row["intact_accuracy"]),
        -int(row["input_dimension"]),
    )
    selected: list[dict[str, Any]] = []
    used: set[tuple[str, str]] = set()
    for row in sorted(proposals, key=ranking, reverse=True):
        diversity = (str(row["target_space"]), str(row["writer_observation_radius"]))
        if diversity in used:
            continue
        intact_x, _, bits, groups = datasets[
            (
                int(row["source_read_sweeps"]),
                str(row["writer_observation_radius"]),
                int(row["trace_sweeps"]),
            )
        ]
        target = (
            bits
            if row["target_space"] == "visible-bits"
            else ar.texture_encode(bits.reshape(-1, 4, 4), 16)
        )
        model = _fit_linear(
            intact_x, target, float(row["ridge"]), str(row["compression"])
        )
        training_ids = sorted(set(groups.tolist()))
        transform = {
            "transform_id": str(row["decoder_id"]),
            "kind": "linear",
            "input_mode": "stack",
            "target_space": str(row["target_space"]),
            "input_mean": model["input_mean"].tolist(),
            "input_scale": model["input_scale"].tolist(),
            "weights": model["weights"].tolist(),
            "bias": model["bias"].tolist(),
            "model_frozen": True,
            "training_pair_count": len(training_ids),
            "training_pair_ids_sha256": hashlib.sha256(
                "\n".join(training_ids).encode()
            ).hexdigest(),
            "model_sha256": _digest(
                {
                    "mean": model["input_mean"].tolist(),
                    "scale": model["input_scale"].tolist(),
                    "weights": model["weights"].tolist(),
                    "bias": model["bias"].tolist(),
                }
            ),
        }
        selected.append({**row, "writer_transform": transform})
        used.add(diversity)
        if len(selected) == 4:
            break
    complete = len(proposals) == len(registered) and len(selected) == 4
    return proposals, selected if complete else []


def _candidate_specs(
    decoders: Sequence[dict[str, Any]],
    frontend: dict[str, Any],
) -> list[dict[str, Any]]:
    if len(decoders) != 4:
        raise ValueError("Stage-6G requires four frozen decoder families")

    def configured_frontend(
        identifier: str,
        source: int,
        length: int,
    ) -> dict[str, Any]:
        result = dict(frontend)
        result.update(
            {
                "frontend_id": identifier,
                "read_sweeps": source,
                "clearance_updates": 1,
                "trace_sweeps": length,
            }
        )
        return result

    label_free: list[dict[str, Any]] = []
    for source, feature in (
        (40, "endpoint"),
        (48, "endpoint"),
        (40, "multiscale"),
        (48, "multiscale"),
    ):
        candidate_id = f"stage6g-label-free-s{source:02d}-{feature}"
        label_free.append(
            {
                "candidate_id": candidate_id,
                "claim_tier": "strict",
                "claim_class": "label-free-local",
                "training_mode": "label-free",
                "mechanism": "timing-only",
                "writer_source": "visible",
                "writer_input_contract": "visible-only",
                "writer_feature": feature,
                "writer_observation_radius": "patch",
                "somatic_architecture": "none",
                "somatic_channels": 1,
                "somatic_retention": 0.0,
                "somatic_bias": 0.0,
                "frontend": configured_frontend(candidate_id, source, 1),
            }
        )

    assisted: list[dict[str, Any]] = []
    for index, decoder in enumerate(decoders):
        source = int(decoder["source_read_sweeps"])
        length = int(decoder["trace_sweeps"])
        candidate_id = f"stage6g-assisted-{index:02d}-{decoder['decoder_id']}"
        assisted.append(
            {
                "candidate_id": candidate_id,
                "claim_tier": "broad",
                "claim_class": "rulebook-assisted-local",
                "training_mode": "rulebook-assisted",
                "mechanism": "timing-only",
                "writer_source": "visible",
                "writer_input_contract": "visible-only",
                "writer_feature": "endpoint",
                "writer_observation_radius": decoder["writer_observation_radius"],
                "somatic_architecture": "none",
                "somatic_channels": 1,
                "somatic_retention": 0.0,
                "somatic_bias": 0.0,
                "writer_transform": decoder["writer_transform"],
                "frontend": configured_frontend(candidate_id, source, length),
            }
        )

    patch_decoders = [
        row
        for row in decoders
        if row["writer_observation_radius"] == "patch"
    ]
    if not patch_decoders:
        raise AssertionError("Stage-6G did not seal a patch translator")
    seed_decoder = max(
        patch_decoders,
        key=lambda row: (
            _lower(row["carrier_roundtrip_accuracy"]),
            _lower(row["intact_minus_sham"]),
        ),
    )
    somatic: list[dict[str, Any]] = []
    variants = (
        ("multi-timescale-ema", "visible", "slow"),
        ("local-reservoir", "visible", "mean"),
        ("multi-timescale-ema", "somatic", "slow"),
        ("transition-eligibility", "somatic", "mean"),
    )
    for index, (architecture, source_kind, readout) in enumerate(variants):
        candidate_id = f"stage6g-somatic-{index:02d}-{architecture}-{source_kind}"
        transform = json.loads(json.dumps(seed_decoder["writer_transform"]))
        transform["transform_id"] = f"{transform['transform_id']}-{architecture}-{source_kind}"
        somatic.append(
            {
                "candidate_id": candidate_id,
                "claim_tier": "broad",
                "claim_class": "rulebook-assisted-local",
                "training_mode": "rulebook-assisted",
                "mechanism": "somatic-field",
                "writer_source": source_kind,
                "writer_input_contract": (
                    "field-readable" if source_kind == "somatic" else "visible-only"
                ),
                "writer_feature": "endpoint",
                "writer_observation_radius": "patch",
                "somatic_architecture": architecture,
                "somatic_channels": 2,
                "somatic_retention": 0.95,
                "somatic_bias": 0.60,
                "somatic_readout": readout,
                "somatic_acquisition_window": 8,
                "somatic_support_sweeps": 8,
                "writer_transform": transform,
                "frontend": configured_frontend(
                    candidate_id,
                    int(seed_decoder["source_read_sweeps"]),
                    int(seed_decoder["trace_sweeps"]),
                ),
            }
        )

    # Interleave families so the reduced smoke profile exercises label-free,
    # translated-visible, and translated-somatic mechanisms.
    specs: list[dict[str, Any]] = []
    for index in range(4):
        specs.extend((label_free[index], assisted[index], somatic[index]))
    if len(specs) != 12 or len({row["candidate_id"] for row in specs}) != 12:
        raise AssertionError("Stage-6G frozen candidate allocation changed")
    return specs


def _closure_decomposition(
    rows: Sequence[dict[str, Any]],
    decoder: dict[str, Any],
    frontend: dict[str, Any],
    specs: Sequence[dict[str, Any]],
    stage6br_root: Path,
    contract: LocalTransductionContract,
) -> dict[str, Any]:
    source = int(decoder["source_read_sweeps"])
    radius = str(decoder["writer_observation_radius"])
    length = int(decoder["trace_sweeps"])
    features, bits, _ = _extract_dataset(rows, source, radius, length, "intact")
    transform = decoder["writer_transform"]
    model = {
        "input_mean": np.asarray(transform["input_mean"], dtype=np.float32),
        "input_scale": np.asarray(transform["input_scale"], dtype=np.float32),
        "weights": np.asarray(transform["weights"], dtype=np.float32),
        "bias": np.asarray(transform["bias"], dtype=np.float32),
    }
    predicted_patch = _prediction_patch(
        _predict(model, features), str(decoder["target_space"])
    )
    true_patch = bits.reshape(-1, 4, 4)
    true_roundtrip = _roundtrip_bits(true_patch, frontend)
    predicted_roundtrip = _roundtrip_bits(predicted_patch, frontend)
    if radius == "patch" and length == 1:
        raw_patch = features.reshape(-1, 4, 4)
        raw_roundtrip = _roundtrip_bits(raw_patch, frontend)
        raw_accuracy = float(np.mean(raw_roundtrip == bits))
    else:
        raw_accuracy = float("nan")

    assisted_spec = next(
        row for row in specs if row["training_mode"] == "rulebook-assisted"
    )
    candidate = pb.build_writeback_candidates([assisted_spec], stage6br_root)[0][0]
    usable = 2 * (len(true_patch) // 2)
    proposal, _ = pb._quantize_frontend(
        ar.texture_encode(true_patch[:usable], 16), candidate
    )
    shares, active = pb._encode_carrier(
        proposal, candidate, contract, "stage6g-decomposition", 5, "true-payload"
    )
    copied, uncorrectable = pb._copy_carrier(
        shares, "stage6g-decomposition", 6, usable // 2, contract
    )
    recovered, valid = pb._joint_payload(copied, active, candidate)
    recovered_bits = np.where(
        ar.texture_decode(recovered, 16).reshape(-1, 16) >= 0.0, 1.0, -1.0
    )
    true_accuracy = float(np.mean(true_roundtrip == bits))
    predicted_accuracy = float(np.mean(predicted_roundtrip == bits))
    physical_accuracy = float(np.mean(recovered_bits == bits[:usable]))
    downstream_gate = bool(true_accuracy >= 0.95 and physical_accuracy >= 0.95)
    translator_gate = bool(
        _lower(decoder["carrier_roundtrip_accuracy"])
        >= contract.translator_accuracy_minimum
        and _lower(decoder["intact_minus_sham"])
        > contract.translator_effect_minimum
    )
    return {
        "state": "complete",
        "stage_gate": downstream_gate and translator_gate,
        "true_payload_quantized_accuracy": true_accuracy,
        "frozen_translator_training_fit_accuracy": predicted_accuracy,
        "raw_identity_roundtrip_accuracy": raw_accuracy,
        "physical_share_copy_roundtrip_accuracy": physical_accuracy,
        "physical_share_valid_fraction": float(np.mean(valid)),
        "copy_uncorrectable_fraction": float(uncorrectable),
        "cross_validated_translator": {
            "decoder_id": decoder["decoder_id"],
            "intact_accuracy": decoder["intact_accuracy"],
            "intact_minus_sham": decoder["intact_minus_sham"],
            "carrier_roundtrip_accuracy": decoder["carrier_roundtrip_accuracy"],
        },
        "downstream_carrier_gate": downstream_gate,
        "translator_gate": translator_gate,
        "teacher_assisted_runtime_control": {
            "registered": True,
            "promotable": False,
            "target_exposed": True,
            "purpose": "locate an otherwise ambiguous downstream failure",
        },
        "final_audit_trajectory_state": "untouched",
    }


def _prepare_subcampaign(
    stage_root: Path,
    profile_name: str,
    specs: Sequence[dict[str, Any]],
    design_digest: str,
    roots: dict[str, Path],
    *,
    auto_final_audit: bool,
) -> tuple[
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    pb.PhenotypeBridgeProfile,
    LocalTransductionContract,
    ar.MotifContract,
    list[dict[str, Any]],
]:
    frozen, cohorts, profile, _, writer_contract, templates, parent_digest = pb._prepare_stage6e(
        stage_root,
        profile_name,
        auto_final_audit=auto_final_audit,
        **roots,
    )
    if profile_name == "reference":
        bridge_ids = sorted(str(pair["pair_id"]) for pair in cohorts["bridge"])
        bridge_digest = hashlib.sha256("\n".join(bridge_ids).encode()).hexdigest()
        trained_digests = {
            str(row["writer_transform"]["training_pair_ids_sha256"])
            for row in specs
            if row.get("training_mode") == "rulebook-assisted"
        }
        if trained_digests != {bridge_digest}:
            raise ValueError("frozen translator training cohort differs from Stage-6G bridge cohort")
    selection_digest = _digest(list(specs))
    ar._atomic_json(
        stage_root / "PARENT_PREPARATION.json",
        {
            "parent_design_digest": parent_digest,
            "campaign_design_digest": design_digest,
            "candidate_selection_digest": selection_digest,
        },
    )
    ar._atomic_json(
        stage_root / "WRITEBACK_CANDIDATES.json",
        {
            "design_digest": design_digest,
            "selection_digest": selection_digest,
            "selection_frozen_before_screen": True,
            "promotable_count": len(specs),
            "runtime_retraining": False,
            "candidates": list(specs),
        },
    )
    bridge_root = stage_root / "bridge"
    bridge_root.mkdir(parents=True, exist_ok=True)
    bridge_result = {
        "experiment": "ca_motif_phenotype_bridge_stage_6e",
        "design_digest": design_digest,
        "phase": "bridge",
        "state": "complete",
        "stage_gate": True,
        "selection_digest": selection_digest,
        "local_transduction_registry": True,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(bridge_root / "RESULTS.json", bridge_result)
    ar._atomic_text(bridge_root / "COMPLETE", "complete\n")
    return (
        frozen,
        cohorts,
        profile,
        LocalTransductionContract(),
        writer_contract,
        templates,
    )


def _translator_screen_gate(summary: dict[str, Any]) -> bool:
    if summary.get("training_mode") != "rulebook-assisted":
        return True
    controls = summary.get("control_retention", {})
    return bool(
        controls.get("translator_ablation", 1.0) <= 0.30
        and controls.get("translator_history_shuffle", 1.0) <= 0.50
        and controls.get("translator_weight_shuffle", 1.0) <= 0.70
        and controls.get("translator_bit_permutation", 1.0) <= 0.70
    )


def _filter_screen(
    stage_root: Path,
    result: dict[str, Any],
    *,
    scientific: bool,
) -> dict[str, Any]:
    summaries = result["candidate_summaries"]
    candidates = [
        candidate_id
        for candidate_id in result.get("selected_candidate_ids", [])
        if not scientific or _translator_screen_gate(summaries[candidate_id])
    ]
    selected: list[str] = []
    counts = {"strict": 0, "broad": 0}
    for candidate_id in candidates:
        tier = str(summaries[candidate_id]["claim_tier"])
        if tier in counts and counts[tier] < 2:
            selected.append(candidate_id)
            counts[tier] += 1
    result["pre_translator_control_candidate_ids"] = list(
        result.get("selected_candidate_ids", [])
    )
    result["selected_candidate_ids"] = selected
    result["selected_by_tier"] = {
        tier: [candidate_id for candidate_id in selected if summaries[candidate_id]["claim_tier"] == tier]
        for tier in counts
    }
    result["translator_control_gate_applied"] = scientific
    result["stage_gate"] = bool(selected)
    ar._atomic_json(stage_root / "screen/RESULTS.json", result)
    return result


def _filter_qualification(
    stage_root: Path,
    result: dict[str, Any],
    *,
    scientific: bool,
) -> dict[str, Any]:
    summaries = result.get("candidate_summaries", {})
    qualified: list[str] = []
    seen: set[str] = set()
    for candidate_id in result.get("qualified_candidate_ids", []):
        generation16 = summaries[candidate_id]["generation16"]
        tier = str(generation16["claim_tier"])
        controls = generation16.get("control_retention", {})
        translator_gate = bool(
            generation16.get("training_mode") != "rulebook-assisted"
            or (
                controls.get("translator_ablation", 1.0) <= 0.30
                and controls.get("translator_history_shuffle", 1.0) <= 0.30
                and controls.get("translator_weight_shuffle", 1.0) <= 0.50
                and controls.get("translator_bit_permutation", 1.0) <= 0.50
            )
        )
        if (not scientific or translator_gate) and tier not in seen:
            qualified.append(candidate_id)
            seen.add(tier)
    result["pre_translator_control_qualified_ids"] = list(
        result.get("qualified_candidate_ids", [])
    )
    result["qualified_candidate_ids"] = qualified
    result["translator_control_gate_applied"] = scientific
    result["stage_gate"] = bool(qualified)
    ar._atomic_json(stage_root / "qualify/RESULTS.json", result)
    return result


def _run_development(
    output: Path,
    profile_name: str,
    specs: Sequence[dict[str, Any]],
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
    stage_root = output / "stage6g"
    frozen, cohorts, profile, contract, writer_contract, templates = _prepare_subcampaign(
        stage_root,
        profile_name,
        specs,
        design_digest,
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
        design_digest=design_digest,
        stage6br_root=roots["stage6br_root"],
        workers=workers,
        resume=resume,
        scientific=profile_name == "reference",
        status=status,
    )
    screen_conditions = tuple(
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
    audit_conditions = tuple(
        dict.fromkeys(
            (
                *pb.AUDIT_CONDITIONS,
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
    active_phase[0] = "screen"
    screen = pb._run_screen(
        **common,
        deadline=float(campaign["exploration_deadline_unix"]),
        conditions=screen_conditions,
    )
    screen = _filter_screen(
        stage_root, screen, scientific=profile_name == "reference"
    )
    active_phase[0] = "qualify"
    qualify = pb._run_qualification(
        **common,
        deadline=float(campaign["exploration_deadline_unix"]),
        conditions=qualification_conditions,
    )
    qualify = _filter_qualification(
        stage_root, qualify, scientific=profile_name == "reference"
    )
    active_phase[0] = "endurance"
    endurance = pb._run_endurance(
        **common,
        deadline=float(campaign["exploration_deadline_unix"]),
        conditions=tuple(
            dict.fromkeys(
                (
                    *pb.ENDURANCE_CONDITIONS,
                    "translator_ablation",
                    "translator_history_shuffle",
                    "writer_spatial_shift",
                )
            )
        ),
    )
    active_phase[0] = "adjudicate"
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
    design_digest: str,
    profile_name: str,
    decomposition: dict[str, Any],
    development: dict[str, Any] | None,
    specs: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    by_id = {str(row["candidate_id"]): row for row in specs}
    if development is None:
        selected = qualified = enduring = confirmed = []
        reserve = "untouched"
        verdict = "INCONCLUSIVE_RESOURCE_LIMIT"
    else:
        selected = list(development["screen"].get("selected_candidate_ids", []))
        qualified = list(development["qualify"].get("qualified_candidate_ids", []))
        enduring = list(development["endurance"].get("enduring_candidate_ids", []))
        confirmed = list(development["adjudicate"].get("confirmed_candidate_ids", []))
        reserve = str(
            development["adjudicate"].get(
                "final_audit_trajectory_state", "untouched"
            )
        )
        confirmed_modes = {
            str(by_id[candidate_id].get("training_mode"))
            for candidate_id in confirmed
            if candidate_id in by_id
        }
        budget_truncated = any(
            development[phase].get("state") == "budget_truncated"
            for phase in ("screen", "qualify", "endurance", "adjudicate")
        )
        if budget_truncated:
            verdict = "INCONCLUSIVE_RESOURCE_LIMIT"
        elif profile_name == "smoke":
            verdict = "SMOKE_PATH_VALIDATED"
        elif "label-free" in confirmed_modes:
            verdict = "LABEL_FREE_LOCAL_PH_CONFIRMED"
        elif "rulebook-assisted" in confirmed_modes:
            verdict = "RULEBOOK_ASSISTED_LOCAL_PH_CONFIRMED"
        elif enduring:
            verdict = "LOCAL_CLOSURE_NOT_CONFIRMED"
        elif qualified:
            verdict = "ONE_GENERATION_TRANSDUCTION_ONLY"
        elif selected:
            verdict = "LOCAL_TRANSDUCTION_NOT_ENDURING"
        elif not decomposition.get("downstream_carrier_gate"):
            verdict = "DOWNSTREAM_CARRIER_FAILURE"
        elif decomposition.get("translator_gate"):
            verdict = "DECODABLE_NOT_TRANSDUCIBLE"
        else:
            verdict = "LOCAL_INFORMATION_INSUFFICIENT"
    result = {
        "experiment": "ca_motif_local_transduction_stage_6g",
        "design_digest": design_digest,
        "state": "complete",
        "profile_name": profile_name,
        "verdict": verdict,
        "parent_verdict": "OBSERVABLE_NOT_WRITABLE",
        "selected_candidate_ids": selected,
        "qualified_candidate_ids": qualified,
        "enduring_candidate_ids": enduring,
        "confirmed_candidate_ids": confirmed,
        "confirmed_claim_classes": sorted(
            {
                str(by_id[candidate_id].get("claim_class"))
                for candidate_id in confirmed
                if candidate_id in by_id
            }
        ),
        "stage_gate": bool(confirmed),
        "final_audit_opened": reserve in ("opened", "complete", "partial"),
        "final_audit_trajectory_state": reserve,
        "runtime_adaptation_promotable": False,
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
        "# Stage 6G local transduction and hereditary closure\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"Selected: {selected}\n\nQualified: {qualified}\n\n"
        f"Enduring: {enduring}\n\nConfirmed: {confirmed}\n\n"
        "The target-exposed per-daughter control was non-promotable.\n",
    )
    if verdict == "LABEL_FREE_LOCAL_PH_CONFIRMED":
        lay = "A daughter used only its local visible form to rebuild a fresh note repeatedly, without a learned history decoder."
    elif verdict == "RULEBOOK_ASSISTED_LOCAL_PH_CONFIRMED":
        lay = "A fixed translator in the rulebook converted the daughter's local form into a renewable inherited note across the full causal audit."
    elif verdict == "DECODABLE_NOT_TRANSDUCIBLE":
        lay = "The local trace contains the old history and the carrier machinery works, but even a frozen translator could not close the live generational loop."
    elif verdict == "DOWNSTREAM_CARRIER_FAILURE":
        lay = "Even a correct replacement note did not reliably guide the next daughter, so the remaining problem lies downstream of translation."
    elif verdict == "INCONCLUSIVE_RESOURCE_LIMIT":
        lay = "The registered clock expired before the decisive transduction tests completed."
    else:
        lay = "The experiment localized how far a readable local trace can travel back toward renewable inherited memory."
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


def run_motif_local_transduction(
    output: Path,
    *,
    stage6f_root: Path = DEFAULT_STAGE6F_ROOT,
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
    """Run the sealed Stage-6G local-transduction campaign."""

    ar.require_pinned_numpy()
    if profile_name not in pb.PUBLIC_PROFILES:
        raise ValueError(f"unknown Stage-6G profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6G workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6G max-hours must be in (0, 8]")
    if profile_name == "reference" and not auto_final_audit:
        raise ValueError("reference Stage-6G requires automatic final-audit authorization")
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ar._atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
    stage6f_root = stage6f_root.resolve()
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
        contract, campaign, design_digest, integrity = _prepare_campaign(
            output,
            profile_name,
            stage6f_root,
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
            integrity | {"next_phase": "decode"},
            "# Stage 6G integrity\n\nThe complete Stage-6F local-signal result and all 32 bridge traces were hashed and verified.",
            "# Lay summary\n\nThe new experiment starts from the exact completed evidence and does not alter it.",
        )

        rows = wb._trace_rows(stage6f_root / "replay")
        frontends = _load_json(
            stage6f_root / "replay/SEALED_FRONTENDS.json"
        )["frontends"]
        frontend = min(
            [row for row in frontends if bool(row.get("promotable", True))],
            key=lambda row: (int(row["bits"]), str(row["frontend_id"])),
        )
        active_phase[0] = "decode"
        if resume and (output / "decode/COMPLETE").exists():
            decode = _load_json(output / "decode/RESULTS.json")
            decoders = list(_load_json(output / "SEALED_TRANSLATORS.json")["decoders"])
        else:
            proposals, decoders = _decoder_grid(
                rows,
                frontend,
                pb.PHENOTYPE_BRIDGE_PROFILES[profile_name],
                contract,
                status,
                float(campaign["exploration_deadline_unix"]),
            )
            ar._atomic_json(
                output / "DECODER_GRID.json",
                {
                    "design_digest": design_digest,
                    "registered_count": len(proposals),
                    "proposals": proposals,
                },
            )
            ar._atomic_json(
                output / "SEALED_TRANSLATORS.json",
                {
                    "design_digest": design_digest,
                    "selection_frozen_before_screen": True,
                    "runtime_retraining": False,
                    "decoder_count": len(decoders),
                    "selection_digest": _digest(decoders),
                    "decoders": decoders,
                },
            )
            decode = {
                "state": "complete" if len(proposals) == 144 and len(decoders) == 4 else "budget_truncated",
                "stage_gate": len(decoders) == 4,
                "registered_decoder_count": len(proposals),
                "sealed_decoder_count": len(decoders),
                "sealed_decoder_ids": [row["decoder_id"] for row in decoders],
                "selection_digest": _digest(decoders),
                "next_phase": "decompose" if decoders else None,
                "final_audit_trajectory_state": "untouched",
            }
            _write_phase(
                output,
                "decode",
                design_digest,
                decode,
                "# Frozen local decoder ladder\n\nFour diverse translators were selected by pair-blocked development folds and frozen before screening.",
                "# Lay summary\n\nWe learned a fixed dictionary for translating the daughter's local pattern into the note's alphabet.",
            )

        specs: list[dict[str, Any]] = []
        decomposition: dict[str, Any]
        development: dict[str, Any] | None = None
        if decoders and time.time() < float(campaign["exploration_deadline_unix"]):
            specs = _candidate_specs(decoders, frontend)
            active_phase[0] = "decompose"
            if resume and (output / "decompose/COMPLETE").exists():
                decomposition = _load_json(output / "decompose/RESULTS.json")
            else:
                best_decoder = max(
                    decoders,
                    key=lambda row: (
                        _lower(row["carrier_roundtrip_accuracy"]),
                        _lower(row["intact_minus_sham"]),
                    ),
                )
                decomposition = _closure_decomposition(
                    rows,
                    best_decoder,
                    frontend,
                    specs,
                    roots["stage6br_root"],
                    contract,
                )
                _write_phase(
                    output,
                    "decompose",
                    design_digest,
                    decomposition | {"next_phase": "discover"},
                    "# Closure decomposition\n\nVisible decoding, Walsh quantization, secret sharing, copy noise, and carrier recovery were scored separately.",
                    "# Lay summary\n\nThis distinguishes a bad dictionary from a broken note-delivery system.",
                )

            active_phase[0] = "discover"
            ar._atomic_json(
                output / "TRANSDUCER_CANDIDATES.json",
                {
                    "design_digest": design_digest,
                    "selection_frozen_before_screen": True,
                    "selection_digest": _digest(specs),
                    "candidate_count": len(specs),
                    "claim_counts": {
                        "label-free-local": sum(
                            row["claim_class"] == "label-free-local" for row in specs
                        ),
                        "rulebook-assisted-local": sum(
                            row["claim_class"] == "rulebook-assisted-local" for row in specs
                        ),
                    },
                    "candidates": specs,
                },
            )
            discovery = {
                "state": "complete",
                "stage_gate": len(specs) == 12,
                "candidate_count": len(specs),
                "selection_digest": _digest(specs),
                "selection_frozen_before_screen": True,
                "next_phase": "screen",
                "final_audit_trajectory_state": "untouched",
            }
            _write_phase(
                output,
                "discover",
                design_digest,
                discovery,
                "# Stage 6G frozen candidates\n\nFour label-free, four frozen-visible, and four frozen-somatic writers were sealed.",
                "# Lay summary\n\nThe twelve best attempts were locked before any new lineage was tested.",
            )

            active_phase[0] = "screen"
            development = _run_development(
                output,
                profile_name,
                specs,
                design_digest,
                roots,
                campaign,
                status,
                active_phase,
                workers=workers,
                resume=resume,
                auto_final_audit=auto_final_audit,
            )
            for phase_name in ("screen", "qualify", "endurance", "adjudicate"):
                active_phase[0] = phase_name
                summary = development[phase_name]
                _write_phase(
                    output,
                    phase_name,
                    design_digest,
                    {
                        "state": summary.get("state", "complete"),
                        "stage_gate": bool(summary.get("stage_gate")),
                        "subcampaign_result": summary,
                        "next_phase": None,
                        "final_audit_trajectory_state": summary.get(
                            "final_audit_trajectory_state", "untouched"
                        ),
                    },
                    f"# Stage 6G {phase_name}\n\nThe nested sealed campaign contains the complete causal statistics.",
                    "# Lay summary\n\nOnly mechanisms passing every earlier test were allowed to continue.",
                )
        else:
            decomposition = {
                "state": "budget_truncated",
                "stage_gate": False,
                "downstream_carrier_gate": False,
                "translator_gate": False,
                "final_audit_trajectory_state": "untouched",
            }

        active_phase[0] = "complete"
        result = _campaign_result(
            output,
            design_digest,
            profile_name,
            decomposition,
            development,
            specs,
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
    "DEFAULT_STAGE6F_ROOT",
    "PHASES",
    "LocalTransductionContract",
    "run_motif_local_transduction",
)
