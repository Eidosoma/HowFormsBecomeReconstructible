"""Qualify the baseline-aware causal writer on four frozen DoorKey parents."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import platform
import re
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch.nn import functional as F

from .doorkey_boundary import make_boundary_packet
from .doorkey_carrier import (
    GermSchema,
    carrier_digest,
    corrupt_byte,
    empty_germ,
    permute_payloads,
    read_germ,
)
from .doorkey_causal_writer import (
    CausalWriterLedger,
    MIN_VERIFIED_EFFECTS,
    SLOT_NAMES,
    derive_causal_writer_decision,
    expected_interaction_actions,
    ledger_storage_bytes,
    renew_germ_from_causal_evidence,
)
from .doorkey_env import Action, CAUSAL_CHAIN, DoorKeyEnv, TRANSFORMS, make_layout, oracle_plan
from .doorkey_feedback_scout import _disk_preflight, _read_hash_manifest
from .doorkey_phase_value_credit import (
    CausalCreditDescendant,
    causal_credit_digests,
    make_causal_credit_descendant,
)
from .doorkey_ppo_v2 import (
    START_ACTION,
    FeedbackPPOConfig,
    _apply_prior,
    _conditional_chain,
    _module_digest,
    birth_feedback_ppo_descendant,
)
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


RUN_ID = "doorkey_causal_writer_qualification_v1_attempt1"
ASSAY_LAYOUT_SEED = 82_000_000
ASSAY_ACTION_SEED = 83_000_000
CHILD_SEED = 84_000_000
WORLDS_PER_TRANSFORM = 8
STOCHASTIC_REPEATS = 4
EXPECTED_CHECKPOINT_HASHES = (
    "7a5097d1d07132bc67cdfb524e7b365af49a6d307578423fb31fac519a501523",
    "d91c5f7dfc97d2604e7c6a93465d17af1d76de06df44c46e82bd646c26c484cd",
    "9f24c2d84c91ef05652f3c525f1078edf06ab31023783fd76c37f5b9d7473a9f",
    "055a5c77e9f91286b7bd75b592fa54d793b9bc2ec1996b75ae5dd035ef2b6cbf",
)


def parent_specs(root: Path) -> list[dict[str, Any]]:
    scout_output = root / "outputs/doorkey_phase_value_credit_scout_v1_attempt1"
    multi_output = root / "outputs/doorkey_phase_value_credit_multiseed_v1_attempt1"
    return [
        {
            "parent": 0,
            "birth_seed": 920_000,
            "checkpoint": scout_output / "phase_actor_checkpoint.pt",
            "result": scout_output / "phase_actor.json",
            "source_output": scout_output,
            "source_run": root / "runs/doorkey_phase_value_credit_scout_v1_attempt1",
            "expected_sha256": EXPECTED_CHECKPOINT_HASHES[0],
        },
        *[
            {
                "parent": parent,
                "birth_seed": 923_000 + 1_000 * parent,
                "checkpoint": multi_output
                / f"phase_actor_replicate_{parent}_checkpoint.pt",
                "result": multi_output / f"phase_actor_replicate_{parent}.json",
                "source_output": multi_output,
                "source_run": root
                / "runs/doorkey_phase_value_credit_multiseed_v1_attempt1",
                "expected_sha256": EXPECTED_CHECKPOINT_HASHES[parent],
            }
            for parent in range(1, 4)
        ],
    ]


def runtime_qualification() -> dict[str, Any]:
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
    }
    gates = {
        "python_3_13": platform.python_version_tuple()[:2] == ("3", "13"),
        "numpy_2_5_2": np.__version__ == "2.5.2",
        "torch_2_14_cpu": torch.__version__ == "2.14.0+cpu",
        "cuda_disabled": not torch.cuda.is_available(),
        "intraop_threads_one": torch.get_num_threads() == 1,
        "interop_threads_one": torch.get_num_interop_threads() == 1,
    }
    return {"values": values, "gates": gates, "passes": all(gates.values())}


def _verify_recorded_inputs(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = []
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


def qualify_parent_bank(root: Path, specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    source_groups: dict[str, dict[str, Any]] = {}
    for spec in specs:
        output = Path(spec["source_output"])
        run = Path(spec["source_run"])
        key = str(output)
        if key not in source_groups:
            status = json.loads((run / "STATUS.json").read_text(encoding="utf-8"))
            source_groups[key] = {
                "output": key,
                "run": str(run),
                "complete_sentinel": (run / "COMPLETE").is_file(),
                "status_complete": status.get("status") == "COMPLETE",
                "input_rows": _verify_recorded_inputs(run / "MANIFEST.json"),
                "output_rows": _read_hash_manifest(output / "output_hashes.sha256"),
            }
    parent_rows = []
    expected_empty = empty_germ(1)
    for spec in specs:
        checkpoint_path = Path(spec["checkpoint"])
        result_path = Path(spec["result"])
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        result = json.loads(result_path.read_text(encoding="utf-8"))
        parent_rows.append(
            {
                "parent": int(spec["parent"]),
                "birth_seed": int(spec["birth_seed"]),
                "checkpoint": str(checkpoint_path),
                "checkpoint_sha256": sha256_file(checkpoint_path),
                "expected_checkpoint_sha256": str(spec["expected_sha256"]),
                "checkpoint_hash_matches": sha256_file(checkpoint_path)
                == spec["expected_sha256"],
                "checkpoint_arm": checkpoint.get("arm"),
                "checkpoint_birth_seed": checkpoint.get("birth_seed"),
                "checkpoint_updates": checkpoint.get("updates"),
                "checkpoint_empty_germ": bool(
                    np.array_equal(checkpoint.get("germ"), expected_empty)
                ),
                "result_completed": bool(result.get("completed_cleanly")),
                "result_arm": result.get("arm"),
            }
        )
    gates = {
        "two_source_runs_exact": len(source_groups) == 2,
        "all_source_runs_complete": all(
            row["complete_sentinel"] and row["status_complete"]
            for row in source_groups.values()
        ),
        "all_recorded_inputs_verify": all(
            item["matches"]
            for row in source_groups.values()
            for item in row["input_rows"]
        ),
        "all_recorded_outputs_verify": all(
            row["output_rows"]
            and all(item["matches"] for item in row["output_rows"])
            for row in source_groups.values()
        ),
        "four_exact_parent_rows": len(parent_rows) == 4,
        "all_checkpoint_hashes_match": all(
            row["checkpoint_hash_matches"] for row in parent_rows
        ),
        "all_phase_actor_100_updates": all(
            row["checkpoint_arm"] == "phase_actor"
            and row["result_arm"] == "phase_actor"
            and row["checkpoint_updates"] == 100
            and row["result_completed"]
            for row in parent_rows
        ),
        "all_birth_seeds_match": all(
            row["checkpoint_birth_seed"] == row["birth_seed"]
            for row in parent_rows
        ),
        "all_source_germs_empty": all(row["checkpoint_empty_germ"] for row in parent_rows),
    }
    return {
        "source_groups": list(source_groups.values()),
        "parent_rows": parent_rows,
        "gates": gates,
        "passes": all(gates.values()),
    }


def load_parent_and_birth(
    checkpoint_path: Path,
) -> tuple[CausalCreditDescendant, CausalCreditDescendant, FeedbackPPOConfig, dict[str, Any]]:
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = FeedbackPPOConfig(**payload["config"])
    birth_seed = int(payload["birth_seed"])
    parent = make_causal_credit_descendant(config, birth_seed)
    parent.learner.model.load_state_dict(payload["model_state_dict"])
    parent.auxiliary_heads.load_state_dict(payload["auxiliary_heads_state_dict"])
    parent.learner.writer.load_state_dict(payload["writer_state_dict"])
    parent.learner.germ = np.array(payload["germ"], dtype=np.uint8, copy=True)
    birth = make_causal_credit_descendant(config, birth_seed)
    return parent, birth, config, payload


def collect_writer_assay(
    parent: CausalCreditDescendant,
    birth: CausalCreditDescendant,
    config: FeedbackPPOConfig,
) -> tuple[CausalWriterLedger, list[dict[str, Any]], dict[str, Any]]:
    envs: list[DoorKeyEnv] = []
    stream_ids: list[int] = []
    for transform_index, transform in enumerate(TRANSFORMS):
        for local_seed in range(WORLDS_PER_TRANSFORM):
            seed = ASSAY_LAYOUT_SEED + transform_index * 10_000 + local_seed
            for stream in range(STOCHASTIC_REPEATS):
                envs.append(
                    DoorKeyEnv(make_layout(seed, transform), max_steps=config.max_episode_steps)
                )
                stream_ids.append(stream)
    count = len(envs)
    final_hidden = torch.zeros((count, config.hidden_size), dtype=torch.float32)
    birth_hidden = torch.zeros_like(final_hidden)
    previous_action = torch.full((count,), START_ACTION, dtype=torch.long)
    previous_reward = torch.zeros(count, dtype=torch.float32)
    episode_start = torch.ones(count, dtype=torch.bool)
    active = np.ones(count, dtype=bool)
    uniforms = np.random.default_rng(ASSAY_ACTION_SEED).random(
        (config.max_episode_steps, count)
    )
    ledger = CausalWriterLedger.empty()
    parent.learner.model.eval()
    birth.learner.model.eval()
    recurrent_bytes = (
        final_hidden.numel() * final_hidden.element_size()
        + birth_hidden.numel() * birth_hidden.element_size()
    )

    for step in range(config.max_episode_steps):
        before_np = np.stack([env.observation().vector() for env in envs])
        observations = torch.from_numpy(before_np).to(dtype=torch.float32)
        with torch.no_grad():
            final_logits, _, next_final_hidden = parent.learner.model.forward_step(
                observations,
                final_hidden,
                episode_start,
                previous_action,
                previous_reward,
            )
            birth_logits, _, next_birth_hidden = birth.learner.model.forward_step(
                observations,
                birth_hidden,
                episode_start,
                previous_action,
                previous_reward,
            )
            final_probabilities = F.softmax(final_logits, dim=-1).cpu().numpy()
            birth_probabilities = F.softmax(birth_logits, dim=-1).cpu().numpy()
            cumulative = np.cumsum(final_probabilities, axis=1)
            action_np = (uniforms[step, :, None] > cumulative).sum(axis=1)
            action_np = np.minimum(action_np, config.num_actions - 1)
        reward_np = np.zeros(count, dtype=np.float32)
        done_indices: list[int] = []
        for index in np.flatnonzero(active):
            after, reward, terminated, truncated, info = envs[index].step(
                int(action_np[index])
            )
            reward_np[index] = reward
            ledger.record(
                before_np[index],
                int(action_np[index]),
                after.vector(),
                info,
                birth_probabilities[index],
                final_probabilities[index],
            )
            if terminated or truncated:
                active[index] = False
                done_indices.append(int(index))
        final_hidden = next_final_hidden
        birth_hidden = next_birth_hidden
        previous_action = torch.from_numpy(action_np).to(dtype=torch.long)
        previous_reward = torch.from_numpy(reward_np)
        episode_start = torch.zeros_like(episode_start)
        if done_indices:
            final_hidden[done_indices] = 0.0
            birth_hidden[done_indices] = 0.0
            previous_action[done_indices] = START_ACTION
            previous_reward[done_indices] = 0.0
        if not active.any():
            break
    rows = [
        {
            "layout_seed": env.layout.seed,
            "transform": env.layout.transform,
            "action_stream": stream_ids[index],
            "success": env.terminated,
            "truncated": env.truncated,
            "episode_steps": env.steps,
            "event_steps": dict(env.event_steps),
            "auxiliary_steps": dict(env.auxiliary_steps),
        }
        for index, env in enumerate(envs)
    ]
    summary = {
        "world_count": count,
        "unique_layout_count": WORLDS_PER_TRANSFORM * len(TRANSFORMS),
        "successes": sum(bool(row["success"]) for row in rows),
        "conditional_chain": _conditional_chain(rows),
        "recurrent_comparator_bytes": recurrent_bytes,
    }
    return ledger, rows, summary


def _model_parameter_bytes(module: torch.nn.Module) -> int:
    return int(sum(value.numel() * value.element_size() for value in module.parameters()))


def qualify_one_parent(spec: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    parent, birth, config, _ = load_parent_and_birth(Path(spec["checkpoint"]))
    before = causal_credit_digests(parent)
    ledger, rows, summary = collect_writer_assay(parent, birth, config)
    after = causal_credit_digests(parent)
    decision = derive_causal_writer_decision(ledger)
    renewal = renew_germ_from_causal_evidence(ledger, parent.learner.germ)
    decoded = read_germ(renewal.germ)

    replay_parent, replay_birth, replay_config, _ = load_parent_and_birth(
        Path(spec["checkpoint"])
    )
    replay_ledger, replay_rows, replay_summary = collect_writer_assay(
        replay_parent, replay_birth, replay_config
    )
    replay_decision = derive_causal_writer_decision(replay_ledger)
    replay_renewal = renew_germ_from_causal_evidence(
        replay_ledger, replay_parent.learner.germ
    )
    replay_exact = bool(
        ledger.to_dict() == replay_ledger.to_dict()
        and rows == replay_rows
        and summary == replay_summary
        and decision.to_dict() == replay_decision.to_dict()
        and np.array_equal(renewal.germ, replay_renewal.germ)
    )
    expected = expected_interaction_actions()
    gates = {
        "parent_state_unchanged": before == after,
        "writer_assay_replay_exact": replay_exact,
        "expected_episode_count": len(rows)
        == WORLDS_PER_TRANSFORM * len(TRANSFORMS) * STOCHASTIC_REPEATS,
        "all_carrier_addresses_and_checksums_valid": bool(
            decoded.address_valid.all() and decoded.checksum_valid.all()
        ),
        "carrier_exactly_64_bytes": renewal.germ.nbytes == 64,
        "key_record_readable": bool(decoded.active[0, 1]),
        "key_record_is_pickup": int(decoded.prior_logits[0, 1].argmax())
        == expected[1],
        "door_record_readable": bool(decoded.active[0, 3]),
        "door_record_is_open": int(decoded.prior_logits[0, 3].argmax())
        == expected[3],
        "navigation_slots_abstain": not bool(decoded.active[0, 0])
        and not bool(decoded.active[0, 2]),
    }
    result = {
        "parent": int(spec["parent"]),
        "birth_seed": int(spec["birth_seed"]),
        "checkpoint": str(spec["checkpoint"]),
        "config": asdict(config),
        "assay": summary,
        "ledger": ledger.to_dict(),
        "decision": decision.to_dict(),
        "renewal": renewal.to_dict(),
        "carrier": renewal.germ.tolist(),
        "carrier_sha256": carrier_digest(renewal.germ),
        "decoded": {
            "active": decoded.active.tolist(),
            "targets": decoded.prior_logits.argmax(axis=-1).tolist(),
            "trust": decoded.trust.tolist(),
            "freshness": decoded.freshness.tolist(),
        },
        "writer_cost": {
            "transmitted_carrier_bytes": 64,
            "analytic_ledger_array_bytes": ledger_storage_bytes(ledger),
            "reconstructed_birth_comparator_parameter_bytes": _model_parameter_bytes(
                birth.learner.model
            ),
            "neural_writer_scaffold_parameter_bytes_unused": _model_parameter_bytes(
                parent.learner.writer
            ),
            "transient_dual_recurrent_state_bytes": summary[
                "recurrent_comparator_bytes"
            ],
            "assay_transitions": ledger.transition_count,
        },
        "gates": gates,
        "passes": all(gates.values()),
    }
    return result, rows


def _probe_observations() -> tuple[np.ndarray, np.ndarray]:
    key_rows: list[np.ndarray] = []
    door_rows: list[np.ndarray] = []
    for transform_index, transform in enumerate(TRANSFORMS):
        for local_seed in range(WORLDS_PER_TRANSFORM):
            layout = make_layout(
                85_000_000 + transform_index * 10_000 + local_seed, transform
            )
            env = DoorKeyEnv(layout)
            for action in oracle_plan(layout):
                before = env.observation().vector()
                if int(action) == int(Action.PICKUP):
                    key_rows.append(before.copy())
                if int(action) == int(Action.OPEN):
                    door_rows.append(before.copy())
                env.step(action)
    return np.stack(key_rows), np.stack(door_rows)


def _one_step_probabilities(
    descendant: Any, observations_np: np.ndarray, germ_mode: str
) -> np.ndarray:
    config = descendant.model.config
    observations = torch.from_numpy(observations_np).to(dtype=torch.float32)
    count = len(observations_np)
    hidden = torch.zeros((count, config.hidden_size), dtype=torch.float32)
    episode_start = torch.ones(count, dtype=torch.bool)
    previous_action = torch.full((count,), START_ACTION, dtype=torch.long)
    previous_reward = torch.zeros(count, dtype=torch.float32)
    descendant.model.eval()
    with torch.no_grad():
        base_logits, _, _ = descendant.model.forward_step(
            observations,
            hidden,
            episode_start,
            previous_action,
            previous_reward,
        )
        logits, _ = _apply_prior(base_logits, descendant, observations, germ_mode)
        return F.softmax(logits, dim=-1).cpu().numpy()


def qualify_expression_probe(
    parent_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    key_observations, door_observations = _probe_observations()
    rows = []
    all_gates: list[bool] = []
    for parent in parent_results:
        config = FeedbackPPOConfig(**parent["config"])
        carrier = np.asarray(parent["carrier"], dtype=np.uint8)
        zero = empty_germ(1)
        swapped = permute_payloads(carrier, np.asarray([0, 3, 2, 1]))
        key_lesion = corrupt_byte(carrier, 1 * 16 + 4)
        door_lesion = corrupt_byte(carrier, 3 * 16 + 4)
        child_seed = CHILD_SEED + int(parent["parent"])

        def child(germ: np.ndarray):
            return birth_feedback_ppo_descendant(
                make_boundary_packet(germ), config, child_seed
            )

        probabilities: dict[str, dict[str, np.ndarray]] = {}
        for name, germ, mode in (
            ("intact", carrier, "direct_prior"),
            ("zero", zero, "direct_prior"),
            ("blind", carrier, "blind"),
            ("swapped", swapped, "direct_prior"),
            ("key_lesion", key_lesion, "direct_prior"),
            ("door_lesion", door_lesion, "direct_prior"),
        ):
            descendant = child(germ)
            probabilities[name] = {
                "key": _one_step_probabilities(descendant, key_observations, mode),
                "door": _one_step_probabilities(descendant, door_observations, mode),
            }
        key = int(Action.PICKUP)
        door = int(Action.OPEN)
        gates = {
            "intact_raises_pickup": float(probabilities["intact"]["key"][:, key].mean())
            > float(probabilities["zero"]["key"][:, key].mean()),
            "intact_raises_open": float(probabilities["intact"]["door"][:, door].mean())
            > float(probabilities["zero"]["door"][:, door].mean()),
            "blind_equals_zero_key": bool(
                np.array_equal(probabilities["blind"]["key"], probabilities["zero"]["key"])
            ),
            "blind_equals_zero_door": bool(
                np.array_equal(probabilities["blind"]["door"], probabilities["zero"]["door"])
            ),
            "key_lesion_abstains": bool(
                np.array_equal(
                    probabilities["key_lesion"]["key"], probabilities["zero"]["key"]
                )
            ),
            "door_lesion_abstains": bool(
                np.array_equal(
                    probabilities["door_lesion"]["door"], probabilities["zero"]["door"]
                )
            ),
            "swapped_raises_wrong_open_at_key": float(
                probabilities["swapped"]["key"][:, door].mean()
            )
            > float(probabilities["zero"]["key"][:, door].mean()),
            "swapped_raises_wrong_pickup_at_door": float(
                probabilities["swapped"]["door"][:, key].mean()
            )
            > float(probabilities["zero"]["door"][:, key].mean()),
        }
        all_gates.extend(gates.values())
        rows.append(
            {
                "parent": int(parent["parent"]),
                "child_seed": child_seed,
                "probe_states_per_context": len(key_observations),
                "mean_probability": {
                    name: {
                        "key_pickup": float(values["key"][:, key].mean()),
                        "key_open": float(values["key"][:, door].mean()),
                        "door_pickup": float(values["door"][:, key].mean()),
                        "door_open": float(values["door"][:, door].mean()),
                    }
                    for name, values in probabilities.items()
                },
                "gates": gates,
                "passes": all(gates.values()),
            }
        )
    gates = {
        "four_parent_probes": len(rows) == 4,
        "all_parent_expression_gates_pass": all(all_gates),
    }
    return {"rows": rows, "gates": gates, "passes": all(gates.values())}


def _effect_ledger(slot: int, action: int, count: int = MIN_VERIFIED_EFFECTS) -> CausalWriterLedger:
    ledger = CausalWriterLedger.empty()
    ledger.effect_action_counts[slot, action] = count
    ledger.context_action_counts[slot, action] = count
    ledger.birth_probability_sums[slot] = count / 8.0
    ledger.final_probability_sums[slot, action] = count
    ledger.transition_count = count
    return ledger


def qualify_transactions() -> dict[str, Any]:
    schema = GermSchema()
    pickup = _effect_ledger(1, int(Action.PICKUP))
    first = renew_germ_from_causal_evidence(pickup, empty_germ(1), schema)
    aged_once = renew_germ_from_causal_evidence(CausalWriterLedger.empty(), first.germ, schema)
    renewed = renew_germ_from_causal_evidence(pickup, aged_once.germ, schema)
    changed = renew_germ_from_causal_evidence(
        _effect_ledger(1, int(Action.OPEN)), renewed.germ, schema
    )
    silent = changed.germ
    silent_payload = silent.reshape(4, 16)[1, 4:13].copy()
    for _ in range(33):
        silent = renew_germ_from_causal_evidence(
            CausalWriterLedger.empty(), silent, schema
        ).germ
    near = CausalWriterLedger.empty()
    near.context_action_counts[1, Action.OPEN] = MIN_VERIFIED_EFFECTS
    near.transition_count = MIN_VERIFIED_EFFECTS
    near_result = renew_germ_from_causal_evidence(near, changed.germ, schema)
    refuted = CausalWriterLedger.empty()
    refuted.context_action_counts[1, Action.OPEN] = MIN_VERIFIED_EFFECTS
    refuted.interaction_attempt_counts[1, Action.OPEN] = MIN_VERIFIED_EFFECTS
    refuted.transition_count = MIN_VERIFIED_EFFECTS
    revoke_result = renew_germ_from_causal_evidence(refuted, changed.germ, schema)
    contradictory = renew_germ_from_causal_evidence(pickup, changed.germ, schema)
    carriers = (
        first.germ,
        aged_once.germ,
        renewed.germ,
        changed.germ,
        silent,
        near_result.germ,
        revoke_result.germ,
        contradictory.germ,
    )
    gates = {
        "new_write_readable": bool(read_germ(first.germ).active[0, 1]),
        "same_content_renewal_resets_freshness": bool(
            renewed.same_content_renewal_mask[0, 1]
            and renewed.germ.reshape(4, 16)[1, 13] == 0
        ),
        "confident_change_overwrites": bool(
            changed.semantic_change_mask[0, 1]
            and read_germ(changed.germ).prior_logits[0, 1].argmax() == Action.OPEN
        ),
        "silence_preserves_payload_and_trust": bool(
            np.array_equal(silent.reshape(4, 16)[1, 4:13], silent_payload)
        ),
        "thirty_three_silent_boundaries_abstain": not bool(
            read_germ(silent).active[0, 1]
        ),
        "near_miss_does_not_revoke": bool(
            not near_result.revocation_mask[0, 1]
            and read_germ(near_result.germ).active[0, 1]
        ),
        "exact_failed_opportunities_revoke": bool(
            revoke_result.revocation_mask[0, 1]
            and not read_germ(revoke_result.germ).active[0, 1]
        ),
        "contradictory_effect_overwrites_not_revokes": bool(
            contradictory.semantic_change_mask[0, 1]
            and not contradictory.revocation_mask[0, 1]
            and read_germ(contradictory.germ).prior_logits[0, 1].argmax()
            == Action.PICKUP
        ),
        "all_carriers_exact_64_valid": all(
            carrier.nbytes == 64
            and read_germ(carrier).address_valid.all()
            and read_germ(carrier).checksum_valid.all()
            for carrier in carriers
        ),
    }
    return {"gates": gates, "passes": all(gates.values())}


def markdown_report(audit: Mapping[str, Any]) -> str:
    lines = [
        "# DoorKey causal writer qualification",
        "",
        f"**Qualification:** `{'PASS' if audit['overall_pass'] else 'FAIL'}`  ",
        "**Scientific verdict:** `NONE — OUTCOME-KNOWN DEVELOPMENT RUNG`  ",
        "**Vertical carrier comparison:** `NOT RUN`",
        "",
        "## Bottom line",
        "",
        "The analytic writer reconstructed a same-self birth comparator, observed only lived before/action/after transitions, and wrote the unchanged 64-byte format. All four frozen parents wrote readable PICKUP and OPEN records while the rotation-dependent navigation slots abstained. Fresh same-seed children expressed those records, wrong-content exchange reversed the interaction bias, and reader-off or checksum lesions abstained.",
        "",
        "This qualifies a designed causal record, not learned ontology or vertical heredity. The parent assays and their expected direction were inspected before freeze and are disclosed in the protocol.",
        "",
        "## Parent writer assays",
        "",
        "| Parent | Effects find/acquire/find-door/open | Confidence by slot | Active targets | Assay goals |",
        "|---:|---|---|---|---:|",
    ]
    for row in audit["parents"]:
        effects = row["decision"]["effect_counts"]
        confidence = row["decision"]["confidence"]
        active = row["decoded"]["active"][0]
        targets = row["decoded"]["targets"][0]
        active_targets = ", ".join(
            f"{SLOT_NAMES[index]}:{targets[index]}"
            for index, enabled in enumerate(active)
            if enabled
        )
        lines.append(
            f"| {row['parent']} | {'/'.join(str(value) for value in effects)} | {'/'.join(f'{value:.3f}' for value in confidence)} | `{active_targets}` | {row['assay']['successes']}/128 |"
        )
    lines.extend(
        [
            "",
            "Action 4 is PICKUP and action 5 is OPEN. Slots 0 and 2 summarize rotation-dependent navigation events and correctly remain below the fixed trust threshold. Every parent and exact replay left its actor, critics, auxiliary heads, and dormant neural writer unchanged.",
            "",
            "## Fresh-child expression",
            "",
            "| Parent | Zero→intact PICKUP at key | Zero→intact OPEN at door | Swapped wrong-action checks | Lesion/blind abstention |",
            "|---:|---:|---:|---|---|",
        ]
    )
    for row in audit["expression"]["rows"]:
        p = row["mean_probability"]
        lines.append(
            f"| {row['parent']} | {p['zero']['key_pickup']:.3f}→{p['intact']['key_pickup']:.3f} | {p['zero']['door_open']:.3f}→{p['intact']['door_open']:.3f} | `{'PASS' if p['swapped']['key_open'] > p['zero']['key_open'] and p['swapped']['door_pickup'] > p['zero']['door_pickup'] else 'FAIL'}` | `{'PASS' if row['gates']['key_lesion_abstains'] and row['gates']['door_lesion_abstains'] and row['gates']['blind_equals_zero_key'] and row['gates']['blind_equals_zero_door'] else 'FAIL'}` |"
        )
    costs = audit["parents"][0]["writer_cost"]
    lines.extend(
        [
            "",
            "## Cost and boundary",
            "",
            f"Only `{costs['transmitted_carrier_bytes']}` bytes cross a boundary. Per parent, the disposable evidence arrays occupy `{costs['analytic_ledger_array_bytes']}` raw bytes, the reconstructed birth comparator has `{costs['reconstructed_birth_comparator_parameter_bytes']}` parameter bytes, the unused neural writer scaffold has `{costs['neural_writer_scaffold_parameter_bytes_unused']}` parameter bytes, and the dual recurrent assay state uses `{costs['transient_dual_recurrent_state_bytes']}` bytes. These are writer/soma costs, not carrier capacity.",
            "",
            "## Integrity",
            "",
        ]
    )
    for section_name in ("runtime", "parent_bank", "transactions", "expression"):
        section = audit[section_name]
        for name, passed in section["gates"].items():
            lines.append(f"- `{section_name}.{name}`: `{'PASS' if passed else 'FAIL'}`")
    for row in audit["parents"]:
        for name, passed in row["gates"].items():
            lines.append(
                f"- `parent_{row['parent']}.{name}`: `{'PASS' if passed else 'FAIL'}`"
            )
    lines.extend(
        [
            "",
            "## Next",
            "",
            "Freeze one three-boundary development scout. Each birth must destroy actor/critic, auxiliary heads, both optimizers, recurrent/action/reward state, rollout state, writer evidence, comparator state, and RNG state. Compare active rewrite with stale founder copy, silence, wrong content with repair, reader-off, writer-off, and checksum abstention on common worlds. Preserve the six-link chain and learning AUC; terminal success alone is too sparse.",
            "",
            "A pass there would bear directly on L17's development/heredity distinction and L20's self-written renewable-carrier clause, but would still be a hand-addressed direct-action record rather than a learned disposition.",
            "",
        ]
    )
    return "\n".join(lines)


def run_qualification(args: argparse.Namespace) -> int:
    started = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id):
        raise ValueError("invalid run ID")
    root = external_root(args.external_root)
    workspace = Path(__file__).resolve().parents[2]
    output_dir = root / "outputs" / args.run_id
    run_dir = root / "runs" / args.run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(f"immutable run ID exists: {args.run_id}")
    run_dir.mkdir(parents=True)
    disk = _disk_preflight(root, 8 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")
    specs = parent_specs(root)
    input_paths = [
        workspace / "protocols/DOORKEY_CAUSAL_WRITER_QUALIFICATION_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_phase_value_credit.py",
        workspace / "src/laws_confirmation/doorkey_phase_value_multiseed.py",
        workspace / "src/laws_confirmation/doorkey_causal_writer.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_causal_writer.py",
    ]
    for spec in specs:
        input_paths.extend(
            (
                Path(spec["checkpoint"]),
                Path(spec["result"]),
                Path(spec["source_output"]) / "output_hashes.sha256",
                Path(spec["source_run"]) / "MANIFEST.json",
                Path(spec["source_run"]) / "STATUS.json",
                Path(spec["source_run"]) / "COMPLETE",
            )
        )
    input_paths = sorted({path.resolve() for path in input_paths})
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing qualification inputs: {missing}")
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "stage": "DoorKey causal writer qualification",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "external_root": str(root),
        "output_dir": str(output_dir),
        "input_sha256": input_hashes,
        "contract_digest": canonical_digest(input_hashes),
        "repository_head": git_head(workspace),
        "workers": 1,
        "development_assay_episodes": 4
        * WORLDS_PER_TRANSFORM
        * len(TRANSFORMS)
        * STOCHASTIC_REPEATS,
        "scientific_confirmation_futures": 0,
        "carrier_effect_comparisons": 0,
        "disk_preflight": disk,
        "environment": environment_manifest(),
    }
    atomic_json(run_dir / "MANIFEST.json", manifest, root)
    atomic_json(run_dir / "STATUS.json", {"status": "RUNNING", "updated_utc": utc_now()}, root)
    try:
        runtime = runtime_qualification()
        bank = qualify_parent_bank(root, specs)
        transactions = qualify_transactions()
        parents: list[dict[str, Any]] = []
        all_rows: list[dict[str, Any]] = []
        for spec in specs:
            parent, rows = qualify_one_parent(spec)
            parents.append(parent)
            all_rows.extend({"parent": parent["parent"], **row} for row in rows)
        expression = qualify_expression_probe(parents)
        audit = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "status": "OUTCOME_KNOWN_DEVELOPMENT_QUALIFICATION",
            "pre_freeze_diagnostics_disclosed": True,
            "runtime": runtime,
            "parent_bank": bank,
            "transactions": transactions,
            "parents": parents,
            "expression": expression,
            "overall_pass": bool(
                runtime["passes"]
                and bank["passes"]
                and transactions["passes"]
                and all(parent["passes"] for parent in parents)
                and expression["passes"]
            ),
            "vertical_boundaries_run": 0,
            "numbered_law_verdict_changes": 0,
        }
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "qualification.json", audit, root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), root)
        atomic_text(
            output_dir / "parent_world_rows.jsonl",
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in all_rows
            ),
            root,
        )
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", root)
        outputs = [
            output_dir / "qualification.json",
            output_dir / "audit.md",
            output_dir / "parent_world_rows.jsonl",
            output_dir / "input_hashes.sha256",
        ]
        write_hash_manifest(outputs, output_dir / "output_hashes.sha256", root)
        status = {
            "status": "COMPLETE" if audit["overall_pass"] else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started,
            "overall_pass": audit["overall_pass"],
            "development_assay_episodes": manifest["development_assay_episodes"],
            "scientific_confirmation_futures": 0,
            "carrier_effect_comparisons": 0,
            "output_files": [str(path) for path in outputs]
            + [str(output_dir / "output_hashes.sha256")],
        }
        atomic_json(run_dir / "STATUS.json", status, root)
        sentinel = "COMPLETE" if audit["overall_pass"] else "FAILED"
        atomic_text(run_dir / sentinel, status["completed_utc"] + "\n", root)
        print(output_dir / "audit.md")
        return 0 if audit["overall_pass"] else 1
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started,
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
    parser.add_argument("--run-id", default=RUN_ID)
    return parser


def main() -> int:
    return run_qualification(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
