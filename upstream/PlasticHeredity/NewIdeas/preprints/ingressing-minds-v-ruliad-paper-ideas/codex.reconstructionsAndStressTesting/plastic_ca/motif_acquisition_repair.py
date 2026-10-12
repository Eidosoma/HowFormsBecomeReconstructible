"""Stage-6C-R repair of acquired texture writing in cellular automata.

The completed Stage-6C campaign is immutable input.  This module adds a
separate, locally observed, secret-shared texture latch; it does not modify the
frozen Stage-6C implementation or its results.
"""

from __future__ import annotations

from collections import deque
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
)
from .motif_minimality import (
    DEFAULT_STAGE1_ROOT,
    DEFAULT_STAGE2_ROOT,
    DEFAULT_STAGE3_ROOT,
    DEFAULT_STAGE3R_ROOT,
    DEFAULT_STAGE4_ROOT,
    DEFAULT_STAGE5_ROOT,
    DEFAULT_STAGE5R_ROOT,
    _founder_bounded_payload,
    _quantize,
    _resize_board,
    _score_state,
    _swap_histories,
    load_frozen_stage5r,
)
from .motif_minimality_repair import repair_origins
from .motif_renewal_repair import latch_update
from .motif_synergistic_heredity import (
    DEFAULT_STAGE6BR_ROOT,
    SYNERGY_PROFILES,
    SynergyContract,
    _carrier_diagnostics,
    _encode_carrier,
    _joint_payload,
    acquisition_templates,
    build_synergy_candidates,
    carrier_code_roundtrip,
    propagate_share_channels,
    reconstruct_share_field,
    select_synergy_cohorts,
)


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_ACQUISITION_REPAIR_PROTOCOL.md"
DEFAULT_STAGE6C_ROOT = ROOT / "results/ca-motif-lineage-stage-6c"
PHASES = ("forensics", "screen", "qualify", "endurance", "adjudicate")
STAGE6C_WINNER = "synergy-xor-k04-h07-r50-eh84"

SCREEN_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
    "acquisition_write_disabled",
)
QUALIFICATION_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
    "acquisition_write_disabled",
    "zero_every_boundary",
    "shuffle_every_boundary",
    "transport_disabled",
    "ablate_after_g5",
    "rescue_same_enter_g6",
    "rescue_opposite_enter_g6",
    "statistical_disabled",
    "translated_patch",
)
ENDURANCE_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
)
ALL_CONDITIONS = tuple(dict.fromkeys((*QUALIFICATION_CONDITIONS,)))


@dataclass(frozen=True)
class AcquisitionRepairContract:
    implementation_version: str = "ca-motif-acquisition-repair-v1"
    namespace: str = "plastic-ca-motif-acquisition-repair-v1"
    rule: int = 31649
    generation_sweeps: int = 64
    statistical_read_sweeps: int = 32
    observe_start: int = 57
    acquisition_generation: int = 4
    acquisition_start: int = 41
    acquisition_end: int = 48
    texture_trace_sweeps: int = 8
    process_noise: float = 0.002
    bit_corruption: float = 0.01
    texture_seed_count: int = 4
    texture_seed_radius: int = 3
    texture_hops: int = 3
    texture_bits: int = 4
    strict_alpha: float = 0.025
    screen_read_minimum: float = 0.25
    qualification_read_minimum: float = 0.15
    qualification_terminal_minimum: float = 0.05
    endurance_generation32_minimum: float = 0.10
    endurance_generation64_minimum: float = 0.05
    active_rewrite_minimum: float = 0.10
    joint_accuracy_minimum: float = 0.75
    subset_accuracy_maximum: float = 0.60
    loss_fraction: float = 0.70
    rescue_fraction: float = 0.70
    template_positive_fraction: float = 0.75
    survival_minimum: float = 0.90
    translation_retention: float = 0.70
    statistical_retention: float = 0.70
    decoder_splits: int = 4
    max_workers: int = 4
    max_hours: float = 8.0
    exploration_stop_hours: float = 5.5
    adjudication_reserve_hours: float = 2.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {
            "visible_reset": "bitwise-identical before every generation",
            "texture_share_algebra": "four-of-four XOR",
            "texture_ecc": "Hamming(8,4)",
            "writer_observes_environment_bits": False,
            "runtime_family_labels": False,
            "random_streams": "semantic, paired, worker-independent",
            "claim_boundary": "engineered synthetic CA heredity",
        }

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True)
class AcquisitionRepairProfile:
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


ACQUISITION_REPAIR_PROFILES: dict[str, AcquisitionRepairProfile] = {
    "smoke": AcquisitionRepairProfile(2, 2, 2, 2, 2, 2, 2, 2, 100, 4),
    "pilot": AcquisitionRepairProfile(8, 4, 16, 4, 8, 4, 8, 4, 1_000, 12),
    "reference": AcquisitionRepairProfile(
        24, 4, 32, 8, 8, 4, 62, 4, 10_000, 24
    ),
}
PUBLIC_PROFILES = tuple(ACQUISITION_REPAIR_PROFILES)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def walsh_texture_basis() -> np.ndarray:
    """Return a fixed sequency-ordered 16 by 16 Walsh basis."""

    matrix = np.asarray([[1.0]], dtype=np.float32)
    while matrix.shape[0] < 16:
        matrix = np.block([[matrix, matrix], [matrix, -matrix]])
    changes = np.sum(matrix[:, 1:] != matrix[:, :-1], axis=1)
    order = np.lexsort((np.arange(16), changes))
    return matrix[order].astype(np.float32)


TEXTURE_BASIS = walsh_texture_basis()


def texture_encode(patches: np.ndarray, rank: int) -> np.ndarray:
    """Project signed 4 by 4 patches onto the registered Walsh modes."""

    values = np.asarray(patches, dtype=np.float32)
    if values.shape[-2:] != (4, 4):
        raise ValueError("texture patches must be 4 by 4")
    if rank not in (4, 8, 16):
        raise ValueError("texture rank must be 4, 8, or 16")
    flat = values.reshape(values.shape[:-2] + (16,))
    return (flat @ TEXTURE_BASIS[:rank].T / np.float32(16.0)).astype(np.float32)


def texture_decode(coefficients: np.ndarray, rank: int) -> np.ndarray:
    """Decode registered Walsh coefficients to a signed 4 by 4 texture."""

    values = np.asarray(coefficients, dtype=np.float32)
    if values.shape[-1] != rank:
        raise ValueError("texture coefficient rank mismatch")
    flat = values @ TEXTURE_BASIS[:rank]
    return np.clip(flat, -1.0, 1.0).reshape(values.shape[:-1] + (4, 4))


def texture_codec(rank: int) -> dict[str, Any]:
    return {
        "bits": 4,
        "rank": rank,
        "quantizer_scale": np.ones(rank, dtype=np.float32),
        "basis": TEXTURE_BASIS[:rank].copy(),
        "codec_id": f"texture-walsh-r{rank:02d}-q04",
    }


def build_acquisition_repair_candidates(
    stage6br_root: Path = DEFAULT_STAGE6BR_ROOT,
) -> list[dict[str, Any]]:
    """Build the frozen 24-cell texture repair factorial."""

    statistical, _, _ = build_synergy_candidates(stage6br_root)
    by_id = {str(row["candidate_id"]): row for row in statistical}
    if STAGE6C_WINNER not in by_id:
        raise ValueError("frozen Stage-6C statistical scaffold is missing")
    scaffold = by_id[STAGE6C_WINNER]
    rows: list[dict[str, Any]] = []
    for rank in (4, 8, 16):
        for strength in (0.35, 0.60):
            for read_sweeps in (32, 48):
                for rho in (0.50, 0.75):
                    rows.append(
                        {
                            "candidate_id": (
                                f"texture-r{rank:02d}-s{int(strength * 100):02d}-"
                                f"d{read_sweeps:02d}-rho{int(rho * 100):02d}"
                            ),
                            "rank": rank,
                            "bits": 4,
                            "payload_bits": rank * 4,
                            "codec_model": texture_codec(rank),
                            "read_strength": strength,
                            "read_sweeps": read_sweeps,
                            "rho": rho,
                            "seed_count": 4,
                            "seed_radius": 3,
                            "germination_hops": 3,
                            "share_scheme": "xor-kofk",
                            "seed_mode": "secret-shared",
                            "joint_read_required": True,
                            "ecc": "hamming84",
                            "statistical_candidate": scaffold,
                            "promotable": True,
                        }
                    )
    if len(rows) != 24:
        raise AssertionError("Stage-6C-R candidate grid must contain 24 cells")
    return rows


def _candidate_public(candidate: dict[str, Any]) -> dict[str, Any]:
    basis = np.asarray(candidate["codec_model"]["basis"], dtype=np.float32)
    return {
        key: value
        for key, value in candidate.items()
        if key not in {"codec_model", "statistical_candidate"}
    } | {
        "codec_id": candidate["codec_model"]["codec_id"],
        "basis_sha256": hashlib.sha256(basis.tobytes()).hexdigest(),
        "statistical_scaffold_id": candidate["statistical_candidate"][
            "candidate_id"
        ],
    }


def texture_seed_origins(
    centers: np.ndarray, extent: int, radius: int
) -> np.ndarray:
    """Place four shares on a local cardinal constellation around each center."""

    if radius < 1:
        raise ValueError("texture seed radius must be positive")
    base = np.asarray(centers, dtype=np.int64)
    offsets = np.asarray(
        ((-radius, 0), (0, radius), (radius, 0), (0, -radius)),
        dtype=np.int64,
    )
    return ((base[:, None, :] + offsets[None, :, :]) % extent).astype(np.int16)


def _patch_indices(centers: np.ndarray, extent: int) -> tuple[np.ndarray, np.ndarray]:
    base = np.asarray(centers, dtype=np.int64)
    offsets = np.arange(-2, 2, dtype=np.int64)
    ys = (base[:, 0, None] + offsets[None, :]) % extent
    xs = (base[:, 1, None] + offsets[None, :]) % extent
    return ys, xs


def observe_texture(state: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """Read a signed local patch; this writer API has no target or label input."""

    values = np.asarray(state, dtype=np.bool_)
    ys, xs = _patch_indices(centers, values.shape[1])
    patches = np.empty((len(values), 4, 4), dtype=np.float32)
    for sample in range(len(values)):
        patches[sample] = np.where(
            values[sample][np.ix_(ys[sample], xs[sample])], 1.0, -1.0
        )
    return patches


def apply_texture_reader(
    predicted: np.ndarray,
    centers: np.ndarray,
    coefficients: np.ndarray,
    uniforms: np.ndarray,
    strength: float,
) -> np.ndarray:
    """Bias a local visible patch using only a reconstructed texture field."""

    result = np.asarray(predicted, dtype=np.bool_).copy()
    texture = texture_decode(coefficients, coefficients.shape[-1])
    ys, xs = _patch_indices(centers, result.shape[1])
    random = np.asarray(uniforms, dtype=np.float64)
    for sample in range(len(result)):
        target = texture[sample] >= 0.0
        probability = np.clip(
            np.abs(texture[sample]) * np.float32(strength), 0.0, 1.0
        )
        local_random = random[sample][np.ix_(ys[sample], xs[sample])]
        current = result[sample][np.ix_(ys[sample], xs[sample])]
        result[sample][np.ix_(ys[sample], xs[sample])] = np.where(
            local_random < probability, target, current
        )
    return result


def _apply_environment(
    state: np.ndarray, centers: np.ndarray, environmental_patches: np.ndarray
) -> None:
    ys, xs = _patch_indices(centers, state.shape[1])
    for sample in range(len(state)):
        state[sample][np.ix_(ys[sample], xs[sample])] = environmental_patches[
            sample
        ]


def _texture_match(
    state: np.ndarray, centers: np.ndarray, environmental_patches: np.ndarray
) -> np.ndarray:
    observed = observe_texture(state, centers)
    target = np.where(environmental_patches, 1.0, -1.0)
    return np.mean(observed * target, axis=(1, 2))


def _semantic_uniforms(
    pair_id: str,
    purpose: str,
    generation: int,
    sweep: int,
    replicates: int,
    extent: int,
    namespace: str,
) -> np.ndarray:
    rng = np.random.default_rng(
        _hash_seed(namespace, pair_id, purpose, generation, sweep, extent)
    )
    half = rng.random((replicates, extent, extent))
    return np.concatenate((half, half), axis=0)


def _environment_samples(
    template: np.ndarray, replicates: int, assignment_swap: bool
) -> np.ndarray:
    left = np.asarray(template, dtype=np.bool_)
    right = ~left
    if assignment_swap:
        left, right = right, left
    return np.concatenate(
        (
            np.repeat(left[None], replicates, axis=0),
            np.repeat(right[None], replicates, axis=0),
        ),
        axis=0,
    )


def _copy_texture_codes(
    shares: np.ndarray,
    pair_id: str,
    generation: int,
    replicates: int,
    contract: AcquisitionRepairContract,
) -> tuple[np.ndarray, float]:
    values = np.asarray(shares, dtype=np.uint8)
    rng = np.random.default_rng(
        _hash_seed(contract.namespace, pair_id, "texture-copy", generation, values.shape[-1])
    )
    half = rng.random((replicates,) + values.shape[1:] + (8,))
    flips = np.concatenate((half, half), axis=0) < contract.bit_corruption
    decoded, uncorrectable = carrier_code_roundtrip(values, "hamming84", flips)
    return decoded.astype(np.uint8), float(uncorrectable)


def _texture_field_at_centers(
    shares: np.ndarray,
    active: np.ndarray,
    centers: np.ndarray,
    candidate: dict[str, Any],
    extent: int,
    hops: int,
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    origins = texture_seed_origins(centers, extent, int(candidate["seed_radius"]))
    raw, occupied, trace = propagate_share_channels(
        shares, active, origins, extent, hops
    )
    field, complete = reconstruct_share_field(raw, occupied, candidate)
    index = np.arange(len(centers))
    values = field[index, centers[:, 0], centers[:, 1]].copy()
    valid = complete[index, centers[:, 0], centers[:, 1]].copy()
    values[~valid] = 0.0
    return values, valid, trace


def _zero_texture(
    samples: int,
    candidate: dict[str, Any],
    contract: AcquisitionRepairContract,
    pair_id: str,
    generation: int,
    purpose: str,
) -> tuple[np.ndarray, np.ndarray]:
    return _encode_carrier(
        np.zeros((samples, int(candidate["rank"])), dtype=np.float32),
        candidate,
        contract,
        pair_id,
        generation,
        purpose=purpose,
    )


def _entry_texture_intervention(
    shares: np.ndarray,
    active: np.ndarray,
    candidate: dict[str, Any],
    condition: str,
    generation: int,
    pair_id: str,
    replicates: int,
    source_exits: Sequence[tuple[np.ndarray, np.ndarray]] | None,
    contract: AcquisitionRepairContract,
) -> tuple[np.ndarray, np.ndarray]:
    result = np.asarray(shares, dtype=np.uint8).copy()
    enabled = np.asarray(active, dtype=np.bool_).copy()
    if condition == "zero_every_boundary":
        result, enabled = _zero_texture(
            len(result), candidate, contract, pair_id, generation, "zero-boundary"
        )
    elif condition == "shuffle_every_boundary":
        result = np.roll(result, 1, axis=-1)
    if condition == "proper_subset":
        enabled[:, -1, :] = False
    if generation == 6 and condition in (
        "ablate_after_g5",
        "rescue_same_enter_g6",
        "rescue_opposite_enter_g6",
    ):
        result, enabled = _zero_texture(
            len(result), candidate, contract, pair_id, generation, "ablation"
        )
    if generation == 6 and condition in (
        "rescue_same_enter_g6",
        "rescue_opposite_enter_g6",
    ):
        if source_exits is None or len(source_exits) < 5:
            raise ValueError("texture rescue requires intact exits through generation 5")
        result = np.asarray(source_exits[4][0], dtype=np.uint8).copy()
        enabled = np.asarray(source_exits[4][1], dtype=np.bool_).copy()
        if condition == "rescue_opposite_enter_g6":
            result = _swap_histories(result, replicates)
            enabled = _swap_histories(enabled, replicates)
    return result, enabled


def simulate_acquired_texture_lineage(
    pair: dict[str, Any],
    configuration: ReaderConfiguration,
    candidate: dict[str, Any],
    condition: str,
    replicates: int,
    generations: int,
    reference: dict[int, dict[str, np.ndarray]],
    writer_contract: MotifContract,
    contract: AcquisitionRepairContract,
    environmental_template: np.ndarray,
    *,
    assignment_swap: bool = False,
    extent: int = 16,
    scale_mode: str = "fixed",
    source_exits: Sequence[tuple[np.ndarray, np.ndarray]] | None = None,
    retain_exits: bool = False,
) -> tuple[dict[str, Any], list[tuple[np.ndarray, np.ndarray]]]:
    """Run one visible-reset lineage with a locally written texture latch."""

    if condition not in ALL_CONDITIONS:
        raise ValueError(f"unknown Stage-6C-R condition {condition!r}")
    if extent not in (16, 32, 64):
        raise ValueError("Stage-6C-R extents are 16, 32, and 64")
    if scale_mode not in ("fixed", "diameter"):
        raise ValueError("scale mode must be fixed or diameter")
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
    statistical = candidate["statistical_candidate"]
    reference_probability = reference[configuration.write_window][
        "motif_probability"
    ]
    founder, founder_terminal = _founder_bounded_payload(
        pair,
        statistical,
        reference_probability,
        replace(writer_contract, rule=contract.rule),
        replicates,
        extent,
        contract.rule,
    )
    statistical_energy = decode_payload(founder, statistical["codec_model"])
    shares, active = _zero_texture(
        2 * replicates, candidate, contract, pair_id, 0, "neutral-founder"
    )
    alive = np.ones(2 * replicates, dtype=np.bool_)
    environment = _environment_samples(
        np.asarray(environmental_template, dtype=np.bool_),
        replicates,
        assignment_swap,
    )
    scale = extent / 16.0 if scale_mode == "diameter" else 1.0
    radius = max(1, int(round(float(candidate["seed_radius"]) * scale)))
    hops = max(1, int(round(float(candidate["germination_hops"]) * scale)))
    read_sweeps = int(candidate["read_sweeps"])
    checkpoints = {
        value
        for value in (1, 2, 4, 5, 6, 8, 16, 32, 64)
        if value <= generations
    }
    outcomes: dict[str, Any] = {}
    texture_history: dict[str, Any] = {}
    carrier_history: dict[str, Any] = {}
    writer_history: dict[str, Any] = {}
    exits: list[tuple[np.ndarray, np.ndarray]] = []
    uncorrectable_values: list[float] = []

    for generation in range(1, generations + 1):
        translated = condition == "translated_patch"
        centers = repair_origins(
            pair_id,
            generation,
            replicates,
            extent,
            "co-located",
            translated=translated,
        )
        shares, active = _entry_texture_intervention(
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
        shares, uncorrectable = _copy_texture_codes(
            shares, pair_id, generation, replicates, contract
        )
        uncorrectable_values.append(uncorrectable)
        entry_payload, entry_valid = _joint_payload(shares, active, candidate)
        effective_hops = 0 if condition == "transport_disabled" else hops
        reader_payload, reader_valid, wave_trace = _texture_field_at_centers(
            shares,
            active,
            centers,
            {**candidate, "seed_radius": radius},
            extent,
            effective_hops,
        )
        state = reset.copy()
        state[~alive] = False
        recent: deque[np.ndarray] = deque(maxlen=writer_contract.observation_window)
        trace_sum = np.zeros((2 * replicates, 4, 4), dtype=np.float64)
        trace_count = 0
        read_state: np.ndarray | None = None
        if generation == contract.acquisition_generation:
            trace_start = contract.acquisition_start
            trace_end = contract.acquisition_end
        else:
            trace_end = read_sweeps
            trace_start = read_sweeps - contract.texture_trace_sweeps + 1
        for sweep in range(1, contract.generation_sweeps + 1):
            predicted = _step(state, contract.rule)
            if (
                condition != "statistical_disabled"
                and sweep <= contract.statistical_read_sweeps
            ):
                predicted = apply_energy_reader(
                    predicted,
                    statistical_energy,
                    _semantic_uniforms(
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
                predicted = apply_texture_reader(
                    predicted,
                    centers,
                    reader_payload,
                    _semantic_uniforms(
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
            predicted ^= _semantic_uniforms(
                pair_id,
                "process",
                generation,
                sweep,
                replicates,
                extent,
                contract.namespace,
            ) < contract.process_noise
            predicted[~alive] = False
            if (
                condition != "sham"
                and generation == contract.acquisition_generation
                and contract.acquisition_start <= sweep <= contract.acquisition_end
            ):
                _apply_environment(predicted, centers, environment)
            state = predicted
            if trace_start <= sweep <= trace_end:
                trace_sum += observe_texture(state, centers)
                trace_count += 1
            if sweep == read_sweeps:
                read_state = state.copy()
            if sweep >= contract.observe_start:
                recent.append(live_2x2_counts_batch(state))
        if trace_count != contract.texture_trace_sweeps:
            raise AssertionError("texture eligibility trace length changed")
        if read_state is None:
            raise AssertionError("texture read checkpoint was not captured")
        alive &= state.any(axis=(1, 2))
        proposal = texture_encode(
            (trace_sum / float(trace_count)).astype(np.float32),
            int(candidate["rank"]),
        )
        proposal, clipping = _quantize(proposal, candidate["codec_model"])
        writer_connected = bool(np.all(reader_valid | ~alive))
        if generation < contract.acquisition_generation:
            next_payload = np.zeros_like(entry_payload)
        elif (
            generation == contract.acquisition_generation
            and condition == "acquisition_write_disabled"
        ):
            next_payload = entry_payload.copy()
        elif not writer_connected:
            next_payload = np.zeros_like(entry_payload)
        elif generation == contract.acquisition_generation:
            # Registered critical-period full write.  The writer receives only
            # its observed eligibility trace, never the environment template.
            next_payload = proposal
        elif condition == "no_rewrite":
            next_payload, _ = _quantize(
                np.float32(candidate["rho"]) * entry_payload,
                candidate["codec_model"],
            )
        else:
            next_payload, _ = latch_update(
                entry_payload,
                proposal,
                float(candidate["rho"]),
                candidate["codec_model"],
            )
        shares, active = _encode_carrier(
            next_payload,
            candidate,
            contract,
            pair_id,
            generation,
            purpose="texture-write",
        )
        active[~alive] = False

        if generation in checkpoints:
            outcome, _ = _score_state(
                state,
                recent,
                pair,
                founder_terminal,
                replicates,
                writer_contract,
            )
            outcomes[str(generation)] = outcome
            read_match = _texture_match(read_state, centers, environment)
            terminal_match = _texture_match(state, centers, environment)
            texture_history[str(generation)] = {
                "read_match_mean": float(np.mean(read_match)),
                "read_direction_a_mean": float(np.mean(read_match[:replicates])),
                "read_direction_b_mean": float(np.mean(read_match[replicates:])),
                "terminal_match_mean": float(np.mean(terminal_match)),
                "terminal_direction_a_mean": float(
                    np.mean(terminal_match[:replicates])
                ),
                "terminal_direction_b_mean": float(
                    np.mean(terminal_match[replicates:])
                ),
            }
            diagnostic = _carrier_diagnostics(
                shares,
                active,
                candidate,
                replicates,
                _hash_seed(
                    contract.namespace, pair_id, generation, "texture-decoder"
                ),
                contract.decoder_splits,
            )
            carrier_history[str(generation)] = diagnostic | {
                "entry_complete_fraction": float(np.mean(entry_valid)),
                "reader_complete_fraction": float(np.mean(reader_valid)),
                "wave_trace": wave_trace,
            }
            writer_history[str(generation)] = {
                "trace_start": trace_start,
                "trace_end": trace_end,
                "trace_count": trace_count,
                "proposal_mean_abs": float(np.mean(np.abs(proposal))),
                "quantizer_clipping": float(clipping),
                "writer_connected": writer_connected,
            }
        if retain_exits:
            exits.append((shares.copy(), active.copy()))

    result = {
        "candidate_id": str(candidate["candidate_id"]),
        "condition": condition,
        "pair_id": pair_id,
        "extent": extent,
        "scale_mode": scale_mode,
        "replicates": replicates,
        "generations": generations,
        "reset_sha256": hashlib.sha256(reset_a.tobytes()).hexdigest(),
        "reset_asserted_before_every_generation": True,
        "environment_applied": condition != "sham",
        "environment_not_passed_to_writer": True,
        "assignment_swap": assignment_swap,
        "texture_rank": int(candidate["rank"]),
        "texture_seed_radius": radius,
        "texture_hops": hops,
        "texture_payload_bits": int(candidate["payload_bits"]),
        "physical_encoded_bits": int(candidate["rank"]) * 4 * 8
        + int(candidate["rank"]) * 4,
        "physical_value_bits": int(candidate["rank"]) * 4 * 8,
        "physical_occupancy_bits": int(candidate["rank"]) * 4,
        "statistical_scaffold_id": statistical["candidate_id"],
        "statistical_scaffold_frozen": True,
        "outcomes": outcomes,
        "texture_history": texture_history,
        "carrier_history": carrier_history,
        "writer_history": writer_history,
        "survival_fraction": float(np.mean(alive)),
        "copy_uncorrectable_fraction": float(np.mean(uncorrectable_values)),
    }
    return result, exits


def _texture_pair_task(
    payload: tuple[
        dict[str, Any],
        list[dict[str, Any]],
        MotifContract,
        AcquisitionRepairContract,
        dict[int, dict[str, np.ndarray]],
    ]
) -> dict[str, Any]:
    item, models, writer_contract, contract, reference = payload
    candidate_id = str(item["candidate_id"])
    by_id = {str(row["candidate_id"]): row for row in models}
    if candidate_id not in by_id:
        raise ValueError(f"texture candidate is missing: {candidate_id}")
    candidate = by_id[candidate_id]
    configuration = ReaderConfiguration(**item["configuration"])
    template = np.asarray(item["environmental_template"], dtype=np.bool_)
    common = dict(
        pair=item["pair"],
        configuration=configuration,
        candidate=candidate,
        replicates=int(item["replicates"]),
        generations=int(item["generations"]),
        reference=reference,
        writer_contract=writer_contract,
        contract=contract,
        environmental_template=template,
        assignment_swap=bool(item["assignment_swap"]),
        extent=int(item.get("extent", 16)),
        scale_mode=str(item.get("scale_mode", "fixed")),
    )
    intact, exits = simulate_acquired_texture_lineage(
        condition="intact", retain_exits=True, **common
    )
    conditions: dict[str, Any] = {"intact": intact}
    for condition in item["conditions"]:
        if condition == "intact":
            continue
        result, _ = simulate_acquired_texture_lineage(
            condition=str(condition), source_exits=exits, **common
        )
        conditions[str(condition)] = result
    return {
        "checkpoint": item["checkpoint"],
        "analysis_kind": str(item.get("analysis_kind", "lineage")),
        "pair_id": item["pair"]["pair_id"],
        "candidate_id": candidate_id,
        "template_pair_id": item["template_pair_id"],
        "template_ids": item["template_ids"],
        "assignment_swap": bool(item["assignment_swap"]),
        "extent": int(item.get("extent", 16)),
        "scale_mode": str(item.get("scale_mode", "fixed")),
        "replicates": int(item["replicates"]),
        "generations": int(item["generations"]),
        "conditions": conditions,
    }


def _metric(
    row: dict[str, Any], condition: str, generation: int, key: str
) -> float:
    return float(
        row["conditions"][condition]["texture_history"][str(generation)][key]
    )


def _paired_texture_effects(
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
        if condition not in row.get("conditions", {}) or "sham" not in row.get(
            "conditions", {}
        ):
            continue
        try:
            values.append(
                _metric(row, condition, generation, key)
                - _metric(row, "sham", generation, key)
            )
        except KeyError:
            continue
    return values


def _boot(
    values: Sequence[float],
    profile: AcquisitionRepairProfile,
    contract: AcquisitionRepairContract,
    *key: object,
) -> dict[str, Any]:
    return _bootstrap(
        values,
        profile.bootstrap_resamples,
        _hash_seed(contract.namespace, *key),
        contract.strict_alpha,
    )


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        return 1.0
    return numerator / denominator


def _texture_summary(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
    profile: AcquisitionRepairProfile,
    contract: AcquisitionRepairContract,
    phase: str,
) -> dict[str, Any]:
    candidate_id = str(candidate["candidate_id"])
    read = _paired_texture_effects(
        rows, candidate_id, "intact", generation, "read_match_mean"
    )
    terminal = _paired_texture_effects(
        rows, candidate_id, "intact", generation, "terminal_match_mean"
    )
    passive = _paired_texture_effects(
        rows, candidate_id, "no_rewrite", generation, "read_match_mean"
    )
    active = [left - right for left, right in zip(read, passive)]
    template_values: dict[str, list[float]] = {}
    for row, value in zip(
        [row for row in rows if row.get("candidate_id") == candidate_id], read
    ):
        template_values.setdefault(str(row["template_pair_id"]), []).append(value)
    template_means = {
        key: float(np.mean(value)) for key, value in template_values.items()
    }
    controls: dict[str, float] = {}
    for condition in (
        "no_rewrite",
        "proper_subset",
        "read_disabled",
        "acquisition_write_disabled",
        "zero_every_boundary",
        "shuffle_every_boundary",
        "transport_disabled",
    ):
        values = _paired_texture_effects(
            rows, candidate_id, condition, generation, "read_match_mean"
        )
        if values:
            controls[condition] = _safe_ratio(
                float(np.mean(values)), float(np.mean(read)) if read else 0.0
            )
    joint_values: list[float] = []
    subset_rows: list[list[float]] = []
    survival: list[float] = []
    inherited: list[float] = []
    inherited_sham: list[float] = []
    uncorrectable: list[float] = []
    for row in rows:
        if row.get("candidate_id") != candidate_id:
            continue
        try:
            carrier = row["conditions"]["intact"]["carrier_history"][
                str(generation)
            ]
            joint_values.append(float(carrier["joint_balanced_accuracy"]))
            subset_rows.append(
                [
                    float(value)
                    for value in carrier["proper_subset_balanced_accuracies"]
                ]
            )
            survival.append(
                float(row["conditions"]["intact"]["survival_fraction"])
            )
            inherited.append(
                float(
                    row["conditions"]["intact"]["outcomes"][str(generation)][
                        "terminal"
                    ]["crossover"]
                )
            )
            inherited_sham.append(
                float(
                    row["conditions"]["sham"]["outcomes"][str(generation)][
                        "terminal"
                    ]["crossover"]
                )
            )
            uncorrectable.append(
                float(
                    row["conditions"]["intact"][
                        "copy_uncorrectable_fraction"
                    ]
                )
            )
        except KeyError:
            continue
    subset: list[float] = []
    subset_index: int | None = None
    if subset_rows:
        matrix = np.asarray(subset_rows, dtype=np.float64)
        subset_index = int(np.argmax(np.mean(matrix, axis=0)))
        subset = matrix[:, subset_index].tolist()
    read_mean = float(np.mean(read)) if read else 0.0
    inherited_mean = float(np.mean(inherited)) if inherited else 0.0
    inherited_sham_mean = (
        float(np.mean(inherited_sham)) if inherited_sham else 0.0
    )
    translated = _paired_texture_effects(
        rows, candidate_id, "translated_patch", generation, "read_match_mean"
    )
    result: dict[str, Any] = {
        "candidate": _candidate_public(candidate),
        "generation": generation,
        "read_acquisition": _boot(
            read, profile, contract, phase, candidate_id, generation, "read"
        ),
        "terminal_acquisition": _boot(
            terminal,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "terminal",
        ),
        "active_rewrite_advantage": _boot(
            active,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "active",
        ),
        "joint_decoder": _boot(
            joint_values,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "joint",
        ),
        "proper_subset_decoder": _boot(
            subset,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "subset",
        ),
        "worst_proper_subset_index": subset_index,
        "control_retention": controls,
        "template_means": template_means,
        "fraction_templates_positive": (
            float(np.mean(np.asarray(list(template_means.values())) > 0.0))
            if template_means
            else 0.0
        ),
        "survival_mean": float(np.mean(survival)) if survival else 0.0,
        "statistical_scaffold_intact_mean": inherited_mean,
        "statistical_scaffold_sham_mean": inherited_sham_mean,
        "statistical_scaffold_retention": (
            inherited_mean / inherited_sham_mean
            if inherited_sham_mean > 0.0
            else 0.0
        ),
        "translation_retention": (
            _safe_ratio(float(np.mean(translated)), read_mean)
            if translated
            else None
        ),
        "copy_uncorrectable_mean": (
            float(np.mean(uncorrectable)) if uncorrectable else 0.0
        ),
    }
    if "ablate_after_g5" in next(
        (
            row["conditions"]
            for row in rows
            if row.get("candidate_id") == candidate_id
        ),
        {},
    ):
        ablated = _paired_texture_effects(
            rows, candidate_id, "ablate_after_g5", generation, "read_match_mean"
        )
        rescued = _paired_texture_effects(
            rows,
            candidate_id,
            "rescue_same_enter_g6",
            generation,
            "read_match_mean",
        )
        opposite = _paired_texture_effects(
            rows,
            candidate_id,
            "rescue_opposite_enter_g6",
            generation,
            "read_match_mean",
        )
        result["ablation_retention"] = _safe_ratio(
            float(np.mean(ablated)) if ablated else 0.0, read_mean
        )
        result["same_rescue_retention"] = _safe_ratio(
            float(np.mean(rescued)) if rescued else 0.0, read_mean
        )
        result["opposite_rescue"] = _boot(
            opposite,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "opposite-rescue",
        )
    return result


def _ci_bound(summary: dict[str, Any], index: int) -> float | None:
    value = summary.get("ci", [None, None])[index]
    return None if value is None else float(value)


def _screen_gate(
    summary: dict[str, Any], contract: AcquisitionRepairContract
) -> bool:
    read = summary["read_acquisition"]
    joint = summary["joint_decoder"]
    subset = summary["proper_subset_decoder"]
    controls = summary["control_retention"]
    required = (
        "no_rewrite",
        "proper_subset",
        "read_disabled",
        "acquisition_write_disabled",
    )
    return bool(
        float(read.get("mean") or 0.0) >= contract.screen_read_minimum
        and (_ci_bound(read, 0) or -math.inf) > 0.0
        and (_ci_bound(joint, 0) or -math.inf)
        >= contract.joint_accuracy_minimum
        and (_ci_bound(subset, 1) or math.inf)
        <= contract.subset_accuracy_maximum
        and all(
            controls.get(condition, 1.0) <= 1.0 - contract.loss_fraction
            for condition in required
        )
        and summary["survival_mean"] >= contract.survival_minimum
        and summary["statistical_scaffold_retention"]
        >= contract.statistical_retention
    )


def _qualification_gate(
    summary: dict[str, Any], contract: AcquisitionRepairContract
) -> bool:
    read = summary["read_acquisition"]
    terminal = summary["terminal_acquisition"]
    active = summary["active_rewrite_advantage"]
    controls = summary["control_retention"]
    required = (
        "no_rewrite",
        "proper_subset",
        "read_disabled",
        "acquisition_write_disabled",
        "zero_every_boundary",
        "shuffle_every_boundary",
        "transport_disabled",
    )
    opposite = summary.get("opposite_rescue", {})
    return bool(
        float(read.get("mean") or 0.0)
        >= contract.qualification_read_minimum
        and (_ci_bound(read, 0) or -math.inf) > 0.0
        and float(terminal.get("mean") or 0.0)
        >= contract.qualification_terminal_minimum
        and (_ci_bound(terminal, 0) or -math.inf) > 0.0
        and float(active.get("mean") or 0.0)
        >= contract.active_rewrite_minimum
        and (_ci_bound(active, 0) or -math.inf) > 0.0
        and summary["fraction_templates_positive"]
        >= contract.template_positive_fraction
        and (_ci_bound(summary["joint_decoder"], 0) or -math.inf)
        >= contract.joint_accuracy_minimum
        and (_ci_bound(summary["proper_subset_decoder"], 1) or math.inf)
        <= contract.subset_accuracy_maximum
        and all(
            controls.get(condition, 1.0) <= 1.0 - contract.loss_fraction
            for condition in required
        )
        and summary.get("ablation_retention", 1.0)
        <= 1.0 - contract.loss_fraction
        and summary.get("same_rescue_retention", 0.0)
        >= contract.rescue_fraction
        and float(opposite.get("mean") or 0.0) < 0.0
        and (summary.get("translation_retention") or 0.0)
        >= contract.translation_retention
        and summary["survival_mean"] >= contract.survival_minimum
        and summary["statistical_scaffold_retention"]
        >= contract.statistical_retention
    )


def _profile_candidate_subset(
    candidates: Sequence[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    if limit >= len(candidates):
        return list(candidates)
    by_rank = {
        rank: [row for row in candidates if int(row["rank"]) == rank]
        for rank in (4, 8, 16)
    }
    selected: list[dict[str, Any]] = []
    cursor = 0
    while len(selected) < limit:
        changed = False
        for rank in (4, 8, 16):
            rows = by_rank[rank]
            if cursor < len(rows) and len(selected) < limit:
                selected.append(rows[cursor])
                changed = True
        if not changed:
            break
        cursor += 1
    return selected


def _template_pairs(
    templates: Sequence[dict[str, Any]], split: str
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    rows = [row for row in templates if row["split"] == split]
    if len(rows) % 2:
        raise ValueError("texture template split is not complement paired")
    result = []
    for index in range(0, len(rows), 2):
        left, right = rows[index], rows[index + 1]
        left_bits = np.asarray(left["bits"], dtype=np.uint8)
        right_bits = np.asarray(right["bits"], dtype=np.uint8)
        if not np.array_equal(1 - left_bits, right_bits):
            raise ValueError("texture template complement pairing changed")
        result.append((left, right))
    return result


def _make_items(
    pairs: Sequence[dict[str, Any]],
    candidates: Sequence[dict[str, Any]],
    template_pairs: Sequence[tuple[dict[str, Any], dict[str, Any]]],
    configuration: ReaderConfiguration,
    *,
    phase: str,
    replicates: int,
    generations: int,
    conditions: Sequence[str],
    extent: int = 16,
    scale_mode: str = "fixed",
    analysis_kind: str = "lineage",
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for pair_index, pair in enumerate(pairs):
        left, right = template_pairs[pair_index % len(template_pairs)]
        for candidate_index, candidate in enumerate(candidates):
            for future in (0, 1):
                checkpoint = (
                    f"{phase}-{analysis_kind}-e{extent:02d}-{scale_mode}-"
                    f"g{generations:02d}-p{pair_index:04d}-"
                    f"c{candidate_index:03d}-f{future}"
                )
                items.append(
                    {
                        "checkpoint": checkpoint,
                        "analysis_kind": analysis_kind,
                        "pair": pair,
                        "candidate_id": candidate["candidate_id"],
                        "configuration": asdict(configuration),
                        "replicates": replicates,
                        "generations": generations,
                        "conditions": tuple(conditions),
                        "environmental_template": left["bits"],
                        "template_pair_id": f"{left['template_id']}+{right['template_id']}",
                        "template_ids": (left["template_id"], right["template_id"]),
                        "assignment_swap": bool(future),
                        "extent": extent,
                        "scale_mode": scale_mode,
                    }
                )
    return items


def _frozen_stage6c_hashes(stage6c_root: Path) -> dict[str, str]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "COHORTS.json",
        "synergy/RESULTS.json",
        "plasticity/RESULTS.json",
        "COMPLETE",
    )
    missing = [stage6c_root / name for name in required if not (stage6c_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6C artifacts: {missing}")
    status = _load_json(stage6c_root / "STATUS.json")
    result = _load_json(stage6c_root / "RESULTS.json")
    cohorts = _load_json(stage6c_root / "COHORTS.json")
    if status.get("state") != "complete":
        raise ValueError("Stage-6C is not complete")
    if status.get("verdict") != "DURABLE_PARTITIONED_BUT_LEAKY_MEMORY":
        raise ValueError("Stage-6C verdict changed")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6C protected reserve is no longer untouched")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6C cohort reserve is no longer untouched")
    return {name: _sha256(stage6c_root / name) for name in required}


def _prepare_stage6cr(
    output: Path,
    profile_name: str,
    *,
    auto_final_audit: bool,
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
    AcquisitionRepairProfile,
    AcquisitionRepairContract,
    MotifContract,
    list[dict[str, Any]],
    list[dict[str, Any]],
    str,
]:
    stage6c_root = stage6c_root.resolve()
    stage6br_root = stage6br_root.resolve()
    stage6c_hashes = _frozen_stage6c_hashes(stage6c_root)
    frozen = load_frozen_stage5r(
        stage5r_root,
        stage5_root,
        stage4_root,
        stage3r_root,
        stage3_root,
        stage2_root,
        stage1_root,
    )
    profile = ACQUISITION_REPAIR_PROFILES[profile_name]
    contract = AcquisitionRepairContract()
    writer_contract = MotifContract()
    base = select_synergy_cohorts(
        frozen,
        SYNERGY_PROFILES["reference"],
        "reference",
        open_final=False,
    )
    exposed = base["plasticity"]
    stage6c_design = _load_json(stage6c_root / "DESIGN.json")
    expected = stage6c_design["development_pair_ids"]["plasticity"]
    observed = [str(pair["pair_id"]) for pair in exposed]
    if observed != expected:
        raise ValueError("Stage-6C exposed qualification cohort changed")
    cohorts = {
        "screen": exposed[: profile.screen_pairs],
        "qualification": exposed[24 : 24 + profile.qualification_pairs],
        "endurance": exposed[56 : 56 + profile.endurance_pairs],
        "final": [],
    }
    used = [
        str(pair["pair_id"])
        for name, rows in cohorts.items()
        if name != "final"
        for pair in rows
    ]
    if len(used) != len(set(used)):
        raise AssertionError("Stage-6C-R developmental cohorts overlap")
    if set(used) & set(frozen["later_ids"]):
        raise AssertionError("Stage-6C-R development touched the final reserve")
    candidates = build_acquisition_repair_candidates(stage6br_root)
    templates = acquisition_templates(SynergyContract())
    reserve_digest = hashlib.sha256(
        "\n".join(frozen["later_ids"]).encode()
    ).hexdigest()
    design_payload = {
        "experiment": "ca_motif_acquisition_repair_stage_6cr",
        "contract": contract.to_dict(),
        "writer_contract_digest": writer_contract.digest,
        "profile_name": profile_name,
        "profile": asdict(profile),
        "phases": PHASES,
        "automatic_phase_progression": True,
        "automatic_final_audit_user_authorized": bool(auto_final_audit),
        "automatic_final_audit_requires_all_developmental_gates": True,
        "frozen_stage6c_sha256": stage6c_hashes,
        "stage6c_design_digest": stage6c_design["design_digest"],
        "stage6c_failure_diagnosis": {
            "acquisition_mean": 0.005615234375,
            "active_rewrite_advantage": -0.0211181640625,
            "acquisition_sweeps": (41, 48),
            "writer_sweeps": (49, 64),
            "overlap_sweeps": 0,
            "selected_origin_displacement": 0.0,
            "repair_targets": ("eligibility timing", "spatial texture capacity"),
        },
        "candidate_factorial": {
            "rank": (4, 8, 16),
            "read_strength": (0.35, 0.60),
            "read_sweeps": (32, 48),
            "rho": (0.50, 0.75),
            "candidate_count": len(candidates),
            "promotion_limit": 2,
            "candidate_ids": [row["candidate_id"] for row in candidates],
        },
        "development_pair_ids": {
            key: [str(pair["pair_id"]) for pair in rows]
            for key, rows in cohorts.items()
            if key != "final"
        },
        "development_uses_only_stage6c_exposed_pairs": True,
        "paired_opposite_environment_assignments": True,
        "templates": templates,
        "final_audit_pair_count": len(frozen["later_ids"]),
        "final_audit_pair_ids_sha256": reserve_digest,
        "final_audit_trajectories_loaded": False,
        "implementation_sha256": {
            "motif_acquisition_repair.py": _sha256(Path(__file__)),
            "motif_synergistic_heredity.py": _sha256(
                Path(__file__).with_name("motif_synergistic_heredity.py")
            ),
        },
        "input_sha256": {
            "protocol": _sha256(PROTOCOL_PATH),
            **{
                f"stage5r_{key}": _sha256(path)
                for key, path in frozen["paths"].items()
            },
        },
        "cleanroom_exclusion": (
            "no Wagner or Fable implementation source is read, imported, "
            "hashed, or executed"
        ),
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
            raise ValueError("Stage-6C-R design changed; refusing a mixed resume")
    else:
        _atomic_json(design_path, design)
    prior_cohorts = (
        _load_json(output / "COHORTS.json")
        if (output / "COHORTS.json").exists()
        else {}
    )
    reserve_state = prior_cohorts.get("final_audit_trajectory_state", "untouched")
    _atomic_json(
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
    _atomic_json(
        output / "CANDIDATES.json",
        {
            "design_digest": design_digest,
            "candidate_count": len(candidates),
            "candidates": [_candidate_public(row) for row in candidates],
        },
    )
    _atomic_json(
        output / "ACQUISITION_TEMPLATES.json",
        {
            "design_digest": design_digest,
            "templates": templates,
            "environment_bits_passed_to_writer": False,
        },
    )
    _atomic_json(
        output / "CLEANROOM_PROVENANCE.json",
        {
            "experiment": "ca_motif_acquisition_repair_stage_6cr",
            "design_digest": design_digest,
            "excluded_code": ("Wagner implementation", "Fable implementation"),
            "excluded_code_read_import_hash_execute": True,
            "implementation_independent": True,
        },
    )
    return (
        frozen,
        cohorts,
        profile,
        contract,
        writer_contract,
        candidates,
        templates,
        design_digest,
    )


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
        "experiment": "ca_motif_acquisition_repair_stage_6cr",
        "design_digest": design_digest,
        "phase": phase,
        **result,
    }
    _atomic_json(root / "RESULTS.json", payload)
    _atomic_json(
        root / "STAGE_DECISION.json",
        {
            "experiment": payload["experiment"],
            "design_digest": design_digest,
            "phase": phase,
            "state": payload.get("state", "complete"),
            "stage_gate": bool(payload.get("stage_gate", False)),
            "decision": (
                "advance" if payload.get("stage_gate") and next_phase else (
                    "campaign_complete" if payload.get("stage_gate") else "phase_gate_failed"
                )
            ),
            "next_phase": next_phase if payload.get("stage_gate") else None,
            "final_audit_trajectory_state": payload.get(
                "final_audit_trajectory_state", "untouched"
            ),
        },
    )
    _atomic_text(root / "REPORT.md", report.rstrip() + "\n")
    _atomic_text(root / "LAY_SUMMARY.md", lay.rstrip() + "\n")
    _atomic_text(root / "COMPLETE", "complete\n")


def _run_forensics(
    output: Path,
    stage6c_root: Path,
    design_digest: str,
    status: Any,
) -> dict[str, Any]:
    status("running", "stage6c-frozen-diagnosis", completed=0, total=1)
    plasticity = _load_json(stage6c_root / "plasticity/RESULTS.json")
    selected = plasticity.get("qualification_candidate_ids", [])
    summary = plasticity.get("candidate_summaries", {}).get(STAGE6C_WINNER, {})
    acquisition = summary.get("acquisition", {})
    origin_displacements: list[float] = []
    checkpoint_root = stage6c_root / "plasticity-qualification/checkpoints"
    for path in sorted(checkpoint_root.glob("*.json")):
        row = _load_json(path).get("result", {})
        if row.get("candidate_id") != STAGE6C_WINNER:
            continue
        history = row.get("conditions", {}).get("intact", {}).get(
            "origin_history", {}
        )
        origin_displacements.extend(
            float(value["max_displacement"]) for value in history.values()
        )
        break
    stage_gate = bool(
        STAGE6C_WINNER in selected
        and not bool(summary.get("acquisition_gate", True))
        and acquisition.get("effect", {}).get("mean") is not None
        and max(origin_displacements, default=0.0) == 0.0
    )
    result = {
        "state": "complete",
        "stage_gate": stage_gate,
        "stage6c_selected_candidate_ids": selected,
        "stage6c_acquisition": acquisition,
        "acquisition_interval": (41, 48),
        "writer_observation_interval": (49, 64),
        "overlap_sweeps": 0,
        "selected_origin_max_displacement": max(origin_displacements, default=0.0),
        "origin_mismatch_hypothesis_rejected": True,
        "registered_repair_targets": (
            "simultaneous eligibility trace",
            "spatial texture representation",
        ),
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_result(
        output,
        "forensics",
        design_digest,
        result,
        "# Stage 6C-R forensics\n\nThe frozen Stage 6C failure is reproduced. "
        "The exposure and writer windows did not overlap; origin displacement "
        "was zero, so origin handoff is not retuned.",
        "# Lay summary\n\nThe old writer looked only after the experience had ended. "
        "The suspected location mismatch was not present.",
        next_phase="screen",
    )
    status("running", "stage6c-frozen-diagnosis", completed=1, total=1)
    return result


def _ranked_ids(summaries: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(
        summaries,
        key=lambda candidate_id: (
            -float(summaries[candidate_id]["read_acquisition"].get("mean") or 0.0),
            -float(
                summaries[candidate_id]["terminal_acquisition"].get("mean") or 0.0
            ),
            int(summaries[candidate_id]["candidate"]["rank"]),
            candidate_id,
        ),
    )


def _run_screen(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: AcquisitionRepairProfile,
    contract: AcquisitionRepairContract,
    writer_contract: MotifContract,
    candidates: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    scientific: bool,
    status: Any,
) -> dict[str, Any]:
    models = _profile_candidate_subset(candidates, profile.candidate_limit)
    items = _make_items(
        cohorts["screen"],
        models,
        _template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="screen",
        replicates=profile.screen_replicates,
        generations=8,
        conditions=SCREEN_CONDITIONS,
    )
    rows, complete = _run_json_checkpoints(
        output,
        "screen-trajectories-stage6cr",
        items,
        models,
        _texture_pair_task,
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
        str(candidate["candidate_id"]): _texture_summary(
            rows, candidate, 8, profile, contract, "screen"
        )
        for candidate in models
    }
    for value in summaries.values():
        value["screen_gate"] = _screen_gate(value, contract) if scientific else True
    ranked = _ranked_ids(summaries)
    eligible = [candidate_id for candidate_id in ranked if summaries[candidate_id]["screen_gate"]]
    selected = eligible[:2] if complete else []
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(selected),
        "scientific_gate_applied": scientific,
        "candidate_summaries": summaries,
        "eligible_candidate_ids": eligible,
        "selected_candidate_ids": selected,
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_result(
        output,
        "screen",
        design_digest,
        result,
        "# Stage 6C-R screen\n\nSelected texture candidates: "
        + (", ".join(selected) if selected else "none"),
        "# Lay summary\n\nThe screen asked whether a locally observed experience "
        "could cross one visible reset using all four hidden shares.",
        next_phase="qualify",
    )
    return result


def _models_by_id(
    candidates: Sequence[dict[str, Any]], candidate_ids: Sequence[str]
) -> list[dict[str, Any]]:
    by_id = {str(row["candidate_id"]): row for row in candidates}
    missing = [value for value in candidate_ids if value not in by_id]
    if missing:
        raise ValueError(f"selected texture models are missing: {missing}")
    return [by_id[value] for value in candidate_ids]


def _run_qualification(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: AcquisitionRepairProfile,
    contract: AcquisitionRepairContract,
    writer_contract: MotifContract,
    candidates: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    scientific: bool,
    status: Any,
) -> dict[str, Any]:
    screen = _load_json(output / "screen/RESULTS.json")
    selected_ids = screen.get("selected_candidate_ids", [])
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
            "# Stage 6C-R qualification\n\nSkipped because the screen gate failed.",
            "# Lay summary\n\nNo texture carrier was strong enough to retest.",
            next_phase="endurance",
        )
        return result
    models = _models_by_id(candidates, selected_ids)
    items = _make_items(
        cohorts["qualification"],
        models,
        _template_pairs(templates, "qualification"),
        frozen["stage4"]["configuration"],
        phase="qualify",
        replicates=profile.qualification_replicates,
        generations=16,
        conditions=QUALIFICATION_CONDITIONS,
    )
    rows, complete = _run_json_checkpoints(
        output,
        "qualification-trajectories-stage6cr",
        items,
        models,
        _texture_pair_task,
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
        str(candidate["candidate_id"]): _texture_summary(
            rows, candidate, 16, profile, contract, "qualification"
        )
        for candidate in models
    }
    for value in summaries.values():
        value["qualification_gate"] = (
            _qualification_gate(value, contract) if scientific else True
        )
    qualified = [
        candidate_id
        for candidate_id in _ranked_ids(summaries)
        if summaries[candidate_id]["qualification_gate"]
    ][:2]
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
        "# Stage 6C-R qualification\n\nQualified texture candidates: "
        + (", ".join(qualified) if qualified else "none"),
        "# Lay summary\n\nThe surviving designs were challenged with erasure, "
        "missing pieces, stopped renewal, and correct and opposite rescues.",
        next_phase="endurance",
    )
    return result


def _endurance_gate(
    generation32: dict[str, Any],
    generation64: dict[str, Any],
    scales: dict[str, dict[str, Any]],
    contract: AcquisitionRepairContract,
) -> bool:
    read32 = generation32["read_acquisition"]
    read64 = generation64["read_acquisition"]
    base = float(
        scales.get("extent16-fixed", {})
        .get("read_acquisition", {})
        .get("mean")
        or 0.0
    )
    scale_pass = True
    for extent in (16, 32, 64):
        values = [
            float(
                scales.get(f"extent{extent}-{mode}", {})
                .get("read_acquisition", {})
                .get("mean")
                or 0.0
            )
            for mode in ("fixed", "diameter")
        ]
        if max(values, default=0.0) < contract.translation_retention * base:
            scale_pass = False
    return bool(
        float(read32.get("mean") or 0.0)
        >= contract.endurance_generation32_minimum
        and (_ci_bound(read32, 0) or -math.inf) > 0.0
        and float(read64.get("mean") or 0.0)
        >= contract.endurance_generation64_minimum
        and (_ci_bound(read64, 0) or -math.inf) > 0.0
        and generation64["survival_mean"] >= contract.survival_minimum
        and generation64["control_retention"].get("no_rewrite", 1.0)
        <= 1.0 - contract.loss_fraction
        and generation64["control_retention"].get("proper_subset", 1.0)
        <= 1.0 - contract.loss_fraction
        and generation64["control_retention"].get("read_disabled", 1.0)
        <= 1.0 - contract.loss_fraction
        and scale_pass
    )


def _run_endurance(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: AcquisitionRepairProfile,
    contract: AcquisitionRepairContract,
    writer_contract: MotifContract,
    candidates: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    scientific: bool,
    status: Any,
) -> dict[str, Any]:
    qualification = _load_json(output / "qualify/RESULTS.json")
    qualified_ids = qualification.get("qualified_candidate_ids", [])
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
            "# Stage 6C-R endurance\n\nSkipped because qualification failed.",
            "# Lay summary\n\nNo acquired texture was strong enough for the long test.",
            next_phase="adjudicate",
        )
        return result
    models = _models_by_id(candidates, qualified_ids)
    template_pairs = _template_pairs(templates, "qualification")
    items = _make_items(
        cohorts["endurance"],
        models,
        template_pairs,
        frozen["stage4"]["configuration"],
        phase="endurance",
        replicates=profile.endurance_replicates,
        generations=64,
        conditions=ENDURANCE_CONDITIONS,
        analysis_kind="lineage",
    )
    for extent in (16, 32, 64):
        for scale_mode in ("fixed", "diameter"):
            items.extend(
                _make_items(
                    cohorts["endurance"],
                    models,
                    template_pairs,
                    frozen["stage4"]["configuration"],
                    phase="endurance",
                    replicates=profile.endurance_replicates,
                    generations=16,
                    conditions=ENDURANCE_CONDITIONS,
                    extent=extent,
                    scale_mode=scale_mode,
                    analysis_kind="scale",
                )
            )
    rows, complete = _run_json_checkpoints(
        output,
        "endurance-trajectories-stage6cr",
        items,
        models,
        _texture_pair_task,
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
        lineage_rows = [
            row
            for row in rows
            if row["analysis_kind"] == "lineage"
            and row["candidate_id"] == candidate_id
        ]
        generation32 = _texture_summary(
            lineage_rows, candidate, 32, profile, contract, "endurance-g32"
        )
        generation64 = _texture_summary(
            lineage_rows, candidate, 64, profile, contract, "endurance-g64"
        )
        scale_summaries: dict[str, Any] = {}
        for extent in (16, 32, 64):
            for scale_mode in ("fixed", "diameter"):
                scale_rows = [
                    row
                    for row in rows
                    if row["analysis_kind"] == "scale"
                    and row["candidate_id"] == candidate_id
                    and row["extent"] == extent
                    and row["scale_mode"] == scale_mode
                ]
                scale_summaries[f"extent{extent}-{scale_mode}"] = _texture_summary(
                    scale_rows,
                    candidate,
                    16,
                    profile,
                    contract,
                    f"endurance-scale-{extent}-{scale_mode}",
                )
        gate = (
            _endurance_gate(generation32, generation64, scale_summaries, contract)
            if scientific
            else True
        )
        summaries[candidate_id] = {
            "candidate": _candidate_public(candidate),
            "generation32": generation32,
            "generation64": generation64,
            "scale": scale_summaries,
            "endurance_gate": gate,
        }
    enduring = [
        candidate_id
        for candidate_id in qualified_ids
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
        "# Stage 6C-R endurance\n\nEnduring texture candidates: "
        + (", ".join(enduring) if enduring else "none"),
        "# Lay summary\n\nThe acquired memory was followed for 64 generations "
        "and challenged on three lattice sizes.",
        next_phase="adjudicate",
    )
    return result


def _open_final_pairs(frozen: dict[str, Any]) -> list[dict[str, Any]]:
    opened = select_synergy_cohorts(
        frozen,
        SYNERGY_PROFILES["reference"],
        "reference",
        open_final=True,
    )["final"]
    if len(opened) != 62:
        raise ValueError("Stage-6C-R final reserve is incomplete")
    return opened


def _update_reserve_state(
    output: Path, state: str, *, final_digest: str | None = None
) -> None:
    path = output / "COHORTS.json"
    payload = _load_json(path)
    payload["final_audit_trajectory_state"] = state
    payload["final_audit_trajectories_not_loaded"] = state == "untouched"
    if final_digest is not None:
        payload["final_audit_digest"] = final_digest
    _atomic_json(path, payload)


def _run_adjudication(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: AcquisitionRepairProfile,
    contract: AcquisitionRepairContract,
    writer_contract: MotifContract,
    candidates: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    scientific: bool,
    auto_final_audit: bool,
    status: Any,
) -> dict[str, Any]:
    endurance = _load_json(output / "endurance/RESULTS.json")
    enduring_ids = endurance.get("enduring_candidate_ids", [])
    if not enduring_ids:
        result = {
            "state": "complete",
            "stage_gate": False,
            "finalist_candidate_ids": [],
            "confirmed_candidate_ids": [],
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
            "# Stage 6C-R adjudication\n\nThe final reserve remained sealed.",
            "# Lay summary\n\nThe protected final cases were not needed because an "
            "earlier gate failed.",
            next_phase=None,
        )
        return result
    if scientific and not auto_final_audit:
        raise ValueError("reference Stage-6C-R final audit lacks authorization")
    models = _models_by_id(candidates, enduring_ids)
    if scientific:
        final_pairs = _open_final_pairs(frozen)
        reserve_state = "opened"
        _update_reserve_state(output, reserve_state)
    else:
        final_pairs = cohorts["qualification"][: profile.final_pairs]
        reserve_state = "smoke-exposed-only"
    pair_digest = hashlib.sha256(
        "\n".join(str(pair["pair_id"]) for pair in final_pairs).encode()
    ).hexdigest()
    _atomic_json(
        output / "FINAL_AUDIT_DESIGN.json",
        {
            "design_digest": design_digest,
            "candidate_ids": enduring_ids,
            "pair_count": len(final_pairs),
            "pair_ids_sha256": pair_digest,
            "conditions": QUALIFICATION_CONDITIONS,
            "templates": [
                (left["template_id"], right["template_id"])
                for left, right in _template_pairs(templates, "audit")
            ],
            "retuning": False,
        },
    )
    items = _make_items(
        final_pairs,
        models,
        _template_pairs(templates, "audit"),
        frozen["stage4"]["configuration"],
        phase="final-audit",
        replicates=profile.final_replicates,
        generations=16,
        conditions=QUALIFICATION_CONDITIONS,
        analysis_kind="final",
    )
    rows, complete = _run_json_checkpoints(
        output,
        "final-audit-trajectories-stage6cr",
        items,
        models,
        _texture_pair_task,
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
        str(candidate["candidate_id"]): _texture_summary(
            rows, candidate, 16, profile, contract, "final-audit"
        )
        for candidate in models
    }
    for value in summaries.values():
        value["final_gate"] = (
            _qualification_gate(value, contract) if scientific else True
        )
    confirmed = [
        candidate_id
        for candidate_id in enduring_ids
        if summaries.get(candidate_id, {}).get("final_gate")
    ]
    if not complete:
        confirmed = []
    final_digest = hashlib.sha256(
        json.dumps(summaries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if scientific:
        _update_reserve_state(
            output, "complete" if complete else "partial", final_digest=final_digest
        )
        reserve_state = "complete" if complete else "partial"
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(confirmed),
        "scientific_gate_applied": scientific,
        "finalist_candidate_ids": enduring_ids,
        "confirmed_candidate_ids": confirmed,
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
        "# Stage 6C-R adjudication\n\nConfirmed candidates: "
        + (", ".join(confirmed) if confirmed else "none"),
        "# Lay summary\n\nThe untouched cases were opened only after every earlier "
        "test passed; no settings were changed afterward.",
        next_phase=None,
    )
    return result


def _campaign_clock(
    output: Path,
    design_digest: str,
    max_hours: float,
    *,
    resume: bool,
) -> dict[str, Any]:
    path = output / "CAMPAIGN.json"
    if path.exists():
        payload = _load_json(path)
        if not resume:
            raise ValueError("Stage-6C-R output exists; use --resume")
        if payload.get("design_digest") != design_digest:
            raise ValueError("Stage-6C-R campaign design mismatch")
        if not math.isclose(float(payload["max_hours"]), max_hours):
            raise ValueError("Stage-6C-R max-hours changed during resume")
        return payload
    started = time.time()
    fraction = (
        AcquisitionRepairContract().exploration_stop_hours
        / AcquisitionRepairContract().max_hours
    )
    payload = {
        "experiment": "ca_motif_acquisition_repair_stage_6cr",
        "design_digest": design_digest,
        "started_unix": started,
        "max_hours": max_hours,
        "hard_deadline_unix": started + max_hours * 3600.0,
        "exploration_deadline_unix": started + max_hours * fraction * 3600.0,
        "adjudication_reserve_hours": max_hours * (1.0 - fraction),
        "deadline_persists_across_resume": True,
    }
    _atomic_json(path, payload)
    return payload


def _status_writer(
    output: Path,
    profile_name: str,
    campaign: dict[str, Any],
    active_phase: list[str],
) -> Any:
    def write(state: str, current: str, **extra: Any) -> None:
        phase = active_phase[0]
        cohorts = (
            _load_json(output / "COHORTS.json")
            if (output / "COHORTS.json").exists()
            else {}
        )
        payload = {
            "state": state,
            "stage": "ca_motif_acquisition_repair_stage_6cr",
            "profile": profile_name,
            "phase": phase,
            "current": current,
            "pid": os.getpid(),
            "workers_hard_max": AcquisitionRepairContract().max_workers,
            "started_unix": campaign["started_unix"],
            "updated_unix": time.time(),
            "elapsed_seconds": time.time() - float(campaign["started_unix"]),
            "deadline_remaining_seconds": max(
                0.0, float(campaign["hard_deadline_unix"]) - time.time()
            ),
            "exploration_deadline_unix": campaign["exploration_deadline_unix"],
            "hard_deadline_unix": campaign["hard_deadline_unix"],
            "final_audit_trajectory_state": cohorts.get(
                "final_audit_trajectory_state", "untouched"
            ),
            **extra,
        }
        _atomic_json(output / "STATUS.json", payload)
        if phase in PHASES:
            phase_root = output / phase
            phase_root.mkdir(parents=True, exist_ok=True)
            _atomic_json(phase_root / "STATUS.json", payload)
        progress = ""
        if "completed" in extra and "total" in extra:
            progress = f" {extra['completed']}/{extra['total']}"
        print(f"[{state}] stage6cr-{phase}:{current}{progress}", flush=True)

    return write


def _require_phase(output: Path, phase: str, design_digest: str) -> None:
    path = output / phase / "RESULTS.json"
    if not path.exists() or not (output / phase / "COMPLETE").exists():
        raise ValueError(f"Stage-6C-R predecessor is incomplete: {phase}")
    if _load_json(path).get("design_digest") != design_digest:
        raise ValueError(f"Stage-6C-R predecessor design mismatch: {phase}")


def _campaign_verdict(output: Path, scientific: bool) -> str:
    if not scientific:
        return "SMOKE_PATH_VALIDATED"
    screen = _load_json(output / "screen/RESULTS.json")
    qualification = _load_json(output / "qualify/RESULTS.json")
    endurance = _load_json(output / "endurance/RESULTS.json")
    adjudication = _load_json(output / "adjudicate/RESULTS.json")
    if adjudication.get("confirmed_candidate_ids"):
        return "CONFIRMED_ACQUIRED_TEXTURE_PLASTIC_HEREDITY"
    if not screen.get("stage_gate"):
        return "NO_ACQUIRED_TEXTURE_WRITE"
    if not qualification.get("stage_gate"):
        return "SHORT_LIVED_ACQUIRED_TEXTURE_ONLY"
    if not endurance.get("stage_gate"):
        return "ACQUIRED_TEXTURE_NOT_DURABLE_OR_SCALABLE"
    return "DEVELOPMENT_ONLY_ACQUIRED_TEXTURE_HEREDITY"


def _write_campaign_outputs(
    output: Path,
    design_digest: str,
    profile_name: str,
    scientific: bool,
) -> dict[str, Any]:
    verdict = _campaign_verdict(output, scientific)
    phase_results = {
        phase: _load_json(output / phase / "RESULTS.json") for phase in PHASES
    }
    cohorts = _load_json(output / "COHORTS.json")
    result = {
        "experiment": "ca_motif_acquisition_repair_stage_6cr",
        "design_digest": design_digest,
        "state": "complete",
        "profile_name": profile_name,
        "scientific_gate_applied": scientific,
        "verdict": verdict,
        "stage_gate": bool(
            phase_results["adjudicate"].get("confirmed_candidate_ids")
        ),
        "selected_candidate_ids": phase_results["screen"].get(
            "selected_candidate_ids", []
        ),
        "qualified_candidate_ids": phase_results["qualify"].get(
            "qualified_candidate_ids", []
        ),
        "enduring_candidate_ids": phase_results["endurance"].get(
            "enduring_candidate_ids", []
        ),
        "confirmed_candidate_ids": phase_results["adjudicate"].get(
            "confirmed_candidate_ids", []
        ),
        "final_audit_opened": bool(
            phase_results["adjudicate"].get("final_audit_opened", False)
        ),
        "final_audit_trajectory_state": cohorts[
            "final_audit_trajectory_state"
        ],
        "phase_gates": {
            phase: bool(value.get("stage_gate"))
            for phase, value in phase_results.items()
        },
    }
    _atomic_json(output / "RESULTS.json", result)
    _atomic_json(
        output / "STAGE_DECISION.json",
        {
            "experiment": result["experiment"],
            "design_digest": design_digest,
            "state": "complete",
            "decision": "campaign_complete",
            "stage_gate": result["stage_gate"],
            "verdict": verdict,
            "next_phase": None,
            "final_audit_trajectory_state": result[
                "final_audit_trajectory_state"
            ],
        },
    )
    _atomic_text(
        output / "REPORT.md",
        "# Stage 6C-R acquisition repair\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"Selected: {result['selected_candidate_ids']}\n\n"
        f"Qualified: {result['qualified_candidate_ids']}\n\n"
        f"Enduring: {result['enduring_candidate_ids']}\n\n"
        f"Confirmed: {result['confirmed_candidate_ids']}\n\n"
        "The final reserve was "
        + ("opened under the frozen gate.\n" if result["final_audit_opened"] else "not opened.\n"),
    )
    lay = (
        "The locally observed texture crossed the visible reset and survived "
        "every causal and held-out test."
        if result["stage_gate"]
        else "No candidate completed the full acquisition, renewal, endurance, "
        "and held-out ladder."
    )
    _atomic_text(output / "LAY_SUMMARY.md", "# Lay summary\n\n" + lay + "\n")
    _atomic_json(
        output / "MANIFEST.json",
        {
            "experiment": result["experiment"],
            "design_digest": design_digest,
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "result_sha256": _sha256(output / "RESULTS.json"),
            "protocol_sha256": _sha256(PROTOCOL_PATH),
            "implementation_sha256": _sha256(Path(__file__)),
        },
    )
    _atomic_text(output / "COMPLETE", "complete\n")
    return result


def run_motif_acquisition_repair(
    output: Path,
    *,
    phase: str = "all",
    stage6c_root: Path = DEFAULT_STAGE6C_ROOT,
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
    """Run the frozen Stage-6C-R acquisition repair campaign."""

    require_pinned_numpy()
    if phase not in (*PHASES, "all"):
        raise ValueError(f"unknown Stage-6C-R phase {phase!r}")
    if profile_name not in PUBLIC_PROFILES:
        raise ValueError(f"unknown Stage-6C-R profile {profile_name!r}")
    if workers < 1 or workers > AcquisitionRepairContract().max_workers:
        raise ValueError("Stage-6C-R workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > AcquisitionRepairContract().max_hours:
        raise ValueError("Stage-6C-R max-hours must be in (0, 8]")
    if profile_name == "reference" and not auto_final_audit:
        raise ValueError(
            "reference Stage-6C-R requires registered automatic final-audit authorization"
        )
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    _atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
    active_phase = ["prepare"]
    campaign: dict[str, Any] | None = None
    status: Any = None
    try:
        (
            frozen,
            cohorts,
            profile,
            contract,
            writer_contract,
            candidates,
            templates,
            design_digest,
        ) = _prepare_stage6cr(
            output,
            profile_name,
            auto_final_audit=auto_final_audit,
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
        campaign = _campaign_clock(
            output, design_digest, max_hours, resume=resume
        )
        status = _status_writer(output, profile_name, campaign, active_phase)
        status("running", "frozen-design-verified")
        selected_phases = PHASES if phase == "all" else (phase,)
        if phase != "all":
            for predecessor in PHASES[: PHASES.index(phase)]:
                _require_phase(output, predecessor, design_digest)
        scientific = profile_name == "reference"
        runners = {
            "forensics": lambda: _run_forensics(
                output, stage6c_root.resolve(), design_digest, status
            ),
            "screen": lambda: _run_screen(
                output,
                frozen,
                cohorts,
                profile,
                contract,
                writer_contract,
                candidates,
                templates,
                design_digest,
                workers=workers,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                scientific=scientific,
                status=status,
            ),
            "qualify": lambda: _run_qualification(
                output,
                frozen,
                cohorts,
                profile,
                contract,
                writer_contract,
                candidates,
                templates,
                design_digest,
                workers=workers,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                scientific=scientific,
                status=status,
            ),
            "endurance": lambda: _run_endurance(
                output,
                frozen,
                cohorts,
                profile,
                contract,
                writer_contract,
                candidates,
                templates,
                design_digest,
                workers=workers,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                scientific=scientific,
                status=status,
            ),
            "adjudicate": lambda: _run_adjudication(
                output,
                frozen,
                cohorts,
                profile,
                contract,
                writer_contract,
                candidates,
                templates,
                design_digest,
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
            result = _write_campaign_outputs(
                output, design_digest, profile_name, scientific
            )
            status(
                "complete",
                "campaign-complete",
                verdict=result["verdict"],
            )
        return result
    except BaseException as error:
        if campaign is None:
            campaign = {
                "started_unix": time.time(),
                "hard_deadline_unix": time.time(),
                "exploration_deadline_unix": time.time(),
            }
        if status is None:
            status = _status_writer(output, profile_name, campaign, active_phase)
        status("failed", "campaign-failed", error=repr(error))
        _atomic_json(
            output / "ERROR.json",
            {
                "error": repr(error),
                "phase": active_phase[0],
                "updated_unix": time.time(),
            },
        )
        raise


__all__ = (
    "ACQUISITION_REPAIR_PROFILES",
    "AcquisitionRepairContract",
    "DEFAULT_STAGE6C_ROOT",
    "PHASES",
    "apply_texture_reader",
    "build_acquisition_repair_candidates",
    "observe_texture",
    "run_motif_acquisition_repair",
    "simulate_acquired_texture_lineage",
    "texture_decode",
    "texture_encode",
    "texture_seed_origins",
    "walsh_texture_basis",
)
