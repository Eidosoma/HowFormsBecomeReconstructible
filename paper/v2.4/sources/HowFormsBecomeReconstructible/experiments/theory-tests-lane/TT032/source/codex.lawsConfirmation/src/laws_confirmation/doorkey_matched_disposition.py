"""Matched-behavior decomposition of DoorKey germ action shaping.

The inherited-reader arm and an external-controller arm receive identical
packet-derived action-logit additions through update 20.  The controller is a
separate apparatus path: its descendant inherits an empty packet, and its
carrier is never installed in descendant state.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import platform
import time
import traceback
from typing import Any, Callable, Iterator, Mapping, Sequence, TypeVar

import numpy as np
import torch

from . import doorkey_ppo_v2 as ppo_v2
from . import doorkey_vertical_multifounder as source_confirmation
from . import doorkey_vertical_scout as frozen_vertical
from .doorkey_boundary import make_boundary_packet
from .doorkey_carrier import (
    GermSchema,
    carrier_digest,
    empty_germ,
    read_germ,
)
from .doorkey_env import CAUSAL_CHAIN, DoorKeyEnv
from .doorkey_feedback_scout import (
    ACTION_MODES,
    _atomic_torch_save,
    _disk_preflight,
    _read_hash_manifest,
)
from .doorkey_phase_value_credit import (
    CHANNELS,
    CausalCreditDescendant,
    CausalCreditRollout,
    _finite_credit_history,
    _first_evaluation_reach,
    _module_birth_details,
    rollout_semantics,
)
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import FeedbackPPOConfig, _optimizer_tensor_count
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


RUN_ID = "doorkey_matched_behavior_disposition_v1_attempt1"
SOURCE_RUN = source_confirmation.RUN_ID
FOUNDERS = (1, 2, 3)
GENERATION = 4
ARMS = (
    "persistent_germ",
    "early_germ",
    "early_controller",
    "delayed_germ",
    "post_key_germ",
    "wrong_early",
    "carrier_blind",
    "silence",
)
UPDATES = frozen_vertical.UPDATES
CUTOFF_UPDATE = 20
EXPECTED_STEPS = frozen_vertical.EXPECTED_STEPS
MAX_WORKERS = 4
REGISTERED_CELLS = len(FOUNDERS) * len(ARMS)
REGISTERED_TRANSITIONS = REGISTERED_CELLS * EXPECTED_STEPS

T = TypeVar("T")


def seed_row(founder: int) -> dict[str, int]:
    """Return the frozen G4 seed pair for one confirmation founder."""

    if founder not in FOUNDERS:
        raise ValueError("unregistered founder")
    return {
        "birth": 180_000_000 + 100_000 * founder,
        "training": 190_000_000 + 100_000 * founder,
    }


SEEDS = {founder: seed_row(founder) for founder in FOUNDERS}


def make_post_key_mask(carrier: np.ndarray) -> np.ndarray:
    """Return a valid packet with only the pre-key slot-1 record silenced."""

    array = np.asarray(carrier, dtype=np.uint8)
    if array.shape != (1, GermSchema().carrier_bytes):
        raise ValueError("post-key mask requires one exact carrier")
    slots = array.reshape(1, 4, 16).copy()
    slots[0, 1, 12] = np.uint8(0)
    slots[0, 1, 15] = np.uint8(int(slots[0, 1, :15].astype(np.int64).sum()) % 256)
    return slots.reshape(1, 64)


def expression_for(
    arm: str,
    update: int,
    *,
    correct_carrier: np.ndarray,
    post_key_carrier: np.ndarray,
) -> dict[str, Any]:
    """Return the frozen reader/controller schedule at one evaluation/update."""

    if arm not in ARMS or not 0 <= update <= UPDATES:
        raise ValueError("unregistered arm or update")
    early = update <= CUTOFF_UPDATE
    if arm == "persistent_germ":
        return {"path": "inherited_reader", "germ_mode": "direct_prior"}
    if arm == "early_germ":
        return {
            "path": "inherited_reader",
            "germ_mode": "direct_prior" if early else "blind",
        }
    if arm == "early_controller" and early:
        return {
            "path": "external_controller",
            "germ_mode": "direct_prior",
            "carrier": correct_carrier,
            "label": "matched_correct_packet",
        }
    if arm == "early_controller":
        return {"path": "inherited_reader", "germ_mode": "direct_prior"}
    if arm == "delayed_germ":
        return {
            "path": "inherited_reader",
            "germ_mode": "blind" if early else "direct_prior",
        }
    if arm == "post_key_germ":
        return {
            "path": "masked_reader",
            "germ_mode": "direct_prior",
            "carrier": post_key_carrier,
            "label": "slot_1_silenced_slot_3_preserved",
        }
    if arm == "wrong_early":
        return {
            "path": "inherited_reader",
            "germ_mode": "direct_prior" if early else "blind",
        }
    if arm == "carrier_blind":
        return {"path": "inherited_reader", "germ_mode": "blind"}
    if arm == "silence":
        return {"path": "inherited_reader", "germ_mode": "direct_prior"}
    raise AssertionError("unreachable registered arm")


def _apply_packet_prior(
    logits: torch.Tensor,
    learner: Any,
    observations: torch.Tensor,
    carrier: np.ndarray,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Apply a packet as external action apparatus without reading learner.germ."""

    decoded = read_germ(np.asarray(carrier, dtype=np.uint8), GermSchema())
    slot_logits = torch.from_numpy(decoded.prior_logits[0].copy()).to(
        device=observations.device
    )
    slot_active = torch.from_numpy(decoded.active[0].copy()).to(
        device=observations.device
    )
    tiles = observations[:, :9].round().long()
    has_key = observations[:, 9] > 0.5
    standing_on_key = observations[:, 10] > 0.5
    key_visible = (tiles == DoorKeyEnv.KEY).any(dim=1) | standing_on_key
    door_visible = (
        (tiles == DoorKeyEnv.DOOR_CLOSED) | (tiles == DoorKeyEnv.DOOR_OPEN)
    ).any(dim=1)
    context = torch.zeros(
        observations.shape[0], dtype=torch.long, device=observations.device
    )
    context = torch.where(~has_key & key_visible, torch.ones_like(context), context)
    context = torch.where(has_key, torch.full_like(context, 2), context)
    context = torch.where(has_key & door_visible, torch.full_like(context, 3), context)
    prior = slot_logits[context]
    active = slot_active[context]
    return (
        logits
        + prior
        * active.to(logits.dtype)[:, None]
        * learner.model.config.germ_logit_scale,
        active,
    )


@contextmanager
def external_prior_path(
    descendant: CausalCreditDescendant,
    carrier: np.ndarray,
    tracker: dict[str, Any],
    *,
    label: str,
) -> Iterator[None]:
    """Temporarily route prior calls to non-inherited controller apparatus."""

    controller = np.asarray(carrier, dtype=np.uint8).copy()
    if controller.shape != (1, 64) or controller.nbytes != 64:
        raise ValueError("external controller requires one exact 64-byte packet")
    inherited = descendant.learner.germ
    expected_digest = carrier_digest(inherited)
    expected_bytes = inherited.copy()
    controller_digest = carrier_digest(controller)
    controller_bytes = controller.copy()
    original_vertical = frozen_vertical._apply_prior
    original_ppo = ppo_v2._apply_prior

    def apply_external(
        logits: torch.Tensor,
        learner: Any,
        observations: torch.Tensor,
        germ_mode: str,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        before = carrier_digest(learner.germ)
        unchanged_before = before == expected_digest and np.array_equal(
            learner.germ, expected_bytes
        )
        tracker["calls"] = int(tracker.get("calls", 0)) + 1
        tracker["germ_unchanged_each_call"] = bool(
            tracker.get("germ_unchanged_each_call", True) and unchanged_before
        )
        controller_unchanged_before = bool(
            carrier_digest(controller) == controller_digest
            and np.array_equal(controller, controller_bytes)
        )
        tracker["controller_unchanged_each_call"] = bool(
            tracker.get("controller_unchanged_each_call", True)
            and controller_unchanged_before
        )
        if (
            germ_mode != "direct_prior"
            or not unchanged_before
            or not controller_unchanged_before
        ):
            raise RuntimeError("external prior call violated its frozen contract")
        result = _apply_packet_prior(logits, learner, observations, controller)
        unchanged_after = carrier_digest(
            learner.germ
        ) == expected_digest and np.array_equal(learner.germ, expected_bytes)
        tracker["germ_unchanged_each_call"] = bool(
            tracker["germ_unchanged_each_call"] and unchanged_after
        )
        controller_unchanged_after = bool(
            carrier_digest(controller) == controller_digest
            and np.array_equal(controller, controller_bytes)
        )
        tracker["controller_unchanged_each_call"] = bool(
            tracker["controller_unchanged_each_call"] and controller_unchanged_after
        )
        if not unchanged_after or not controller_unchanged_after:
            raise RuntimeError("external controller mutated inherited carrier")
        return result

    if original_vertical is not original_ppo:
        raise RuntimeError(
            "frozen rollout and evaluation prior implementations diverged"
        )
    tracker["contexts"] = int(tracker.get("contexts", 0)) + 1
    tracker.setdefault("labels", {})[label] = (
        int(tracker.setdefault("labels", {}).get(label, 0)) + 1
    )
    tracker.setdefault("controller_carrier_sha256", {})[label] = controller_digest
    frozen_vertical._apply_prior = apply_external
    ppo_v2._apply_prior = apply_external
    try:
        yield
    finally:
        frozen_vertical._apply_prior = original_vertical
        ppo_v2._apply_prior = original_ppo
        restored = np.array_equal(descendant.learner.germ, expected_bytes)
        tracker["germ_restored_after_every_context"] = bool(
            tracker.get("germ_restored_after_every_context", True) and restored
        )
        if not restored:
            raise RuntimeError("external controller context changed inherited carrier")


def run_with_expression(
    descendant: CausalCreditDescendant,
    expression: Mapping[str, Any],
    tracker: dict[str, Any],
    operation: Callable[[str], T],
) -> T:
    """Run one rollout, update, or evaluation under a frozen expression row."""

    mode = str(expression["germ_mode"])
    if expression["path"] == "inherited_reader":
        return operation(mode)
    with external_prior_path(
        descendant,
        np.asarray(expression["carrier"], dtype=np.uint8),
        tracker,
        label=str(expression["label"]),
    ):
        return operation(mode)


def _deep_update(digest: Any, value: Any) -> None:
    """Feed exact typed state into a stable recursive digest."""

    if isinstance(value, torch.Tensor):
        array = value.detach().cpu().contiguous().numpy()
        digest.update(b"torch")
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(repr(array.shape).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    elif isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        digest.update(b"numpy")
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(repr(array.shape).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    elif isinstance(value, np.generic):
        _deep_update(digest, value.item())
    elif is_dataclass(value) and not isinstance(value, type):
        digest.update(f"dataclass:{type(value).__qualname__}".encode("utf-8"))
        _deep_update(digest, asdict(value))
    elif isinstance(value, Mapping):
        digest.update(b"mapping")
        for key in sorted(value, key=lambda item: repr(item)):
            _deep_update(digest, key)
            _deep_update(digest, value[key])
    elif isinstance(value, (list, tuple)):
        digest.update(type(value).__name__.encode("ascii"))
        for item in value:
            _deep_update(digest, item)
    elif isinstance(value, (set, frozenset)):
        digest.update(type(value).__name__.encode("ascii"))
        for item in sorted(value, key=repr):
            _deep_update(digest, item)
    elif isinstance(value, Path):
        _deep_update(digest, str(value))
    elif isinstance(value, bytes):
        digest.update(b"bytes")
        digest.update(value)
    elif value is None or isinstance(value, (str, int, float, bool)):
        digest.update(type(value).__name__.encode("ascii"))
        digest.update(repr(value).encode("utf-8"))
    elif hasattr(value, "__dict__"):
        digest.update(f"object:{type(value).__qualname__}".encode("utf-8"))
        _deep_update(digest, vars(value))
    else:
        raise TypeError(f"unsupported digest value: {type(value)!r}")


def deep_digest(value: Any) -> str:
    digest = hashlib.sha256()
    _deep_update(digest, value)
    return digest.hexdigest()


def soma_environment_digests(
    descendant: CausalCreditDescendant,
    environments: DoorKeyVectorEnv,
) -> dict[str, str]:
    """Digest all continuing state except the intentionally different carrier."""

    learner = descendant.learner
    parts: dict[str, Any] = {
        "actor_critic": learner.model.state_dict(),
        "auxiliary_heads": descendant.auxiliary_heads.state_dict(),
        "writer": learner.writer.state_dict(),
        "ppo_optimizer": learner.optimizer.state_dict(),
        "writer_optimizer": learner.writer_optimizer.state_dict(),
        "recurrent_hidden": learner.recurrent_hidden,
        "previous_actions": learner.previous_actions,
        "previous_rewards": learner.previous_rewards,
        "rollout_state": learner.rollout_state,
        "numpy_rng": learner.numpy_rng.bit_generator.state,
        "torch_rng": learner.torch_generator.get_state(),
        "normalization_state": learner.normalization_state,
        "curriculum_state": learner.curriculum_state,
        "population_statistics": learner.population_statistics,
        "birth_seed": learner.birth_seed,
        "public_rulebook_digest": learner.public_rulebook_digest,
        "environment": environments,
    }
    rows = {name: deep_digest(value) for name, value in parts.items()}
    rows["aggregate"] = deep_digest(rows)
    return rows


def _clean_evaluation(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "germ_mode"}


def behavior_digest(
    history: Sequence[Mapping[str, Any]],
    evaluations: Sequence[Mapping[str, Any]],
    *,
    first_update: int,
    last_update: int,
    final_evaluations: Mapping[str, Any] | None = None,
    final_world_rows: Mapping[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "history": [
            dict(row)
            for row in history
            if first_update <= int(row["update"]) <= last_update
        ],
        "evaluations": [
            _clean_evaluation(row)
            for row in evaluations
            if first_update <= int(row["update"]) <= last_update
        ],
    }
    if final_evaluations is not None:
        payload["final_evaluations"] = {
            mode: _clean_evaluation(row) for mode, row in final_evaluations.items()
        }
    if final_world_rows is not None:
        payload["final_world_rows"] = final_world_rows
    return deep_digest(payload)


def _verify_manifest_inputs(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
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
    failed = [dict(row) for row in rows if not row.get("matches")]
    return {
        "row_count": len(rows),
        "matching_count": len(rows) - len(failed),
        "mismatches": failed,
        "passes": bool(rows) and not failed,
    }


def qualify_sources(root: Path) -> dict[str, Any]:
    """Verify the completed confirmation and the three actual G3 parents."""

    source_output = root / "outputs" / SOURCE_RUN
    source_run = root / "runs" / SOURCE_RUN
    confirmation_path = source_output / "confirmation.json"
    manifest_path = source_run / "MANIFEST.json"
    status_path = source_run / "STATUS.json"
    confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    input_rows = _verify_manifest_inputs(manifest)
    output_rows = _read_hash_manifest(source_output / "output_hashes.sha256")
    output_paths = {row["path"] for row in output_rows}
    upstream = source_confirmation.qualify_sources(root)

    parents: list[dict[str, Any]] = []
    config_digests: set[str] = set()
    for founder in FOUNDERS:
        result_path = source_output / f"founder_{founder}" / "g3_rewrite.json"
        checkpoint_path = (
            source_output / f"founder_{founder}" / "g3_rewrite_checkpoint.pt"
        )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        outgoing = np.asarray(result.get("scheduled_next_carrier", []), dtype=np.uint8)
        checkpoint_outgoing = np.asarray(
            checkpoint.get("scheduled_next_germ", []), dtype=np.uint8
        )
        packet_audit = source_confirmation._correct_functional_packet(outgoing)
        config = dict(result.get("config", {}))
        if config:
            config_digests.add(canonical_digest(config))
        result_sha = sha256_file(result_path)
        checkpoint_sha = sha256_file(checkpoint_path)
        gates = {
            "source_result_registered": result.get("run_id") == SOURCE_RUN
            and result.get("founder") == founder
            and result.get("generation") == 3
            and result.get("arm") == "rewrite",
            "source_result_completed": bool(result.get("completed_cleanly")),
            "result_is_in_output_manifest": str(result_path.resolve()) in output_paths,
            "checkpoint_is_in_output_manifest": str(checkpoint_path.resolve())
            in output_paths,
            "checkpoint_hash_exact": checkpoint_sha == result.get("checkpoint_sha256"),
            "checkpoint_identity_exact": checkpoint.get("run_id")
            == frozen_vertical.RUN_ID
            and checkpoint.get("generation") == 3
            and checkpoint.get("arm") == "rewrite",
            "checkpoint_outgoing_exact": np.array_equal(checkpoint_outgoing, outgoing),
            "outgoing_digest_exact": outgoing.shape == (1, 64)
            and carrier_digest(outgoing) == result.get("scheduled_next_carrier_sha256"),
            "outgoing_functional_content_exact": bool(packet_audit["passes"]),
            "writer_output_selected": result.get("scheduled_next_source")
            == "writer_candidate",
            "config_present": bool(config),
        }
        parents.append(
            {
                "founder": founder,
                "result": str(result_path),
                "result_sha256": result_sha,
                "checkpoint": str(checkpoint_path),
                "checkpoint_sha256": checkpoint_sha,
                "outgoing_carrier": outgoing.tolist(),
                "outgoing_carrier_sha256": (
                    carrier_digest(outgoing) if outgoing.shape == (1, 64) else None
                ),
                "outgoing_packet_audit": packet_audit,
                "config": config,
                "gates": gates,
                "passes": all(gates.values()),
            }
        )

    source_gates = {
        "run_ids_exact": confirmation.get("run_id") == SOURCE_RUN
        and manifest.get("run_id") == SOURCE_RUN,
        "confirmation_completed_cleanly": bool(confirmation.get("completed_cleanly")),
        "exactly_20_source_completion_gates": len(
            confirmation.get("completion_gates", {})
        )
        == 20,
        "all_20_source_completion_gates_pass": bool(
            confirmation.get("completion_gates")
        )
        and all(confirmation.get("completion_gates", {}).values()),
        "source_status_complete": status.get("status") == "COMPLETE",
        "source_status_manifest_verified": bool(
            status.get("output_manifest_self_verifies")
        ),
        "source_complete_sentinel_present": (source_run / "COMPLETE").is_file(),
        "source_failed_sentinel_absent": not (source_run / "FAILED").exists(),
        "all_recorded_source_inputs_verify": bool(input_rows)
        and all(row["matches"] for row in input_rows),
        "all_recorded_source_outputs_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
        "upstream_sources_still_qualify": bool(upstream["passes"]),
        "three_g3_parent_records_pass": len(parents) == len(FOUNDERS)
        and all(row["passes"] for row in parents),
        "parent_configs_identical": len(config_digests) == 1,
    }
    return {
        "confirmation_path": str(confirmation_path),
        "manifest_path": str(manifest_path),
        "status_path": str(status_path),
        "source_input_manifest": _manifest_summary(input_rows),
        "source_output_manifest": _manifest_summary(output_rows),
        "parents": parents,
        "upstream": upstream,
        "gates": source_gates,
        "passes": all(source_gates.values()),
    }


def cell_specs(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build the frozen 24-cell G4 intervention registry."""

    parents = {int(row["founder"]): row for row in source["parents"]}
    specs: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        correct = np.asarray(parents[founder]["outgoing_carrier"], dtype=np.uint8)
        controls = source_confirmation.initial_carriers(correct)
        wrong = np.asarray(controls["wrong_frozen"], dtype=np.uint8)
        silence = empty_germ(1, GermSchema())
        post_key = make_post_key_mask(correct)
        for arm in ARMS:
            if arm in {"early_controller", "silence"}:
                incoming = silence
            elif arm == "wrong_early":
                incoming = wrong
            else:
                incoming = correct
            specs.append(
                {
                    "founder": founder,
                    "generation": GENERATION,
                    "arm": arm,
                    "birth_seed": seed_row(founder)["birth"],
                    "training_seed": seed_row(founder)["training"],
                    "parent_checkpoint": parents[founder]["checkpoint"],
                    "parent_checkpoint_sha256": parents[founder]["checkpoint_sha256"],
                    "source_carrier_sha256": carrier_digest(correct),
                    "incoming_germ": incoming.tolist(),
                    "correct_controller_germ": correct.tolist(),
                    "post_key_controller_germ": post_key.tolist(),
                    "wrong_germ_sha256": carrier_digest(wrong),
                }
            )
    return specs


def segment_learning_auc(
    evaluations: Sequence[Mapping[str, Any]],
    action_mode: str,
    first_update: int,
    last_update: int,
) -> dict[str, Any]:
    """Compute normalized causal-chain AUC over an explicitly bounded segment."""

    rows = sorted(
        (
            row
            for row in evaluations
            if row["action_mode"] == action_mode
            and first_update <= int(row["update"]) <= last_update
        ),
        key=lambda row: int(row["update"]),
    )
    updates = np.asarray([int(row["update"]) for row in rows], dtype=np.float64)
    if len(rows) < 2 or updates[0] != first_update or updates[-1] != last_update:
        raise ValueError("segment AUC requires both registered endpoints")
    width = float(last_update - first_update)
    events: dict[str, dict[str, float]] = {}
    for event in CAUSAL_CHAIN:
        chain = [
            next(item for item in row["conditional_chain"] if item["to"] == event)
            for row in rows
        ]
        reached = np.asarray(
            [item["reached"] / row["world_count"] for item, row in zip(chain, rows)],
            dtype=np.float64,
        )
        conditional = np.asarray(
            [
                0.0
                if item["conditional_probability"] is None
                else item["conditional_probability"]
                for item in chain
            ],
            dtype=np.float64,
        )
        events[event] = {
            "reached_fraction_auc": float(np.trapezoid(reached, updates) / width),
            "conditional_probability_auc": float(
                np.trapezoid(conditional, updates) / width
            ),
        }
    terminal = np.asarray(
        [row["successes"] / row["world_count"] for row in rows],
        dtype=np.float64,
    )
    return {
        "action_mode": action_mode,
        "first_update": first_update,
        "last_update": last_update,
        "updates": updates.astype(int).tolist(),
        "events": events,
        "terminal_success_fraction_auc": float(np.trapezoid(terminal, updates) / width),
    }


def _evaluate_cell(
    descendant: CausalCreditDescendant,
    config: FeedbackPPOConfig,
    expression: Mapping[str, Any],
    tracker: dict[str, Any],
    action_mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    evaluation, rows = run_with_expression(
        descendant,
        expression,
        tracker,
        lambda mode: frozen_vertical._evaluate(descendant, config, mode, action_mode),
    )
    evaluation["world_rows_sha256"] = deep_digest(rows)
    return evaluation, rows


def _train_cell(
    spec: Mapping[str, Any],
    config: FeedbackPPOConfig,
    output_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Train one registered G4 cell under its time-varying expression path."""

    founder = int(spec["founder"])
    arm = str(spec["arm"])
    if founder not in FOUNDERS or arm not in ARMS:
        raise ValueError("unregistered matched-disposition cell")
    birth_seed = int(spec["birth_seed"])
    training_seed = int(spec["training_seed"])
    incoming = np.asarray(spec["incoming_germ"], dtype=np.uint8)
    correct = np.asarray(spec["correct_controller_germ"], dtype=np.uint8)
    post_key = np.asarray(spec["post_key_controller_germ"], dtype=np.uint8)
    packet = make_boundary_packet(incoming)
    stem = f"g4_{arm}"
    result_path = output_dir / f"{stem}.json"
    checkpoint_path = output_dir / f"{stem}_checkpoint.pt"
    progress_path = output_dir / "progress" / f"{stem}.json"
    if result_path.is_file() != checkpoint_path.is_file():
        raise RuntimeError(f"partial resumable artifacts for founder {founder} {arm}")
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("run_id") != RUN_ID
            or result.get("founder") != founder
            or result.get("generation") != GENERATION
            or result.get("arm") != arm
            or result.get("birth_seed") != birth_seed
            or result.get("training_seed") != training_seed
            or result.get("updates") != UPDATES
            or result.get("incoming_carrier_sha256") != packet.digest()
            or not result.get("completed_cleanly")
        ):
            raise RuntimeError(f"invalid resumable result for founder {founder} {arm}")
        print(f"founder {founder} {stem} already complete; resuming", flush=True)
        return result

    atomic_json(
        progress_path,
        {
            "status": "STARTING",
            "updated_utc": utc_now(),
            "founder": founder,
            "generation": GENERATION,
            "arm": arm,
            "update": 0,
        },
        output_root,
    )
    descendant = frozen_vertical.make_vertical_descendant(packet, config, birth_seed)
    boundary = frozen_vertical.audit_vertical_boundary(
        Path(spec["parent_checkpoint"]),
        descendant,
        packet,
        generation=GENERATION,
    )
    initial_state = _module_birth_details(descendant)
    initial_germ = descendant.learner.germ.copy()
    incoming_read = read_germ(initial_germ)
    tracker: dict[str, Any] = {
        "calls": 0,
        "contexts": 0,
        "labels": {},
        "controller_carrier_sha256": {},
        "germ_unchanged_each_call": True,
        "germ_restored_after_every_context": True,
        "controller_unchanged_each_call": True,
    }

    evaluations: list[dict[str, Any]] = []
    expression = expression_for(
        arm,
        0,
        correct_carrier=correct,
        post_key_carrier=post_key,
    )
    for action_mode in ACTION_MODES:
        evaluation, _ = _evaluate_cell(
            descendant, config, expression, tracker, action_mode
        )
        evaluation["update"] = 0
        evaluations.append(evaluation)

    environments = DoorKeyVectorEnv(
        config.num_envs,
        training_seed,
        config.max_episode_steps,
        "terminal",
    )
    history: list[dict[str, Any]] = []
    total_episodes = 0
    total_successes = 0
    cumulative_events = {channel: 0 for channel in CHANNELS}
    first_signal_update: dict[str, int | None] = {channel: None for channel in CHANNELS}
    semantics_accumulator: dict[str, bool] = {}
    last_rollout: CausalCreditRollout | None = None
    cutoff_digests: dict[str, str] | None = None
    for update in range(1, UPDATES + 1):
        expression = expression_for(
            arm,
            update,
            correct_carrier=correct,
            post_key_carrier=post_key,
        )
        rollout, completed = run_with_expression(
            descendant,
            expression,
            tracker,
            lambda mode: frozen_vertical.collect_vertical_rollout(
                descendant, environments, config, mode
            ),
        )
        last_rollout = rollout
        rollout_sha256 = deep_digest(vars(rollout))
        completed_sha256 = deep_digest(completed)
        semantics = rollout_semantics(rollout)
        for name, passed in semantics.items():
            semantics_accumulator[name] = bool(
                semantics_accumulator.get(name, True) and passed
            )
        event_counts = {
            channel: int(rollout.event_rewards[:, :, index].sum().item())
            for index, channel in enumerate(CHANNELS)
        }
        phase_counts = {
            channel: int(torch.count_nonzero(rollout.phases == index).item())
            for index, channel in enumerate(CHANNELS)
        }
        for channel in CHANNELS:
            cumulative_events[channel] += event_counts[channel]
            if event_counts[channel] and first_signal_update[channel] is None:
                first_signal_update[channel] = update
        metrics = run_with_expression(
            descendant,
            expression,
            tracker,
            lambda mode: frozen_vertical.vertical_phase_ppo_update(
                descendant, rollout, config, mode
            ),
        )
        update_successes = sum(bool(row["success"]) for row in completed)
        total_episodes += len(completed)
        total_successes += update_successes
        row: dict[str, Any] = {
            "update": update,
            "environment_steps": update * config.num_envs * config.rollout_steps,
            "episodes_completed": len(completed),
            "episode_successes": update_successes,
            "cumulative_episodes": total_episodes,
            "cumulative_successes": total_successes,
            "mean_rollout_terminal_reward": float(rollout.terminal_rewards.mean()),
            "max_rollout_terminal_reward": float(rollout.terminal_rewards.max()),
            "event_counts": event_counts,
            "cumulative_event_counts": dict(cumulative_events),
            "phase_counts": phase_counts,
            "rollout_semantics": semantics,
            "rollout_sha256": rollout_sha256,
            "completed_episode_rows_sha256": completed_sha256,
            **metrics,
        }
        history.append(row)
        latest: list[dict[str, Any]] = []
        if update % 10 == 0:
            for action_mode in ACTION_MODES:
                evaluation, _ = _evaluate_cell(
                    descendant, config, expression, tracker, action_mode
                )
                evaluation["update"] = update
                evaluations.append(evaluation)
                latest.append(evaluation)
        if update == CUTOFF_UPDATE:
            cutoff_digests = soma_environment_digests(descendant, environments)
        if update % 5 == 0:
            atomic_json(
                progress_path,
                {
                    "status": "RUNNING",
                    "updated_utc": utc_now(),
                    "founder": founder,
                    "generation": GENERATION,
                    "arm": arm,
                    "update": update,
                    "updates": UPDATES,
                    "environment_steps": row["environment_steps"],
                    "cumulative_episodes": total_episodes,
                    "cumulative_successes": total_successes,
                    "cumulative_event_counts": dict(cumulative_events),
                    "latest_evaluations": latest,
                },
                output_root,
            )
            print(
                f"founder {founder} {stem} update {update}/{UPDATES} "
                f"events={cumulative_events['key']}/"
                f"{cumulative_events['door']}/{cumulative_events['goal']}",
                flush=True,
            )

    if last_rollout is None or cutoff_digests is None:
        raise RuntimeError("matched-disposition cell missed rollout or cutoff state")

    final_expression = expression_for(
        arm,
        UPDATES,
        correct_carrier=correct,
        post_key_carrier=post_key,
    )
    final_evaluations: dict[str, Any] = {}
    final_world_rows: dict[str, Any] = {}
    final_replay = True
    for action_mode in ACTION_MODES:
        evaluation, rows = _evaluate_cell(
            descendant, config, final_expression, tracker, action_mode
        )
        final_evaluations[action_mode] = evaluation
        final_world_rows[action_mode] = rows
        scheduled = [
            row
            for row in evaluations
            if int(row["update"]) == UPDATES and row["action_mode"] == action_mode
        ]
        expected = dict(evaluation)
        expected["update"] = UPDATES
        final_replay &= len(scheduled) == 1 and scheduled[0] == expected

    final_state = _module_birth_details(descendant)
    final_digests = soma_environment_digests(descendant, environments)
    early_behavior_sha256 = behavior_digest(
        history,
        evaluations,
        first_update=0,
        last_update=CUTOFF_UPDATE,
    )
    post_behavior_sha256 = behavior_digest(
        history,
        evaluations,
        first_update=CUTOFF_UPDATE + 1,
        last_update=UPDATES,
        final_evaluations=final_evaluations,
        final_world_rows=final_world_rows,
    )
    full_behavior_sha256 = behavior_digest(
        history,
        evaluations,
        first_update=0,
        last_update=UPDATES,
        final_evaluations=final_evaluations,
        final_world_rows=final_world_rows,
    )

    rollout_state = frozen_vertical.rollout_payload(last_rollout)
    checkpoint_payload = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "source_run_id": SOURCE_RUN,
        "founder": founder,
        "generation": GENERATION,
        "arm": arm,
        "birth_seed": birth_seed,
        "training_seed": training_seed,
        "updates": UPDATES,
        "reward_mode": "terminal",
        "config": asdict(config),
        "germ": descendant.learner.germ,
        "model_state_dict": descendant.learner.model.state_dict(),
        "auxiliary_heads_state_dict": descendant.auxiliary_heads.state_dict(),
        "writer_state_dict": descendant.learner.writer.state_dict(),
        "optimizer_state_dict": descendant.learner.optimizer.state_dict(),
        "writer_optimizer_state_dict": descendant.learner.writer_optimizer.state_dict(),
        "recurrent_hidden": descendant.learner.recurrent_hidden,
        "previous_actions": descendant.learner.previous_actions,
        "previous_rewards": descendant.learner.previous_rewards,
        "rollout_state": rollout_state,
        "numpy_rng_state": descendant.learner.numpy_rng.bit_generator.state,
        "torch_generator_state": descendant.learner.torch_generator.get_state(),
    }
    _atomic_torch_save(checkpoint_path, checkpoint_payload)
    checkpoint_verified = False
    controller_absent_from_checkpoint = False
    try:
        reloaded = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        controller_absent_from_checkpoint = not any(
            "controller" in str(key).lower() for key in reloaded
        )
        checkpoint_verified = bool(
            reloaded.get("run_id") == RUN_ID
            and reloaded.get("founder") == founder
            and reloaded.get("generation") == GENERATION
            and reloaded.get("arm") == arm
            and int(reloaded.get("updates", -1)) == UPDATES
            and np.array_equal(reloaded.get("germ"), initial_germ)
            and reloaded.get("rollout_state") is not None
            and controller_absent_from_checkpoint
        )
    except Exception:
        checkpoint_verified = False

    evaluation_counts = {
        action_mode: sum(row["action_mode"] == action_mode for row in evaluations)
        for action_mode in ACTION_MODES
    }
    expected_evaluations = 1 + UPDATES // 10
    post_key_read = read_germ(post_key)
    post_key_mask_exact = bool(
        post_key.shape == (1, 64)
        and post_key_read.address_valid.all()
        and post_key_read.checksum_valid.all()
        and post_key_read.active[0].tolist() == [False, False, False, True]
        and int(post_key_read.prior_logits.argmax(axis=-1)[0, 3]) == 5
    )
    external_expected = arm in {"early_controller", "post_key_germ"}
    expected_controller_contexts = {
        "early_controller": 46,
        "post_key_germ": 224,
    }.get(arm, 0)
    gates = {
        "boundary_reset_passes": bool(boundary["passes"]),
        "parent_checkpoint_hash_exact": sha256_file(Path(spec["parent_checkpoint"]))
        == spec["parent_checkpoint_sha256"],
        "all_metrics_finite": _finite_credit_history(history),
        "expected_update_count": len(history) == UPDATES,
        "expected_environment_steps": history[-1]["environment_steps"]
        == EXPECTED_STEPS,
        "expected_evaluations_per_mode": all(
            evaluation_counts[action_mode] == expected_evaluations
            for action_mode in ACTION_MODES
        ),
        "final_evaluations_replay_exactly": final_replay,
        "all_rollout_semantics_pass": bool(semantics_accumulator)
        and all(semantics_accumulator.values()),
        "actor_critic_changed_in_life": initial_state["digests"]["actor_critic"]
        != final_state["digests"]["actor_critic"],
        "auxiliary_heads_changed_in_life": initial_state["digests"]["auxiliary_heads"]
        != final_state["digests"]["auxiliary_heads"],
        "auxiliary_heads_zero_at_birth": bool(initial_state["auxiliary_heads_zero"]),
        "neural_writer_scaffold_dormant": initial_state["digests"]["writer"]
        == final_state["digests"]["writer"],
        "writer_optimizer_dormant": _optimizer_tensor_count(
            descendant.learner.writer_optimizer
        )
        == 0,
        "birth_carrier_unchanged_inside_life": np.array_equal(
            descendant.learner.germ, initial_germ
        ),
        "incoming_packet_exactly_64_bytes": initial_germ.nbytes == 64,
        "controller_call_presence_exact": (int(tracker["calls"]) > 0)
        == external_expected,
        "controller_context_count_exact": int(tracker["contexts"])
        == expected_controller_contexts,
        "controller_never_changed_inherited_germ": bool(
            tracker["germ_unchanged_each_call"]
            and tracker["germ_restored_after_every_context"]
        ),
        "controller_packet_unchanged": bool(tracker["controller_unchanged_each_call"]),
        "controller_absent_from_descendant_fields": not any(
            "controller" in name.lower() for name in vars(descendant.learner)
        ),
        "controller_absent_from_checkpoint_state": controller_absent_from_checkpoint,
        "post_key_mask_exact": post_key_mask_exact,
        "checkpoint_reloads_with_leak_probe": checkpoint_verified,
        "scientific_matched_behavior_outcome_not_completion_gate": True,
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "source_run_id": SOURCE_RUN,
        "founder": founder,
        "generation": GENERATION,
        "arm": arm,
        "birth_seed": birth_seed,
        "training_seed": training_seed,
        "updates": UPDATES,
        "environment_steps": EXPECTED_STEPS,
        "cutoff_update": CUTOFF_UPDATE,
        "reward_mode": "terminal",
        "phase_credit_mode": "phase_actor",
        "config": asdict(config),
        "parent_checkpoint": str(spec["parent_checkpoint"]),
        "parent_checkpoint_sha256": spec["parent_checkpoint_sha256"],
        "source_carrier_sha256": spec["source_carrier_sha256"],
        "incoming_carrier": incoming.tolist(),
        "incoming_carrier_sha256": packet.digest(),
        "incoming_decoded": {
            "active": incoming_read.active.tolist(),
            "targets": incoming_read.prior_logits.argmax(axis=-1).tolist(),
            "trust": incoming_read.trust.tolist(),
            "freshness": incoming_read.freshness.tolist(),
            "address_valid": incoming_read.address_valid.tolist(),
            "checksum_valid": incoming_read.checksum_valid.tolist(),
        },
        "post_key_mask_sha256": carrier_digest(post_key),
        "post_key_mask_decoded": {
            "active": post_key_read.active.tolist(),
            "targets": post_key_read.prior_logits.argmax(axis=-1).tolist(),
            "checksum_valid": post_key_read.checksum_valid.tolist(),
        },
        "boundary_audit": boundary,
        "external_expression_audit": tracker,
        "history": history,
        "evaluations": evaluations,
        "learning_auc": {
            action_mode: frozen_vertical.learning_auc(evaluations, action_mode)
            for action_mode in ACTION_MODES
        },
        "post_cutoff_learning_auc": {
            action_mode: segment_learning_auc(
                evaluations, action_mode, CUTOFF_UPDATE, UPDATES
            )
            for action_mode in ACTION_MODES
        },
        "final_evaluations": final_evaluations,
        "final_world_rows": final_world_rows,
        "episodes_completed": total_episodes,
        "training_goal_successes": total_successes,
        "cumulative_event_counts": cumulative_events,
        "first_signal_update": first_signal_update,
        "first_evaluation_reach": {
            action_mode: _first_evaluation_reach(evaluations, action_mode)
            for action_mode in ACTION_MODES
        },
        "initial_state": initial_state,
        "final_state": final_state,
        "cutoff_soma_environment_digests": cutoff_digests,
        "final_soma_environment_digests": final_digests,
        "early_behavior_sha256": early_behavior_sha256,
        "post_cutoff_behavior_sha256": post_behavior_sha256,
        "behavior_fingerprint": full_behavior_sha256,
        "rollout_semantics": semantics_accumulator,
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "completion_gates": gates,
        "completed_cleanly": all(gates.values()),
    }
    atomic_json(result_path, result, output_root)
    atomic_json(
        progress_path,
        {
            "status": "COMPLETE" if result["completed_cleanly"] else "FAILED_GATES",
            "updated_utc": utc_now(),
            "founder": founder,
            "generation": GENERATION,
            "arm": arm,
            "update": UPDATES,
            "training_goal_successes": total_successes,
            "cumulative_event_counts": cumulative_events,
            "incoming_carrier_sha256": packet.digest(),
            "result_path": str(result_path),
        },
        output_root,
    )
    if not result["completed_cleanly"]:
        raise RuntimeError(f"founder {founder} {stem} failed gates: {gates}")
    return result


def _worker_train_cell(
    spec: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    output_root_text: str,
    output_dir_text: str,
) -> dict[str, Any]:
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    return _train_cell(
        spec,
        FeedbackPPOConfig(**dict(config_payload)),
        Path(output_root_text),
        Path(output_dir_text),
    )


def matched_behavior_audit(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply the registered exact disposition-versus-controller endpoint."""

    by_cell = {(int(row["founder"]), str(row["arm"])): row for row in results}
    founder_rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        germ = by_cell[(founder, "early_germ")]
        controller = by_cell[(founder, "early_controller")]
        early_exact = (
            germ["early_behavior_sha256"] == controller["early_behavior_sha256"]
        )
        cutoff_left = germ["cutoff_soma_environment_digests"]
        cutoff_right = controller["cutoff_soma_environment_digests"]
        cutoff_exact = cutoff_left["aggregate"] == cutoff_right["aggregate"]
        post_exact = (
            germ["post_cutoff_behavior_sha256"]
            == controller["post_cutoff_behavior_sha256"]
        )
        final_left = germ["final_soma_environment_digests"]
        final_right = controller["final_soma_environment_digests"]
        final_exact = final_left["aggregate"] == final_right["aggregate"]
        cutoff_differences = sorted(
            name
            for name in set(cutoff_left) | set(cutoff_right)
            if cutoff_left.get(name) != cutoff_right.get(name)
        )
        final_differences = sorted(
            name
            for name in set(final_left) | set(final_right)
            if final_left.get(name) != final_right.get(name)
        )
        gates = {
            "early_behavior_exact": early_exact,
            "cutoff_soma_environment_exact": cutoff_exact,
            "post_cutoff_behavior_exact": post_exact,
            "final_soma_environment_exact": final_exact,
        }
        founder_rows.append(
            {
                "founder": founder,
                "early_germ_sha256": germ["early_behavior_sha256"],
                "early_controller_sha256": controller["early_behavior_sha256"],
                "cutoff_germ_sha256": cutoff_left["aggregate"],
                "cutoff_controller_sha256": cutoff_right["aggregate"],
                "post_germ_sha256": germ["post_cutoff_behavior_sha256"],
                "post_controller_sha256": controller["post_cutoff_behavior_sha256"],
                "final_germ_sha256": final_left["aggregate"],
                "final_controller_sha256": final_right["aggregate"],
                "cutoff_differing_components": cutoff_differences,
                "final_differing_components": final_differences,
                "gates": gates,
                "all_four_exact": all(gates.values()),
            }
        )

    all_exact = len(founder_rows) == len(FOUNDERS) and all(
        row["all_four_exact"] for row in founder_rows
    )
    learning_path_detected = any(
        row["gates"]["early_behavior_exact"]
        and not (
            row["gates"]["cutoff_soma_environment_exact"]
            and row["gates"]["post_cutoff_behavior_exact"]
            and row["gates"]["final_soma_environment_exact"]
        )
        for row in founder_rows
    )
    if all_exact:
        classification = "DIRECT_ACTION_SHAPING_SUFFICIENT_3_OF_3"
        disposition = "NO_SEPARATE_GERM_DISPOSITION_DETECTED_3_OF_3"
    elif learning_path_detected:
        classification = "GERM_SPECIFIC_LEARNING_PATH_DETECTED"
        disposition = "SEPARATE_GERM_DISPOSITION_DETECTED"
    else:
        classification = "BEHAVIOR_MATCH_FAILED"
        disposition = "DISPOSITION_CONTRAST_INVALID"
    return {
        "classification": classification,
        "disposition_classification": disposition,
        "founder_results": founder_rows,
        "all_three_founders_all_four_exact": all_exact,
        "exact_equality_endpoint_no_tolerance": True,
        "scientific_outcome_used_as_completion_gate": False,
        "scope": "frozen_DoorKey_reader_and_phase_credit_PPO_only",
    }


def exact_blind_silence_alias_audit(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify unread correct bytes have no route absent in empty silence."""

    by_cell = {(int(row["founder"]), str(row["arm"])): row for row in results}
    rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        blind = by_cell[(founder, "carrier_blind")]
        silence = by_cell[(founder, "silence")]
        behavior_exact = (
            blind["behavior_fingerprint"] == silence["behavior_fingerprint"]
        )
        cutoff_exact = (
            blind["cutoff_soma_environment_digests"]["aggregate"]
            == silence["cutoff_soma_environment_digests"]["aggregate"]
        )
        final_exact = (
            blind["final_soma_environment_digests"]["aggregate"]
            == silence["final_soma_environment_digests"]["aggregate"]
        )
        rows.append(
            {
                "founder": founder,
                "behavior_exact": behavior_exact,
                "cutoff_soma_environment_exact": cutoff_exact,
                "final_soma_environment_exact": final_exact,
                "blind_behavior_sha256": blind["behavior_fingerprint"],
                "silence_behavior_sha256": silence["behavior_fingerprint"],
                "exact": behavior_exact and cutoff_exact and final_exact,
            }
        )
    return {"comparisons": rows, "passes": all(row["exact"] for row in rows)}


def cell_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "founder": int(result["founder"]),
        "generation": int(result["generation"]),
        "arm": str(result["arm"]),
        "incoming_carrier_sha256": result["incoming_carrier_sha256"],
        "source_carrier_sha256": result["source_carrier_sha256"],
        "learning_auc": result["learning_auc"],
        "post_cutoff_learning_auc": result["post_cutoff_learning_auc"],
        "training_events": dict(result["cumulative_event_counts"]),
        "training_goal_successes": int(result["training_goal_successes"]),
        "final_fixed_successes": int(
            result["final_evaluations"]["fixed_random"]["successes"]
        ),
        "final_deterministic_successes": int(
            result["final_evaluations"]["deterministic"]["successes"]
        ),
        "early_behavior_sha256": result["early_behavior_sha256"],
        "post_cutoff_behavior_sha256": result["post_cutoff_behavior_sha256"],
        "behavior_fingerprint": result["behavior_fingerprint"],
        "cutoff_soma_environment_sha256": result["cutoff_soma_environment_digests"][
            "aggregate"
        ],
        "final_soma_environment_sha256": result["final_soma_environment_digests"][
            "aggregate"
        ],
        "completed_cleanly": bool(result["completed_cleanly"]),
    }


def descriptive_contrasts(
    results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return outcome-open causal-chain differences with no pass threshold."""

    by_cell = {(int(row["founder"]), str(row["arm"])): row for row in results}
    comparisons = (
        ("persistent_germ", "early_germ", "continuing_reader_after_cutoff"),
        ("delayed_germ", "silence", "late_reader"),
        ("post_key_germ", "silence", "post_key_open_only_reader"),
        ("wrong_early", "early_germ", "wrong_vs_correct_early"),
        ("wrong_early", "silence", "wrong_early_vs_silence"),
        ("early_germ", "silence", "correct_early_carryover"),
        ("early_controller", "silence", "controller_early_carryover"),
    )
    rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        for left_arm, right_arm, label in comparisons:
            left = by_cell[(founder, left_arm)]
            right = by_cell[(founder, right_arm)]
            full_events: dict[str, float] = {}
            post_events: dict[str, float] = {}
            for event in CAUSAL_CHAIN:
                full_events[event] = float(
                    left["learning_auc"]["fixed_random"]["events"][event][
                        "reached_fraction_auc"
                    ]
                    - right["learning_auc"]["fixed_random"]["events"][event][
                        "reached_fraction_auc"
                    ]
                )
                post_events[event] = float(
                    left["post_cutoff_learning_auc"]["fixed_random"]["events"][event][
                        "reached_fraction_auc"
                    ]
                    - right["post_cutoff_learning_auc"]["fixed_random"]["events"][
                        event
                    ]["reached_fraction_auc"]
                )
            rows.append(
                {
                    "founder": founder,
                    "contrast": label,
                    "left": left_arm,
                    "right": right_arm,
                    "fixed_random_full_reached_auc_difference": full_events,
                    "fixed_random_post_cutoff_reached_auc_difference": post_events,
                    "training_goal_difference": int(left["training_goal_successes"])
                    - int(right["training_goal_successes"]),
                    "final_fixed_goal_difference": int(
                        left["final_evaluations"]["fixed_random"]["successes"]
                    )
                    - int(right["final_evaluations"]["fixed_random"]["successes"]),
                }
            )
    return rows


def markdown_report(study: Mapping[str, Any]) -> str:
    outcome = study["matched_behavior_audit"]
    lines = [
        "# DoorKey matched-behavior disposition test v1",
        "",
        f"**Structural completion:** `{'PASS' if study['completed_cleanly'] else 'FAIL'}`  ",
        f"**Registered classification:** `{outcome['classification']}`  ",
        f"**Disposition statement:** `{outcome['disposition_classification']}`",
        "",
        "## Exact inherited-germ versus external-controller comparison",
        "",
        "| Founder | Early behavior | Cutoff soma + environment | Later behavior | Final soma + environment |",
        "|---:|---|---|---|---|",
    ]
    for row in outcome["founder_results"]:
        gates = row["gates"]
        lines.append(
            f"| {row['founder']} | "
            f"`{'EXACT' if gates['early_behavior_exact'] else 'DIFF'}` | "
            f"`{'EXACT' if gates['cutoff_soma_environment_exact'] else 'DIFF'}` | "
            f"`{'EXACT' if gates['post_cutoff_behavior_exact'] else 'DIFF'}` | "
            f"`{'EXACT' if gates['final_soma_environment_exact'] else 'DIFF'}` |"
        )
    lines.extend(
        [
            "",
            "## Unread-carrier apparatus alias",
            "",
        ]
    )
    for row in study["blind_silence_alias_audit"]["comparisons"]:
        lines.append(
            f"- Founder {row['founder']}: `carrier_blind == silence` "
            f"is `{'EXACT' if row['exact'] else 'DIFFERENT'}`."
        )
    lines.extend(["", "## Cell outcomes", ""])
    lines.append(
        "| Founder | Arm | Open-door AUC | Post-cutoff open AUC | Training goals | Final fixed goals |"
    )
    lines.append("|---:|---|---:|---:|---:|---:|")
    for row in study["cell_summaries"]:
        full = row["learning_auc"]["fixed_random"]["events"]["open_door"][
            "reached_fraction_auc"
        ]
        post = row["post_cutoff_learning_auc"]["fixed_random"]["events"]["open_door"][
            "reached_fraction_auc"
        ]
        lines.append(
            f"| {row['founder']} | `{row['arm']}` | {full:.6f} | "
            f"{post:.6f} | {row['training_goal_successes']} | "
            f"{row['final_fixed_successes']} |"
        )
    lines.extend(["", "## Structural completion gates", ""])
    for name, passed in study["completion_gates"].items():
        lines.append(f"- `{name}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            (
                "The exact classification addresses only the frozen DoorKey "
                "reader and phase-credit PPO. It does not exclude future "
                "64-byte mechanisms with carrier-conditioned values or other "
                "learning-specific interfaces, and it does not establish the "
                "universal wording of L17 or L20."
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
    source_output = root / "outputs" / SOURCE_RUN
    source_run = root / "runs" / SOURCE_RUN
    source_manifest = json.loads(
        (source_run / "MANIFEST.json").read_text(encoding="utf-8")
    )
    paths = [
        workspace / "protocols/DOORKEY_MATCHED_BEHAVIOR_DISPOSITION_V1.md",
        workspace / "requirements-doorkey.lock",
        Path(__file__).resolve(),
        workspace / "src/laws_confirmation/doorkey_vertical_multifounder.py",
        workspace / "src/laws_confirmation/doorkey_vertical_scout.py",
        workspace / "src/laws_confirmation/doorkey_phase_value_credit.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/io.py",
        workspace / "tests/test_doorkey_matched_disposition.py",
        workspace / "scripts/run_doorkey_matched_disposition.sh",
        workspace / "scripts/run_doorkey_matched_disposition_detached.sh",
        source_output / "confirmation.json",
        source_output / "audit.md",
        source_output / "input_hashes.sha256",
        source_output / "output_hashes.sha256",
        source_run / "MANIFEST.json",
        source_run / "STATUS.json",
        source_run / "COMPLETE",
    ]
    paths.extend(Path(path) for path in source_manifest.get("input_sha256", {}))
    for parent in source["parents"]:
        paths.extend((Path(parent["result"]), Path(parent["checkpoint"])))
    unique = sorted({path.resolve() for path in paths})
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen matched-disposition inputs: {missing}")
    return unique


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


def run_study(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if args.run_id != RUN_ID:
        raise ValueError(f"frozen run ID must be {RUN_ID}")
    if args.workers != MAX_WORKERS:
        raise ValueError(f"frozen study requires exactly {MAX_WORKERS} workers")
    root = external_root(args.external_root)
    output_dir = root / "outputs" / args.run_id
    run_dir = root / "runs" / args.run_id
    workspace = Path(__file__).resolve().parents[2]
    source = qualify_sources(root)
    if not source["passes"]:
        raise RuntimeError(f"frozen source qualification failed: {source['gates']}")
    config = FeedbackPPOConfig(**dict(source["parents"][0]["config"]))
    specs = cell_specs(source)
    input_paths = _input_paths(workspace, root, source)
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    contract_digest = canonical_digest(input_hashes)
    disk = _disk_preflight(root, 128 * 1024 * 1024)
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
            (output_dir / f"founder_{founder}" / "progress").mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "run_id": args.run_id,
            "source_run_id": SOURCE_RUN,
            "stage": "DoorKey matched-behavior disposition decomposition",
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
            "generation": GENERATION,
            "arms": list(ARMS),
            "cutoff_update": CUTOFF_UPDATE,
            "registered_cells": REGISTERED_CELLS,
            "updates_per_cell": UPDATES,
            "transitions_per_cell": EXPECTED_STEPS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "exact_equality_endpoint": True,
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
        training_started = time.monotonic()
        results: list[dict[str, Any]] = []
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
                    results.append(future.result())
                except Exception as error:
                    raise RuntimeError(
                        f"founder {spec['founder']} G4 {spec['arm']} worker failed"
                    ) from error
                atomic_json(
                    output_dir / "progress.json",
                    {
                        "status": "RUNNING",
                        "updated_utc": utc_now(),
                        "completed_cells": len(results),
                        "registered_cells": REGISTERED_CELLS,
                    },
                    root,
                )
        elapsed_training = time.monotonic() - training_started
        results.sort(key=lambda row: (int(row["founder"]), ARMS.index(str(row["arm"]))))
        unique_cells = {
            (int(row["founder"]), int(row["generation"]), str(row["arm"]))
            for row in results
        }
        matched = matched_behavior_audit(results)
        alias = exact_blind_silence_alias_audit(results)
        summaries = [cell_summary(row) for row in results]
        contrasts = descriptive_contrasts(results)
        expected_source_digests = {
            int(parent["founder"]): parent["outgoing_carrier_sha256"]
            for parent in source["parents"]
        }
        expected_post_key_digests = {
            int(parent["founder"]): carrier_digest(
                make_post_key_mask(
                    np.asarray(parent["outgoing_carrier"], dtype=np.uint8)
                )
            )
            for parent in source["parents"]
        }
        expected_incoming_digests = {
            (int(spec["founder"]), str(spec["arm"])): carrier_digest(
                np.asarray(spec["incoming_germ"], dtype=np.uint8)
            )
            for spec in specs
        }
        completion_gates = {
            "runtime_qualified": bool(runtime["passes"]),
            "frozen_sources_qualified": bool(source["passes"]),
            "exactly_24_registered_cells": len(results) == REGISTERED_CELLS
            and len(unique_cells) == REGISTERED_CELLS,
            "all_cells_registered_to_study": all(
                row.get("run_id") == RUN_ID
                and row.get("source_run_id") == SOURCE_RUN
                and row.get("generation") == GENERATION
                for row in results
            ),
            "all_cells_completed_cleanly": all(
                bool(row["completed_cleanly"]) for row in results
            ),
            "all_cells_100_updates": all(row["updates"] == UPDATES for row in results),
            "all_cells_expected_transitions": all(
                row["environment_steps"] == EXPECTED_STEPS for row in results
            ),
            "all_24_boundaries_reset": all(
                row["boundary_audit"]["passes"] for row in results
            ),
            "all_parent_checkpoint_links_exact": all(
                row["boundary_audit"]["parent_checkpoint_sha256"]
                == row["parent_checkpoint_sha256"]
                for row in results
            ),
            "all_source_carrier_links_exact": all(
                row["source_carrier_sha256"]
                == expected_source_digests[int(row["founder"])]
                for row in results
            ),
            "all_birth_packets_exactly_64_bytes": all(
                np.asarray(row["incoming_carrier"], dtype=np.uint8).nbytes == 64
                for row in results
            ),
            "all_registered_incoming_interventions_exact": all(
                row["incoming_carrier_sha256"]
                == expected_incoming_digests[(int(row["founder"]), str(row["arm"]))]
                for row in results
            ),
            "all_controller_calls_preserved_inherited_germ": all(
                row["completion_gates"]["controller_never_changed_inherited_germ"]
                and row["completion_gates"]["controller_packet_unchanged"]
                for row in results
            ),
            "controller_absent_from_all_descendant_and_checkpoint_state": all(
                row["completion_gates"]["controller_absent_from_descendant_fields"]
                and row["completion_gates"]["controller_absent_from_checkpoint_state"]
                for row in results
            ),
            "post_key_masks_valid_and_source_exact": all(
                row["completion_gates"]["post_key_mask_exact"]
                and row["post_key_mask_sha256"]
                == expected_post_key_digests[int(row["founder"])]
                for row in results
            ),
            "all_writer_scaffolds_and_optimizers_dormant": all(
                row["completion_gates"]["neural_writer_scaffold_dormant"]
                and row["completion_gates"]["writer_optimizer_dormant"]
                for row in results
            ),
            "all_metrics_finite": all(
                _finite_credit_history(row["history"]) for row in results
            ),
            "all_rollout_semantics_pass": all(
                row["completion_gates"]["all_rollout_semantics_pass"] for row in results
            ),
            "all_final_evaluations_replay_exactly": all(
                row["completion_gates"]["final_evaluations_replay_exactly"]
                for row in results
            ),
            "all_checkpoints_reload": all(
                row["completion_gates"]["checkpoint_reloads_with_leak_probe"]
                for row in results
            ),
            "carrier_blind_equals_silence_all_founders": bool(alias["passes"]),
            "four_workers_one_thread": args.workers == MAX_WORKERS
            and runtime["values"]["torch_num_threads"] == 1,
            "scientific_outcomes_not_used_as_completion_gates": True,
        }
        study = {
            "schema_version": 1,
            "run_id": args.run_id,
            "source_run_id": SOURCE_RUN,
            "generated_utc": utc_now(),
            "status": "MATCHED_BEHAVIOR_MECHANISM_DECOMPOSITION",
            "runtime": runtime,
            "sources": source,
            "config": asdict(config),
            "seeds": SEEDS,
            "founders": list(FOUNDERS),
            "generation": GENERATION,
            "arms": list(ARMS),
            "cutoff_update": CUTOFF_UPDATE,
            "cell_specs": specs,
            "cell_result_files": [
                str(output_dir / f"founder_{row['founder']}" / f"g4_{row['arm']}.json")
                for row in results
            ],
            "cell_summaries": summaries,
            "matched_behavior_audit": matched,
            "blind_silence_alias_audit": alias,
            "descriptive_contrasts": contrasts,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "registered_cells": REGISTERED_CELLS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "elapsed_training_seconds": elapsed_training,
            "max_workers": MAX_WORKERS,
            "threads_per_worker": 1,
            "numbered_law_verdict_changes": 0,
        }
        atomic_json(output_dir / "disposition.json", study, root)
        atomic_text(output_dir / "audit.md", markdown_report(study), root)
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
        status_ok = bool(study["completed_cleanly"] and outputs_verify)
        status = {
            "status": "COMPLETE" if status_ok else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "completed_cleanly": bool(study["completed_cleanly"]),
            "output_manifest_self_verifies": outputs_verify,
            "registered_cells": REGISTERED_CELLS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "max_workers": MAX_WORKERS,
            "classification": matched["classification"],
            "disposition_classification": matched["disposition_classification"],
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
    return run_study(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
