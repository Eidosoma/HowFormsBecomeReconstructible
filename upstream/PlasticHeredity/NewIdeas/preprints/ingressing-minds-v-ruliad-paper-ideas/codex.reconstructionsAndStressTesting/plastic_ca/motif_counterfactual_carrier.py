"""Stage-6O prospective audit of the two leads exposed by Stage 6N.

Stage 6N is an immutable parent.  This module corrects the prospective motion
question by separating instruction obedience from signed original direction
and by scoring form modulo D4 symmetry.  It also independently repeats the two
compact near-miss oracle trajectories before allowing the frozen attractor
pipeline to advance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Sequence

import numpy as np

from . import motif_acquisition_repair as ar
from . import motif_causal_attractor as cn
from . import motif_inverse_distillation as il
from . import motif_latent_regeneration as lm
from . import motif_phenotype_bridge as pb
from . import motif_writer_closure as wc
from .life_family import life_rule_notation


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "CA_MOTIF_COUNTERFACTUAL_CARRIER_PROTOCOL.md"
DISCOVERY_LOG = ROOT / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"
DEFAULT_STAGE6N_ROOT = ROOT / "results/ca-motif-causal-attractor-stage-6n"
DEFAULT_STAGE6M_ROOT = cn.DEFAULT_STAGE6M_ROOT
DEFAULT_STAGE6L_ROOT = cn.DEFAULT_STAGE6L_ROOT
PARENT_STAGE6N_DIGEST = (
    "4d6de28b28aa275677c84f10d48eb3ccd9abe4a699372a94a471fdc52305fd48"
)
PHASES = (
    "integrity",
    "allocation",
    "motion-metric-audit",
    "motion-oracle",
    "motion-writer",
    "motion-validation",
    "compact-confirmation",
    "compact-attractor-fit",
    "compact-contraction",
    "compact-closed-loop",
    "compact-validation",
    "adjudicate",
)


@dataclass(frozen=True)
class CounterfactualCarrierProfile:
    development_pairs: int
    procedural_validation_pairs: int
    trace_replicates: int
    validation_replicates: int
    rollout_rounds: int
    maximum_frozen_writers: int
    compact_confirmation_start: int
    compact_confirmation_pairs: int
    compact_dimensions: tuple[int, ...]
    attractor_kinds: tuple[str, ...]
    support_lengths: tuple[int, ...]
    writer_endpoints: tuple[int, ...]
    motion_scan_per_rule: int
    motion_development_pairs: int
    motion_validation_pairs: int
    motion_oracle_pairs: int
    motion_codebook_sizes: tuple[int, ...]
    bootstrap_resamples: int

    def causal_profile(self) -> cn.CausalAttractorProfile:
        return cn.CausalAttractorProfile(
            self.development_pairs,
            self.procedural_validation_pairs,
            self.trace_replicates,
            self.validation_replicates,
            self.rollout_rounds,
            self.maximum_frozen_writers,
            self.compact_confirmation_pairs,
            self.compact_dimensions,
            self.attractor_kinds,
            self.support_lengths,
            self.writer_endpoints,
            self.motion_scan_per_rule,
            self.motion_development_pairs,
            self.motion_validation_pairs,
            self.motion_oracle_pairs,
            self.motion_codebook_sizes,
            self.bootstrap_resamples,
        )


PROFILES = {
    "smoke": CounterfactualCarrierProfile(
        6,
        2,
        1,
        1,
        1,
        1,
        0,
        2,
        (4,),
        ("leaky",),
        (8,),
        (16,),
        512,
        4,
        2,
        2,
        (4,),
        100,
    ),
    "reference": CounterfactualCarrierProfile(
        56,
        16,
        2,
        4,
        3,
        2,
        8,
        16,
        (4, 16),
        ("leaky", "contractive-tanh", "prototype"),
        (8, 16),
        (16, 24),
        8192,
        40,
        16,
        8,
        (2, 4, 8, 16, 32),
        10_000,
    ),
}


@dataclass(frozen=True)
class CounterfactualCarrierContract(cn.CausalAttractorContract):
    implementation_version: str = "ca-motif-counterfactual-carrier-v1"
    namespace: str = "plastic-ca-motif-counterfactual-carrier-v1"
    motion_rescue_direction_contrast_minimum: float = 0.40

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "implementation_version": self.implementation_version,
                "namespace": self.namespace,
                "motion_rescue_direction_contrast_minimum": (
                    self.motion_rescue_direction_contrast_minimum
                ),
                "motion_form_symmetry": "D4-max; direction-never-aligned",
                "motion_direction_scores": (
                    "instruction-relative",
                    "signed-original-relative",
                ),
                "compact_confirmation_dimensions": (4, 16),
                "compact_threshold_lowered": False,
                "final_reserve_policy": "unreachable-and-never-open-in-stage-6o",
            }
        )
        return payload


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _empty(reason: str) -> dict[str, Any]:
    return {
        "state": "complete",
        "stage_gate": False,
        "skipped_reason": reason,
        "final_audit_trajectory_state": "untouched",
    }


def _d4_foreground_overlap(
    observed: np.ndarray, target: np.ndarray
) -> dict[str, Any]:
    """Translation-invariant form overlap maximized over D4, never velocity."""

    best: dict[str, Any] = {
        "foreground_f1": 0.0,
        "foreground_iou": 0.0,
        "mass_ratio": 0.0,
        "form_symmetry": 0,
    }
    for symmetry in range(8):
        transformed = il._d4_blocks(
            np.asarray(target, dtype=np.float32), symmetry
        )
        score = cn._foreground_overlap(observed, transformed)
        if (score["foreground_f1"], score["foreground_iou"]) > (
            best["foreground_f1"],
            best["foreground_iou"],
        ):
            best = {**score, "form_symmetry": symmetry}
    return best


def _counterfactual_motion_metrics(
    observed_history: Sequence[np.ndarray],
    target_history: Sequence[np.ndarray],
    instructed_displacement: Sequence[int],
    original_displacement: Sequence[int],
) -> dict[str, Any]:
    detection = wc._detect_mover(observed_history)
    target_detection = wc._detect_mover(target_history)
    if detection is None or target_detection is None:
        return {
            "mover_detected": False,
            "foreground_f1": 0.0,
            "foreground_iou": 0.0,
            "mass_ratio": 0.0,
            "form_symmetry": None,
            "instruction_direction_similarity": 0.0,
            "signed_original_direction_similarity": 0.0,
            "direction_similarity": 0.0,
            "correct_instruction_direction": False,
            "correct_original_direction": False,
            "correct_direction": False,
            "form_success": False,
        }
    best: dict[str, Any] = {
        "foreground_f1": 0.0,
        "foreground_iou": 0.0,
        "mass_ratio": 0.0,
        "form_symmetry": 0,
    }
    observed_start = int(detection["detection_start"])
    target_start = int(target_detection["detection_start"])
    phase_count = max(int(detection["period"]), int(target_detection["period"]))
    for left_phase in range(phase_count):
        left_index = min(len(observed_history) - 1, observed_start + left_phase)
        for right_phase in range(phase_count):
            right_index = min(len(target_history) - 1, target_start + right_phase)
            score = _d4_foreground_overlap(
                observed_history[left_index], target_history[right_index]
            )
            if (score["foreground_f1"], score["foreground_iou"]) > (
                best["foreground_f1"],
                best["foreground_iou"],
            ):
                best = score
    instruction_similarity = wc._velocity_similarity(
        detection["displacement_yx"], instructed_displacement
    )
    original_similarity = wc._velocity_similarity(
        detection["displacement_yx"], original_displacement
    )
    form_success = bool(
        best["foreground_f1"] >= 0.70 and 0.5 <= best["mass_ratio"] <= 2.0
    )
    return {
        "mover_detected": True,
        **best,
        "instruction_direction_similarity": float(instruction_similarity),
        "signed_original_direction_similarity": float(original_similarity),
        "direction_similarity": float(instruction_similarity),
        "correct_instruction_direction": bool(instruction_similarity > 0.5),
        "correct_original_direction": bool(original_similarity > 0.5),
        "correct_direction": bool(instruction_similarity > 0.5),
        "form_success": form_success,
        "detected_period": int(detection["period"]),
        "detected_displacement_yx": list(detection["displacement_yx"]),
    }


def _motion_lineage(
    model: dict[str, Any],
    pair: dict[str, Any],
    direction: str,
    condition: str,
    *,
    oracle: bool,
    generations: int = 4,
) -> dict[str, Any]:
    specification = pair[direction]
    rule = int(pair["rule"])
    initial = wc._unpack_state_hex(specification["initial_hex"], (32, 32))
    original_history = wc._simulate_history(initial, rule, 64)
    history = original_history[:49]
    stored: np.ndarray | None = None
    generation_rows: list[dict[str, Any]] = []
    shape_bits = int(model["shape_bits"])
    original_direction = tuple(int(v) for v in specification["displacement_yx"])
    diagonal = all(abs(float(value)) > 1e-6 for value in original_direction)
    for generation in range(1, generations + 1):
        if oracle:
            shape_code, orientation = cn._oracle_motion_code(
                model, original_history, specification, rule
            )
        else:
            shape_code, orientation = cn._predict_motion_code(model, history)
        written = lm._bits_for_code(shape_code, orientation, shape_bits)
        if generation == 1 or condition not in ("no_renewal", "write_disabled"):
            stored = written.copy()
        if stored is None:
            stored = np.zeros_like(written)
        incoming = stored.copy()
        active = True
        if condition in ("zero", "read_disabled"):
            incoming.fill(0)
            active = False
        elif condition == "shuffle":
            rng = np.random.default_rng(
                ar._hash_seed(
                    "stage6o-motion-shuffle",
                    pair["pair_id"],
                    direction,
                    generation,
                )
            )
            incoming = incoming[rng.permutation(len(incoming))]
        elif condition == "shape_only":
            incoming[shape_bits:] = 0
        elif condition == "polarity_only":
            incoming[:shape_bits] = 0
        elif condition == "opposite_polarity":
            incoming[shape_bits:] = lm._bits_for_code(
                0, lm._opposite_orientation(orientation, diagonal), 0
            )
        elif condition in ("matching_rescue", "opposite_rescue") and generation == 2:
            incoming.fill(0)
            active = False
        elif condition == "matching_rescue" and generation == 3:
            incoming = lm._bits_for_code(shape_code, orientation, shape_bits)
        elif condition == "opposite_rescue" and generation == 3:
            incoming = lm._bits_for_code(
                shape_code,
                lm._opposite_orientation(orientation, diagonal),
                shape_bits,
            )
        elif condition in ("no_renewal", "write_disabled") and generation > 1:
            incoming.fill(0)
            active = False
        elif condition == "ablation" and generation >= 3:
            incoming.fill(0)
            active = False
        copied, exact = lm._bit_codec_roundtrip(
            incoming,
            ar._hash_seed(
                "stage6o-motion-copy",
                pair["pair_id"],
                direction,
                condition,
                generation,
            ),
        )
        decoded_shape, decoded_orientation = lm._code_from_bits(
            copied, shape_bits
        )
        patch = cn._decode_motion_code(
            model, decoded_shape, decoded_orientation, rule
        )
        if not active or condition == "polarity_only":
            patch = np.zeros_like(patch)
        center = (16, 16)
        if condition == "translation_scrub":
            rng = np.random.default_rng(
                ar._hash_seed(
                    "stage6o-motion-translation",
                    pair["pair_id"],
                    direction,
                    generation,
                )
            )
            center = (int(rng.integers(8, 25)), int(rng.integers(8, 25)))
        reset = lm._install_motion_patch_at(patch, center)
        phase_advance = 0
        if condition == "phase_scrub":
            phase_advance = int(
                ar._hash_seed(
                    "stage6o-motion-phase",
                    pair["pair_id"],
                    direction,
                    generation,
                )
                % max(1, int(specification["period"]))
            )
            if phase_advance:
                reset = wc._simulate_history(reset, rule, phase_advance)[-1]
        new_history = wc._simulate_history(reset, rule, 48)
        instructed = original_direction
        if condition == "opposite_polarity" or (
            condition == "opposite_rescue" and generation == 3
        ):
            instructed = (-original_direction[0], -original_direction[1])
        metrics = _counterfactual_motion_metrics(
            new_history, original_history, instructed, original_direction
        )
        generation_rows.append(
            {
                "generation": generation,
                "visible_reset_zero_before_carrier_read": True,
                "payload_bits": len(incoming),
                "copy_exact": exact,
                "phase_advance": phase_advance,
                "translation_center": list(center),
                "instructed_displacement_yx": list(instructed),
                "original_displacement_yx": list(original_direction),
                **metrics,
            }
        )
        history = new_history
    return {
        "condition": condition,
        "direction": direction,
        "oracle": oracle,
        "generations": generation_rows,
        "final_form_success": bool(generation_rows[-1]["form_success"]),
        "final_correct_instruction_direction": bool(
            generation_rows[-1]["correct_instruction_direction"]
        ),
        "all_boundaries_visibly_reset": True,
        "daughter_rewrites_from_visible_history": bool(
            not oracle and condition not in ("write_disabled", "no_renewal")
        ),
    }


def _motion_recovery(
    pair_rows: Sequence[dict[str, Any]], condition: str, generation: int
) -> dict[str, float]:
    selected = [
        result["generations"][generation - 1]
        for row in pair_rows
        for key, result in row["conditions"].items()
        if key.endswith(f":{condition}") and len(result["generations"]) >= generation
    ]
    if not selected:
        return {
            "mover_detection_fraction": 0.0,
            "form_success_fraction": 0.0,
            "instruction_direction_fraction": 0.0,
            "joint_success_fraction": 0.0,
            "foreground_f1_mean": 0.0,
            "instruction_direction_similarity_mean": 0.0,
            "signed_original_direction_similarity_mean": 0.0,
        }
    return {
        "mover_detection_fraction": float(
            np.mean([row["mover_detected"] for row in selected])
        ),
        "form_success_fraction": float(
            np.mean([row["form_success"] for row in selected])
        ),
        "instruction_direction_fraction": float(
            np.mean([row["correct_instruction_direction"] for row in selected])
        ),
        "joint_success_fraction": float(
            np.mean(
                [
                    row["form_success"] and row["correct_instruction_direction"]
                    for row in selected
                ]
            )
        ),
        "foreground_f1_mean": float(
            np.mean([row["foreground_f1"] for row in selected])
        ),
        "instruction_direction_similarity_mean": float(
            np.mean([row["instruction_direction_similarity"] for row in selected])
        ),
        "signed_original_direction_similarity_mean": float(
            np.mean(
                [row["signed_original_direction_similarity"] for row in selected]
            )
        ),
    }


def _motion_oracle_gate(
    summaries: dict[str, dict[str, float]],
    payload_bits: int,
    contract: CounterfactualCarrierContract,
) -> tuple[bool, dict[str, float]]:
    intact1 = summaries["intact_generation1"]
    intact4 = summaries["intact_generation4"]
    zero4 = summaries["zero_generation4"]
    opposite4 = summaries["opposite_polarity_generation4"]
    matching3 = summaries["matching_rescue_generation3"]
    opposite3 = summaries["opposite_rescue_generation3"]
    signed_contrast = (
        matching3["signed_original_direction_similarity_mean"]
        - opposite3["signed_original_direction_similarity_mean"]
    )
    worst_form = min(
        intact1["foreground_f1_mean"],
        intact4["foreground_f1_mean"],
        opposite4["foreground_f1_mean"],
        matching3["foreground_f1_mean"],
        opposite3["foreground_f1_mean"],
    )
    worst_instruction = min(
        intact1["instruction_direction_fraction"],
        intact4["instruction_direction_fraction"],
        opposite4["instruction_direction_fraction"],
        matching3["instruction_direction_fraction"],
        opposite3["instruction_direction_fraction"],
    )
    gate = bool(
        payload_bits <= 8
        and intact1["foreground_f1_mean"]
        >= contract.motion_foreground_f1_minimum
        and intact1["instruction_direction_fraction"]
        >= contract.motion_generation1_minimum
        and intact4["foreground_f1_mean"]
        >= contract.motion_foreground_f1_minimum
        and intact4["instruction_direction_fraction"]
        >= contract.motion_generation4_minimum
        and opposite4["foreground_f1_mean"]
        >= contract.motion_foreground_f1_minimum
        and opposite4["instruction_direction_fraction"]
        >= contract.motion_generation4_minimum
        and matching3["foreground_f1_mean"]
        >= contract.motion_foreground_f1_minimum
        and matching3["instruction_direction_fraction"]
        >= contract.motion_generation1_minimum
        and opposite3["foreground_f1_mean"]
        >= contract.motion_foreground_f1_minimum
        and opposite3["instruction_direction_fraction"]
        >= contract.motion_generation1_minimum
        and signed_contrast
        >= contract.motion_rescue_direction_contrast_minimum
        and zero4["mover_detection_fraction"] <= contract.metric_null_maximum
    )
    return gate, {
        "signed_rescue_direction_contrast": float(signed_contrast),
        "worst_required_foreground_f1": float(worst_form),
        "worst_required_instruction_recovery": float(worst_instruction),
    }


def _load_stage6n_motion_fits(
    stage6n_root: Path,
    profile: CounterfactualCarrierProfile,
) -> list[dict[str, Any]]:
    fits: list[dict[str, Any]] = []
    root = stage6n_root / "stage6n/motion-medoid-fit/checkpoints"
    for family in ("global-medoid", "rule-conditioned-medoid"):
        for count in profile.motion_codebook_sizes:
            path = root / f"{family}-k{count}.json"
            payload = _load_json(path)
            if payload.get("design_digest") != PARENT_STAGE6N_DIGEST:
                raise ValueError(f"Stage-6N motion model digest mismatch: {path}")
            fits.append(payload["fitted"])
    return fits


def _run_motion_oracle(
    stage_root: Path,
    stage6n_root: Path,
    development_pairs: Sequence[dict[str, Any]],
    profile_name: str,
    profile: CounterfactualCarrierProfile,
    contract: CounterfactualCarrierContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    root = stage_root / "motion-counterfactual-oracle"
    root.mkdir(parents=True, exist_ok=True)
    fits = _load_stage6n_motion_fits(stage6n_root, profile)
    conditions = (
        "intact",
        "zero",
        "opposite_polarity",
        "matching_rescue",
        "opposite_rescue",
    )
    oracle_pairs = list(development_pairs[: profile.motion_oracle_pairs])
    candidate_summaries: dict[str, Any] = {}
    qualified: list[tuple[float, int, str, dict[str, Any]]] = []
    for model_index, fitted in enumerate(fits, start=1):
        if time.time() >= deadline:
            break
        model = fitted["model"]
        path = root / f"{model['model_id']}.json"
        if resume and path.exists():
            pair_rows = _load_json(path)["pair_rows"]
        else:
            pair_rows = []
            for pair_index, pair in enumerate(oracle_pairs, start=1):
                if time.time() >= deadline:
                    break
                results = {
                    f"{direction}:{condition}": _motion_lineage(
                        model,
                        pair,
                        direction,
                        condition,
                        oracle=True,
                    )
                    for direction in ("forward", "opposite")
                    for condition in conditions
                }
                pair_rows.append(
                    {
                        "pair_id": pair["pair_id"],
                        "rule": pair["rule"],
                        "conditions": results,
                    }
                )
                status(
                    "running",
                    "corrected-motion-oracle-trajectories",
                    completed=(model_index - 1) * len(oracle_pairs) + pair_index,
                    total=len(fits) * len(oracle_pairs),
                    model_id=model["model_id"],
                )
            ar._atomic_json(
                path,
                {
                    "design_digest": design_digest,
                    "model_digest": model["model_digest"],
                    "pair_rows": pair_rows,
                },
            )
        summaries = {
            "intact_generation1": _motion_recovery(pair_rows, "intact", 1),
            "intact_generation4": _motion_recovery(pair_rows, "intact", 4),
            "zero_generation4": _motion_recovery(pair_rows, "zero", 4),
            "opposite_polarity_generation4": _motion_recovery(
                pair_rows, "opposite_polarity", 4
            ),
            "matching_rescue_generation3": _motion_recovery(
                pair_rows, "matching_rescue", 3
            ),
            "opposite_rescue_generation3": _motion_recovery(
                pair_rows, "opposite_rescue", 3
            ),
        }
        gate, diagnostics = _motion_oracle_gate(
            summaries, int(model["payload_bits"]), contract
        )
        if profile_name == "smoke":
            gate = len(pair_rows) == len(oracle_pairs)
        selection_score = float(
            0.55 * diagnostics["worst_required_foreground_f1"]
            + 0.35 * diagnostics["worst_required_instruction_recovery"]
            + 0.10
            * min(1.0, diagnostics["signed_rescue_direction_contrast"] / 2.0)
        )
        candidate_summaries[model["model_id"]] = {
            "model_digest": model["model_digest"],
            "decoder_family": model["decoder_family"],
            "payload_bits": model["payload_bits"],
            "cross_validation": fitted["cross_validation"],
            **summaries,
            **diagnostics,
            "selection_score": selection_score,
            "stage_gate": gate,
        }
        if gate:
            qualified.append(
                (
                    selection_score,
                    -int(model["payload_bits"]),
                    str(model["model_id"]),
                    fitted,
                )
            )
    qualified.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    selected = qualified[0][3] if qualified else None
    complete = len(candidate_summaries) == len(fits)
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and selected is not None),
        "registered_model_count": len(fits),
        "completed_model_count": len(candidate_summaries),
        "candidate_summaries": candidate_summaries,
        "qualified_model_ids": [row[2] for row in qualified],
        "selected_model_id": selected["model"]["model_id"] if selected else None,
        "selected_model_digest": (
            selected["model"]["model_digest"] if selected else None
        ),
        "oracle_target_access": True,
        "oracle_promotable": False,
        "instruction_and_original_direction_scored_separately": True,
        "d4_applied_to_form_only": True,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result, selected


def _fresh_motion_validation_bank(
    stage_root: Path,
    stage6n_root: Path,
    stage6m_root: Path,
    stage6l_root: Path,
    profile_name: str,
    profile: CounterfactualCarrierProfile,
    contract: CounterfactualCarrierContract,
    *,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    path = stage_root / "MOTION_VALIDATION_BANK.json"
    if path.exists():
        return _load_json(path)
    exposed_m = _load_json(stage6m_root / "stage6m/MOTION_BANK.json")
    if profile_name == "smoke":
        pairs = list(exposed_m.get("pairs", []))[: profile.motion_validation_pairs]
        result = {
            "state": "complete",
            "stage_gate": len(pairs) == profile.motion_validation_pairs,
            "pairs": pairs,
            "validation_pair_count": len(pairs),
            "role": "smoke-exposed-only",
            "scientific_holdout": False,
            "frozen_before_corrected_model_selection": True,
            "final_audit_trajectory_state": "untouched",
        }
        ar._atomic_json(path, result)
        return result
    excluded_hex = {
        str(specification["initial_hex"])
        for pair in exposed_m.get("pairs", [])
        for specification in (pair["forward"], pair["opposite"])
    }
    exposed_l = _load_json(stage6l_root / "stage6l/MOTION_BANK.json")
    excluded_hex.update(
        str(specification["initial_hex"])
        for pair in exposed_l.get("pairs", [])
        for specification in (pair["forward"], pair["opposite"])
    )
    stage6k_root = Path(_load_json(stage6l_root / "DESIGN.json")["stage6k_root"])
    exposed_k = _load_json(stage6k_root / "stage6k/MOVER_PANEL.json")
    excluded_hex.update(
        str(specification["initial_hex"])
        for pair in exposed_k.get("pairs", [])
        for specification in (pair["forward"], pair["opposite"])
    )
    old_bank = stage6n_root / "stage6n/MOTION_VALIDATION_BANK.json"
    if old_bank.exists():
        exposed_n = _load_json(old_bank)
        excluded_hex.update(
            str(specification["initial_hex"])
            for pair in exposed_n.get("pairs", [])
            for specification in (pair["forward"], pair["opposite"])
        )
    discoveries: list[dict[str, Any]] = []
    per_rule: dict[str, Any] = {}
    for index, rule in enumerate(wc.MOVER_RULES, start=1):
        if time.time() >= deadline:
            break
        rows = il._scan_motion_rule(
            rule, profile.motion_scan_per_rule, contract.namespace
        )
        fresh: list[dict[str, Any]] = []
        for row in rows:
            if str(row["initial_hex"]) in excluded_hex:
                continue
            copied = dict(row)
            copied["mover_id"] = str(row["mover_id"]).replace(
                "stage6l-", "stage6o-"
            )
            copied["source"] = "stage6o-fresh-deterministic-5x5-scan"
            fresh.append(copied)
        discoveries.extend(fresh)
        per_rule[str(rule)] = {
            "notation": life_rule_notation(rule),
            "scanned": profile.motion_scan_per_rule,
            "fresh_detected": len(fresh),
        }
        status(
            "running",
            "allocate-stage6o-motion-validation-bank",
            completed=index,
            total=len(wc.MOVER_RULES),
            fresh_discoveries=len(discoveries),
        )
    ordered = sorted(
        discoveries,
        key=lambda row: (
            ar._hash_seed(contract.namespace, "motion-holdout", row["mover_id"]),
            row["mover_id"],
        ),
    )
    pairs: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in ordered:
        key = (
            int(row["rule"]),
            int(row["period"]),
            tuple(row["displacement_yx"]),
            str(row["initial_hex"]),
        )
        if key in seen:
            continue
        pair = wc._discovered_pair(row)
        if pair is None:
            continue
        seen.add(key)
        pairs.append(pair)
        if len(pairs) >= profile.motion_validation_pairs:
            break
    complete = bool(
        len(pairs) == profile.motion_validation_pairs
        and len(per_rule) == len(wc.MOVER_RULES)
    )
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": complete,
        "rules": per_rule,
        "pairs": pairs,
        "validation_pair_count": len(pairs),
        "scientific_holdout": True,
        "frozen_before_corrected_model_selection": True,
        "d4_families_not_split": True,
        "stage6k_through_stage6n_initial_states_excluded": True,
        "allocation_digest": _digest([pair["pair_id"] for pair in pairs]),
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(path, result)
    return result


def _run_motion_validation(
    stage_root: Path,
    fitted: dict[str, Any] | None,
    bank: dict[str, Any],
    profile_name: str,
    contract: CounterfactualCarrierContract,
    design_digest: str,
    *,
    resume: bool,
    deadline: float,
    status: Any,
) -> dict[str, Any]:
    if fitted is None:
        return _empty("no symmetry-aware motion oracle qualifier")
    model = fitted["model"]
    conditions = (
        "intact",
        "phase_scrub",
        "translation_scrub",
        "zero",
        "shuffle",
        "shape_only",
        "polarity_only",
        "opposite_polarity",
        "read_disabled",
        "write_disabled",
        "no_renewal",
        "ablation",
        "matching_rescue",
        "opposite_rescue",
    )
    root = stage_root / "motion-renewal-validation"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    pairs = list(bank.get("pairs", []))
    pair_rows: list[dict[str, Any]] = []
    for index, pair in enumerate(pairs, start=1):
        path = checkpoints / f"{pair['pair_id']}.json"
        if resume and path.exists():
            row = _load_json(path)["row"]
        else:
            if time.time() >= deadline:
                break
            results = {
                f"{direction}:{condition}": _motion_lineage(
                    model,
                    pair,
                    direction,
                    condition,
                    oracle=False,
                )
                for direction in ("forward", "opposite")
                for condition in conditions
            }
            row = {
                "pair_id": pair["pair_id"],
                "rule": pair["rule"],
                "conditions": results,
            }
            ar._atomic_json(path, {"design_digest": design_digest, "row": row})
        pair_rows.append(row)
        status(
            "running",
            "validate-symmetry-aware-motion-renewal",
            completed=index,
            total=len(pairs),
            payload_bits=model["payload_bits"],
        )
    complete = bool(len(pair_rows) == len(pairs) and bank.get("stage_gate"))
    recovery = {
        condition: {
            "generation1": _motion_recovery(pair_rows, condition, 1),
            "generation3": _motion_recovery(pair_rows, condition, 3),
            "generation4": _motion_recovery(pair_rows, condition, 4),
        }
        for condition in conditions
    }
    required = {
        "intact_generation1": recovery["intact"]["generation1"],
        "intact_generation4": recovery["intact"]["generation4"],
        "zero_generation4": recovery["zero"]["generation4"],
        "opposite_polarity_generation4": recovery["opposite_polarity"][
            "generation4"
        ],
        "matching_rescue_generation3": recovery["matching_rescue"][
            "generation3"
        ],
        "opposite_rescue_generation3": recovery["opposite_rescue"][
            "generation3"
        ],
    }
    causal_gate, diagnostics = _motion_oracle_gate(
        required, int(model["payload_bits"]), contract
    )
    phase4 = recovery["phase_scrub"]["generation4"]
    translation4 = recovery["translation_scrub"]["generation4"]
    null_conditions = (
        "zero",
        "read_disabled",
        "write_disabled",
        "no_renewal",
        "ablation",
    )
    null_maximum = max(
        recovery[condition]["generation4"]["mover_detection_fraction"]
        for condition in null_conditions
    )
    intact4 = recovery["intact"]["generation4"]
    no_renewal4 = recovery["no_renewal"]["generation4"]
    renewal_advantage = (
        intact4["joint_success_fraction"]
        - no_renewal4["joint_success_fraction"]
    )
    invariance_gate = bool(
        phase4["foreground_f1_mean"] >= contract.motion_foreground_f1_minimum
        and phase4["instruction_direction_fraction"]
        >= contract.motion_generation4_minimum
        and translation4["foreground_f1_mean"]
        >= contract.motion_foreground_f1_minimum
        and translation4["instruction_direction_fraction"]
        >= contract.motion_generation4_minimum
    )
    renewal_gate = bool(
        renewal_advantage >= contract.compact_control_advantage_minimum
        and null_maximum <= contract.metric_null_maximum
    )
    gate = bool(complete and causal_gate and invariance_gate and renewal_gate)
    if profile_name == "smoke":
        gate = complete
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": gate,
        "validation_pair_count": len(pair_rows),
        "selected_model_id": model["model_id"],
        "selected_model_digest": model["model_digest"],
        "decoder_family": model["decoder_family"],
        "meaningful_payload_bits": model["payload_bits"],
        "recovery": recovery,
        **diagnostics,
        "maximum_null_mover_detection": float(null_maximum),
        "active_renewal_joint_advantage": float(renewal_advantage),
        "counterfactual_causal_gate": causal_gate,
        "phase_translation_invariance_gate": invariance_gate,
        "active_renewal_gate": renewal_gate,
        "foreground_background_excluded": True,
        "form_scored_modulo_d4": True,
        "direction_never_symmetry_aligned": True,
        "shape_and_polarity_heads_separate": True,
        "literal_occupancy_payload_removed": True,
        "visible_reset_every_boundary": True,
        "pair_results": pair_rows,
        "final_audit_trajectory_state": "untouched",
    }
    ar._atomic_json(root / "RESULTS.json", result)
    return result


def _pair_block_bootstrap_interval(
    rows: Sequence[dict[str, Any]],
    candidate_id: str,
    condition: str,
    generation: int,
    resamples: int,
    seed: int,
) -> list[float]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        if row.get("candidate_id") != candidate_id:
            continue
        try:
            value = row["conditions"][condition]["texture_history"][
                str(generation)
            ]["post_washout_match_mean"]
        except KeyError:
            continue
        grouped.setdefault(str(row.get("pair_id", row.get("checkpoint"))), []).append(
            float(value)
        )
    pair_means = np.asarray(
        [np.mean(values) for values in grouped.values()], dtype=np.float64
    )
    if len(pair_means) == 0:
        return [0.0, 0.0]
    rng = np.random.default_rng(seed)
    draws = np.empty(max(1, int(resamples)), dtype=np.float64)
    for index in range(len(draws)):
        sample = pair_means[rng.integers(0, len(pair_means), len(pair_means))]
        draws[index] = float(np.mean(sample))
    return [float(v) for v in np.quantile(draws, (0.025, 0.975))]


def _run_compact_confirmation(
    stage_root: Path,
    stage6n_root: Path,
    source: dict[str, Any],
    pairs: Sequence[dict[str, Any]],
    profile_name: str,
    profile: CounterfactualCarrierProfile,
    templates: list[dict[str, Any]],
    frozen: dict[str, Any],
    writer_contract: ar.MotifContract,
    contract: CounterfactualCarrierContract,
    design_digest: str,
    *,
    workers: int,
    resume: bool,
    deadline: float,
    status: Any,
) -> tuple[dict[str, Any], list[int]]:
    models: dict[int, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    for dimension in profile.compact_dimensions:
        payload = _load_json(
            stage6n_root / f"stage6n/compact-oracle/rank-{dimension:02d}.json"
        )
        if payload.get("design_digest") != PARENT_STAGE6N_DIGEST:
            raise ValueError(f"Stage-6N compact rank {dimension} digest mismatch")
        model = payload["fitted"]["model"]
        models[dimension] = model
        candidates.append(
            cn._compact_candidate(
                source,
                model,
                suffix=f"stage6o-independent-confirm-r{dimension}",
                oracle=True,
            )
        )
    start = profile.compact_confirmation_start
    confirmation_pairs = list(pairs[start : start + profile.compact_confirmation_pairs])
    conditions = (
        "inherited_field_zero",
        "inherited_field_shuffle",
        "inherited_field_coefficient_shuffle",
        "inherited_field_read_disabled",
        "inherited_field_write_disabled",
        "inherited_field_no_renewal",
        "inherited_field_one_bin_damage",
        "inherited_field_copy_noise_5",
        "inherited_field_same_rescue",
        "inherited_field_opposite_rescue",
    )
    items = ar._make_items(
        confirmation_pairs,
        candidates,
        ar._template_pairs(templates, "development"),
        frozen["stage4"]["configuration"],
        phase="stage6o-independent-compact-confirmation",
        replicates=profile.trace_replicates,
        generations=8,
        conditions=("intact", *conditions),
        analysis_kind="stage6o-nonpromotable-compact-confirmation",
    )
    rows, complete = ar._run_json_checkpoints(
        stage_root,
        "compact-confirmation-trajectories",
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
    passing: list[int] = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        dimension = int(candidate["closure_model"]["latent_size"])
        intact = cn._metric_mean(
            rows, candidate_id, "intact", "post_washout_match_mean", 8
        )
        controls = {
            condition: cn._metric_mean(
                rows,
                candidate_id,
                condition,
                "post_washout_match_mean",
                8,
            )
            for condition in (
                "inherited_field_zero",
                "inherited_field_shuffle",
                "inherited_field_coefficient_shuffle",
                "inherited_field_read_disabled",
                "inherited_field_no_renewal",
            )
        }
        matching = cn._metric_mean(
            rows,
            candidate_id,
            "inherited_field_same_rescue",
            "post_washout_match_mean",
            6,
        )
        opposite = cn._metric_mean(
            rows,
            candidate_id,
            "inherited_field_opposite_rescue",
            "post_washout_match_mean",
            6,
        )
        minimum_advantage = min(
            (intact - value for value in controls.values()), default=-1.0
        )
        gate = bool(
            complete
            and intact >= contract.compact_recovery_minimum
            and minimum_advantage >= contract.compact_control_advantage_minimum
            and matching - opposite
            >= contract.compact_control_advantage_minimum
        )
        if profile_name == "smoke":
            gate = complete
        if gate:
            passing.append(dimension)
        summaries[str(dimension)] = {
            "candidate_id": candidate_id,
            "latent_size": dimension,
            "confirmation_pair_count": len(confirmation_pairs),
            "new_trajectory_namespace": True,
            "intact_generation8_post_washout": intact,
            "intact_pair_block_bootstrap_95": _pair_block_bootstrap_interval(
                rows,
                candidate_id,
                "intact",
                8,
                profile.bootstrap_resamples,
                ar._hash_seed(contract.namespace, "compact-bootstrap", dimension),
            ),
            "controls_generation8": controls,
            "minimum_intact_control_advantage": minimum_advantage,
            "matching_rescue_generation6": matching,
            "opposite_rescue_generation6": opposite,
            "matching_minus_opposite_rescue": matching - opposite,
            "stage_gate": gate,
        }
    result = {
        "state": "complete" if complete else "budget_truncated",
        "stage_gate": bool(complete and passing),
        "registered_dimensions": list(profile.compact_dimensions),
        "qualified_dimensions": sorted(passing),
        "candidate_summaries": summaries,
        "confirmation_pair_ids": [pair["pair_id"] for pair in confirmation_pairs],
        "confirmation_pair_ids_sha256": _digest(
            [pair["pair_id"] for pair in confirmation_pairs]
        ),
        "stage6n_oracle_pairs_excluded": profile_name == "reference",
        "decoder_fit_exposure_disclosed": True,
        "causal_reliability_not_model_generality": True,
        "threshold_lowered": False,
        "completed_trajectories": len(rows),
        "registered_trajectories": len(items),
        "oracle_target_access": True,
        "oracle_promotable": False,
        "final_audit_trajectory_state": "untouched",
    }
    return result, sorted(passing)[:2]


def _parent_integrity(
    stage6n_root: Path = DEFAULT_STAGE6N_ROOT,
    stage6m_root: Path = DEFAULT_STAGE6M_ROOT,
    stage6l_root: Path = DEFAULT_STAGE6L_ROOT,
) -> dict[str, Any]:
    required = (
        "DESIGN.json",
        "RESULTS.json",
        "STATUS.json",
        "MANIFEST.json",
        "STAGE_DECISION.json",
        "stage6n/COHORTS.json",
        "stage6n/compact-oracle/rank-04.json",
        "stage6n/compact-oracle/rank-16.json",
        "COMPLETE",
    )
    required += tuple(
        f"stage6n/motion-medoid-fit/checkpoints/{family}-k{count}.json"
        for family in ("global-medoid", "rule-conditioned-medoid")
        for count in (2, 4, 8, 16, 32)
    )
    missing = [str(stage6n_root / name) for name in required if not (stage6n_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen Stage-6N artifacts: {missing}")
    result = _load_json(stage6n_root / "RESULTS.json")
    status = _load_json(stage6n_root / "STATUS.json")
    if result.get("state") != "complete" or status.get("state") != "complete":
        raise ValueError("Stage-6O requires a complete Stage-6N parent")
    if result.get("design_digest") != PARENT_STAGE6N_DIGEST:
        raise ValueError("Stage-6O parent Stage-6N design is not the frozen run")
    if result.get("verdict") != "NO_CAUSAL_COMPACT_OR_ABSTRACT_CARRIER":
        raise ValueError("Stage-6O requires the registered Stage-6N boundary")
    if result.get("final_audit_trajectory_state") != "untouched":
        raise ValueError("Stage-6N final reserve was touched")
    design = _load_json(stage6n_root / "DESIGN.json")
    expected_impl = design.get("implementation_hashes", {}).get(
        "motif_causal_attractor.py"
    )
    if expected_impl != ar._sha256(Path(cn.__file__)):
        raise ValueError("Stage-6N implementation changed after the frozen run")
    ancestry = cn._parent_integrity(stage6m_root, stage6l_root)
    return {
        "state": "complete",
        "stage_gate": True,
        "parent_verdict": result["verdict"],
        "parent_design_digest": result["design_digest"],
        "parent_result_sha256": ar._sha256(stage6n_root / "RESULTS.json"),
        "stage6n_required_hashes": {
            name: ar._sha256(stage6n_root / name) for name in required
        },
        "procedural_pair_ids_sha256": ancestry["procedural_pair_ids_sha256"],
        "procedural_trajectories_sealed": True,
        "final_pair_count": 62,
        "final_pair_ids_sha256": ancestry["final_pair_ids_sha256"],
        "final_audit_trajectory_state": "untouched",
    }


def _prepare_campaign(
    output: Path,
    profile_name: str,
    stage6n_root: Path,
    stage6m_root: Path,
    stage6l_root: Path,
    max_hours: float,
    *,
    resume: bool,
) -> tuple[
    CounterfactualCarrierContract,
    CounterfactualCarrierProfile,
    dict[str, Any],
    str,
    dict[str, Any],
]:
    contract = CounterfactualCarrierContract()
    profile = PROFILES[profile_name]
    integrity = _parent_integrity(stage6n_root, stage6m_root, stage6l_root)
    design = {
        "experiment": "ca_motif_counterfactual_carrier_stage_6o",
        "prospective_followup_to": PARENT_STAGE6N_DIGEST,
        "stage6n_verdict_immutable": True,
        "contract": contract.to_dict(),
        "profile_name": profile_name,
        "profile": asdict(profile),
        "stage6n_root": str(stage6n_root.resolve()),
        "stage6m_root": str(stage6m_root.resolve()),
        "stage6l_root": str(stage6l_root.resolve()),
        "stage6n_required_hashes": integrity["stage6n_required_hashes"],
        "registered_phases": PHASES,
        "compact_confirmation": {
            "dimensions": profile.compact_dimensions,
            "pair_slice": (
                profile.compact_confirmation_start,
                profile.compact_confirmation_start
                + profile.compact_confirmation_pairs,
            ),
            "threshold_lowered": False,
            "claim": "causal-reliability-not-model-generality",
        },
        "motion_correction": {
            "form_alignment": "phase-translation-D4",
            "direction_alignment": "none",
            "instruction_score": "relative-to-carrier-command",
            "causal_contrast": "signed-relative-to-original-direction",
            "validation_frozen_before_model_selection": True,
        },
        "cohort_route": {
            "compact_confirmation": "exposed development pairs excluded from Stage-6N compact oracle",
            "compact_validation": "16 sealed Stage-6M procedural pairs; conditional",
            "motion_development": "exposed Stage-6M mover bank",
            "motion_validation": "fresh Stage-6O deterministic namespace",
            "final": "62-pair protected reserve unreachable",
        },
        "compute": {
            "hard_hours": max_hours,
            "exploration_cutoff_hours": min(
                max_hours, contract.exploration_stop_hours
            ),
            "worker_cap": 4,
            "detached_and_resumable": True,
        },
        "protocol_sha256": ar._sha256(PROTOCOL_PATH),
        "implementation_hashes": {
            "motif_counterfactual_carrier.py": ar._sha256(Path(__file__)),
            "motif_causal_attractor.py": ar._sha256(Path(cn.__file__)),
            "motif_latent_regeneration.py": ar._sha256(Path(lm.__file__)),
            "motif_phenotype_bridge.py": ar._sha256(Path(pb.__file__)),
        },
    }
    design_digest = _digest(design)
    design["design_digest"] = design_digest
    design_path = output / "DESIGN.json"
    if resume and design_path.exists():
        if _load_json(design_path).get("design_digest") != design_digest:
            raise ValueError("Stage-6O resume design changed")
    else:
        ar._atomic_json(design_path, design)
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
            "parent_sha256": integrity["parent_result_sha256"],
            "stage6n_result_reinterpreted": False,
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
        payload = {
            "experiment": "ca_motif_counterfactual_carrier_stage_6o",
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
            "hard_deadline_unix": float(campaign["hard_deadline_unix"]),
            "remaining_seconds": max(
                0.0, float(campaign["hard_deadline_unix"]) - now
            ),
            "final_audit_trajectory_state": "untouched",
            **extra,
        }
        if (
            "eta_seconds" not in extra
            and int(extra.get("completed", 0)) > 0
            and "total" in extra
        ):
            rate = payload["elapsed_seconds"] / int(extra["completed"])
            payload["eta_seconds"] = max(
                0.0,
                rate * (int(extra["total"]) - int(extra["completed"])),
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
        "experiment": "ca_motif_counterfactual_carrier_stage_6o",
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


def _reconstruct_context(
    stage_root: Path,
    profile_name: str,
    profile: CounterfactualCarrierProfile,
    design_digest: str,
    integrity: dict[str, Any],
    stage6l_root: Path,
    stage6k_root: Path,
    stage6j_root: Path,
    stage6i_root: Path,
    stage6h_root: Path,
    stage6br_root: Path,
    roots: dict[str, Path],
) -> tuple[
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    list[dict[str, Any]],
    ar.MotifContract,
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    ancestry = il._parent_integrity(stage6k_root, stage6j_root, stage6i_root, stage6h_root)
    causal_profile = profile.causal_profile()
    frozen, cohorts, _, writer_contract, templates = il._reconstruct_cohorts(
        stage_root,
        profile_name,
        il.InverseDistillationProfile(
            causal_profile.development_pairs,
            causal_profile.procedural_validation_pairs,
            causal_profile.trace_replicates,
            causal_profile.validation_replicates,
            causal_profile.rollout_rounds,
            causal_profile.maximum_frozen_writers,
            causal_profile.motion_scan_per_rule,
            causal_profile.motion_development_pairs,
            causal_profile.motion_validation_pairs,
            causal_profile.bootstrap_resamples,
        ),
        ancestry,
        stage6j_root,
        stage6i_root,
        stage6h_root,
        roots,
    )
    ledger_path = stage_root / "COHORTS.json"
    cohort_ledger = _load_json(ledger_path)
    if profile_name == "reference":
        if (
            cohort_ledger["procedural_pair_ids_sha256"]
            != integrity["procedural_pair_ids_sha256"]
        ):
            raise ValueError("Stage-6O procedural identities changed")
    else:
        cohorts["procedural_validation"] = list(
            cohorts["development"][-profile.procedural_validation_pairs :]
        )
        cohort_ledger.update(
            {
                "procedural_validation_role": "smoke-exposed-only",
                "procedural_validation_trajectories_not_simulated_before_freeze": False,
                "scientific_procedural_pair_ids_loaded": False,
            }
        )
        ar._atomic_json(ledger_path, cohort_ledger)
    source = wc._materialize_source_candidate(
        stage_root, stage6h_root, stage6br_root, design_digest
    )
    retained = lm._retained_rows(stage6l_root)
    wanted = {
        str(pair["pair_id"])
        for pair in cohorts["development"][: profile.development_pairs]
    }
    base_rows = [row for row in retained if str(row["pair_id"]) in wanted]
    available = {str(row["pair_id"]) for row in base_rows}
    development_pairs = [
        pair
        for pair in cohorts["development"]
        if str(pair["pair_id"]) in available
    ]
    if len(development_pairs) != profile.development_pairs:
        raise ValueError("Stage-6O retained trace/pair reconstruction mismatch")
    return (
        frozen,
        cohorts,
        templates,
        writer_contract,
        base_rows,
        source,
        development_pairs,
        cohorts["procedural_validation"],
    )


def _run_motion_metric_audit(stage6n_root: Path) -> dict[str, Any]:
    parent = _load_json(stage6n_root / "motion-oracle/RESULTS.json")
    old_rows: dict[str, Any] = {}
    for model_id, summary in parent["candidate_summaries"].items():
        matching = summary["matching_rescue_generation3"]
        opposite = summary["opposite_rescue_generation3"]
        old_rows[model_id] = {
            "old_matching_instruction_accuracy": matching[
                "correct_direction_fraction"
            ],
            "old_opposite_instruction_accuracy": opposite[
                "correct_direction_fraction"
            ],
            "old_subtracted_two_different_instruction_targets": True,
            "prospective_signed_original_contrast_required": True,
        }
    asymmetric = np.zeros((32, 32), dtype=np.bool_)
    asymmetric[13, 14] = True
    asymmetric[14, 14:17] = True
    asymmetric[15, 16] = True
    reflected = il._d4_blocks(asymmetric.astype(np.float32), 4) > 0
    plain = cn._foreground_overlap(reflected, asymmetric)
    aligned = _d4_foreground_overlap(reflected, asymmetric)
    blank = np.zeros((32, 32), dtype=np.bool_)
    blank_score = _d4_foreground_overlap(blank, blank)
    gate = bool(
        aligned["foreground_f1"] == 1.0
        and aligned["foreground_f1"] >= plain["foreground_f1"]
        and blank_score["foreground_f1"] == 0.0
    )
    return {
        "state": "complete",
        "stage_gate": gate,
        "parent_candidate_audit": old_rows,
        "asymmetric_plain_foreground_f1": plain["foreground_f1"],
        "asymmetric_d4_foreground_f1": aligned["foreground_f1"],
        "blank_foreground_f1": blank_score["foreground_f1"],
        "form_symmetry_does_not_transform_velocity": True,
        "parent_verdict_reinterpreted": False,
        "new_trajectories_required": True,
        "final_audit_trajectory_state": "untouched",
    }


def _campaign_result(
    output: Path,
    design_digest: str,
    profile_name: str,
    metric_audit: dict[str, Any],
    motion_oracle: dict[str, Any],
    motion: dict[str, Any],
    compact: dict[str, Any],
    attractor: dict[str, Any],
    contraction: dict[str, Any],
    closed_loop: dict[str, Any],
    narrow: dict[str, Any],
) -> dict[str, Any]:
    motion_gate = bool(motion.get("stage_gate", False))
    narrow_gate = bool(narrow.get("stage_gate", False))
    compact_gate = bool(compact.get("stage_gate", False))
    if profile_name == "smoke":
        verdict = "SMOKE_PATH_VALIDATED"
        scientific_claim = False
    elif motion_gate and narrow_gate:
        verdict = "COUNTERFACTUAL_MOTION_AND_NARROW_ATTRACTOR_PH"
        scientific_claim = True
    elif motion_gate:
        verdict = "SYMMETRY_AWARE_ABSTRACT_MOTION_PH"
        scientific_claim = True
    elif narrow_gate:
        verdict = "CONFIRMED_NARROW_ATTRACTOR_PH_ONLY"
        scientific_claim = True
    elif compact_gate:
        verdict = "COMPACT_CAUSAL_CONTROL_CONFIRMED_ONLY"
        scientific_claim = True
    elif motion_oracle.get("stage_gate", False):
        verdict = "MOTION_COMMAND_CONTROL_ONLY"
        scientific_claim = True
    else:
        verdict = "STAGE6N_LEADS_NOT_CONFIRMED"
        scientific_claim = True
    result = {
        "experiment": "ca_motif_counterfactual_carrier_stage_6o",
        "design_digest": design_digest,
        "profile_name": profile_name,
        "state": "complete",
        "stage_gate": bool(motion_gate or narrow_gate),
        "verdict": verdict,
        "scientific_claim": scientific_claim,
        "motion_metric_audit_gate": bool(metric_audit.get("stage_gate", False)),
        "motion_oracle_gate": bool(motion_oracle.get("stage_gate", False)),
        "abstract_motion_ph_gate": motion_gate,
        "compact_confirmation_gate": compact_gate,
        "compact_attractor_fit_gate": bool(attractor.get("stage_gate", False)),
        "compact_contraction_gate": bool(contraction.get("stage_gate", False)),
        "compact_closed_loop_gate": bool(closed_loop.get("stage_gate", False)),
        "narrow_attractor_ph_gate": narrow_gate,
        "mechanism_level_generality_gate": bool(motion_gate and narrow_gate),
        "selected_motion_model_id": motion_oracle.get("selected_model_id"),
        "qualified_compact_dimensions": compact.get("qualified_dimensions", []),
        "qualified_narrow_candidate_ids": narrow.get(
            "qualified_candidate_ids", []
        ),
        "stage6n_verdict_reinterpreted": False,
        "claim_boundary": (
            "Engineered synthetic CA carriers only. No result implies biology, "
            "human memory, consciousness, or agency."
        ),
        "original_final_reserve_opened": False,
        "final_audit_pair_count": 62,
        "final_audit_trajectory_state": "untouched",
        "phase_results": {
            "motion_metric_audit": metric_audit,
            "motion_oracle": motion_oracle,
            "motion_validation": motion,
            "compact_confirmation": compact,
            "compact_attractor_fit": attractor,
            "compact_contraction": contraction,
            "compact_closed_loop": closed_loop,
            "compact_validation": narrow,
        },
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
            "next_step": (
                "replicate the qualifying carrier under a new rule family"
                if result["stage_gate"]
                else "open no reserve; redesign the first failed causal interface"
            ),
            "final_audit_trajectory_state": "untouched",
        },
    )
    report = (
        "# Stage 6O counterfactual carrier audit and closure\n\n"
        f"Verdict: **{verdict}**.\n\n"
        f"Corrected motion oracle: `{result['motion_oracle_gate']}`; learned "
        f"motion renewal: `{motion_gate}`; compact confirmation: "
        f"`{compact_gate}`; narrow attractor PH: `{narrow_gate}`. Stage 6N "
        "was not reinterpreted, and the protected 62-pair reserve was neither "
        "loaded nor simulated.\n"
    )
    lay = (
        "# Lay summary\n\n"
        "This round asks whether the moving-pattern note really carries two "
        "separable instructions—what object to build and which way it should "
        "move—without mistaking a correctly reversed object for a failure. It "
        "also repeats the two almost-passing compact notes on different "
        "trajectories without lowering the old bar.\n\n"
        f"The registered outcome is **{verdict}**.\n"
    )
    ar._atomic_text(output / "REPORT.md", report)
    ar._atomic_text(output / "LAY_SUMMARY.md", lay)
    ar._atomic_text(output / "COMPLETE", "complete\n")
    return result


def _update_discovery_log(result: dict[str, Any]) -> None:
    if result.get("profile_name") != "reference":
        return
    entry = (
        "\n\n## Stage 6O: counterfactual carrier audit and closure\n\n"
        f"Stage 6O design `{result['design_digest']}` completed with verdict "
        f"**{result['verdict']}**. It prospectively separated instruction "
        "obedience from signed original direction, scored mover form modulo "
        "D4 symmetry, and independently repeated the Stage 6N compact ranks "
        "4 and 16 without lowering their threshold. Stage 6N remained "
        "immutable and the protected 62-pair reserve remained untouched.\n"
    )
    existing = (
        DISCOVERY_LOG.read_text(encoding="utf-8")
        if DISCOVERY_LOG.exists()
        else "# Discovery log\n"
    )
    marker = f"Stage 6O design `{result['design_digest']}`"
    if marker not in existing:
        ar._atomic_text(DISCOVERY_LOG, existing.rstrip() + entry)


def run_motif_counterfactual_carrier(
    output: Path,
    *,
    stage6n_root: Path = DEFAULT_STAGE6N_ROOT,
    stage6m_root: Path = DEFAULT_STAGE6M_ROOT,
    stage6l_root: Path = DEFAULT_STAGE6L_ROOT,
    stage6k_root: Path = il.DEFAULT_STAGE6K_ROOT,
    stage6j_root: Path = il.DEFAULT_STAGE6J_ROOT,
    stage6i_root: Path = il.DEFAULT_STAGE6I_ROOT,
    stage6h_root: Path = il.DEFAULT_STAGE6H_ROOT,
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
    """Run Stage 6O without exposing the protected 62-pair reserve."""

    ar.require_pinned_numpy()
    if profile_name not in PROFILES:
        raise ValueError(f"unknown Stage-6O profile {profile_name!r}")
    if workers < 1 or workers > 4:
        raise ValueError("Stage-6O workers must be in [1, 4]")
    if max_hours <= 0.0 or max_hours > 8.0:
        raise ValueError("Stage-6O max-hours must be in (0, 8]")
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    stage6n_root = stage6n_root.resolve()
    stage6m_root = stage6m_root.resolve()
    stage6l_root = stage6l_root.resolve()
    _parent_integrity(stage6n_root, stage6m_root, stage6l_root)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ar._atomic_text(output / "RUN.pid", f"{os.getpid()}\n")
    stage6k_root = stage6k_root.resolve()
    stage6j_root = stage6j_root.resolve()
    stage6i_root = stage6i_root.resolve()
    stage6h_root = stage6h_root.resolve()
    stage6br_root = stage6br_root.resolve()
    roots = {
        "stage6d_root": stage6d_root.resolve(),
        "stage6c_root": stage6c_root.resolve(),
        "stage6br_root": stage6br_root,
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
            stage6n_root,
            stage6m_root,
            stage6l_root,
            max_hours,
            resume=resume,
        )
        status = _status_writer(output, profile_name, campaign, active, workers)
        status("running", "frozen-stage6n-parent-and-reserves-verified")
        active[0] = "integrity"
        _write_phase(
            output,
            "integrity",
            design_digest,
            integrity | {"next_phase": "allocation"},
            "# Stage 6O integrity\n\nThe completed Stage 6N inputs, near-miss models, mover models, sealed procedural cohort, and untouched final reserve were hash-verified.",
            "# Lay summary\n\nThe earlier result stays unchanged; this follow-up starts from frozen copies of its two leads.",
        )

        stage_root = output / "stage6o"
        (
            frozen,
            cohorts,
            templates,
            writer_contract,
            base_rows,
            source,
            development_pairs,
            procedural_pairs,
        ) = _reconstruct_context(
            stage_root,
            profile_name,
            profile,
            design_digest,
            integrity,
            stage6l_root,
            stage6k_root,
            stage6j_root,
            stage6i_root,
            stage6h_root,
            stage6br_root,
            roots,
        )
        active[0] = "allocation"
        confirmation_pairs = development_pairs[
            profile.compact_confirmation_start :
            profile.compact_confirmation_start + profile.compact_confirmation_pairs
        ]
        motion_bank = _fresh_motion_validation_bank(
            stage_root,
            stage6n_root,
            stage6m_root,
            stage6l_root,
            profile_name,
            profile,
            contract,
            deadline=float(campaign["exploration_deadline_unix"]),
            status=status,
        )
        allocation = {
            "state": "complete" if motion_bank.get("stage_gate") else motion_bank.get("state"),
            "stage_gate": bool(motion_bank.get("stage_gate")),
            "compact_confirmation_pair_count": len(confirmation_pairs),
            "compact_confirmation_pair_ids_sha256": _digest(
                [pair["pair_id"] for pair in confirmation_pairs]
            ),
            "compact_stage6n_oracle_pairs_excluded": profile_name == "reference",
            "motion_validation_pair_count": motion_bank.get("validation_pair_count", 0),
            "motion_validation_allocation_digest": motion_bank.get("allocation_digest"),
            "motion_validation_frozen_before_selection": True,
            "procedural_trajectories_simulated": False,
            "final_audit_trajectory_state": "untouched",
            "next_phase": "motion-metric-audit",
        }
        _write_phase(
            output,
            "allocation",
            design_digest,
            allocation,
            "# Stage 6O allocation\n\nCompact confirmation identities and the fresh mover bank were frozen before corrected model selection.",
            "# Lay summary\n\nThe new exam questions were sealed before choosing which carrier would answer them.",
        )

        active[0] = "motion-metric-audit"
        metric_audit = _run_motion_metric_audit(stage6n_root)
        _write_phase(
            output,
            "motion-metric-audit",
            design_digest,
            metric_audit | {"next_phase": "motion-oracle"},
            "# Stage 6O motion metric audit\n\nForm is now phase/translation/D4 invariant while velocity remains unaligned; instruction and original direction have separate scores.",
            "# Lay summary\n\nTurning a shape around no longer makes it the wrong shape, but moving the wrong way still counts as wrong.",
        )

        exposed_motion = _load_json(stage6m_root / "stage6m/MOTION_BANK.json")
        motion_development = list(exposed_motion.get("pairs", []))[
            : profile.motion_development_pairs
        ]
        active[0] = "motion-oracle"
        if metric_audit.get("stage_gate") and allocation.get("stage_gate"):
            motion_oracle, selected_motion = _run_motion_oracle(
                stage_root,
                stage6n_root,
                motion_development,
                profile_name,
                profile,
                contract,
                design_digest,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                status=status,
            )
        else:
            motion_oracle, selected_motion = (
                _empty("metric audit or prospective allocation failed"),
                None,
            )
        _write_phase(
            output,
            "motion-oracle",
            design_digest,
            motion_oracle | {"next_phase": "motion-writer"},
            "# Stage 6O corrected motion oracle\n\nExact shape and polarity carriers had to preserve form and obey both matching and opposite commands under the corrected metric.",
            "# Lay summary\n\nA perfect note had to build the same kind of object and send it whichever way the arrow said.",
        )

        active[0] = "motion-writer"
        motion_writer = {
            "state": "complete",
            "stage_gate": selected_motion is not None,
            "selected_model_id": (
                selected_motion["model"]["model_id"] if selected_motion else None
            ),
            "selected_model_digest": (
                selected_motion["model"]["model_digest"] if selected_motion else None
            ),
            "model_parameters_refitted_after_stage6n": False,
            "separate_visible_shape_and_polarity_heads": True,
            "runtime_target_access": False,
            "runtime_parent_access": False,
            "runtime_incoming_payload_to_writer": False,
            "final_audit_trajectory_state": "untouched",
            "next_phase": "motion-validation",
        }
        _write_phase(
            output,
            "motion-writer",
            design_digest,
            motion_writer,
            "# Stage 6O frozen motion writer\n\nThe selected Stage 6N visible-spacetime heads were frozen without refitting after corrected oracle selection.",
            "# Lay summary\n\nThe daughter must infer and rewrite the note from what it becomes; it cannot peek at the parent's answer.",
        )

        active[0] = "motion-validation"
        motion = _run_motion_validation(
            stage_root,
            selected_motion,
            motion_bank,
            profile_name,
            contract,
            design_digest,
            resume=resume,
            deadline=float(campaign["hard_deadline_unix"]),
            status=status,
        )
        motion["validation_bank"] = {
            key: value
            for key, value in motion_bank.items()
            if key not in ("pairs", "rules")
        }
        _write_phase(
            output,
            "motion-validation",
            design_digest,
            motion | {"next_phase": "compact-confirmation"},
            "# Stage 6O learned motion renewal\n\nA frozen visible writer faced fresh movers, resets, symmetry scrubs, ablations, no-renewal, and command-specific rescues.",
            "# Lay summary\n\nThe real test is whether unfamiliar daughters keep rewriting the tiny shape-and-arrow note themselves.",
        )

        active[0] = "compact-confirmation"
        compact, dimensions = _run_compact_confirmation(
            stage_root,
            stage6n_root,
            source,
            development_pairs,
            profile_name,
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
            "compact-confirmation",
            design_digest,
            compact | {"next_phase": "compact-attractor-fit"},
            "# Stage 6O compact confirmation\n\nFrozen ranks 4 and 16 repeated the exact causal ladder on a new trajectory slice with the original 0.70 threshold.",
            "# Lay summary\n\nThe two almost-passing short notes took a new exam, with no easier marking.",
        )

        causal_profile = profile.causal_profile()
        active[0] = "compact-attractor-fit"
        if compact.get("stage_gate") and dimensions:
            attractor, selected_specs = cn._run_attractor_fit(
                stage_root,
                base_rows,
                dimensions,
                profile_name,
                causal_profile,
                contract,
                design_digest,
                resume=resume,
                deadline=float(campaign["exploration_deadline_unix"]),
                status=status,
            )
        else:
            attractor, selected_specs = _empty(
                "no compact near-miss passed independent confirmation"
            ), []
        _write_phase(
            output,
            "compact-attractor-fit",
            design_digest,
            attractor | {"next_phase": "compact-contraction"},
            "# Stage 6O compact attractor fit\n\nOnly independently confirmed ranks could enter the frozen radius-four writer grid.",
            "# Lay summary\n\nOnly a reliable perfect note earned the harder test of being rewritten by a daughter.",
        )

        active[0] = "compact-contraction"
        contraction = (
            cn._run_contraction_screen(attractor, selected_specs, contract)
            if selected_specs
            else _empty("no compact attractor reached contraction screening")
        )
        selected_ids = set(contraction.get("selected_spec_ids", []))
        selected_specs = [
            spec for spec in selected_specs if spec["spec_id"] in selected_ids
        ]
        _write_phase(
            output,
            "compact-contraction",
            design_digest,
            contraction | {"next_phase": "compact-closed-loop"},
            "# Stage 6O compact contraction\n\nDamage had to shrink while an undamaged compact state remained stable.",
            "# Lay summary\n\nA hereditary note must clean up a smudge, not faithfully reproduce it.",
        )

        active[0] = "compact-closed-loop"
        if contraction.get("stage_gate") and selected_specs:
            closed_loop, compact_models = cn._run_closed_loop(
                stage_root,
                source,
                base_rows,
                development_pairs,
                selected_specs,
                profile_name,
                causal_profile,
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
            closed_loop, compact_models = _empty(
                "no compact writer contracted registered damage"
            ), []
        _write_phase(
            output,
            "compact-closed-loop",
            design_digest,
            closed_loop | {"next_phase": "compact-validation"},
            "# Stage 6O compact closed loop\n\nThree out-of-fold daughter-generated rollout rounds tested active compact renewal.",
            "# Lay summary\n\nThe note was repeatedly recopied from daughter to daughter to see whether its meaning survived.",
        )

        active[0] = "compact-validation"
        if closed_loop.get("stage_gate") and compact_models:
            narrow, _ = cn._run_narrow_validation(
                stage_root,
                source,
                compact_models,
                procedural_pairs,
                profile_name,
                causal_profile,
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
            narrow = _empty("no frozen compact writer reached sealed validation")
            narrow["qualified_candidate_ids"] = []
            narrow["procedural_validation_opened"] = False
        _write_phase(
            output,
            "compact-validation",
            design_digest,
            narrow | {"next_phase": "adjudicate"},
            "# Stage 6O compact validation\n\nFrozen compact writers faced the full intervention ladder on sealed donor-disjoint pairs only after every prior gate.",
            "# Lay summary\n\nAny surviving self-copying note finally had to work in unfamiliar daughters and fail for the right reasons when erased.",
        )

        active[0] = "adjudicate"
        result = _campaign_result(
            output,
            design_digest,
            profile_name,
            metric_audit,
            motion_oracle,
            motion,
            compact,
            attractor,
            contraction,
            closed_loop,
            narrow,
        )
        _write_phase(
            output,
            "adjudicate",
            design_digest,
            result,
            "# Stage 6O adjudication\n\nCorrected command control, learned motion renewal, compact confirmation, and compact Plastic Heredity were adjudicated independently.",
            "# Lay summary\n\nA perfect instruction, a daughter-written instruction, and a truly renewed hereditary memory remain separate claims.",
        )
        _update_discovery_log(result)
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
    "DEFAULT_STAGE6N_ROOT",
    "DEFAULT_STAGE6M_ROOT",
    "DEFAULT_STAGE6L_ROOT",
    "PHASES",
    "PROFILES",
    "CounterfactualCarrierContract",
    "CounterfactualCarrierProfile",
    "_counterfactual_motion_metrics",
    "_d4_foreground_overlap",
    "_motion_oracle_gate",
    "_parent_integrity",
    "run_motif_counterfactual_carrier",
]
