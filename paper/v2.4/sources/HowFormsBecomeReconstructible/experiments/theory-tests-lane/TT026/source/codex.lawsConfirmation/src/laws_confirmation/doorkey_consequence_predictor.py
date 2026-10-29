"""Independent, experience-trained immediate-consequence reader qualification.

The frozen actor is replayed, never trained with this reader. Simulator twins
are evaluation-only and cannot enter the predictor's experience buffer.
"""

from __future__ import annotations

import argparse
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
import multiprocessing
import os
from pathlib import Path
import time
import traceback
from typing import Any, Mapping

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from . import doorkey_dose_matched_credit as dose
from . import doorkey_matched_disposition as matched
from . import doorkey_targeted_learning_reader as targeted
from . import doorkey_vertical_scout as vertical
from .doorkey_boundary import make_boundary_packet
from .doorkey_carrier import empty_germ, read_germ
from .doorkey_env import Action, DoorKeyEnv, TRANSFORMS, make_layout, oracle_plan
from .doorkey_feedback_scout import (
    _atomic_torch_save,
    _disk_preflight,
    _read_hash_manifest,
)
from .doorkey_phase_value_credit import (
    CHANNELS,
    phase_from_observations,
    rollout_semantics,
)
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import FeedbackPPOConfig
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


RUN_ID = "doorkey_consequence_predictor_audit_v1_attempt1"
ARMS = ("correct", "wrong", "empty", "reader_off", "shuffled")
FOUNDERS = (1, 2, 3)
UPDATES = 100
SNAPSHOTS = (0, 10, 20, 40, 60, 80, 100)
MAX_WORKERS = 3
PANEL_SEED = 270_000_000
PREDICTOR_SEED = 280_000_000
BUFFER_ROLLOUTS = 8
FIT_BATCHES = 16
BATCH_SIZE = 256
HIDDEN_SIZE = 32
LEARNING_RATE = 0.003


class TransitionRecorder:
    """Passive adapter: capture executed outcomes, not first-event rewards."""

    def __init__(self, environments: DoorKeyVectorEnv) -> None:
        self.environments = environments
        self.outcomes: list[np.ndarray] = []

    @property
    def episode_starts(self) -> np.ndarray:
        return self.environments.episode_starts

    def observations(self) -> np.ndarray:
        return self.environments.observations()

    def pop_completed(self) -> list[dict[str, Any]]:
        return self.environments.pop_completed()

    def step(self, actions: np.ndarray) -> tuple:
        result = self.environments.step(actions)
        self.outcomes.append(
            np.asarray(
                [
                    [float(info["acquired"]), float(info["opened"])]
                    for info in result[3]
                ],
                dtype=np.float32,
            )
        )
        return result

    def take_outcomes(self) -> torch.Tensor:
        outcomes = torch.from_numpy(np.stack(self.outcomes))
        self.outcomes.clear()
        return outcomes


def observation_features(observations: torch.Tensor) -> torch.Tensor:
    if observations.ndim != 2 or observations.shape[1] != 13:
        raise ValueError("consequence observations must have shape [N, 13]")
    tiles = observations[:, :9].long()
    if not torch.equal(tiles.to(observations.dtype), observations[:, :9]):
        raise ValueError("tile codes must be integral")
    return torch.cat((F.one_hot(tiles, 8).float().flatten(1), observations[:, 9:]), 1)


class ConsequenceHeads(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.heads = nn.ModuleList(
            nn.Sequential(
                nn.Linear(76, HIDDEN_SIZE), nn.Tanh(), nn.Linear(HIDDEN_SIZE, 8)
            )
            for _ in range(2)
        )
        for head in self.heads:
            nn.init.zeros_(head[-1].weight)
            nn.init.zeros_(head[-1].bias)

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        features = observation_features(observations)
        return torch.stack([head(features).sigmoid() for head in self.heads], 1)


def packet_records(packet: np.ndarray) -> list[dict[str, Any]]:
    if packet.shape != (1, 64) or packet.dtype != np.uint8 or packet.nbytes != 64:
        raise ValueError("one exact 64-byte uint8 packet is required")
    decoded = read_germ(packet)
    return [
        {
            "active": bool(decoded.active[0, slot]),
            "target_action": int(decoded.prior_logits[0, slot].argmax()),
            "trust": int(decoded.trust[0, slot]) / 255.0,
        }
        for slot in (1, 3)
    ]


def centered_scores(scores: torch.Tensor, probabilities: torch.Tensor) -> torch.Tensor:
    """Center stably: action-constant scores produce bitwise zero, even in fp32."""
    differences = scores - scores[..., :1]
    return differences - (differences * probabilities).sum(-1, keepdim=True)


class ConsequenceReader:
    """All persistent predictive state is fresh soma, never germ cargo."""

    def __init__(self, packet: np.ndarray, seed: int, arm: str) -> None:
        if arm not in ARMS:
            raise ValueError("unknown consequence-reader arm")
        self.arm = arm
        self.packet = packet.copy()
        self.records = packet_records(self.packet)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            self.model = ConsequenceHeads()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=LEARNING_RATE)
        self.generator = torch.Generator().manual_seed(seed + 1_000_003)
        self.shuffle_generator = torch.Generator().manual_seed(seed + 2_000_003)
        self.buffer: deque[tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = deque(
            maxlen=BUFFER_ROLLOUTS
        )
        self.positive_counts = [0, 0]
        self.negative_target_counts = [0, 0]
        self.updates = 0

    def state(self) -> dict[str, Any]:
        # Exclude the output switch and provenance: correct/off must alias.
        return {
            "model": self.model.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "sampling_rng": self.generator.get_state(),
            "shuffle_rng": self.shuffle_generator.get_state(),
            "buffer": list(self.buffer),
            "positive_counts": list(self.positive_counts),
            "negative_target_counts": list(self.negative_target_counts),
            "updates": self.updates,
        }

    def digest(self) -> str:
        return matched.deep_digest(self.state())

    def fit(
        self, observations: torch.Tensor, actions: torch.Tensor, outcomes: torch.Tensor
    ) -> dict:
        observations = observations.detach().reshape(-1, 13).clone()
        actions = actions.detach().reshape(-1).clone()
        outcomes = outcomes.detach().reshape(-1, 2)
        if len(observations) != len(actions) or len(outcomes) != len(actions):
            raise ValueError("executed transition arrays must align")
        if not torch.all((outcomes == 0) | (outcomes == 1)):
            raise ValueError("observed consequences must be binary")
        # The empty intervention is a true no-op, including optimizer and RNG.
        if not any(record["active"] for record in self.records):
            return {
                "trained_batches": 0,
                "new_positives": [0, 0],
                "label_counts_preserved": True,
            }
        labels = torch.zeros_like(outcomes)
        positives = []
        for channel, record in enumerate(self.records):
            target = actions == record["target_action"]
            labels[:, channel] = outcomes[:, channel] * target * record["active"]
            positives.append(int(labels[:, channel].sum()))
            self.positive_counts[channel] += positives[-1]
            self.negative_target_counts[channel] += int(
                (target & (labels[:, channel] == 0) & record["active"]).sum()
            )
            if self.arm == "shuffled":
                order = torch.randperm(len(actions), generator=self.shuffle_generator)
                labels[:, channel] = labels[order, channel]
        counts_preserved = positives == [int(labels[:, c].sum()) for c in range(2)]
        self.buffer.append((observations, actions, labels.clone()))
        features = observation_features(torch.cat([row[0] for row in self.buffer]))
        choices = torch.cat([row[1] for row in self.buffer])
        targets = torch.cat([row[2] for row in self.buffer])
        losses = []
        self.model.train()
        for channel, record in enumerate(self.records):
            if not record["active"]:
                continue
            positive = torch.where(targets[:, channel] > 0)[0]
            negative = torch.where(targets[:, channel] == 0)[0]
            for _ in range(FIT_BATCHES):
                if len(positive) and len(negative):
                    indices = torch.cat(
                        [
                            pool[
                                torch.randint(
                                    len(pool),
                                    (BATCH_SIZE // 2,),
                                    generator=self.generator,
                                )
                            ]
                            for pool in (positive, negative)
                        ]
                    )
                else:
                    pool = positive if len(positive) else negative
                    indices = pool[
                        torch.randint(
                            len(pool), (BATCH_SIZE,), generator=self.generator
                        )
                    ]
                logits = self.model.heads[channel](features[indices])
                selected = logits.gather(1, choices[indices, None]).squeeze(1)
                loss = F.binary_cross_entropy_with_logits(
                    selected, targets[indices, channel]
                )
                self.optimizer.zero_grad(set_to_none=True)
                loss.backward()
                self.optimizer.step()
                losses.append(float(loss.detach()))
        self.optimizer.zero_grad(set_to_none=True)
        self.updates += 1
        if not np.isfinite(losses).all():
            raise RuntimeError("nonfinite consequence training loss")
        return {
            "trained_batches": len(losses),
            "mean_balanced_bce": float(np.mean(losses)),
            "new_positives": positives,
            "label_counts_preserved": counts_preserved,
            "buffer_rollouts": len(self.buffer),
        }

    @torch.no_grad()
    def scores(self, observations: torch.Tensor) -> torch.Tensor:
        return self.model(observations.detach().reshape(-1, 13))

    @torch.no_grad()
    def credit_table(
        self, observations: torch.Tensor, probabilities: torch.Tensor
    ) -> torch.Tensor:
        """Prospective, unapplied state/action credits [N, 2, 8]."""
        observations = observations.detach().reshape(-1, 13)
        probabilities = probabilities.detach().reshape(-1, 8)
        result = torch.zeros((len(observations), 2, 8), dtype=observations.dtype)
        if self.arm == "reader_off":
            return result
        predictions = self.scores(observations)
        phases = phase_from_observations(observations)
        for channel, record in enumerate(self.records):
            if record["active"] and self.positive_counts[channel] > 0:
                centered = centered_scores(predictions[:, channel], probabilities)
                result[:, channel] = (
                    centered * record["trust"] * (phases == channel)[:, None]
                )
        return result


def make_readers(packet: np.ndarray, seed: int) -> dict[str, ConsequenceReader]:
    wrong = vertical.initial_carriers(packet)["wrong_frozen"]
    return {
        arm: ConsequenceReader(
            wrong if arm == "wrong" else empty_germ(1) if arm == "empty" else packet,
            seed,
            arm,
        )
        for arm in ARMS
    }


def intervention_row(environment: DoorKeyEnv) -> tuple[np.ndarray, np.ndarray, dict]:
    """All actions from one saved state; neither labels nor clones are training."""
    before = matched.deep_digest(environment)
    outcomes = np.zeros((2, 8), dtype=np.float32)
    for action in Action:
        twin = deepcopy(environment)
        _, _, _, _, info = twin.step(action)
        outcomes[:, int(action)] = (float(info["acquired"]), float(info["opened"]))
    if before != matched.deep_digest(environment):
        raise RuntimeError("diagnostic intervention mutated its source environment")
    return (
        environment.observation().vector(),
        outcomes,
        {
            "layout_seed": environment.layout.seed,
            "transform": environment.layout.transform,
            "state_sha256": before,
            "step": environment.steps,
        },
    )


def make_panel(seed: int = PANEL_SEED, worlds: int = 32) -> dict[str, Any]:
    observations, outcomes, metadata = [], [], []
    for world in range(worlds):
        for transform in TRANSFORMS:
            layout = make_layout(seed + world, transform)
            for path in ("oracle", "random"):
                environment = DoorKeyEnv(layout, max_steps=128)
                random = np.random.default_rng(seed + world + 10_000_019)
                actions = (
                    oracle_plan(layout)
                    if path == "oracle"
                    else random.integers(0, 8, 16)
                )
                for action in actions:
                    observation, labels, row = intervention_row(environment)
                    observations.append(observation)
                    outcomes.append(labels)
                    metadata.append({**row, "path": path})
                    _, _, terminated, truncated, _ = environment.step(int(action))
                    if terminated or truncated:
                        break
    payload = {
        "observations": torch.from_numpy(np.stack(observations)),
        "outcomes": torch.from_numpy(np.stack(outcomes)),
        "states": metadata,
        "base_seed": seed,
        "layout_count": worlds * len(TRANSFORMS),
        "evaluation_only": True,
    }
    payload["sha256"] = matched.deep_digest(payload)
    return payload


def roc_auc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    labels, scores = labels.astype(bool).ravel(), scores.ravel()
    n_positive = int(labels.sum())
    n_negative = len(labels) - n_positive
    if not n_positive or not n_negative:
        return None
    order = np.argsort(scores, kind="stable")
    sorted_scores = scores[order]
    bounds = np.r_[
        0, np.flatnonzero(sorted_scores[1:] != sorted_scores[:-1]) + 1, len(scores)
    ]
    average_ranks = np.repeat((bounds[:-1] + 1 + bounds[1:]) / 2.0, np.diff(bounds))
    positive_rank_sum = float(average_ranks[labels[order]].sum())
    return (positive_rank_sum - n_positive * (n_positive + 1) / 2.0) / (
        n_positive * n_negative
    )


def score_sums(labels: np.ndarray, scores: np.ndarray) -> dict[str, float | int]:
    labels, scores = labels.astype(bool).ravel(), scores.astype(np.float64).ravel()
    if len(labels) != len(scores) or not np.isfinite(scores).all():
        raise ValueError("invalid predictor scores")
    result: dict[str, float | int] = {}
    for name, mask, target in (("positive", labels, 1.0), ("negative", ~labels, 0.0)):
        result[f"{name}_count"] = int(mask.sum())
        result[f"{name}_score_sum"] = float(scores[mask].sum())
        result[f"{name}_squared_error_sum"] = float(
            ((scores[mask] - target) ** 2).sum()
        )
    return result


def summarize_sums(sums: Mapping[str, float | int]) -> dict:
    result = dict(sums)
    errors = []
    for name in ("positive", "negative"):
        count = int(sums[f"{name}_count"])
        result[f"{name}_mean_score"] = (
            sums[f"{name}_score_sum"] / count if count else None
        )
        errors.append(sums[f"{name}_squared_error_sum"] / count if count else None)
    result["balanced_brier"] = (
        sum(errors) / 2 if all(e is not None for e in errors) else None
    )
    return result


def score_metrics(labels: np.ndarray, scores: np.ndarray) -> dict:
    return {
        **summarize_sums(score_sums(labels, scores)),
        "roc_auc": roc_auc(labels, scores),
    }


def evaluate_panel(reader: ConsequenceReader, panel: Mapping[str, Any]) -> dict:
    predictions = reader.scores(panel["observations"]).numpy()
    labels = panel["outcomes"].numpy()
    result = {}
    # Score true semantic actions for every control, including wrong packets.
    for channel, target in enumerate((int(Action.PICKUP), int(Action.OPEN))):
        actionable = labels[:, channel, target] > 0
        others = np.delete(predictions[actionable, channel], target, axis=1)
        margins = predictions[actionable, channel, target] - others.max(axis=1)
        result[CHANNELS[channel]] = {
            "all_actions": score_metrics(labels[:, channel], predictions[:, channel]),
            "target_action": score_metrics(
                labels[:, channel, target], predictions[:, channel, target]
            ),
            "actionable_states": int(actionable.sum()),
            "unique_correct_action_fraction": float(np.mean(margins > 0))
            if len(margins)
            else None,
            "mean_correct_action_margin": float(margins.mean())
            if len(margins)
            else None,
        }
    return result


def prequential_rows(
    reader: ConsequenceReader,
    observations: torch.Tensor,
    actions: torch.Tensor,
    outcomes: torch.Tensor,
) -> dict:
    actions = actions.reshape(-1)
    scores = reader.scores(observations)[torch.arange(len(actions)), :, actions].numpy()
    labels = outcomes.reshape(-1, 2).numpy()
    result = {}
    for channel, target in enumerate((int(Action.PICKUP), int(Action.OPEN))):
        mask = actions.numpy() == target
        result[CHANNELS[channel]] = {
            "executed_all": score_sums(labels[:, channel], scores[:, channel]),
            "executed_target": score_sums(labels[mask, channel], scores[mask, channel]),
        }
    return result


def aggregate_prequential(rows: list[dict], arm: str) -> dict:
    result = {}
    for channel in ("key", "door"):
        result[channel] = {}
        for scope in ("executed_all", "executed_target"):
            sums = {}
            for row in rows:
                for name, value in row["prequential"][arm][channel][scope].items():
                    sums[name] = sums.get(name, 0) + value
            result[channel][scope] = summarize_sums(sums)
    return result


def qualification(results: list[dict]) -> dict:
    founders = []
    for result in results:
        channels = {}
        final = result["snapshots"][-1]["arms"]
        for channel_index, channel in enumerate(("key", "door")):
            correct = final["correct"][channel]
            score = correct["target_action"]
            shuffled = final["shuffled"][channel]["target_action"]
            counts = result["training_counts"]["correct"]
            gates = {
                "both_observed_classes": counts["positive"][channel_index] > 0
                and counts["negative_target"][channel_index] > 0,
                "within_action_auc_at_least_090": score["roc_auc"] is not None
                and score["roc_auc"] >= 0.90,
                "within_action_balanced_brier_below_015": score["balanced_brier"]
                is not None
                and score["balanced_brier"] < 0.15,
                "beats_label_shuffle": score["balanced_brier"] is not None
                and shuffled["balanced_brier"] is not None
                and score["balanced_brier"] < shuffled["balanced_brier"],
                "unique_correct_action_at_least_090": correct[
                    "unique_correct_action_fraction"
                ]
                is not None
                and correct["unique_correct_action_fraction"] >= 0.90,
            }
            channels[channel] = {"gates": gates, "passes": all(gates.values())}
        founders.append(
            {
                "founder": result["founder"],
                "channels": channels,
                "passes": all(row["passes"] for row in channels.values()),
            }
        )
    structural = (
        len(results) == 3
        and [r["founder"] for r in results] == list(FOUNDERS)
        and all(r["completed_cleanly"] for r in results)
    )
    return {
        "label": "INVALID_STRUCTURAL_FAILURE"
        if not structural
        else "PREDICTOR_QUALIFIED_3_OF_3"
        if all(r["passes"] for r in founders)
        else "PREDICTOR_NOT_QUALIFIED_3_OF_3",
        "founders": founders,
        "behavioral_benefit_tested": False,
        "numbered_law_verdict_changes": 0,
    }


def replay_founder(source: Mapping[str, Any], root_text: str, output_text: str) -> dict:
    dose.runtime_qualification(MAX_WORKERS)
    root, output = Path(root_text), Path(output_text)
    founder = int(source["founder"])
    expected_result = json.loads(Path(source["source_result"]).read_text())
    config = FeedbackPPOConfig(**source["config"])
    packet_array = np.asarray(source["incoming_germ"], dtype=np.uint8)
    packet = make_boundary_packet(packet_array)
    descendant = vertical.make_vertical_descendant(
        packet, config, int(source["birth_seed"])
    )
    boundary = vertical.audit_vertical_boundary(
        Path(source["parent_checkpoint"]), descendant, packet, generation=4
    )
    environments = DoorKeyVectorEnv(
        config.num_envs,
        int(source["training_seed"]),
        config.max_episode_steps,
        "terminal",
    )
    recorder = TransitionRecorder(environments)
    readers = make_readers(packet_array, PREDICTOR_SEED + founder * 100_000)
    empty_birth = readers["empty"].digest()
    panel_path = output / "diagnostic_panel.pt"
    panel = torch.load(panel_path, weights_only=False, map_location="cpu")
    panel_before = matched.deep_digest(panel)
    uniform = torch.full((len(panel["observations"]), 8), 1.0 / 8.0)
    actor_parameters = {id(p) for p in descendant.learner.model.parameters()}
    head_parameters = {
        id(p) for reader in readers.values() for p in reader.model.parameters()
    }
    birth_gates = {
        "boundary_reset_passes": bool(boundary["passes"]),
        "parameters_disjoint": actor_parameters.isdisjoint(head_parameters),
        "all_fresh_optimizers": all(not r.optimizer.state for r in readers.values()),
        "all_fresh_buffers": all(not r.buffer for r in readers.values()),
        "birth_scores_constant": all(
            torch.equal(
                r.scores(panel["observations"]), torch.full((len(uniform), 2, 8), 0.5)
            )
            for r in readers.values()
        ),
        "birth_credit_exact_zero": all(
            not torch.count_nonzero(r.credit_table(panel["observations"], uniform))
            for r in readers.values()
        ),
        "head_parameters_matched_at_birth": len(
            {matched.deep_digest(r.model.state_dict()) for r in readers.values()}
        )
        == 1,
    }
    snapshots = [
        {
            "update": 0,
            "arms": {arm: evaluate_panel(r, panel) for arm, r in readers.items()},
        }
    ]
    rows = []
    for update in range(1, UPDATES + 1):
        rollout, completed = vertical.collect_vertical_rollout(
            descendant, recorder, config, "blind"
        )
        outcomes = recorder.take_outcomes()
        expected = expected_result["history"][update - 1]
        before = matched.soma_environment_digests(descendant, environments)
        global_rng = torch.get_rng_state().clone()
        # Score first, then fit: no new rollout label can enter its own prediction.
        prequential = {
            arm: prequential_rows(r, rollout.observations, rollout.actions, outcomes)
            for arm, r in readers.items()
        }
        fits = {
            arm: r.fit(rollout.observations, rollout.actions, outcomes)
            for arm, r in readers.items()
        }
        if update in SNAPSHOTS:
            snapshots.append(
                {
                    "update": update,
                    "arms": {
                        arm: evaluate_panel(r, panel) for arm, r in readers.items()
                    },
                }
            )
        after = matched.soma_environment_digests(descendant, environments)
        uniform_rollout = torch.full((rollout.actions.numel(), 8), 1 / 8.0)
        credits = {
            arm: r.credit_table(rollout.observations, uniform_rollout)
            for arm, r in readers.items()
        }
        metrics = targeted.targeted_ppo_update(
            descendant,
            rollout,
            config,
            learning_carrier=descendant.learner.germ,
            credit_mode="event_only",
            germ_mode="blind",
        )
        post = matched.soma_environment_digests(descendant, environments)
        gates = {
            "rollout_exact": matched.deep_digest(vars(rollout))
            == expected["rollout_sha256"],
            "completed_episodes_exact": matched.deep_digest(completed)
            == expected["completed_episode_rows_sha256"],
            "ppo_metrics_exact": all(
                metrics[name] == expected[name] for name in dose.METRIC_NAMES
            ),
            "ppo_credit_exact": metrics["credit_audit"] == expected["credit_audit"],
            "post_update_state_exact": post["aggregate"]
            == expected["post_update_soma_environment_sha256"],
            "predictor_does_not_change_soma_or_environment": before == after,
            "global_torch_rng_unchanged": torch.equal(
                global_rng, torch.get_rng_state()
            ),
            "recorded_outcomes_align": outcomes.shape == (*rollout.actions.shape, 2),
            "raw_acquisition_includes_first_events": bool(
                torch.all(outcomes[:, :, 0] >= rollout.event_rewards[:, :, 0])
            ),
            "door_events_exact": torch.equal(
                outcomes[:, :, 1], rollout.event_rewards[:, :, 1]
            ),
            "correct_off_head_learning_exact": readers["correct"].digest()
            == readers["reader_off"].digest(),
            "empty_remains_unchanged": readers["empty"].digest() == empty_birth,
            "null_credit_exact_zero": all(
                not torch.count_nonzero(credits[arm])
                for arm in ("wrong", "empty", "reader_off")
            ),
            "centered_credit_finite": all(
                bool(torch.isfinite(c).all()) for c in credits.values()
            ),
            "policy_weighted_credit_zero": all(
                float((c * uniform_rollout[:, None]).sum(-1).abs().max()) < 1e-6
                for c in credits.values()
            ),
            "shuffle_counts_preserved": all(
                fit["label_counts_preserved"] for fit in fits.values()
            ),
            "buffers_bounded": all(
                len(r.buffer) <= BUFFER_ROLLOUTS for r in readers.values()
            ),
            "rollout_semantics": all(rollout_semantics(rollout).values()),
        }
        rows.append(
            {
                "update": update,
                "rollout_sha256": expected["rollout_sha256"],
                "observed_outcomes_sha256": matched.deep_digest(outcomes),
                "post_update_soma_environment_sha256": post["aggregate"],
                "prequential": prequential,
                "fits": fits,
                "gates": gates,
                "passes": all(gates.values()),
            }
        )
        if not rows[-1]["passes"]:
            atomic_json(
                output / f"founder_{founder}_failed_update.json", rows[-1], root
            )
            raise RuntimeError(
                f"founder {founder} update {update} structural failure: {gates}"
            )
        if update % 5 == 0:
            atomic_json(
                output / f"founder_{founder}_progress.json",
                {
                    "status": "RUNNING",
                    "founder": founder,
                    "update": update,
                    "updated_utc": utc_now(),
                },
                root,
            )
            print(
                f"founder {founder}: consequence replay {update}/{UPDATES}", flush=True
            )
    final_state = matched.soma_environment_digests(descendant, environments)
    gates = {
        **birth_gates,
        "all_100_replays_exact": len(rows) == UPDATES
        and all(r["passes"] for r in rows),
        "all_seven_snapshots_present": [r["update"] for r in snapshots]
        == list(SNAPSHOTS),
        "panel_unmodified": panel_before == matched.deep_digest(panel),
        "carrier_unchanged_64_bytes": packet_array.nbytes == 64
        and np.array_equal(descendant.learner.germ, packet_array)
        and all(
            np.array_equal(
                r.packet,
                empty_germ(1)
                if arm == "empty"
                else vertical.initial_carriers(packet_array)["wrong_frozen"]
                if arm == "wrong"
                else packet_array,
            )
            for arm, r in readers.items()
        ),
        "source_result_hash_exact": sha256_file(Path(source["source_result"]))
        == source["source_result_sha256"],
        "final_state_exact": final_state["aggregate"]
        == expected_result["final_soma_environment_digests"]["aggregate"],
        "wrong_no_confirming_consequences": readers["wrong"].positive_counts == [0, 0],
    }
    checkpoint_path = output / f"founder_{founder}_predictors.pt"
    _atomic_torch_save(
        checkpoint_path,
        {
            "run_id": RUN_ID,
            "founder": founder,
            "incoming_packet": packet_array,
            "readers": {arm: r.state() for arm, r in readers.items()},
            "evaluation_only_panel_sha256": panel["sha256"],
        },
    )
    result = {
        "run_id": RUN_ID,
        "founder": founder,
        "source": dict(source),
        "boundary_audit": boundary,
        "replay_rows": rows,
        "snapshots": snapshots,
        "panel_sha256": panel["sha256"],
        "prequential": {arm: aggregate_prequential(rows, arm) for arm in ARMS},
        "training_counts": {
            arm: {
                "positive": r.positive_counts,
                "negative_target": r.negative_target_counts,
            }
            for arm, r in readers.items()
        },
        "final_predictor_digests": {arm: r.digest() for arm, r in readers.items()},
        "predictor_checkpoint": str(checkpoint_path),
        "final_soma_environment_digests": final_state,
        "completion_gates": gates,
        "completed_cleanly": all(gates.values()),
    }
    atomic_json(output / f"founder_{founder}.json", result, root)
    atomic_json(
        output / f"founder_{founder}_progress.json",
        {
            "status": "COMPLETE" if result["completed_cleanly"] else "FAILED_GATES",
            "update": UPDATES,
            "updated_utc": utc_now(),
        },
        root,
    )
    return result


def markdown_report(audit: Mapping[str, Any]) -> str:
    lines = [
        "# DoorKey isolated consequence-predictor qualification",
        "",
        f"Run: `{RUN_ID}`. Structural completion: `{audit['completed_cleanly']}`.",
        f"Frozen outcome: `{audit['qualification']['label']}`.",
        "",
        "Scores are class-balanced, not calibrated event probabilities. All-action",
        "diagnostic labels come from simulator interventions and never enter training.",
        "Every actor trajectory is the immutable source replay; behavior was not tested.",
        "",
        "| Founder | Channel | Correct within-action AUC | Correct balanced Brier | Shuffled Brier | Correct action rank |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for result in audit["founder_summaries"]:
        for channel in ("key", "door"):
            correct = result["final_panel"]["correct"][channel]
            shuffled = result["final_panel"]["shuffled"][channel]
            lines.append(
                f"| {result['founder']} | {channel} | {correct['target_action']['roc_auc']:.6f} | {correct['target_action']['balanced_brier']:.6f} | {shuffled['target_action']['balanced_brier']:.6f} | {correct['unique_correct_action_fraction']:.6f} |"
            )
    lines.extend(
        [
            "",
            "The germ remains an engineered address/action record. This qualifies only",
            "a possible learned reader, not a useful inherited disposition or learned",
            "ontology. L17 and L20 remain MIXED. A fresh-seed behavior experiment requires",
            "a separate frozen contract; this audit does not train PPO with the new head.",
            "",
        ]
    )
    return "\n".join(lines)


def input_paths(workspace: Path, root: Path, source: Mapping[str, Any]) -> list[Path]:
    paths = dose._input_paths(workspace, root, source)
    paths.extend(
        [
            Path(__file__).resolve(),
            workspace / "src/laws_confirmation/doorkey_dose_matched_credit.py",
            workspace / "src/laws_confirmation/doorkey_env.py",
            workspace / "protocols/DOORKEY_CONSEQUENCE_PREDICTOR_AUDIT_V1.md",
            workspace / "tests/test_doorkey_consequence_predictor.py",
            workspace / "scripts/run_doorkey_consequence_predictor.sh",
        ]
    )
    return sorted(set(paths))


def benchmark(root: Path) -> int:
    """Disposable seeds; outcome measurements cannot select a scientific rule."""
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("cannot replace a benchmark frozen by an initialized run")
    dose.runtime_qualification(MAX_WORKERS)
    source = dose.qualify_source(root)
    if not source["passes"]:
        raise RuntimeError("source qualification failed before benchmark")
    config = FeedbackPPOConfig(**source["replay_sources"][0]["config"])
    packet = np.asarray(source["replay_sources"][0]["incoming_germ"], dtype=np.uint8)
    descendant = vertical.make_vertical_descendant(
        make_boundary_packet(packet), config, 290_000_001
    )
    environments = DoorKeyVectorEnv(
        config.num_envs, 291_000_001, config.max_episode_steps, "terminal"
    )
    recorder = TransitionRecorder(environments)
    readers = make_readers(packet, 292_000_001)
    started = time.monotonic()
    for _ in range(8):
        rollout, _ = vertical.collect_vertical_rollout(
            descendant, recorder, config, "blind"
        )
        outcomes = recorder.take_outcomes()
        for reader in readers.values():
            prequential_rows(reader, rollout.observations, rollout.actions, outcomes)
            reader.fit(rollout.observations, rollout.actions, outcomes)
            reader.digest()
        targeted.targeted_ppo_update(
            descendant,
            rollout,
            config,
            learning_carrier=packet,
            credit_mode="event_only",
            germ_mode="blind",
        )
    elapsed = time.monotonic() - started
    # The full audit also hashes source states, evaluates panels, and runs three
    # simultaneous workers. Conservatively charge 2x the loop and 90s fixed cost.
    projected = elapsed / 8 * UPDATES * 2 + 90
    result = {
        "run_id": RUN_ID,
        "non_scientific": True,
        "loop_updates": 8,
        "elapsed_seconds": elapsed,
        "projected_seconds_three_workers": projected,
        "must_detach": projected > 600,
        "measured_utc": utc_now(),
        "source_qualified": source["passes"],
        "source_sha256": sha256_file(Path(__file__)),
    }
    atomic_json(root / "tmp" / f"{RUN_ID}_benchmark.json", result, root)
    print(json.dumps(result, indent=2))
    return 0


def run_audit(root: Path) -> int:
    started = time.monotonic()
    workspace = Path(__file__).resolve().parents[2]
    output, run = root / "outputs" / RUN_ID, root / "runs" / RUN_ID
    if output.exists() or run.exists():
        raise FileExistsError("immutable run directory already exists")
    runtime = dose.runtime_qualification(MAX_WORKERS)
    source = dose.qualify_source(root)
    if not runtime["passes"] or not source["passes"]:
        raise RuntimeError("runtime/source qualification failed")
    benchmark_path = root / "tmp" / f"{RUN_ID}_benchmark.json"
    timing = json.loads(benchmark_path.read_text())
    if timing["source_sha256"] != sha256_file(Path(__file__)):
        raise RuntimeError("benchmark was not made with this frozen source")
    disk = _disk_preflight(root, 128 * 1024**2)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")
    inputs = input_paths(workspace, root, source) + [benchmark_path]
    hashes = {str(path.resolve()): sha256_file(path) for path in inputs}
    output.mkdir(parents=True)
    run.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "started_utc": utc_now(),
        "source_run_id": targeted.RUN_ID,
        "workers": MAX_WORKERS,
        "threads_per_worker": 1,
        "input_sha256": hashes,
        "contract_digest": canonical_digest(hashes),
        "disk_preflight": disk,
        "benchmark": timing,
        "runtime": runtime,
        "environment": environment_manifest(),
        "repository_head": git_head(workspace),
        "registered_transitions": 3 * targeted.EXPECTED_STEPS,
    }
    atomic_json(run / "MANIFEST.json", manifest, root)
    atomic_json(
        run / "STATUS.json",
        {"status": "RUNNING", "run_id": RUN_ID, "updated_utc": utc_now()},
        root,
    )
    atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
    write_hash_manifest(inputs, output / "input_hashes.sha256", root)
    try:
        panel = make_panel()
        _atomic_torch_save(output / "diagnostic_panel.pt", panel)
        results = []
        with ProcessPoolExecutor(
            max_workers=MAX_WORKERS, mp_context=multiprocessing.get_context("spawn")
        ) as executor:
            futures = [
                executor.submit(replay_founder, row, str(root), str(output))
                for row in source["replay_sources"]
            ]
            for future in as_completed(futures):
                results.append(future.result())
                atomic_json(
                    output / "progress.json",
                    {
                        "status": "RUNNING",
                        "completed_founders": len(results),
                        "updated_utc": utc_now(),
                    },
                    root,
                )
        results.sort(key=lambda r: r["founder"])
        decisions = qualification(results)
        gates = {
            "runtime_qualified": runtime["passes"],
            "source_qualified": source["passes"],
            "three_registered_founders": [r["founder"] for r in results]
            == list(FOUNDERS),
            "all_founder_structural_gates": all(
                r["completed_cleanly"] for r in results
            ),
            "shared_heldout_panel_exact": all(
                r["panel_sha256"] == panel["sha256"] for r in results
            ),
            "inputs_still_verify": all(
                sha256_file(Path(path)) == digest for path, digest in hashes.items()
            ),
        }
        audit = {
            "schema_version": 1,
            "run_id": RUN_ID,
            "generated_utc": utc_now(),
            "source": source,
            "runtime": runtime,
            "elapsed_seconds": time.monotonic() - started,
            "registered_transitions": 3 * targeted.EXPECTED_STEPS,
            "panel": {
                "states": len(panel["states"]),
                "interventions": 8 * len(panel["states"]),
                "sha256": panel["sha256"],
                "layout_count": panel["layout_count"],
            },
            "founder_summaries": [
                {
                    "founder": r["founder"],
                    "final_panel": r["snapshots"][-1]["arms"],
                    "prequential": r["prequential"],
                    "training_counts": r["training_counts"],
                    "completion_gates": r["completion_gates"],
                }
                for r in results
            ],
            "qualification": decisions,
            "completion_gates": gates,
            "completed_cleanly": all(gates.values()),
            "numbered_law_verdict_changes": 0,
        }
        atomic_json(output / "consequence_predictor_audit.json", audit, root)
        atomic_text(output / "audit.md", markdown_report(audit), root)
        outputs = sorted(
            p
            for p in output.rglob("*")
            if p.is_file() and p.name != "output_hashes.sha256"
        )
        write_hash_manifest(outputs, output / "output_hashes.sha256", root)
        verification = _read_hash_manifest(output / "output_hashes.sha256")
        verified = bool(verification) and all(row["matches"] for row in verification)
        success = audit["completed_cleanly"] and verified
        status = {
            "status": "COMPLETE" if success else "FAILED_GATES",
            "run_id": RUN_ID,
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started,
            "completed_cleanly": audit["completed_cleanly"],
            "output_manifest_self_verifies": verified,
            "qualification": decisions["label"],
            "registered_transitions": 3 * targeted.EXPECTED_STEPS,
            "max_workers": MAX_WORKERS,
        }
        atomic_json(run / "STATUS.json", status, root)
        atomic_text(
            run / ("COMPLETE" if success else "FAILED"),
            status["completed_utc"] + "\n",
            root,
        )
        print(output / "audit.md", flush=True)
        return 0 if success else 1
    except Exception as error:
        failure = {
            "status": "FAILED",
            "run_id": RUN_ID,
            "failed_utc": utc_now(),
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run / "STATUS.json", failure, root)
        atomic_text(run / "FAILED", failure["failed_utc"] + "\n", root)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()
    root = external_root(args.external_root)
    return benchmark(root) if args.benchmark else run_audit(root)


if __name__ == "__main__":
    raise SystemExit(main())
