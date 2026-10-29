"""Frozen, action-blind diagnosis of trained DoorKey continuation policies.

Oracle prefixes are experimental interventions, not new training or inherited
information. Each actor reconstructs its own recurrence from the same history.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
import multiprocessing
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

import numpy as np
import torch

from . import doorkey_consequence_reader_behavior as source_behavior
from . import doorkey_matched_disposition as matched
from .doorkey_carrier import carrier_digest
from .doorkey_env import Action, CAUSAL_CHAIN, DoorKeyEnv, TRANSFORMS, make_layout, oracle_plan
from .doorkey_feedback_scout import _atomic_torch_save, _disk_preflight, _read_hash_manifest
from .doorkey_ppo_v2 import START_ACTION, _router_contexts
from .io import (
    atomic_json, atomic_text, canonical_digest, environment_manifest,
    external_root, git_head, sha256_file, utc_now, write_hash_manifest,
)


RUN_ID = "doorkey_common_state_continuation_v1_attempt1"
SOURCE_RUN = source_behavior.RUN_ID
FOUNDERS = (1, 2, 3)
ARMS = ("correct", "empty", "shuffled")
STAGES = ("birth", "key_acquired", "door_ready", "door_opened")
BLOCKS = 64
STREAMS = 4
HORIZON = 128
BATCH_SIZE = 128
WORKERS = 3
LAYOUT_SEED = 360_000_000
ACTION_SEED = 370_000_000
BENCHMARK_BLOCKS = 8
BOOTSTRAP_SAMPLES = 10_000
EPISODES_PER_STAGE = BLOCKS * len(TRANSFORMS) * STREAMS
REGISTERED_EPISODES = len(FOUNDERS) * len(ARMS) * len(STAGES) * EPISODES_PER_STAGE


def runtime_qualification() -> dict:
    cpus = source_behavior.pin_cpu_budget()
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    values = {
        "python": platform.python_version(), "numpy": np.__version__,
        "torch": torch.__version__, "cpu_affinity": cpus,
        "worker_processes": WORKERS, "threads_per_worker": torch.get_num_threads(),
        "interop_threads": torch.get_num_interop_threads(),
    }
    gates = {
        "pinned_runtime": platform.python_version_tuple()[:2] == ("3", "13")
        and np.__version__ == "2.5.2" and torch.__version__ == "2.14.0+cpu",
        "cpu_only": not torch.cuda.is_available(),
        "at_most_four_cpus": 0 < len(cpus) <= 4,
        "one_thread": torch.get_num_threads() == torch.get_num_interop_threads() == 1,
        "numerical_thread_limits": all(os.environ.get(k) == "1" for k in (
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"
        )),
    }
    return {"values": values, "gates": gates, "passes": all(gates.values())}


def cell_path(root: Path, founder: int, arm: str) -> Path:
    return root / "outputs" / SOURCE_RUN / f"founder_{founder}" / f"g4_{arm}.json"


def qualify_source(root: Path) -> dict:
    output, run = root / "outputs" / SOURCE_RUN, root / "runs" / SOURCE_RUN
    manifest = json.loads((run / "MANIFEST.json").read_text())
    study = json.loads((output / "consequence_reader_behavior.json").read_text())
    status = json.loads((run / "STATUS.json").read_text())
    inputs = matched._verify_manifest_inputs(manifest)
    outputs = _read_hash_manifest(output / "output_hashes.sha256")
    cells = [json.loads(cell_path(root, f, a).read_text())
             for f in FOUNDERS for a in source_behavior.ARMS]
    apparatus = source_behavior.exact_apparatus_audit(cells)
    classification = source_behavior.registered_classification(cells, apparatus)
    expected_packets = {(s["founder"], s["arm"]): s["incoming_carrier_sha256"]
                        for s in manifest["cell_specs"]}
    gates = {
        "source_identity": manifest["run_id"] == study["run_id"] == status["run_id"] == SOURCE_RUN,
        "source_complete": status["status"] == "COMPLETE" and study["completed_cleanly"]
        and (run / "COMPLETE").is_file() and not (run / "FAILED").exists(),
        "source_gates": bool(study["completion_gates"]) and all(study["completion_gates"].values()),
        "input_hashes": bool(inputs) and all(r["matches"] for r in inputs),
        "output_hashes": bool(outputs) and all(r["matches"] for r in outputs),
        "exact_prefix_and_nulls": apparatus["passes"] and apparatus == study["exact_apparatus"],
        "original_classification_reconstructed": classification == study["registered_classification"],
        "packet_inventory": all(c["incoming_carrier_sha256"] == expected_packets[c["founder"], c["arm"]]
                                for c in cells),
        "fixed_horizon_and_action_space": all(c["config"]["max_episode_steps"] == HORIZON
                                             and c["config"]["num_actions"] == len(Action) for c in cells),
    }
    return {
        "run_id": SOURCE_RUN, "input_manifest": matched._manifest_summary(inputs),
        "output_manifest": matched._manifest_summary(outputs),
        "original_classification": classification, "gates": gates, "passes": all(gates.values()),
    }


def build_prefix_bank(blocks: int, layout_seed: int) -> dict:
    if blocks < 1:
        raise ValueError("positive block count required")
    entries = []
    for block in range(blocks):
        for transform in TRANSFORMS:
            layout = make_layout(layout_seed + block, transform=transform)
            plan = oracle_plan(layout)
            pickup, opening = plan.index(Action.PICKUP), plan.index(Action.OPEN)
            lengths = {"birth": 0, "key_acquired": pickup + 1,
                       "door_ready": opening, "door_opened": opening + 1}
            for stage in STAGES:
                env = DoorKeyEnv(layout, max_steps=HORIZON)
                observations, actions, rewards, resulting_states = [], [], [], []
                for action in plan[:lengths[stage]]:
                    observations.append(env.observation().vector())
                    _, reward, terminated, truncated, _ = env.step(action)
                    if terminated or truncated:
                        raise RuntimeError("oracle prefix exhausted the episode")
                    actions.append(int(action))
                    rewards.append(reward)
                    resulting_states.append(deepcopy(env.state_signature()))
                history = {
                    "observations": np.asarray(observations, dtype=np.float32).reshape(-1, 13),
                    "actions": np.asarray(actions, dtype=np.int64),
                    "rewards": np.asarray(rewards, dtype=np.float32),
                    "resulting_states": resulting_states,
                }
                entries.append({
                    "seed_block": block, "layout_seed": layout_seed + block,
                    "transform": transform, "stage": stage, "environment": env,
                    "history": history, "history_sha256": matched.deep_digest(history),
                    "state_sha256": matched.deep_digest(env), "prefix_steps": env.steps,
                    "remaining_steps": HORIZON - env.steps,
                })
    bank = {"blocks": blocks, "layout_seed": layout_seed, "entries": entries}
    audit = audit_prefix_bank(bank)
    if not audit["passes"]:
        raise RuntimeError(f"invalid prefix bank: {audit}")
    bank["audit"] = audit
    return bank


def audit_prefix_bank(bank: dict) -> dict:
    rows = []
    identities = set()
    for entry in bank["entries"]:
        env, hist, stage = entry["environment"], entry["history"], entry["stage"]
        identities.add((entry["seed_block"], entry["transform"], stage))
        replay = DoorKeyEnv(env.layout, max_steps=HORIZON)
        exact = len(hist["observations"]) == len(hist["actions"]) == len(hist["rewards"]) == len(hist["resulting_states"]) == env.steps
        for obs, action, reward, state in zip(hist["observations"], hist["actions"], hist["rewards"], hist["resulting_states"]):
            exact &= np.array_equal(replay.observation().vector(), obs)
            _, observed_reward, _, _, _ = replay.step(int(action))
            exact &= observed_reward == reward and replay.state_signature() == state
        distance = sum(abs(a - b) for a, b in zip(env.state.position, env.layout.door))
        stage_valid = {
            "birth": env.steps == 0 and not env.state.has_key and not env.state.door_open,
            "key_acquired": env.state.has_key and not env.state.door_open
            and env.auxiliary_steps["key_acquired"] == env.steps,
            "door_ready": env.state.has_key and not env.state.door_open and distance == 1,
            "door_opened": env.state.has_key and env.state.door_open and distance == 1
            and env.event_steps["open_door"] == env.steps,
        }[stage]
        rows.append(bool(exact and stage_valid and not env.terminated and not env.truncated
                         and entry["prefix_steps"] == env.steps < HORIZON
                         and entry["remaining_steps"] == HORIZON - env.steps
                         and env.layout.seed == entry["layout_seed"] == bank["layout_seed"] + entry["seed_block"]
                         and env.layout.transform == entry["transform"]
                         and matched.deep_digest(hist) == entry["history_sha256"]
                         and matched.deep_digest(replay) == entry["state_sha256"] == matched.deep_digest(env)))
    expected = {(b, t, s) for b in range(bank["blocks"]) for t in TRANSFORMS for s in STAGES}
    gates = {"complete_unique_inventory": len(rows) == len(expected) and identities == expected,
             "all_prefixes_valid_and_exact": bool(rows) and all(rows)}
    return {"prefix_count": len(rows), "gates": gates, "passes": all(gates.values())}


def episode_index(entry: dict, stream: int) -> int:
    return (entry["seed_block"] * len(TRANSFORMS) + TRANSFORMS.index(entry["transform"])) * STREAMS + stream


def action_uniforms(index: int, action_seed: int) -> np.ndarray:
    return np.random.default_rng(action_seed + 1_000_003 * index).random(HORIZON)


@torch.no_grad()
def replay_prefix_hidden(model, entries: list[dict]) -> tuple:
    """Fold observations BEFORE each forced action; retain last action feedback.

    Shorter prefixes stop updating in-place while longer histories finish.
    The takeover observation has not yet been fed to the GRU on return.
    """
    count = len(entries)
    hidden = torch.zeros(count, model.config.hidden_size)
    previous_actions = torch.full((count,), START_ACTION, dtype=torch.long)
    previous_rewards = torch.zeros(count)
    starts = torch.ones(count, dtype=torch.bool)
    for time_index in range(max(e["prefix_steps"] for e in entries)):
        active = torch.tensor([time_index < e["prefix_steps"] for e in entries])
        observations = torch.from_numpy(np.stack([
            e["history"]["observations"][time_index] if active[i]
            else e["environment"].observation().vector() for i, e in enumerate(entries)
        ]))
        _, _, next_hidden = model.forward_step(observations, hidden, starts, previous_actions, previous_rewards)
        hidden[active] = next_hidden[active]
        for i, entry in enumerate(entries):
            if active[i]:
                previous_actions[i] = int(entry["history"]["actions"][time_index])
                previous_rewards[i] = float(entry["history"]["rewards"][time_index])
        starts[active] = False
    return hidden, previous_actions, previous_rewards, starts


def sampled_actions(logits: torch.Tensor, uniforms: np.ndarray) -> np.ndarray:
    probabilities = torch.softmax(logits, dim=-1).numpy()
    return np.minimum((uniforms[:, None] > probabilities.cumsum(axis=-1)).sum(axis=-1), len(Action) - 1)


@torch.no_grad()
def continue_batch(model, entries: list[dict], streams: list[int], action_seed: int) -> list[dict]:
    if not entries or len(entries) != len(streams) or len(entries) > BATCH_SIZE:
        raise ValueError("invalid continuation batch")
    environments = [deepcopy(e["environment"]) for e in entries]
    uniforms = np.stack([action_uniforms(episode_index(e, s), action_seed) for e, s in zip(entries, streams)])
    hidden, previous_actions, previous_rewards, starts = replay_prefix_hidden(model, entries)
    active = np.ones(len(entries), dtype=bool)
    traces = [[] for _ in entries]
    counts = [dict.fromkeys(("pickups", "failed_pickups", "open_actions", "failed_opens", "acquisitions", "openings", "drops", "failed_drops", "wrong_context_pickups", "wrong_context_opens", "pickup_context_0", "open_context_2"), 0) for _ in entries]
    context_counts = np.zeros((len(entries), 4, len(Action)), dtype=np.int64)
    while active.any():
        observations = torch.from_numpy(np.stack([e.observation().vector() for e in environments]))
        # Deliberately call only the frozen actor: no reader, germ, or optimizer.
        logits, _, hidden = model.forward_step(observations, hidden, starts, previous_actions, previous_rewards)
        contexts = _router_contexts(observations).numpy()
        draws = uniforms[np.arange(len(entries)), [min(e.steps, HORIZON - 1) for e in environments]]
        actions = sampled_actions(logits, draws)
        for i in np.flatnonzero(active):
            action, context = int(actions[i]), int(contexts[i])
            _, reward, terminated, truncated, info = environments[i].step(action)
            previous_actions[i], previous_rewards[i], starts[i] = action, reward, False
            traces[i].append(action)
            context_counts[i, context, action] += 1
            count = counts[i]
            for name, flag in (
                ("pickups", action == Action.PICKUP), ("open_actions", action == Action.OPEN),
                ("failed_pickups", action == Action.PICKUP and not info["acquired"]),
                ("failed_opens", action == Action.OPEN and not info["opened"]),
                ("acquisitions", info["acquired"]), ("openings", info["opened"]),
                ("drops", info["dropped"]), ("failed_drops", action == Action.DROP and not info["dropped"]),
                ("wrong_context_pickups", action == Action.PICKUP and context != 1),
                ("wrong_context_opens", action == Action.OPEN and context != 3),
                ("pickup_context_0", action == Action.PICKUP and context == 0),
                ("open_context_2", action == Action.OPEN and context == 2),
            ):
                count[name] += int(flag)
            active[i] = not (terminated or truncated)
    rows = []
    for i, (entry, stream, env) in enumerate(zip(entries, streams, environments)):
        length = len(traces[i])
        success = env.event_steps["reach_goal"] is not None
        rows.append({
            **{k: entry[k] for k in ("seed_block", "layout_seed", "transform", "stage", "prefix_steps", "remaining_steps", "history_sha256", "state_sha256")},
            "action_stream": stream, "uniform_stream_sha256": matched.deep_digest(uniforms[i]),
            "prefix_event_steps": dict(entry["environment"].event_steps),
            "prefix_auxiliary_steps": dict(entry["environment"].auxiliary_steps),
            "event_steps": dict(env.event_steps), "auxiliary_steps": dict(env.auxiliary_steps),
            "success": success, "truncated": env.truncated, "episode_steps": env.steps,
            "continuation_steps": length, "goal_cost_censored_at_budget": length if success else entry["remaining_steps"],
            "continuation_counts": counts[i], "continuation_action_counts_by_context": context_counts[i].tolist(),
            "continuation_actions_sha256": matched.deep_digest(traces[i]),
            "environment_trace_sha256": matched.deep_digest(env.transition_trace),
        })
    return rows


def evaluate_panel(model, bank: dict, action_seed: int, progress=None) -> list[dict]:
    rows = []
    for stage in STAGES:
        expanded = [(e, stream) for e in bank["entries"] if e["stage"] == stage for stream in range(STREAMS)]
        for offset in range(0, len(expanded), BATCH_SIZE):
            batch = expanded[offset:offset + BATCH_SIZE]
            rows.extend(continue_batch(model, [e for e, _ in batch], [s for _, s in batch], action_seed))
        if progress is not None:
            progress(stage)
    return rows


def summarize_rows(rows: list[dict]) -> dict:
    summaries = {}
    for stage in STAGES:
        selected = [r for r in rows if r["stage"] == stage]
        if not selected:
            continue
        summaries[stage] = {
            "episodes": len(selected), "successes": sum(r["success"] for r in selected),
            "success_fraction": float(np.mean([r["success"] for r in selected])),
            "mean_censored_goal_cost": float(np.mean([r["goal_cost_censored_at_budget"] for r in selected])),
            "prefix_step_range": [min(r["prefix_steps"] for r in selected), max(r["prefix_steps"] for r in selected)],
            "policy_acquired_key_episodes": sum(r["continuation_counts"]["acquisitions"] > 0 for r in selected),
            "policy_opened_door_episodes": sum(r["continuation_counts"]["openings"] > 0 for r in selected),
            "continuation_counts": {k: sum(r["continuation_counts"][k] for r in selected) for k in selected[0]["continuation_counts"]},
            "action_counts_by_context": np.asarray([r["continuation_action_counts_by_context"] for r in selected]).sum(axis=0).tolist(),
        }
    return summaries


def row_id(row: dict) -> tuple:
    return row["seed_block"], row["layout_seed"], row["transform"], row["action_stream"]


def paired_contrast(correct: list[dict], control: list[dict], founder: int, *, interval: bool, expected_blocks: int = BLOCKS) -> dict:
    left, right = {row_id(r): r for r in correct}, {row_id(r): r for r in control}
    if not left or len(left) != len(correct) or len(right) != len(control) or set(left) != set(right):
        raise ValueError("paired contrast requires identical unique world inventory")
    match_fields = ("stage", "prefix_steps", "remaining_steps", "state_sha256", "history_sha256", "uniform_stream_sha256", "prefix_event_steps", "prefix_auxiliary_steps")
    if any(any(left[k][f] != right[k][f] for f in match_fields) for k in left):
        raise ValueError("paired state/history/time/action stream mismatch")
    block_means = []
    for block in range(expected_blocks):
        keys = [k for k in left if k[0] == block]
        if len(keys) != len(TRANSFORMS) * STREAMS or {(k[2], k[3]) for k in keys} != {(t, s) for t in TRANSFORMS for s in range(STREAMS)}:
            raise ValueError("incomplete layout/rotation/action-stream block")
        block_means.append(float(np.mean([int(left[k]["success"]) - int(right[k]["success"]) for k in keys])))
    if len(left) != expected_blocks * len(TRANSFORMS) * STREAMS:
        raise ValueError("unexpected extra blocks")
    result = {
        "episodes": len(left), "layout_blocks": expected_blocks,
        "correct_successes": sum(r["success"] for r in left.values()),
        "control_successes": sum(r["success"] for r in right.values()),
        "difference": float(np.mean(block_means)), "block_differences": block_means,
        "both_success": sum(left[k]["success"] and right[k]["success"] for k in left),
        "correct_only": sum(left[k]["success"] and not right[k]["success"] for k in left),
        "control_only": sum(right[k]["success"] and not left[k]["success"] for k in left),
        "mean_censored_goal_cost_difference": float(np.mean([left[k]["goal_cost_censored_at_budget"] - right[k]["goal_cost_censored_at_budget"] for k in left])),
    }
    if interval:
        draws = np.random.default_rng(410_000_000 + founder).integers(0, expected_blocks, size=(BOOTSTRAP_SAMPLES, expected_blocks))
        distribution = np.asarray(block_means)[draws].mean(axis=1)
        result["paired_block_bootstrap_95"] = np.quantile(distribution, [.025, .975]).tolist()
        result["bootstrap_samples"] = BOOTSTRAP_SAMPLES
        result["bootstrap_seed"] = 410_000_000 + founder
    return result


def classification(primary: list[dict], structural_pass: bool) -> str:
    if not structural_pass or sorted(r["founder"] for r in primary) != list(FOUNDERS):
        return "INVALID_STRUCTURAL_FAILURE"
    if not all(r["difference"] > 0 for r in primary):
        return "NO_REPLICATED_COMMON_STATE_GOAL_LEAD"
    if all(r["paired_block_bootstrap_95"][0] > 0 for r in primary):
        return "COMMON_STATE_GOAL_LEAD_3_OF_3"
    return "DIRECTIONAL_GOAL_LEAD_UNCERTAIN"


def retained_analysis(root: Path) -> dict:
    """Independent arithmetic on saved worlds, not the source's AUC helper."""
    reconstructed, discordances, gates = [], [], []
    for founder in FOUNDERS:
        cells = {a: json.loads(cell_path(root, founder, a).read_text()) for a in ARMS}
        for arm, cell in cells.items():
            for mode in ("deterministic", "fixed_random"):
                path = []
                for update in range(60, 101, 10):
                    worlds = cell["evaluation_world_rows"][str(update)][mode]
                    raw_reached = {e: sum(w["event_steps"][e] is not None for w in worlds) for e in CAUSAL_CHAIN}
                    reached = {}
                    conditional = []
                    for index, event in enumerate(CAUSAL_CHAIN):
                        eligible = [w for w in worlds if index == 0 or w["event_steps"][CAUSAL_CHAIN[index - 1]] is not None]
                        reached[event] = sum(w["event_steps"][event] is not None for w in eligible)
                        conditional.append({"event": event, "reached": reached[event], "eligible": len(eligible),
                                            "probability": reached[event] / len(eligible) if eligible else None})
                    path.append({"update": update, "episodes": len(worlds), "reached": reached,
                                 "raw_event_reached": raw_reached,
                                 "successes": sum(w["success"] for w in worlds), "conditional_chain": conditional})
                    saved = next(e for e in cell["evaluations"] if e["update"] == update and e["action_mode"] == mode)
                    gates.append(saved["successes"] == path[-1]["successes"] and saved["world_count"] == len(worlds)
                                 and all((s["to"], s["reached"], s["eligible"], s["conditional_probability"]) == (r["event"], r["reached"], r["eligible"], r["probability"])
                                         for s, r in zip(saved["conditional_chain"], conditional)))
                aucs = {}
                for event in ("open_door", "reach_goal"):
                    values = [p["reached"][event] / p["episodes"] for p in path]
                    auc = sum((values[i] + values[i + 1]) * .5 * 10 for i in range(4)) / 40
                    aucs[event] = auc
                    gates.append(auc == cell["post_prefix_auc"][mode]["events"][event]["reached_fraction_auc"])
                reconstructed.append({"founder": founder, "arm": arm, "action_mode": mode, "late_path": path, "late_auc": aucs})
        for control in ("empty", "shuffled"):
            for mode in ("deterministic", "fixed_random"):
                key = lambda w: (w["layout_seed"], w["transform"], w["action_stream"])
                left = {key(w): w for w in cells["correct"]["evaluation_world_rows"]["100"][mode]}
                right = {key(w): w for w in cells[control]["evaluation_world_rows"]["100"][mode]}
                gates.append(set(left) == set(right))
                for event in ("open_door", "reach_goal"):
                    counts = dict.fromkeys(("both", "correct_only", "control_only", "neither"), 0)
                    for k in left:
                        a, b = left[k]["event_steps"][event] is not None, right[k]["event_steps"][event] is not None
                        counts["both" if a and b else "correct_only" if a else "control_only" if b else "neither"] += 1
                    discordances.append({"founder": founder, "control": control, "action_mode": mode, "event": event, **counts})
    return {"post_hoc": True, "not_a_reclassification": True, "reconstructed": reconstructed,
            "paired_final_discordances": discordances, "arithmetic_checks": len(gates), "passes": bool(gates) and all(gates)}


def _snapshot(descendant, reader, environments) -> dict:
    return {"soma": matched.soma_environment_digests(descendant, environments), "reader": reader.digest(),
            "germ": carrier_digest(descendant.learner.germ), "reader_packet": carrier_digest(reader.packet)}


def run_founder(founder: int, root_text: str, bank_sha256: str) -> list[dict]:
    root = external_root(root_text)
    output = root / "outputs" / RUN_ID
    runtime = runtime_qualification()
    if not runtime["passes"]:
        raise RuntimeError("worker runtime gate failed")
    bank_path = output / "prefix_bank.pt"
    if sha256_file(bank_path) != bank_sha256:
        raise RuntimeError("prefix bank hash mismatch")
    bank = torch.load(bank_path, map_location="cpu", weights_only=False)
    if bank["blocks"] != BLOCKS or bank["layout_seed"] != LAYOUT_SEED or not audit_prefix_bank(bank)["passes"]:
        raise RuntimeError("worker prefix registry invalid")
    bank_digest = matched.deep_digest(bank)
    results = []
    for arm in ARMS:
        source = json.loads(cell_path(root, founder, arm).read_text())
        checkpoint = Path(source["checkpoint_path"])
        if sha256_file(checkpoint) != source["checkpoint_sha256"]:
            raise RuntimeError("source checkpoint changed")
        payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
        descendant, reader, environments, config = source_behavior.restore_checkpoint(payload)
        before = _snapshot(descendant, reader, environments)
        original_summaries, original_worlds, original_read_only = source_behavior.evaluate(descendant, reader, environments, config, 100)
        gates = {
            "source_checkpoint_identity": payload["run_id"] == SOURCE_RUN and payload["spec"] == source["spec"],
            "soma_restore_exact": before["soma"] == source["final_soma_environment_digests"],
            "head_restore_exact": before["reader"] == source["final_head_sha256"],
            "packets_exact": before["germ"] == before["reader_packet"] == source["incoming_carrier_sha256"],
            "original_final_evaluations_exact": original_summaries == [e for e in source["evaluations"] if e["update"] == 100]
            and original_worlds == source["evaluation_world_rows"]["100"],
            "original_evaluation_read_only": original_read_only,
        }
        if not all(gates.values()):
            raise RuntimeError(f"source actor replay failed: {founder}/{arm}: {gates}")
        progress_path = output / f"founder_{founder}" / "progress.json"
        def progress(stage, replay):
            atomic_json(progress_path, {"founder": founder, "arm": arm, "stage_completed": stage,
                                       "replay": replay, "updated_utc": utc_now()}, root)
        rows = evaluate_panel(descendant.learner.model, bank, ACTION_SEED, lambda s: progress(s, False))
        replay_rows = evaluate_panel(descendant.learner.model, bank, ACTION_SEED, lambda s: progress(s, True))
        gates.update({
            "entire_panel_exact_replay": rows == replay_rows,
            "all_state_unchanged": before == _snapshot(descendant, reader, environments),
            "prefix_bank_unchanged": bank_digest == matched.deep_digest(bank),
            "registered_episode_count": len(rows) == len(STAGES) * EPISODES_PER_STAGE,
            "all_episode_budgets_exact": all(r["prefix_steps"] + r["continuation_steps"] == r["episode_steps"] <= HORIZON
                                           and (r["success"] or r["truncated"]) for r in rows),
        })
        result_path = output / f"founder_{founder}" / f"{arm}.json"
        result = {"founder": founder, "arm": arm, "source_checkpoint_sha256": source["checkpoint_sha256"],
                  "runtime": runtime, "completion_gates": gates, "completed_cleanly": all(gates.values()),
                  "state_before_and_after_sha256": matched.deep_digest(before), "rows_sha256": matched.deep_digest(rows),
                  "summaries": summarize_rows(rows), "rows": rows}
        atomic_json(result_path, result, root)
        if not result["completed_cleanly"]:
            raise RuntimeError(f"assay integrity failed: {founder}/{arm}: {gates}")
        results.append({k: v for k, v in result.items() if k != "rows"} | {"path": str(result_path)})
        print(f"founder {founder}: {arm} evaluated and exactly replayed", flush=True)
    return results


def input_paths(root: Path) -> list[Path]:
    workspace = Path(__file__).resolve().parents[2]
    source_run, source_output = root / "runs" / SOURCE_RUN, root / "outputs" / SOURCE_RUN
    inherited = json.loads((source_run / "MANIFEST.json").read_text())["input_sha256"]
    outputs = [Path(line.split("  ", 1)[1]) for line in (source_output / "output_hashes.sha256").read_text().splitlines()]
    return sorted(set([
        Path(__file__).resolve(), workspace / "protocols/DOORKEY_COMMON_STATE_CONTINUATION_V1.md",
        workspace / "tests/test_doorkey_common_state_continuation.py",
        workspace / "scripts/run_doorkey_common_state_continuation.sh",
        source_run / "MANIFEST.json", source_run / "STATUS.json", source_run / "COMPLETE",
        source_output / "output_hashes.sha256", *[Path(p) for p in inherited], *outputs,
    ]))


def benchmark_path(root: Path) -> Path:
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root: Path) -> dict:
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("benchmark cannot alter a prepared run")
    runtime, source = runtime_qualification(), qualify_source(root)
    if not runtime["passes"] or not source["passes"] or not _disk_preflight(root, 256 * 1024**2)["preflight_pass"]:
        raise RuntimeError("benchmark runtime/source/storage gate failed")
    cell = json.loads(cell_path(root, 1, "correct").read_text())
    started = time.monotonic()
    payload = torch.load(cell["checkpoint_path"], map_location="cpu", weights_only=False)
    descendant, reader, environments, config = source_behavior.restore_checkpoint(payload)
    before = _snapshot(descendant, reader, environments)
    summaries, worlds, read_only = source_behavior.evaluate(descendant, reader, environments, config, 100)
    original_exact = summaries == [e for e in cell["evaluations"] if e["update"] == 100] and worlds == cell["evaluation_world_rows"]["100"]
    restore_and_original_seconds = time.monotonic() - started
    started = time.monotonic()
    bank = build_prefix_bank(BENCHMARK_BLOCKS, 380_000_000)
    first = evaluate_panel(descendant.learner.model, bank, 390_000_000)
    second = evaluate_panel(descendant.learner.model, bank, 390_000_000)
    assay_seconds = time.monotonic() - started
    if not original_exact or not read_only or first != second or before != _snapshot(descendant, reader, environments):
        raise RuntimeError("benchmark replay/read-only check failed")
    projected = ((len(FOUNDERS) * len(ARMS) / WORKERS)
                 * (restore_and_original_seconds + assay_seconds * BLOCKS / BENCHMARK_BLOCKS) * 1.75 + 60)
    result = {"run_id": RUN_ID, "non_scientific": True, "effect_sizes_not_reported": True,
              "measured_utc": utc_now(), "runtime": runtime,
              "input_sha256": {str(p): sha256_file(p) for p in input_paths(root)},
              "restore_and_original_seconds": restore_and_original_seconds,
              "eight_block_four_stage_full_replay_seconds": assay_seconds,
              "projected_seconds_three_workers": projected, "safety_multiplier": 1.75,
              "fixed_overhead_seconds": 60, "must_detach": projected > 600,
              "all_replay_and_state_gates_pass": True}
    atomic_json(benchmark_path(root), result, root)
    print(json.dumps({k: v for k, v in result.items() if k != "input_sha256"}, indent=2), flush=True)
    return result


def prepare_run(root: Path) -> dict:
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("refusing existing immutable target")
    runtime, source = runtime_qualification(), qualify_source(root)
    timing = json.loads(benchmark_path(root).read_text())
    paths = input_paths(root)
    hashes = {str(p): sha256_file(p) for p in paths}
    disk = _disk_preflight(root, 256 * 1024**2)
    if not (runtime["passes"] and source["passes"] and disk["preflight_pass"]
            and hashes == timing["input_sha256"] and timing["all_replay_and_state_gates_pass"]):
        raise RuntimeError("preparation source/runtime/storage/benchmark check failed")
    paths.append(benchmark_path(root))
    hashes[str(benchmark_path(root))] = sha256_file(benchmark_path(root))
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    manifest = {"schema_version": 1, "run_id": RUN_ID, "prepared_utc": utc_now(), "source": source,
                "runtime": runtime, "benchmark": timing, "disk_preflight": disk,
                "environment": environment_manifest(), "input_sha256": hashes,
                "contract_digest": canonical_digest(hashes), "workers": WORKERS,
                "registered_episodes": REGISTERED_EPISODES, "exact_replay_repetitions": 2,
                "repository_head": git_head(Path(__file__).resolve().parents[2])}
    atomic_json(run / "MANIFEST.json", manifest, root)
    write_hash_manifest(paths, output / "input_hashes.sha256", root)
    atomic_json(run / "STATUS.json", {"run_id": RUN_ID, "status": "PREPARED", "updated_utc": utc_now(),
                                     "projected_seconds": timing["projected_seconds_three_workers"]}, root)
    return manifest


def verify_prepared(root: Path) -> dict:
    run = root / "runs" / RUN_ID
    manifest = json.loads((run / "MANIFEST.json").read_text())
    status = json.loads((run / "STATUS.json").read_text())
    rows = matched._verify_manifest_inputs(manifest)
    if (status["status"] != "PREPARED" or manifest["run_id"] != RUN_ID
            or not rows or not all(r["matches"] for r in rows)
            or manifest["workers"] != WORKERS or manifest["registered_episodes"] != REGISTERED_EPISODES
            or manifest["contract_digest"] != canonical_digest(manifest["input_sha256"])
            or set(manifest["input_sha256"]) != {str(p) for p in input_paths(root) + [benchmark_path(root)]}
            or (run / "COMPLETE").exists() or (run / "FAILED").exists()):
        raise RuntimeError("run not uniquely PREPARED or input contract changed")
    return manifest


def launch_detached(root: Path) -> dict:
    if not (root / "runs" / RUN_ID).exists():
        prepare_run(root)
    manifest = verify_prepared(root)
    run = root / "runs" / RUN_ID
    (run / "LAUNCH.lock").mkdir()
    stdout, stderr = (root / "logs" / f"{RUN_ID}.{suffix}.log" for suffix in ("stdout", "stderr"))
    command = [sys.executable, "-m", "laws_confirmation.doorkey_common_state_continuation", "--external-root", str(root), "--run"]
    with stdout.open("xb") as out_handle, stderr.open("xb") as err_handle:
        process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL,
                                   stdout=out_handle, stderr=err_handle, start_new_session=True)
    launch = {"run_id": RUN_ID, "pid": process.pid, "launched_utc": utc_now(), "command": command,
              "stdout_log": str(stdout), "stderr_log": str(stderr), "status": str(run / "STATUS.json"),
              "progress": str(root / "outputs" / RUN_ID / "founder_N" / "progress.json"),
              "complete": str(run / "COMPLETE"), "failed": str(run / "FAILED"),
              "estimated_seconds": manifest["benchmark"]["projected_seconds_three_workers"], "polling_owner": "user"}
    atomic_text(run / "RUN.pid", f"{process.pid}\n", root)
    atomic_json(run / "LAUNCH.json", launch, root)
    print(json.dumps(launch, indent=2), flush=True)
    # No wait, poll, process inspection, or status read after detachment.
    return launch


def markdown_report(study: dict) -> str:
    lines = ["# DoorKey common-state continuation diagnostic", "", f"Run: `{RUN_ID}`.",
             f"Structural completion: `{study['completed_cleanly']}`.",
             f"Registered diagnostic: `{study['classification']}`.", "",
             "This is fixed-policy evaluation, not training or a new heredity claim.",
             "Oracle progress is supplied and counts against the original 128-step budget.", "",
             "| Founder | Correct goals | Empty goals | Difference | Paired block 95% interval |",
             "|---|---:|---:|---:|---|" ]
    for row in study["primary_contrasts"]:
        lo, hi = row["paired_block_bootstrap_95"]
        lines.append(f"| {row['founder']} | {row['correct_successes']}/{row['episodes']} | {row['control_successes']}/{row['episodes']} | {row['difference']:+.6f} | [{lo:+.6f}, {hi:+.6f}] |")
    lines += ["", "Primary: goal success after a common door-opening prefix.",
              "Intervals resample base-layout blocks, retaining rotations and action streams.",
              "They concern these fixed actors, not uncertainty over trained founder populations.", "",
              "| Founder | Actor | Birth goals | Key supplied | Ready at door | Door opened |",
              "|---|---|---:|---:|---:|---:|"]
    for cell in study["cells"]:
        values = " | ".join(str(cell["summaries"][s]["successes"]) for s in STAGES)
        lines.append(f"| {cell['founder']} | {cell['arm']} | {values} |")
    lines += ["", f"Each descriptive stage has {EPISODES_PER_STAGE} episodes per actor.",
              "The exact second replay is an integrity test, not additional independent evidence.",
              "The earlier failed door-learning classification is unchanged; no law verdict changes.", ""]
    return "\n".join(lines)


def run_study(root: Path) -> int:
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    manifest = verify_prepared(root)
    (run / "EXECUTION.lock").mkdir()
    started = time.monotonic()
    try:
        runtime = runtime_qualification()
        if not runtime["passes"]:
            raise RuntimeError("run runtime gate failed")
        atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
        atomic_json(run / "STATUS.json", {"run_id": RUN_ID, "status": "RUNNING", "started_utc": utc_now(),
                                         "completed_founders": 0, "registered_episodes": REGISTERED_EPISODES}, root)
        retained = retained_analysis(root)
        if not retained["passes"]:
            raise RuntimeError("retained endpoint arithmetic failed")
        atomic_json(output / "retained_analysis.json", retained, root)
        bank = build_prefix_bank(BLOCKS, LAYOUT_SEED)
        _atomic_torch_save(output / "prefix_bank.pt", bank)
        bank_sha256 = sha256_file(output / "prefix_bank.pt")
        results = []
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as executor:
            futures = [executor.submit(run_founder, f, str(root), bank_sha256) for f in FOUNDERS]
            for future in as_completed(futures):
                results.extend(future.result())
                atomic_json(run / "STATUS.json", {"run_id": RUN_ID, "status": "RUNNING", "updated_utc": utc_now(),
                                                 "completed_founders": len(results) // len(ARMS), "registered_episodes": REGISTERED_EPISODES}, root)
        results.sort(key=lambda r: (r["founder"], ARMS.index(r["arm"])))
        contrasts, primary = [], []
        for founder in FOUNDERS:
            cells = {r["arm"]: json.loads(Path(r["path"]).read_text())["rows"] for r in results if r["founder"] == founder}
            for stage in STAGES:
                for control in ("empty", "shuffled"):
                    is_primary = stage == "door_opened" and control == "empty"
                    contrast = paired_contrast([r for r in cells["correct"] if r["stage"] == stage],
                                               [r for r in cells[control] if r["stage"] == stage], founder, interval=is_primary)
                    contrast.update({"founder": founder, "stage": stage, "control": control})
                    contrasts.append(contrast)
                    if is_primary:
                        primary.append(contrast)
        input_rows = matched._verify_manifest_inputs(manifest)
        gates = {"runtime_qualified": runtime["passes"], "source_qualified": manifest["source"]["passes"],
                 "retained_endpoints_exact": retained["passes"], "prefix_bank_valid": bank["audit"]["passes"],
                 "prefix_bank_unchanged": sha256_file(output / "prefix_bank.pt") == bank_sha256,
                 "all_nine_actors_complete": len(results) == len(FOUNDERS) * len(ARMS) and all(r["completed_cleanly"] for r in results),
                 "all_inputs_still_verify": bool(input_rows) and all(r["matches"] for r in input_rows),
                 "all_paired_panels_matched": len(contrasts) == len(FOUNDERS) * len(STAGES) * 2}
        study = {"run_id": RUN_ID, "source_run_id": SOURCE_RUN, "generated_utc": utc_now(), "runtime": runtime,
                 "elapsed_seconds": time.monotonic() - started, "registered_episodes": REGISTERED_EPISODES,
                 "exact_replay_repetitions": 2, "prefix_bank_sha256": bank_sha256, "prefix_audit": bank["audit"],
                 "cells": results, "contrasts": contrasts, "primary_contrasts": primary,
                 "completion_gates": gates, "completed_cleanly": all(gates.values()),
                 "classification": classification(primary, all(gates.values())), "numbered_law_verdict_changes": 0}
        atomic_json(output / "common_state_continuation.json", study, root)
        atomic_text(output / "audit.md", markdown_report(study), root)
        paths = sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256")
        write_hash_manifest(paths, output / "output_hashes.sha256", root)
        output_rows = _read_hash_manifest(output / "output_hashes.sha256")
        verified = bool(output_rows) and all(r["matches"] for r in output_rows)
        success = study["completed_cleanly"] and verified
        status = {"run_id": RUN_ID, "status": "COMPLETE" if success else "FAILED_GATES", "completed_utc": utc_now(),
                  "completed_cleanly": success, "elapsed_seconds": time.monotonic() - started,
                  "classification": study["classification"], "registered_episodes": REGISTERED_EPISODES,
                  "completed_founders": len(results) // len(ARMS), "output_manifest_self_verifies": verified,
                  "workers": WORKERS, "cpu_affinity": runtime["values"]["cpu_affinity"]}
        atomic_json(run / "STATUS.json", status, root)
        atomic_text(run / ("COMPLETE" if success else "FAILED"), status["completed_utc"] + "\n", root)
        print(json.dumps(status, indent=2), flush=True)
        return 0 if success else 1
    except Exception as error:
        failure = {"run_id": RUN_ID, "status": "FAILED", "failed_utc": utc_now(), "error": str(error),
                   "traceback": traceback.format_exc(), "elapsed_seconds": time.monotonic() - started}
        atomic_json(run / "STATUS.json", failure, root)
        atomic_text(run / "FAILED", failure["failed_utc"] + "\n", root)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    for mode in ("benchmark", "prepare", "detach", "run"):
        group.add_argument(f"--{mode}", action="store_true")
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        manifest = prepare_run(root)
        print(json.dumps({"status": "PREPARED", "input_files": len(manifest["input_sha256"]), "estimated_seconds": manifest["benchmark"]["projected_seconds_three_workers"]}, indent=2))
    elif args.detach:
        launch_detached(root)
    else:
        return run_study(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
