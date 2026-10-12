"""Stage-6E phenotype bridge and transient somatic consolidation.

Stage 6D is immutable input.  This module keeps its visible-reset and
secret-sharing substrate but separately tests whether a consumed inherited
texture can cross a visible or temporary-somatic phenotype and be rewritten.

Version 2 repairs the acquisition-generation gate: the environmental writer
must create the founder carrier before an incoming texture carrier exists.
The semantic namespace deliberately remains at v1 so repaired runs reuse the
registered random streams and isolate that single causal change.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, replace
from itertools import combinations
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
from . import motif_synergistic_heredity as sy


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_PHENOTYPE_BRIDGE_PROTOCOL.md"
DEFAULT_STAGE6D_ROOT = ROOT / "results/ca-motif-consumptive-renewal-stage-6d"
PHASES = ("forensics", "bridge", "screen", "qualify", "endurance", "adjudicate")
RULE_STRESS_PANEL = (31648, 31651, 31617, 32673, 64417, 70366)

SCREEN_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
    "acquisition_write_disabled",
    "somatic_write_disabled",
    "somatic_bias_disabled",
    "phenotype_scrub",
    "no_erasure",
)
QUALIFICATION_CONDITIONS = (
    *SCREEN_CONDITIONS,
    "zero_every_boundary",
    "shuffle_every_boundary",
    "transport_disabled",
    "ablate_after_g5",
    "rescue_same_enter_g6",
    "rescue_opposite_enter_g6",
    "phenotype_same_rescue",
    "phenotype_opposite_rescue",
    "somatic_ablation",
    "somatic_shuffle",
    "somatic_same_rescue",
    "somatic_opposite_rescue",
    "writer_observation_shuffle",
    "statistical_disabled",
    "translated_patch",
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
    "translated_patch",
)
AUDIT_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
    "acquisition_write_disabled",
    "phenotype_scrub",
    "phenotype_same_rescue",
    "phenotype_opposite_rescue",
    "somatic_ablation",
    "somatic_same_rescue",
    "somatic_opposite_rescue",
)
ALL_CONDITIONS = tuple(dict.fromkeys((*QUALIFICATION_CONDITIONS, *ENDURANCE_CONDITIONS, *AUDIT_CONDITIONS)))
WRITEBACK_CONDITIONS = (
    "trace_write_disabled",
    "trace_read_disabled",
    "trace_ablation",
    "trace_shuffle",
    "trace_same_rescue",
    "trace_opposite_rescue",
    "writer_temporal_reverse",
    "writer_temporal_shuffle",
)
TRANSDUCTION_CONDITIONS = (
    "translator_ablation",
    "translator_weight_shuffle",
    "translator_bit_permutation",
    "translator_history_shuffle",
    "writer_spatial_shift",
)
TRAJECTORY_FIELD_CONDITIONS = (
    "orbit_phase_shift",
    "orbit_temporal_reverse",
    "orbit_temporal_shuffle",
    "inherited_field_zero",
    "inherited_field_shuffle",
    "inherited_field_read_disabled",
    "inherited_field_write_disabled",
    "inherited_field_no_renewal",
    "inherited_field_ablation",
    "inherited_field_coefficient_shuffle",
    "inherited_field_same_rescue",
    "inherited_field_opposite_rescue",
    "inherited_field_one_bin_damage",
    "inherited_field_copy_noise_5",
    "handoff_visible_scrub",
    "closure_self_rehearsal_disabled",
)
ALL_CONDITIONS = tuple(
    dict.fromkeys(
        (
            *ALL_CONDITIONS,
            *WRITEBACK_CONDITIONS,
            *TRANSDUCTION_CONDITIONS,
            *TRAJECTORY_FIELD_CONDITIONS,
        )
    )
)


@dataclass(frozen=True)
class PhenotypeBridgeContract(cr.ConsumptiveRenewalContract):
    implementation_version: str = "ca-motif-phenotype-bridge-v2-acquisition-repair"
    namespace: str = "plastic-ca-motif-phenotype-bridge-v1"
    somatic_support_sweeps: int = 4
    bridge_clearance_updates: tuple[int, ...] = (1, 2, 3, 5, 9)
    bridge_trace_lengths: tuple[int, ...] = (1, 2, 4, 8)
    final_strict_alpha: float = 0.0125

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "somatic_support_sweeps": self.somatic_support_sweeps,
                "bridge_clearance_updates": self.bridge_clearance_updates,
                "bridge_trace_lengths": self.bridge_trace_lengths,
                "claim_ladder": ("strict-form-mediated", "somatically-mediated"),
                "strict_writer_inputs": ("visible cells",),
                "broad_writer_inputs": ("visible cells",),
                "somatic_birth_state": "exact zero",
                "somatic_inherited": False,
                "rule_stress_panel": RULE_STRESS_PANEL,
            }
        )
        return payload


@dataclass(frozen=True)
class PhenotypeBridgeProfile:
    bridge_pairs: int
    bridge_replicates: int
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


PHENOTYPE_BRIDGE_PROFILES: dict[str, PhenotypeBridgeProfile] = {
    "smoke": PhenotypeBridgeProfile(1, 1, 2, 1, 2, 1, 1, 1, 2, 1, 100, 4),
    "pilot": PhenotypeBridgeProfile(4, 4, 8, 4, 12, 4, 4, 4, 8, 4, 1_000, 14),
    "reference": PhenotypeBridgeProfile(8, 4, 16, 4, 32, 8, 8, 4, 62, 4, 10_000, 26),
}
PUBLIC_PROFILES = tuple(PHENOTYPE_BRIDGE_PROFILES)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _frontend_codec(frontend: dict[str, Any]) -> dict[str, Any]:
    bits = int(frontend["bits"])
    rank = int(frontend.get("rank", 16))
    if rank not in (4, 8, 16):
        raise ValueError("Stage-6E frontend rank must be 4, 8, or 16")
    scale = np.asarray(frontend.get("scale", np.ones(rank)), dtype=np.float32)
    if scale.shape == (16,) and rank < 16:
        scale = scale[:rank]
    if scale.shape != (rank,):
        raise ValueError("Stage-6E frontend scale must match its texture rank")
    return {
        "bits": bits,
        "rank": rank,
        "quantizer_scale": scale,
        "basis": ar.TEXTURE_BASIS[:rank].copy(),
        "codec_id": str(frontend["encoder_id"]),
    }


def _quantize_frontend(values: np.ndarray, candidate: dict[str, Any]) -> tuple[np.ndarray, float]:
    latent = np.asarray(values, dtype=np.float32)
    kind = str(candidate["writer_encoder_kind"])
    if kind == "float32":
        return latent.copy(), 0.0
    if kind == "agc-q4":
        magnitude = np.max(np.abs(latent), axis=-1, keepdims=True)
        threshold = float(candidate["agc_threshold"])
        enabled = magnitude > threshold
        latent = np.divide(latent, magnitude, out=np.zeros_like(latent), where=enabled)
    return ar._quantize(latent, candidate["codec_model"])


def _codes_from_payload(payload: np.ndarray, candidate: dict[str, Any]) -> np.ndarray:
    values = np.asarray(payload, dtype=np.float32)
    codec = candidate["codec_model"]
    bits = int(codec["bits"])
    qmax = (1 << (bits - 1)) - 1
    scale = np.asarray(codec["quantizer_scale"], dtype=np.float32)
    normalized = np.divide(values, scale, out=np.zeros_like(values), where=scale > 0)
    signed = np.clip(np.rint(normalized * qmax), -qmax, qmax).astype(np.int16)
    codes = (signed + qmax).astype(np.uint8)
    if bits <= 4:
        return codes
    return np.concatenate((codes & np.uint8(15), codes >> np.uint8(4)), axis=-1)


def _payload_from_codes(lanes: np.ndarray, candidate: dict[str, Any]) -> np.ndarray:
    values = np.asarray(lanes, dtype=np.uint8)
    codec = candidate["codec_model"]
    bits = int(codec["bits"])
    rank = int(candidate["rank"])
    if bits <= 4:
        codes = values[..., :rank]
    else:
        codes = values[..., :rank] | (values[..., rank : 2 * rank] << np.uint8(4))
    qmax = (1 << (bits - 1)) - 1
    signed = codes.astype(np.int16) - qmax
    signed = np.clip(signed, -qmax, qmax)
    scale = np.asarray(codec["quantizer_scale"], dtype=np.float32)
    return (signed.astype(np.float32) * (scale / np.float32(qmax))).astype(np.float32)


def _encode_carrier(
    payload: np.ndarray,
    candidate: dict[str, Any],
    contract: PhenotypeBridgeContract,
    pair_id: str,
    generation: int,
    purpose: str,
) -> tuple[np.ndarray, np.ndarray]:
    lanes = _codes_from_payload(payload, candidate)
    count = int(candidate["seed_count"])
    shares = sy.xor_share_codes(
        lanes,
        count,
        ar._hash_seed(contract.namespace, pair_id, "share-mask", purpose, generation, count),
    )
    return shares.astype(np.uint8), np.ones_like(shares, dtype=np.bool_)


def _copy_carrier(
    shares: np.ndarray,
    pair_id: str,
    generation: int,
    replicates: int,
    contract: PhenotypeBridgeContract,
    *,
    purpose: str = "texture-copy",
    corruption: float | None = None,
) -> tuple[np.ndarray, float]:
    values = np.asarray(shares, dtype=np.uint8)
    rng = np.random.default_rng(
        ar._hash_seed(contract.namespace, pair_id, purpose, generation, values.shape[-1])
    )
    half = rng.random((replicates,) + values.shape[1:] + (8,))
    probability = contract.bit_corruption if corruption is None else float(corruption)
    flips = np.concatenate((half, half), axis=0) < probability
    decoded, uncorrectable = ar.carrier_code_roundtrip(values, "hamming84", flips)
    return decoded.astype(np.uint8), float(uncorrectable)


def _joint_payload(
    shares: np.ndarray, active: np.ndarray, candidate: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(shares, dtype=np.uint8)
    present = np.asarray(active, dtype=np.bool_)
    valid = np.all(present, axis=(1, 2))
    lanes = np.bitwise_xor.reduce(values, axis=1)
    payload = _payload_from_codes(lanes, candidate)
    payload[~valid] = 0.0
    return payload, valid


def _reader_payload_at_centers(
    shares: np.ndarray,
    active: np.ndarray,
    centers: np.ndarray,
    candidate: dict[str, Any],
    extent: int,
    hops: int,
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    origins = ar.texture_seed_origins(centers, extent, int(candidate["seed_radius"]))
    raw, occupied, trace = ar.propagate_share_channels(shares, active, origins, extent, hops)
    index = np.arange(len(centers))
    local_values = np.rint(raw[index, centers[:, 0], centers[:, 1]]).astype(np.uint8) & np.uint8(15)
    local_active = occupied[index, centers[:, 0], centers[:, 1]]
    complete = np.all(local_active, axis=(1, 2))
    lanes = np.bitwise_xor.reduce(local_values, axis=1)
    payload = _payload_from_codes(lanes, candidate)
    payload[~complete] = 0.0
    return payload, complete, trace


def _carrier_diagnostics(
    shares: np.ndarray,
    active: np.ndarray,
    candidate: dict[str, Any],
    replicates: int,
    seed: int,
    splits: int,
) -> dict[str, Any]:
    payload, valid = _joint_payload(shares, active, candidate)
    joint = sy.heldout_lineage_diagnostics(payload, replicates, seed, splits)
    subset_accuracies: list[float] = []
    for size in range(1, int(candidate["seed_count"])):
        for subset in combinations(range(int(candidate["seed_count"])), size):
            feature = np.asarray(shares[:, subset, :], dtype=np.float32).reshape(len(shares), -1) / 15.0
            diagnostic = sy.heldout_lineage_diagnostics(
                feature,
                replicates,
                ar._hash_seed(seed, "proper-subset", subset),
                splits,
            )
            subset_accuracies.append(float(diagnostic["balanced_accuracy"]))
    return {
        "joint_balanced_accuracy": float(joint["balanced_accuracy"]),
        "joint_valid_fraction": float(np.mean(valid)),
        "proper_subset_balanced_accuracies": subset_accuracies,
        "proper_subset_max_balanced_accuracy": float(max(subset_accuracies, default=1.0)),
    }


def _base_candidate(frontend: dict[str, Any], scaffold: dict[str, Any]) -> dict[str, Any]:
    codec = _frontend_codec(frontend)
    rank = int(codec["rank"])
    return {
        "rank": rank,
        "bits": int(frontend["bits"]),
        "payload_bits": rank * int(frontend["bits"]),
        "codec_model": codec,
        "writer_encoder_kind": str(frontend["kind"]),
        "agc_threshold": float(frontend.get("agc_threshold", 0.0)),
        "read_strength": 0.90,
        "read_sweeps": int(frontend["read_sweeps"]),
        "clearance_updates": int(frontend["clearance_updates"]),
        "trace_sweeps": int(frontend["trace_sweeps"]),
        "seed_count": 4,
        "seed_radius": 3,
        "germination_hops": 3,
        "share_scheme": "xor-kofk",
        "joint_read_required": True,
        "ecc": "hamming84-per-nibble",
        "statistical_candidate": scaffold,
        "frontend_id": str(frontend["frontend_id"]),
    }


def build_phenotype_bridge_candidates(
    frontends: Sequence[dict[str, Any]],
    stage6br_root: Path = ar.DEFAULT_STAGE6BR_ROOT,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the frozen 26-cell nested claim ladder and three anchors."""

    if len(frontends) != 2:
        raise ValueError("Stage-6E requires exactly two sealed frontends")
    stage6d_candidates, _ = cr.build_consumptive_candidates(stage6br_root)
    scaffold = stage6d_candidates[0]["statistical_candidate"]
    rows: list[dict[str, Any]] = []
    for frontend in frontends:
        base = _base_candidate(frontend, scaffold)
        suffix = str(frontend["frontend_id"])
        rows.append(
            base
            | {
                "candidate_id": f"bridge-timing-{suffix}",
                "mechanism": "timing-only",
                "claim_tier": "strict",
                "hysteresis": 0.0,
                "somatic_architecture": "none",
                "somatic_retention": 0.0,
                "somatic_bias": 0.0,
                "promotable": True,
            }
        )
        for persistence in (0.25, 0.50, 0.75, 0.90):
            rows.append(
                base
                | {
                    "candidate_id": f"bridge-h{int(persistence * 100):02d}-{suffix}",
                    "mechanism": "visible-hysteresis",
                    "claim_tier": "strict",
                    "hysteresis": persistence,
                    "somatic_architecture": "none",
                    "somatic_retention": 0.0,
                    "somatic_bias": 0.0,
                    "promotable": True,
                }
            )
    best = _base_candidate(frontends[0], scaffold)
    for architecture in ("local-latch", "diffusing-phase"):
        for retention in (0.75, 0.95):
            for bias in (0.40, 0.80):
                for tier in ("strict", "broad"):
                    rows.append(
                        best
                        | {
                            "candidate_id": (
                                f"bridge-soma-{architecture}-r{int(retention * 100):02d}-"
                                f"b{int(bias * 100):02d}-{tier}"
                            ),
                            "mechanism": "somatic-field",
                            "claim_tier": tier,
                            "hysteresis": 0.0,
                            "somatic_architecture": architecture,
                            "somatic_retention": retention,
                            "somatic_bias": bias,
                            "promotable": True,
                        }
                    )
    if len(rows) != 26:
        raise AssertionError("Stage-6E promotable grid must contain 26 designs")
    legacy_frontend = {
        "frontend_id": "legacy-q4-d40-c05-t08",
        "encoder_id": "texture-walsh-r16-q04",
        "kind": "legacy-q4",
        "bits": 4,
        "scale": [1.0] * 16,
        "read_sweeps": 40,
        "clearance_updates": 5,
        "trace_sweeps": 8,
    }
    legacy = _base_candidate(legacy_frontend, scaffold)
    anchors = [
        legacy
        | {
            "candidate_id": "anchor-stage6d-strict",
            "mechanism": "timing-only",
            "claim_tier": "strict",
            "hysteresis": 0.0,
            "somatic_architecture": "none",
            "somatic_retention": 0.0,
            "somatic_bias": 0.0,
            "promotable": False,
        },
        legacy
        | {
            "candidate_id": "anchor-legacy-no-erasure",
            "mechanism": "legacy-no-erasure",
            "claim_tier": "control",
            "hysteresis": 0.0,
            "somatic_architecture": "none",
            "somatic_retention": 0.0,
            "somatic_bias": 0.0,
            "force_no_erasure": True,
            "promotable": False,
        },
        best
        | {
            "candidate_id": "anchor-direct-somatic-read",
            "mechanism": "somatic-field",
            "claim_tier": "ceiling",
            "hysteresis": 0.0,
            "somatic_architecture": "local-latch",
            "somatic_retention": 0.95,
            "somatic_bias": 0.80,
            "writer_source": "somatic",
            "promotable": False,
        },
    ]
    return rows, anchors


def build_writeback_candidates(
    specs: Sequence[dict[str, Any]],
    stage6br_root: Path = ar.DEFAULT_STAGE6BR_ROOT,
    *,
    maximum_candidates: int = 12,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Materialize a sealed Stage-6F writer registry.

    Specs are JSON-safe and contain a frozen frontend plus mechanism fields.
    Runtime models are rebuilt here so codec arrays and the frozen statistical
    scaffold never need to be serialized or fitted after screening begins.
    """

    if maximum_candidates < 1 or maximum_candidates > 24:
        raise ValueError("writer registry maximum must be between one and twenty-four")
    if not specs or len(specs) > maximum_candidates:
        raise ValueError(
            f"writer registry seals between one and {maximum_candidates} writers"
        )
    stage6d_candidates, _ = cr.build_consumptive_candidates(stage6br_root)
    scaffold = stage6d_candidates[0]["statistical_candidate"]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in specs:
        spec = dict(raw)
        frontend = dict(spec.pop("frontend"))
        candidate_id = str(spec.get("candidate_id", ""))
        if not candidate_id or candidate_id in seen:
            raise ValueError("Stage-6F candidate identifiers must be unique and non-empty")
        seen.add(candidate_id)
        tier = str(spec.get("claim_tier"))
        writer_source = str(spec.get("writer_source", "visible"))
        if tier not in ("strict", "broad"):
            raise ValueError("Stage-6F candidates use strict or broad claim tiers")
        if tier == "strict" and writer_source != "visible":
            raise ValueError("strict Stage-6F writers may observe visible cells only")
        base = _base_candidate(frontend, scaffold)
        row = base | {
            "mechanism": "timing-only" if tier == "strict" else "somatic-field",
            "hysteresis": 0.0,
            "somatic_architecture": "none" if tier == "strict" else "multi-timescale-ema",
            "somatic_retention": 0.0 if tier == "strict" else 0.90,
            "somatic_bias": 0.0 if tier == "strict" else 0.60,
            "somatic_channels": 1 if tier == "strict" else 4,
            "somatic_readout": "mean",
            "writer_source": writer_source,
            "writer_feature": "mean",
            "writer_input_contract": (
                "field-readable" if writer_source == "somatic" else "visible-only"
            ),
            "promotable": True,
        } | spec
        transform = row.get("writer_transform")
        training_mode = str(
            row.get(
                "training_mode",
                "rulebook-assisted" if transform else "label-free",
            )
        )
        if training_mode not in (
            "label-free",
            "rulebook-assisted",
            "teacher-assisted-control",
        ):
            raise ValueError(f"unknown writer training mode {training_mode!r}")
        if transform:
            kind = str(transform.get("kind", "linear"))
            frozen_kinds = {
                "linear",
                "rff-linear",
                "equivariant-linear",
                "mixture-linear",
            }
            if kind in frozen_kinds and not bool(transform.get("model_frozen", False)):
                raise ValueError("writer translators must be frozen before screening")
            if kind in ("target-ceiling", "hybrid-ceiling") and bool(
                row.get("promotable", True)
            ):
                raise ValueError("target-exposed writer ceilings cannot be promotable")
            if kind not in (*frozen_kinds, "target-ceiling", "hybrid-ceiling"):
                raise ValueError(f"unknown writer transform {kind!r}")
        if training_mode == "rulebook-assisted" and not transform:
            raise ValueError("rulebook-assisted candidates require a frozen transform")
        row["training_mode"] = training_mode
        rows.append(row)

    first = rows[0]
    anchor_frontend = dict(specs[0]["frontend"])
    anchor = _base_candidate(anchor_frontend, scaffold)
    anchors = [
        anchor
        | {
            "candidate_id": "stage6f-anchor-no-erasure",
            "mechanism": "legacy-no-erasure",
            "claim_tier": "control",
            "hysteresis": 0.0,
            "somatic_architecture": "none",
            "somatic_retention": 0.0,
            "somatic_bias": 0.0,
            "writer_source": "visible",
            "writer_feature": "mean",
            "writer_input_contract": "visible-only",
            "force_no_erasure": True,
            "promotable": False,
        },
        first
        | {
            "candidate_id": "stage6f-anchor-stopped-write",
            "claim_tier": "control",
            "promotable": False,
        },
    ]
    return rows, anchors


def _candidate_public(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in candidate.items()
        if key not in {"codec_model", "statistical_candidate"}
    } | {
        "codec_id": candidate["codec_model"]["codec_id"],
        "quantizer_scale": np.asarray(candidate["codec_model"]["quantizer_scale"]).tolist(),
        "statistical_scaffold_id": candidate["statistical_candidate"]["candidate_id"],
    }


def _destroy_carrier(shares: np.ndarray, active: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.zeros_like(shares, dtype=np.uint8), np.zeros_like(active, dtype=np.bool_)


def _somatic_retention_schedule(retention: float, channels: int) -> np.ndarray:
    if channels <= 1:
        return np.asarray([retention], dtype=np.float32)
    lower = max(0.20, float(retention) - 0.35)
    upper = min(0.995, float(retention) + 0.045)
    return np.linspace(lower, upper, channels, dtype=np.float32)


def _collapse_somatic(field: np.ndarray, readout: str = "mean") -> np.ndarray:
    current = np.asarray(field, dtype=np.float32)
    if current.ndim == 3:
        return current
    if current.ndim != 4:
        raise ValueError("somatic field must have sample/channel/spatial axes")
    if readout == "slow":
        return current[:, -1]
    if readout == "alternating":
        weights = np.where(np.arange(current.shape[1]) % 2 == 0, 1.0, -1.0).astype(np.float32)
        weights /= np.float32(max(1.0, np.sum(np.abs(weights))))
        return np.einsum("c,ncyx->nyx", weights, current, optimize=True).astype(np.float32)
    return np.mean(current, axis=1, dtype=np.float32)


def _somatic_observe(
    field: np.ndarray,
    centers: np.ndarray,
    readout: str = "mean",
) -> np.ndarray:
    collapsed = _collapse_somatic(field, readout)
    ys, xs = ar._patch_indices(centers, collapsed.shape[1])
    patches = np.empty((len(collapsed), 4, 4), dtype=np.float32)
    for sample in range(len(collapsed)):
        patches[sample] = collapsed[sample][np.ix_(ys[sample], xs[sample])]
    return patches


def _observe_writer_input(
    state: np.ndarray,
    centers: np.ndarray,
    radius: str | int = "patch",
) -> np.ndarray:
    """Read a registered local writer view without exposing targets or carriers."""

    if radius == "patch":
        return ar.observe_texture(state, centers)
    extent = int(state.shape[1])
    value = int(radius)
    if value < 1 or value > 6:
        raise ValueError("writer observation radius must be patch or an integer in [1, 6]")
    offsets = np.arange(-value, value + 1, dtype=np.int64)
    signed = np.where(np.asarray(state, dtype=np.bool_), 1.0, -1.0).astype(np.float32)
    patches = np.empty(
        (len(signed), 2 * value + 1, 2 * value + 1), dtype=np.float32
    )
    for sample, center in enumerate(np.asarray(centers, dtype=np.int64)):
        ys = (int(center[0]) + offsets) % extent
        xs = (int(center[1]) + offsets) % extent
        patches[sample] = signed[sample][np.ix_(ys, xs)]
    return patches


def _d4_patch(values: np.ndarray, index: int) -> np.ndarray:
    """Apply one registered square symmetry to sample by row by column patches."""

    current = np.asarray(values, dtype=np.float32)
    rotation = int(index) % 4
    reflected = int(index) >= 4
    if reflected:
        current = np.flip(current, axis=-1)
    return np.rot90(current, rotation, axes=(-2, -1)).copy()


def _d4_inverse(values: np.ndarray, index: int) -> np.ndarray:
    current = np.rot90(
        np.asarray(values, dtype=np.float32),
        -(int(index) % 4),
        axes=(-2, -1),
    )
    if int(index) >= 4:
        current = np.flip(current, axis=-1)
    return current.copy()


def _writer_transform_features(
    transform: dict[str, Any],
    writer_feature: np.ndarray,
    trace_stack: np.ndarray,
) -> np.ndarray:
    input_mode = str(transform.get("input_mode", "stack"))
    if input_mode == "stack":
        values = np.moveaxis(np.asarray(trace_stack, dtype=np.float32), 1, 0)
        expected_dimension = int(
            np.asarray(transform.get("input_mean", ()), dtype=np.float32).size
        )
        actual_dimension = int(np.prod(values.shape[1:]))
        if expected_dimension and actual_dimension != expected_dimension:
            temporal_view = str(transform.get("temporal_view", "exact"))
            spatial_dimension = int(np.prod(values.shape[2:]))
            if (
                temporal_view != "tail-trained-window"
                or spatial_dimension <= 0
                or expected_dimension % spatial_dimension
            ):
                return values.reshape(len(values), -1)
            trained_sweeps = expected_dimension // spatial_dimension
            registered_sweeps = int(
                transform.get("trained_trace_sweeps", trained_sweeps)
            )
            if trained_sweeps != registered_sweeps or values.shape[1] < trained_sweeps:
                raise ValueError("writer-transform registered temporal view mismatch")
            values = values[:, -trained_sweeps:]
    elif input_mode == "feature":
        values = np.asarray(writer_feature, dtype=np.float32)
    else:
        raise ValueError(f"unknown writer-transform input mode {input_mode!r}")
    return values.reshape(len(values), -1)


def _transform_writer_proposal(
    candidate: dict[str, Any],
    writer_feature: np.ndarray,
    trace_stack: np.ndarray,
    environment: np.ndarray,
    condition: str,
    generation: int,
    replicates: int,
    contract: PhenotypeBridgeContract,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply a frozen Stage-6G translator and return Walsh carrier coefficients.

    Promotable transforms contain only immutable numeric coefficients learned
    before screening.  The target-exposed branch is accepted solely as an
    explicitly non-promotable downstream ceiling.
    """

    transform = candidate.get("writer_transform")
    if not transform:
        values = np.asarray(writer_feature, dtype=np.float32)
        if values.shape[-2:] != (4, 4):
            raise ValueError("an untransformed writer must emit a 4 by 4 patch")
        return ar.texture_encode(values, int(candidate["rank"])), {
            "kind": "identity",
            "transform_id": "identity",
            "target_space": "visible-patch",
            "input_dimension": int(np.prod(values.shape[1:])),
            "target_exposed": False,
        }

    kind = str(transform.get("kind", "linear"))
    transform_id = str(transform.get("transform_id", kind))
    if kind == "hybrid-ceiling":
        if bool(candidate.get("promotable", True)):
            raise ValueError("hybrid target ceilings cannot be promotable")
        if generation not in {int(value) for value in transform["ceiling_generations"]}:
            fallback_candidate = dict(candidate)
            fallback_candidate["writer_transform"] = dict(transform["fallback"])
            proposal, metadata = _transform_writer_proposal(
                fallback_candidate,
                writer_feature,
                trace_stack,
                environment,
                condition,
                generation,
                replicates,
                contract,
            )
            metadata = dict(metadata)
            metadata["kind"] = "hybrid-ceiling-fallback"
            metadata["transform_id"] = transform_id
            return proposal, metadata
        decoded_patch = np.where(environment, 1.0, -1.0).astype(np.float32)
        input_dimension = 0
        target_exposed = True
        target_space = "visible-bits"
    elif kind == "target-ceiling":
        if bool(candidate.get("promotable", True)):
            raise ValueError("target-exposed writer ceilings cannot be promotable")
        decoded_patch = np.where(environment, 1.0, -1.0).astype(np.float32)
        input_dimension = 0
        target_exposed = True
        target_space = "visible-bits"
    elif kind in (
        "linear",
        "rff-linear",
        "equivariant-linear",
        "mixture-linear",
    ):
        features = _writer_transform_features(transform, writer_feature, trace_stack)
        mean = np.asarray(transform["input_mean"], dtype=np.float32)
        scale = np.asarray(transform["input_scale"], dtype=np.float32)
        if mean.shape != scale.shape or mean.shape != (features.shape[1],):
            raise ValueError("writer-transform normalization shape mismatch")
        normalized = np.divide(
            features - mean,
            scale,
            out=np.zeros_like(features),
            where=scale > np.float32(1e-6),
        )
        feature_permutation: np.ndarray | None = None
        if (
            condition == "translator_weight_shuffle"
            and generation == contract.intervention_generation
        ):
            rng = np.random.default_rng(
                ar._hash_seed(
                    contract.namespace,
                    candidate["candidate_id"],
                    "translator-weight-shuffle",
                )
            )
            feature_permutation = rng.permutation(normalized.shape[1])
            normalized = normalized[:, feature_permutation]
        if kind == "linear":
            weights = np.asarray(transform["weights"], dtype=np.float32)
            bias = np.asarray(transform["bias"], dtype=np.float32)
            if weights.shape != (features.shape[1], 16) or bias.shape != (16,):
                raise ValueError("writer-transform coefficient shape mismatch")
            translated = normalized @ weights + bias
        elif kind == "rff-linear":
            projection = np.asarray(transform["projection"], dtype=np.float32)
            phase = np.asarray(transform["phase"], dtype=np.float32)
            output_weights = np.asarray(transform["output_weights"], dtype=np.float32)
            bias = np.asarray(transform["bias"], dtype=np.float32)
            if projection.shape[0] != features.shape[1] or phase.shape != (
                projection.shape[1],
            ):
                raise ValueError("random-feature projection shape mismatch")
            if output_weights.shape != (projection.shape[1], 16) or bias.shape != (
                16,
            ):
                raise ValueError("random-feature output shape mismatch")
            hidden = np.float32(math.sqrt(2.0 / projection.shape[1])) * np.cos(
                normalized @ projection + phase
            )
            translated = hidden @ output_weights + bias
        elif kind == "mixture-linear":
            centers = np.asarray(transform["gate_centers"], dtype=np.float32)
            expert_weights = np.asarray(transform["expert_weights"], dtype=np.float32)
            expert_bias = np.asarray(transform["expert_bias"], dtype=np.float32)
            if centers.ndim != 2 or centers.shape[1] != features.shape[1]:
                raise ValueError("mixture gate center shape mismatch")
            if expert_weights.shape != (len(centers), features.shape[1], 16):
                raise ValueError("mixture expert weight shape mismatch")
            if expert_bias.shape != (len(centers), 16):
                raise ValueError("mixture expert bias shape mismatch")
            temperature = max(float(transform.get("gate_temperature", 1.0)), 1e-6)
            logits = -np.mean(
                (normalized[:, None, :] - centers[None, :, :]) ** 2,
                axis=2,
            ) / np.float32(temperature)
            logits -= np.max(logits, axis=1, keepdims=True)
            gates = np.exp(logits)
            gates /= np.sum(gates, axis=1, keepdims=True)
            expert_outputs = np.einsum(
                "nd,kdo->nko", normalized, expert_weights, optimize=True
            ) + expert_bias[None]
            translated = np.einsum("nk,nko->no", gates, expert_outputs, optimize=True)
        else:
            if features.shape[1] != 16:
                raise ValueError("equivariant translators require one 4 by 4 feature")
            weights = np.asarray(transform["weights"], dtype=np.float32)
            bias = np.asarray(transform["bias"], dtype=np.float32)
            if weights.shape != (16, 16) or bias.shape != (16,):
                raise ValueError("equivariant coefficient shape mismatch")
            equivariant_features = features
            if feature_permutation is not None:
                equivariant_features = equivariant_features[:, feature_permutation]
            patches = equivariant_features.reshape(-1, 4, 4)
            predictions = []
            for symmetry in range(8):
                transformed = _d4_patch(patches, symmetry).reshape(-1, 16)
                transformed = np.divide(
                    transformed - mean,
                    scale,
                    out=np.zeros_like(transformed),
                    where=scale > np.float32(1e-6),
                )
                predicted = (transformed @ weights + bias).reshape(-1, 4, 4)
                predictions.append(_d4_inverse(predicted, symmetry))
            translated = np.mean(predictions, axis=0, dtype=np.float32).reshape(-1, 16)
        target_space = str(transform.get("target_space", "visible-bits"))
        if target_space == "visible-bits":
            decoded_patch = np.clip(translated, -1.0, 1.0).reshape(-1, 4, 4)
        elif target_space == "walsh-coefficients":
            decoded_patch = ar.texture_decode(translated, 16)
        else:
            raise ValueError(f"unknown writer-transform target space {target_space!r}")
        input_dimension = int(features.shape[1])
        target_exposed = False
    else:
        raise ValueError(f"unknown writer-transform kind {kind!r}")

    if condition == "translator_ablation" and generation == contract.intervention_generation:
        decoded_patch = np.zeros_like(decoded_patch)
    elif (
        condition == "translator_bit_permutation"
        and generation == contract.intervention_generation
    ):
        permutation = np.random.default_rng(
            ar._hash_seed(
                contract.namespace,
                candidate["candidate_id"],
                "translator-bit-permutation",
            )
        ).permutation(16)
        decoded_patch = decoded_patch.reshape(len(decoded_patch), 16)[:, permutation].reshape(
            -1, 4, 4
        )
    elif (
        condition == "translator_history_shuffle"
        and generation == contract.intervention_generation
    ):
        decoded_patch = ar._swap_histories(decoded_patch, replicates)

    return ar.texture_encode(decoded_patch, int(candidate["rank"])), {
        "kind": kind,
        "transform_id": transform_id,
        "target_space": target_space,
        "input_dimension": input_dimension,
        "temporal_view": str(transform.get("temporal_view", "exact")),
        "target_exposed": target_exposed,
        "decoded_patch_mean_abs": float(np.mean(np.abs(decoded_patch))),
    }


def _somatic_write(
    field: np.ndarray,
    state: np.ndarray,
    centers: np.ndarray,
    retention: float,
    architecture: str,
    previous_state: np.ndarray | None = None,
) -> np.ndarray:
    current = np.asarray(field, dtype=np.float32)
    if current.ndim == 3:
        current = current[:, None]
    channels = current.shape[1]
    schedule = _somatic_retention_schedule(retention, channels)[None, :, None, None]
    if architecture in ("diffusing-phase", "local-reservoir"):
        carried = (
            np.float32(0.5) * current
            + np.float32(0.125) * np.roll(current, 1, axis=2)
            + np.float32(0.125) * np.roll(current, -1, axis=2)
            + np.float32(0.125) * np.roll(current, 1, axis=3)
            + np.float32(0.125) * np.roll(current, -1, axis=3)
        )
        if architecture == "local-reservoir" and channels > 1:
            carried = np.tanh(
                carried
                + np.float32(0.18) * np.roll(current, 1, axis=1)
                - np.float32(0.11) * np.roll(current, -1, axis=1)
            ).astype(np.float32)
    elif architecture in (
        "local-latch",
        "multi-timescale-ema",
        "transition-eligibility",
    ):
        carried = current.copy()
    else:
        return np.zeros_like(current)
    result = schedule * carried
    observed = ar.observe_texture(state, centers)
    transitioned = None
    if previous_state is not None:
        previous = ar.observe_texture(previous_state, centers)
        transitioned = np.where(observed != previous, observed, 0.0).astype(np.float32)
    ys, xs = ar._patch_indices(centers, state.shape[1])
    for sample in range(len(result)):
        for channel in range(channels):
            local = result[sample, channel][np.ix_(ys[sample], xs[sample])]
            source = observed[sample]
            if architecture == "transition-eligibility" and transitioned is not None and channel % 2:
                source = transitioned[sample]
            if architecture == "local-reservoir":
                source = np.float32(1.0 if channel % 2 == 0 else -0.75) * source
            result[sample, channel][np.ix_(ys[sample], xs[sample])] = (
                local + np.float32(1.0 - schedule[0, channel, 0, 0]) * source
            )
    return np.clip(result, -1.0, 1.0).astype(np.float32)


def _somatic_decay(field: np.ndarray, retention: float, architecture: str) -> np.ndarray:
    current = np.asarray(field, dtype=np.float32)
    if current.ndim == 3:
        current = current[:, None]
    if architecture in ("diffusing-phase", "local-reservoir"):
        current = (
            np.float32(0.5) * current
            + np.float32(0.125) * np.roll(current, 1, axis=2)
            + np.float32(0.125) * np.roll(current, -1, axis=2)
            + np.float32(0.125) * np.roll(current, 1, axis=3)
            + np.float32(0.125) * np.roll(current, -1, axis=3)
        )
        if architecture == "local-reservoir" and current.shape[1] > 1:
            current = np.tanh(
                current
                + np.float32(0.18) * np.roll(current, 1, axis=1)
                - np.float32(0.11) * np.roll(current, -1, axis=1)
            ).astype(np.float32)
    schedule = _somatic_retention_schedule(retention, current.shape[1])[None, :, None, None]
    return (schedule * current).astype(np.float32)


def _apply_somatic_bias(
    predicted: np.ndarray,
    field: np.ndarray,
    uniforms: np.ndarray,
    strength: float,
    readout: str = "mean",
) -> np.ndarray:
    result = np.asarray(predicted, dtype=np.bool_).copy()
    collapsed = _collapse_somatic(field, readout)
    magnitude = np.clip(np.abs(collapsed) * np.float32(strength), 0.0, 1.0)
    return np.where(np.asarray(uniforms) < magnitude, collapsed >= 0.0, result)


def _set_somatic_patch(
    field: np.ndarray,
    centers: np.ndarray,
    environment: np.ndarray,
    opposite: bool = False,
) -> None:
    if field.ndim == 3:
        field_view = field[:, None]
    else:
        field_view = field
    values = np.where(environment, 1.0, -1.0).astype(np.float32)
    if opposite:
        values = -values
    ys, xs = ar._patch_indices(centers, field_view.shape[2])
    for sample in range(len(field_view)):
        for channel in range(field_view.shape[1]):
            field_view[sample, channel][np.ix_(ys[sample], xs[sample])] = values[sample]


def _set_field_patch(
    field: np.ndarray,
    centers: np.ndarray,
    patches: np.ndarray,
) -> None:
    """Install reconstructed signed patches without exposing a target label."""

    field_view = field[:, None] if field.ndim == 3 else field
    values = np.asarray(patches, dtype=np.float32)
    if values.ndim == 3:
        values = values[:, None]
    if values.ndim != 4 or values.shape[1] not in (1, field_view.shape[1]):
        raise ValueError("field patches must be sample-by-channel-by-4-by-4")
    ys, xs = ar._patch_indices(centers, field_view.shape[2])
    for sample in range(len(field_view)):
        for channel in range(field_view.shape[1]):
            source_channel = 0 if values.shape[1] == 1 else channel
            field_view[sample, channel][np.ix_(ys[sample], xs[sample])] = values[
                sample, source_channel
            ]


def _field_observe_channels(field: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """Observe every signed field channel without collapsing hidden state."""

    values = np.asarray(field, dtype=np.float32)
    if values.ndim == 3:
        values = values[:, None]
    ys, xs = ar._patch_indices(centers, values.shape[2])
    result = np.empty((len(values), values.shape[1], 4, 4), dtype=np.float32)
    for sample in range(len(values)):
        for channel in range(values.shape[1]):
            result[sample, channel] = values[sample, channel][
                np.ix_(ys[sample], xs[sample])
            ]
    return result


def _adaptive_handoff_update(
    daughter_field: np.ndarray,
    adapter: np.ndarray,
    state: np.ndarray,
    previous_state: np.ndarray,
    centers: np.ndarray,
    candidate: dict[str, Any],
    history: Sequence[np.ndarray] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Locally distil visible spacetime into a zero-born outgoing field.

    The parent field is deliberately absent from this interface.  Channel zero
    observes visible form and channel one observes directed transitions.  The
    adapter is transient and is never encoded across a reproductive boundary.
    """

    closure_model = candidate.get("closure_model")
    if closure_model is not None:
        if not bool(closure_model.get("model_frozen", False)):
            raise ValueError("a runtime closure model must be frozen")
        if bool(closure_model.get("runtime_target_labels", False)):
            raise ValueError("a promotable closure model cannot expose runtime targets")
        states = list(history or (previous_state, state))
        predicted = _closure_model_predict(states, centers, closure_model)
        adapter_patches = _field_observe_channels(adapter, centers)
        retention = np.float32(candidate.get("adapter_retention", 0.80))
        learning_rate = np.float32(candidate.get("adapter_learning_rate", 0.35))
        proposal = np.clip(
            retention * adapter_patches + learning_rate * predicted,
            -1.0,
            1.0,
        ).astype(np.float32)
        confidence = np.mean(np.abs(predicted), axis=(1, 2, 3))
        threshold = float(closure_model.get("confidence_threshold", 0.0))
        event_mask = confidence >= threshold
        updated_adapter = np.where(
            event_mask[:, None, None, None], proposal, adapter_patches
        ).astype(np.float32)
        _set_field_patch(adapter, centers, updated_adapter)
        daughter_patches = _field_observe_channels(daughter_field, centers)
        write_rate = np.float32(candidate.get("daughter_write_rate", 0.35))
        write_proposal = np.clip(
            (np.float32(1.0) - write_rate) * daughter_patches
            + write_rate * updated_adapter,
            -1.0,
            1.0,
        ).astype(np.float32)
        written = np.where(
            event_mask[:, None, None, None], write_proposal, daughter_patches
        ).astype(np.float32)
        _set_field_patch(daughter_field, centers, written)
        return (
            daughter_field,
            adapter,
            event_mask,
        )

    current = np.where(
        ar.observe_texture(state, centers) >= 0.0, 1.0, -1.0
    ).astype(np.float32)
    previous = np.where(
        ar.observe_texture(previous_state, centers) >= 0.0, 1.0, -1.0
    ).astype(np.float32)
    transition = np.where(current != previous, current, 0.0).astype(np.float32)
    channels = int(candidate.get("field_channels", 1))
    sources = np.stack((current, transition), axis=1)
    if channels == 1:
        sources = sources[:, :1]
    elif channels != 2:
        raise ValueError("adaptive handoff supports one or two field channels")

    architecture = str(candidate.get("adaptive_architecture", "phase-latch-distiller"))
    learning_rate = np.float32(candidate.get("adapter_learning_rate", 0.35))
    retention = np.float32(candidate.get("adapter_retention", 0.80))
    adapter_patches = _field_observe_channels(adapter, centers)
    if architecture == "phase-latch-distiller":
        updated_adapter = retention * adapter_patches + learning_rate * sources * (
            np.float32(1.0) - np.square(adapter_patches)
        )
        event_mask = np.ones((len(sources),), dtype=np.bool_)
    elif architecture == "dual-timescale-predictive-reservoir":
        coupled = sources.copy()
        if channels == 2:
            coupled[:, 0] += np.float32(0.20) * adapter_patches[:, 1]
            coupled[:, 1] -= np.float32(0.12) * adapter_patches[:, 0]
        updated_adapter = np.tanh(
            retention * adapter_patches + learning_rate * coupled
        ).astype(np.float32)
        event_mask = np.ones((len(sources),), dtype=np.bool_)
    elif architecture == "event-canonicalized-eligibility":
        coherence = np.mean(np.abs(transition), axis=(1, 2))
        threshold = float(candidate.get("event_threshold", 0.20))
        event_mask = coherence >= threshold
        proposal = retention * adapter_patches + learning_rate * sources
        updated_adapter = np.where(
            event_mask[:, None, None, None],
            proposal,
            retention * adapter_patches,
        )
    else:
        raise ValueError(f"unknown adaptive handoff architecture {architecture!r}")

    updated_adapter = np.clip(updated_adapter, -1.0, 1.0).astype(np.float32)
    _set_field_patch(adapter, centers, updated_adapter)
    daughter_patches = _field_observe_channels(daughter_field, centers)
    write_rate = np.float32(candidate.get("daughter_write_rate", 0.35))
    written = np.clip(
        (np.float32(1.0) - write_rate) * daughter_patches
        + write_rate * updated_adapter,
        -1.0,
        1.0,
    ).astype(np.float32)
    _set_field_patch(daughter_field, centers, written)
    return daughter_field, adapter, event_mask


def _closure_local_features(
    history: Sequence[np.ndarray],
    centers: np.ndarray,
    radius: int,
    window: int,
    canonicalize: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Summarize a local visible spacetime window for a frozen writer.

    Only visible Boolean states and local centres enter this function.  The
    inherited field, target history, labels, pair identity, and generation
    index are deliberately absent.  Four spatial blocks retain the current
    form, temporal mean, signed displacement, and local activity.
    """

    if radius not in (2, 4, 6):
        raise ValueError("closure writer radius must be 2, 4, or 6")
    if window not in (8, 16, 32):
        raise ValueError("closure writer window must be 8, 16, or 32")
    if not history:
        raise ValueError("closure writer needs at least one visible state")
    selected = list(history)[-window:]
    while len(selected) < window:
        selected.insert(0, selected[0])
    extent = int(np.asarray(selected[-1]).shape[1])
    offsets = np.arange(-radius, radius + 1, dtype=np.int64)
    centers_array = np.asarray(centers, dtype=np.int64)
    local = np.empty(
        (window, len(centers_array), 2 * radius + 1, 2 * radius + 1),
        dtype=np.float32,
    )
    for time_index, state_value in enumerate(selected):
        signed = np.where(np.asarray(state_value, dtype=np.bool_), 1.0, -1.0).astype(
            np.float32
        )
        for sample, center in enumerate(centers_array):
            ys = (int(center[0]) + offsets) % extent
            xs = (int(center[1]) + offsets) % extent
            local[time_index, sample] = signed[sample][np.ix_(ys, xs)]
    current = local[-1]
    temporal_mean = np.mean(local, axis=0, dtype=np.float32)
    displacement = np.float32(0.5) * (local[-1] - local[0])
    if window > 1:
        activity = np.mean(
            np.float32(0.5) * np.abs(np.diff(local, axis=0)),
            axis=0,
            dtype=np.float32,
        )
    else:  # pragma: no cover - registered windows are longer than one
        activity = np.zeros_like(current)
    blocks = np.stack((current, temporal_mean, displacement, activity), axis=1)
    orientations = np.zeros(len(centers_array), dtype=np.int8)
    if canonicalize:
        for sample in range(len(blocks)):
            candidates = [
                _d4_patch(blocks[sample], symmetry) for symmetry in range(8)
            ]
            # Lexicographic canonicalization is deterministic even for tied
            # symmetric states; the symmetry index is the final tie-break.
            keys = [
                tuple(np.round(value, 6).reshape(-1).tolist()) + (symmetry,)
                for symmetry, value in enumerate(candidates)
            ]
            orientation = min(range(8), key=lambda index: keys[index])
            orientations[sample] = orientation
            blocks[sample] = candidates[orientation]
    flattened = blocks.reshape(len(blocks), -1)
    bias = np.ones((len(blocks), 1), dtype=np.float32)
    return np.concatenate((flattened, bias), axis=1), orientations


def _closure_transform_targets(
    targets: np.ndarray,
    orientations: np.ndarray,
) -> np.ndarray:
    """Map two-channel 4-by-4 targets into their canonical frames."""

    values = np.asarray(targets, dtype=np.float32)
    if values.ndim != 4 or values.shape[1:] != (2, 4, 4):
        raise ValueError("closure targets must be sample-by-2-by-4-by-4")
    result = np.empty_like(values)
    for sample, orientation in enumerate(np.asarray(orientations, dtype=np.int8)):
        result[sample] = _d4_patch(values[sample], int(orientation))
    return result


def _closure_model_predict(
    history: Sequence[np.ndarray],
    centers: np.ndarray,
    model: dict[str, Any],
) -> np.ndarray:
    """Evaluate a sealed local writer and return two signed field patches."""

    features, orientations = _closure_local_features(
        history,
        centers,
        int(model["radius"]),
        int(model["window"]),
        bool(model["canonicalize"]),
    )
    mean = np.asarray(model["input_mean"], dtype=np.float32)
    scale = np.asarray(model["input_scale"], dtype=np.float32)
    if mean.shape != (features.shape[1],) or scale.shape != mean.shape:
        raise ValueError("closure normalization shape mismatch")
    normalized = np.divide(
        features - mean,
        scale,
        out=np.zeros_like(features),
        where=scale > np.float32(1e-6),
    )
    kind = str(model["kind"])
    design = normalized
    if kind in ("sketched-ridge", "rff", "local-reservoir"):
        projection = np.asarray(model["projection"], dtype=np.float32)
        phase = np.asarray(model["projection_phase"], dtype=np.float32)
        if projection.shape[0] != normalized.shape[1] or phase.shape != (
            projection.shape[1],
        ):
            raise ValueError("closure projection shape mismatch")
        projected = normalized @ projection + phase
        if kind == "sketched-ridge":
            design = projected.astype(np.float32)
        elif kind == "rff":
            design = np.float32(math.sqrt(2.0 / projection.shape[1])) * np.cos(
                projected
            )
        else:
            design = np.tanh(projected).astype(np.float32)
    elif kind != "equivariant-ridge":
        raise ValueError(f"unknown closure writer kind {kind!r}")
    weights = np.asarray(model["weights"], dtype=np.float32)
    bias = np.asarray(model["bias"], dtype=np.float32)
    if str(model.get("latent_kind", "")) == "codebook":
        codebook = np.asarray(model.get("latent_codebook"), dtype=np.float32)
        if (
            codebook.ndim != 2
            or codebook.shape[1] != 32
            or weights.shape != (design.shape[1], len(codebook))
            or bias.shape != (len(codebook),)
        ):
            raise ValueError("closure latent codebook shape mismatch")
        logits = design @ weights + bias
        raw_output = codebook[np.argmax(logits, axis=1)]
    else:
        if weights.shape != (design.shape[1], 32) or bias.shape != (32,):
            raise ValueError("closure output shape mismatch")
        raw_output = design @ weights + bias
    raw_output = np.clip(raw_output, -1.0, 1.0)
    if str(model.get("output_space", "signed-patches")) == "q4-coefficients":
        rank = int(model.get("output_rank", 16))
        if rank != 16 or raw_output.shape[1] != 2 * rank:
            raise ValueError("closure q4 coefficient output must contain two rank-16 channels")
        canonical = np.stack(
            (
                ar.texture_decode(raw_output[:, :rank], rank),
                ar.texture_decode(raw_output[:, rank:], rank),
            ),
            axis=1,
        )
    else:
        canonical = raw_output.reshape(-1, 2, 4, 4)
    result = np.empty_like(canonical)
    for sample, orientation in enumerate(orientations):
        result[sample] = _d4_inverse(canonical[sample], int(orientation))
    return result.astype(np.float32)


def _compact_model_code(
    history: Sequence[np.ndarray],
    centers: np.ndarray,
    model: dict[str, Any],
) -> np.ndarray:
    """Predict a compact signed carrier from local visible spacetime only."""

    features, _ = _closure_local_features(
        history,
        centers,
        int(model["radius"]),
        int(model["window"]),
        bool(model.get("canonicalize", False)),
    )
    mean = np.asarray(model["input_mean"], dtype=np.float32)
    scale = np.asarray(model["input_scale"], dtype=np.float32)
    if mean.shape != (features.shape[1],) or scale.shape != mean.shape:
        raise ValueError("compact writer normalization shape mismatch")
    design = np.divide(
        features - mean,
        scale,
        out=np.zeros_like(features),
        where=scale > np.float32(1e-6),
    )
    if "projection" in model:
        projection = np.asarray(model["projection"], dtype=np.float32)
        if projection.shape[0] != design.shape[1]:
            raise ValueError("compact writer projection shape mismatch")
        design = design @ projection
    weights = np.asarray(model["latent_weights"], dtype=np.float32)
    bias = np.asarray(model["latent_bias"], dtype=np.float32)
    latent_size = int(model["latent_size"])
    if weights.shape != (design.shape[1], latent_size) or bias.shape != (
        latent_size,
    ):
        raise ValueError("compact writer output shape mismatch")
    return np.clip(design @ weights + bias, -1.0, 1.0).astype(np.float32)


def _compact_decode_field(code: np.ndarray, model: dict[str, Any]) -> np.ndarray:
    """Decode normalized compact values into the established two-channel field."""

    values = np.asarray(code, dtype=np.float32)
    latent_size = int(model["latent_size"])
    if values.ndim != 2 or values.shape[1] != latent_size:
        raise ValueError("compact carrier shape mismatch")
    decoder = np.asarray(model["latent_decoder"], dtype=np.float32)
    target_mean = np.asarray(model["latent_target_mean"], dtype=np.float32)
    latent_scale = np.asarray(model["latent_scale"], dtype=np.float32)
    if decoder.shape != (latent_size, 32):
        raise ValueError("compact decoder must reconstruct 32 field coefficients")
    if target_mean.shape != (32,) or latent_scale.shape != (latent_size,):
        raise ValueError("compact decoder normalization shape mismatch")
    coefficients = (
        (np.clip(values, -1.0, 1.0) * latent_scale) @ decoder + target_mean
    )
    coefficients = np.clip(coefficients, -1.0, 1.0).astype(np.float32)
    return np.stack(
        (
            ar.texture_decode(coefficients[:, :16], 16),
            ar.texture_decode(coefficients[:, 16:], 16),
        ),
        axis=1,
    ).astype(np.float32)


def _compact_oracle_code(
    environment: np.ndarray, model: dict[str, Any]
) -> np.ndarray:
    """Non-promotable exact code for causal controllability calibration."""

    target = np.where(environment, 1.0, -1.0).astype(np.float32)
    coefficients = np.concatenate(
        (
            ar.texture_encode(target, 16),
            np.zeros((len(target), 16), dtype=np.float32),
        ),
        axis=1,
    )
    decoder = np.asarray(model["latent_decoder"], dtype=np.float32)
    target_mean = np.asarray(model["latent_target_mean"], dtype=np.float32)
    latent_scale = np.asarray(model["latent_scale"], dtype=np.float32)
    raw = (coefficients - target_mean) @ decoder.T
    return np.clip(
        np.divide(
            raw,
            latent_scale,
            out=np.zeros_like(raw),
            where=latent_scale > np.float32(1e-6),
        ),
        -1.0,
        1.0,
    ).astype(np.float32)


def _compact_attractor_update(
    current: np.ndarray, predicted: np.ndarray, model: dict[str, Any]
) -> np.ndarray:
    """Update the zero-born outgoing compact state with a registered dynamic."""

    state = np.asarray(current, dtype=np.float32)
    proposal = np.asarray(predicted, dtype=np.float32)
    if state.shape != proposal.shape:
        raise ValueError("compact attractor state/prediction shape mismatch")
    kind = str(model.get("attractor_kind", "leaky"))
    retention = np.float32(model.get("attractor_retention", 0.65))
    if kind == "leaky":
        updated = retention * state + (np.float32(1.0) - retention) * proposal
    elif kind == "contractive-tanh":
        recurrent = np.float32(model.get("recurrent_gain", 0.55))
        # Express the recurrence around the visible prediction so the clean
        # code is a fixed point and perturbations shrink monotonically.
        updated = proposal + recurrent * np.tanh(state - proposal)
    elif kind == "prototype":
        prototypes = np.asarray(model.get("latent_prototypes"), dtype=np.float32)
        if prototypes.ndim != 2 or prototypes.shape[1] != state.shape[1]:
            raise ValueError("compact prototype attractor shape mismatch")
        blended = retention * state + (np.float32(1.0) - retention) * proposal
        nearest = prototypes[
            np.argmin(np.sum((blended[:, None] - prototypes[None]) ** 2, axis=2), axis=1)
        ]
        strength = np.float32(model.get("prototype_strength", 0.35))
        updated = (np.float32(1.0) - strength) * blended + strength * nearest
    else:
        raise ValueError(f"unknown compact attractor kind {kind!r}")
    return np.clip(updated, -1.0, 1.0).astype(np.float32)


def _closure_oracle_patches(
    environment: np.ndarray,
    mode: str,
    pair_id: str,
    generation: int,
    sweep: int,
    contract: "PhenotypeBridgeContract",
) -> np.ndarray:
    """Create a non-promotable diagnostic field with explicit target access."""

    target = np.where(environment, 1.0, -1.0).astype(np.float32)
    if mode == "opposite":
        target = -target
    elif mode == "random":
        random = np.random.default_rng(
            ar._hash_seed(
                contract.namespace,
                pair_id,
                "closure-oracle-random",
                generation,
                sweep,
            )
        )
        target = np.where(random.random(target.shape) < 0.5, 1.0, -1.0).astype(
            np.float32
        )
    elif mode != "target":
        raise ValueError(f"unknown closure oracle mode {mode!r}")
    return np.stack((target, np.zeros_like(target)), axis=1)


def _field_codec_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Build the independent q4 codec used by the Stage-6I slow field."""

    if bool(candidate.get("compact_latent_carrier", False)):
        model = candidate.get("closure_model") or {}
        rank = int(model.get("latent_size", candidate.get("latent_size", 0)))
        if rank not in (2, 4, 8, 16):
            raise ValueError("compact inherited field rank must be 2, 4, 8, or 16")
        result = dict(candidate)
        result.update(
            {
                "rank": rank,
                "field_base_rank": rank,
                "field_channels": 2,
                "bits": 4,
                "payload_bits": rank * 4,
                "seed_count": 4,
                "writer_encoder_kind": "field-q4",
                "agc_threshold": 0.0,
                "codec_model": {
                    "bits": 4,
                    "rank": rank,
                    "quantizer_scale": np.ones(rank, dtype=np.float32),
                    "basis": np.eye(rank, dtype=np.float32),
                    "codec_id": f"compact-latent-r{rank:02d}-q04",
                },
            }
        )
        return result

    base_rank = int(candidate.get("field_rank", 16))
    if base_rank not in (4, 8, 16):
        raise ValueError("inherited field rank must be 4, 8, or 16")
    channels = int(candidate.get("field_channels", 1))
    if channels not in (1, 2):
        raise ValueError("inherited field uses one or two channels")
    rank = base_rank * channels
    result = dict(candidate)
    result.update(
        {
            "rank": rank,
            "field_base_rank": base_rank,
            "field_channels": channels,
            "bits": 4,
            "payload_bits": rank * 4,
            "seed_count": 4,
            "writer_encoder_kind": "field-q4",
            "agc_threshold": 0.0,
            "codec_model": {
                "bits": 4,
                "rank": rank,
                "quantizer_scale": np.ones(rank, dtype=np.float32),
                "basis": np.concatenate(
                    [ar.TEXTURE_BASIS[:base_rank].copy() for _ in range(channels)],
                    axis=0,
                ),
                "codec_id": f"slow-field-walsh-c{channels}-r{base_rank:02d}-q04",
            },
        }
    )
    return result


def _apply_visible_stabilizer(
    predicted: np.ndarray,
    current: np.ndarray,
    uniforms: np.ndarray,
    strength: float,
    controller: str,
) -> np.ndarray:
    """A label-blind controller whose only state is the visible lattice."""

    proposal = np.asarray(predicted, dtype=np.bool_)
    state = np.asarray(current, dtype=np.bool_)
    random = np.asarray(uniforms, dtype=np.float64)
    if controller == "hysteresis":
        target = state
        eligible = proposal != state
    else:
        neighbours = np.zeros(state.shape, dtype=np.int16)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                neighbours += np.roll(state, shift=(dy, dx), axis=(1, 2))
        majority = neighbours >= 5
        if controller == "local-basin":
            target = majority
            eligible = proposal != majority
        elif controller == "phase-compensator":
            # Only damp changes on a local interface; stable interiors follow
            # the unmodified CA rule.
            target = state
            eligible = (proposal != state) & (neighbours >= 3) & (neighbours <= 6)
        else:
            raise ValueError(f"unknown visible stabilizer {controller!r}")
    return np.where(eligible & (random < float(strength)), target, proposal)


def _orbit_metrics(
    observed: Sequence[np.ndarray],
    target: Sequence[np.ndarray],
    opposite: Sequence[np.ndarray],
    condition: str,
    seed: int,
) -> dict[str, Any]:
    """Phase-invariant, order-sensitive correct-minus-opposite orbit score."""

    if len(observed) == 0 or len(observed) != len(target) or len(observed) != len(opposite):
        return {
            "window_sweeps": 0,
            "margin_mean": 0.0,
            "direction_a_mean": 0.0,
            "direction_b_mean": 0.0,
            "correct_similarity_mean": 0.0,
            "opposite_similarity_mean": 0.0,
            "best_phase_mean": 0.0,
        }
    actual = np.asarray(observed, dtype=np.float32)
    wanted = np.asarray(target, dtype=np.float32)
    rejected = np.asarray(opposite, dtype=np.float32)
    if condition == "orbit_phase_shift":
        actual = np.roll(actual, max(1, len(actual) // 4), axis=0)
    elif condition == "orbit_temporal_reverse":
        actual = actual[::-1]
    elif condition == "orbit_temporal_shuffle":
        actual = actual[np.random.default_rng(seed).permutation(len(actual))]
    per_phase: list[np.ndarray] = []
    correct_phases: list[np.ndarray] = []
    opposite_phases: list[np.ndarray] = []
    axes = (0, 2, 3)
    for lag in range(len(actual)):
        shifted_wanted = np.roll(wanted, lag, axis=0)
        shifted_rejected = np.roll(rejected, lag, axis=0)
        correct = np.mean(actual * shifted_wanted, axis=axes)
        wrong = np.mean(actual * shifted_rejected, axis=axes)
        correct_phases.append(correct)
        opposite_phases.append(wrong)
        per_phase.append(np.float32(0.5) * (correct - wrong))
    margins = np.stack(per_phase, axis=0)
    best_phase = np.argmax(margins, axis=0)
    index = np.arange(margins.shape[1])
    best = margins[best_phase, index]
    correct_matrix = np.stack(correct_phases, axis=0)
    opposite_matrix = np.stack(opposite_phases, axis=0)
    return {
        "window_sweeps": len(actual),
        "margin_mean": float(np.mean(best)),
        "direction_a_mean": float(np.mean(best[: len(best) // 2])),
        "direction_b_mean": float(np.mean(best[len(best) // 2 :])),
        "correct_similarity_mean": float(
            np.mean(correct_matrix[best_phase, index])
        ),
        "opposite_similarity_mean": float(
            np.mean(opposite_matrix[best_phase, index])
        ),
        "best_phase_mean": float(np.mean(best_phase)),
    }


def _directed_orbit_metrics(
    observed: Sequence[np.ndarray],
    target: Sequence[np.ndarray],
    opposite: Sequence[np.ndarray],
    condition: str,
    seed: int,
) -> dict[str, Any]:
    """Cyclic-phase invariant score that retains the arrow of local time."""

    if len(observed) == 0 or len(observed) != len(target) or len(observed) != len(opposite):
        return {
            "directed_window_sweeps": 0,
            "directed_margin_mean": 0.0,
            "directed_correct_similarity_mean": 0.0,
            "directed_opposite_similarity_mean": 0.0,
            "directed_best_phase_mean": 0.0,
        }
    actual = np.asarray(observed, dtype=np.float32)
    wanted = np.asarray(target, dtype=np.float32)
    rejected = np.asarray(opposite, dtype=np.float32)
    if condition == "orbit_phase_shift":
        actual = np.roll(actual, max(1, len(actual) // 4), axis=0)
    elif condition == "orbit_temporal_reverse":
        actual = actual[::-1]
    elif condition == "orbit_temporal_shuffle":
        actual = actual[np.random.default_rng(seed).permutation(len(actual))]

    actual_delta = np.roll(actual, -1, axis=0) - actual
    margins: list[np.ndarray] = []
    correct_values: list[np.ndarray] = []
    wrong_values: list[np.ndarray] = []
    axes = (0, 2, 3)
    for lag in range(len(actual)):
        shifted_wanted = np.roll(wanted, lag, axis=0)
        shifted_rejected = np.roll(rejected, lag, axis=0)
        wanted_delta = np.roll(shifted_wanted, -1, axis=0) - shifted_wanted
        rejected_delta = np.roll(shifted_rejected, -1, axis=0) - shifted_rejected
        frame_correct = np.mean(actual * shifted_wanted, axis=axes)
        frame_wrong = np.mean(actual * shifted_rejected, axis=axes)
        delta_correct = np.mean(actual_delta * wanted_delta, axis=axes) / np.float32(2.0)
        delta_wrong = np.mean(actual_delta * rejected_delta, axis=axes) / np.float32(2.0)
        correct = np.float32(0.5) * (frame_correct + delta_correct)
        wrong = np.float32(0.5) * (frame_wrong + delta_wrong)
        correct_values.append(correct)
        wrong_values.append(wrong)
        margins.append(np.float32(0.5) * (correct - wrong))
    matrix = np.stack(margins, axis=0)
    best_phase = np.argmax(matrix, axis=0)
    index = np.arange(matrix.shape[1])
    correct_matrix = np.stack(correct_values, axis=0)
    wrong_matrix = np.stack(wrong_values, axis=0)
    return {
        "directed_window_sweeps": len(actual),
        "directed_margin_mean": float(np.mean(matrix[best_phase, index])),
        "directed_correct_similarity_mean": float(
            np.mean(correct_matrix[best_phase, index])
        ),
        "directed_opposite_similarity_mean": float(
            np.mean(wrong_matrix[best_phase, index])
        ),
        "directed_best_phase_mean": float(np.mean(best_phase)),
    }


def _directed_reference_diagnostic(
    target: Sequence[np.ndarray],
    opposite: Sequence[np.ndarray],
    seed: int,
) -> dict[str, Any]:
    """Report whether a reference orbit has a distinguishable time arrow."""

    intact = _directed_orbit_metrics(target, target, opposite, "intact", seed)
    reverse = _directed_orbit_metrics(
        target, target, opposite, "orbit_temporal_reverse", seed
    )
    shuffled = [
        _directed_orbit_metrics(
            target,
            target,
            opposite,
            "orbit_temporal_shuffle",
            ar._hash_seed(seed, "reference-shuffle", index),
        )["directed_margin_mean"]
        for index in range(8)
    ]
    intact_margin = float(intact["directed_margin_mean"])
    disrupted = max(
        float(reverse["directed_margin_mean"]),
        float(np.quantile(shuffled, 0.95)) if shuffled else 0.0,
    )
    separation = intact_margin - disrupted
    return {
        "reference_directed_intact_margin": intact_margin,
        "reference_directed_reverse_margin": float(
            reverse["directed_margin_mean"]
        ),
        "reference_directed_shuffle_q95": float(
            np.quantile(shuffled, 0.95)
        ) if shuffled else 0.0,
        "reference_directed_separation": separation,
        "reference_temporally_identifiable": bool(separation >= 0.25),
    }


def _entry_intervention(
    shares: np.ndarray,
    active: np.ndarray,
    candidate: dict[str, Any],
    condition: str,
    generation: int,
    pair_id: str,
    replicates: int,
    source_exits: Sequence[tuple[np.ndarray, np.ndarray]] | None,
    contract: PhenotypeBridgeContract,
) -> tuple[np.ndarray, np.ndarray]:
    result = np.asarray(shares, dtype=np.uint8).copy()
    enabled = np.asarray(active, dtype=np.bool_).copy()
    if condition == "zero_every_boundary":
        return _destroy_carrier(result, enabled)
    if condition == "proper_subset" and result.shape[1] > 1:
        result[:, -1] = 0
        enabled[:, -1] = False
    if condition == "shuffle_every_boundary" and generation > contract.acquisition_generation:
        rng = np.random.default_rng(ar._hash_seed(contract.namespace, pair_id, "boundary-shuffle", generation))
        order = rng.permutation(len(result))
        result = result[order]
        enabled = enabled[order]
    if condition == "ablate_after_g5" and generation >= contract.intervention_generation:
        return _destroy_carrier(result, enabled)
    if generation == contract.intervention_generation and source_exits:
        source_values, source_active = source_exits[generation - 2][:2]
        if condition == "rescue_same_enter_g6":
            result = np.asarray(source_values, dtype=np.uint8).copy()
            enabled = np.asarray(source_active, dtype=np.bool_).copy()
        elif condition == "rescue_opposite_enter_g6":
            result = ar._swap_histories(np.asarray(source_values), replicates)
            enabled = ar._swap_histories(np.asarray(source_active), replicates)
    return result, enabled


def _field_entry_intervention(
    shares: np.ndarray,
    active: np.ndarray,
    condition: str,
    generation: int,
    pair_id: str,
    replicates: int,
    source_exits: Sequence[tuple[np.ndarray, ...]] | None,
    contract: PhenotypeBridgeContract,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply history interventions to the physically separate slow field."""

    result = np.asarray(shares, dtype=np.uint8).copy()
    enabled = np.asarray(active, dtype=np.bool_).copy()
    if condition == "inherited_field_zero":
        return _destroy_carrier(result, enabled)
    if (
        condition == "inherited_field_shuffle"
        and generation > contract.acquisition_generation
    ):
        result = ar._swap_histories(result, replicates)
        enabled = ar._swap_histories(enabled, replicates)
    if (
        condition == "inherited_field_ablation"
        and generation >= contract.intervention_generation
    ):
        return _destroy_carrier(result, enabled)
    if generation == contract.intervention_generation and source_exits:
        source = source_exits[generation - 2]
        if len(source) >= 4:
            source_values = np.asarray(source[2], dtype=np.uint8)
            source_active = np.asarray(source[3], dtype=np.bool_)
            if condition == "inherited_field_same_rescue":
                result = source_values.copy()
                enabled = source_active.copy()
            elif condition == "inherited_field_opposite_rescue":
                result = ar._swap_histories(source_values, replicates)
                enabled = ar._swap_histories(source_active, replicates)
    return result, enabled


def _profile_candidates(
    candidates: Sequence[dict[str, Any]],
    anchors: Sequence[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    if limit >= len(candidates):
        selected = list(candidates)
    else:
        groups = {
            "timing-only": [row for row in candidates if row["mechanism"] == "timing-only"],
            "visible-hysteresis": [row for row in candidates if row["mechanism"] == "visible-hysteresis"],
            "strict-somatic": [
                row for row in candidates
                if row["mechanism"] == "somatic-field" and row["claim_tier"] == "strict"
            ],
            "broad-somatic": [
                row for row in candidates
                if row["mechanism"] == "somatic-field" and row["claim_tier"] == "broad"
            ],
        }
        selected = []
        cursors = {key: 0 for key in groups}
        while len(selected) < limit:
            changed = False
            for key in groups:
                cursor = cursors[key]
                if cursor < len(groups[key]) and len(selected) < limit:
                    selected.append(groups[key][cursor])
                    cursors[key] += 1
                    changed = True
            if not changed:
                break
    return [*selected, *anchors]


def simulate_phenotype_lineage(
    pair: dict[str, Any],
    configuration: ar.ReaderConfiguration,
    candidate: dict[str, Any],
    condition: str,
    replicates: int,
    generations: int,
    reference: dict[int, dict[str, np.ndarray]],
    writer_contract: ar.MotifContract,
    contract: PhenotypeBridgeContract,
    environmental_template: np.ndarray,
    *,
    assignment_swap: bool = False,
    extent: int = 16,
    scale_mode: str = "fixed",
    source_exits: Sequence[tuple[np.ndarray, np.ndarray]] | None = None,
    retain_exits: bool = False,
    retain_bridge_trace: bool = False,
    retain_bridge_generations: Sequence[int] | None = None,
    retain_writer_samples: bool = False,
    rule: int | None = None,
) -> tuple[dict[str, Any], list[tuple[np.ndarray, np.ndarray]]]:
    """Run a lineage while explicitly auditing every memory-bearing state."""

    if condition not in ALL_CONDITIONS:
        raise ValueError(f"unknown Stage-6E condition {condition!r}")
    if extent not in (16, 32, 64):
        raise ValueError("Stage-6E extents are 16, 32, and 64")
    if scale_mode not in ("fixed", "diameter"):
        raise ValueError("scale mode must be fixed or diameter")
    active_rule = int(contract.rule if rule is None else rule)
    closure_oracle_mode = str(candidate.get("closure_oracle_mode", ""))
    if closure_oracle_mode and bool(candidate.get("promotable", True)):
        raise ValueError("target-exposed closure oracles must be non-promotable")
    pair_id = str(pair["pair_id"])
    reset_a = ar._resize_board(ar._state_from_hex("life", pair["donor_a"]["initial_state_hex"]), extent)
    reset_b = ar._resize_board(ar._state_from_hex("life", pair["donor_b"]["initial_state_hex"]), extent)
    if not np.array_equal(reset_a, reset_b):
        raise AssertionError(f"visible reset mismatch in pair {pair_id}")
    reset = np.repeat(reset_a[None], 2 * replicates, axis=0)
    statistical = candidate["statistical_candidate"]
    reference_probability = reference[configuration.write_window]["motif_probability"]
    founder, founder_terminal = ar._founder_bounded_payload(
        pair,
        statistical,
        reference_probability,
        replace(writer_contract, rule=active_rule),
        replicates,
        extent,
        active_rule,
    )
    statistical_energy = ar.decode_payload(founder, statistical["codec_model"])
    lane_count = int(candidate["rank"]) * (2 if int(candidate["bits"]) > 4 else 1)
    shares = np.zeros((2 * replicates, 4, lane_count), dtype=np.uint8)
    carrier_active = np.zeros_like(shares, dtype=np.bool_)
    mechanism = str(candidate["mechanism"])
    inherited_field = mechanism == "inherited-field"
    compact_latent = bool(
        inherited_field and candidate.get("compact_latent_carrier", False)
    )
    two_buffer_handoff = bool(candidate.get("two_buffer_handoff", False))
    field_candidate = _field_codec_candidate(candidate) if inherited_field else None
    field_lane_count = int(field_candidate["rank"]) if field_candidate else 1
    field_channels = int(candidate.get("field_channels", 1))
    field_shares = np.zeros(
        (2 * replicates, 4, field_lane_count), dtype=np.uint8
    )
    field_active = np.zeros_like(field_shares, dtype=np.bool_)
    alive = np.ones(2 * replicates, dtype=np.bool_)
    environment = ar._environment_samples(
        np.asarray(environmental_template, dtype=np.bool_), replicates, assignment_swap
    )
    scale = extent / 16.0 if scale_mode == "diameter" else 1.0
    radius = max(1, int(round(float(candidate["seed_radius"]) * scale)))
    hops = max(1, int(round(float(candidate["germination_hops"]) * scale)))
    read_sweeps = int(candidate["read_sweeps"])
    checkpoints = {
        value for value in (1, 2, 4, 5, 6, 7, 8, 16, 32, 64) if value <= generations
    }
    outcomes: dict[str, Any] = {}
    texture_history: dict[str, Any] = {}
    carrier_history: dict[str, Any] = {}
    writer_history: dict[str, Any] = {}
    somatic_history: dict[str, Any] = {}
    inherited_field_history: dict[str, Any] = {}
    orbit_history: dict[str, Any] = {}
    bridge_trace: dict[str, Any] = {}
    handoff_trace: dict[str, Any] = {}
    writer_samples: dict[str, Any] = {}
    exits: list[tuple[np.ndarray, np.ndarray]] = []
    uncorrectable_values: list[float] = []
    carrier_absence: list[bool] = []
    strict_field_absence: list[bool] = []
    birth_zero: list[bool] = []
    exit_zero: list[bool] = []
    field_copy_uncorrectable_values: list[float] = []
    field_birth_valid_values: list[bool] = []
    field_exit_valid_values: list[bool] = []
    daughter_birth_zero_values: list[bool] = []
    adapter_birth_zero_values: list[bool] = []
    adapter_exit_zero_values: list[bool] = []
    parent_erased_before_finalize_values: list[bool] = []
    direct_parent_copy_values: list[bool] = []

    trace_generations = {
        int(value) for value in (retain_bridge_generations or (5,))
    }
    for generation in range(1, generations + 1):
        translated = condition == "translated_patch"
        centers = ar.repair_origins(
            pair_id, generation, replicates, extent, "co-located", translated=translated
        )
        shares, carrier_active = _entry_intervention(
            shares,
            carrier_active,
            candidate,
            condition,
            generation,
            pair_id,
            replicates,
            source_exits,
            contract,
        )
        shares, uncorrectable = _copy_carrier(
            shares, pair_id, generation, replicates, contract
        )
        uncorrectable_values.append(uncorrectable)
        field_entry_valid = np.zeros(2 * replicates, dtype=np.bool_)
        field_entry_payload = np.zeros(
            (2 * replicates, field_lane_count), dtype=np.float32
        )
        field_copy_uncorrectable = 0.0
        if inherited_field and field_candidate is not None:
            field_shares, field_active = _field_entry_intervention(
                field_shares,
                field_active,
                condition,
                generation,
                pair_id,
                replicates,
                source_exits,
                contract,
            )
            field_corruption = (
                0.05
                if condition == "inherited_field_copy_noise_5"
                else float(candidate.get("field_copy_corruption", contract.bit_corruption))
            )
            field_shares, field_copy_uncorrectable = _copy_carrier(
                field_shares,
                pair_id,
                generation,
                replicates,
                contract,
                purpose="slow-field-copy",
                corruption=field_corruption,
            )
            if condition == "inherited_field_coefficient_shuffle" and field_lane_count > 1:
                order = np.random.default_rng(
                    ar._hash_seed(
                        contract.namespace,
                        pair_id,
                        "slow-field-coefficient-shuffle",
                        generation,
                    )
                ).permutation(field_lane_count)
                field_shares = field_shares[..., order]
                field_active = field_active[..., order]
            field_entry_payload, field_entry_valid = _joint_payload(
                field_shares, field_active, field_candidate
            )
            if (
                condition == "inherited_field_one_bin_damage"
                and generation > contract.acquisition_generation
                and field_lane_count > 0
            ):
                # Apply exactly one q4 step after physical decoding.  This is a
                # registered perturbation, not a second hidden noise channel.
                field_entry_payload[:, 0] = np.clip(
                    field_entry_payload[:, 0] + np.float32(1.0 / 7.0),
                    -1.0,
                    1.0,
                )
            field_copy_uncorrectable_values.append(field_copy_uncorrectable)
            if generation > contract.acquisition_generation:
                field_birth_valid_values.append(
                    bool(np.all(field_entry_valid | ~alive))
                )
        entry_payload, entry_valid = _joint_payload(shares, carrier_active, candidate)
        effective_hops = 0 if condition == "transport_disabled" else hops
        reader_payload, reader_valid, wave_trace = _reader_payload_at_centers(
            shares,
            carrier_active,
            centers,
            candidate | {"seed_radius": radius},
            extent,
            effective_hops,
        )
        state = reset.copy()
        state[~alive] = False
        somatic_channels = max(1, int(candidate.get("somatic_channels", 1)))
        somatic = np.zeros(
            (2 * replicates, somatic_channels, extent, extent), dtype=np.float32
        )
        slow_field = np.zeros(
            (2 * replicates, field_channels, extent, extent), dtype=np.float32
        )
        daughter_field = np.zeros_like(slow_field)
        adaptive_state = np.zeros_like(slow_field)
        compact_adapter = np.zeros(
            (2 * replicates, field_lane_count), dtype=np.float32
        )
        if inherited_field and field_candidate is not None:
            if compact_latent:
                reconstructed = _compact_decode_field(
                    field_entry_payload, candidate["closure_model"]
                )
            else:
                base_rank = int(
                    field_candidate.get("field_base_rank", field_candidate["rank"])
                )
                reconstructed_channels = [
                    ar.texture_decode(
                        field_entry_payload[
                            :, channel * base_rank : (channel + 1) * base_rank
                        ],
                        base_rank,
                    )
                    for channel in range(field_channels)
                ]
                reconstructed = np.stack(reconstructed_channels, axis=1)
            reconstructed[~field_entry_valid] = 0.0
            _set_field_patch(slow_field, centers, reconstructed)
        daughter_birth_zero_values.append(not bool(np.any(daughter_field)))
        adapter_birth_zero_values.append(not bool(np.any(adaptive_state)))
        birth_zero.append(not bool(np.any(somatic)))
        recent: deque[np.ndarray] = deque(maxlen=writer_contract.observation_window)
        closure_history: deque[np.ndarray] = deque(
            [state.copy()],
            maxlen=int(candidate.get("closure_model", {}).get("window", 16)),
        )
        trace_sum: np.ndarray | None = None
        trace_count = 0
        trace_observations: list[np.ndarray] = []
        read_state: np.ndarray | None = None
        post_state: np.ndarray | None = None
        writer_state: np.ndarray | None = None
        field_peak = 0.0
        carrier_erased_before_writer = False
        somatic_intervention_applied = False
        phenotype_intervention_applied = False
        tier = str(candidate["claim_tier"])
        field_erased_before_writer = mechanism != "somatic-field"
        if generation == contract.acquisition_generation:
            writer_start = contract.acquisition_start
            writer_end = contract.acquisition_end
            support_end = writer_start - 1
        elif inherited_field and two_buffer_handoff:
            support = (
                contract.generation_sweeps - read_sweeps
                if bool(candidate.get("closure_full_support", False))
                else int(candidate.get("field_support_sweeps", 8))
            )
            writer_offset = int(candidate.get("daughter_writer_start_offset", 5))
            write_span = int(candidate.get("daughter_writer_sweeps", 8))
            support_end = read_sweeps + support
            writer_start = read_sweeps + writer_offset
            writer_end = writer_start + write_span - 1
        elif mechanism in ("somatic-field", "inherited-field"):
            support_end = read_sweeps + int(
                candidate.get(
                    "field_support_sweeps"
                    if inherited_field
                    else "somatic_support_sweeps",
                    contract.somatic_support_sweeps,
                )
            )
            writer_start = support_end + 1
            writer_end = writer_start + int(candidate["trace_sweeps"]) - 1
        else:
            writer_start = read_sweeps + int(candidate["clearance_updates"])
            writer_end = writer_start + int(candidate["trace_sweeps"]) - 1
            support_end = writer_start - 1
        if writer_end > contract.generation_sweeps:
            raise AssertionError("Stage-6E writer window exceeds the generation")
        per_sweep_patches: dict[str, Any] = {}
        per_sweep_all_patches: dict[str, Any] = {}
        per_sweep_state_hex: dict[str, Any] = {}
        orbit_observed: list[np.ndarray] = []
        orbit_target: list[np.ndarray] = []
        orbit_opposite: list[np.ndarray] = []
        target_reference_state: np.ndarray | None = None
        opposite_reference_state: np.ndarray | None = None
        orbit_window = int(candidate.get("orbit_window_sweeps", 16))

        for sweep in range(1, contract.generation_sweeps + 1):
            previous_state = state.copy()
            predicted = ar._step(state, active_rule)
            if condition != "statistical_disabled" and sweep <= contract.statistical_read_sweeps:
                predicted = ar.apply_energy_reader(
                    predicted,
                    statistical_energy,
                    ar._semantic_uniforms(
                        pair_id,
                        "statistical-read",
                        generation,
                        sweep,
                        replicates,
                        extent,
                        contract.namespace,
                    ),
                    configuration.strength,
                )
            if condition != "read_disabled" and sweep <= read_sweeps:
                predicted = ar.apply_texture_reader(
                    predicted,
                    centers,
                    reader_payload,
                    ar._semantic_uniforms(
                        pair_id,
                        "texture-read",
                        generation,
                        sweep,
                        replicates,
                        extent,
                        contract.namespace,
                    ),
                    float(candidate["read_strength"]),
                )
            predicted ^= ar._semantic_uniforms(
                pair_id,
                "process",
                generation,
                sweep,
                replicates,
                extent,
                contract.namespace,
            ) < contract.process_noise
            if (
                mechanism == "visible-hysteresis"
                and generation != contract.acquisition_generation
                and read_sweeps < sweep <= writer_end
            ):
                keep = ar._semantic_uniforms(
                    pair_id,
                    "visible-hysteresis",
                    generation,
                    sweep,
                    replicates,
                    extent,
                    contract.namespace,
                ) < float(candidate["hysteresis"])
                predicted = np.where(keep, state, predicted)
            if (
                mechanism == "visible-stabilizer"
                and generation != contract.acquisition_generation
                and read_sweeps < sweep <= support_end
            ):
                base_strength = float(candidate.get("visible_strength", 0.50))
                if str(candidate.get("support_schedule", "short")) == "annealed":
                    remaining = max(1, support_end - sweep + 1)
                    span = max(1, support_end - read_sweeps)
                    base_strength *= remaining / span
                predicted = _apply_visible_stabilizer(
                    predicted,
                    state,
                    ar._semantic_uniforms(
                        pair_id,
                        "visible-stabilizer",
                        generation,
                        sweep,
                        replicates,
                        extent,
                        contract.namespace,
                    ),
                    base_strength,
                    str(candidate.get("visible_controller", "hysteresis")),
                )
            if mechanism == "somatic-field":
                acquisition_window = max(
                    1, int(candidate.get("somatic_acquisition_window", read_sweeps))
                )
                acquisition_start = max(1, read_sweeps - acquisition_window + 1)
                if acquisition_start <= sweep <= read_sweeps and condition not in (
                    "somatic_write_disabled",
                    "trace_write_disabled",
                ):
                    somatic = _somatic_write(
                        somatic,
                        predicted,
                        centers,
                        float(candidate["somatic_retention"]),
                        str(candidate["somatic_architecture"]),
                        previous_state,
                    )
                elif sweep > read_sweeps and np.any(somatic):
                    somatic = _somatic_decay(
                        somatic,
                        float(candidate["somatic_retention"]),
                        str(candidate["somatic_architecture"]),
                    )
                field_peak = max(field_peak, float(np.max(np.abs(somatic))))
                field_allowed = (
                    sweep > read_sweeps
                    and condition not in (
                        "somatic_bias_disabled",
                        "somatic_ablation",
                        "trace_read_disabled",
                        "trace_ablation",
                    )
                    and (tier == "broad" or sweep <= support_end)
                )
                if field_allowed:
                    predicted = _apply_somatic_bias(
                        predicted,
                        somatic,
                        ar._semantic_uniforms(
                            pair_id,
                            "somatic-bias",
                            generation,
                            sweep,
                            replicates,
                            extent,
                            contract.namespace,
                        ),
                        float(candidate["somatic_bias"]),
                        str(candidate.get("somatic_readout", "mean")),
                    )
            if inherited_field:
                field_allowed = (
                    generation != contract.acquisition_generation
                    and read_sweeps < sweep <= support_end
                    and condition
                    not in (
                        "inherited_field_read_disabled",
                        "inherited_field_ablation",
                        "trace_read_disabled",
                    )
                )
                if field_allowed:
                    field_strength = float(candidate.get("field_bias", 0.60))
                    if str(candidate.get("support_schedule", "short")) == "annealed":
                        remaining = max(1, support_end - sweep + 1)
                        span = max(1, support_end - read_sweeps)
                        field_strength *= remaining / span
                    field_for_bias = slow_field
                    if two_buffer_handoff and field_channels == 2:
                        field_for_bias = slow_field[:, :1] + np.float32(0.35) * slow_field[:, 1:2]
                    predicted = _apply_somatic_bias(
                        predicted,
                        field_for_bias,
                        ar._semantic_uniforms(
                            pair_id,
                            "inherited-field-bias",
                            generation,
                            sweep,
                            replicates,
                            extent,
                            contract.namespace,
                        ),
                        field_strength,
                        "mean",
                    )
                closure_rehearsal_allowed = bool(
                    two_buffer_handoff
                    and candidate.get("closure_self_rehearsal", False)
                    and generation != contract.acquisition_generation
                    and sweep > support_end
                    and condition
                    not in (
                        "closure_self_rehearsal_disabled",
                        "inherited_field_read_disabled",
                        "inherited_field_ablation",
                        "trace_read_disabled",
                    )
                    and np.any(daughter_field)
                )
                if closure_rehearsal_allowed:
                    rehearsal_field = daughter_field
                    if field_channels == 2:
                        rehearsal_field = (
                            daughter_field[:, :1]
                            + np.float32(0.35) * daughter_field[:, 1:2]
                        )
                    predicted = _apply_somatic_bias(
                        predicted,
                        rehearsal_field,
                        ar._semantic_uniforms(
                            pair_id,
                            "closure-self-rehearsal",
                            generation,
                            sweep,
                            replicates,
                            extent,
                            contract.namespace,
                        ),
                        float(candidate.get("closure_rehearsal_bias", 0.45)),
                        "mean",
                    )
            predicted[~alive] = False
            if (
                condition != "sham"
                and generation == contract.acquisition_generation
                and contract.acquisition_start <= sweep <= contract.acquisition_end
            ):
                ar._apply_environment(predicted, centers, environment)
            state = predicted
            closure_history.append(state.copy())

            if inherited_field and writer_start <= sweep <= writer_end:
                field_write_enabled = condition not in (
                    "no_rewrite",
                    "inherited_field_write_disabled",
                    "inherited_field_no_renewal",
                    "trace_write_disabled",
                )
                if field_write_enabled:
                    if two_buffer_handoff:
                        if compact_latent:
                            compact_model = candidate["closure_model"]
                            if bool(candidate.get("compact_oracle_mode", False)):
                                predicted_code = _compact_oracle_code(
                                    environment, compact_model
                                )
                            else:
                                predicted_code = _compact_model_code(
                                    list(closure_history), centers, compact_model
                                )
                            compact_adapter = _compact_attractor_update(
                                compact_adapter, predicted_code, compact_model
                            )
                            decoded = _compact_decode_field(
                                compact_adapter, compact_model
                            )
                            _set_field_patch(daughter_field, centers, decoded)
                        elif closure_oracle_mode:
                            oracle = _closure_oracle_patches(
                                environment,
                                closure_oracle_mode,
                                pair_id,
                                generation,
                                sweep,
                                contract,
                            )
                            _set_field_patch(daughter_field, centers, oracle)
                            _set_field_patch(adaptive_state, centers, oracle)
                        else:
                            daughter_field, adaptive_state, _ = _adaptive_handoff_update(
                                daughter_field,
                                adaptive_state,
                                state,
                                previous_state,
                                centers,
                                candidate,
                                history=closure_history,
                            )
                    else:
                        slow_field = _somatic_write(
                            slow_field,
                            state,
                            centers,
                            float(candidate.get("field_retention", 0.95)),
                            str(candidate.get("field_architecture", "local-latch")),
                            previous_state,
                        )

            if (
                inherited_field
                and two_buffer_handoff
                and generation != contract.acquisition_generation
                and sweep == support_end
            ):
                slow_field.fill(0.0)
                if condition == "handoff_visible_scrub":
                    cr._phenotype_intervention(
                        state,
                        centers,
                        environment,
                        "phenotype_scrub",
                        pair_id,
                        generation,
                        replicates,
                        contract,
                    )

            if (
                two_buffer_handoff
                and generation == contract.intervention_generation
                and read_sweeps <= sweep <= writer_end
            ):
                handoff_trace[str(sweep)] = {
                    "visible_match_mean": float(
                        np.mean(ar._texture_match(state, centers, environment))
                    ),
                    "parent_field_mean_abs": float(np.mean(np.abs(slow_field))),
                    "daughter_field_mean_abs": float(
                        np.mean(np.abs(daughter_field))
                    ),
                    "adaptive_state_mean_abs": float(
                        np.mean(np.abs(adaptive_state))
                    ),
                    "parent_support_active": bool(sweep <= support_end),
                    "daughter_write_active": bool(writer_start <= sweep <= writer_end),
                }

            if sweep == read_sweeps:
                target_reference_state = state.copy()
                opposite_reference_state = state.copy()
                ar._apply_environment(
                    target_reference_state, centers, environment
                )
                ar._apply_environment(
                    opposite_reference_state, centers, ~environment
                )
            elif (
                read_sweeps < sweep <= read_sweeps + orbit_window
                and target_reference_state is not None
                and opposite_reference_state is not None
            ):
                target_reference_state = ar._step(target_reference_state, active_rule)
                opposite_reference_state = ar._step(
                    opposite_reference_state, active_rule
                )
                orbit_observed.append(ar.observe_texture(state, centers))
                orbit_target.append(
                    ar.observe_texture(target_reference_state, centers)
                )
                orbit_opposite.append(
                    ar.observe_texture(opposite_reference_state, centers)
                )

            if sweep == read_sweeps:
                read_state = state.copy()
                if generation != contract.acquisition_generation:
                    if condition != "no_erasure" and not candidate.get("force_no_erasure", False):
                        shares, carrier_active = _destroy_carrier(shares, carrier_active)
                        carrier_erased_before_writer = True
            if mechanism == "somatic-field" and generation != contract.acquisition_generation:
                if condition in ("somatic_ablation", "trace_ablation") and generation == contract.intervention_generation:
                    somatic.fill(0.0)
                    somatic_intervention_applied = True
                if sweep == support_end and tier == "strict":
                    somatic.fill(0.0)
                    field_erased_before_writer = True
                if sweep == writer_start - 1 and tier == "broad" and generation == contract.intervention_generation:
                    if condition in ("somatic_shuffle", "trace_shuffle"):
                        somatic = ar._swap_histories(somatic, replicates)
                        somatic_intervention_applied = True
                    elif condition in ("somatic_same_rescue", "trace_same_rescue"):
                        somatic.fill(0.0)
                        _set_somatic_patch(somatic, centers, environment)
                        somatic_intervention_applied = True
                    elif condition in ("somatic_opposite_rescue", "trace_opposite_rescue"):
                        somatic.fill(0.0)
                        _set_somatic_patch(somatic, centers, environment, opposite=True)
                        somatic_intervention_applied = True
            if sweep == writer_start - 1 and generation != contract.acquisition_generation:
                phenotype_intervention_applied = cr._phenotype_intervention(
                    state,
                    centers,
                    environment,
                    condition,
                    pair_id,
                    generation,
                    replicates,
                    contract,
                )
            if sweep == writer_start:
                post_state = state.copy()
            if writer_start <= sweep <= writer_end:
                writer_centers = centers
                if (
                    condition == "writer_spatial_shift"
                    and generation == contract.intervention_generation
                ):
                    writer_centers = (
                        np.asarray(centers, dtype=np.int64)
                        + np.asarray((2, 2), dtype=np.int64)
                    ) % extent
                if (
                    generation != contract.acquisition_generation
                    and candidate.get("writer_source") == "somatic"
                ):
                    observed = _somatic_observe(
                        somatic,
                        writer_centers,
                        str(candidate.get("somatic_readout", "mean")),
                    )
                else:
                    observation_radius: str | int = (
                        "patch"
                        if generation == contract.acquisition_generation
                        else candidate.get("writer_observation_radius", "patch")
                    )
                    observed = _observe_writer_input(
                        state, writer_centers, observation_radius
                    )
                if condition in ("trace_read_disabled", "somatic_bias_disabled"):
                    observed = np.zeros_like(observed)
                if condition == "writer_observation_shuffle" and generation == contract.intervention_generation:
                    observed = ar._swap_histories(observed, replicates)
                if trace_sum is None:
                    trace_sum = np.zeros_like(observed, dtype=np.float64)
                trace_sum += observed
                trace_count += 1
                trace_observations.append(np.asarray(observed, dtype=np.float32).copy())
            if sweep == writer_end:
                writer_state = state.copy()
                if mechanism == "somatic-field":
                    somatic.fill(0.0)
            if retain_bridge_trace and generation in trace_generations and sweep > read_sweeps:
                per_sweep_patches[str(sweep)] = ar.observe_texture(state, centers).tolist()
            if retain_bridge_trace and generation in trace_generations:
                per_sweep_all_patches[str(sweep)] = ar.observe_texture(state, centers).tolist()
                per_sweep_state_hex[str(sweep)] = [
                    np.packbits(sample.reshape(-1)).tobytes().hex() for sample in state
                ]
            if sweep >= contract.observe_start:
                recent.append(ar.live_2x2_counts_batch(state))

        if read_state is None:
            raise AssertionError("Stage-6E read checkpoint was not captured")
        if post_state is None:
            post_state = read_state.copy()
        if writer_state is None or trace_count <= 0 or trace_sum is None:
            raise AssertionError("Stage-6E writer trace changed")
        alive &= state.any(axis=(1, 2))
        ordered_trace = trace_observations
        if condition == "writer_temporal_reverse":
            ordered_trace = list(reversed(ordered_trace))
        elif condition == "writer_temporal_shuffle" and len(ordered_trace) > 1:
            order_rng = np.random.default_rng(
                ar._hash_seed(contract.namespace, pair_id, "writer-time-shuffle", generation)
            )
            order = order_rng.permutation(len(ordered_trace))
            ordered_trace = [ordered_trace[int(index)] for index in order]
        feature_kind = (
            "mean"
            if generation == contract.acquisition_generation
            else str(candidate.get("writer_feature", "mean"))
        )
        trace_stack = np.stack(ordered_trace, axis=0)
        if feature_kind == "endpoint":
            writer_feature = trace_stack[-1]
        elif feature_kind == "temporal-median":
            writer_feature = np.median(trace_stack, axis=0).astype(np.float32)
        elif feature_kind == "transition":
            writer_feature = trace_stack[-1] - trace_stack[0]
        elif feature_kind == "autocorrelation" and len(trace_stack) > 1:
            writer_feature = np.mean(trace_stack[1:] * trace_stack[:-1], axis=0)
        elif feature_kind == "temporal-mix" and len(trace_stack) > 1:
            weights = np.linspace(-1.0, 1.0, len(trace_stack), dtype=np.float32)
            normalizer = np.sum(np.abs(weights))
            writer_feature = np.tensordot(weights / normalizer, trace_stack, axes=(0, 0))
        elif feature_kind == "multiscale":
            averaged = np.mean(trace_stack, axis=0)
            writer_feature = (
                np.float32(0.5) * averaged
                + np.float32(0.125) * np.roll(averaged, 1, axis=1)
                + np.float32(0.125) * np.roll(averaged, -1, axis=1)
                + np.float32(0.125) * np.roll(averaged, 1, axis=2)
                + np.float32(0.125) * np.roll(averaged, -1, axis=2)
            )
        else:
            writer_feature = (trace_sum / float(trace_count)).astype(np.float32)
        if generation == contract.acquisition_generation:
            # Founder acquisition retains the registered environmental writer.
            # A Stage-6G translator is learned for daughter form, not allowed to
            # alter the origin of the lineage it will later be asked to renew.
            raw_proposal = ar.texture_encode(
                np.asarray(writer_feature, dtype=np.float32), int(candidate["rank"])
            )
            transform_metadata = {
                "kind": "founder-bypass",
                "transform_id": "founder-bypass",
                "target_space": "visible-patch",
                "input_dimension": 16,
                "target_exposed": False,
            }
        else:
            raw_proposal, transform_metadata = _transform_writer_proposal(
                candidate,
                np.asarray(writer_feature, dtype=np.float32),
                trace_stack,
                environment,
                condition,
                generation,
                replicates,
                contract,
            )
        proposal, clipping = _quantize_frontend(
            np.float32(candidate.get("write_gain", 1.0)) * raw_proposal,
            candidate,
        )
        if retain_writer_samples and generation >= contract.acquisition_generation:
            proposal_patch = ar.texture_decode(proposal, int(candidate["rank"]))
            target_patch = np.where(environment, 1.0, -1.0).astype(np.float32)
            writer_samples[str(generation)] = {
                "writer_feature": np.asarray(writer_feature, dtype=np.float32).tolist(),
                "trace_stack": np.moveaxis(
                    np.asarray(trace_stack, dtype=np.float32), 1, 0
                ).tolist(),
                "target_patch": target_patch.tolist(),
                "proposal_coefficients": np.asarray(proposal, dtype=np.float32).tolist(),
                "proposal_patch": np.asarray(proposal_patch, dtype=np.float32).tolist(),
                "proposal_bit_accuracy": float(
                    np.mean((proposal_patch >= 0.0) == (target_patch >= 0.0))
                ),
                "writer_source": str(candidate.get("writer_source", "visible")),
                "writer_transform_target_exposed": bool(
                    transform_metadata["target_exposed"]
                ),
            }
        writer_connected = bool(np.all(reader_valid | ~alive))
        carrier_absent_during_writer = bool(not np.any(carrier_active) and not np.any(shares))
        field_absent_during_writer = bool(not np.any(somatic)) if tier == "strict" else False
        if generation != contract.acquisition_generation:
            carrier_absence.append(carrier_absent_during_writer)
            if tier == "strict":
                strict_field_absence.append(field_erased_before_writer and field_absent_during_writer)
        zero_payload = np.zeros((2 * replicates, int(candidate["rank"])), dtype=np.float32)
        if generation < contract.acquisition_generation:
            next_payload = zero_payload
            write_fresh = False
        elif generation == contract.acquisition_generation and condition == "acquisition_write_disabled":
            next_payload = zero_payload
            write_fresh = False
        elif generation == contract.acquisition_generation:
            # Acquisition is the origin of the texture lineage.  There is no
            # incoming texture carrier to validate at this boundary, so the
            # environmental writer must not be gated by ``reader_valid``.
            # Stage 6D has the same explicit branch.  Omitting it made every
            # Stage-6E founder carrier empty and rendered intact and sham
            # trajectories identical from generation five onward.
            next_payload = proposal
            write_fresh = True
        elif generation > contract.acquisition_generation and condition == "no_rewrite":
            next_payload = zero_payload
            write_fresh = False
        elif generation > contract.acquisition_generation and bool(
            candidate.get("closure_disable_texture_carrier", False)
        ):
            next_payload = zero_payload
            write_fresh = False
        elif not writer_connected:
            next_payload = zero_payload
            write_fresh = False
        else:
            next_payload = proposal
            write_fresh = True
        if write_fresh:
            shares, carrier_active = _encode_carrier(
                next_payload,
                candidate,
                contract,
                pair_id,
                generation,
                "phenotype-bridge-write",
            )
            carrier_active[~alive] = False
        else:
            shares, carrier_active = _destroy_carrier(shares, carrier_active)
        field_write_fresh = False
        field_clipping = 0.0
        if inherited_field and field_candidate is not None:
            if compact_latent:
                raw_field_payload = compact_adapter
            else:
                outgoing_field = daughter_field if two_buffer_handoff else slow_field
                field_patches = _field_observe_channels(outgoing_field, centers)
                base_rank = int(
                    field_candidate.get("field_base_rank", field_candidate["rank"])
                )
                raw_field_payload = np.concatenate(
                    [
                        ar.texture_encode(field_patches[:, channel], base_rank)
                        for channel in range(field_channels)
                    ],
                    axis=1,
                )
            field_payload, field_clipping = _quantize_frontend(
                raw_field_payload, field_candidate
            )
            field_write_fresh = bool(
                generation >= contract.acquisition_generation
                and condition
                not in (
                    "no_rewrite",
                    "acquisition_write_disabled",
                    "inherited_field_zero",
                    "inherited_field_write_disabled",
                    "inherited_field_no_renewal",
                    "inherited_field_ablation",
                    "trace_write_disabled",
                )
            )
            if field_write_fresh:
                field_shares, field_active = _encode_carrier(
                    field_payload,
                    field_candidate,
                    contract,
                    pair_id,
                    generation,
                    "slow-field-write",
                )
                field_active[~alive] = False
            else:
                field_shares, field_active = _destroy_carrier(
                    field_shares, field_active
                )
            if generation >= contract.acquisition_generation:
                field_exit_valid_values.append(
                    bool(np.all(np.all(field_active, axis=(1, 2)) | ~alive))
                )
                if two_buffer_handoff:
                    parent_erased_before_finalize_values.append(not bool(np.any(slow_field)))
                    direct_parent_copy_values.append(
                        not bool(np.shares_memory(slow_field, daughter_field))
                    )
        adaptive_state.fill(0.0)
        compact_adapter.fill(0.0)
        adapter_exit_zero_values.append(not bool(np.any(adaptive_state)))
        somatic.fill(0.0)
        exit_zero.append(not bool(np.any(somatic)))

        if generation in checkpoints:
            outcome, _ = ar._score_state(
                state, recent, pair, founder_terminal, replicates, writer_contract
            )
            outcomes[str(generation)] = outcome

            def match_snapshot(snapshot: np.ndarray) -> tuple[float, float, float]:
                values = ar._texture_match(snapshot, centers, environment)
                return (
                    float(np.mean(values)),
                    float(np.mean(values[:replicates])),
                    float(np.mean(values[replicates:])),
                )

            def projected_match(
                snapshot: np.ndarray, rank: int
            ) -> tuple[float, float, float]:
                observed_patch = ar.observe_texture(snapshot, centers)
                target_patch = np.where(environment, 1.0, -1.0).astype(np.float32)
                observed_coefficients = ar.texture_encode(observed_patch, rank)
                target_coefficients = ar.texture_encode(target_patch, rank)
                denominator = np.sum(target_coefficients**2, axis=1)
                values = np.divide(
                    np.sum(observed_coefficients * target_coefficients, axis=1),
                    denominator,
                    out=np.zeros_like(denominator),
                    where=denominator > np.float32(1e-8),
                )
                values = np.clip(values, -1.0, 1.0)
                return (
                    float(np.mean(values)),
                    float(np.mean(values[:replicates])),
                    float(np.mean(values[replicates:])),
                )

            read_match = match_snapshot(read_state)
            post_match = match_snapshot(post_state)
            writer_match = match_snapshot(writer_state)
            terminal_match = match_snapshot(state)
            orbit_history[str(generation)] = _orbit_metrics(
                orbit_observed,
                orbit_target,
                orbit_opposite,
                condition,
                ar._hash_seed(
                    contract.namespace,
                    pair_id,
                    "orbit-order",
                    generation,
                ),
            ) | _directed_orbit_metrics(
                orbit_observed,
                orbit_target,
                orbit_opposite,
                condition,
                ar._hash_seed(
                    contract.namespace,
                    pair_id,
                    "directed-orbit-order",
                    generation,
                ),
            ) | _directed_reference_diagnostic(
                orbit_target,
                orbit_opposite,
                ar._hash_seed(
                    contract.namespace,
                    pair_id,
                    "directed-reference-identifiability",
                    generation,
                ),
            ) | {
                "carrier_erased_before_window": carrier_erased_before_writer,
                "reference_kind": "paired-context-target-and-opposite-base-rule",
                "phase_invariant": True,
                "temporal_order_preserved": condition
                not in ("orbit_temporal_reverse", "orbit_temporal_shuffle"),
            }
            texture_history[str(generation)] = {
                "read_match_mean": read_match[0],
                "read_direction_a_mean": read_match[1],
                "read_direction_b_mean": read_match[2],
                "post_washout_match_mean": post_match[0],
                "post_washout_direction_a_mean": post_match[1],
                "post_washout_direction_b_mean": post_match[2],
                "writer_match_mean": writer_match[0],
                "writer_direction_a_mean": writer_match[1],
                "writer_direction_b_mean": writer_match[2],
                "terminal_match_mean": terminal_match[0],
                "terminal_direction_a_mean": terminal_match[1],
                "terminal_direction_b_mean": terminal_match[2],
            }
            for rank in (4, 8):
                for prefix, snapshot in (
                    ("read", read_state),
                    ("post_washout", post_state),
                    ("writer", writer_state),
                    ("terminal", state),
                ):
                    projected = projected_match(snapshot, rank)
                    texture_history[str(generation)].update(
                        {
                            f"{prefix}_rank{rank}_match_mean": projected[0],
                            f"{prefix}_rank{rank}_direction_a_mean": projected[1],
                            f"{prefix}_rank{rank}_direction_b_mean": projected[2],
                        }
                    )
            carrier_history[str(generation)] = _carrier_diagnostics(
                shares,
                carrier_active,
                candidate,
                replicates,
                ar._hash_seed(contract.namespace, pair_id, generation, "texture-decoder"),
                contract.decoder_splits,
            ) | {
                "entry_complete_fraction": float(np.mean(entry_valid)),
                "reader_complete_fraction": float(np.mean(reader_valid)),
                "wave_trace": wave_trace,
            }
            writer_history[str(generation)] = {
                "read_end": read_sweeps,
                "writer_start": writer_start,
                "writer_end": writer_end,
                "trace_count": trace_count,
                "writer_feature": feature_kind,
                "writer_observation_radius": candidate.get(
                    "writer_observation_radius", "patch"
                ),
                "writer_transform_kind": transform_metadata["kind"],
                "writer_transform_id": transform_metadata["transform_id"],
                "writer_transform_target_space": transform_metadata["target_space"],
                "writer_transform_input_dimension": transform_metadata["input_dimension"],
                "writer_transform_temporal_view": transform_metadata.get(
                    "temporal_view", "exact"
                ),
                "writer_transform_target_exposed": transform_metadata["target_exposed"],
                "writer_transform_frozen": bool(
                    candidate.get("writer_transform", {}).get("model_frozen", False)
                ),
                "raw_proposal_mean_abs": float(np.mean(np.abs(raw_proposal))),
                "proposal_mean_abs": float(np.mean(np.abs(proposal))),
                "quantizer_clipping": float(clipping),
                "writer_connected": writer_connected,
                "writer_connection_required": generation > contract.acquisition_generation,
                "acquisition_writer_independent": generation == contract.acquisition_generation,
                "incoming_payload_exposed_to_writer": False,
                "somatic_exposed_to_writer": bool(
                    generation != contract.acquisition_generation
                    and candidate.get("writer_source") == "somatic"
                ),
                "carrier_erased_before_writer": carrier_erased_before_writer,
                "carrier_absent_during_writer": carrier_absent_during_writer,
                "field_erased_before_writer": field_erased_before_writer,
                "field_absent_during_writer": field_absent_during_writer,
                "phenotype_intervention_applied": phenotype_intervention_applied,
                "somatic_intervention_applied": somatic_intervention_applied,
                "fresh_carrier_written": write_fresh,
            }
            somatic_history[str(generation)] = {
                "birth_zero": birth_zero[-1],
                "exit_zero": exit_zero[-1],
                "peak_mean_abs": field_peak,
                "architecture": str(candidate["somatic_architecture"]),
                "claim_tier": tier,
            }
            if inherited_field and field_candidate is not None:
                inherited_field_history[str(generation)] = {
                    "entry_valid_fraction": float(np.mean(field_entry_valid)),
                    "entry_payload_mean_abs": float(
                        np.mean(np.abs(field_entry_payload))
                    ),
                    "copy_uncorrectable_fraction": field_copy_uncorrectable,
                    "field_rank": int(field_candidate["rank"]),
                    "field_base_rank": int(
                        field_candidate.get("field_base_rank", field_candidate["rank"])
                    ),
                    "field_channels": field_channels,
                    "compact_latent_carrier": compact_latent,
                    "compact_latent_size": (
                        int(candidate["closure_model"]["latent_size"])
                        if compact_latent
                        else None
                    ),
                    "field_architecture": str(
                        candidate.get("field_architecture", "local-latch")
                    ),
                    "field_peak_mean_abs": float(
                        np.max(np.abs(daughter_field if two_buffer_handoff else slow_field))
                    ),
                    "field_bias": float(candidate.get("field_bias", 0.60)),
                    "fresh_field_written": field_write_fresh,
                    "two_buffer_handoff": two_buffer_handoff,
                    "daughter_field_zero_at_birth": daughter_birth_zero_values[-1],
                    "adapter_zero_at_birth": adapter_birth_zero_values[-1],
                    "adapter_zero_at_exit": adapter_exit_zero_values[-1],
                    "parent_erased_before_outgoing_finalize": (
                        parent_erased_before_finalize_values[-1]
                        if parent_erased_before_finalize_values
                        else not two_buffer_handoff
                    ),
                    "parent_daughter_buffers_distinct": (
                        direct_parent_copy_values[-1]
                        if direct_parent_copy_values
                        else not two_buffer_handoff
                    ),
                    "quantizer_clipping": float(field_clipping),
                    "exit_decoder": _carrier_diagnostics(
                        field_shares,
                        field_active,
                        field_candidate,
                        replicates,
                        ar._hash_seed(
                            contract.namespace,
                            pair_id,
                            generation,
                            "slow-field-decoder",
                        ),
                        contract.decoder_splits,
                    ),
                }
        if retain_bridge_trace and generation in trace_generations:
            bridge_trace[str(generation)] = {
                "read_end": read_sweeps,
                "patches_after_read": per_sweep_patches,
                "patches_all": per_sweep_all_patches,
                "full_state_hex": per_sweep_state_hex,
                "state_shape": [extent, extent],
                "centers": np.asarray(centers, dtype=np.int16).tolist(),
                "environment": np.where(environment, 1.0, -1.0).tolist(),
            }
        if retain_exits:
            if inherited_field:
                exits.append(
                    (
                        shares.copy(),
                        carrier_active.copy(),
                        field_shares.copy(),
                        field_active.copy(),
                    )
                )
            else:
                exits.append((shares.copy(), carrier_active.copy()))

    strict = str(candidate["claim_tier"]) == "strict"
    result = {
        "candidate_id": str(candidate["candidate_id"]),
        "condition": condition,
        "pair_id": pair_id,
        "extent": extent,
        "scale_mode": scale_mode,
        "rule": active_rule,
        "replicates": replicates,
        "generations": generations,
        "reset_sha256": hashlib.sha256(reset_a.tobytes()).hexdigest(),
        "reset_asserted_before_every_generation": True,
        "environment_applied": condition != "sham",
        "environment_not_passed_to_writer": not bool(
            candidate.get("writer_transform", {}).get("kind") == "target-ceiling"
            or closure_oracle_mode
            or candidate.get("compact_oracle_mode", False)
        ),
        "incoming_payload_not_passed_to_writer": True,
        "somatic_not_passed_to_writer": candidate.get("writer_source") != "somatic",
        "assignment_swap": assignment_swap,
        "mechanism": str(candidate["mechanism"]),
        "claim_tier": str(candidate["claim_tier"]),
        "training_mode": str(candidate.get("training_mode", "label-free")),
        "texture_rank": int(candidate["rank"]),
        "texture_payload_bits": int(candidate["payload_bits"]),
        "physical_encoded_bits": int(lane_count * 4 * 8 + lane_count * 4),
        "statistical_scaffold_id": statistical["candidate_id"],
        "statistical_scaffold_frozen": True,
        "all_renewal_writer_windows_carrier_absent": bool(carrier_absence and all(carrier_absence)) if generations > 4 else True,
        "all_strict_writer_windows_field_absent": bool(strict_field_absence and all(strict_field_absence)) if strict and generations > 4 else strict,
        "somatic_zero_at_every_birth": bool(birth_zero and all(birth_zero)),
        "somatic_zero_at_every_exit": bool(exit_zero and all(exit_zero)),
        "outcomes": outcomes,
        "texture_history": texture_history,
        "carrier_history": carrier_history,
        "writer_history": writer_history,
        "somatic_history": somatic_history,
        "inherited_field_history": inherited_field_history,
        "orbit_history": orbit_history,
        "bridge_trace": bridge_trace,
        "handoff_trace": handoff_trace,
        "writer_samples": writer_samples,
        "survival_fraction": float(np.mean(alive)),
        "copy_uncorrectable_fraction": float(np.mean(uncorrectable_values)),
        "field_copy_uncorrectable_fraction": float(
            np.mean(field_copy_uncorrectable_values)
        )
        if field_copy_uncorrectable_values
        else 0.0,
        "inherited_field_birth_valid_fraction": float(
            np.mean(field_birth_valid_values)
        )
        if field_birth_valid_values
        else (0.0 if inherited_field else 1.0),
        "inherited_field_exit_valid_fraction": float(
            np.mean(field_exit_valid_values)
        )
        if field_exit_valid_values
        else (0.0 if inherited_field else 1.0),
        "inherited_field_crosses_visible_reset": inherited_field,
        "inherited_field_encoded_bottleneck": inherited_field,
        "two_buffer_handoff": two_buffer_handoff,
        "closure_model_kind": (
            str(candidate.get("closure_model", {}).get("kind"))
            if candidate.get("closure_model")
            else None
        ),
        "closure_model_frozen": bool(
            candidate.get("closure_model", {}).get("model_frozen", False)
        ),
        "closure_canonicalized": bool(
            candidate.get("closure_model", {}).get("canonicalize", False)
        ),
        "closure_self_rehearsal": bool(candidate.get("closure_self_rehearsal", False)),
        "closure_oracle_mode": closure_oracle_mode or None,
        "closure_oracle_nonpromotable": bool(
            closure_oracle_mode and not candidate.get("promotable", True)
        ),
        "compact_latent_carrier": compact_latent,
        "compact_oracle_mode": bool(candidate.get("compact_oracle_mode", False)),
        "compact_oracle_nonpromotable": bool(
            candidate.get("compact_oracle_mode", False)
            and not candidate.get("promotable", True)
        ),
        "closure_texture_carrier_disabled_after_acquisition": bool(
            candidate.get("closure_disable_texture_carrier", False)
        ),
        "daughter_field_zero_at_every_birth": bool(
            daughter_birth_zero_values and all(daughter_birth_zero_values)
        ) if two_buffer_handoff else True,
        "adaptive_state_zero_at_every_birth": bool(
            adapter_birth_zero_values and all(adapter_birth_zero_values)
        ) if two_buffer_handoff else True,
        "adaptive_state_zero_at_every_exit": bool(
            adapter_exit_zero_values and all(adapter_exit_zero_values)
        ) if two_buffer_handoff else True,
        "parent_field_erased_before_every_finalize": bool(
            parent_erased_before_finalize_values
            and all(parent_erased_before_finalize_values)
        ) if two_buffer_handoff and generations >= contract.acquisition_generation else True,
        "parent_daughter_buffers_always_distinct": bool(
            direct_parent_copy_values and all(direct_parent_copy_values)
        ) if two_buffer_handoff and generations >= contract.acquisition_generation else True,
    }
    return result, exits


def _phenotype_pair_task(
    payload: tuple[
        dict[str, Any],
        list[dict[str, Any]],
        ar.MotifContract,
        PhenotypeBridgeContract,
        dict[int, dict[str, np.ndarray]],
    ]
) -> dict[str, Any]:
    item, models, writer_contract, contract, reference = payload
    by_id = {str(row["candidate_id"]): row for row in models}
    candidate = by_id[str(item["candidate_id"])]
    configuration = ar.ReaderConfiguration(**item["configuration"])
    common = dict(
        pair=item["pair"],
        configuration=configuration,
        candidate=candidate,
        replicates=int(item["replicates"]),
        generations=int(item["generations"]),
        reference=reference,
        writer_contract=writer_contract,
        contract=contract,
        environmental_template=np.asarray(item["environmental_template"], dtype=np.bool_),
        assignment_swap=bool(item["assignment_swap"]),
        extent=int(item.get("extent", 16)),
        scale_mode=str(item.get("scale_mode", "fixed")),
        rule=int(item.get("rule", contract.rule)),
        retain_writer_samples=bool(item.get("retain_writer_samples", False)),
        retain_bridge_trace=bool(item.get("retain_bridge_trace", False)),
        retain_bridge_generations=tuple(
            int(value) for value in item.get("retain_bridge_generations", (5,))
        ),
    )
    intact, exits = simulate_phenotype_lineage(
        condition="intact", retain_exits=True, **common
    )
    conditions: dict[str, Any] = {"intact": intact}
    for condition in item["conditions"]:
        if condition == "intact":
            continue
        result, _ = simulate_phenotype_lineage(
            condition=str(condition), source_exits=exits, **common
        )
        conditions[str(condition)] = result
    return {
        "checkpoint": item["checkpoint"],
        "analysis_kind": str(item.get("analysis_kind", "lineage")),
        "pair_id": item["pair"]["pair_id"],
        "candidate_id": str(item["candidate_id"]),
        "template_pair_id": item["template_pair_id"],
        "template_ids": item["template_ids"],
        "assignment_swap": bool(item["assignment_swap"]),
        "extent": int(item.get("extent", 16)),
        "scale_mode": str(item.get("scale_mode", "fixed")),
        "rule": int(item.get("rule", contract.rule)),
        "replicates": int(item["replicates"]),
        "generations": int(item["generations"]),
        "conditions": conditions,
    }


def _bridge_trace_task(
    payload: tuple[
        dict[str, Any],
        list[dict[str, Any]],
        ar.MotifContract,
        PhenotypeBridgeContract,
        dict[int, dict[str, np.ndarray]],
    ]
) -> dict[str, Any]:
    item, models, writer_contract, contract, reference = payload
    by_id = {str(row["candidate_id"]): row for row in models}
    candidate = by_id[str(item["candidate_id"])]
    common = dict(
        pair=item["pair"],
        configuration=ar.ReaderConfiguration(**item["configuration"]),
        candidate=candidate,
        replicates=int(item["replicates"]),
        generations=5,
        reference=reference,
        writer_contract=writer_contract,
        contract=contract,
        environmental_template=np.asarray(item["environmental_template"], dtype=np.bool_),
        assignment_swap=bool(item["assignment_swap"]),
        retain_bridge_trace=True,
    )
    conditions = {}
    for condition in ("intact", "sham"):
        result, _ = simulate_phenotype_lineage(condition=condition, **common)
        conditions[condition] = result
    return {
        "checkpoint": item["checkpoint"],
        "analysis_kind": "bridge-trace",
        "pair_id": item["pair"]["pair_id"],
        "candidate_id": str(item["candidate_id"]),
        "template_pair_id": item["template_pair_id"],
        "template_ids": item["template_ids"],
        "assignment_swap": bool(item["assignment_swap"]),
        "extent": 16,
        "scale_mode": "fixed",
        "replicates": int(item["replicates"]),
        "generations": 5,
        "conditions": conditions,
    }


def _bridge_source_models(stage6br_root: Path) -> list[dict[str, Any]]:
    stage6d, _ = cr.build_consumptive_candidates(stage6br_root)
    scaffold = stage6d[0]["statistical_candidate"]
    models = []
    for read_sweeps, gain in ((40, 1.0), (48, 1.5)):
        frontend = {
            "frontend_id": f"source-q4-d{read_sweeps:02d}",
            "encoder_id": "texture-walsh-r16-q04",
            "kind": "legacy-q4",
            "bits": 4,
            "scale": [1.0] * 16,
            "read_sweeps": read_sweeps,
            "clearance_updates": 5,
            "trace_sweeps": 8,
        }
        models.append(
            _base_candidate(frontend, scaffold)
            | {
                "candidate_id": str(frontend["frontend_id"]),
                "mechanism": "timing-only",
                "claim_tier": "strict",
                "hysteresis": 0.0,
                "somatic_architecture": "none",
                "somatic_retention": 0.0,
                "somatic_bias": 0.0,
                "write_gain": gain,
                "promotable": False,
            }
        )
    return models


def _proposal_from_trace(trace: dict[str, Any], start: int, length: int) -> np.ndarray:
    patches = trace["patches_after_read"]
    selected = [np.asarray(patches[str(sweep)], dtype=np.float32) for sweep in range(start, start + length)]
    return ar.texture_encode(np.mean(selected, axis=0).astype(np.float32), 16)


def _ranking_lower(summary: dict[str, Any]) -> float:
    value = summary.get("ci", [None, None])[0]
    return float(summary.get("mean") or 0.0) if value is None else float(value)


def _bridge_frontend_grid(
    rows: Sequence[dict[str, Any]],
    profile: PhenotypeBridgeProfile,
    contract: PhenotypeBridgeContract,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_values: list[np.ndarray] = []
    sham_magnitudes: list[float] = []
    for row in rows:
        for condition in ("intact", "sham"):
            trace = row["conditions"][condition]["bridge_trace"]["5"]
            for patch in trace["patches_after_read"].values():
                coefficients = ar.texture_encode(np.asarray(patch, dtype=np.float32), 16)
                raw_values.append(coefficients.reshape(-1, 16))
                if condition == "sham":
                    sham_magnitudes.extend(np.max(np.abs(coefficients), axis=-1).tolist())
    pooled = np.concatenate(raw_values, axis=0)
    calibrated_scale = np.clip(np.quantile(np.abs(pooled), 0.95, axis=0), 1.0 / 127.0, 1.0)
    agc_threshold = float(np.quantile(np.asarray(sham_magnitudes), 0.99))
    encoders = (
        {
            "encoder_id": "legacy-q4-unit",
            "kind": "legacy-q4",
            "bits": 4,
            "scale": np.ones(16, dtype=np.float32),
        },
        {
            "encoder_id": "calibrated-q4-p95",
            "kind": "calibrated-q4",
            "bits": 4,
            "scale": calibrated_scale,
        },
        {
            "encoder_id": "agc-q4-sham99",
            "kind": "agc-q4",
            "bits": 4,
            "scale": np.ones(16, dtype=np.float32),
            "agc_threshold": agc_threshold,
        },
        {
            "encoder_id": "unit-q8",
            "kind": "unit-q8",
            "bits": 8,
            "scale": np.ones(16, dtype=np.float32),
        },
        {
            "encoder_id": "float32-ceiling",
            "kind": "float32",
            "bits": 32,
            "scale": np.ones(16, dtype=np.float32),
            "promotable": False,
        },
    )
    summaries: list[dict[str, Any]] = []
    for source in (40, 48):
        source_id = f"source-q4-d{source:02d}"
        source_rows = [row for row in rows if row["candidate_id"] == source_id]
        for clearance in contract.bridge_clearance_updates:
            start = source + clearance
            for trace_sweeps in contract.bridge_trace_lengths:
                if start + trace_sweeps - 1 > contract.generation_sweeps:
                    continue
                for encoder in encoders:
                    frontend = {
                        "frontend_id": (
                            f"{encoder['encoder_id']}-d{source:02d}-"
                            f"c{clearance:02d}-t{trace_sweeps:02d}"
                        ),
                        "encoder_id": encoder["encoder_id"],
                        "kind": encoder["kind"],
                        "bits": encoder["bits"],
                        "scale": np.asarray(encoder["scale"], dtype=np.float32).tolist(),
                        "agc_threshold": float(encoder.get("agc_threshold", 0.0)),
                        "read_sweeps": source,
                        "clearance_updates": clearance,
                        "trace_sweeps": trace_sweeps,
                        "promotable": bool(encoder.get("promotable", True)),
                    }
                    temporary = {
                        "writer_encoder_kind": frontend["kind"],
                        "agc_threshold": frontend["agc_threshold"],
                        "codec_model": _frontend_codec(frontend),
                    }
                    effects: list[float] = []
                    intact_values: list[float] = []
                    sham_values: list[float] = []
                    for row in source_rows:
                        values: dict[str, float] = {}
                        for condition in ("intact", "sham"):
                            trace = row["conditions"][condition]["bridge_trace"]["5"]
                            raw = _proposal_from_trace(trace, start, trace_sweeps)
                            proposal, _ = _quantize_frontend(raw, temporary)
                            decoded = ar.texture_decode(proposal, 16)
                            target = np.asarray(trace["environment"], dtype=np.float32)
                            values[condition] = float(np.mean(decoded * target))
                        intact_values.append(values["intact"])
                        sham_values.append(values["sham"])
                        effects.append(values["intact"] - values["sham"])
                    bootstrap = ar._bootstrap(
                        effects,
                        profile.bootstrap_resamples,
                        ar._hash_seed(contract.namespace, "bridge-proxy", frontend["frontend_id"]),
                        contract.strict_alpha,
                    )
                    summaries.append(
                        frontend
                        | {
                            "proxy_effect": bootstrap,
                            "intact_mean": float(np.mean(intact_values)),
                            "sham_mean": float(np.mean(sham_values)),
                        }
                    )
    ranked = sorted(
        summaries,
        key=lambda row: (
            -_ranking_lower(row["proxy_effect"]),
            int(row["bits"]),
            int(row["trace_sweeps"]),
            -int(row["clearance_updates"]),
            str(row["frontend_id"]),
        ),
    )
    validation: list[dict[str, Any]] = []
    per_encoder: dict[str, int] = {}
    for row in ranked:
        if not row["promotable"]:
            continue
        encoder_id = str(row["encoder_id"])
        if per_encoder.get(encoder_id, 0) >= 2:
            continue
        validation.append(row)
        per_encoder[encoder_id] = per_encoder.get(encoder_id, 0) + 1
        if len(validation) == 8:
            break
    audit = {
        "calibrated_scale": calibrated_scale.tolist(),
        "agc_threshold": agc_threshold,
        "evaluated_cells": len(summaries),
        "proxy_summaries": summaries,
        "validation_frontends": validation,
        "float32_promotable": False,
    }
    return validation, audit


def _validation_candidates(
    frontends: Sequence[dict[str, Any]], stage6br_root: Path
) -> list[dict[str, Any]]:
    stage6d, _ = cr.build_consumptive_candidates(stage6br_root)
    scaffold = stage6d[0]["statistical_candidate"]
    return [
        _base_candidate(frontend, scaffold)
        | {
            "candidate_id": f"validate-{frontend['frontend_id']}",
            "mechanism": "timing-only",
            "claim_tier": "strict",
            "hysteresis": 0.0,
            "somatic_architecture": "none",
            "somatic_retention": 0.0,
            "somatic_bias": 0.0,
            "promotable": True,
        }
        for frontend in frontends
    ]


def _boot_effect(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
    profile: PhenotypeBridgeProfile,
    contract: PhenotypeBridgeContract,
    key: str,
) -> dict[str, Any]:
    values = cr._effect_values(rows, candidate_id, condition, generation, "read_match_mean")
    return ar._bootstrap(
        values,
        profile.bootstrap_resamples,
        ar._hash_seed(contract.namespace, key, candidate_id, generation),
        contract.strict_alpha,
    )


def _summary(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
    profile: PhenotypeBridgeProfile,
    contract: PhenotypeBridgeContract,
    phase: str,
) -> dict[str, Any]:
    base = cr._consumptive_summary(rows, candidate, generation, profile, contract, phase)
    candidate_id = str(candidate["candidate_id"])
    read_mean = float(base["read_acquisition"].get("mean") or 0.0)
    for condition in (
        "somatic_write_disabled",
        "somatic_bias_disabled",
        "somatic_ablation",
        "somatic_shuffle",
        "somatic_same_rescue",
        "trace_write_disabled",
        "trace_read_disabled",
        "trace_ablation",
        "trace_shuffle",
        "trace_same_rescue",
        "writer_temporal_reverse",
        "writer_temporal_shuffle",
        "translator_ablation",
        "translator_weight_shuffle",
        "translator_bit_permutation",
        "translator_history_shuffle",
        "writer_spatial_shift",
    ):
        values = cr._effect_values(rows, candidate_id, condition, generation, "read_match_mean")
        if values:
            base["control_retention"][condition] = cr._ratio(float(np.mean(values)), read_mean)
    opposite = cr._effect_values(
        rows, candidate_id, "somatic_opposite_rescue", generation, "read_match_mean"
    )
    if opposite:
        base["somatic_opposite_rescue"] = ar._bootstrap(
            opposite,
            profile.bootstrap_resamples,
            ar._hash_seed(contract.namespace, phase, candidate_id, generation, "somatic-opposite"),
            contract.strict_alpha,
        )
    trace_opposite = cr._effect_values(
        rows, candidate_id, "trace_opposite_rescue", generation, "read_match_mean"
    )
    if trace_opposite:
        base["trace_opposite_rescue"] = ar._bootstrap(
            trace_opposite,
            profile.bootstrap_resamples,
            ar._hash_seed(contract.namespace, phase, candidate_id, generation, "trace-opposite"),
            contract.strict_alpha,
        )
    relevant = [row for row in rows if row.get("candidate_id") == candidate_id and "intact" in row.get("conditions", {})]
    base["strict_field_absence_fraction"] = float(
        np.mean([
            bool(row["conditions"]["intact"]["all_strict_writer_windows_field_absent"])
            for row in relevant
        ])
    ) if relevant else 0.0
    base["somatic_birth_zero_fraction"] = float(
        np.mean([bool(row["conditions"]["intact"]["somatic_zero_at_every_birth"]) for row in relevant])
    ) if relevant else 0.0
    base["somatic_exit_zero_fraction"] = float(
        np.mean([bool(row["conditions"]["intact"]["somatic_zero_at_every_exit"]) for row in relevant])
    ) if relevant else 0.0
    base["writer_visible_only_fraction"] = float(
        np.mean([bool(row["conditions"]["intact"]["somatic_not_passed_to_writer"]) for row in relevant])
    ) if relevant else 0.0
    base["writer_field_read_fraction"] = float(
        np.mean([not bool(row["conditions"]["intact"]["somatic_not_passed_to_writer"]) for row in relevant])
    ) if relevant else 0.0
    base["claim_tier"] = str(candidate["claim_tier"])
    base["mechanism"] = str(candidate["mechanism"])
    base["writer_source"] = str(candidate.get("writer_source", "visible"))
    base["writer_input_contract"] = str(
        candidate.get("writer_input_contract", "visible-only")
    )
    base["training_mode"] = str(candidate.get("training_mode", "label-free"))
    return base


def _tier_invariants(summary: dict[str, Any]) -> bool:
    field_readable = bool(
        summary.get("claim_tier") == "broad"
        and summary.get("writer_input_contract") == "field-readable"
    )
    common = bool(
        summary.get("carrier_absence_fraction") == 1.0
        and summary.get("somatic_birth_zero_fraction") == 1.0
        and summary.get("somatic_exit_zero_fraction") == 1.0
        and (
            summary.get("writer_field_read_fraction") == 1.0
            if field_readable
            else summary.get("writer_visible_only_fraction") == 1.0
        )
    )
    if summary.get("claim_tier") == "strict":
        return common and summary.get("strict_field_absence_fraction") == 1.0
    return common


def _screen_gate(summary: dict[str, Any], contract: PhenotypeBridgeContract) -> bool:
    gate = cr._screen_gate(summary, contract) and _tier_invariants(summary)
    if summary.get("mechanism") == "somatic-field":
        controls = summary["control_retention"]
        gate = gate and controls.get("somatic_write_disabled", 1.0) <= 0.30
        gate = gate and controls.get("somatic_bias_disabled", 1.0) <= 0.30
    return bool(gate)


def _qualification_gate(
    generation8: dict[str, Any],
    generation16: dict[str, Any],
    contract: PhenotypeBridgeContract,
) -> bool:
    tier = str(generation16["claim_tier"])
    tested = generation16
    if tier == "broad" and generation16.get("mechanism") == "somatic-field":
        tested = dict(generation16)
        controls = generation16["control_retention"]
        tested["phenotype_scrub_retention"] = controls.get("somatic_ablation", 1.0)
        tested["phenotype_same_rescue_retention"] = controls.get("somatic_same_rescue", 0.0)
        tested["phenotype_opposite_rescue"] = generation16.get("somatic_opposite_rescue", {})
    return bool(
        cr._qualification_gate(generation8, tested, contract)
        and _tier_invariants(generation16)
    )


def _endurance_gate(
    generation32: dict[str, Any],
    generation64: dict[str, Any],
    scales: dict[str, dict[str, Any]],
    contract: PhenotypeBridgeContract,
) -> bool:
    return bool(
        cr._endurance_gate(generation32, generation64, scales, contract)
        and _tier_invariants(generation64)
    )


def _audit_gate(
    generation8: dict[str, Any],
    generation16: dict[str, Any],
    generation64: dict[str, Any],
    contract: PhenotypeBridgeContract,
) -> bool:
    tested = generation64
    if (
        generation64["claim_tier"] == "broad"
        and generation64.get("mechanism") == "somatic-field"
    ):
        tested = dict(generation64)
        controls = generation64["control_retention"]
        tested["phenotype_scrub_retention"] = controls.get("somatic_ablation", 1.0)
        tested["phenotype_same_rescue_retention"] = controls.get("somatic_same_rescue", 0.0)
        tested["phenotype_opposite_rescue"] = generation64.get("somatic_opposite_rescue", {})
    return bool(
        cr._audit_gate(generation8, generation16, tested, contract)
        and _tier_invariants(generation64)
    )


def _frozen_stage6d_hashes(stage6d_root: Path) -> dict[str, str]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "COHORTS.json",
        "screen/RESULTS.json",
        "COMPLETE",
    )
    missing = [stage6d_root / name for name in required if not (stage6d_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6D artifacts: {missing}")
    result = _load_json(stage6d_root / "RESULTS.json")
    status = _load_json(stage6d_root / "STATUS.json")
    cohorts = _load_json(stage6d_root / "COHORTS.json")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6D is not complete")
    if result.get("verdict") != "NO_RENEWABLE_TEXTURE":
        raise ValueError("Stage-6D verdict changed")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6D protected reserve is no longer untouched")
    return {name: ar._sha256(stage6d_root / name) for name in required}


def _prepare_stage6e(
    output: Path,
    profile_name: str,
    *,
    auto_final_audit: bool,
    stage6d_root: Path,
    stage6c_root: Path,
    stage6br_root: Path,
    stage5r_root: Path,
    stage5_root: Path,
    stage4_root: Path,
    stage3r_root: Path,
    stage3_root: Path,
    stage2_root: Path,
    stage1_root: Path,
) -> tuple[
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    PhenotypeBridgeProfile,
    PhenotypeBridgeContract,
    ar.MotifContract,
    list[dict[str, Any]],
    str,
]:
    stage6d_root = stage6d_root.resolve()
    stage6c_root = stage6c_root.resolve()
    stage6br_root = stage6br_root.resolve()
    stage6d_hashes = _frozen_stage6d_hashes(stage6d_root)
    stage6c_hashes = ar._frozen_stage6c_hashes(stage6c_root)
    frozen = ar.load_frozen_stage5r(
        stage5r_root,
        stage5_root,
        stage4_root,
        stage3r_root,
        stage3_root,
        stage2_root,
        stage1_root,
    )
    profile = PHENOTYPE_BRIDGE_PROFILES[profile_name]
    contract = PhenotypeBridgeContract()
    writer_contract = ar.MotifContract()
    base = ar.select_synergy_cohorts(
        frozen, ar.SYNERGY_PROFILES["reference"], "reference", open_final=False
    )
    exposed = base["plasticity"]
    expected = _load_json(stage6c_root / "DESIGN.json")["development_pair_ids"]["plasticity"]
    if [str(pair["pair_id"]) for pair in exposed] != expected:
        raise ValueError("Stage-6C exposed cohort changed")
    cursor = 0

    def take(count: int) -> list[dict[str, Any]]:
        nonlocal cursor
        result = exposed[cursor : cursor + count]
        cursor += count
        if len(result) != count:
            raise ValueError("Stage-6E exposed cohort is incomplete")
        return result

    cohorts = {
        "bridge": take(profile.bridge_pairs),
        "screen": take(profile.screen_pairs),
        "qualification": take(profile.qualification_pairs),
        "endurance": take(profile.endurance_pairs),
        "final": [],
    }
    used = [str(pair["pair_id"]) for name, rows in cohorts.items() if name != "final" for pair in rows]
    if len(used) != len(set(used)):
        raise AssertionError("Stage-6E developmental cohorts overlap")
    if set(used) & set(frozen["later_ids"]):
        raise AssertionError("Stage-6E development touched the protected reserve")
    templates = ar.acquisition_templates(ar.SynergyContract())
    reserve_digest = hashlib.sha256("\n".join(frozen["later_ids"]).encode()).hexdigest()
    design_payload = {
        "experiment": "ca_motif_phenotype_bridge_stage_6e",
        "contract": contract.to_dict(),
        "writer_contract_digest": writer_contract.digest,
        "profile_name": profile_name,
        "profile": asdict(profile),
        "phases": PHASES,
        "automatic_phase_progression": True,
        "automatic_final_audit_user_authorized": bool(auto_final_audit),
        "automatic_final_audit_requires_all_developmental_gates": True,
        "frozen_stage6d_sha256": stage6d_hashes,
        "frozen_stage6c_sha256": stage6c_hashes,
        "stage6d_design_digest": _load_json(stage6d_root / "DESIGN.json")["design_digest"],
        "candidate_factorial": {
            "timing_only": 2,
            "visible_hysteresis": {"strengths": (0.25, 0.50, 0.75, 0.90), "count": 8},
            "somatic": {
                "architecture": ("local-latch", "diffusing-phase"),
                "retention": (0.75, 0.95),
                "bias": (0.40, 0.80),
                "claim_tier": ("strict", "broad"),
                "count": 16,
            },
            "promotable_count": 26,
            "nonpromotable_anchor_count": 3,
        },
        "bridge_selection": {
            "source_read_sweeps": (40, 48),
            "clearance_updates": contract.bridge_clearance_updates,
            "trace_sweeps": contract.bridge_trace_lengths,
            "encoders": (
                "legacy-q4-unit",
                "calibrated-q4-p95",
                "agc-q4-sham99",
                "unit-q8",
                "float32-ceiling-nonpromotable",
            ),
            "selection_limit": 2,
            "distinct_encoder_required": True,
        },
        "development_pair_ids": {
            key: [str(pair["pair_id"]) for pair in rows]
            for key, rows in cohorts.items()
            if key != "final"
        },
        "development_uses_only_stage6c_exposed_pairs": True,
        "paired_opposite_environment_assignments": True,
        "templates": templates,
        "rule_stress_panel": RULE_STRESS_PANEL,
        "rule_stress_can_rescue": False,
        "final_audit_pair_count": len(frozen["later_ids"]),
        "final_audit_pair_ids_sha256": reserve_digest,
        "final_audit_trajectories_loaded": False,
        "implementation_sha256": {
            "motif_phenotype_bridge.py": ar._sha256(Path(__file__)),
            "motif_consumptive_renewal.py": ar._sha256(Path(__file__).with_name("motif_consumptive_renewal.py")),
            "motif_acquisition_repair.py": ar._sha256(Path(__file__).with_name("motif_acquisition_repair.py")),
        },
        "input_sha256": {
            "protocol": ar._sha256(PROTOCOL_PATH),
            **{f"stage5r_{key}": ar._sha256(path) for key, path in frozen["paths"].items()},
        },
        "writer_api_excludes": (
            "environment template",
            "target label",
            "family label",
            "lineage identity",
            "incoming carrier payload",
            "somatic field for promotable designs",
        ),
        "cleanroom_exclusion": "no Wagner or Fable implementation source is read, imported, hashed, or executed",
        "retuning_on_final_audit": False,
        "claim_boundary": "engineered synthetic cellular-automaton heredity",
    }
    design_digest = hashlib.sha256(
        json.dumps(design_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    design = design_payload | {"design_digest": design_digest}
    design_path = output / "DESIGN.json"
    if design_path.exists():
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6E design changed; refusing a mixed resume")
    else:
        ar._atomic_json(design_path, design)
    prior = _load_json(output / "COHORTS.json") if (output / "COHORTS.json").exists() else {}
    reserve_state = prior.get("final_audit_trajectory_state", "untouched")
    ar._atomic_json(
        output / "COHORTS.json",
        {
            "design_digest": design_digest,
            "development_pair_ids": design["development_pair_ids"],
            "final_audit_pair_count": len(frozen["later_ids"]),
            "final_audit_pair_ids_sha256": reserve_digest,
            "final_audit_trajectory_state": reserve_state,
            "final_audit_trajectories_not_loaded": reserve_state == "untouched",
        },
    )
    ar._atomic_json(
        output / "CANDIDATE_FAMILIES.json",
        {"design_digest": design_digest, **design["candidate_factorial"]},
    )
    ar._atomic_json(
        output / "CLEANROOM_PROVENANCE.json",
        {
            "experiment": design["experiment"],
            "design_digest": design_digest,
            "excluded_code": ("Wagner implementation", "Fable implementation"),
            "excluded_code_read_import_hash_execute": True,
            "implementation_independent": True,
        },
    )
    return frozen, cohorts, profile, contract, writer_contract, templates, design_digest


def _write_phase_result(
    output: Path,
    phase: str,
    design_digest: str,
    result: dict[str, Any],
    report: str,
    lay: str,
    *,
    next_phase: str | None,
) -> None:
    root = output / phase
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment": "ca_motif_phenotype_bridge_stage_6e",
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
            "decision": "advance" if payload.get("stage_gate") and next_phase else "campaign_complete" if payload.get("stage_gate") else "phase_gate_failed",
            "next_phase": next_phase if payload.get("stage_gate") else None,
            "final_audit_trajectory_state": payload.get("final_audit_trajectory_state", "untouched"),
        },
    )
    ar._atomic_text(root / "REPORT.md", report.rstrip() + "\n")
    ar._atomic_text(root / "LAY_SUMMARY.md", lay.rstrip() + "\n")
    ar._atomic_text(root / "COMPLETE", "complete\n")


def _run_forensics(
    output: Path,
    stage6d_root: Path,
    design_digest: str,
    status: Any,
) -> dict[str, Any]:
    candidate_id = "consume-r16-s90-d40-w04-g100"
    paths = sorted((stage6d_root / "screen-trajectories-stage6d/checkpoints").glob("*.json"))
    rows = [
        _load_json(path)["result"]
        for path in paths
        if _load_json(path)["result"].get("candidate_id") == candidate_id
    ]
    status("running", "stage6d-first-handoff", completed=0, total=max(1, len(rows)))

    def effect(key: str) -> float:
        values = [
            float(row["conditions"]["intact"]["texture_history"]["5"][key])
            - float(row["conditions"]["sham"]["texture_history"]["5"][key])
            for row in rows
        ]
        return float(np.mean(values)) if values else 0.0

    decode = float(
        np.mean([
            row["conditions"]["intact"]["carrier_history"]["5"]["joint_balanced_accuracy"]
            for row in rows
        ])
    ) if rows else 0.0
    diagnosis = {
        "candidate_id": candidate_id,
        "trajectory_count": len(rows),
        "generation5_read_effect": effect("read_match_mean"),
        "generation5_post_washout_effect": effect("post_washout_match_mean"),
        "generation5_writer_effect": effect("writer_match_mean"),
        "generation5_fresh_carrier_joint_decode": decode,
        "failure_location": "visible-decay-and-writer-quantization",
    }
    stage_gate = bool(
        diagnosis["generation5_read_effect"] > 0.75
        and diagnosis["generation5_writer_effect"] > 0.0
        and 0.40 <= decode <= 0.60
    )
    result = {
        "state": "complete",
        "stage_gate": stage_gate,
        "diagnosis": diagnosis,
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_result(
        output,
        "forensics",
        design_digest,
        result,
        "# Stage 6E forensics\n\nThe frozen Stage 6D first handoff was re-aggregated. "
        f"Read effect was {diagnosis['generation5_read_effect']:.4f}, writer-window effect "
        f"was {diagnosis['generation5_writer_effect']:.4f}, and the replacement carrier "
        f"decoded at {decode:.4f}.",
        "# Lay summary\n\nThe daughter could read the inherited note, but the visible drawing faded "
        "and the replacement note contained no reliable history.",
        next_phase="bridge",
    )
    status("running", "stage6d-first-handoff", completed=len(rows), total=max(1, len(rows)))
    return result


def _run_bridge(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: PhenotypeBridgeProfile,
    contract: PhenotypeBridgeContract,
    writer_contract: ar.MotifContract,
    templates: list[dict[str, Any]],
    design_digest: str,
    stage6br_root: Path,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    models = _bridge_source_models(stage6br_root)
    items = ar._make_items(
        cohorts["bridge"],
        models,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="bridge-trace",
        replicates=profile.bridge_replicates,
        generations=5,
        conditions=("intact", "sham"),
    )
    trace_rows, trace_complete = ar._run_json_checkpoints(
        output,
        "bridge-traces-stage6e",
        items,
        models,
        _bridge_trace_task,
        writer_contract,
        contract,
        frozen["stage4"]["reference"],
        design_digest,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    if not trace_complete:
        result = {
            "state": "budget_truncated",
            "stage_gate": False,
            "selected_frontends": [],
            "completed_trace_trajectories": len(trace_rows),
            "registered_trace_trajectories": len(items),
            "final_audit_trajectory_state": "untouched",
        }
        _write_phase_result(
            output,
            "bridge",
            design_digest,
            result,
            "# Stage 6E bridge map\n\nThe bridge map hit the exploration deadline.",
            "# Lay summary\n\nThe timing map did not finish within its registered budget.",
            next_phase="screen",
        )
        return result
    validation_frontends, audit = _bridge_frontend_grid(trace_rows, profile, contract)
    validation_models = _validation_candidates(validation_frontends, stage6br_root)
    validation_items = ar._make_items(
        cohorts["bridge"],
        validation_models,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="bridge-validation",
        replicates=profile.bridge_replicates,
        generations=6,
        conditions=("intact", "sham"),
    )
    validation_rows, validation_complete = ar._run_json_checkpoints(
        output,
        "bridge-validation-stage6e",
        validation_items,
        validation_models,
        _phenotype_pair_task,
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
    for candidate, frontend in zip(validation_models, validation_frontends):
        values = cr._effect_values(
            validation_rows, str(candidate["candidate_id"]), "intact", 6, "read_match_mean"
        )
        summaries[str(candidate["candidate_id"])] = {
            "frontend": frontend,
            "next_daughter_read_effect": ar._bootstrap(
                values,
                profile.bootstrap_resamples,
                ar._hash_seed(contract.namespace, "bridge-validation", candidate["candidate_id"]),
                contract.strict_alpha,
            ),
        }
    ranked = sorted(
        summaries,
        key=lambda candidate_id: (
            -_ranking_lower(summaries[candidate_id]["next_daughter_read_effect"]),
            int(summaries[candidate_id]["frontend"]["bits"]),
            int(summaries[candidate_id]["frontend"]["trace_sweeps"]),
            -int(summaries[candidate_id]["frontend"]["clearance_updates"]),
            candidate_id,
        ),
    )
    selected: list[dict[str, Any]] = []
    used_encoders: set[str] = set()
    for candidate_id in ranked:
        frontend = summaries[candidate_id]["frontend"]
        if str(frontend["encoder_id"]) in used_encoders:
            continue
        selected.append(frontend)
        used_encoders.add(str(frontend["encoder_id"]))
        if len(selected) == 2:
            break
    complete = trace_complete and validation_complete and len(selected) == 2
    if not complete:
        selected = []
    selection_digest = hashlib.sha256(
        json.dumps(selected, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    sealed = {
        "design_digest": design_digest,
        "selection_digest": selection_digest,
        "selection_frozen_before_screen": True,
        "frontends": selected,
        "validation_summaries": summaries,
        "calibration": {
            "calibrated_scale": audit["calibrated_scale"],
            "agc_threshold": audit["agc_threshold"],
        },
    }
    ar._atomic_json(output / "SEALED_FRONTENDS.json", sealed)
    if selected:
        candidates, anchors = build_phenotype_bridge_candidates(selected, stage6br_root)
        ar._atomic_json(
            output / "CANDIDATES.json",
            {
                "design_digest": design_digest,
                "selection_digest": selection_digest,
                "promotable_count": len(candidates),
                "candidates": [_candidate_public(row) for row in candidates],
                "anchors": [_candidate_public(row) for row in anchors],
            },
        )
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "selected_frontends": selected,
        "selection_digest": selection_digest,
        "proxy_audit": audit,
        "validation_summaries": summaries,
        "completed_trace_trajectories": len(trace_rows),
        "registered_trace_trajectories": len(items),
        "completed_validation_trajectories": len(validation_rows),
        "registered_validation_trajectories": len(validation_items),
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_result(
        output,
        "bridge",
        design_digest,
        result,
        "# Stage 6E bridge map\n\nSealed frontends: "
        + (", ".join(row["frontend_id"] for row in selected) if selected else "none"),
        "# Lay summary\n\nThe timing map measured how quickly the drawing fades and which label-blind "
        "writer can turn the surviving drawing into a readable next note.",
        next_phase="screen",
    )
    return result


def _load_models(output: Path, stage6br_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    writeback_registry = output / "WRITEBACK_CANDIDATES.json"
    if writeback_registry.exists():
        registry = _load_json(writeback_registry)
        if not registry.get("selection_frozen_before_screen"):
            raise ValueError("Stage-6F writer registry was not sealed before screening")
        specs = list(registry.get("candidates", []))
        return build_writeback_candidates(
            specs,
            stage6br_root,
            maximum_candidates=int(registry.get("maximum_candidates", 12)),
        )
    sealed = _load_json(output / "SEALED_FRONTENDS.json")
    if not sealed.get("selection_frozen_before_screen") or len(sealed.get("frontends", [])) != 2:
        raise ValueError("Stage-6E frontends are not sealed")
    return build_phenotype_bridge_candidates(sealed["frontends"], stage6br_root)


def _run_screen(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: PhenotypeBridgeProfile,
    contract: PhenotypeBridgeContract,
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
    conditions: Sequence[str] = SCREEN_CONDITIONS,
) -> dict[str, Any]:
    bridge = _load_json(output / "bridge/RESULTS.json")
    if not bridge.get("stage_gate"):
        result = {
            "state": "complete",
            "stage_gate": False,
            "candidate_summaries": {},
            "selected_candidate_ids": [],
            "selected_by_tier": {"strict": [], "broad": []},
            "skipped_reason": "bridge map did not seal two frontends",
            "final_audit_trajectory_state": "untouched",
        }
        _write_phase_result(
            output,
            "screen",
            design_digest,
            result,
            "# Stage 6E screen\n\nSkipped because the bridge map did not seal two frontends.",
            "# Lay summary\n\nThe one-generation timing study did not produce a complete writer design.",
            next_phase="qualify",
        )
        return result
    candidates, anchors = _load_models(output, stage6br_root)
    models = _profile_candidates(candidates, anchors, profile.candidate_limit)
    items = ar._make_items(
        cohorts["screen"],
        models,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="screen",
        replicates=profile.screen_replicates,
        generations=8,
        conditions=conditions,
    )
    rows, complete = ar._run_json_checkpoints(
        output,
        "screen-trajectories-stage6e",
        items,
        models,
        _phenotype_pair_task,
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
        str(candidate["candidate_id"]): _summary(rows, candidate, 8, profile, contract, "screen")
        for candidate in models
    }
    for summary in summaries.values():
        summary["screen_gate"] = _screen_gate(summary, contract) if scientific else bool(summary["candidate"].get("promotable", False))
    ranked = sorted(
        summaries,
        key=lambda candidate_id: (
            -float(summaries[candidate_id]["post_washout_acquisition"].get("mean") or 0.0),
            -float(summaries[candidate_id]["active_rewrite_advantage"].get("mean") or 0.0),
            candidate_id,
        ),
    )
    selected: list[str] = []
    counts = {"strict": 0, "broad": 0}
    for candidate_id in ranked:
        summary = summaries[candidate_id]
        tier = str(summary.get("claim_tier"))
        if not summary["screen_gate"] or tier not in counts or counts[tier] >= 2:
            continue
        selected.append(candidate_id)
        counts[tier] += 1
    if not complete:
        selected = []
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(selected),
        "scientific_gate_applied": scientific,
        "candidate_summaries": summaries,
        "selected_candidate_ids": selected,
        "selected_by_tier": {tier: [cid for cid in selected if summaries[cid]["claim_tier"] == tier] for tier in counts},
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_result(
        output,
        "screen",
        design_digest,
        result,
        "# Stage 6E screen\n\nSelected candidates: " + (", ".join(selected) if selected else "none"),
        "# Lay summary\n\nEach design had to rebuild a fresh note after the inherited one was destroyed; "
        "strict and temporary-somatic mechanisms were scored separately.",
        next_phase="qualify",
    )
    return result


def _models_by_id(candidates: Sequence[dict[str, Any]], candidate_ids: Sequence[str]) -> list[dict[str, Any]]:
    by_id = {str(row["candidate_id"]): row for row in candidates}
    missing = [candidate_id for candidate_id in candidate_ids if candidate_id not in by_id]
    if missing:
        raise ValueError(f"Stage-6E selected candidates are missing: {missing}")
    return [by_id[candidate_id] for candidate_id in candidate_ids]


def _run_qualification(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: PhenotypeBridgeProfile,
    contract: PhenotypeBridgeContract,
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
    conditions: Sequence[str] = QUALIFICATION_CONDITIONS,
) -> dict[str, Any]:
    screen = _load_json(output / "screen/RESULTS.json")
    selected_ids = list(screen.get("selected_candidate_ids", []))
    if not selected_ids:
        result = {
            "state": "complete",
            "stage_gate": False,
            "qualification_candidate_ids": [],
            "qualified_candidate_ids": [],
            "candidate_summaries": {},
            "skipped_reason": "screen gate failed",
            "final_audit_trajectory_state": "untouched",
        }
        _write_phase_result(
            output,
            "qualify",
            design_digest,
            result,
            "# Stage 6E qualification\n\nSkipped because the screen failed.",
            "# Lay summary\n\nNo design preserved enough newly written history for the causal challenges.",
            next_phase="endurance",
        )
        return result
    candidates, anchors = _load_models(output, stage6br_root)
    models = _models_by_id([*candidates, *anchors], selected_ids)
    items = ar._make_items(
        cohorts["qualification"],
        models,
        ar._template_pairs(templates, "qualification"),
        frozen["stage4"]["configuration"],
        phase="qualify",
        replicates=profile.qualification_replicates,
        generations=16,
        conditions=conditions,
    )
    rows, complete = ar._run_json_checkpoints(
        output,
        "qualification-trajectories-stage6e",
        items,
        models,
        _phenotype_pair_task,
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
    for candidate in models:
        candidate_id = str(candidate["candidate_id"])
        generation8 = _summary(rows, candidate, 8, profile, contract, "qualification-g8")
        generation16 = _summary(rows, candidate, 16, profile, contract, "qualification-g16")
        summaries[candidate_id] = {
            "candidate": _candidate_public(candidate),
            "generation8": generation8,
            "generation16": generation16,
            "qualification_gate": _qualification_gate(generation8, generation16, contract) if scientific else True,
        }
    ranked = sorted(
        summaries,
        key=lambda candidate_id: (
            -float(summaries[candidate_id]["generation16"]["post_washout_acquisition"].get("mean") or 0.0),
            -float(summaries[candidate_id]["generation16"]["active_rewrite_advantage"].get("mean") or 0.0),
            candidate_id,
        ),
    )
    qualified: list[str] = []
    seen: set[str] = set()
    for candidate_id in ranked:
        candidate_public = summaries[candidate_id]["candidate"]
        group = str(
            candidate_public.get(
                "selection_group",
                summaries[candidate_id]["generation16"]["claim_tier"],
            )
        )
        if summaries[candidate_id]["qualification_gate"] and group not in seen:
            qualified.append(candidate_id)
            seen.add(group)
    if not complete:
        qualified = []
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(qualified),
        "scientific_gate_applied": scientific,
        "qualification_candidate_ids": selected_ids,
        "qualified_candidate_ids": qualified,
        "candidate_summaries": summaries,
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_result(
        output,
        "qualify",
        design_digest,
        result,
        "# Stage 6E qualification\n\nQualified candidates: " + (", ".join(qualified) if qualified else "none"),
        "# Lay summary\n\nThe survivors were erased, shuffled, rescued, reversed, translated, and "
        "separated from both hidden-carrier and temporary-field shortcuts.",
        next_phase="endurance",
    )
    return result


def _run_endurance(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: PhenotypeBridgeProfile,
    contract: PhenotypeBridgeContract,
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
    conditions: Sequence[str] = ENDURANCE_CONDITIONS,
) -> dict[str, Any]:
    qualification = _load_json(output / "qualify/RESULTS.json")
    qualified_ids = list(qualification.get("qualified_candidate_ids", []))
    if not qualified_ids:
        result = {
            "state": "complete",
            "stage_gate": False,
            "endurance_candidate_ids": [],
            "enduring_candidate_ids": [],
            "candidate_summaries": {},
            "skipped_reason": "qualification gate failed",
            "final_audit_trajectory_state": "untouched",
        }
        _write_phase_result(
            output,
            "endurance",
            design_digest,
            result,
            "# Stage 6E endurance\n\nSkipped because qualification failed.",
            "# Lay summary\n\nNo candidate earned the long-generation and scale tests.",
            next_phase="adjudicate",
        )
        return result
    candidates, anchors = _load_models(output, stage6br_root)
    models = _models_by_id([*candidates, *anchors], qualified_ids)
    template_pairs = ar._template_pairs(templates, "qualification")
    items = ar._make_items(
        cohorts["endurance"],
        models,
        template_pairs,
        frozen["stage4"]["configuration"],
        phase="endurance",
        replicates=profile.endurance_replicates,
        generations=64,
        conditions=conditions,
        analysis_kind="lineage",
    )
    for extent in (16, 32, 64):
        for scale_mode in ("fixed", "diameter"):
            items.extend(
                ar._make_items(
                    cohorts["endurance"],
                    models,
                    template_pairs,
                    frozen["stage4"]["configuration"],
                    phase=f"scale-{extent}-{scale_mode}",
                    replicates=profile.endurance_replicates,
                    generations=16,
                    conditions=ENDURANCE_CONDITIONS,
                    extent=extent,
                    scale_mode=scale_mode,
                    analysis_kind="scale",
                )
            )
    for rule in RULE_STRESS_PANEL:
        rule_items = ar._make_items(
            cohorts["endurance"],
            models,
            template_pairs,
            frozen["stage4"]["configuration"],
            phase=f"rule-{rule}",
            replicates=profile.endurance_replicates,
            generations=16,
            conditions=("intact", "sham", "no_rewrite"),
            analysis_kind="rule-stress",
        )
        for item in rule_items:
            item["rule"] = rule
        items.extend(rule_items)
    rows, complete = ar._run_json_checkpoints(
        output,
        "endurance-trajectories-stage6e",
        items,
        models,
        _phenotype_pair_task,
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
    qualification_summaries = qualification["candidate_summaries"]
    for candidate in models:
        candidate_id = str(candidate["candidate_id"])
        lineage_rows = [
            row for row in rows
            if row["analysis_kind"] == "lineage" and row["candidate_id"] == candidate_id
        ]
        generation32 = _summary(lineage_rows, candidate, 32, profile, contract, "endurance-g32")
        generation64 = _summary(lineage_rows, candidate, 64, profile, contract, "endurance-g64")
        scales: dict[str, Any] = {}
        for extent in (16, 32, 64):
            for scale_mode in ("fixed", "diameter"):
                scale_rows = [
                    row for row in rows
                    if row["analysis_kind"] == "scale"
                    and row["candidate_id"] == candidate_id
                    and row["extent"] == extent
                    and row["scale_mode"] == scale_mode
                ]
                scales[f"extent{extent}-{scale_mode}"] = _summary(
                    scale_rows,
                    candidate,
                    16,
                    profile,
                    contract,
                    f"endurance-scale-{extent}-{scale_mode}",
                )
        base_effect = float(
            qualification_summaries[candidate_id]["generation16"]["read_acquisition"].get("mean") or 0.0
        )
        rules: dict[str, Any] = {}
        related_passes = 0
        for rule in RULE_STRESS_PANEL:
            rule_rows = [
                row for row in rows
                if row["analysis_kind"] == "rule-stress"
                and row["candidate_id"] == candidate_id
                and int(row["rule"]) == rule
            ]
            effect = _boot_effect(
                rule_rows,
                candidate_id,
                "intact",
                16,
                profile,
                contract,
                f"rule-{rule}",
            )
            rule_pass = bool(
                rule != 70366
                and float(effect.get("mean") or 0.0) >= 0.70 * base_effect
                and cr._bound(effect, 0, -math.inf) > 0.0
            )
            related_passes += int(rule_pass)
            rules[str(rule)] = {"read_effect": effect, "related_rule_pass": rule_pass}
        gate = _endurance_gate(generation32, generation64, scales, contract) if scientific else True
        summaries[candidate_id] = {
            "candidate": _candidate_public(candidate),
            "generation32": generation32,
            "generation64": generation64,
            "scale": scales,
            "rule_stress": rules,
            "related_rules_passed": related_passes,
            "rule_domain_label": "TRANSFERABLE" if related_passes >= 4 else "RULE_LOCAL",
            "rule_stress_can_rescue": False,
            "endurance_gate": gate,
        }
    enduring = [
        candidate_id for candidate_id in qualified_ids
        if summaries.get(candidate_id, {}).get("endurance_gate")
    ]
    if not complete:
        enduring = []
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(enduring),
        "scientific_gate_applied": scientific,
        "endurance_candidate_ids": qualified_ids,
        "enduring_candidate_ids": enduring,
        "candidate_summaries": summaries,
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_result(
        output,
        "endurance",
        design_digest,
        result,
        "# Stage 6E endurance\n\nEnduring candidates: " + (", ".join(enduring) if enduring else "none"),
        "# Lay summary\n\nThe surviving designs repeatedly rebuilt memory for 64 generations, across "
        "three lattice sizes, and were then moved unchanged to six other rules.",
        next_phase="adjudicate",
    )
    return result


def _update_reserve_state(output: Path, state: str, *, final_digest: str | None = None) -> None:
    path = output / "COHORTS.json"
    payload = _load_json(path)
    payload["final_audit_trajectory_state"] = state
    payload["final_audit_trajectories_not_loaded"] = state == "untouched"
    if final_digest is not None:
        payload["final_audit_digest"] = final_digest
    ar._atomic_json(path, payload)


def _run_adjudication(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: PhenotypeBridgeProfile,
    contract: PhenotypeBridgeContract,
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
    conditions: Sequence[str] = AUDIT_CONDITIONS,
) -> dict[str, Any]:
    endurance = _load_json(output / "endurance/RESULTS.json")
    enduring_ids = list(endurance.get("enduring_candidate_ids", []))
    if not enduring_ids:
        result = {
            "state": "complete",
            "stage_gate": False,
            "finalist_candidate_ids": [],
            "frozen_winner_ids": {},
            "confirmed_candidate_ids": [],
            "confirmed_tiers": [],
            "candidate_summaries": {},
            "final_audit_opened": False,
            "skipped_reason": "endurance gate failed",
            "final_audit_trajectory_state": "untouched",
        }
        _write_phase_result(
            output,
            "adjudicate",
            design_digest,
            result,
            "# Stage 6E adjudication\n\nThe final reserve remained sealed.",
            "# Lay summary\n\nAn exposed-data test failed, so none of the protected cases were inspected.",
            next_phase=None,
        )
        return result
    if scientific and not auto_final_audit:
        raise ValueError("reference Stage-6E final audit lacks authorization")
    candidates, anchors = _load_models(output, stage6br_root)
    by_id = {str(row["candidate_id"]): row for row in [*candidates, *anchors]}
    winners: dict[str, str] = {}
    endurance_summaries = endurance["candidate_summaries"]
    groups = sorted(
        {
            str(
                by_id[candidate_id].get(
                    "selection_group", by_id[candidate_id]["claim_tier"]
                )
            )
            for candidate_id in enduring_ids
        }
    )
    for group in groups:
        group_ids = [
            candidate_id
            for candidate_id in enduring_ids
            if str(
                by_id[candidate_id].get(
                    "selection_group", by_id[candidate_id]["claim_tier"]
                )
            )
            == group
        ]
        ranked = sorted(
            group_ids,
            key=lambda candidate_id: (
                -float(endurance_summaries[candidate_id]["generation64"]["post_washout_acquisition"].get("mean") or 0.0),
                -float(endurance_summaries[candidate_id]["generation64"]["read_acquisition"].get("mean") or 0.0),
                candidate_id,
            ),
        )
        if ranked:
            winners[group] = ranked[0]
    winner_ids = list(winners.values())
    models = _models_by_id([*candidates, *anchors], winner_ids)
    pair_digest = hashlib.sha256("\n".join(frozen["later_ids"]).encode()).hexdigest()
    ar._atomic_json(
        output / "FINAL_AUDIT_DESIGN.json",
        {
            "design_digest": design_digest,
            "winner_ids_by_group": winners,
            "winner_ids_by_tier": winners,
            "winners_frozen_before_pair_loading": True,
            "pair_count": 62 if scientific else profile.final_pairs,
            "pair_ids_sha256": pair_digest if scientific else None,
            "conditions": conditions,
            "templates": [
                (left["template_id"], right["template_id"])
                for left, right in ar._template_pairs(templates, "audit")
            ],
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
            raise ValueError("Stage-6E final reserve is incomplete")
        _update_reserve_state(output, "opened")
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
        conditions=conditions,
        analysis_kind="final",
    )
    rows, complete = ar._run_json_checkpoints(
        output,
        "final-audit-trajectories-stage6e",
        items,
        models,
        _phenotype_pair_task,
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
    summaries: dict[str, Any] = {}
    confirmed: list[str] = []
    for candidate in models:
        candidate_id = str(candidate["candidate_id"])
        generation8 = _summary(rows, candidate, 8, profile, final_contract, "final-g8")
        generation16 = _summary(rows, candidate, 16, profile, final_contract, "final-g16")
        generation64 = _summary(rows, candidate, 64, profile, final_contract, "final-g64")
        gate = _audit_gate(generation8, generation16, generation64, final_contract) if scientific else True
        summaries[candidate_id] = {
            "candidate": _candidate_public(candidate),
            "generation8": generation8,
            "generation16": generation16,
            "generation64": generation64,
            "final_gate": gate,
        }
        if complete and gate:
            confirmed.append(candidate_id)
    final_digest = hashlib.sha256(
        json.dumps(summaries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if scientific:
        reserve_state = "complete" if complete else "partial"
        _update_reserve_state(output, reserve_state, final_digest=final_digest)
    confirmed_tiers = [str(by_id[candidate_id]["claim_tier"]) for candidate_id in confirmed]
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(confirmed),
        "scientific_gate_applied": scientific,
        "finalist_candidate_ids": enduring_ids,
        "frozen_winner_ids": winners,
        "confirmed_candidate_ids": confirmed,
        "confirmed_tiers": confirmed_tiers,
        "candidate_summaries": summaries,
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "final_audit_opened": scientific,
        "final_audit_digest": final_digest,
        "final_audit_trajectory_state": reserve_state,
    }
    _write_phase_result(
        output,
        "adjudicate",
        design_digest,
        result,
        "# Stage 6E adjudication\n\nConfirmed candidates: " + (", ".join(confirmed) if confirmed else "none"),
        "# Lay summary\n\nAt most one strict and one temporary-somatic design were frozen before the "
        "protected cases were opened, and each claim was judged independently.",
        next_phase=None,
    )
    return result


def _campaign_clock(
    output: Path, design_digest: str, max_hours: float, *, resume: bool
) -> dict[str, Any]:
    path = output / "CAMPAIGN.json"
    if path.exists():
        payload = _load_json(path)
        if not resume:
            raise ValueError("Stage-6E output exists; use --resume")
        if payload.get("design_digest") != design_digest:
            raise ValueError("Stage-6E campaign design mismatch")
        if not math.isclose(float(payload["max_hours"]), max_hours):
            raise ValueError("Stage-6E max-hours changed during resume")
        return payload
    started = time.time()
    fraction = PhenotypeBridgeContract().exploration_stop_hours / PhenotypeBridgeContract().max_hours
    payload = {
        "experiment": "ca_motif_phenotype_bridge_stage_6e",
        "design_digest": design_digest,
        "started_unix": started,
        "max_hours": max_hours,
        "hard_deadline_unix": started + max_hours * 3600.0,
        "exploration_deadline_unix": started + max_hours * fraction * 3600.0,
        "adjudication_reserve_hours": max_hours * (1.0 - fraction),
        "deadline_persists_across_resume": True,
    }
    ar._atomic_json(path, payload)
    return payload


def _status_writer(
    output: Path,
    profile_name: str,
    campaign: dict[str, Any],
    active_phase: list[str],
) -> Any:
    def write(state: str, current: str, **extra: Any) -> None:
        phase = active_phase[0]
        cohorts = _load_json(output / "COHORTS.json") if (output / "COHORTS.json").exists() else {}
        payload = {
            "state": state,
            "stage": "ca_motif_phenotype_bridge_stage_6e",
            "profile": profile_name,
            "phase": phase,
            "current": current,
            "pid": os.getpid(),
            "workers_hard_max": PhenotypeBridgeContract().max_workers,
            "started_unix": campaign["started_unix"],
            "updated_unix": time.time(),
            "elapsed_seconds": time.time() - float(campaign["started_unix"]),
            "deadline_remaining_seconds": max(0.0, float(campaign["hard_deadline_unix"]) - time.time()),
            "exploration_deadline_unix": campaign["exploration_deadline_unix"],
            "hard_deadline_unix": campaign["hard_deadline_unix"],
            "final_audit_trajectory_state": cohorts.get("final_audit_trajectory_state", "untouched"),
            **extra,
        }
        ar._atomic_json(output / "STATUS.json", payload)
        if phase in PHASES:
            root = output / phase
            root.mkdir(parents=True, exist_ok=True)
            ar._atomic_json(root / "STATUS.json", payload)
        progress = f" {extra['completed']}/{extra['total']}" if "completed" in extra and "total" in extra else ""
        print(f"[{state}] stage6e-{phase}:{current}{progress}", flush=True)

    return write


def _require_phase(output: Path, phase: str, design_digest: str) -> None:
    path = output / phase / "RESULTS.json"
    if not path.exists() or not (output / phase / "COMPLETE").exists():
        raise ValueError(f"Stage-6E predecessor is incomplete: {phase}")
    if _load_json(path).get("design_digest") != design_digest:
        raise ValueError(f"Stage-6E predecessor design mismatch: {phase}")


def _campaign_verdict(output: Path, scientific: bool) -> str:
    if not scientific:
        return "SMOKE_PATH_VALIDATED"
    phases = {phase: _load_json(output / phase / "RESULTS.json") for phase in PHASES}
    if any(value.get("state") == "budget_truncated" for value in phases.values()):
        return "INCONCLUSIVE_RESOURCE_LIMIT"
    confirmed = set(phases["adjudicate"].get("confirmed_tiers", []))
    if "strict" in confirmed:
        return "STRICT_FORM_MEDIATED_PH_CONFIRMED"
    if "broad" in confirmed:
        return "SOMATICALLY_MEDIATED_PH_CONFIRMED"
    bridge_effects = [
        float(value.get("next_daughter_read_effect", {}).get("mean") or 0.0)
        for value in phases["bridge"].get("validation_summaries", {}).values()
    ]
    if max(bridge_effects, default=0.0) >= PhenotypeBridgeContract().screen_read_minimum:
        return "ONE_GENERATION_BRIDGE_ONLY"
    diagnosis = phases["forensics"].get("diagnosis", {})
    if float(diagnosis.get("generation5_read_effect") or 0.0) >= PhenotypeBridgeContract().screen_read_minimum:
        return "DIRECT_ECHO_ONLY"
    return "NO_RENEWABLE_PHENOTYPE"


def _write_campaign_outputs(
    output: Path,
    design_digest: str,
    profile_name: str,
    scientific: bool,
) -> dict[str, Any]:
    verdict = _campaign_verdict(output, scientific)
    phases = {phase: _load_json(output / phase / "RESULTS.json") for phase in PHASES}
    cohorts = _load_json(output / "COHORTS.json")
    result = {
        "experiment": "ca_motif_phenotype_bridge_stage_6e",
        "design_digest": design_digest,
        "state": "complete",
        "profile_name": profile_name,
        "scientific_gate_applied": scientific,
        "verdict": verdict,
        "stage_gate": bool(phases["adjudicate"].get("confirmed_candidate_ids")),
        "selected_frontends": phases["bridge"].get("selected_frontends", []),
        "selected_candidate_ids": phases["screen"].get("selected_candidate_ids", []),
        "qualified_candidate_ids": phases["qualify"].get("qualified_candidate_ids", []),
        "enduring_candidate_ids": phases["endurance"].get("enduring_candidate_ids", []),
        "frozen_winner_ids": phases["adjudicate"].get("frozen_winner_ids", {}),
        "confirmed_candidate_ids": phases["adjudicate"].get("confirmed_candidate_ids", []),
        "confirmed_tiers": phases["adjudicate"].get("confirmed_tiers", []),
        "final_audit_opened": bool(phases["adjudicate"].get("final_audit_opened", False)),
        "final_audit_trajectory_state": cohorts["final_audit_trajectory_state"],
        "phase_gates": {phase: bool(value.get("stage_gate")) for phase, value in phases.items()},
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
            "final_audit_trajectory_state": result["final_audit_trajectory_state"],
        },
    )
    ar._atomic_text(
        output / "REPORT.md",
        "# Stage 6E phenotype bridge and somatic consolidation\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"Sealed frontends: {[row.get('frontend_id') for row in result['selected_frontends']]}\n\n"
        f"Selected: {result['selected_candidate_ids']}\n\n"
        f"Qualified: {result['qualified_candidate_ids']}\n\n"
        f"Enduring: {result['enduring_candidate_ids']}\n\n"
        f"Frozen winners: {result['frozen_winner_ids']}\n\n"
        f"Confirmed: {result['confirmed_candidate_ids']}\n\n"
        + ("The final reserve was opened under the frozen gate.\n" if result["final_audit_opened"] else "The final reserve was not opened.\n"),
    )
    if verdict == "STRICT_FORM_MEDIATED_PH_CONFIRMED":
        lay = "A daughter rebuilt a learned form after all old and temporary memory was gone, then wrote a fresh note from that visible form."
    elif verdict == "SOMATICALLY_MEDIATED_PH_CONFIRMED":
        lay = "A temporary daughter-side memory helped hold the learned form long enough to write a fresh inherited note, and that temporary memory itself never crossed birth."
    elif verdict == "ONE_GENERATION_BRIDGE_ONLY":
        lay = "The repaired handoff worked once, but repeated daughters could not keep renewing it."
    elif verdict == "DIRECT_ECHO_ONLY":
        lay = "The inherited note could draw the form briefly, but no independently renewed memory survived."
    else:
        lay = "Neither visible persistence nor a temporary daughter field produced renewable acquired form under the registered tests."
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
        },
    )
    ar._atomic_text(output / "COMPLETE", "complete\n")
    return result


def run_motif_phenotype_bridge(
    output: Path,
    *,
    phase: str = "all",
    stage6d_root: Path = DEFAULT_STAGE6D_ROOT,
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
    """Run the frozen Stage-6E phenotype-bridge campaign."""

    ar.require_pinned_numpy()
    if phase not in (*PHASES, "all"):
        raise ValueError(f"unknown Stage-6E phase {phase!r}")
    if profile_name not in PUBLIC_PROFILES:
        raise ValueError(f"unknown Stage-6E profile {profile_name!r}")
    if workers < 1 or workers > PhenotypeBridgeContract().max_workers:
        raise ValueError("Stage-6E workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > PhenotypeBridgeContract().max_hours:
        raise ValueError("Stage-6E max-hours must be in (0, 8]")
    if profile_name == "reference" and not auto_final_audit:
        raise ValueError("reference Stage-6E requires registered automatic final-audit authorization")
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ar._atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
    active_phase = ["prepare"]
    campaign: dict[str, Any] | None = None
    status: Any = None
    try:
        frozen, cohorts, profile, contract, writer_contract, templates, design_digest = _prepare_stage6e(
            output,
            profile_name,
            auto_final_audit=auto_final_audit,
            stage6d_root=stage6d_root,
            stage6c_root=stage6c_root,
            stage6br_root=stage6br_root,
            stage5r_root=stage5r_root,
            stage5_root=stage5_root,
            stage4_root=stage4_root,
            stage3r_root=stage3r_root,
            stage3_root=stage3_root,
            stage2_root=stage2_root,
            stage1_root=stage1_root,
        )
        campaign = _campaign_clock(output, design_digest, max_hours, resume=resume)
        status = _status_writer(output, profile_name, campaign, active_phase)
        status("running", "frozen-design-verified")
        selected_phases = PHASES if phase == "all" else (phase,)
        if phase != "all":
            for predecessor in PHASES[: PHASES.index(phase)]:
                _require_phase(output, predecessor, design_digest)
        scientific = profile_name == "reference"
        common = dict(
            output=output,
            frozen=frozen,
            cohorts=cohorts,
            profile=profile,
            contract=contract,
            writer_contract=writer_contract,
            templates=templates,
            design_digest=design_digest,
        )
        runners = {
            "forensics": lambda: _run_forensics(output, stage6d_root.resolve(), design_digest, status),
            "bridge": lambda: _run_bridge(
                **common,
                stage6br_root=stage6br_root,
                workers=workers,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                status=status,
            ),
            "screen": lambda: _run_screen(
                **common,
                stage6br_root=stage6br_root,
                workers=workers,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                scientific=scientific,
                status=status,
            ),
            "qualify": lambda: _run_qualification(
                **common,
                stage6br_root=stage6br_root,
                workers=workers,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                scientific=scientific,
                status=status,
            ),
            "endurance": lambda: _run_endurance(
                **common,
                stage6br_root=stage6br_root,
                workers=workers,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                scientific=scientific,
                status=status,
            ),
            "adjudicate": lambda: _run_adjudication(
                **common,
                stage6br_root=stage6br_root,
                workers=workers,
                resume=resume,
                deadline=float(campaign["hard_deadline_unix"]),
                scientific=scientific,
                auto_final_audit=auto_final_audit,
                status=status,
            ),
        }
        result: dict[str, Any] = {"state": "not_started"}
        for current_phase in selected_phases:
            active_phase[0] = current_phase
            if resume and (output / current_phase / "COMPLETE").exists():
                result = _load_json(output / current_phase / "RESULTS.json")
                status("completed_phase", "resume-existing-phase")
                continue
            status("running", "phase-start")
            result = runners[current_phase]()
            status("completed_phase", "phase-complete")
        if phase == "all":
            active_phase[0] = "complete"
            result = _write_campaign_outputs(output, design_digest, profile_name, scientific)
            status("complete", "campaign-complete", verdict=result["verdict"])
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
    "ALL_CONDITIONS",
    "DEFAULT_STAGE6D_ROOT",
    "PHASES",
    "PHENOTYPE_BRIDGE_PROFILES",
    "PhenotypeBridgeContract",
    "build_phenotype_bridge_candidates",
    "build_writeback_candidates",
    "run_motif_phenotype_bridge",
    "simulate_phenotype_lineage",
)
