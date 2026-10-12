"""Stage-6C synergistic and acquired-form CA Plastic Heredity tests.

This module consumes immutable clean-room Stage-5R and Stage-6B-R artifacts.
It deliberately does not alter their code, outputs, or decisions.  The final
Stage-5R reserve is loaded only after a Stage-6C design has been sealed and all
developmental gates have passed.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, replace
import hashlib
from itertools import combinations
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Sequence

import numpy as np

from .causal_heredity import (
    _atomic_json,
    _atomic_text,
    _hash_seed,
    _sha256,
    _state_from_hex,
)
from .e19 import require_pinned_numpy
from .life_family import live_2x2_counts_batch
from .motif_compression import _run_json_checkpoints, decode_payload
from .motif_lineage import (
    MotifContract,
    ReaderConfiguration,
    _bootstrap,
    _step,
    apply_energy_reader,
    motif3_codes,
)
from .motif_localization import apply_local_reader
from .motif_minimality import (
    DEFAULT_STAGE1_ROOT,
    DEFAULT_STAGE2_ROOT,
    DEFAULT_STAGE3_ROOT,
    DEFAULT_STAGE3R_ROOT,
    DEFAULT_STAGE4_ROOT,
    DEFAULT_STAGE5_ROOT,
    DEFAULT_STAGE5R_ROOT,
    MINIMALITY_PROFILES,
    RULE,
    _binary_information_lower_bound,
    _configuration_payload,
    _founder_bounded_payload,
    _payload_summary,
    _quantize,
    _resize_board,
    _score_state,
    _swap_histories,
    load_frozen_stage5r,
    select_minimality_cohorts,
)
from .motif_minimality_repair import (
    _condition_values,
    _paired_advantage,
    _semantic_uniforms,
    _transition_summary,
    heldout_lineage_diagnostics,
    toroidal_chebyshev_distance,
)
from .motif_renewal_repair import (
    FULL_ANCHOR_ID,
    _codes_payload,
    _field_distance_summary_multiseed,
    _outside_light_cone_fraction,
    _payload_codes,
    _phenotype_distance_outcomes_multiseed,
    _site_count_moments,
    _window_endpoint,
    candidate_public,
    hamming84_decode,
    hamming84_encode,
    latch_update,
    load_models,
    renewal_seed_origins,
)


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_LINEAGE_STAGE6C_PROTOCOL.md"
DEFAULT_STAGE6BR_ROOT = ROOT / "results/ca-motif-lineage-stage-6br"
PHASES = ("forensics", "synergy", "plasticity", "endurance", "adjudicate")
SOURCE_MODEL_ID = "renew-h05-wcentered-5-flocal-rollout-r75-eh84"
REPLICATED_CONTROL_ID = (
    "stage6c-control-replicated-k04-h05-r75-eh84"
)
PARTITIONED_CONTROL_IDS = (
    "stage6c-control-partitioned-k02-h07-r75-eh84",
    "stage6c-control-partitioned-k04-h07-r75-eh84",
)
ANCHOR_CONTROL_ID = "stage6c-control-whole-lattice"

SCREEN_CONDITIONS = (
    "intact",
    "no_rewrite",
    "communication_cut_vertical",
    "communication_cut_horizontal",
    "carrier_corruption_1",
    "translated_patch",
)
FULL_CONDITIONS = (
    "intact",
    "zero_every_boundary",
    "shuffle_every_boundary",
    "read_disabled",
    "founder_write_disabled",
    "write_disabled",
    "no_rewrite",
    "ablate_after_g2",
    "rescue_same_enter_g4",
    "rescue_opposite_enter_g4",
    "opposite_founder",
    "carrier_corruption_1",
    "transport_disabled",
    "regeneration_disabled",
    "translated_patch",
    "communication_cut_vertical",
    "communication_cut_horizontal",
    "germination_cut_vertical",
    "write_cut_vertical",
    "proper_subset",
    "share_swap_one_g4",
    "founder_clamped",
)
FINAL_CONDITIONS = (
    "intact",
    "zero_every_boundary",
    "shuffle_every_boundary",
    "read_disabled",
    "founder_write_disabled",
    "write_disabled",
    "no_rewrite",
    "rescue_same_enter_g4",
    "rescue_opposite_enter_g4",
    "transport_disabled",
    "regeneration_disabled",
    "translated_patch",
    "communication_cut_vertical",
    "communication_cut_horizontal",
    "proper_subset",
)


@dataclass(frozen=True)
class SynergyContract:
    implementation_version: str = "ca-motif-lineage-stage6c-cleanroom-v1"
    namespace: str = "plastic-ca-motif-lineage-stage6c-v1"
    rule: int = RULE
    generation_sweeps: int = 64
    read_sweeps: int = 32
    write_start: int = 49
    write_end: int = 64
    observe_start: int = 57
    acquisition_generation: int = 4
    acquisition_start: int = 41
    acquisition_end: int = 48
    process_noise: float = 0.002
    bit_corruption: float = 0.01
    strict_alpha: float = 0.025
    screen_generation8: float = 0.15
    qualification_generation16: float = 0.10
    active_advantage_minimum: float = 0.05
    acquisition_minimum: float = 0.10
    subset_accuracy_maximum: float = 0.60
    joint_accuracy_minimum: float = 0.75
    survival_gate: float = 0.90
    translation_retention: float = 0.70
    anchor_retention: float = 0.70
    loss_fraction: float = 0.70
    rescue_fraction: float = 0.70
    decoder_splits: int = 4
    max_workers: int = 4
    max_hours: float = 8.0
    exploration_stop_hours: float = 5.5
    adjudication_reserve_hours: float = 2.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {
            "visible_reset": "bitwise-identical matched board before every generation",
            "share_algebra": "k-of-k XOR over four-bit quantized channels",
            "runtime_labels": False,
            "random_streams": "semantic, paired, order and worker independent",
            "claim_boundary": "engineered synthetic CA heredity",
        }

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.to_dict(), sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()


@dataclass(frozen=True)
class SynergyProfile:
    screen_pairs: int
    screen_replicates: int
    qualification_pairs: int
    qualification_replicates: int
    scale_pairs: int
    scale_replicates: int
    endurance_pairs: int
    endurance_replicates: int
    final_pairs: int
    final_replicates: int
    bootstrap_resamples: int
    screen_candidate_limit: int


SYNERGY_PROFILES: dict[str, SynergyProfile] = {
    "smoke": SynergyProfile(2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 100, 4),
    "pilot": SynergyProfile(12, 4, 24, 4, 8, 2, 8, 4, 8, 4, 1_000, 12),
    "reference": SynergyProfile(
        32, 4, 64, 8, 24, 4, 24, 8, 62, 4, 10_000, 24
    ),
}
PUBLIC_PROFILES = tuple(SYNERGY_PROFILES)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def xor_share_codes(
    codes: np.ndarray, share_count: int, seed: int
) -> np.ndarray:
    """Return perfect k-of-k XOR shares of four-bit channel codes."""

    values = np.asarray(codes, dtype=np.uint8)
    if share_count not in (2, 4):
        raise ValueError("Stage-6C XOR sharing requires two or four shares")
    if np.any(values > 15):
        raise ValueError("XOR inputs must be four-bit codes")
    random = np.random.default_rng(seed).integers(
        0, 16, size=values.shape + (share_count - 1,), dtype=np.uint8
    )
    random = np.moveaxis(random, -1, -2)
    final = values.copy()
    for index in range(share_count - 1):
        final ^= random[..., index, :]
    return np.concatenate((random, final[..., None, :]), axis=-2)


def xor_reconstruct_codes(shares: np.ndarray) -> np.ndarray:
    values = np.asarray(shares, dtype=np.uint8)
    if values.ndim < 2 or values.shape[-2] not in (2, 4):
        raise ValueError("XOR shares require a two- or four-valued share axis")
    if np.any(values > 15):
        raise ValueError("XOR shares must contain four-bit codes")
    return np.bitwise_xor.reduce(values, axis=-2)


def carrier_code_roundtrip(
    codes: np.ndarray, ecc: str, flips: np.ndarray | None = None
) -> tuple[np.ndarray, float]:
    """Transmit exact four-bit share codes, optionally through Hamming SECDED."""

    values = np.asarray(codes, dtype=np.uint8) & np.uint8(0x0F)
    if ecc == "none":
        bits = (
            (values[..., None] >> np.arange(4, dtype=np.uint8)) & 1
        ).astype(np.uint8)
        if flips is not None:
            bits ^= np.asarray(flips, dtype=np.uint8)
        decoded = np.sum(
            bits << np.arange(4, dtype=np.uint8), axis=-1
        ).astype(np.uint8)
        uncorrectable = np.zeros(decoded.shape, dtype=np.bool_)
    elif ecc == "hamming84":
        bits = hamming84_encode(values)
        if flips is not None:
            bits ^= np.asarray(flips, dtype=np.uint8)
        decoded, uncorrectable = hamming84_decode(bits)
    else:
        raise ValueError(f"unknown Stage-6C ECC mode {ecc!r}")
    return decoded, float(np.mean(uncorrectable))


def acquisition_templates(contract: SynergyContract) -> list[dict[str, Any]]:
    """Create 20 frozen density-balanced motifs as ten complement pairs."""

    rows: list[dict[str, Any]] = []
    for pair_index in range(10):
        rng = np.random.default_rng(
            _hash_seed(contract.namespace, "acquisition-template", pair_index)
        )
        flat = np.zeros(16, dtype=np.bool_)
        flat[rng.choice(16, size=8, replace=False)] = True
        for complement in (False, True):
            value = ~flat if complement else flat
            index = len(rows)
            split = "development" if index < 8 else (
                "qualification" if index < 16 else "audit"
            )
            rows.append(
                {
                    "template_id": f"acq-{index:02d}",
                    "split": split,
                    "complement_pair": pair_index,
                    "bits_hex": f"{int(''.join('1' if bit else '0' for bit in value), 2):04x}",
                    "bits": value.reshape(4, 4).astype(np.uint8).tolist(),
                    "live_cells": int(np.sum(value)),
                }
            )
    return rows


def _candidate_public(candidate: dict[str, Any]) -> dict[str, Any]:
    return candidate_public(candidate) | {
        "share_scheme": candidate.get("share_scheme", "single"),
        "joint_read_required": bool(candidate.get("joint_read_required", False)),
    }


def build_synergy_candidates(
    stage6br_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    design = _load_json(stage6br_root / "DESIGN.json")
    models = load_models(stage6br_root, str(design["design_digest"]))
    by_id = {str(row["candidate_id"]): row for row in models}
    if SOURCE_MODEL_ID not in by_id:
        raise ValueError("frozen Stage-6B-R source model is missing")
    if FULL_ANCHOR_ID not in by_id:
        raise ValueError("frozen Stage-6B-R whole-lattice anchor is missing")
    source = by_id[SOURCE_MODEL_ID]
    candidates: list[dict[str, Any]] = []
    for share_count in (2, 4):
        for hops in (5, 6, 7):
            for rho in (0.25, 0.50):
                for ecc in ("none", "hamming84"):
                    ecc_id = "raw" if ecc == "none" else "h84"
                    candidates.append(
                        {
                            **source,
                            "candidate_id": (
                                f"synergy-xor-k{share_count:02d}-h{hops:02d}-"
                                f"r{int(rho * 100):02d}-e{ecc_id}"
                            ),
                            "share_scheme": "xor-kofk",
                            "seed_mode": "secret-shared",
                            "seed_count": share_count,
                            "germination_hops": hops,
                            "rho": rho,
                            "ecc": ecc,
                            "joint_read_required": True,
                            "promotable": True,
                            "bounded": True,
                        }
                    )
    controls = [
        {
            **source,
            "candidate_id": REPLICATED_CONTROL_ID,
            "share_scheme": "replicated",
            "seed_mode": "replicated",
            "seed_count": 4,
            "germination_hops": 5,
            "rho": 0.75,
            "ecc": "hamming84",
            "joint_read_required": False,
            "promotable": False,
        },
        {
            **source,
            "candidate_id": PARTITIONED_CONTROL_IDS[0],
            "share_scheme": "partitioned",
            "seed_mode": "partitioned",
            "seed_count": 2,
            "germination_hops": 7,
            "rho": 0.75,
            "ecc": "hamming84",
            "joint_read_required": True,
            "promotable": False,
        },
        {
            **source,
            "candidate_id": PARTITIONED_CONTROL_IDS[1],
            "share_scheme": "partitioned",
            "seed_mode": "partitioned",
            "seed_count": 4,
            "germination_hops": 7,
            "rho": 0.75,
            "ecc": "hamming84",
            "joint_read_required": True,
            "promotable": False,
        },
    ]
    anchor = {
        **by_id[FULL_ANCHOR_ID],
        "candidate_id": ANCHOR_CONTROL_ID,
        "share_scheme": "single",
        "seed_mode": "single",
        "seed_count": 1,
        "joint_read_required": False,
        "promotable": False,
        "bounded": False,
    }
    if len(candidates) != 24:
        raise AssertionError("Stage-6C secret-sharing grid must contain 24 candidates")
    return candidates, controls, anchor


def _share_masks(candidate: dict[str, Any], rank: int) -> np.ndarray:
    count = int(candidate["seed_count"])
    scheme = str(candidate["share_scheme"])
    masks = np.ones((count, rank), dtype=np.bool_)
    if scheme == "partitioned":
        masks.fill(False)
        for channel in range(rank):
            masks[channel % count, channel] = True
    return masks


def _encode_carrier(
    payload: np.ndarray,
    candidate: dict[str, Any],
    contract: SynergyContract,
    pair_id: str,
    generation: int,
    purpose: str = "write",
) -> tuple[np.ndarray, np.ndarray]:
    codes = _payload_codes(payload, candidate["codec_model"])
    count = int(candidate["seed_count"])
    scheme = str(candidate["share_scheme"])
    if scheme == "xor-kofk":
        shares = xor_share_codes(
            codes,
            count,
            _hash_seed(
                contract.namespace,
                pair_id,
                "share-mask",
                purpose,
                generation,
                count,
            ),
        )
    elif scheme == "replicated":
        shares = np.repeat(codes[:, None, :], count, axis=1)
    elif scheme == "partitioned":
        masks = _share_masks(candidate, codes.shape[-1])
        shares = np.repeat(codes[:, None, :], count, axis=1)
        shares[~np.broadcast_to(masks[None, :, :], shares.shape)] = 0
    elif scheme == "single":
        shares = codes[:, None, :]
    else:
        raise ValueError(f"unknown Stage-6C share scheme {scheme!r}")
    active = np.broadcast_to(
        _share_masks(candidate, codes.shape[-1])[None, :, :], shares.shape
    ).copy()
    return shares.astype(np.uint8), active


def _joint_payload(
    shares: np.ndarray,
    active: np.ndarray,
    candidate: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(shares, dtype=np.uint8)
    present = np.asarray(active, dtype=np.bool_)
    scheme = str(candidate["share_scheme"])
    codec = candidate["codec_model"]
    if scheme == "xor-kofk":
        valid = np.all(present, axis=(1, 2))
        codes = xor_reconstruct_codes(values)
    elif scheme == "partitioned":
        masks = _share_masks(candidate, values.shape[-1])
        required = np.broadcast_to(masks[None, :, :], present.shape)
        valid = np.all(np.logical_or(~required, present), axis=(1, 2))
        codes = np.bitwise_or.reduce(
            np.where(required, values, np.uint8(0)), axis=1
        )
    elif scheme in ("replicated", "single"):
        seed_valid = np.all(present, axis=2)
        valid = np.any(seed_valid, axis=1)
        first = np.argmax(seed_valid, axis=1)
        codes = values[np.arange(values.shape[0]), first]
    else:
        raise ValueError(f"unknown share scheme {scheme!r}")
    payload = _codes_payload(codes, codec)
    payload[~valid] = 0.0
    return payload, valid


def _barrier_shift(
    values: np.ndarray,
    occupied: np.ndarray,
    dy: int,
    dx: int,
    cut_axis: str | None,
) -> tuple[np.ndarray, np.ndarray]:
    shifted_values = np.roll(values, (dy, dx), axis=(1, 2))
    shifted_occupied = np.roll(occupied, (dy, dx), axis=(1, 2))
    extent = values.shape[1]
    if cut_axis in ("vertical", "both") and dx:
        columns = (0, extent // 2) if dx == 1 else (
            extent - 1,
            extent // 2 - 1,
        )
        for column in columns:
            shifted_values[:, :, column] = 0.0
            shifted_occupied[:, :, column] = False
    if cut_axis in ("horizontal", "both") and dy:
        rows = (0, extent // 2) if dy == 1 else (
            extent - 1,
            extent // 2 - 1,
        )
        for row in rows:
            shifted_values[:, row, :] = 0.0
            shifted_occupied[:, row, :] = False
    return shifted_values, shifted_occupied


def propagate_share_channels(
    shares: np.ndarray,
    active: np.ndarray,
    origins: np.ndarray,
    extent: int,
    hops: int,
    *,
    cut_axis: str | None = None,
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    """Propagate every seed/share channel independently by local copying."""

    values = np.asarray(shares, dtype=np.float32)
    enabled = np.asarray(active, dtype=np.bool_)
    samples, seed_count, rank = values.shape
    field = np.zeros(
        (samples, extent, extent, seed_count, rank), dtype=np.float32
    )
    occupied = np.zeros(field.shape, dtype=np.bool_)
    for sample in range(samples):
        for seed in range(seed_count):
            y, x = np.asarray(origins[sample, seed], dtype=np.int64)
            mask = enabled[sample, seed]
            field[sample, y, x, seed, mask] = values[sample, seed, mask]
            occupied[sample, y, x, seed, mask] = True
    trace: list[float] = []
    for _ in range(hops):
        count = np.zeros(occupied.shape, dtype=np.int16)
        total = np.zeros(field.shape, dtype=np.float64)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if not (dy or dx):
                    continue
                shifted, shifted_occ = _barrier_shift(
                    field.astype(np.float64) * occupied,
                    occupied,
                    dy,
                    dx,
                    cut_axis,
                )
                count += shifted_occ
                total += shifted
        new = (~occupied) & (count > 0)
        numerator = total + field.astype(np.float64) * occupied
        denominator = count + occupied.astype(np.int16)
        averaged = np.divide(
            numerator,
            denominator,
            out=np.zeros_like(numerator),
            where=denominator > 0,
        )
        field[occupied | new] = averaged[occupied | new]
        occupied |= new
        trace.append(float(np.mean(np.any(occupied, axis=(3, 4)))))
    return field, occupied, trace


def reconstruct_share_field(
    carrier_field: np.ndarray,
    carrier_occupied: np.ndarray,
    candidate: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    """Expose a reader field only where the registered shares have met."""

    values = np.rint(np.asarray(carrier_field)).astype(np.uint8) & np.uint8(15)
    occupied = np.asarray(carrier_occupied, dtype=np.bool_)
    scheme = str(candidate["share_scheme"])
    codec = candidate["codec_model"]
    if scheme == "xor-kofk":
        channel_complete = np.all(occupied, axis=3)
        codes = np.bitwise_xor.reduce(values, axis=3)
        complete = np.all(channel_complete, axis=-1)
    elif scheme == "partitioned":
        masks = _share_masks(candidate, values.shape[-1])
        required = masks[None, None, None, :, :]
        channel_complete = np.any(occupied & required, axis=3)
        codes = np.bitwise_or.reduce(
            np.where(required, values, np.uint8(0)), axis=3
        )
        complete = np.all(channel_complete, axis=-1)
    elif scheme in ("replicated", "single"):
        seed_complete = np.all(occupied, axis=-1)
        complete = np.any(seed_complete, axis=3)
        first = np.argmax(seed_complete, axis=3)
        gather = np.broadcast_to(
            first[..., None, None], values.shape[:3] + (1, values.shape[-1])
        )
        codes = np.take_along_axis(values, gather, axis=3)[..., 0, :]
    else:
        raise ValueError(f"unknown share scheme {scheme!r}")
    decoded = _codes_payload(codes, codec)
    if bool(candidate.get("joint_read_required", False)):
        decoded[~complete] = 0.0
    return decoded.astype(np.float32), complete


def _carrier_diagnostics(
    shares: np.ndarray,
    active: np.ndarray,
    candidate: dict[str, Any],
    replicates: int,
    seed: int,
    splits: int,
) -> dict[str, Any]:
    payload, valid = _joint_payload(shares, active, candidate)
    joint = heldout_lineage_diagnostics(payload, replicates, seed, splits)
    count = int(candidate["seed_count"])
    subset_accuracies: list[float] = []
    if count > 1:
        for size in range(1, count):
            for subset in combinations(range(count), size):
                feature = np.asarray(shares[:, subset, :], dtype=np.float32)
                feature = feature.reshape(feature.shape[0], -1) / np.float32(15.0)
                diag = heldout_lineage_diagnostics(
                    feature,
                    replicates,
                    _hash_seed(seed, "proper-subset", subset),
                    splits,
                )
                subset_accuracies.append(float(diag["balanced_accuracy"]))
    else:
        subset_accuracies.append(1.0)
    subset_max = float(max(subset_accuracies))
    return {
        "joint_balanced_accuracy": float(joint["balanced_accuracy"]),
        "joint_tie_fraction": float(joint["tie_fraction"]),
        "joint_information_lower_bound_bits": _binary_information_lower_bound(
            float(joint["balanced_accuracy"])
        ),
        "proper_subset_balanced_accuracy_max": subset_max,
        "proper_subset_balanced_accuracy_mean": float(
            np.mean(subset_accuracies)
        ),
        "proper_subset_balanced_accuracies": subset_accuracies,
        "proper_subset_count": len(subset_accuracies),
        "joint_complete_fraction": float(np.mean(valid)),
    }


def _apply_acquisition(
    state: np.ndarray,
    origins: np.ndarray,
    template: np.ndarray,
) -> None:
    extent = state.shape[1]
    offsets = np.arange(-2, 2, dtype=np.int64)
    for sample in range(len(state)):
        y, x = np.asarray(origins[sample, 0], dtype=np.int64)
        ys = (y + offsets) % extent
        xs = (x + offsets) % extent
        state[sample][np.ix_(ys, xs)] = template


def _acquisition_match(
    state: np.ndarray,
    origins: np.ndarray,
    template: np.ndarray,
) -> np.ndarray:
    extent = state.shape[1]
    offsets = np.arange(-2, 2, dtype=np.int64)
    target = np.where(template, 1.0, -1.0)
    values = np.zeros(len(state), dtype=np.float64)
    for sample in range(len(state)):
        y, x = np.asarray(origins[sample, 0], dtype=np.int64)
        ys = (y + offsets) % extent
        xs = (x + offsets) % extent
        observed = np.where(state[sample][np.ix_(ys, xs)], 1.0, -1.0)
        values[sample] = float(np.mean(observed * target))
    return values


def _intervene_carrier(
    shares: np.ndarray,
    active: np.ndarray,
    candidate: dict[str, Any],
    condition: str,
    generation: int,
    pair_id: str,
    replicates: int,
    source_exits: Sequence[tuple[np.ndarray, np.ndarray]] | None,
    contract: SynergyContract,
) -> tuple[np.ndarray, np.ndarray, float]:
    values = np.asarray(shares, dtype=np.uint8).copy()
    present = np.asarray(active, dtype=np.bool_).copy()
    if condition == "zero_every_boundary":
        present.fill(False)
    elif condition == "shuffle_every_boundary":
        permutation = np.random.default_rng(
            _hash_seed(contract.namespace, pair_id, "channel-shuffle", generation)
        ).permutation(values.shape[-1])
        values = values[..., permutation]
        present = present[..., permutation]
    elif condition == "opposite_founder" and generation == 1:
        values = _swap_histories(values, replicates)
        present = _swap_histories(present, replicates)
    elif condition in (
        "ablate_after_g2",
        "rescue_same_enter_g4",
        "rescue_opposite_enter_g4",
    ) and generation == 3:
        present.fill(False)
    elif condition in (
        "rescue_same_enter_g4",
        "rescue_opposite_enter_g4",
    ) and generation == 4:
        if source_exits is None or len(source_exits) < 3:
            raise ValueError("Stage-6C rescue requires intact-sister exits")
        values = np.asarray(source_exits[2][0], dtype=np.uint8).copy()
        present = np.asarray(source_exits[2][1], dtype=np.bool_).copy()
        if condition == "rescue_opposite_enter_g4":
            values = _swap_histories(values, replicates)
            present = _swap_histories(present, replicates)
    elif condition == "share_swap_one_g4" and generation == 4:
        if source_exits is None or len(source_exits) < 3:
            raise ValueError("share swap requires intact-sister exits")
        values = np.asarray(source_exits[2][0], dtype=np.uint8).copy()
        present = np.asarray(source_exits[2][1], dtype=np.bool_).copy()
        values[:, 0] = _swap_histories(values[:, 0], replicates)
        present[:, 0] = _swap_histories(present[:, 0], replicates)
    uncorrectable = 0.0
    flips = None
    if condition == "carrier_corruption_1":
        bit_count = 8 if candidate.get("ecc") == "hamming84" else 4
        half = np.random.default_rng(
            _hash_seed(contract.namespace, pair_id, "bit-corruption", generation)
        ).random(
            (replicates, values.shape[1], values.shape[2], bit_count)
        ) < contract.bit_corruption
        flips = np.concatenate((half, half), axis=0)
    values, uncorrectable = carrier_code_roundtrip(
        values, str(candidate.get("ecc", "none")), flips
    )
    return values, present, uncorrectable


def _decay_carrier(
    shares: np.ndarray,
    active: np.ndarray,
    rho: float,
    contract: SynergyContract,
    pair_id: str,
    generation: int,
) -> tuple[np.ndarray, np.ndarray]:
    if not 0.0 <= rho <= 1.0:
        raise ValueError("carrier turnover must be in [0, 1]")
    samples = np.asarray(active).shape[0]
    if samples % 2:
        raise ValueError("paired carrier decay requires two equal histories")
    half = np.random.default_rng(
        _hash_seed(contract.namespace, pair_id, "passive-retention", generation)
    ).random((samples // 2, *np.asarray(active).shape[1:])) < rho
    retain = np.concatenate((half, half), axis=0)
    return np.asarray(shares, dtype=np.uint8).copy(), np.asarray(active) & retain


def _inconsistent_write(
    proposals: np.ndarray,
    entry_payload: np.ndarray,
    candidate: dict[str, Any],
    contract: SynergyContract,
    pair_id: str,
    generation: int,
) -> tuple[np.ndarray, np.ndarray]:
    count = int(candidate["seed_count"])
    rows: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    for seed in range(count):
        latent, _ = latch_update(
            entry_payload,
            proposals[:, seed],
            float(candidate["rho"]),
            candidate["codec_model"],
        )
        values, active = _encode_carrier(
            latent,
            candidate,
            contract,
            pair_id,
            generation,
            purpose=f"disconnected-writer-{seed}",
        )
        rows.append(values[:, seed])
        masks.append(active[:, seed])
    return np.stack(rows, axis=1), np.stack(masks, axis=1)


def simulate_synergistic_lineage(
    pair: dict[str, Any],
    configuration: ReaderConfiguration,
    candidate: dict[str, Any],
    condition: str,
    replicates: int,
    generations: int,
    reference: dict[int, dict[str, np.ndarray]],
    writer_contract: MotifContract,
    contract: SynergyContract,
    *,
    extent: int = 16,
    source_exits: Sequence[tuple[np.ndarray, np.ndarray]] | None = None,
    retain_exits: bool = False,
    acquisition_template: np.ndarray | None = None,
    apply_acquisition: bool = True,
) -> tuple[dict[str, Any], list[tuple[np.ndarray, np.ndarray]]]:
    """Run a visible-reset lineage whose boundary state is distributed shares."""

    if condition not in FULL_CONDITIONS:
        raise ValueError(f"unknown Stage-6C condition {condition!r}")
    if extent not in (16, 32, 64):
        raise ValueError("Stage-6C extents are 16, 32, and 64")
    pair_id = str(pair["pair_id"])
    reset_a = _resize_board(
        _state_from_hex("life", pair["donor_a"]["initial_state_hex"]), extent
    )
    reset_b = _resize_board(
        _state_from_hex("life", pair["donor_b"]["initial_state_hex"]), extent
    )
    if not np.array_equal(reset_a, reset_b):
        raise AssertionError(f"visible reset mismatch in pair {pair_id}")
    reset = np.repeat(reset_a[None], 2 * replicates, axis=0)
    reference_probability = reference[configuration.write_window][
        "motif_probability"
    ]
    founder, founder_terminal = _founder_bounded_payload(
        pair,
        candidate,
        reference_probability,
        replace(writer_contract, rule=contract.rule),
        replicates,
        extent,
        contract.rule,
    )
    shares, active = _encode_carrier(
        founder, candidate, contract, pair_id, 0, purpose="founder"
    )
    founder_shares = shares.copy()
    founder_active = active.copy()
    if condition == "founder_write_disabled":
        active.fill(False)
    alive = np.ones(2 * replicates, dtype=np.bool_)
    checkpoints = {
        value
        for value in (1, 2, 4, 6, 8, 16, 32, 64)
        if value <= generations
    }
    outcomes: dict[str, Any] = {}
    decoders: dict[str, Any] = {}
    carrier_history: dict[str, Any] = {}
    writer_history: dict[str, Any] = {}
    origin_history: dict[str, Any] = {}
    acquisition_history: dict[str, Any] = {}
    exits: list[tuple[np.ndarray, np.ndarray]] = []
    coverage_values: list[float] = []
    uncorrectable_values: list[float] = []
    codec = candidate["codec_model"]
    basis = np.asarray(codec["basis"], dtype=np.float32)
    signs = basis.astype(np.float64) * math.sqrt(512.0)
    write_sweeps = contract.write_end - contract.write_start + 1
    alpha = float(writer_contract.jeffreys_alpha)
    seed_count = int(candidate["seed_count"])
    hops = int(candidate["germination_hops"])
    rho = float(candidate["rho"])
    origin_policy = str(candidate.get("origin_policy", "co-located"))
    template = (
        np.asarray(acquisition_template, dtype=np.bool_)
        if acquisition_template is not None
        else None
    )
    if template is not None and template.shape != (4, 4):
        raise ValueError("acquisition template must be 4x4")

    for generation in range(1, generations + 1):
        shares, active, uncorrectable = _intervene_carrier(
            shares,
            active,
            candidate,
            condition,
            generation,
            pair_id,
            replicates,
            source_exits,
            contract,
        )
        uncorrectable_values.append(uncorrectable)
        entry_shares = shares.copy()
        entry_active = active.copy()
        entry_payload, _ = _joint_payload(
            entry_shares, entry_active, candidate
        )
        translated = condition == "translated_patch"
        origins = renewal_seed_origins(
            pair_id,
            generation,
            replicates,
            extent,
            seed_count,
            origin_policy,
            translated=translated,
        )
        next_origins = renewal_seed_origins(
            pair_id,
            generation + 1,
            replicates,
            extent,
            seed_count,
            origin_policy,
            translated=translated,
        )
        field_active = entry_active.copy()
        if condition == "proper_subset":
            field_active[:, -1] = False
        cut_axis: str | None = None
        if condition in (
            "communication_cut_vertical",
            "germination_cut_vertical",
        ):
            cut_axis = "vertical"
        elif condition == "communication_cut_horizontal":
            cut_axis = "horizontal"
        effective_hops = 0 if condition == "transport_disabled" else hops
        carrier_field, carrier_occupied, wave_trace = propagate_share_channels(
            entry_shares,
            field_active,
            origins,
            extent,
            effective_hops,
            cut_axis=cut_axis,
        )
        field, occupied = reconstruct_share_field(
            carrier_field, carrier_occupied, candidate
        )
        writer_connected = np.any(occupied, axis=(1, 2))
        if condition == "germination_cut_vertical":
            writer_field, writer_occupied, _ = propagate_share_channels(
                entry_shares,
                entry_active,
                origins,
                extent,
                effective_hops,
                cut_axis=None,
            )
            _, writer_complete = reconstruct_share_field(
                writer_field, writer_occupied, candidate
            )
            writer_connected = np.any(writer_complete, axis=(1, 2))
        if condition == "regeneration_disabled":
            field.fill(0.0)
            occupied.fill(False)
        coverage_values.append(float(np.mean(occupied)))
        field_distance = _field_distance_summary_multiseed(
            field, occupied, origins
        )
        outside_light_cone = _outside_light_cone_fraction(
            occupied, origins, effective_hops
        )
        state = reset.copy()
        state[~alive] = False
        recent: deque[np.ndarray] = deque(
            maxlen=writer_contract.observation_window
        )
        site_sign_sum = np.zeros(
            (2 * replicates, extent, extent, int(candidate["rank"])),
            dtype=np.float64,
        )
        for sweep in range(1, contract.generation_sweeps + 1):
            predicted = _step(state, contract.rule)
            if condition != "read_disabled" and sweep <= contract.read_sweeps:
                uniforms = _semantic_uniforms(
                    pair_id, "stage6c-read", generation, sweep, replicates, extent
                )
                if np.all(occupied) and np.array_equal(
                    field, np.broadcast_to(field[:, :1, :1], field.shape)
                ):
                    predicted = apply_energy_reader(
                        predicted,
                        decode_payload(field[:, 0, 0], codec),
                        uniforms,
                        configuration.strength,
                    )
                else:
                    predicted = apply_local_reader(
                        predicted,
                        field,
                        basis,
                        uniforms,
                        configuration.strength,
                    )
            predicted ^= _semantic_uniforms(
                pair_id, "stage6c-process", generation, sweep, replicates, extent
            ) < contract.process_noise
            predicted[~alive] = False
            if (
                template is not None
                and apply_acquisition
                and generation == contract.acquisition_generation
                and contract.acquisition_start <= sweep <= contract.acquisition_end
            ):
                _apply_acquisition(predicted, origins, template)
            state = predicted
            if contract.write_start <= sweep <= contract.write_end:
                site_sign_sum += signs[motif3_codes(state)]
            if sweep >= contract.observe_start:
                recent.append(live_2x2_counts_batch(state))
        alive &= state.any(axis=(1, 2))

        moment_rows: list[np.ndarray] = []
        site_count = 1
        routing_steps = 0
        for seed in range(seed_count):
            endpoint, site_count, routing_steps = _window_endpoint(
                site_sign_sum,
                candidate,
                next_origins[:, seed],
                disabled=False,
            )
            moment_rows.append(
                _site_count_moments(
                    endpoint, signs, site_count, write_sweeps, alpha
                )
            )
        moments = np.stack(moment_rows, axis=1)
        proposals = (
            moments @ np.asarray(candidate["weight"], dtype=np.float64)
            + np.asarray(candidate["bias"], dtype=np.float64)
        ).astype(np.float32)
        proposal = np.mean(proposals, axis=1)
        proposal, _ = _quantize(proposal, codec)
        if condition == "write_disabled":
            next_shares = entry_shares.copy()
            next_active = np.zeros_like(entry_active)
        elif condition == "founder_clamped":
            next_shares, next_active = _encode_carrier(
                founder,
                candidate,
                contract,
                pair_id,
                generation,
                purpose="founder-clamp",
            )
        elif condition == "no_rewrite":
            next_shares, next_active = _decay_carrier(
                entry_shares,
                entry_active,
                rho,
                contract,
                pair_id,
                generation,
            )
        elif condition in (
            "write_cut_vertical",
            "communication_cut_vertical",
            "communication_cut_horizontal",
        ) or not bool(np.all(writer_connected | ~alive)):
            next_shares, next_active = _inconsistent_write(
                proposals,
                entry_payload,
                candidate,
                contract,
                pair_id,
                generation,
            )
        else:
            latent, _ = latch_update(
                entry_payload,
                proposal,
                rho,
                codec,
            )
            next_shares, next_active = _encode_carrier(
                latent, candidate, contract, pair_id, generation
            )
        shares = next_shares
        active = next_active
        active[~alive] = False

        if generation in checkpoints:
            outcome, phenotype = _score_state(
                state,
                recent,
                pair,
                founder_terminal,
                replicates,
                writer_contract,
            )
            outcome["distance_bands"] = _phenotype_distance_outcomes_multiseed(
                state,
                origins,
                pair,
                alive,
                replicates,
                writer_contract,
                hops,
            )
            outcomes[str(generation)] = outcome
            diagnostic = _carrier_diagnostics(
                shares,
                active,
                candidate,
                replicates,
                _hash_seed(
                    contract.namespace,
                    pair_id,
                    condition,
                    generation,
                    "carrier",
                ),
                contract.decoder_splits,
            )
            phenotype_decoder = heldout_lineage_diagnostics(
                phenotype,
                replicates,
                _hash_seed(
                    contract.namespace,
                    pair_id,
                    condition,
                    generation,
                    "phenotype",
                ),
                contract.decoder_splits,
            )
            decoders[str(generation)] = diagnostic | {
                "phenotype_balanced_accuracy": phenotype_decoder[
                    "balanced_accuracy"
                ],
                "phenotype_tie_fraction": phenotype_decoder["tie_fraction"],
            }
            exit_payload, exit_valid = _joint_payload(shares, active, candidate)
            carrier_history[str(generation)] = {
                "entry": _payload_summary(entry_payload, replicates),
                "exit": _payload_summary(exit_payload, replicates),
                "transition": _transition_summary(
                    entry_payload, exit_payload, replicates
                ),
                "joint_complete_fraction": float(np.mean(exit_valid)),
                "occupied_fraction_after_germination": float(np.mean(occupied)),
                "wave_trace": wave_trace,
                "distance_bands": field_distance,
                "outside_light_cone_occupied_fraction": outside_light_cone,
            }
            writer_history[str(generation)] = {
                "window_kind": candidate["window_kind"],
                "window_value": int(candidate["window_value"]),
                "window_site_count": site_count,
                "routing_steps": routing_steps,
                "moment_mean_abs": float(np.mean(np.abs(moments))),
                "latent_mean_abs": float(np.mean(np.abs(proposal))),
                "writer_network_connected_fraction": float(
                    np.mean(writer_connected)
                ),
            }
            displacement = toroidal_chebyshev_distance(
                origins.reshape(-1, 2),
                next_origins.reshape(-1, 2),
                extent,
            )
            origin_history[str(generation)] = {
                "policy": origin_policy,
                "mean_displacement": float(np.mean(displacement)),
                "max_displacement": int(np.max(displacement)),
                "translation_applied_to_read_write_and_acquisition": translated,
            }
            if template is not None:
                match = _acquisition_match(state, origins, template)
                acquisition_history[str(generation)] = {
                    "match_mean": float(np.mean(match)),
                    "direction_a_mean": float(np.mean(match[:replicates])),
                    "direction_b_mean": float(np.mean(match[replicates:])),
                }
        if retain_exits:
            exits.append((shares.copy(), active.copy()))

    value_bits = int(candidate["bits"])
    inherited_value_bits = value_bits * int(candidate["rank"]) * seed_count
    if str(candidate["share_scheme"]) == "partitioned":
        inherited_value_bits = value_bits * int(candidate["rank"])
    encoded_bits = inherited_value_bits * (
        2 if candidate.get("ecc") == "hamming84" else 1
    )
    occupancy_bits = int(candidate["rank"]) * seed_count
    rank = int(candidate["rank"])
    routing_steps_total = hops + 2 * int(candidate["window_value"])
    result = {
        "candidate_id": str(candidate["candidate_id"]),
        "condition": condition,
        "rule": int(contract.rule),
        "extent": extent,
        "reset_sha256": hashlib.sha256(reset_a.tobytes()).hexdigest(),
        "reset_asserted_before_every_generation": True,
        "acquisition_applied": template is not None,
        "logical_payload_bits": int(candidate["payload_bits"]),
        "inherited_share_value_bits": inherited_value_bits,
        "inherited_occupancy_bits": occupancy_bits,
        "physical_encoded_bits": encoded_bits + occupancy_bits,
        "temporary_share_field_values": extent * extent * seed_count * rank,
        "temporary_reconstruction_values": extent * extent * rank,
        "routing_site_channel_updates_upper_bound": (
            extent * extent * seed_count * rank * routing_steps_total
        ),
        "seed_density": seed_count / float(extent * extent),
        "shared_writer_parameter_bits": int(
            (
                np.asarray(candidate["weight"]).size
                + np.asarray(candidate["bias"]).size
            )
            * 32
        ),
        "seed_count": seed_count,
        "share_scheme": candidate["share_scheme"],
        "germination_hops": hops,
        "rho": rho,
        "ecc": candidate.get("ecc", "none"),
        "founder_payload": _payload_summary(founder, replicates),
        "uncorrectable_codeword_fraction_mean": float(
            np.mean(uncorrectable_values)
        ),
        "germination_coverage_mean": float(np.mean(coverage_values)),
        "outcomes": outcomes,
        "decoders": decoders,
        "carrier_history": carrier_history,
        "writer_history": writer_history,
        "origin_history": origin_history,
        "acquisition_history": acquisition_history,
    }
    return result, exits


def _synergy_task(
    payload: tuple[
        dict[str, Any],
        list[dict[str, Any]],
        MotifContract,
        SynergyContract,
        dict[int, dict[str, np.ndarray]],
    ]
) -> dict[str, Any]:
    item, candidates, writer_contract, contract, reference = payload
    candidate = next(
        row
        for row in candidates
        if row["candidate_id"] == item["candidate_id"]
    )
    configuration = ReaderConfiguration(**item["configuration"])
    replicates = int(item["replicates"])
    generations = int(item["generations"])
    extent = int(item.get("extent", 16))
    conditions = tuple(item.get("conditions", ("intact",)))
    template_payload = item.get("acquisition_template")
    template = (
        np.asarray(template_payload, dtype=np.bool_)
        if template_payload is not None
        else None
    )
    results: dict[str, Any] = {}
    if template is not None:
        sham, _ = simulate_synergistic_lineage(
            item["pair"],
            configuration,
            candidate,
            "intact",
            replicates,
            generations,
            reference,
            writer_contract,
            contract,
            extent=extent,
            acquisition_template=template,
            apply_acquisition=False,
        )
        results["sham_intact"] = sham
    intact, exits = simulate_synergistic_lineage(
        item["pair"],
        configuration,
        candidate,
        "intact",
        replicates,
        generations,
        reference,
        writer_contract,
        contract,
        extent=extent,
        retain_exits=True,
        acquisition_template=template,
    )
    if "intact" in conditions:
        results["intact"] = intact
    for condition in conditions:
        if condition == "intact":
            continue
        row, _ = simulate_synergistic_lineage(
            item["pair"],
            configuration,
            candidate,
            condition,
            replicates,
            generations,
            reference,
            writer_contract,
            contract,
            extent=extent,
            source_exits=exits,
            acquisition_template=template,
        )
        results[condition] = row
    return {
        "checkpoint": item["checkpoint"],
        "pair_id": item["pair"]["pair_id"],
        "candidate_id": candidate["candidate_id"],
        "template_id": item.get("template_id"),
        "replicates": replicates,
        "generations": generations,
        "extent": extent,
        "conditions": results,
    }


def _boot(
    values: Sequence[float],
    profile: SynergyProfile,
    contract: SynergyContract,
    *key: object,
) -> dict[str, Any]:
    return _bootstrap(
        values,
        profile.bootstrap_resamples,
        _hash_seed(contract.namespace, *key),
        contract.strict_alpha,
    )


def _diagnostic_values(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
    section: str,
    key: str,
) -> list[float]:
    values: list[float] = []
    for row in rows:
        if row.get("candidate_id") != candidate_id:
            continue
        try:
            values.append(
                float(
                    row["conditions"][condition][section][str(generation)][key]
                )
            )
        except KeyError:
            continue
    return values


def _retention(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
) -> float:
    intact = _condition_values(rows, candidate_id, "intact", generation)
    control = _condition_values(rows, candidate_id, condition, generation)
    intact_mean = float(np.mean(intact)) if intact else 0.0
    control_mean = float(np.mean(control)) if control else 0.0
    return control_mean / intact_mean if intact_mean > 0.0 else 1.0


def _candidate_summary(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
    profile: SynergyProfile,
    contract: SynergyContract,
    phase: str,
    *,
    anchor_mean: float | None = None,
) -> dict[str, Any]:
    candidate_id = str(candidate["candidate_id"])
    intact = _condition_values(rows, candidate_id, "intact", generation)
    direction_a = _condition_values(
        rows, candidate_id, "intact", generation, "direction_a"
    )
    direction_b = _condition_values(
        rows, candidate_id, "intact", generation, "direction_b"
    )
    survival = _condition_values(
        rows, candidate_id, "intact", generation, "survival"
    )
    active = (
        _paired_advantage(
            rows, candidate_id, "intact", "no_rewrite", generation
        )
        if _condition_values(rows, candidate_id, "no_rewrite", generation)
        else []
    )
    translated = _condition_values(
        rows, candidate_id, "translated_patch", generation
    )
    corrupted = _condition_values(
        rows, candidate_id, "carrier_corruption_1", generation
    )
    joint = _diagnostic_values(
        rows,
        candidate_id,
        "intact",
        generation,
        "decoders",
        "joint_balanced_accuracy",
    )
    subset_rows: list[list[float]] = []
    for row in rows:
        if row.get("candidate_id") != candidate_id:
            continue
        try:
            subset_rows.append(
                [
                    float(value)
                    for value in row["conditions"]["intact"]["decoders"][
                        str(generation)
                    ]["proper_subset_balanced_accuracies"]
                ]
            )
        except KeyError:
            continue
    subset: list[float] = []
    subset_index: int | None = None
    if subset_rows:
        width = len(subset_rows[0])
        if any(len(row) != width for row in subset_rows):
            raise ValueError("proper-subset diagnostic width changed")
        matrix = np.asarray(subset_rows, dtype=np.float64)
        subset_index = int(np.argmax(np.mean(matrix, axis=0)))
        subset = matrix[:, subset_index].tolist()
    mean = float(np.mean(intact)) if intact else 0.0
    translated_mean = float(np.mean(translated)) if translated else 0.0
    result: dict[str, Any] = {
        "candidate": _candidate_public(candidate),
        "crossover": _boot(
            intact, profile, contract, phase, candidate_id, generation, "intact"
        ),
        "direction_a_mean": float(np.mean(direction_a)) if direction_a else 0.0,
        "direction_b_mean": float(np.mean(direction_b)) if direction_b else 0.0,
        "fraction_pairs_positive": (
            float(np.mean(np.asarray(intact) > 0.0)) if intact else 0.0
        ),
        "survival_mean": float(np.mean(survival)) if survival else 0.0,
        "active_rewrite_advantage": _boot(
            active, profile, contract, phase, candidate_id, generation, "active"
        ),
        "translated": _boot(
            translated,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "translated",
        ),
        "translation_retention": (
            translated_mean / mean if mean > 0.0 else 0.0
        ),
        "carrier_corruption": _boot(
            corrupted,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "corruption",
        ),
        "joint_decoder": _boot(
            joint, profile, contract, phase, candidate_id, generation, "joint"
        ),
        "proper_subset_decoder": _boot(
            subset, profile, contract, phase, candidate_id, generation, "subset"
        ),
        "joint_decoder_mean": float(np.mean(joint)) if joint else None,
        "proper_subset_decoder_max_mean": (
            float(np.mean(subset)) if subset else None
        ),
        "worst_proper_subset_index": subset_index,
    }
    result["anchor_retention"] = (
        mean / anchor_mean
        if anchor_mean is not None and anchor_mean > 0.0
        else 1.0
    )
    for condition in (
        "no_rewrite",
        "communication_cut_vertical",
        "communication_cut_horizontal",
        "proper_subset",
        "zero_every_boundary",
        "shuffle_every_boundary",
        "read_disabled",
        "founder_write_disabled",
        "write_disabled",
        "transport_disabled",
        "regeneration_disabled",
    ):
        if _condition_values(rows, candidate_id, condition, generation):
            result.setdefault("control_retention", {})[condition] = _retention(
                rows, candidate_id, condition, generation
            )
    return result


def _base_recovery_gate(
    summary: dict[str, Any],
    contract: SynergyContract,
    minimum: float,
) -> bool:
    lower = summary["crossover"]["ci"][0]
    active_lower = summary["active_rewrite_advantage"]["ci"][0]
    return bool(
        float(summary["crossover"]["mean"] or 0.0) >= minimum
        and lower is not None
        and float(lower) > 0.0
        and float(summary["active_rewrite_advantage"]["mean"] or 0.0)
        >= contract.active_advantage_minimum
        and active_lower is not None
        and float(active_lower) > 0.0
        and summary["direction_a_mean"] > 0.0
        and summary["direction_b_mean"] > 0.0
        and summary["fraction_pairs_positive"] >= 0.50
        and summary["survival_mean"] >= contract.survival_gate
        and summary["translation_retention"] >= contract.translation_retention
        and summary["anchor_retention"] >= contract.anchor_retention
    )


def _synergy_gate(
    summary: dict[str, Any], contract: SynergyContract
) -> bool:
    joint_lower = summary["joint_decoder"]["ci"][0]
    subset_upper = summary["proper_subset_decoder"]["ci"][1]
    controls = summary.get("control_retention", {})
    return bool(
        _base_recovery_gate(summary, contract, contract.screen_generation8)
        and joint_lower is not None
        and float(joint_lower) >= contract.joint_accuracy_minimum
        and subset_upper is not None
        and float(subset_upper) <= contract.subset_accuracy_maximum
        and controls.get("no_rewrite", 1.0) <= 1.0 - contract.loss_fraction
        and controls.get("communication_cut_vertical", 1.0)
        <= 1.0 - contract.loss_fraction
        and controls.get("communication_cut_horizontal", 1.0)
        <= 1.0 - contract.loss_fraction
    )


def _acquisition_values(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
) -> list[float]:
    values: list[float] = []
    for row in rows:
        if row.get("candidate_id") != candidate_id:
            continue
        try:
            acquired = float(
                row["conditions"][condition]["acquisition_history"][
                    str(generation)
                ]["match_mean"]
            )
            sham = float(
                row["conditions"]["sham_intact"]["acquisition_history"][
                    str(generation)
                ]["match_mean"]
            )
        except KeyError:
            # Sham runs have no intervention and therefore no acquisition
            # section.  Score their terminal patch directly if persisted by a
            # future schema; the v1 schema uses zero as the registered neutral
            # projection.
            try:
                acquired = float(
                    row["conditions"][condition]["acquisition_history"][
                        str(generation)
                    ]["match_mean"]
                )
            except KeyError:
                continue
            sham = 0.0
        values.append(acquired - sham)
    return values


def _acquisition_summary(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    generation: int,
    profile: SynergyProfile,
    contract: SynergyContract,
    phase: str,
) -> dict[str, Any]:
    intact = _acquisition_values(rows, candidate_id, "intact", generation)
    no_rewrite = _acquisition_values(
        rows, candidate_id, "no_rewrite", generation
    )
    by_template: dict[str, list[float]] = {}
    for row, value in zip(
        [row for row in rows if row.get("candidate_id") == candidate_id],
        intact,
    ):
        template_id = str(row.get("template_id"))
        by_template.setdefault(template_id, []).append(value)
    template_means = {
        key: float(np.mean(values)) for key, values in by_template.items()
    }
    paired = [
        left - right for left, right in zip(intact, no_rewrite)
    ]
    return {
        "effect": _boot(
            intact, profile, contract, phase, candidate_id, generation, "acquired"
        ),
        "active_rewrite_advantage": _boot(
            paired,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "acquired-active",
        ),
        "template_means": template_means,
        "fraction_templates_positive": (
            float(np.mean(np.asarray(list(template_means.values())) > 0.0))
            if template_means
            else 0.0
        ),
    }


def _write_phase_outputs(
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
    payload = result | {"phase": phase, "design_digest": design_digest}
    decision = {
        "experiment": "ca_motif_lineage_stage_6c",
        "state": result.get("state"),
        "phase": phase,
        "design_digest": design_digest,
        "stage_gate": bool(result.get("stage_gate")),
        "decision": (
            "campaign_complete"
            if phase == PHASES[-1]
            else "continue_registered_exploration"
        ),
        "next_phase": next_phase,
        "automatic_launch": next_phase is not None,
        "final_audit_trajectory_state": result.get(
            "final_audit_trajectory_state", "untouched"
        ),
    }
    _atomic_json(root / "RESULTS.json", payload)
    _atomic_json(root / "STAGE_DECISION.json", decision)
    _atomic_text(root / "REPORT.md", report)
    _atomic_text(root / "LAY_SUMMARY.md", lay)
    if result.get("state") == "complete":
        _atomic_text(root / "COMPLETE", "complete\n")
    _atomic_json(output / "RESULTS.json", payload)
    _atomic_json(output / "STAGE_DECISION.json", decision)
    _atomic_text(output / "REPORT.md", report)
    _atomic_text(output / "LAY_SUMMARY.md", lay)


def _stage_items(
    cohort: Sequence[dict[str, Any]],
    candidates: Sequence[dict[str, Any]],
    configuration: dict[str, Any],
    *,
    prefix: str,
    replicates: int,
    generations: int,
    conditions: Sequence[str],
    templates: Sequence[dict[str, Any]] | None = None,
    extent: int = 16,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for pair_index, pair in enumerate(cohort):
        template = (
            templates[pair_index % len(templates)]
            if templates
            else None
        )
        for candidate_index, candidate in enumerate(candidates):
            item = {
                "checkpoint": f"{prefix}-p{pair_index:04d}-c{candidate_index:03d}",
                "pair": pair,
                "candidate_id": candidate["candidate_id"],
                "configuration": configuration,
                "replicates": replicates,
                "generations": generations,
                "conditions": tuple(conditions),
                "extent": extent,
            }
            if template is not None:
                item["template_id"] = template["template_id"]
                item["acquisition_template"] = template["bits"]
            items.append(item)
    return items


def _run_forensics(
    output: Path,
    stage6br_root: Path,
    design_digest: str,
    status,
) -> dict[str, Any]:
    status("running", "stage6br-forensic-lock", completed=0, total=1)
    status6br = _load_json(stage6br_root / "STATUS.json")
    result6br = _load_json(stage6br_root / "RESULTS.json")
    cohorts6br = _load_json(stage6br_root / "COHORTS.json")
    qualification = result6br.get("qualification", {})
    source_id = next(
        (
            key
            for key in qualification
            if key.startswith("coverage-")
            and "s04-replicated" in key
        ),
        None,
    )
    if source_id is None:
        raise ValueError("Stage-6B-R replicated qualification object is missing")
    source_summary = qualification[source_id]
    cut_retention = float(
        source_summary["targeted_control_retention"]["communication_cut"]
    )
    seed_positions = ((0, 0), (0, 8), (8, 0), (8, 8))
    vertical_components = {
        "left": [position for position in seed_positions if position[1] < 8],
        "right": [position for position in seed_positions if position[1] >= 8],
    }
    topology = {
        name: {
            "seed_positions": values,
            "complete_replicated_payloads": len(values),
        }
        for name, values in vertical_components.items()
    }
    stage_gate = bool(
        status6br.get("state") == "complete"
        and status6br.get("verdict") == "TRANSIENT_LOCAL_PH_ONLY"
        and result6br.get("final_audit_trajectory_state") == "untouched"
        and cohorts6br.get("final_audit_trajectory_state") == "untouched"
        and all(
            row["complete_replicated_payloads"] >= 1
            for row in topology.values()
        )
        and cut_retention > 0.90
    )
    result = {
        "state": "complete",
        "stage_gate": stage_gate,
        "stage6br_verdict": status6br.get("verdict"),
        "stage6br_communication_cut_retention": cut_retention,
        "cut_topology": topology,
        "interpretation": (
            "the Stage-6B-R cut left complete payload copies on both sides"
        ),
        "frozen_stage6br_sha256": {
            name: _sha256(stage6br_root / name)
            for name in (
                "DESIGN.json",
                "RESULTS.json",
                "STATUS.json",
                "COHORTS.json",
                "RENEWAL_MODELS.json",
                "RENEWAL_MODELS.npz",
            )
        },
        "final_audit_trajectory_state": "untouched",
    }
    status("running", "stage6br-forensic-lock", completed=1, total=1)
    _write_phase_outputs(
        output,
        "forensics",
        design_digest,
        result,
        "# Stage 6C forensic lock\n\n"
        f"Stage-6B-R communication-cut retention was {cut_retention:.4f}. "
        "Each separated component retained a complete replicated payload.\n",
        "# Lay summary\n\n"
        "The earlier cut did not truly split the memory: both sides still had "
        "a complete copy. Stage 6C can therefore test a stricter shared memory.\n",
        next_phase="synergy",
    )
    return result


def _run_synergy(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: SynergyProfile,
    contract: SynergyContract,
    writer_contract: MotifContract,
    design_digest: str,
    candidates: Sequence[dict[str, Any]],
    controls: Sequence[dict[str, Any]],
    anchor: dict[str, Any],
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status,
    scientific: bool,
) -> dict[str, Any]:
    screened = list(candidates[: profile.screen_candidate_limit])
    models = [anchor, *controls, *screened]
    configuration = _configuration_payload(frozen["stage4"]["configuration"])
    items = _stage_items(
        cohorts["synergy"],
        models,
        configuration,
        prefix="synergy-screen",
        replicates=profile.screen_replicates,
        generations=8,
        conditions=SCREEN_CONDITIONS,
    )
    status("running", "synergy-screen", completed=0, total=len(items))
    rows, complete = _run_json_checkpoints(
        output,
        "synergy-screen",
        items,
        models,
        _synergy_task,
        writer_contract,
        contract,  # type: ignore[arg-type]
        frozen["stage4"]["reference"],
        design_digest,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    if not complete:
        return {"state": "partial_budget_exhausted", "stage_gate": False}
    anchor_summary = _candidate_summary(
        rows, anchor, 8, profile, contract, "synergy"
    )
    anchor_mean = float(anchor_summary["crossover"]["mean"] or 0.0)
    summaries = {
        str(model["candidate_id"]): _candidate_summary(
            rows,
            model,
            8,
            profile,
            contract,
            "synergy",
            anchor_mean=anchor_mean,
        )
        for model in models
    }
    eligible: list[dict[str, Any]] = []
    for candidate in screened:
        summary = summaries[str(candidate["candidate_id"])]
        passed = _synergy_gate(summary, contract) if scientific else True
        summary["synergy_gate"] = passed
        if passed:
            eligible.append(candidate)
    ranked = sorted(
        eligible,
        key=lambda row: (
            -float(
                summaries[str(row["candidate_id"])]["crossover"]["mean"]
                or -1.0
            ),
            -float(
                summaries[str(row["candidate_id"])][
                    "active_rewrite_advantage"
                ]["mean"]
                or -1.0
            ),
            str(row["candidate_id"]),
        ),
    )
    selected = ranked[:2]
    control_gates = {
        str(control["candidate_id"]): _synergy_gate(
            summaries[str(control["candidate_id"])], contract
        )
        for control in controls
    }
    result = {
        "state": "complete",
        "scientific_gate_applied": scientific,
        "stage_gate": bool(eligible),
        "eligible_candidate_ids": [
            str(row["candidate_id"]) for row in eligible
        ],
        "selected_candidate_ids": [
            str(row["candidate_id"]) for row in selected
        ],
        "control_synergy_gates": control_gates,
        "candidate_summaries": summaries,
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_outputs(
        output,
        "synergy",
        design_digest,
        result,
        "# Stage 6C synergistic-carrier screen\n\n"
        f"Strict synergy-positive candidates: {result['eligible_candidate_ids'] or 'none'}.\n",
        "# Lay summary\n\n"
        "This stage asks whether the form can be recovered only when separated "
        "pieces of memory physically meet. No isolated piece is allowed to know "
        "the answer.\n",
        next_phase="plasticity",
    )
    return result


def _causal_qualification(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    generation: int,
    contract: SynergyContract,
) -> tuple[bool, dict[str, Any]]:
    loss_conditions = (
        "zero_every_boundary",
        "shuffle_every_boundary",
        "read_disabled",
        "founder_write_disabled",
        "write_disabled",
        "transport_disabled",
        "regeneration_disabled",
        "communication_cut_vertical",
        "communication_cut_horizontal",
        "proper_subset",
    )
    retention = {
        condition: _retention(rows, candidate_id, condition, generation)
        for condition in loss_conditions
    }
    loss_pass = all(
        value <= 1.0 - contract.loss_fraction
        for value in retention.values()
    )
    intact = _condition_values(rows, candidate_id, "intact", generation)
    same = _condition_values(
        rows, candidate_id, "rescue_same_enter_g4", generation
    )
    opposite = _condition_values(
        rows, candidate_id, "rescue_opposite_enter_g4", generation
    )
    intact_mean = float(np.mean(intact)) if intact else 0.0
    same_mean = float(np.mean(same)) if same else 0.0
    opposite_mean = float(np.mean(opposite)) if opposite else 0.0
    rescue_pass = bool(
        intact_mean > 0.0
        and same_mean / intact_mean >= contract.rescue_fraction
        and opposite_mean < 0.0
    )
    return loss_pass and rescue_pass, {
        "targeted_control_retention": retention,
        "targeted_loss_pass": loss_pass,
        "same_rescue_retention": (
            same_mean / intact_mean if intact_mean > 0.0 else 0.0
        ),
        "opposite_rescue_mean": opposite_mean,
        "rescue_and_reversal_pass": rescue_pass,
    }


def _run_plasticity(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: SynergyProfile,
    contract: SynergyContract,
    writer_contract: MotifContract,
    design_digest: str,
    candidates: Sequence[dict[str, Any]],
    anchor: dict[str, Any],
    templates: Sequence[dict[str, Any]],
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status,
    scientific: bool,
) -> dict[str, Any]:
    prior = _load_json(output / "synergy/RESULTS.json")
    by_id = {str(row["candidate_id"]): row for row in candidates}
    selected = [
        by_id[value] for value in prior.get("selected_candidate_ids", ())
    ]
    if not selected:
        result = {
            "state": "complete",
            "stage_gate": False,
            "qualification_candidate_ids": [],
            "qualified_candidate_ids": [],
            "candidate_summaries": {},
            "final_audit_trajectory_state": "untouched",
        }
        _write_phase_outputs(
            output,
            "plasticity",
            design_digest,
            result,
            "# Stage 6C causal plasticity qualification\n\nNo candidate entered qualification.\n",
            "# Lay summary\n\nNo shared carrier passed the first causal screen.\n",
            next_phase="endurance",
        )
        return result
    models = [anchor, *selected]
    qualification_templates = [
        row for row in templates if row["split"] == "qualification"
    ]
    configuration = _configuration_payload(frozen["stage4"]["configuration"])
    items = _stage_items(
        cohorts["plasticity"],
        models,
        configuration,
        prefix="plasticity-qualification",
        replicates=profile.qualification_replicates,
        generations=16,
        conditions=FULL_CONDITIONS,
        templates=qualification_templates,
    )
    status(
        "running",
        "plasticity-qualification",
        completed=0,
        total=len(items),
    )
    rows, complete = _run_json_checkpoints(
        output,
        "plasticity-qualification",
        items,
        models,
        _synergy_task,
        writer_contract,
        contract,  # type: ignore[arg-type]
        frozen["stage4"]["reference"],
        design_digest,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    if not complete:
        return {"state": "partial_budget_exhausted", "stage_gate": False}
    anchor_summary = _candidate_summary(
        rows, anchor, 16, profile, contract, "plasticity"
    )
    anchor_mean = float(anchor_summary["crossover"]["mean"] or 0.0)
    summaries: dict[str, Any] = {ANCHOR_CONTROL_ID: anchor_summary}
    qualified: list[dict[str, Any]] = []
    for candidate in selected:
        candidate_id = str(candidate["candidate_id"])
        summary = _candidate_summary(
            rows,
            candidate,
            16,
            profile,
            contract,
            "plasticity",
            anchor_mean=anchor_mean,
        )
        acquisition = _acquisition_summary(
            rows,
            candidate_id,
            8,
            profile,
            contract,
            "plasticity",
        )
        causal_pass, causal = _causal_qualification(
            rows, candidate_id, 16, contract
        )
        acquired_lower = acquisition["effect"]["ci"][0]
        acquired_active_lower = acquisition["active_rewrite_advantage"]["ci"][0]
        acquisition_pass = bool(
            float(acquisition["effect"]["mean"] or 0.0)
            >= contract.acquisition_minimum
            and acquired_lower is not None
            and float(acquired_lower) > 0.0
            and acquisition["fraction_templates_positive"] >= 0.75
            and acquired_active_lower is not None
            and float(acquired_active_lower) > 0.0
        )
        passed = (
            _base_recovery_gate(
                summary, contract, contract.qualification_generation16
            )
            and causal_pass
            and acquisition_pass
        ) if scientific else True
        summary.update(
            causal
            | {
                "acquisition": acquisition,
                "acquisition_gate": acquisition_pass,
                "qualification_gate": passed,
            }
        )
        summaries[candidate_id] = summary
        if passed:
            qualified.append(candidate)
    qualified = sorted(
        qualified,
        key=lambda row: -float(
            summaries[str(row["candidate_id"])]["acquisition"]["effect"][
                "mean"
            ]
            or -1.0
        ),
    )[:2]
    result = {
        "state": "complete",
        "scientific_gate_applied": scientific,
        "stage_gate": bool(qualified),
        "qualification_candidate_ids": [
            str(row["candidate_id"]) for row in selected
        ],
        "qualified_candidate_ids": [
            str(row["candidate_id"]) for row in qualified
        ],
        "candidate_summaries": summaries,
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_outputs(
        output,
        "plasticity",
        design_digest,
        result,
        "# Stage 6C causal plasticity qualification\n\n"
        f"Strict acquired-form candidates: {result['qualified_candidate_ids'] or 'none'}.\n",
        "# Lay summary\n\n"
        "The visible parent was given a new local experience. This stage asks "
        "whether the shared carrier—not a direct edit—lets reset daughters "
        "recover a trace of that experience.\n",
        next_phase="endurance",
    )
    return result


def build_synergy_scale_variants(
    sources: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for source in sources:
        source_id = str(source["candidate_id"])
        base_hops = int(source["germination_hops"])
        for extent in (16, 32, 64):
            for mode in ("fixed", "diameter"):
                hops = (
                    base_hops
                    if mode == "fixed"
                    else int(math.ceil(base_hops * extent / 16.0))
                )
                variants.append(
                    {
                        **source,
                        "candidate_id": (
                            f"scale-{source_id}-n{extent:02d}-{mode}"
                        ),
                        "source_candidate_id": source_id,
                        "extent": extent,
                        "scale_mode": mode,
                        "germination_hops": hops,
                    }
                )
    return variants


def _scale_items(
    cohort: Sequence[dict[str, Any]],
    variants: Sequence[dict[str, Any]],
    configuration: dict[str, Any],
    profile: SynergyProfile,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for pair_index, pair in enumerate(cohort):
        for candidate_index, candidate in enumerate(variants):
            items.append(
                {
                    "checkpoint": (
                        f"scale-p{pair_index:04d}-c{candidate_index:03d}"
                    ),
                    "pair": pair,
                    "candidate_id": candidate["candidate_id"],
                    "configuration": configuration,
                    "replicates": profile.scale_replicates,
                    "generations": 8,
                    "conditions": (
                        "intact",
                        "no_rewrite",
                        "communication_cut_vertical",
                        "translated_patch",
                    ),
                    "extent": int(candidate["extent"]),
                }
            )
    return items


def _scale_summary(
    rows: Sequence[dict[str, Any]],
    variants: Sequence[dict[str, Any]],
    profile: SynergyProfile,
    contract: SynergyContract,
) -> dict[str, Any]:
    candidates: dict[str, Any] = {}
    by_source: dict[str, dict[str, dict[str, Any]]] = {}
    for candidate in variants:
        candidate_id = str(candidate["candidate_id"])
        summary = _candidate_summary(
            rows, candidate, 8, profile, contract, "scale"
        )
        outside = _diagnostic_values(
            rows,
            candidate_id,
            "intact",
            8,
            "carrier_history",
            "outside_light_cone_occupied_fraction",
        )
        summary["outside_light_cone_occupied_fraction_max"] = (
            float(max(outside)) if outside else 1.0
        )
        summary["exact_light_cone_support"] = bool(
            outside and max(outside) == 0.0
        )
        candidates[candidate_id] = summary
        source_id = str(candidate["source_candidate_id"])
        mode = str(candidate["scale_mode"])
        extent = str(candidate["extent"])
        by_source.setdefault(source_id, {}).setdefault(mode, {})[extent] = summary
    class_pass: dict[str, bool] = {}
    geometry: dict[str, Any] = {}
    for source_id, modes in by_source.items():
        fixed = modes.get("fixed", {})
        diameter = modes.get("diameter", {})
        d16 = float(
            diameter.get("16", {}).get("crossover", {}).get("mean") or 0.0
        )
        d64 = float(
            diameter.get("64", {}).get("crossover", {}).get("mean") or 0.0
        )
        f64 = float(
            fixed.get("64", {}).get("crossover", {}).get("mean") or 0.0
        )
        diameter_retention = d64 / d16 if d16 > 0.0 else 0.0
        fixed_to_diameter = f64 / d64 if d64 > 0.0 else 1.0
        exact = all(
            bool(summary.get("exact_light_cone_support"))
            for mode_rows in modes.values()
            for summary in mode_rows.values()
        )
        passed = bool(
            diameter_retention >= 0.70
            and fixed_to_diameter <= 0.30
            and exact
        )
        class_pass[source_id] = passed
        geometry[source_id] = {
            "diameter_retention_n64_vs_n16": diameter_retention,
            "fixed_to_diameter_n64": fixed_to_diameter,
            "exact_light_cone_support": exact,
            "geometry_gate": passed,
        }
    return {
        "candidate_summaries": candidates,
        "geometry": geometry,
        "class_pass": class_pass,
        "nearest_neighbour_only": True,
    }


def _run_endurance(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: SynergyProfile,
    contract: SynergyContract,
    writer_contract: MotifContract,
    design_digest: str,
    candidates: Sequence[dict[str, Any]],
    controls: Sequence[dict[str, Any]],
    templates: Sequence[dict[str, Any]],
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status,
    scientific: bool,
) -> dict[str, Any]:
    plasticity = _load_json(output / "plasticity/RESULTS.json")
    by_id = {str(row["candidate_id"]): row for row in candidates}
    qualified = [
        by_id[value]
        for value in plasticity.get("qualified_candidate_ids", ())
    ]
    if not qualified:
        result = {
            "state": "complete",
            "stage_gate": False,
            "scale": {},
            "passing_geometry_candidate_ids": [],
            "enduring_candidate_ids": [],
            "endurance_summaries": {},
            "final_audit_trajectory_state": "untouched",
        }
        _write_phase_outputs(
            output,
            "endurance",
            design_digest,
            result,
            "# Stage 6C geometry and endurance\n\nNo candidate entered this phase.\n",
            "# Lay summary\n\nNo candidate reached the long-distance test.\n",
            next_phase="adjudicate",
        )
        return result
    scale_sources = [*qualified, controls[0]]
    variants = build_synergy_scale_variants(scale_sources)
    configuration = _configuration_payload(frozen["stage4"]["configuration"])
    scale_items = _scale_items(
        cohorts["scale"], variants, configuration, profile
    )
    status("running", "scale-checkpoints", completed=0, total=len(scale_items))
    scale_rows, complete = _run_json_checkpoints(
        output,
        "scale-checkpoints-stage6c",
        scale_items,
        variants,
        _synergy_task,
        writer_contract,
        contract,  # type: ignore[arg-type]
        frozen["stage4"]["reference"],
        design_digest,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    if not complete:
        return {"state": "partial_budget_exhausted", "stage_gate": False}
    scale = _scale_summary(scale_rows, variants, profile, contract)
    passing_geometry = [
        row
        for row in qualified
        if scale["class_pass"].get(str(row["candidate_id"]), False)
        or not scientific
    ]
    if not passing_geometry:
        result = {
            "state": "complete",
            "scientific_gate_applied": scientific,
            "stage_gate": False,
            "scale": scale,
            "passing_geometry_candidate_ids": [],
            "enduring_candidate_ids": [],
            "endurance_summaries": {},
            "final_audit_trajectory_state": "untouched",
        }
        _write_phase_outputs(
            output,
            "endurance",
            design_digest,
            result,
            "# Stage 6C geometry and endurance\n\nNo candidate passed causal geometry.\n",
            "# Lay summary\n\nThe separated pieces could not preserve the "
            "registered local scaling signature.\n",
            next_phase="adjudicate",
        )
        return result
    qualification_templates = [
        row for row in templates if row["split"] == "qualification"
    ]
    endurance_items = _stage_items(
        cohorts["endurance"],
        passing_geometry,
        configuration,
        prefix="endurance",
        replicates=profile.endurance_replicates,
        generations=64,
        conditions=(
            "intact",
            "no_rewrite",
            "carrier_corruption_1",
            "translated_patch",
            "germination_cut_vertical",
            "write_cut_vertical",
        ),
        templates=qualification_templates,
    )
    status(
        "running",
        "endurance-checkpoints",
        completed=0,
        total=len(endurance_items),
    )
    endurance_rows, complete = _run_json_checkpoints(
        output,
        "endurance-checkpoints-stage6c",
        endurance_items,
        passing_geometry,
        _synergy_task,
        writer_contract,
        contract,  # type: ignore[arg-type]
        frozen["stage4"]["reference"],
        design_digest,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    if not complete:
        return {"state": "partial_budget_exhausted", "stage_gate": False}
    summaries: dict[str, Any] = {}
    enduring: list[dict[str, Any]] = []
    for candidate in passing_geometry:
        candidate_id = str(candidate["candidate_id"])
        summary = _candidate_summary(
            endurance_rows,
            candidate,
            64,
            profile,
            contract,
            "endurance",
        )
        acquisition = _acquisition_summary(
            endurance_rows,
            candidate_id,
            64,
            profile,
            contract,
            "endurance",
        )
        germination_current = _retention(
            endurance_rows, candidate_id, "germination_cut_vertical", 1
        )
        write_current = _retention(
            endurance_rows, candidate_id, "write_cut_vertical", 1
        )
        write_next = _retention(
            endurance_rows, candidate_id, "write_cut_vertical", 2
        )
        timing_pass = bool(
            germination_current <= 1.0 - contract.loss_fraction
            and write_current >= contract.rescue_fraction
            and write_next <= 1.0 - contract.loss_fraction
        )
        lower = summary["crossover"]["ci"][0]
        active_lower = summary["active_rewrite_advantage"]["ci"][0]
        acquired_lower = acquisition["effect"]["ci"][0]
        passed = bool(
            lower is not None
            and float(lower) > 0.0
            and float(summary["active_rewrite_advantage"]["mean"] or 0.0)
            >= contract.active_advantage_minimum
            and active_lower is not None
            and float(active_lower) > 0.0
            and acquired_lower is not None
            and float(acquired_lower) > 0.0
            and summary["translation_retention"] >= contract.translation_retention
            and timing_pass
        ) if scientific else True
        summary.update(
            {
                "acquisition": acquisition,
                "timed_cut_retention": {
                    "germination_cut_generation1": germination_current,
                    "write_cut_generation1": write_current,
                    "write_cut_generation2": write_next,
                },
                "timing_gate": timing_pass,
                "endurance_gate": passed,
            }
        )
        summaries[candidate_id] = summary
        if passed:
            enduring.append(candidate)
    enduring = enduring[:2]
    result = {
        "state": "complete",
        "scientific_gate_applied": scientific,
        "stage_gate": bool(enduring),
        "scale": scale,
        "passing_geometry_candidate_ids": [
            str(row["candidate_id"]) for row in passing_geometry
        ],
        "enduring_candidate_ids": [
            str(row["candidate_id"]) for row in enduring
        ],
        "endurance_summaries": summaries,
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_outputs(
        output,
        "endurance",
        design_digest,
        result,
        "# Stage 6C geometry and endurance\n\n"
        f"Enduring synergistic candidates: {result['enduring_candidate_ids'] or 'none'}.\n",
        "# Lay summary\n\n"
        "The surviving memories were separated over larger worlds and followed "
        "for 64 generations. Fixed-time and distance-scaled communication remain "
        "separate claims.\n",
        next_phase="adjudicate",
    )
    return result


def select_synergy_cohorts(
    frozen: dict[str, Any],
    profile: SynergyProfile,
    profile_name: str,
    *,
    open_final: bool,
) -> dict[str, list[dict[str, Any]]]:
    base = select_minimality_cohorts(
        MINIMALITY_PROFILES[profile_name],
        frozen,
        profile_name=profile_name,
        open_audit=open_final,
    )
    result = {
        "synergy": base["compression_qualification"][: profile.screen_pairs],
        "plasticity": base["locality_qualification"][
            : profile.qualification_pairs
        ],
        "scale": base["ecology"][: profile.scale_pairs],
        "endurance": base["locality_endurance"][: profile.endurance_pairs],
        "final": (
            base["audit"][: profile.final_pairs] if open_final else []
        ),
    }
    for name, expected in (
        ("synergy", profile.screen_pairs),
        ("plasticity", profile.qualification_pairs),
        ("scale", profile.scale_pairs),
        ("endurance", profile.endurance_pairs),
    ):
        if len(result[name]) != expected:
            raise ValueError(f"Stage-6C {name} cohort is incomplete")
    if open_final and len(result["final"]) != profile.final_pairs:
        raise ValueError("opened Stage-6C final cohort is incomplete")
    used = [
        str(pair["pair_id"])
        for name, rows in result.items()
        if name != "final"
        for pair in rows
    ]
    if len(used) != len(set(used)):
        raise AssertionError("Stage-6C developmental cohorts overlap")
    if profile_name == "reference" and set(used) & set(frozen["later_ids"]):
        raise AssertionError("Stage-6C development touched the protected reserve")
    return result


def _negative_verdict(output: Path) -> str:
    synergy = _load_json(output / "synergy/RESULTS.json")
    summaries = synergy.get("candidate_summaries", {})
    partitioned_effects = [
        float(summaries.get(candidate_id, {}).get("crossover", {}).get("mean") or 0.0)
        for candidate_id in PARTITIONED_CONTROL_IDS
    ]
    replicated_effect = float(
        summaries.get(REPLICATED_CONTROL_ID, {})
        .get("crossover", {})
        .get("mean")
        or 0.0
    )
    if max(partitioned_effects, default=0.0) >= SynergyContract().screen_generation8:
        return "DURABLE_PARTITIONED_BUT_LEAKY_MEMORY"
    if replicated_effect >= SynergyContract().screen_generation8:
        return "REDUNDANT_CARRIER_ONLY"
    forensics = _load_json(output / "forensics/RESULTS.json")
    if forensics.get("stage_gate"):
        return "TRANSIENT_LOCAL_PH_ONLY"
    return "NO_INTEGRATED_CA_PH"


def _final_design(
    enduring: Sequence[dict[str, Any]],
    controls: Sequence[dict[str, Any]],
    anchor: dict[str, Any],
    templates: Sequence[dict[str, Any]],
    profile: SynergyProfile,
    design_digest: str,
    frozen: dict[str, Any],
    stage6br_root: Path,
) -> dict[str, Any]:
    audit_templates = [row for row in templates if row["split"] == "audit"]
    models = [*enduring, controls[0], anchor]
    payload = {
        "experiment": "ca_motif_lineage_stage_6c_final_audit",
        "parent_design_digest": design_digest,
        "candidate_ids": [str(row["candidate_id"]) for row in enduring],
        "candidate_order": [str(row["candidate_id"]) for row in models],
        "candidate_public": [_candidate_public(row) for row in models],
        "conditions": FINAL_CONDITIONS,
        "generations": 32,
        "replicates_per_history": profile.final_replicates,
        "finalist_pair_count": profile.final_pairs,
        "control_pair_count": min(8, profile.final_pairs),
        "pair_ids_sha256": hashlib.sha256(
            "\n".join(frozen["later_ids"][: profile.final_pairs]).encode()
        ).hexdigest(),
        "audit_acquisition_templates": audit_templates,
        "source_model_metadata_sha256": _sha256(
            stage6br_root / "RENEWAL_MODELS.json"
        ),
        "source_model_arrays_sha256": _sha256(
            stage6br_root / "RENEWAL_MODELS.npz"
        ),
        "automatic_opening_authorized": True,
        "retuning_after_seal": False,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload | {"final_audit_digest": digest}


def _run_adjudicate(
    output: Path,
    frozen: dict[str, Any],
    profile: SynergyProfile,
    profile_name: str,
    contract: SynergyContract,
    writer_contract: MotifContract,
    design_digest: str,
    candidates: Sequence[dict[str, Any]],
    controls: Sequence[dict[str, Any]],
    anchor: dict[str, Any],
    templates: Sequence[dict[str, Any]],
    stage6br_root: Path,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status,
    scientific: bool,
    auto_final_audit: bool,
) -> dict[str, Any]:
    endurance = _load_json(output / "endurance/RESULTS.json")
    by_id = {str(row["candidate_id"]): row for row in candidates}
    enduring = [
        by_id[value]
        for value in endurance.get("enduring_candidate_ids", ())
    ][:2]
    if not enduring:
        verdict = _negative_verdict(output)
        result = {
            "state": "complete",
            "stage_gate": False,
            "enduring_candidate_ids": [],
            "confirmed_candidate_ids": [],
            "final_audit_opened": False,
            "final_audit_trajectory_state": "untouched",
            "verdict": verdict,
        }
        _write_phase_outputs(
            output,
            "adjudicate",
            design_digest,
            result,
            "# Stage 6C adjudication\n\n"
            f"Verdict: **{verdict}**. The protected reserve was not opened.\n",
            "# Lay summary\n\n"
            "No candidate completed the full shared-memory, acquired-form, "
            "geometry, and endurance ladder. The final cases stayed untouched.\n",
            next_phase=None,
        )
        return result
    if not auto_final_audit:
        raise ValueError(
            "enduring Stage-6C candidates require --auto-final-audit"
        )
    final_design = _final_design(
        enduring,
        controls,
        anchor,
        templates,
        profile,
        design_digest,
        frozen,
        stage6br_root,
    )
    design_path = output / "FINAL_AUDIT_DESIGN.json"
    if design_path.exists():
        if _load_json(design_path) != final_design:
            raise ValueError("sealed Stage-6C final design changed")
    else:
        _atomic_json(design_path, final_design)
    opened = select_synergy_cohorts(
        frozen, profile, profile_name, open_final=True
    )
    cohort_path = output / "COHORTS.json"
    cohort_payload = _load_json(cohort_path)
    cohort_payload.update(
        {
            "final_audit_trajectory_state": "opened",
            "final_audit_trajectories_not_loaded": False,
            "final_audit_opened_unix": time.time(),
            "final_audit_digest": final_design["final_audit_digest"],
        }
    )
    _atomic_json(cohort_path, cohort_payload)
    final_models = [*enduring, controls[0], anchor]
    audit_templates = [row for row in templates if row["split"] == "audit"]
    configuration = _configuration_payload(frozen["stage4"]["configuration"])
    winner_items = _stage_items(
        opened["final"],
        enduring,
        configuration,
        prefix="final-audit-winner",
        replicates=profile.final_replicates,
        generations=32,
        conditions=FINAL_CONDITIONS,
        templates=audit_templates,
    )
    control_items = _stage_items(
        opened["final"][: min(8, len(opened["final"]))],
        [controls[0], anchor],
        configuration,
        prefix="final-audit-control",
        replicates=profile.final_replicates,
        generations=32,
        conditions=FINAL_CONDITIONS,
        templates=audit_templates,
    )
    items = [*winner_items, *control_items]
    status("running", "final-audit", completed=0, total=len(items))
    rows, complete = _run_json_checkpoints(
        output,
        "final-audit-stage6c",
        items,
        final_models,
        _synergy_task,
        writer_contract,
        contract,  # type: ignore[arg-type]
        frozen["stage4"]["reference"],
        design_digest,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    if not complete:
        return {
            "state": "partial_budget_exhausted",
            "stage_gate": False,
            "final_audit_opened": True,
            "final_audit_trajectory_state": "opened",
        }
    anchor_summary = _candidate_summary(
        rows, anchor, 32, profile, contract, "final-audit"
    )
    anchor_mean = float(anchor_summary["crossover"]["mean"] or 0.0)
    summaries: dict[str, Any] = {ANCHOR_CONTROL_ID: anchor_summary}
    confirmed_lineage: list[dict[str, Any]] = []
    confirmed_acquired: list[dict[str, Any]] = []
    for model in [*enduring, controls[0]]:
        candidate_id = str(model["candidate_id"])
        summary = _candidate_summary(
            rows,
            model,
            32,
            profile,
            contract,
            "final-audit",
            anchor_mean=anchor_mean,
        )
        acquisition = _acquisition_summary(
            rows,
            candidate_id,
            32,
            profile,
            contract,
            "final-audit",
        )
        causal_pass, causal = _causal_qualification(
            rows, candidate_id, 32, contract
        )
        lineage_pass = bool(
            str(model.get("share_scheme")) == "xor-kofk"
            and _base_recovery_gate(
                summary, contract, contract.qualification_generation16
            )
            and causal_pass
            and _synergy_gate(summary, contract)
        ) if scientific else str(model.get("share_scheme")) == "xor-kofk"
        acquired_lower = acquisition["effect"]["ci"][0]
        acquired_pass = bool(
            lineage_pass
            and float(acquisition["effect"]["mean"] or 0.0)
            >= contract.acquisition_minimum
            and acquired_lower is not None
            and float(acquired_lower) > 0.0
            and acquisition["fraction_templates_positive"] >= 0.75
        ) if scientific else lineage_pass
        summary.update(
            causal
            | {
                "acquisition": acquisition,
                "final_lineage_gate": lineage_pass,
                "final_acquisition_gate": acquired_pass,
            }
        )
        summaries[candidate_id] = summary
        if model in enduring and lineage_pass:
            confirmed_lineage.append(model)
        if model in enduring and acquired_pass:
            confirmed_acquired.append(model)
    if confirmed_acquired:
        verdict = "CONFIRMED_SYNERGISTIC_ACQUIRED_CA_PH"
    elif confirmed_lineage:
        verdict = "CONFIRMED_SYNERGISTIC_LINEAGE_CA_PH"
    else:
        verdict = _negative_verdict(output)
    cohort_payload.update(
        {
            "final_audit_trajectory_state": "complete",
            "final_audit_completed_unix": time.time(),
        }
    )
    _atomic_json(cohort_path, cohort_payload)
    result = {
        "state": "complete",
        "stage_gate": bool(confirmed_lineage),
        "enduring_candidate_ids": [
            str(row["candidate_id"]) for row in enduring
        ],
        "confirmed_candidate_ids": [
            str(row["candidate_id"]) for row in confirmed_lineage
        ],
        "confirmed_acquired_candidate_ids": [
            str(row["candidate_id"]) for row in confirmed_acquired
        ],
        "final_audit": summaries,
        "final_audit_opened": True,
        "final_audit_trajectory_state": "complete",
        "final_audit_digest": final_design["final_audit_digest"],
        "verdict": verdict,
    }
    _write_phase_outputs(
        output,
        "adjudicate",
        design_digest,
        result,
        "# Stage 6C adjudication\n\n"
        f"Verdict: **{verdict}**. Confirmed objects: "
        f"{result['confirmed_candidate_ids'] or 'none'}.\n",
        "# Lay summary\n\n"
        "The sealed test asks whether separate pieces truly need one another "
        "and whether they can pass on a newly acquired visible change.\n",
        next_phase=None,
    )
    return result


def _prepare_stage6c(
    output: Path,
    profile_name: str,
    *,
    auto_final_audit: bool,
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
    SynergyProfile,
    SynergyContract,
    MotifContract,
    str,
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
]:
    stage6br_root = stage6br_root.resolve()
    required6br = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "COHORTS.json",
        "RENEWAL_MODELS.json",
        "RENEWAL_MODELS.npz",
        "COMPLETE",
    )
    missing = [
        stage6br_root / name
        for name in required6br
        if not (stage6br_root / name).exists()
    ]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6B-R artifacts: {missing}")
    status6br = _load_json(stage6br_root / "STATUS.json")
    result6br = _load_json(stage6br_root / "RESULTS.json")
    cohorts6br = _load_json(stage6br_root / "COHORTS.json")
    if status6br.get("state") != "complete":
        raise ValueError("Stage-6B-R is not complete")
    if status6br.get("verdict") != "TRANSIENT_LOCAL_PH_ONLY":
        raise ValueError("Stage-6C requires the frozen Stage-6B-R verdict")
    if result6br.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6B-R final reserve is no longer untouched")
    if cohorts6br.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6B-R cohort reserve is no longer untouched")
    frozen = load_frozen_stage5r(
        stage5r_root,
        stage5_root,
        stage4_root,
        stage3r_root,
        stage3_root,
        stage2_root,
        stage1_root,
    )
    profile = SYNERGY_PROFILES[profile_name]
    contract = SynergyContract()
    writer_contract = MotifContract()
    cohorts = select_synergy_cohorts(
        frozen, profile, profile_name, open_final=False
    )
    candidates, controls, anchor = build_synergy_candidates(stage6br_root)
    templates = acquisition_templates(contract)
    development_pair_ids = {
        name: [str(pair["pair_id"]) for pair in rows]
        for name, rows in cohorts.items()
        if name != "final"
    }
    reserve_digest = hashlib.sha256(
        "\n".join(frozen["later_ids"]).encode()
    ).hexdigest()
    stage6br_hashes = {
        name: _sha256(stage6br_root / name)
        for name in required6br
        if name != "COMPLETE"
    }
    design_payload = {
        "experiment": "ca_motif_lineage_stage_6c",
        "contract": contract.to_dict(),
        "writer_contract_digest": writer_contract.digest,
        "profile_name": profile_name,
        "profile": asdict(profile),
        "phases": PHASES,
        "automatic_phase_progression": True,
        "negative_phase_does_not_trigger_retuning": True,
        "automatic_final_audit_user_authorized": bool(auto_final_audit),
        "automatic_final_audit_requires_all_prior_gates": True,
        "stage5r_design_digest": frozen["design_digest"],
        "stage6br_design_digest": _load_json(
            stage6br_root / "DESIGN.json"
        )["design_digest"],
        "frozen_stage6br_sha256": stage6br_hashes,
        "source_model_id": SOURCE_MODEL_ID,
        "configuration": frozen["stage4"]["configuration"].to_dict(),
        "candidate_factorial": {
            "share_counts": (2, 4),
            "radii": (5, 6, 7),
            "turnovers": (0.25, 0.50),
            "ecc": ("none", "hamming84"),
            "candidate_count": len(candidates),
            "candidate_ids": [str(row["candidate_id"]) for row in candidates],
            "promotion_limit": 2,
        },
        "control_ids": [
            str(row["candidate_id"]) for row in [*controls, anchor]
        ],
        "acquisition_templates": templates,
        "development_pair_ids": development_pair_ids,
        "new_semantic_futures_on_previously_exposed_pair_bank": True,
        "final_audit_pair_count": len(frozen["later_ids"]),
        "final_audit_pair_ids_sha256": reserve_digest,
        "final_audit_trajectories_loaded": False,
        "input_sha256": {
            "protocol": _sha256(PROTOCOL_PATH),
            **{
                f"stage5r_{key}": _sha256(path)
                for key, path in frozen["paths"].items()
            },
        },
        "implementation_sha256": {
            "motif_synergistic_heredity.py": _sha256(Path(__file__)),
            "motif_renewal_repair.py": _sha256(
                Path(__file__).with_name("motif_renewal_repair.py")
            ),
            "motif_minimality.py": _sha256(
                Path(__file__).with_name("motif_minimality.py")
            ),
        },
        "cleanroom_exclusion": (
            "no Wagner or Fable implementation source is read, imported, "
            "hashed, or executed"
        ),
        "claim_boundary": "engineered synthetic cellular-automaton heredity",
        "retuning_on_final_audit": False,
    }
    design_digest = hashlib.sha256(
        json.dumps(
            design_payload, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    design = design_payload | {"design_digest": design_digest}
    design_path = output / "DESIGN.json"
    if design_path.exists():
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6C design changed; refusing a mixed resume")
    else:
        _atomic_json(design_path, design)
    cohort_path = output / "COHORTS.json"
    prior = _load_json(cohort_path) if cohort_path.exists() else {}
    reserve_state = prior.get("final_audit_trajectory_state", "untouched")
    _atomic_json(
        cohort_path,
        {
            "design_digest": design_digest,
            "development_pair_ids": development_pair_ids,
            "development_pair_count": sum(
                len(rows) for rows in development_pair_ids.values()
            ),
            "final_audit_pair_count": len(frozen["later_ids"]),
            "final_audit_pair_ids_sha256": reserve_digest,
            "final_audit_trajectory_state": reserve_state,
            "final_audit_trajectories_not_loaded": reserve_state == "untouched",
            **{
                key: value
                for key, value in prior.items()
                if key.startswith("final_audit_")
                and key
                not in {
                    "final_audit_trajectory_state",
                    "final_audit_trajectories_not_loaded",
                }
            },
        },
    )
    _atomic_json(
        output / "CANDIDATES.json",
        {
            "design_digest": design_digest,
            "candidate_count": len(candidates),
            "candidates": [_candidate_public(row) for row in candidates],
            "controls": [
                _candidate_public(row) for row in [*controls, anchor]
            ],
            "source_models_frozen_before_stage6c": True,
        },
    )
    _atomic_json(
        output / "ACQUISITION_TEMPLATES.json",
        {
            "design_digest": design_digest,
            "templates": templates,
            "carrier_edited_by_acquisition": False,
        },
    )
    provenance = {
        "experiment": "ca_motif_lineage_stage_6c",
        "design_digest": design_digest,
        "permitted_inputs": (
            "published prose, code-free documentation, data artifacts, and "
            "prior code written in this clean-room reconstruction"
        ),
        "excluded_inputs": (
            "Wagner implementation code and Fable implementation code"
        ),
        "excluded_code_read_import_hash_execute": True,
        "implementation_independent": True,
    }
    provenance_path = output / "CLEANROOM_PROVENANCE.json"
    if provenance_path.exists() and _load_json(provenance_path) != provenance:
        raise ValueError("Stage-6C clean-room provenance changed")
    _atomic_json(provenance_path, provenance)
    return (
        frozen,
        cohorts,
        profile,
        contract,
        writer_contract,
        design_digest,
        candidates,
        controls,
        anchor,
        templates,
    )


def _campaign_clock(
    output: Path,
    design_digest: str,
    max_hours: float,
    *,
    resume: bool,
) -> dict[str, Any]:
    path = output / "CAMPAIGN.json"
    if path.exists():
        campaign = _load_json(path)
        if not resume:
            raise ValueError("Stage-6C output exists; use --resume")
        if campaign.get("design_digest") != design_digest:
            raise ValueError("Stage-6C campaign design mismatch")
        if not math.isclose(float(campaign["max_hours"]), max_hours):
            raise ValueError("Stage-6C max-hours changed during resume")
        return campaign
    started = time.time()
    hard_deadline = started + max_hours * 3600.0
    exploration_fraction = (
        SynergyContract().exploration_stop_hours
        / SynergyContract().max_hours
    )
    exploration_hours = max_hours * exploration_fraction
    campaign = {
        "experiment": "ca_motif_lineage_stage_6c",
        "design_digest": design_digest,
        "started_unix": started,
        "max_hours": max_hours,
        "hard_deadline_unix": hard_deadline,
        "exploration_deadline_unix": started + exploration_hours * 3600.0,
        "adjudication_reserve_hours": max_hours - exploration_hours,
        "deadline_persists_across_resume": True,
    }
    _atomic_json(path, campaign)
    return campaign


def _status_writer(
    output: Path,
    profile_name: str,
    campaign: dict[str, Any],
    active_phase: list[str],
):
    def status(state: str, current: str, **extra: Any) -> None:
        now = time.time()
        phase = active_phase[0]
        payload = {
            "state": state,
            "stage": "6c-synergistic-acquired-heredity",
            "phase": phase,
            "current": current,
            "profile": profile_name,
            "pid": os.getpid(),
            "workers_hard_max": SynergyContract().max_workers,
            "started_unix": float(campaign["started_unix"]),
            "updated_unix": now,
            "elapsed_seconds": now - float(campaign["started_unix"]),
            "hard_deadline_unix": float(campaign["hard_deadline_unix"]),
            "exploration_deadline_unix": float(
                campaign["exploration_deadline_unix"]
            ),
            "deadline_remaining_seconds": max(
                0.0, float(campaign["hard_deadline_unix"]) - now
            ),
            **extra,
        }
        _atomic_json(output / "STATUS.json", payload)
        if phase in PHASES:
            (output / phase).mkdir(parents=True, exist_ok=True)
            _atomic_json(output / phase / "STATUS.json", payload)
        progress = (
            f" {extra['completed']}/{extra['total']}"
            if "completed" in extra
            else ""
        )
        print(f"[{state}] stage6c-{phase}:{current}{progress}", flush=True)

    return status


def _require_phase_complete(
    output: Path, phase: str, design_digest: str
) -> dict[str, Any]:
    path = output / phase / "RESULTS.json"
    if not path.exists() or not (output / phase / "COMPLETE").exists():
        raise FileNotFoundError(f"completed Stage-6C predecessor required: {path}")
    result = _load_json(path)
    if result.get("design_digest") != design_digest:
        raise ValueError(f"Stage-6C {phase} design mismatch")
    if result.get("state") != "complete":
        raise ValueError(f"Stage-6C {phase} is not complete")
    return result


def _update_discovery_log(verdict: str, elapsed_seconds: float) -> None:
    path = ROOT / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"
    if not path.exists():
        return
    start = "<!-- CA_MOTIF_STAGE6C_RESULT_START -->"
    end = "<!-- CA_MOTIF_STAGE6C_RESULT_END -->"
    block = (
        f"{start}\n## CA motif-lineage Stage 6C\n\n"
        f"Verdict: `{verdict}`. Elapsed `{elapsed_seconds / 3600.0:.3f}` wall hours.\n"
        "See `results/ca-motif-lineage-stage-6c/REPORT.md` and "
        "`LAY_SUMMARY.md`.\n"
        f"{end}"
    )
    text = path.read_text(encoding="utf-8")
    if start in text and end in text:
        before, remainder = text.split(start, 1)
        _, after = remainder.split(end, 1)
        updated = before.rstrip() + "\n\n" + block + after
    else:
        updated = text.rstrip() + "\n\n" + block + "\n"
    _atomic_text(path, updated)


def run_motif_synergistic_heredity(
    output: Path,
    *,
    phase: str = "all",
    stage6br_root: Path = DEFAULT_STAGE6BR_ROOT,
    stage5r_root: Path = DEFAULT_STAGE5R_ROOT,
    stage5_root: Path = DEFAULT_STAGE5_ROOT,
    stage4_root: Path = DEFAULT_STAGE4_ROOT,
    stage3r_root: Path = DEFAULT_STAGE3R_ROOT,
    stage3_root: Path = DEFAULT_STAGE3_ROOT,
    stage2_root: Path = DEFAULT_STAGE2_ROOT,
    stage1_root: Path = DEFAULT_STAGE1_ROOT,
    profile_name: str = "reference",
    workers: int = 4,
    max_hours: float = 8.0,
    resume: bool = False,
    auto_final_audit: bool = False,
) -> dict[str, Any]:
    """Run the five-phase Stage-6C campaign under one persisted clock."""

    require_pinned_numpy()
    if phase not in (*PHASES, "all"):
        raise ValueError(f"unknown Stage-6C phase {phase!r}")
    if profile_name not in PUBLIC_PROFILES:
        raise ValueError(f"unknown Stage-6C profile {profile_name!r}")
    if workers < 1 or workers > SynergyContract().max_workers:
        raise ValueError("Stage-6C workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > SynergyContract().max_hours:
        raise ValueError("Stage-6C max-hours must be in (0, 8]")
    if profile_name == "reference" and not auto_final_audit:
        raise ValueError(
            "reference Stage-6C requires registered automatic final-audit authorization"
        )
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    _atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
    try:
        (
            frozen,
            cohorts,
            profile,
            contract,
            writer_contract,
            design_digest,
            candidates,
            controls,
            anchor,
            templates,
        ) = _prepare_stage6c(
            output,
            profile_name,
            auto_final_audit=auto_final_audit,
            stage6br_root=stage6br_root,
            stage5r_root=stage5r_root,
            stage5_root=stage5_root,
            stage4_root=stage4_root,
            stage3r_root=stage3r_root,
            stage3_root=stage3_root,
            stage2_root=stage2_root,
            stage1_root=stage1_root,
        )
        campaign = _campaign_clock(
            output, design_digest, max_hours, resume=resume
        )
        active_phase = ["prepare"]
        status = _status_writer(
            output, profile_name, campaign, active_phase
        )
        status("running", "frozen-design-verified")
        selected = PHASES if phase == "all" else (phase,)
        if phase != "all":
            for predecessor in PHASES[: PHASES.index(phase)]:
                _require_phase_complete(output, predecessor, design_digest)
        scientific = profile_name == "reference"
        result: dict[str, Any] = {
            "state": "not_started",
            "design_digest": design_digest,
        }
        runners = {
            "forensics": lambda deadline: _run_forensics(
                output, stage6br_root.resolve(), design_digest, status
            ),
            "synergy": lambda deadline: _run_synergy(
                output,
                frozen,
                cohorts,
                profile,
                contract,
                writer_contract,
                design_digest,
                candidates,
                controls,
                anchor,
                workers=workers,
                resume=resume,
                deadline=deadline,
                status=status,
                scientific=scientific,
            ),
            "plasticity": lambda deadline: _run_plasticity(
                output,
                frozen,
                cohorts,
                profile,
                contract,
                writer_contract,
                design_digest,
                candidates,
                anchor,
                templates,
                workers=workers,
                resume=resume,
                deadline=deadline,
                status=status,
                scientific=scientific,
            ),
            "endurance": lambda deadline: _run_endurance(
                output,
                frozen,
                cohorts,
                profile,
                contract,
                writer_contract,
                design_digest,
                candidates,
                controls,
                templates,
                workers=workers,
                resume=resume,
                deadline=deadline,
                status=status,
                scientific=scientific,
            ),
            "adjudicate": lambda deadline: _run_adjudicate(
                output,
                frozen,
                profile,
                profile_name,
                contract,
                writer_contract,
                design_digest,
                candidates,
                controls,
                anchor,
                templates,
                stage6br_root.resolve(),
                workers=workers,
                resume=resume,
                deadline=deadline,
                status=status,
                scientific=scientific,
                auto_final_audit=auto_final_audit,
            ),
        }
        for current_phase in selected:
            active_phase[0] = current_phase
            phase_root = output / current_phase
            phase_root.mkdir(parents=True, exist_ok=True)
            if resume and (phase_root / "COMPLETE").exists():
                result = _require_phase_complete(
                    output, current_phase, design_digest
                )
                status("skipped", "complete-checkpoint")
                continue
            if current_phase != "forensics":
                predecessor = PHASES[PHASES.index(current_phase) - 1]
                _require_phase_complete(output, predecessor, design_digest)
            deadline = float(
                campaign[
                    "hard_deadline_unix"
                    if current_phase == "adjudicate"
                    else "exploration_deadline_unix"
                ]
            )
            if time.time() >= deadline:
                result = {
                    "state": "partial_budget_exhausted",
                    "phase": current_phase,
                    "design_digest": design_digest,
                }
                status("partial_budget_exhausted", "deadline-before-phase")
                break
            manifest = {
                "experiment": "ca_motif_lineage_stage_6c",
                "phase": current_phase,
                "profile": profile_name,
                "design_digest": design_digest,
                "contract_digest": contract.digest,
                "workers": workers,
                "workers_hard_max": 4,
                "max_hours_total_campaign": max_hours,
                "resume": resume,
                "auto_final_audit": auto_final_audit,
                "campaign_started_unix": campaign["started_unix"],
                "hard_deadline_unix": campaign["hard_deadline_unix"],
                "exploration_deadline_unix": campaign[
                    "exploration_deadline_unix"
                ],
                "phase_started_unix": time.time(),
                "environment": {
                    "python": sys.version,
                    "numpy": np.__version__,
                    "platform": platform.platform(),
                    "cpu_count": os.cpu_count(),
                    "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
                },
            }
            manifest_path = phase_root / "MANIFEST.json"
            if not manifest_path.exists():
                _atomic_json(manifest_path, manifest)
            status("running", "phase-start")
            result = runners[current_phase](deadline)
            if result.get("state") != "complete":
                status(
                    str(result.get("state", "partial")), "phase-incomplete"
                )
                break
            _atomic_json(
                output / "QUEUE.json",
                {
                    "experiment": "ca_motif_lineage_stage_6c",
                    "design_digest": design_digest,
                    "state": (
                        "complete"
                        if current_phase == PHASES[-1]
                        else "automatic_progression"
                    ),
                    "completed_phase": current_phase,
                    "next_phase": (
                        PHASES[PHASES.index(current_phase) + 1]
                        if current_phase != PHASES[-1]
                        else None
                    ),
                    "automatic_launch": current_phase != PHASES[-1],
                    "final_audit_trajectory_state": result.get(
                        "final_audit_trajectory_state", "untouched"
                    ),
                },
            )
            status("completed_phase", "phase-complete")
        if result.get("state") == "complete" and selected[-1] == "adjudicate":
            _atomic_text(output / "COMPLETE", "complete\n")
            active_phase[0] = "complete"
            status(
                "complete",
                "campaign-complete",
                verdict=result.get("verdict"),
                final_audit_trajectory_state=result.get(
                    "final_audit_trajectory_state", "untouched"
                ),
            )
            if profile_name == "reference":
                _update_discovery_log(
                    str(result.get("verdict")),
                    time.time() - float(campaign["started_unix"]),
                )
        return result
    except BaseException as error:
        _atomic_json(
            output / "STATUS.json",
            {
                "state": "failed",
                "stage": "6c-synergistic-acquired-heredity",
                "pid": os.getpid(),
                "updated_unix": time.time(),
                "error": repr(error),
            },
        )
        raise


__all__ = [
    "DEFAULT_STAGE6BR_ROOT",
    "PHASES",
    "PUBLIC_PROFILES",
    "SYNERGY_PROFILES",
    "SynergyContract",
    "SynergyProfile",
    "acquisition_templates",
    "build_synergy_candidates",
    "build_synergy_scale_variants",
    "carrier_code_roundtrip",
    "propagate_share_channels",
    "reconstruct_share_field",
    "run_motif_synergistic_heredity",
    "select_synergy_cohorts",
    "simulate_synergistic_lineage",
    "xor_reconstruct_codes",
    "xor_share_codes",
]
