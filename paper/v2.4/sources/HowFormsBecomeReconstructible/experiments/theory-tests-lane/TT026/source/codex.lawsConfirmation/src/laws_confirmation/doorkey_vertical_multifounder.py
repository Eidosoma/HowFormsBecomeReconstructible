"""Scout-informed multi-founder confirmation of the DoorKey vertical carrier.

The frozen descendant engine is imported from :mod:`doorkey_vertical_scout`.
This module supplies new seeds, four independently trained founders, a strict
84-cell registry, confirmatory endpoint classification, and run isolation.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
import multiprocessing
import os
from pathlib import Path
import platform
from statistics import median
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from .doorkey_carrier import carrier_digest, read_germ
from .doorkey_feedback_scout import _disk_preflight, _read_hash_manifest
from .doorkey_phase_value_credit import _finite_credit_history
from .doorkey_ppo_v2 import FeedbackPPOConfig
from . import doorkey_vertical_scout as frozen_vertical
from .io import (
    atomic_json,
    atomic_text,
    canonical_digest,
    environment_manifest,
    external_root,
    git_head,
    sha256_file,
    utc_now,
    write_hash_manifest,
)


RUN_ID = "doorkey_vertical_multifounder_confirmation_v1_attempt1"
ENGINE_RUN = frozen_vertical.RUN_ID
WRITER_RUN = frozen_vertical.WRITER_RUN
SCOUT_RUN = frozen_vertical.RUN_ID
ARMS = (
    "rewrite",
    "stale_copy",
    "silence",
    "wrong_frozen",
    "wrong_rewrite",
    "reader_off_rewrite",
    "lesion_rewrite",
)
WRITER_ARMS = frozenset(
    {
        "rewrite",
        "stale_copy",
        "wrong_rewrite",
        "reader_off_rewrite",
        "lesion_rewrite",
    }
)
EXPECTED_SCHEDULE_SOURCES = {
    "rewrite": "writer_candidate",
    "stale_copy": "original_founder",
    "silence": "valid_empty",
    "wrong_frozen": "wrong_founder",
    "wrong_rewrite": "writer_candidate",
    "reader_off_rewrite": "writer_candidate",
    "lesion_rewrite": "writer_candidate",
}
FOUNDERS = (0, 1, 2, 3)
CONFIRMATORY_FOUNDERS = (1, 2, 3)
GENERATIONS = (1, 2, 3)
UPDATES = frozen_vertical.UPDATES
EXPECTED_STEPS = frozen_vertical.EXPECTED_STEPS
MAX_WORKERS = 4
PRIMARY_MARGIN = 0.05
REGISTERED_CELLS = len(FOUNDERS) * len(GENERATIONS) * len(ARMS)
REGISTERED_TRANSITIONS = REGISTERED_CELLS * EXPECTED_STEPS


def seed_row(founder: int, generation: int) -> dict[str, int]:
    """Return the frozen disjoint seed row for one founder/generation."""

    if founder not in FOUNDERS or generation not in GENERATIONS:
        raise ValueError("unregistered founder or generation")
    offset = 100_000 * founder + 1_000 * generation
    return {
        "birth": 140_000_000 + offset,
        "training": 150_000_000 + offset,
        "writer_layout": 160_000_000 + offset,
        "writer_action": 170_000_000 + offset,
    }


SEEDS = {
    founder: {generation: seed_row(founder, generation) for generation in GENERATIONS}
    for founder in FOUNDERS
}


def _verify_recorded_inputs(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path_text, expected in manifest.get("input_sha256", {}).items():
        path = Path(path_text)
        live = sha256_file(path) if path.is_file() else None
        rows.append(
            {
                "path": str(path),
                "expected_sha256": expected,
                "live_sha256": live,
                "matches": live == expected,
            }
        )
    return rows


def _manifest_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    failures = [dict(row) for row in rows if not row.get("matches")]
    return {
        "row_count": len(rows),
        "matching_count": len(rows) - len(failures),
        "mismatches": failures,
        "passes": bool(rows) and not failures,
    }


def _correct_functional_packet(carrier: Any) -> dict[str, Any]:
    array = np.asarray(carrier, dtype=np.uint8)
    shape_ok = array.shape == (1, 64) and array.nbytes == 64
    if not shape_ok:
        return {
            "shape": list(array.shape),
            "bytes": int(array.nbytes),
            "active": None,
            "targets": None,
            "gates": {"exactly_64_bytes": False},
            "passes": False,
        }
    decoded = read_germ(array)
    active = decoded.active[0].tolist()
    targets = decoded.prior_logits.argmax(axis=-1)[0].tolist()
    expected_active = [False, True, False, True]
    gates = {
        "exactly_64_bytes": shape_ok,
        "only_slots_1_and_3_active": active == expected_active,
        "slot_1_targets_pickup_4": bool(decoded.active[0, 1]) and targets[1] == 4,
        "slot_3_targets_open_5": bool(decoded.active[0, 3]) and targets[3] == 5,
        "all_addresses_valid": bool(decoded.address_valid.all()),
        "all_checksums_valid": bool(decoded.checksum_valid.all()),
    }
    return {
        "shape": list(array.shape),
        "bytes": int(array.nbytes),
        "sha256": carrier_digest(array),
        "active": active,
        "targets": targets,
        "trust": decoded.trust[0].tolist(),
        "freshness": decoded.freshness[0].tolist(),
        "gates": gates,
        "passes": all(gates.values()),
    }


def _writer_emission_audit(result: Mapping[str, Any]) -> dict[str, Any]:
    """Require a valid functional packet produced by an active two-slot write."""

    packet = _correct_functional_packet(result["scheduled_next_carrier"])
    writer = result.get("writer", {})
    write_mask = writer.get("renewal", {}).get("write_mask")
    gates = {
        "functional_packet_correct": bool(packet["passes"]),
        "writer_enabled": bool(writer.get("enabled")),
        "scheduled_writer_candidate": result.get("scheduled_next_source")
        == "writer_candidate",
        "candidate_digest_is_scheduled_digest": writer.get("candidate_carrier_sha256")
        == result.get("scheduled_next_carrier_sha256"),
        "writer_actively_wrote_slots_1_and_3": write_mask
        == [[False, True, False, True]],
    }
    return {
        "packet": packet,
        "write_mask": write_mask,
        "gates": gates,
        "passes": all(gates.values()),
    }


def qualify_sources(root: Path) -> dict[str, Any]:
    """Verify the writer bank, four founders, and development scout."""

    writer_output = root / "outputs" / WRITER_RUN
    writer_run = root / "runs" / WRITER_RUN
    qualification_path = writer_output / "qualification.json"
    writer_manifest_path = writer_run / "MANIFEST.json"
    writer_status_path = writer_run / "STATUS.json"
    writer_base = frozen_vertical.qualify_writer_source(root)
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    writer_manifest = json.loads(writer_manifest_path.read_text(encoding="utf-8"))
    writer_status = json.loads(writer_status_path.read_text(encoding="utf-8"))
    parents = qualification.get("parents", [])
    bank = qualification.get("parent_bank", {})
    bank_rows = {int(row["parent"]): row for row in bank.get("parent_rows", [])}
    parent_audits: list[dict[str, Any]] = []
    configs: list[Mapping[str, Any]] = []
    for founder in FOUNDERS:
        record = next(
            (row for row in parents if int(row.get("parent", -1)) == founder),
            {},
        )
        bank_row = bank_rows.get(founder, {})
        checkpoint = Path(str(record.get("checkpoint", "")))
        carrier = np.asarray(record.get("carrier", []), dtype=np.uint8)
        packet = _correct_functional_packet(carrier)
        config = record.get("config", {})
        if config:
            configs.append(config)
        gates = {
            "parent_index_exact": record.get("parent") == founder,
            "parent_qualification_passed": bool(record.get("passes")),
            "checkpoint_exists": checkpoint.is_file(),
            "checkpoint_hash_exact": bool(
                checkpoint.is_file()
                and sha256_file(checkpoint) == bank_row.get("checkpoint_sha256")
                and bank_row.get("checkpoint_hash_matches")
            ),
            "carrier_digest_exact": bool(
                carrier.shape == (1, 64)
                and carrier_digest(carrier) == record.get("carrier_sha256")
            ),
            "carrier_functional_content_exact": bool(packet["passes"]),
            "config_present": bool(config),
        }
        parent_audits.append(
            {
                "founder": founder,
                "role": ("development_anchor" if founder == 0 else "confirmation"),
                "checkpoint": str(checkpoint),
                "checkpoint_sha256": bank_row.get("checkpoint_sha256"),
                "carrier": carrier.tolist(),
                "carrier_sha256": record.get("carrier_sha256"),
                "carrier_audit": packet,
                "config": config,
                "gates": gates,
                "passes": all(gates.values()),
            }
        )

    writer_inputs = _verify_recorded_inputs(writer_manifest)
    writer_outputs = _read_hash_manifest(writer_output / "output_hashes.sha256")
    config_digests = {canonical_digest(config) for config in configs}
    writer_gates = {
        "legacy_founder_zero_qualification_passes": bool(writer_base["passes"]),
        "run_ids_exact": qualification.get("run_id") == WRITER_RUN
        and writer_manifest.get("run_id") == WRITER_RUN,
        "status_complete": writer_status.get("status") == "COMPLETE",
        "complete_sentinel_present": (writer_run / "COMPLETE").is_file(),
        "overall_qualification_passed": bool(qualification.get("overall_pass")),
        "parent_bank_passed": bool(bank.get("passes")),
        "four_parent_records": len(parents) == len(FOUNDERS),
        "all_parent_audits_pass": len(parent_audits) == len(FOUNDERS)
        and all(row["passes"] for row in parent_audits),
        "all_configs_identical": len(configs) == len(FOUNDERS)
        and len(config_digests) == 1,
        "all_recorded_inputs_verify": bool(writer_inputs)
        and all(row["matches"] for row in writer_inputs),
        "all_recorded_outputs_verify": bool(writer_outputs)
        and all(row["matches"] for row in writer_outputs),
    }

    scout_output = root / "outputs" / SCOUT_RUN
    scout_run = root / "runs" / SCOUT_RUN
    scout_path = scout_output / "scout.json"
    scout_manifest_path = scout_run / "MANIFEST.json"
    scout_status_path = scout_run / "STATUS.json"
    scout = json.loads(scout_path.read_text(encoding="utf-8"))
    scout_manifest = json.loads(scout_manifest_path.read_text(encoding="utf-8"))
    scout_status = json.loads(scout_status_path.read_text(encoding="utf-8"))
    scout_inputs = _verify_recorded_inputs(scout_manifest)
    scout_outputs = _read_hash_manifest(scout_output / "output_hashes.sha256")
    scout_gates = {
        "run_ids_exact": scout.get("run_id") == SCOUT_RUN
        and scout_manifest.get("run_id") == SCOUT_RUN,
        "development_status_exact": scout.get("status")
        == "OUTCOME_OPEN_DEVELOPMENT_SCOUT",
        "scout_completed_cleanly": bool(scout.get("completed_cleanly")),
        "all_scout_completion_gates_passed": bool(scout.get("completion_gates"))
        and all(scout.get("completion_gates", {}).values()),
        "status_complete": scout_status.get("status") == "COMPLETE",
        "status_output_manifest_verified": bool(
            scout_status.get("output_manifest_self_verifies")
        ),
        "complete_sentinel_present": (scout_run / "COMPLETE").is_file(),
        "all_recorded_inputs_verify": bool(scout_inputs)
        and all(row["matches"] for row in scout_inputs),
        "all_recorded_outputs_verify": bool(scout_outputs)
        and all(row["matches"] for row in scout_outputs),
        "founder_zero_digest_matches": bool(parent_audits)
        and scout.get("founder_carrier_sha256")
        == parent_audits[0].get("carrier_sha256"),
    }
    gates = {
        "writer_source_passes": all(writer_gates.values()),
        "development_scout_passes": all(scout_gates.values()),
    }
    return {
        "writer": {
            "qualification_path": str(qualification_path),
            "manifest_path": str(writer_manifest_path),
            "status_path": str(writer_status_path),
            "input_manifest": _manifest_summary(writer_inputs),
            "output_manifest": _manifest_summary(writer_outputs),
            "gates": writer_gates,
            "passes": all(writer_gates.values()),
        },
        "scout": {
            "scout_path": str(scout_path),
            "manifest_path": str(scout_manifest_path),
            "status_path": str(scout_status_path),
            "manifest_input_paths": list(scout_manifest.get("input_sha256", {})),
            "input_manifest": _manifest_summary(scout_inputs),
            "output_manifest": _manifest_summary(scout_outputs),
            "gates": scout_gates,
            "passes": all(scout_gates.values()),
        },
        "parents": parent_audits,
        "gates": gates,
        "passes": all(gates.values()),
    }


def initial_carriers(founder: np.ndarray) -> dict[str, np.ndarray]:
    """Construct the seven registered carrier controls."""

    all_carriers = frozen_vertical.initial_carriers(founder)
    return {arm: all_carriers[arm].copy() for arm in ARMS}


def generation_specs(
    founder_index: int,
    generation: int,
    carriers: Mapping[str, np.ndarray],
    parent_checkpoints: Mapping[str, Path],
    *,
    founder: np.ndarray,
    wrong: np.ndarray,
    empty: np.ndarray,
) -> list[dict[str, Any]]:
    """Build the frozen seven-arm registry for one vertical generation."""

    seed = seed_row(founder_index, generation)
    specs: list[dict[str, Any]] = []
    for arm in ARMS:
        schedule_mode = "writer_candidate"
        fixed_next: np.ndarray | None = None
        fixed_label: str | None = None
        if arm == "stale_copy":
            schedule_mode = "fixed"
            fixed_next = founder
            fixed_label = "original_founder"
        elif arm == "silence":
            schedule_mode = "fixed"
            fixed_next = empty
            fixed_label = "valid_empty"
        elif arm == "wrong_frozen":
            schedule_mode = "fixed"
            fixed_next = wrong
            fixed_label = "wrong_founder"
        spec: dict[str, Any] = {
            "founder": founder_index,
            "founder_role": (
                "development_anchor" if founder_index == 0 else "confirmation"
            ),
            "generation": generation,
            "arm": arm,
            "birth_seed": seed["birth"],
            "training_seed": seed["training"],
            "writer_layout_seed": seed["writer_layout"],
            "writer_action_seed": seed["writer_action"],
            "germ_mode": ("blind" if arm == "reader_off_rewrite" else "direct_prior"),
            "writer_enabled": arm in WRITER_ARMS,
            "schedule_mode": schedule_mode,
            "incoming_germ": carriers[arm].tolist(),
            "parent_checkpoint": str(parent_checkpoints[arm]),
        }
        if fixed_next is not None:
            spec["fixed_next_germ"] = fixed_next.tolist()
            spec["fixed_source_label"] = fixed_label
        specs.append(spec)
    return specs


def _worker_train_cell(
    spec: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    output_root_text: str,
    founder_output_text: str,
) -> dict[str, Any]:
    """Run the frozen engine, then add confirmation registry metadata."""

    result = frozen_vertical._worker_train_cell(
        spec,
        config_payload,
        output_root_text,
        founder_output_text,
    )
    founder = int(spec["founder"])
    prior_founder = result.get("founder")
    if prior_founder is not None and int(prior_founder) != founder:
        raise RuntimeError("resumable result belongs to a different founder")
    engine_run_id = result.get("engine_run_id", result.get("run_id"))
    if engine_run_id != ENGINE_RUN:
        raise RuntimeError("cell was not produced by the frozen vertical engine")
    result["engine_run_id"] = ENGINE_RUN
    result["run_id"] = RUN_ID
    result["founder"] = founder
    result["founder_role"] = str(spec["founder_role"])
    output_root = Path(output_root_text)
    founder_output = Path(founder_output_text)
    result_path = founder_output / f"g{result['generation']}_{result['arm']}.json"
    atomic_json(result_path, result, output_root)
    progress_path = (
        founder_output / "progress" / f"g{result['generation']}_{result['arm']}.json"
    )
    if progress_path.is_file():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        progress.update(
            {
                "run_id": RUN_ID,
                "engine_run_id": ENGINE_RUN,
                "founder": founder,
                "founder_role": str(spec["founder_role"]),
            }
        )
        atomic_json(progress_path, progress, output_root)
    return result


def runtime_qualification(workers: int) -> dict[str, Any]:
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    values = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "torch_num_threads": torch.get_num_threads(),
        "torch_num_interop_threads": torch.get_num_interop_threads(),
        "worker_processes": workers,
    }
    gates = {
        "python_3_13": platform.python_version_tuple()[:2] == ("3", "13"),
        "numpy_2_5_2": np.__version__ == "2.5.2",
        "torch_2_14_cpu": torch.__version__ == "2.14.0+cpu",
        "cuda_disabled": not torch.cuda.is_available(),
        "main_intraop_threads_one": torch.get_num_threads() == 1,
        "main_interop_threads_one": torch.get_num_interop_threads() == 1,
        "exactly_four_workers": workers == MAX_WORKERS,
    }
    return {"values": values, "gates": gates, "passes": all(gates.values())}


def exact_alias_audit(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_cell = {
        (int(row["founder"]), int(row["generation"]), str(row["arm"])): row
        for row in results
    }

    def same(founder: int, generation: int, arms: Sequence[str]) -> dict[str, Any]:
        fingerprints = {
            arm: by_cell[(founder, generation, arm)]["behavior_fingerprint"]
            for arm in arms
        }
        return {
            "founder": founder,
            "generation": generation,
            "arms": list(arms),
            "fingerprints": fingerprints,
            "exact": len(set(fingerprints.values())) == 1,
        }

    rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        rows.extend(
            [
                same(founder, 1, ("rewrite", "stale_copy")),
                same(founder, 1, ("wrong_frozen", "wrong_rewrite")),
                same(
                    founder,
                    1,
                    ("silence", "reader_off_rewrite", "lesion_rewrite"),
                ),
                *[
                    same(
                        founder,
                        generation,
                        ("silence", "reader_off_rewrite"),
                    )
                    for generation in GENERATIONS
                ],
            ]
        )
    return {"comparisons": rows, "passes": all(row["exact"] for row in rows)}


def lineage_schedule_audit(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_cell = {
        (int(row["founder"]), int(row["generation"]), str(row["arm"])): row
        for row in results
    }
    rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        for arm in ARMS:
            for generation in (2, 3):
                parent = by_cell[(founder, generation - 1, arm)]
                child = by_cell[(founder, generation, arm)]
                exact = (
                    parent["scheduled_next_carrier_sha256"]
                    == child["incoming_carrier_sha256"]
                )
                rows.append(
                    {
                        "founder": founder,
                        "arm": arm,
                        "boundary": f"G{generation - 1}->G{generation}",
                        "parent_scheduled_sha256": parent[
                            "scheduled_next_carrier_sha256"
                        ],
                        "child_incoming_sha256": child["incoming_carrier_sha256"],
                        "exact": exact,
                    }
                )
    return {"rows": rows, "passes": all(row["exact"] for row in rows)}


def cell_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "founder": int(result["founder"]),
        "founder_role": str(result["founder_role"]),
        **frozen_vertical.cell_summary(result),
    }


def _open_auc(result: Mapping[str, Any]) -> float:
    return float(
        result["learning_auc"]["fixed_random"]["events"]["open_door"][
            "reached_fraction_auc"
        ]
    )


def classify_outcomes(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Apply the scout-informed endpoints without affecting run completion."""

    by_cell = {
        (int(row["founder"]), int(row["generation"]), str(row["arm"])): row
        for row in results
    }
    founder_rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        generation_rows: list[dict[str, Any]] = []
        for generation in GENERATIONS:
            rewrite = by_cell[(founder, generation, "rewrite")]
            silence = by_cell[(founder, generation, "silence")]
            reader_off = by_cell[(founder, generation, "reader_off_rewrite")]
            generation_rows.append(
                {
                    "generation": generation,
                    "rewrite_open_auc": _open_auc(rewrite),
                    "silence_open_auc": _open_auc(silence),
                    "reader_off_open_auc": _open_auc(reader_off),
                    "rewrite_minus_silence": _open_auc(rewrite) - _open_auc(silence),
                    "rewrite_minus_reader_off": _open_auc(rewrite)
                    - _open_auc(reader_off),
                }
            )
        primary_mean = float(
            np.mean([row["rewrite_minus_silence"] for row in generation_rows])
        )
        wrong_differences = [
            _open_auc(by_cell[(founder, generation, "wrong_rewrite")])
            - _open_auc(by_cell[(founder, generation, "wrong_frozen")])
            for generation in (2, 3)
        ]
        lesion_differences = [
            _open_auc(by_cell[(founder, generation, "lesion_rewrite")])
            - _open_auc(by_cell[(founder, generation, "silence")])
            for generation in (2, 3)
        ]
        wrong_emission = _writer_emission_audit(by_cell[(founder, 1, "wrong_rewrite")])
        lesion_emission = _writer_emission_audit(
            by_cell[(founder, 1, "lesion_rewrite")]
        )
        rewrite_packets = [
            {
                "generation": generation,
                **_writer_emission_audit(by_cell[(founder, generation, "rewrite")]),
            }
            for generation in GENERATIONS
        ]
        wrong_mean = float(np.mean(wrong_differences))
        lesion_mean = float(np.mean(lesion_differences))
        founder_rows.append(
            {
                "founder": founder,
                "role": ("development_anchor" if founder == 0 else "confirmation"),
                "generation_endpoints": generation_rows,
                "primary_mean_rewrite_minus_silence": primary_mean,
                "primary_above_margin": primary_mean > PRIMARY_MARGIN,
                "wrong_repair": {
                    "g1_outgoing_emission": wrong_emission,
                    "g2_g3_open_auc_differences": wrong_differences,
                    "mean_difference": wrong_mean,
                    "above_margin": wrong_mean > PRIMARY_MARGIN,
                    "passes": bool(wrong_emission["passes"])
                    and wrong_mean > PRIMARY_MARGIN,
                },
                "lesion_rescue": {
                    "g1_outgoing_emission": lesion_emission,
                    "g2_g3_open_auc_differences": lesion_differences,
                    "mean_difference": lesion_mean,
                    "above_margin": lesion_mean > PRIMARY_MARGIN,
                    "passes": bool(lesion_emission["passes"])
                    and lesion_mean > PRIMARY_MARGIN,
                },
                "rewrite_outgoing_packets": rewrite_packets,
                "rewrite_content_correct_every_generation": all(
                    row["passes"] for row in rewrite_packets
                ),
            }
        )

    confirmation = [
        row for row in founder_rows if row["founder"] in CONFIRMATORY_FOUNDERS
    ]
    primary_values = [row["primary_mean_rewrite_minus_silence"] for row in confirmation]
    primary_median = float(median(primary_values))
    primary_replicated = bool(
        len(confirmation) == len(CONFIRMATORY_FOUNDERS)
        and all(row["primary_above_margin"] for row in confirmation)
        and primary_median > PRIMARY_MARGIN
    )
    wrong_repaired = bool(
        len(confirmation) == len(CONFIRMATORY_FOUNDERS)
        and all(row["wrong_repair"]["passes"] for row in confirmation)
    )
    lesion_rescued = bool(
        len(confirmation) == len(CONFIRMATORY_FOUNDERS)
        and all(row["lesion_rescue"]["passes"] for row in confirmation)
    )
    rewrite_correct = all(
        row["rewrite_content_correct_every_generation"] for row in founder_rows
    )
    return {
        "endpoint_frozen_after_development_scout": True,
        "practical_margin": PRIMARY_MARGIN,
        "primary_measure": (
            "mean_G1_G2_G3_fixed_random_open_door_reached_fraction_auc_"
            "rewrite_minus_silence"
        ),
        "confirmation_founders": list(CONFIRMATORY_FOUNDERS),
        "founder_results": founder_rows,
        "confirmation_primary_values": primary_values,
        "confirmation_primary_median": primary_median,
        "primary_classification": (
            "PRIMARY_REPLICATED_3_OF_3"
            if primary_replicated
            else "PRIMARY_NOT_REPLICATED_3_OF_3"
        ),
        "wrong_repair_classification": (
            "WRONG_CONTENT_REPAIRED_3_OF_3"
            if wrong_repaired
            else "WRONG_CONTENT_NOT_REPAIRED_3_OF_3"
        ),
        "lesion_rescue_classification": (
            "LESION_RESCUED_3_OF_3" if lesion_rescued else "LESION_NOT_RESCUED_3_OF_3"
        ),
        "rewrite_content_classification": (
            "REWRITE_CONTENT_CORRECT_ALL_12_WRITES"
            if rewrite_correct
            else "REWRITE_CONTENT_NOT_CORRECT_ALL_12_WRITES"
        ),
        "exact_all_positive_sign_probability_under_independent_fair_signs": 0.125,
        "conventional_significance_claimed": False,
    }


def descriptive_contrasts(
    summaries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        subset = [row for row in summaries if int(row["founder"]) == founder]
        for row in frozen_vertical.descriptive_contrasts(subset):
            rows.append(
                {
                    "founder": founder,
                    "founder_role": (
                        "development_anchor" if founder == 0 else "confirmation"
                    ),
                    **row,
                }
            )
    return rows


def markdown_report(confirmation: Mapping[str, Any]) -> str:
    outcome = confirmation["outcomes"]
    lines = [
        "# DoorKey vertical multi-founder confirmation v1",
        "",
        f"**Structural completion:** `{'PASS' if confirmation['completed_cleanly'] else 'FAIL'}`  ",
        f"**Primary outcome:** `{outcome['primary_classification']}`  ",
        f"**Wrong-content repair:** `{outcome['wrong_repair_classification']}`  ",
        f"**Lesion rescue:** `{outcome['lesion_rescue_classification']}`",
        "",
        "## Primary carrier effect",
        "",
        (
            "The endpoint and 0.05 margin were frozen after the one-founder "
            "development scout. Founder 0 is an anchor; only founders 1--3 "
            "count toward confirmation."
        ),
        "",
        "| Founder | Role | G1 rewrite-silence | G2 | G3 | Mean | >0.05 |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for row in outcome["founder_results"]:
        differences = [
            item["rewrite_minus_silence"] for item in row["generation_endpoints"]
        ]
        lines.append(
            f"| {row['founder']} | `{row['role']}` | "
            f"{differences[0]:.6f} | {differences[1]:.6f} | "
            f"{differences[2]:.6f} | "
            f"{row['primary_mean_rewrite_minus_silence']:.6f} | "
            f"`{'PASS' if row['primary_above_margin'] else 'FAIL'}` |"
        )
    lines.extend(
        [
            "",
            (f"Confirmation median: `{outcome['confirmation_primary_median']:.6f}`."),
            "",
            "## Repair outcomes",
            "",
            "| Founder | Wrong packet corrected | Wrong G2/G3 mean | Wrong pass | Lesion packet corrected | Lesion G2/G3 mean | Lesion pass |",
            "|---:|---|---:|---|---|---:|---|",
        ]
    )
    for row in outcome["founder_results"]:
        wrong = row["wrong_repair"]
        lesion = row["lesion_rescue"]
        lines.append(
            f"| {row['founder']} | "
            f"`{'PASS' if wrong['g1_outgoing_emission']['passes'] else 'FAIL'}` | "
            f"{wrong['mean_difference']:.6f} | "
            f"`{'PASS' if wrong['passes'] else 'FAIL'}` | "
            f"`{'PASS' if lesion['g1_outgoing_emission']['passes'] else 'FAIL'}` | "
            f"{lesion['mean_difference']:.6f} | "
            f"`{'PASS' if lesion['passes'] else 'FAIL'}` |"
        )
    lines.extend(
        [
            "",
            "## Structural completion gates",
            "",
        ]
    )
    for name, passed in confirmation["completion_gates"].items():
        lines.append(f"- `{name}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            (
                "This run tests a bounded written, bottlenecked, read, renewed, "
                "and repairable carrier after complete soma resets. It does not "
                "test learned ontology/addressing or distinguish inherited learning "
                "disposition from direct action shaping. It does not by itself "
                "establish the universal wording of L17 or L20."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _input_paths(
    workspace: Path,
    root: Path,
    source: Mapping[str, Any],
) -> list[Path]:
    writer_output = root / "outputs" / WRITER_RUN
    writer_run = root / "runs" / WRITER_RUN
    scout_output = root / "outputs" / SCOUT_RUN
    scout_run = root / "runs" / SCOUT_RUN
    paths = [
        workspace / "protocols/DOORKEY_VERTICAL_MULTIFOUNDER_CONFIRMATION_V1.md",
        workspace / "protocols/DOORKEY_VERTICAL_THREE_BOUNDARY_SCOUT_V1.md",
        workspace / "requirements-doorkey.lock",
        Path(__file__).resolve(),
        workspace / "src/laws_confirmation/doorkey_vertical_scout.py",
        workspace / "tests/test_doorkey_vertical_multifounder.py",
        workspace / "tests/test_doorkey_vertical_scout.py",
        workspace / "scripts/run_doorkey_vertical_multifounder.sh",
        workspace / "scripts/run_doorkey_vertical_multifounder_detached.sh",
        writer_output / "qualification.json",
        writer_output / "input_hashes.sha256",
        writer_output / "output_hashes.sha256",
        writer_run / "MANIFEST.json",
        writer_run / "STATUS.json",
        writer_run / "COMPLETE",
        scout_output / "scout.json",
        scout_output / "audit.md",
        scout_output / "input_hashes.sha256",
        scout_output / "output_hashes.sha256",
        scout_run / "MANIFEST.json",
        scout_run / "STATUS.json",
        scout_run / "COMPLETE",
    ]
    paths.extend(Path(path) for path in source["scout"]["manifest_input_paths"])
    paths.extend(Path(row["checkpoint"]) for row in source["parents"])
    unique = sorted({path.resolve() for path in paths})
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen multi-founder inputs: {missing}")
    return unique


def run_confirmation(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if args.run_id != RUN_ID:
        raise ValueError(f"frozen run ID must be {RUN_ID}")
    if args.workers != MAX_WORKERS:
        raise ValueError(f"frozen confirmation requires exactly {MAX_WORKERS} workers")
    root = external_root(args.external_root)
    output_dir = root / "outputs" / args.run_id
    run_dir = root / "runs" / args.run_id
    workspace = Path(__file__).resolve().parents[2]
    source = qualify_sources(root)
    if not source["passes"]:
        raise RuntimeError(f"frozen source qualification failed: {source['gates']}")
    parent_records = {int(row["founder"]): row for row in source["parents"]}
    config = FeedbackPPOConfig(**dict(parent_records[0]["config"]))
    input_paths = _input_paths(workspace, root, source)
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    contract_digest = canonical_digest(input_hashes)
    disk = _disk_preflight(root, 256 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    if args.resume:
        if not run_dir.is_dir() or not output_dir.is_dir():
            raise FileNotFoundError("cannot resume a run that was not initialized")
        if (run_dir / "COMPLETE").is_file():
            print(output_dir / "audit.md")
            return 0
        old_manifest = json.loads(
            (run_dir / "MANIFEST.json").read_text(encoding="utf-8")
        )
        if (
            old_manifest.get("run_id") != args.run_id
            or old_manifest.get("contract_digest") != contract_digest
            or old_manifest.get("workers") != MAX_WORKERS
        ):
            raise RuntimeError("resume contract differs from initialized run")
    else:
        if output_dir.exists() or run_dir.exists():
            raise FileExistsError(f"immutable run ID exists: {args.run_id}")
        run_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        for founder in FOUNDERS:
            (output_dir / f"founder_{founder}").mkdir()
        manifest = {
            "schema_version": 1,
            "run_id": args.run_id,
            "engine_run_id": ENGINE_RUN,
            "stage": "DoorKey vertical multi-founder confirmation",
            "status": "RUNNING",
            "started_utc": utc_now(),
            "external_root": str(root),
            "output_dir": str(output_dir),
            "input_sha256": input_hashes,
            "contract_digest": contract_digest,
            "repository_head": git_head(workspace),
            "workers": MAX_WORKERS,
            "threads_per_worker": 1,
            "founders": list(FOUNDERS),
            "confirmation_founders": list(CONFIRMATORY_FOUNDERS),
            "generations": len(GENERATIONS),
            "arms": list(ARMS),
            "registered_cells": REGISTERED_CELLS,
            "updates_per_cell": UPDATES,
            "transitions_per_cell": EXPECTED_STEPS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "primary_margin": PRIMARY_MARGIN,
            "primary_margin_frozen_after_scout": True,
            "scientific_outcomes_are_completion_gates": False,
            "disk_preflight": disk,
            "environment": environment_manifest(),
        }
        atomic_json(run_dir / "MANIFEST.json", manifest, root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", root)
    atomic_json(
        run_dir / "STATUS.json",
        {
            "status": "RUNNING",
            "updated_utc": utc_now(),
            "run_id": args.run_id,
            "resume": bool(args.resume),
        },
        root,
    )
    atomic_text(run_dir / "RUN.pid", f"{os.getpid()}\n", root)

    try:
        runtime = runtime_qualification(args.workers)
        carriers: dict[int, dict[str, np.ndarray]] = {}
        wrong: dict[int, np.ndarray] = {}
        empty: dict[int, np.ndarray] = {}
        parent_checkpoints: dict[int, dict[str, Path]] = {}
        for founder in FOUNDERS:
            founder_carrier = np.asarray(
                parent_records[founder]["carrier"], dtype=np.uint8
            )
            carriers[founder] = initial_carriers(founder_carrier)
            wrong[founder] = carriers[founder]["wrong_frozen"].copy()
            empty[founder] = carriers[founder]["silence"].copy()
            checkpoint = Path(parent_records[founder]["checkpoint"])
            parent_checkpoints[founder] = {arm: checkpoint for arm in ARMS}

        results: list[dict[str, Any]] = []
        generation_specs_record: list[dict[str, Any]] = []
        training_started = time.monotonic()
        for generation in GENERATIONS:
            specs: list[dict[str, Any]] = []
            for founder in FOUNDERS:
                founder_carrier = np.asarray(
                    parent_records[founder]["carrier"], dtype=np.uint8
                )
                specs.extend(
                    generation_specs(
                        founder,
                        generation,
                        carriers[founder],
                        parent_checkpoints[founder],
                        founder=founder_carrier,
                        wrong=wrong[founder],
                        empty=empty[founder],
                    )
                )
            generation_specs_record.extend(specs)
            generation_results: list[dict[str, Any]] = []
            context = multiprocessing.get_context("spawn")
            with ProcessPoolExecutor(
                max_workers=MAX_WORKERS, mp_context=context
            ) as executor:
                future_to_spec = {
                    executor.submit(
                        _worker_train_cell,
                        spec,
                        asdict(config),
                        str(root),
                        str(output_dir / f"founder_{spec['founder']}"),
                    ): spec
                    for spec in specs
                }
                for future in as_completed(future_to_spec):
                    spec = future_to_spec[future]
                    try:
                        generation_results.append(future.result())
                    except Exception as error:
                        raise RuntimeError(
                            f"founder {spec['founder']} G{generation} "
                            f"{spec['arm']} worker failed"
                        ) from error
            generation_results.sort(
                key=lambda row: (
                    int(row["founder"]),
                    ARMS.index(str(row["arm"])),
                )
            )
            expected_keys = {(founder, arm) for founder in FOUNDERS for arm in ARMS}
            returned_keys = {
                (int(row["founder"]), str(row["arm"])) for row in generation_results
            }
            if returned_keys != expected_keys:
                raise RuntimeError(
                    f"G{generation} returned an incomplete founder/arm set"
                )
            results.extend(generation_results)
            for result in generation_results:
                founder = int(result["founder"])
                arm = str(result["arm"])
                carriers[founder][arm] = np.asarray(
                    result["scheduled_next_carrier"], dtype=np.uint8
                )
                parent_checkpoints[founder][arm] = (
                    output_dir
                    / f"founder_{founder}"
                    / f"g{generation}_{arm}_checkpoint.pt"
                )
            atomic_json(
                output_dir / "lineage_progress.json",
                {
                    "status": "RUNNING",
                    "updated_utc": utc_now(),
                    "completed_generations": generation,
                    "completed_cells": len(results),
                    "scheduled_carrier_sha256": {
                        str(founder): {
                            arm: carrier_digest(carriers[founder][arm]) for arm in ARMS
                        }
                        for founder in FOUNDERS
                    },
                },
                root,
            )

        elapsed_training = time.monotonic() - training_started
        results.sort(
            key=lambda row: (
                int(row["founder"]),
                int(row["generation"]),
                ARMS.index(str(row["arm"])),
            )
        )
        aliases = exact_alias_audit(results)
        schedule = lineage_schedule_audit(results)
        summaries = [cell_summary(row) for row in results]
        contrasts = descriptive_contrasts(summaries)
        outcomes = classify_outcomes(results)
        unique_cells = {
            (int(row["founder"]), int(row["generation"]), str(row["arm"]))
            for row in results
        }
        completion_gates = {
            "runtime_qualified": bool(runtime["passes"]),
            "frozen_sources_qualified": bool(source["passes"]),
            "exactly_84_registered_cells": len(results) == REGISTERED_CELLS
            and len(unique_cells) == REGISTERED_CELLS,
            "all_cells_registered_to_confirmation_run": all(
                row.get("run_id") == RUN_ID and row.get("engine_run_id") == ENGINE_RUN
                for row in results
            ),
            "all_cells_completed_cleanly": all(
                bool(row["completed_cleanly"]) for row in results
            ),
            "all_cells_100_updates": all(row["updates"] == UPDATES for row in results),
            "all_cells_expected_transitions": all(
                row["environment_steps"] == EXPECTED_STEPS for row in results
            ),
            "all_84_boundaries_reset": all(
                row["boundary_audit"]["passes"] for row in results
            ),
            "all_birth_packets_exactly_64_bytes": all(
                np.asarray(row["incoming_carrier"], dtype=np.uint8).nbytes == 64
                for row in results
            ),
            "all_scheduled_packets_exactly_64_bytes": all(
                np.asarray(row["scheduled_next_carrier"], dtype=np.uint8).nbytes == 64
                for row in results
            ),
            "all_schedule_sources_exact": all(
                row["scheduled_next_source"]
                == EXPECTED_SCHEDULE_SOURCES[str(row["arm"])]
                for row in results
            ),
            "all_writer_enablement_exact": all(
                bool(row["writer"]["enabled"]) == (str(row["arm"]) in WRITER_ARMS)
                for row in results
            ),
            "lineage_schedule_exact": bool(schedule["passes"]),
            "all_writer_transactions_valid_and_replayed": all(
                bool(row["writer"]["passes"])
                for row in results
                if row["writer"]["enabled"]
            ),
            "all_designed_behavioral_aliases_exact": bool(aliases["passes"]),
            "four_workers_one_thread": args.workers == MAX_WORKERS
            and runtime["values"]["torch_num_threads"] == 1,
            "all_metrics_finite": all(
                _finite_credit_history(row["history"]) for row in results
            ),
            "all_final_evaluations_replay_exactly": all(
                row["completion_gates"]["final_evaluations_replay_exactly"]
                for row in results
            ),
            "all_checkpoints_reload": all(
                row["completion_gates"]["checkpoint_reloads_with_leak_probe"]
                for row in results
            ),
            "scientific_outcomes_not_used_as_completion_gates": True,
        }
        confirmation = {
            "schema_version": 1,
            "run_id": args.run_id,
            "engine_run_id": ENGINE_RUN,
            "generated_utc": utc_now(),
            "status": "SCOUT_INFORMED_MULTIFOUNDER_CONFIRMATION",
            "runtime": runtime,
            "sources": source,
            "config": asdict(config),
            "seeds": SEEDS,
            "founders": list(FOUNDERS),
            "confirmation_founders": list(CONFIRMATORY_FOUNDERS),
            "arms": list(ARMS),
            "generations": list(GENERATIONS),
            "generation_specs": generation_specs_record,
            "cell_result_files": [
                str(
                    output_dir
                    / f"founder_{row['founder']}"
                    / f"g{row['generation']}_{row['arm']}.json"
                )
                for row in results
            ],
            "cell_summaries": summaries,
            "descriptive_contrasts": contrasts,
            "outcomes": outcomes,
            "exact_alias_audit": aliases,
            "lineage_schedule_audit": schedule,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "registered_cells": REGISTERED_CELLS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "elapsed_training_seconds": elapsed_training,
            "max_workers": MAX_WORKERS,
            "threads_per_worker": 1,
            "numbered_law_verdict_changes": 0,
        }
        atomic_json(output_dir / "confirmation.json", confirmation, root)
        atomic_text(output_dir / "audit.md", markdown_report(confirmation), root)
        output_paths = sorted(
            path.resolve()
            for path in output_dir.rglob("*")
            if path.is_file() and path.name != "output_hashes.sha256"
        )
        write_hash_manifest(output_paths, output_dir / "output_hashes.sha256", root)
        output_rows = _read_hash_manifest(output_dir / "output_hashes.sha256")
        outputs_verify = bool(output_rows) and all(
            row["matches"] for row in output_rows
        )
        status_ok = bool(confirmation["completed_cleanly"] and outputs_verify)
        status = {
            "status": "COMPLETE" if status_ok else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "completed_cleanly": bool(confirmation["completed_cleanly"]),
            "output_manifest_self_verifies": outputs_verify,
            "registered_cells": REGISTERED_CELLS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "max_workers": MAX_WORKERS,
            "primary_classification": outcomes["primary_classification"],
            "wrong_repair_classification": outcomes["wrong_repair_classification"],
            "lesion_rescue_classification": outcomes["lesion_rescue_classification"],
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
        }
        atomic_json(run_dir / "STATUS.json", status, root)
        sentinel = "COMPLETE" if status_ok else "FAILED"
        atomic_text(run_dir / sentinel, status["completed_utc"] + "\n", root)
        print(output_dir / "audit.md")
        return 0 if status_ok else 1
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", root)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> int:
    return run_confirmation(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
