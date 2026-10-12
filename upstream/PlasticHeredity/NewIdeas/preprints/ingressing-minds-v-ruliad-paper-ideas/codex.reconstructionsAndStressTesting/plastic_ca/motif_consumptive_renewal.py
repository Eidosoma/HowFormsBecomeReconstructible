"""Stage-6D consumptive texture renewal in cellular automata.

Stage 6C-R is immutable input.  This module tests a stricter renewal cycle in
which the incoming texture carrier is destroyed before a label-blind writer
observes the daughter's carrier-free visible form and creates fresh shares.
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

from . import motif_acquisition_repair as ar


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_CONSUMPTIVE_RENEWAL_PROTOCOL.md"
DEFAULT_STAGE6CR_ROOT = ROOT / "results/ca-motif-acquisition-repair-stage-6cr"
PHASES = ("forensics", "screen", "qualify", "endurance", "adjudicate")
ANCHOR_SOURCE_ID = "texture-r16-s60-d48-rho50"
ANCHOR_ID = "anchor-r16-s60-d48-rho50"

SCREEN_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
    "acquisition_write_disabled",
    "no_erasure",
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
    "phenotype_scrub",
    "phenotype_same_rescue",
    "phenotype_opposite_rescue",
    "writer_observation_shuffle",
)
ENDURANCE_CONDITIONS = (
    "intact",
    "sham",
    "no_rewrite",
    "proper_subset",
    "read_disabled",
    "acquisition_write_disabled",
    "phenotype_scrub",
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
)
ALL_CONDITIONS = tuple(
    dict.fromkeys(
        (*SCREEN_CONDITIONS, *QUALIFICATION_CONDITIONS, *ENDURANCE_CONDITIONS)
    )
)


@dataclass(frozen=True)
class ConsumptiveRenewalContract:
    implementation_version: str = "ca-motif-consumptive-renewal-v1"
    namespace: str = "plastic-ca-motif-consumptive-renewal-v1"
    rule: int = 31649
    generation_sweeps: int = 64
    statistical_read_sweeps: int = 32
    observe_start: int = 57
    acquisition_generation: int = 4
    acquisition_start: int = 41
    acquisition_end: int = 48
    texture_trace_sweeps: int = 8
    intervention_generation: int = 6
    process_noise: float = 0.002
    bit_corruption: float = 0.01
    texture_seed_count: int = 4
    texture_seed_radius: int = 3
    texture_hops: int = 3
    texture_bits: int = 4
    strict_alpha: float = 0.025
    screen_read_minimum: float = 0.25
    screen_post_washout_minimum: float = 0.10
    qualification_read_minimum: float = 0.20
    qualification_post_washout_minimum: float = 0.08
    qualification_terminal_minimum: float = 0.05
    endurance_generation32_minimum: float = 0.10
    endurance_generation64_minimum: float = 0.05
    endurance_post_washout_minimum: float = 0.0
    active_rewrite_minimum: float = 0.15
    joint_accuracy_minimum: float = 0.75
    subset_accuracy_maximum: float = 0.60
    loss_fraction: float = 0.70
    endurance_no_rewrite_maximum: float = 0.10
    rescue_fraction: float = 0.70
    generation16_retention: float = 0.70
    template_positive_fraction: float = 1.0
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
            "renewal_order": (
                "read",
                "destroy incoming carrier",
                "carrier-free washout",
                "observe visible daughter",
                "write fresh carrier",
            ),
            "writer_observes_environment_bits": False,
            "writer_observes_incoming_payload": False,
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
class ConsumptiveRenewalProfile:
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


CONSUMPTIVE_RENEWAL_PROFILES: dict[str, ConsumptiveRenewalProfile] = {
    "smoke": ConsumptiveRenewalProfile(2, 2, 2, 2, 2, 2, 2, 2, 100, 4),
    "pilot": ConsumptiveRenewalProfile(8, 4, 16, 4, 8, 4, 8, 4, 1_000, 12),
    "reference": ConsumptiveRenewalProfile(
        24, 4, 32, 8, 8, 4, 62, 4, 10_000, 24
    ),
}
PUBLIC_PROFILES = tuple(CONSUMPTIVE_RENEWAL_PROFILES)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_consumptive_candidates(
    stage6br_root: Path = ar.DEFAULT_STAGE6BR_ROOT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return the frozen 24 strict candidates and one calibration anchor."""

    old = ar.build_acquisition_repair_candidates(stage6br_root)
    by_id = {str(row["candidate_id"]): row for row in old}
    if ANCHOR_SOURCE_ID not in by_id:
        raise ValueError("Stage-6C-R calibration anchor is missing")
    source = by_id[ANCHOR_SOURCE_ID]
    scaffold = source["statistical_candidate"]
    rows: list[dict[str, Any]] = []
    for strength in (0.60, 0.75, 0.90):
        for read_sweeps in (40, 48):
            for washout_sweeps in (4, 8):
                for write_gain in (1.0, 1.5):
                    candidate_id = (
                        f"consume-r16-s{int(strength * 100):02d}-"
                        f"d{read_sweeps:02d}-w{washout_sweeps:02d}-"
                        f"g{int(write_gain * 100):03d}"
                    )
                    rows.append(
                        {
                            "candidate_id": candidate_id,
                            "rank": 16,
                            "bits": 4,
                            "payload_bits": 64,
                            "codec_model": ar.texture_codec(16),
                            "read_strength": strength,
                            "read_sweeps": read_sweeps,
                            "washout_sweeps": washout_sweeps,
                            "write_gain": write_gain,
                            "rho": 0.0,
                            "renewal_mode": "consumptive",
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
        raise AssertionError("Stage-6D candidate grid must contain 24 cells")
    anchor = {
        **source,
        "candidate_id": ANCHOR_ID,
        "calibration_source_id": ANCHOR_SOURCE_ID,
        "washout_sweeps": 0,
        "write_gain": 1.0,
        "renewal_mode": "legacy_anchor",
        "promotable": False,
    }
    return rows, anchor


def _candidate_public(candidate: dict[str, Any]) -> dict[str, Any]:
    return ar._candidate_public(candidate)


def _profile_candidates(
    candidates: Sequence[dict[str, Any]],
    anchor: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    if limit >= len(candidates):
        selected = list(candidates)
    elif limit <= 1:
        selected = [candidates[-1]]
    else:
        indexes = [index * (len(candidates) - 1) // (limit - 1) for index in range(limit)]
        selected = [candidates[index] for index in indexes]
    return [*selected, anchor]


def _destroy_carrier(
    shares: np.ndarray, active: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Physically remove both share values and their occupancy bits."""

    return np.zeros_like(shares, dtype=np.uint8), np.zeros_like(active, dtype=np.bool_)


def _scrub_patch(
    state: np.ndarray,
    centers: np.ndarray,
    pair_id: str,
    generation: int,
    replicates: int,
    contract: ConsumptiveRenewalContract,
) -> None:
    rng = np.random.default_rng(
        ar._hash_seed(contract.namespace, pair_id, "phenotype-scrub", generation)
    )
    half = rng.random((replicates, 4, 4)) < 0.5
    patches = np.concatenate((half, half), axis=0)
    ar._apply_environment(state, centers, patches)


def _phenotype_intervention(
    state: np.ndarray,
    centers: np.ndarray,
    environment: np.ndarray,
    condition: str,
    pair_id: str,
    generation: int,
    replicates: int,
    contract: ConsumptiveRenewalContract,
) -> bool:
    if generation != contract.intervention_generation or condition not in (
        "phenotype_scrub",
        "phenotype_same_rescue",
        "phenotype_opposite_rescue",
    ):
        return False
    _scrub_patch(state, centers, pair_id, generation, replicates, contract)
    if condition == "phenotype_same_rescue":
        ar._apply_environment(state, centers, environment)
    elif condition == "phenotype_opposite_rescue":
        ar._apply_environment(state, centers, ~environment)
    return True


def simulate_consumptive_lineage(
    pair: dict[str, Any],
    configuration: ar.ReaderConfiguration,
    candidate: dict[str, Any],
    condition: str,
    replicates: int,
    generations: int,
    reference: dict[int, dict[str, np.ndarray]],
    writer_contract: ar.MotifContract,
    contract: ConsumptiveRenewalContract,
    environmental_template: np.ndarray,
    *,
    assignment_swap: bool = False,
    extent: int = 16,
    scale_mode: str = "fixed",
    source_exits: Sequence[tuple[np.ndarray, np.ndarray]] | None = None,
    retain_exits: bool = False,
) -> tuple[dict[str, Any], list[tuple[np.ndarray, np.ndarray]]]:
    """Run one lineage with a carrier-free interval before every renewal write."""

    if condition not in ALL_CONDITIONS:
        raise ValueError(f"unknown Stage-6D condition {condition!r}")
    if extent not in (16, 32, 64):
        raise ValueError("Stage-6D extents are 16, 32, and 64")
    if scale_mode not in ("fixed", "diameter"):
        raise ValueError("scale mode must be fixed or diameter")
    pair_id = str(pair["pair_id"])
    reset_a = ar._resize_board(
        ar._state_from_hex("life", pair["donor_a"]["initial_state_hex"]), extent
    )
    reset_b = ar._resize_board(
        ar._state_from_hex("life", pair["donor_b"]["initial_state_hex"]), extent
    )
    if not np.array_equal(reset_a, reset_b):
        raise AssertionError(f"visible reset mismatch in pair {pair_id}")
    reset = np.repeat(reset_a[None], 2 * replicates, axis=0)
    statistical = candidate["statistical_candidate"]
    reference_probability = reference[configuration.write_window]["motif_probability"]
    founder, founder_terminal = ar._founder_bounded_payload(
        pair,
        statistical,
        reference_probability,
        replace(writer_contract, rule=contract.rule),
        replicates,
        extent,
        contract.rule,
    )
    statistical_energy = ar.decode_payload(founder, statistical["codec_model"])
    zero_payload = np.zeros((2 * replicates, int(candidate["rank"])), dtype=np.float32)
    shares = np.zeros(
        (2 * replicates, int(candidate["seed_count"]), int(candidate["rank"])),
        dtype=np.uint8,
    )
    active = np.zeros_like(shares, dtype=np.bool_)
    alive = np.ones(2 * replicates, dtype=np.bool_)
    environment = ar._environment_samples(
        np.asarray(environmental_template, dtype=np.bool_),
        replicates,
        assignment_swap,
    )
    scale = extent / 16.0 if scale_mode == "diameter" else 1.0
    radius = max(1, int(round(float(candidate["seed_radius"]) * scale)))
    hops = max(1, int(round(float(candidate["germination_hops"]) * scale)))
    read_sweeps = int(candidate["read_sweeps"])
    strict = str(candidate["renewal_mode"]) == "consumptive"
    washout_sweeps = int(candidate["washout_sweeps"]) if strict else 0
    checkpoints = {
        value
        for value in (1, 2, 4, 5, 6, 7, 8, 16, 32, 64)
        if value <= generations
    }
    outcomes: dict[str, Any] = {}
    texture_history: dict[str, Any] = {}
    carrier_history: dict[str, Any] = {}
    writer_history: dict[str, Any] = {}
    exits: list[tuple[np.ndarray, np.ndarray]] = []
    uncorrectable_values: list[float] = []
    renewal_absence: list[bool] = []

    for generation in range(1, generations + 1):
        translated = condition == "translated_patch"
        centers = ar.repair_origins(
            pair_id,
            generation,
            replicates,
            extent,
            "co-located",
            translated=translated,
        )
        shares, active = ar._entry_texture_intervention(
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
        shares, uncorrectable = ar._copy_texture_codes(
            shares, pair_id, generation, replicates, contract
        )
        uncorrectable_values.append(uncorrectable)
        entry_payload, entry_valid = ar._joint_payload(shares, active, candidate)
        effective_hops = 0 if condition == "transport_disabled" else hops
        reader_payload, reader_valid, wave_trace = ar._texture_field_at_centers(
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
        washout_state: np.ndarray | None = None
        writer_state: np.ndarray | None = None
        intervention_applied = False
        erased_before_writer = False
        if generation == contract.acquisition_generation:
            writer_start = contract.acquisition_start
            writer_end = contract.acquisition_end
            washout_end = writer_start - 1
        elif strict:
            washout_end = read_sweeps + washout_sweeps
            writer_start = washout_end + 1
            writer_end = writer_start + contract.texture_trace_sweeps - 1
        else:
            writer_end = read_sweeps
            writer_start = read_sweeps - contract.texture_trace_sweeps + 1
            washout_end = read_sweeps
        if writer_end > contract.generation_sweeps:
            raise AssertionError("Stage-6D writer window exceeds the generation")

        for sweep in range(1, contract.generation_sweeps + 1):
            predicted = ar._step(state, contract.rule)
            if (
                condition != "statistical_disabled"
                and sweep <= contract.statistical_read_sweeps
            ):
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
            predicted[~alive] = False
            if (
                condition != "sham"
                and generation == contract.acquisition_generation
                and contract.acquisition_start <= sweep <= contract.acquisition_end
            ):
                ar._apply_environment(predicted, centers, environment)
            state = predicted
            if sweep == read_sweeps:
                read_state = state.copy()
                if strict and generation != contract.acquisition_generation:
                    if condition != "no_erasure":
                        shares, active = _destroy_carrier(shares, active)
                        erased_before_writer = True
            if sweep == washout_end:
                washout_state = state.copy()
                intervention_applied = _phenotype_intervention(
                    state,
                    centers,
                    environment,
                    condition,
                    pair_id,
                    generation,
                    replicates,
                    contract,
                )
            if writer_start <= sweep <= writer_end:
                observed = ar.observe_texture(state, centers)
                if (
                    condition == "writer_observation_shuffle"
                    and generation == contract.intervention_generation
                ):
                    observed = ar._swap_histories(observed, replicates)
                trace_sum += observed
                trace_count += 1
            if sweep == writer_end:
                writer_state = state.copy()
            if sweep >= contract.observe_start:
                recent.append(ar.live_2x2_counts_batch(state))

        if read_state is None:
            raise AssertionError("Stage-6D read checkpoint was not captured")
        if washout_state is None:
            washout_state = read_state.copy()
        if writer_state is None or trace_count != contract.texture_trace_sweeps:
            raise AssertionError("Stage-6D writer trace changed")
        alive &= state.any(axis=(1, 2))
        raw_proposal = ar.texture_encode(
            (trace_sum / float(trace_count)).astype(np.float32),
            int(candidate["rank"]),
        )
        proposal, clipping = ar._quantize(
            np.float32(candidate["write_gain"]) * raw_proposal,
            candidate["codec_model"],
        )
        writer_connected = bool(np.all(reader_valid | ~alive))
        carrier_absent_during_writer = bool(
            not np.any(active) and not np.any(shares)
        )
        if strict and generation != contract.acquisition_generation:
            renewal_absence.append(carrier_absent_during_writer)
        if generation < contract.acquisition_generation:
            next_payload = zero_payload.copy()
            write_fresh = False
        elif (
            generation == contract.acquisition_generation
            and condition == "acquisition_write_disabled"
        ):
            next_payload = zero_payload.copy()
            write_fresh = False
        elif generation == contract.acquisition_generation:
            next_payload = proposal
            write_fresh = True
        elif condition == "no_rewrite":
            next_payload = zero_payload.copy()
            write_fresh = False
        elif not writer_connected:
            next_payload = zero_payload.copy()
            write_fresh = False
        elif strict:
            next_payload = proposal
            write_fresh = True
        else:
            next_payload, clipping = ar.latch_update(
                entry_payload,
                proposal,
                float(candidate["rho"]),
                candidate["codec_model"],
            )
            write_fresh = True
        if write_fresh:
            shares, active = ar._encode_carrier(
                next_payload,
                candidate,
                contract,
                pair_id,
                generation,
                purpose="consumptive-texture-write",
            )
            active[~alive] = False
        else:
            shares, active = _destroy_carrier(shares, active)

        if generation in checkpoints:
            outcome, _ = ar._score_state(
                state,
                recent,
                pair,
                founder_terminal,
                replicates,
                writer_contract,
            )
            outcomes[str(generation)] = outcome

            def match_snapshot(snapshot: np.ndarray) -> tuple[float, float, float]:
                values = ar._texture_match(snapshot, centers, environment)
                return (
                    float(np.mean(values)),
                    float(np.mean(values[:replicates])),
                    float(np.mean(values[replicates:])),
                )

            read_match = match_snapshot(read_state)
            washout_match = match_snapshot(washout_state)
            writer_match = match_snapshot(writer_state)
            terminal_match = match_snapshot(state)
            texture_history[str(generation)] = {
                "read_match_mean": read_match[0],
                "read_direction_a_mean": read_match[1],
                "read_direction_b_mean": read_match[2],
                "post_washout_match_mean": washout_match[0],
                "post_washout_direction_a_mean": washout_match[1],
                "post_washout_direction_b_mean": washout_match[2],
                "writer_match_mean": writer_match[0],
                "writer_direction_a_mean": writer_match[1],
                "writer_direction_b_mean": writer_match[2],
                "terminal_match_mean": terminal_match[0],
                "terminal_direction_a_mean": terminal_match[1],
                "terminal_direction_b_mean": terminal_match[2],
            }
            diagnostic = ar._carrier_diagnostics(
                shares,
                active,
                candidate,
                replicates,
                ar._hash_seed(
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
                "read_end": read_sweeps,
                "washout_end": washout_end,
                "writer_start": writer_start,
                "writer_end": writer_end,
                "trace_count": trace_count,
                "proposal_mean_abs": float(np.mean(np.abs(proposal))),
                "quantizer_clipping": float(clipping),
                "writer_connected": writer_connected,
                "incoming_payload_exposed_to_writer": False,
                "carrier_erased_before_writer": erased_before_writer,
                "carrier_absent_during_writer": carrier_absent_during_writer,
                "phenotype_intervention_applied": intervention_applied,
                "fresh_carrier_written": write_fresh,
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
        "incoming_payload_not_passed_to_writer": True,
        "assignment_swap": assignment_swap,
        "renewal_mode": candidate["renewal_mode"],
        "texture_rank": int(candidate["rank"]),
        "texture_seed_radius": radius,
        "texture_hops": hops,
        "texture_payload_bits": int(candidate["payload_bits"]),
        "physical_encoded_bits": int(candidate["rank"]) * 4 * 8
        + int(candidate["rank"]) * 4,
        "statistical_scaffold_id": statistical["candidate_id"],
        "statistical_scaffold_frozen": True,
        "all_renewal_writer_windows_carrier_absent": bool(
            renewal_absence and all(renewal_absence)
        ) if strict and generations > contract.acquisition_generation else strict,
        "renewal_writer_window_count": len(renewal_absence),
        "outcomes": outcomes,
        "texture_history": texture_history,
        "carrier_history": carrier_history,
        "writer_history": writer_history,
        "survival_fraction": float(np.mean(alive)),
        "copy_uncorrectable_fraction": float(np.mean(uncorrectable_values)),
    }
    return result, exits


def _consumptive_pair_task(
    payload: tuple[
        dict[str, Any],
        list[dict[str, Any]],
        ar.MotifContract,
        ConsumptiveRenewalContract,
        dict[int, dict[str, np.ndarray]],
    ]
) -> dict[str, Any]:
    item, models, writer_contract, contract, reference = payload
    candidate_id = str(item["candidate_id"])
    by_id = {str(row["candidate_id"]): row for row in models}
    if candidate_id not in by_id:
        raise ValueError(f"Stage-6D candidate is missing: {candidate_id}")
    candidate = by_id[candidate_id]
    configuration = ar.ReaderConfiguration(**item["configuration"])
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
    intact, exits = simulate_consumptive_lineage(
        condition="intact", retain_exits=True, **common
    )
    conditions: dict[str, Any] = {"intact": intact}
    for condition in item["conditions"]:
        if condition == "intact":
            continue
        result, _ = simulate_consumptive_lineage(
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


def _boot(
    values: Sequence[float],
    profile: ConsumptiveRenewalProfile,
    contract: ConsumptiveRenewalContract,
    *key: object,
) -> dict[str, Any]:
    return ar._bootstrap(
        values,
        profile.bootstrap_resamples,
        ar._hash_seed(contract.namespace, *key),
        contract.strict_alpha,
    )


def _effect_values(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
    key: str,
) -> list[float]:
    return ar._paired_texture_effects(
        rows, candidate_id, condition, generation, key
    )


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0.0 else 1.0


def _consumptive_summary(
    rows: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    generation: int,
    profile: ConsumptiveRenewalProfile,
    contract: ConsumptiveRenewalContract,
    phase: str,
) -> dict[str, Any]:
    """Extend the Stage-6C-R summary with carrier-free and transfer metrics."""

    base = ar._texture_summary(rows, candidate, generation, profile, contract, phase)
    candidate_id = str(candidate["candidate_id"])
    read = _effect_values(
        rows, candidate_id, "intact", generation, "read_match_mean"
    )
    post = _effect_values(
        rows, candidate_id, "intact", generation, "post_washout_match_mean"
    )
    writer = _effect_values(
        rows, candidate_id, "intact", generation, "writer_match_mean"
    )
    read_mean = float(np.mean(read)) if read else 0.0
    base["post_washout_acquisition"] = _boot(
        post, profile, contract, phase, candidate_id, generation, "post-washout"
    )
    base["writer_window_acquisition"] = _boot(
        writer, profile, contract, phase, candidate_id, generation, "writer-window"
    )
    for condition in (
        "no_erasure",
        "phenotype_scrub",
        "phenotype_same_rescue",
        "phenotype_opposite_rescue",
        "writer_observation_shuffle",
    ):
        values = _effect_values(
            rows, candidate_id, condition, generation, "read_match_mean"
        )
        if values:
            base["control_retention"][condition] = _ratio(
                float(np.mean(values)), read_mean
            )
    phenotype_scrub = _effect_values(
        rows, candidate_id, "phenotype_scrub", generation, "read_match_mean"
    )
    phenotype_same = _effect_values(
        rows,
        candidate_id,
        "phenotype_same_rescue",
        generation,
        "read_match_mean",
    )
    phenotype_opposite = _effect_values(
        rows,
        candidate_id,
        "phenotype_opposite_rescue",
        generation,
        "read_match_mean",
    )
    writer_shuffle = _effect_values(
        rows,
        candidate_id,
        "writer_observation_shuffle",
        generation,
        "read_match_mean",
    )
    if phenotype_scrub:
        base["phenotype_scrub_retention"] = _ratio(
            float(np.mean(phenotype_scrub)), read_mean
        )
    if phenotype_same:
        base["phenotype_same_rescue_retention"] = _ratio(
            float(np.mean(phenotype_same)), read_mean
        )
    if phenotype_opposite:
        base["phenotype_opposite_rescue"] = _boot(
            phenotype_opposite,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "phenotype-opposite",
        )
    if writer_shuffle:
        base["writer_shuffle"] = _boot(
            writer_shuffle,
            profile,
            contract,
            phase,
            candidate_id,
            generation,
            "writer-shuffle",
        )
    strict_rows = [
        row
        for row in rows
        if row.get("candidate_id") == candidate_id
        and "intact" in row.get("conditions", {})
    ]
    absence = [
        bool(row["conditions"]["intact"]["all_renewal_writer_windows_carrier_absent"])
        for row in strict_rows
    ]
    base["carrier_absence_fraction"] = (
        float(np.mean(absence)) if absence else 0.0
    )
    base["promotable"] = bool(candidate.get("promotable", False))
    return base


def _bound(summary: dict[str, Any], index: int, default: float) -> float:
    value = summary.get("ci", [None, None])[index]
    return default if value is None else float(value)


def _screen_gate(
    summary: dict[str, Any], contract: ConsumptiveRenewalContract
) -> bool:
    read = summary["read_acquisition"]
    post = summary["post_washout_acquisition"]
    active = summary["active_rewrite_advantage"]
    controls = summary["control_retention"]
    required = (
        "no_rewrite",
        "proper_subset",
        "read_disabled",
        "acquisition_write_disabled",
    )
    return bool(
        summary["promotable"]
        and float(read.get("mean") or 0.0) >= contract.screen_read_minimum
        and _bound(read, 0, -math.inf) > 0.0
        and float(post.get("mean") or 0.0)
        >= contract.screen_post_washout_minimum
        and _bound(post, 0, -math.inf) > 0.0
        and float(active.get("mean") or 0.0) >= contract.active_rewrite_minimum
        and _bound(active, 0, -math.inf) > 0.0
        and summary["fraction_templates_positive"]
        >= contract.template_positive_fraction
        and _bound(summary["joint_decoder"], 0, -math.inf)
        >= contract.joint_accuracy_minimum
        and _bound(summary["proper_subset_decoder"], 1, math.inf)
        <= contract.subset_accuracy_maximum
        and all(
            controls.get(condition, 1.0) <= 1.0 - contract.loss_fraction
            for condition in required
        )
        and summary["survival_mean"] >= contract.survival_minimum
        and summary["statistical_scaffold_retention"]
        >= contract.statistical_retention
        and summary["carrier_absence_fraction"] == 1.0
    )


def _qualification_gate(
    generation8: dict[str, Any],
    generation16: dict[str, Any],
    contract: ConsumptiveRenewalContract,
) -> bool:
    read8 = float(generation8["read_acquisition"].get("mean") or 0.0)
    read = generation16["read_acquisition"]
    post = generation16["post_washout_acquisition"]
    terminal = generation16["terminal_acquisition"]
    active = generation16["active_rewrite_advantage"]
    controls = generation16["control_retention"]
    required = (
        "no_rewrite",
        "proper_subset",
        "read_disabled",
        "acquisition_write_disabled",
        "zero_every_boundary",
        "shuffle_every_boundary",
        "transport_disabled",
    )
    carrier_opposite = generation16.get("opposite_rescue", {})
    phenotype_opposite = generation16.get("phenotype_opposite_rescue", {})
    writer_shuffle = generation16.get("writer_shuffle", {})
    return bool(
        float(read.get("mean") or 0.0) >= contract.qualification_read_minimum
        and _bound(read, 0, -math.inf) > 0.0
        and float(post.get("mean") or 0.0)
        >= contract.qualification_post_washout_minimum
        and _bound(post, 0, -math.inf) > 0.0
        and float(terminal.get("mean") or 0.0)
        >= contract.qualification_terminal_minimum
        and _bound(terminal, 0, -math.inf) > 0.0
        and float(active.get("mean") or 0.0) >= contract.active_rewrite_minimum
        and _bound(active, 0, -math.inf) > 0.0
        and read8 > 0.0
        and float(read.get("mean") or 0.0)
        >= contract.generation16_retention * read8
        and generation16["fraction_templates_positive"]
        >= contract.template_positive_fraction
        and _bound(generation16["joint_decoder"], 0, -math.inf)
        >= contract.joint_accuracy_minimum
        and _bound(generation16["proper_subset_decoder"], 1, math.inf)
        <= contract.subset_accuracy_maximum
        and all(
            controls.get(condition, 1.0) <= 1.0 - contract.loss_fraction
            for condition in required
        )
        and generation16.get("ablation_retention", 1.0)
        <= 1.0 - contract.loss_fraction
        and generation16.get("same_rescue_retention", 0.0)
        >= contract.rescue_fraction
        and _bound(carrier_opposite, 1, math.inf) < 0.0
        and generation16.get("phenotype_scrub_retention", 1.0)
        <= 1.0 - contract.loss_fraction
        and generation16.get("phenotype_same_rescue_retention", 0.0)
        >= contract.rescue_fraction
        and _bound(phenotype_opposite, 1, math.inf) < 0.0
        and _bound(writer_shuffle, 1, math.inf) < 0.0
        and float(generation16.get("translation_retention") or 0.0)
        >= contract.translation_retention
        and generation16["survival_mean"] >= contract.survival_minimum
        and generation16["statistical_scaffold_retention"]
        >= contract.statistical_retention
        and generation16["carrier_absence_fraction"] == 1.0
    )


def _endurance_gate(
    generation32: dict[str, Any],
    generation64: dict[str, Any],
    scales: dict[str, dict[str, Any]],
    contract: ConsumptiveRenewalContract,
) -> bool:
    read32 = generation32["read_acquisition"]
    read64 = generation64["read_acquisition"]
    post64 = generation64["post_washout_acquisition"]
    base = float(
        scales.get("extent16-fixed", {})
        .get("read_acquisition", {})
        .get("mean")
        or 0.0
    )
    scale_pass = base > 0.0 and all(
        float(
            scales.get(f"extent{extent}-{mode}", {})
            .get("read_acquisition", {})
            .get("mean")
            or 0.0
        )
        >= contract.translation_retention * base
        for extent in (16, 32, 64)
        for mode in ("fixed", "diameter")
    )
    return bool(
        float(read32.get("mean") or 0.0)
        >= contract.endurance_generation32_minimum
        and _bound(read32, 0, -math.inf) > 0.0
        and float(read64.get("mean") or 0.0)
        >= contract.endurance_generation64_minimum
        and _bound(read64, 0, -math.inf) > 0.0
        and float(post64.get("mean") or 0.0)
        > contract.endurance_post_washout_minimum
        and _bound(post64, 0, -math.inf) > 0.0
        and generation64["control_retention"].get("no_rewrite", 1.0)
        <= contract.endurance_no_rewrite_maximum
        and generation64["control_retention"].get("proper_subset", 1.0)
        <= 1.0 - contract.loss_fraction
        and generation64["control_retention"].get("read_disabled", 1.0)
        <= 1.0 - contract.loss_fraction
        and float(generation64.get("translation_retention") or 0.0)
        >= contract.translation_retention
        and generation64["survival_mean"] >= contract.survival_minimum
        and generation64["carrier_absence_fraction"] == 1.0
        and scale_pass
    )


def _audit_gate(
    generation8: dict[str, Any],
    generation16: dict[str, Any],
    generation64: dict[str, Any],
    contract: ConsumptiveRenewalContract,
) -> bool:
    controls = generation64["control_retention"]
    phenotype_opposite = generation64.get("phenotype_opposite_rescue", {})
    return bool(
        _screen_gate(generation8, contract)
        and float(generation16["read_acquisition"].get("mean") or 0.0)
        >= contract.qualification_read_minimum
        and _bound(generation16["read_acquisition"], 0, -math.inf) > 0.0
        and float(generation64["read_acquisition"].get("mean") or 0.0)
        >= contract.endurance_generation64_minimum
        and _bound(generation64["read_acquisition"], 0, -math.inf) > 0.0
        and float(generation64["post_washout_acquisition"].get("mean") or 0.0)
        > 0.0
        and _bound(generation64["post_washout_acquisition"], 0, -math.inf) > 0.0
        and controls.get("no_rewrite", 1.0)
        <= contract.endurance_no_rewrite_maximum
        and controls.get("proper_subset", 1.0) <= 1.0 - contract.loss_fraction
        and controls.get("read_disabled", 1.0) <= 1.0 - contract.loss_fraction
        and controls.get("acquisition_write_disabled", 1.0)
        <= 1.0 - contract.loss_fraction
        and generation64.get("phenotype_scrub_retention", 1.0)
        <= 1.0 - contract.loss_fraction
        and generation64.get("phenotype_same_rescue_retention", 0.0)
        >= contract.rescue_fraction
        and _bound(phenotype_opposite, 1, math.inf) < 0.0
        and generation64["carrier_absence_fraction"] == 1.0
        and generation64["survival_mean"] >= contract.survival_minimum
        and generation64["statistical_scaffold_retention"]
        >= contract.statistical_retention
    )


def _frozen_stage6cr_hashes(stage6cr_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "COHORTS.json",
        "screen/RESULTS.json",
        "COMPLETE",
    )
    missing = [stage6cr_root / name for name in required if not (stage6cr_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6C-R artifacts: {missing}")
    status = _load_json(stage6cr_root / "STATUS.json")
    result = _load_json(stage6cr_root / "RESULTS.json")
    cohorts = _load_json(stage6cr_root / "COHORTS.json")
    screen = _load_json(stage6cr_root / "screen/RESULTS.json")
    if status.get("state") != "complete" or result.get("state") != "complete":
        raise ValueError("Stage-6C-R is not complete")
    if result.get("verdict") != "NO_ACQUIRED_TEXTURE_WRITE":
        raise ValueError("Stage-6C-R verdict changed")
    if cohorts.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6C-R protected reserve is no longer untouched")
    near = screen.get("candidate_summaries", {}).get(ANCHOR_SOURCE_ID)
    passive = screen.get("candidate_summaries", {}).get(
        "texture-r16-s60-d48-rho75"
    )
    if near is None or passive is None:
        raise ValueError("Stage-6C-R forensic anchors are missing")
    diagnosis = {
        "near_active_anchor": {
            "candidate_id": ANCHOR_SOURCE_ID,
            "read_mean": near["read_acquisition"]["mean"],
            "read_threshold_shortfall": (
                0.25 - float(near["read_acquisition"]["mean"])
            ),
            "active_rewrite_advantage": near["active_rewrite_advantage"]["mean"],
            "no_rewrite_retention": near["control_retention"]["no_rewrite"],
            "joint_decoder": near["joint_decoder"]["mean"],
            "proper_subset_upper": near["proper_subset_decoder"]["ci"][1],
        },
        "passive_anchor": {
            "candidate_id": "texture-r16-s60-d48-rho75",
            "read_mean": passive["read_acquisition"]["mean"],
            "terminal_mean": passive["terminal_acquisition"]["mean"],
            "no_rewrite_retention": passive["control_retention"]["no_rewrite"],
        },
    }
    return ({name: ar._sha256(stage6cr_root / name) for name in required}, diagnosis)


def _prepare_stage6d(
    output: Path,
    profile_name: str,
    *,
    auto_final_audit: bool,
    stage6cr_root: Path,
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
    ConsumptiveRenewalProfile,
    ConsumptiveRenewalContract,
    ar.MotifContract,
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, Any],
    str,
]:
    stage6cr_root = stage6cr_root.resolve()
    stage6c_root = stage6c_root.resolve()
    stage6br_root = stage6br_root.resolve()
    stage6cr_hashes, diagnosis = _frozen_stage6cr_hashes(stage6cr_root)
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
    profile = CONSUMPTIVE_RENEWAL_PROFILES[profile_name]
    contract = ConsumptiveRenewalContract()
    writer_contract = ar.MotifContract()
    base = ar.select_synergy_cohorts(
        frozen,
        ar.SYNERGY_PROFILES["reference"],
        "reference",
        open_final=False,
    )
    exposed = base["plasticity"]
    stage6c_design = _load_json(stage6c_root / "DESIGN.json")
    expected = stage6c_design["development_pair_ids"]["plasticity"]
    observed = [str(pair["pair_id"]) for pair in exposed]
    if observed != expected:
        raise ValueError("Stage-6C exposed cohort changed")
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
        raise AssertionError("Stage-6D developmental cohorts overlap")
    if set(used) & set(frozen["later_ids"]):
        raise AssertionError("Stage-6D development touched the final reserve")
    candidates, anchor = build_consumptive_candidates(stage6br_root)
    templates = ar.acquisition_templates(ar.SynergyContract())
    reserve_digest = hashlib.sha256(
        "\n".join(frozen["later_ids"]).encode()
    ).hexdigest()
    stage6cr_design = _load_json(stage6cr_root / "DESIGN.json")
    design_payload = {
        "experiment": "ca_motif_consumptive_renewal_stage_6d",
        "contract": contract.to_dict(),
        "writer_contract_digest": writer_contract.digest,
        "profile_name": profile_name,
        "profile": asdict(profile),
        "phases": PHASES,
        "automatic_phase_progression": True,
        "automatic_final_audit_user_authorized": bool(auto_final_audit),
        "automatic_final_audit_requires_all_developmental_gates": True,
        "frozen_stage6cr_sha256": stage6cr_hashes,
        "frozen_stage6c_sha256": stage6c_hashes,
        "stage6cr_design_digest": stage6cr_design["design_digest"],
        "stage6c_design_digest": stage6c_design["design_digest"],
        "stage6cr_forensic_diagnosis": diagnosis,
        "candidate_factorial": {
            "rank": (16,),
            "read_strength": (0.60, 0.75, 0.90),
            "read_sweeps": (40, 48),
            "washout_sweeps": (4, 8),
            "write_gain": (1.0, 1.5),
            "strict_candidate_count": len(candidates),
            "screen_promotion_limit": 3,
            "qualification_promotion_limit": 2,
            "anchor_id": ANCHOR_ID,
            "anchor_promotable": False,
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
            "motif_consumptive_renewal.py": ar._sha256(Path(__file__)),
            "motif_acquisition_repair.py": ar._sha256(
                Path(__file__).with_name("motif_acquisition_repair.py")
            ),
            "motif_synergistic_heredity.py": ar._sha256(
                Path(__file__).with_name("motif_synergistic_heredity.py")
            ),
        },
        "input_sha256": {
            "protocol": ar._sha256(PROTOCOL_PATH),
            **{
                f"stage5r_{key}": ar._sha256(path)
                for key, path in frozen["paths"].items()
            },
        },
        "writer_api_excludes": (
            "environment template",
            "target label",
            "family label",
            "lineage identity",
            "incoming carrier payload",
        ),
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
            raise ValueError("Stage-6D design changed; refusing a mixed resume")
    else:
        ar._atomic_json(design_path, design)
    prior_cohorts = (
        _load_json(output / "COHORTS.json")
        if (output / "COHORTS.json").exists()
        else {}
    )
    reserve_state = prior_cohorts.get("final_audit_trajectory_state", "untouched")
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
        output / "CANDIDATES.json",
        {
            "design_digest": design_digest,
            "strict_candidate_count": len(candidates),
            "candidates": [_candidate_public(row) for row in candidates],
            "calibration_anchor": _candidate_public(anchor),
        },
    )
    ar._atomic_json(
        output / "ACQUISITION_TEMPLATES.json",
        {
            "design_digest": design_digest,
            "templates": templates,
            "environment_bits_passed_to_writer": False,
            "incoming_payload_passed_to_writer": False,
        },
    )
    ar._atomic_json(
        output / "CLEANROOM_PROVENANCE.json",
        {
            "experiment": "ca_motif_consumptive_renewal_stage_6d",
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
        anchor,
        templates,
        diagnosis,
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
        "experiment": "ca_motif_consumptive_renewal_stage_6d",
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
            "decision": (
                "advance"
                if payload.get("stage_gate") and next_phase
                else (
                    "campaign_complete"
                    if payload.get("stage_gate")
                    else "phase_gate_failed"
                )
            ),
            "next_phase": next_phase if payload.get("stage_gate") else None,
            "final_audit_trajectory_state": payload.get(
                "final_audit_trajectory_state", "untouched"
            ),
        },
    )
    ar._atomic_text(root / "REPORT.md", report.rstrip() + "\n")
    ar._atomic_text(root / "LAY_SUMMARY.md", lay.rstrip() + "\n")
    ar._atomic_text(root / "COMPLETE", "complete\n")


def _run_forensics(
    output: Path,
    diagnosis: dict[str, Any],
    design_digest: str,
    status: Any,
) -> dict[str, Any]:
    status("running", "frozen-stage6cr-diagnosis", completed=0, total=1)
    near = diagnosis["near_active_anchor"]
    passive = diagnosis["passive_anchor"]
    stage_gate = bool(
        0.0 < float(near["read_threshold_shortfall"]) < 0.01
        and float(near["active_rewrite_advantage"]) > 0.20
        and float(near["no_rewrite_retention"]) <= 0.30
        and float(passive["no_rewrite_retention"]) > 0.70
    )
    result = {
        "state": "complete",
        "stage_gate": stage_gate,
        "near_active_anchor": near,
        "passive_anchor": passive,
        "registered_repair": "destroy incoming carrier before writer observation",
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_result(
        output,
        "forensics",
        design_digest,
        result,
        "# Stage 6D forensics\n\nThe frozen near-active and passive anchors "
        "were reproduced from Stage 6C-R artifacts.  The strict repair removes "
        "the incoming carrier before every daughter writer window.",
        "# Lay summary\n\nOne old design nearly renewed memory, while the strongest "
        "short-term design mostly kept an old note.  Stage 6D forbids keeping "
        "that note while the daughter writes the next one.",
        next_phase="screen",
    )
    status("running", "frozen-stage6cr-diagnosis", completed=1, total=1)
    return result


def _ranked_ids(summaries: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(
        summaries,
        key=lambda candidate_id: (
            -float(
                summaries[candidate_id]["post_washout_acquisition"].get("mean")
                or 0.0
            ),
            -float(
                summaries[candidate_id]["active_rewrite_advantage"].get("mean")
                or 0.0
            ),
            candidate_id,
        ),
    )


def _models_by_id(
    candidates: Sequence[dict[str, Any]], candidate_ids: Sequence[str]
) -> list[dict[str, Any]]:
    by_id = {str(row["candidate_id"]): row for row in candidates}
    missing = [candidate_id for candidate_id in candidate_ids if candidate_id not in by_id]
    if missing:
        raise ValueError(f"Stage-6D selected candidates are missing: {missing}")
    return [by_id[candidate_id] for candidate_id in candidate_ids]


def _run_screen(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: ConsumptiveRenewalProfile,
    contract: ConsumptiveRenewalContract,
    writer_contract: ar.MotifContract,
    candidates: list[dict[str, Any]],
    anchor: dict[str, Any],
    templates: list[dict[str, Any]],
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    scientific: bool,
    status: Any,
) -> dict[str, Any]:
    models = _profile_candidates(candidates, anchor, profile.candidate_limit)
    items = ar._make_items(
        cohorts["screen"],
        models,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="screen",
        replicates=profile.screen_replicates,
        generations=8,
        conditions=SCREEN_CONDITIONS,
    )
    rows, complete = ar._run_json_checkpoints(
        output,
        "screen-trajectories-stage6d",
        items,
        models,
        _consumptive_pair_task,
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
        str(candidate["candidate_id"]): _consumptive_summary(
            rows, candidate, 8, profile, contract, "screen"
        )
        for candidate in models
    }
    for summary in summaries.values():
        summary["screen_gate"] = _screen_gate(summary, contract) if scientific else summary["promotable"]
    ranked = _ranked_ids(summaries)
    eligible = [
        candidate_id
        for candidate_id in ranked
        if summaries[candidate_id]["screen_gate"]
    ]
    selected = eligible[:3] if complete else []
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(selected),
        "scientific_gate_applied": scientific,
        "candidate_summaries": summaries,
        "eligible_candidate_ids": eligible,
        "selected_candidate_ids": selected,
        "calibration_anchor_id": ANCHOR_ID,
        "calibration_anchor_promotable": False,
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "final_audit_trajectory_state": "untouched",
    }
    _write_phase_result(
        output,
        "screen",
        design_digest,
        result,
        "# Stage 6D screen\n\nSelected strict candidates: "
        + (", ".join(selected) if selected else "none"),
        "# Lay summary\n\nThe incoming note was destroyed before the daughter "
        "writer observed the visible pattern.  Only daughters that made a fresh "
        "note could advance.",
        next_phase="qualify",
    )
    return result


def _run_qualification(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: ConsumptiveRenewalProfile,
    contract: ConsumptiveRenewalContract,
    writer_contract: ar.MotifContract,
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
            "# Stage 6D qualification\n\nSkipped because the strict screen failed.",
            "# Lay summary\n\nNo fresh daughter-written carrier was strong enough "
            "for the causal challenges.",
            next_phase="endurance",
        )
        return result
    models = _models_by_id(candidates, selected_ids)
    items = ar._make_items(
        cohorts["qualification"],
        models,
        ar._template_pairs(templates, "qualification"),
        frozen["stage4"]["configuration"],
        phase="qualify",
        replicates=profile.qualification_replicates,
        generations=16,
        conditions=QUALIFICATION_CONDITIONS,
    )
    rows, complete = ar._run_json_checkpoints(
        output,
        "qualification-trajectories-stage6d",
        items,
        models,
        _consumptive_pair_task,
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
        generation8 = _consumptive_summary(
            rows, candidate, 8, profile, contract, "qualification-g8"
        )
        generation16 = _consumptive_summary(
            rows, candidate, 16, profile, contract, "qualification-g16"
        )
        gate = (
            _qualification_gate(generation8, generation16, contract)
            if scientific
            else True
        )
        summaries[candidate_id] = {
            "candidate": _candidate_public(candidate),
            "generation8": generation8,
            "generation16": generation16,
            "qualification_gate": gate,
        }
    ranked = sorted(
        summaries,
        key=lambda candidate_id: (
            -float(
                summaries[candidate_id]["generation16"][
                    "post_washout_acquisition"
                ].get("mean")
                or 0.0
            ),
            -float(
                summaries[candidate_id]["generation16"][
                    "active_rewrite_advantage"
                ].get("mean")
                or 0.0
            ),
            candidate_id,
        ),
    )
    qualified = [
        candidate_id
        for candidate_id in ranked
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
        "# Stage 6D qualification\n\nQualified consumptive candidates: "
        + (", ".join(qualified) if qualified else "none"),
        "# Lay summary\n\nThe survivors were tested by destroying, scrambling, "
        "rescuing, and reversing both the hidden carrier and the visible form "
        "from which daughters write.",
        next_phase="endurance",
    )
    return result


def _run_endurance(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: ConsumptiveRenewalProfile,
    contract: ConsumptiveRenewalContract,
    writer_contract: ar.MotifContract,
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
            "# Stage 6D endurance\n\nSkipped because qualification failed.",
            "# Lay summary\n\nNo consumptively renewed memory was ready for the "
            "64-generation and scale tests.",
            next_phase="adjudicate",
        )
        return result
    models = _models_by_id(candidates, qualified_ids)
    template_pairs = ar._template_pairs(templates, "qualification")
    items = ar._make_items(
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
                ar._make_items(
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
    rows, complete = ar._run_json_checkpoints(
        output,
        "endurance-trajectories-stage6d",
        items,
        models,
        _consumptive_pair_task,
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
        generation32 = _consumptive_summary(
            lineage_rows, candidate, 32, profile, contract, "endurance-g32"
        )
        generation64 = _consumptive_summary(
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
                scale_summaries[f"extent{extent}-{scale_mode}"] = (
                    _consumptive_summary(
                        scale_rows,
                        candidate,
                        16,
                        profile,
                        contract,
                        f"endurance-scale-{extent}-{scale_mode}",
                    )
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
        "# Stage 6D endurance\n\nEnduring consumptive candidates: "
        + (", ".join(enduring) if enduring else "none"),
        "# Lay summary\n\nThe daughters repeatedly destroyed and rebuilt their "
        "memory for 64 generations and on three lattice sizes.",
        next_phase="adjudicate",
    )
    return result


def _open_final_pairs(frozen: dict[str, Any]) -> list[dict[str, Any]]:
    opened = ar.select_synergy_cohorts(
        frozen,
        ar.SYNERGY_PROFILES["reference"],
        "reference",
        open_final=True,
    )["final"]
    if len(opened) != 62:
        raise ValueError("Stage-6D final reserve is incomplete")
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
    ar._atomic_json(path, payload)


def _run_adjudication(
    output: Path,
    frozen: dict[str, Any],
    cohorts: dict[str, list[dict[str, Any]]],
    profile: ConsumptiveRenewalProfile,
    contract: ConsumptiveRenewalContract,
    writer_contract: ar.MotifContract,
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
            "frozen_winner_id": None,
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
            "# Stage 6D adjudication\n\nThe final reserve remained sealed.",
            "# Lay summary\n\nAn earlier test failed, so none of the protected "
            "cases were inspected.",
            next_phase=None,
        )
        return result
    if scientific and not auto_final_audit:
        raise ValueError("reference Stage-6D final audit lacks authorization")
    endurance_summaries = endurance["candidate_summaries"]
    ranked = sorted(
        enduring_ids,
        key=lambda candidate_id: (
            -float(
                endurance_summaries[candidate_id]["generation64"][
                    "post_washout_acquisition"
                ].get("mean")
                or 0.0
            ),
            -float(
                endurance_summaries[candidate_id]["generation64"][
                    "read_acquisition"
                ].get("mean")
                or 0.0
            ),
            candidate_id,
        ),
    )
    winner_id = ranked[0]
    models = _models_by_id(candidates, [winner_id])
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
    ar._atomic_json(
        output / "FINAL_AUDIT_DESIGN.json",
        {
            "design_digest": design_digest,
            "candidate_id": winner_id,
            "winner_frozen_before_pair_loading": True,
            "pair_count": len(final_pairs),
            "pair_ids_sha256": pair_digest,
            "conditions": AUDIT_CONDITIONS,
            "templates": [
                (left["template_id"], right["template_id"])
                for left, right in ar._template_pairs(templates, "audit")
            ],
            "generations": 64,
            "retuning": False,
        },
    )
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
        output,
        "final-audit-trajectories-stage6d",
        items,
        models,
        _consumptive_pair_task,
        writer_contract,
        contract,
        frozen["stage4"]["reference"],
        design_digest,
        workers=workers,
        resume=resume,
        deadline=deadline,
        status=status,
    )
    candidate = models[0]
    generation8 = _consumptive_summary(
        rows, candidate, 8, profile, contract, "final-audit-g8"
    )
    generation16 = _consumptive_summary(
        rows, candidate, 16, profile, contract, "final-audit-g16"
    )
    generation64 = _consumptive_summary(
        rows, candidate, 64, profile, contract, "final-audit-g64"
    )
    final_gate = (
        _audit_gate(generation8, generation16, generation64, contract)
        if scientific
        else True
    )
    summaries = {
        winner_id: {
            "candidate": _candidate_public(candidate),
            "generation8": generation8,
            "generation16": generation16,
            "generation64": generation64,
            "final_gate": final_gate,
        }
    }
    confirmed = [winner_id] if complete and final_gate else []
    final_digest = hashlib.sha256(
        json.dumps(summaries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if scientific:
        reserve_state = "complete" if complete else "partial"
        _update_reserve_state(output, reserve_state, final_digest=final_digest)
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(confirmed),
        "scientific_gate_applied": scientific,
        "finalist_candidate_ids": enduring_ids,
        "frozen_winner_id": winner_id,
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
        "# Stage 6D adjudication\n\nConfirmed candidate: "
        + (winner_id if confirmed else "none"),
        "# Lay summary\n\nThe protected cases were opened only after every "
        "developmental test passed, using one already-frozen design.",
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
            raise ValueError("Stage-6D output exists; use --resume")
        if payload.get("design_digest") != design_digest:
            raise ValueError("Stage-6D campaign design mismatch")
        if not math.isclose(float(payload["max_hours"]), max_hours):
            raise ValueError("Stage-6D max-hours changed during resume")
        return payload
    started = time.time()
    fraction = (
        ConsumptiveRenewalContract().exploration_stop_hours
        / ConsumptiveRenewalContract().max_hours
    )
    payload = {
        "experiment": "ca_motif_consumptive_renewal_stage_6d",
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
        cohorts = (
            _load_json(output / "COHORTS.json")
            if (output / "COHORTS.json").exists()
            else {}
        )
        payload = {
            "state": state,
            "stage": "ca_motif_consumptive_renewal_stage_6d",
            "profile": profile_name,
            "phase": phase,
            "current": current,
            "pid": os.getpid(),
            "workers_hard_max": ConsumptiveRenewalContract().max_workers,
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
        ar._atomic_json(output / "STATUS.json", payload)
        if phase in PHASES:
            phase_root = output / phase
            phase_root.mkdir(parents=True, exist_ok=True)
            ar._atomic_json(phase_root / "STATUS.json", payload)
        progress = ""
        if "completed" in extra and "total" in extra:
            progress = f" {extra['completed']}/{extra['total']}"
        print(f"[{state}] stage6d-{phase}:{current}{progress}", flush=True)

    return write


def _require_phase(output: Path, phase: str, design_digest: str) -> None:
    path = output / phase / "RESULTS.json"
    if not path.exists() or not (output / phase / "COMPLETE").exists():
        raise ValueError(f"Stage-6D predecessor is incomplete: {phase}")
    if _load_json(path).get("design_digest") != design_digest:
        raise ValueError(f"Stage-6D predecessor design mismatch: {phase}")


def _campaign_verdict(output: Path, scientific: bool) -> str:
    if not scientific:
        return "SMOKE_PATH_VALIDATED"
    phase_results = {
        phase: _load_json(output / phase / "RESULTS.json") for phase in PHASES
    }
    if any(value.get("state") == "budget_truncated" for value in phase_results.values()):
        return "INCONCLUSIVE_RESOURCE_LIMIT"
    screen = phase_results["screen"]
    qualification = phase_results["qualify"]
    endurance = phase_results["endurance"]
    adjudication = phase_results["adjudicate"]
    if adjudication.get("confirmed_candidate_ids"):
        return "CONSUMPTIVE_PLASTIC_HEREDITY_CONFIRMED"
    if not screen.get("stage_gate"):
        strict = [
            value
            for candidate_id, value in screen.get("candidate_summaries", {}).items()
            if candidate_id != ANCHOR_ID
        ]
        direct_only = any(
            float(value.get("read_acquisition", {}).get("mean") or 0.0)
            >= ConsumptiveRenewalContract().screen_read_minimum
            and float(
                value.get("post_washout_acquisition", {}).get("mean") or 0.0
            )
            < ConsumptiveRenewalContract().screen_post_washout_minimum
            for value in strict
        )
        return "ACQUIRED_BUT_DIRECT_ECHO_ONLY" if direct_only else "NO_RENEWABLE_TEXTURE"
    if not qualification.get("stage_gate"):
        return "DEVELOPMENTAL_ONLY_NOT_CONFIRMED"
    if not endurance.get("stage_gate"):
        return "RENEWAL_WITHOUT_ENDURANCE"
    return "DEVELOPMENTAL_ONLY_NOT_CONFIRMED"


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
        "experiment": "ca_motif_consumptive_renewal_stage_6d",
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
        "frozen_winner_id": phase_results["adjudicate"].get("frozen_winner_id"),
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
            "final_audit_trajectory_state": result[
                "final_audit_trajectory_state"
            ],
        },
    )
    ar._atomic_text(
        output / "REPORT.md",
        "# Stage 6D consumptive renewal\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"Selected: {result['selected_candidate_ids']}\n\n"
        f"Qualified: {result['qualified_candidate_ids']}\n\n"
        f"Enduring: {result['enduring_candidate_ids']}\n\n"
        f"Frozen winner: {result['frozen_winner_id']}\n\n"
        f"Confirmed: {result['confirmed_candidate_ids']}\n\n"
        "The final reserve was "
        + (
            "opened under the frozen gate.\n"
            if result["final_audit_opened"]
            else "not opened.\n"
        ),
    )
    if result["stage_gate"]:
        lay = (
            "A learned local form survived because every daughter used it to "
            "make a fresh hidden memory after the inherited memory had already "
            "been destroyed."
        )
    elif verdict == "ACQUIRED_BUT_DIRECT_ECHO_ONLY":
        lay = (
            "The carrier could briefly draw the learned form, but that form did "
            "not remain long enough without the carrier to write a fresh memory."
        )
    elif verdict == "NO_RENEWABLE_TEXTURE":
        lay = (
            "No design made a sufficiently strong fresh daughter-written memory "
            "after the incoming memory was destroyed."
        )
    else:
        lay = (
            "Fresh daughter-written memory appeared during development but did "
            "not pass every endurance and protected test."
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
        },
    )
    ar._atomic_text(output / "COMPLETE", "complete\n")
    return result


def run_motif_consumptive_renewal(
    output: Path,
    *,
    phase: str = "all",
    stage6cr_root: Path = DEFAULT_STAGE6CR_ROOT,
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
    """Run the frozen Stage-6D consumptive-renewal campaign."""

    ar.require_pinned_numpy()
    if phase not in (*PHASES, "all"):
        raise ValueError(f"unknown Stage-6D phase {phase!r}")
    if profile_name not in PUBLIC_PROFILES:
        raise ValueError(f"unknown Stage-6D profile {profile_name!r}")
    if workers < 1 or workers > ConsumptiveRenewalContract().max_workers:
        raise ValueError("Stage-6D workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > ConsumptiveRenewalContract().max_hours:
        raise ValueError("Stage-6D max-hours must be in (0, 8]")
    if profile_name == "reference" and not auto_final_audit:
        raise ValueError(
            "reference Stage-6D requires registered automatic final-audit authorization"
        )
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ar._atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
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
            anchor,
            templates,
            diagnosis,
            design_digest,
        ) = _prepare_stage6d(
            output,
            profile_name,
            auto_final_audit=auto_final_audit,
            stage6cr_root=stage6cr_root,
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
        runners = {
            "forensics": lambda: _run_forensics(
                output, diagnosis, design_digest, status
            ),
            "screen": lambda: _run_screen(
                output,
                frozen,
                cohorts,
                profile,
                contract,
                writer_contract,
                candidates,
                anchor,
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
            status("complete", "campaign-complete", verdict=result["verdict"])
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
    "ALL_CONDITIONS",
    "CONSUMPTIVE_RENEWAL_PROFILES",
    "ConsumptiveRenewalContract",
    "DEFAULT_STAGE6CR_ROOT",
    "PHASES",
    "build_consumptive_candidates",
    "run_motif_consumptive_renewal",
    "simulate_consumptive_lineage",
)
