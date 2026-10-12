from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray

from fep_lab.types import CategoricalModel

from .config import ExperimentConfig
from .controllers import (
    ActiveInferenceController,
    NoopController,
    OracleController,
    ReactiveController,
    ScheduledController,
)
from .environment import EnvironmentDesign, GardActiveInferenceEnvironment, encode_observation
from .models import ModelCounts, hidden_state
from .types import (
    Action,
    Controller,
    ControllerName,
    ObservationThresholds,
    RawObservation,
)


@dataclass(frozen=True)
class BehaviorTrace:
    regimes: NDArray[np.int8]
    raw_growth: NDArray[np.int32]
    raw_similarity: NDArray[np.float64]
    raw_alignment: NDArray[np.float64]
    cues: NDArray[np.int8]
    terminal: NDArray[np.int8]
    actions: NDArray[np.int8]


def fitted_thresholds(traces: list[BehaviorTrace]) -> ObservationThresholds:
    if not traces:
        raise ValueError("at least one behavior trace is required")
    alignments = np.concatenate([trace.raw_alignment for trace in traces])
    growth = np.concatenate(
        [
            trace.raw_growth[trace.terminal == 0]
            for trace in traces
            if np.any(trace.terminal == 0)
        ]
    )
    if growth.size == 0:
        growth = np.asarray((100.0, 300.0), dtype=np.float64)
    alignment_cut = np.quantile(alignments, (1.0 / 3.0, 2.0 / 3.0))
    growth_cut = np.quantile(growth, (1.0 / 3.0, 2.0 / 3.0))
    if alignment_cut[1] - alignment_cut[0] < 1e-9:
        center = float(np.mean(alignment_cut))
        alignment_cut = np.asarray((center - 1e-6, center + 1e-6))
    if growth_cut[1] <= growth_cut[0]:
        growth_cut[1] = growth_cut[0] + 1.0
    result = ObservationThresholds(
        alignment=(float(alignment_cut[0]), float(alignment_cut[1])),
        growth=(float(growth_cut[0]), float(growth_cut[1])),
    )
    result.validate()
    return result


def _raw_at(trace: BehaviorTrace, index: int) -> RawObservation:
    return RawObservation(
        growth_steps=int(trace.raw_growth[index]),
        boundary_similarity=float(trace.raw_similarity[index]),
        alignment_score=float(trace.raw_alignment[index]),
        cue=int(trace.cues[index]),
        terminal=bool(trace.terminal[index]),
    )


def counts_from_behavior(
    traces: list[BehaviorTrace], thresholds: ObservationThresholds
) -> ModelCounts:
    counts = ModelCounts.empty()
    for trace in traces:
        observations = [
            encode_observation(_raw_at(trace, index), thresholds)
            for index in range(len(trace.regimes))
        ]
        alignments = [observation[2] for observation in observations]
        states = [
            hidden_state(int(regime), int(alignment))
            for regime, alignment in zip(trace.regimes, alignments, strict=True)
        ]
        counts.add_initial(states[0], observations[0])
        for index, action in enumerate(trace.actions):
            if index + 1 >= len(states):
                break
            counts.add_transition(
                states[index], int(action), states[index + 1], observations[index + 1]
            )
    return counts


def run_behavior_trace(
    config: ExperimentConfig,
    design: EnvironmentDesign,
    beta: NDArray[np.float64],
    initial: NDArray[np.int64],
    seeds: tuple[int, int, int],
    steps: int,
    action_offset: int,
) -> BehaviorTrace:
    environment = GardActiveInferenceEnvironment(
        config,
        design,
        beta,
        initial,
        *seeds,
        thresholds=ObservationThresholds(),
    )
    initial_step = environment.initial_step()
    regimes = [initial_step.external_regime]
    raw = [initial_step.raw_observation]
    actions: list[int] = []
    for step in range(steps):
        action = int((step + action_offset) % 4)
        result = environment.step(action)
        actions.append(action)
        regimes.append(result.external_regime)
        raw.append(result.raw_observation)
        if not result.completed:
            break
    return BehaviorTrace(
        regimes=np.asarray(regimes, dtype=np.int8),
        raw_growth=np.asarray([value.growth_steps for value in raw], dtype=np.int32),
        raw_similarity=np.asarray(
            [value.boundary_similarity for value in raw], dtype=np.float64
        ),
        raw_alignment=np.asarray(
            [value.alignment_score for value in raw], dtype=np.float64
        ),
        cues=np.asarray([value.cue for value in raw], dtype=np.int8),
        terminal=np.asarray([value.terminal for value in raw], dtype=np.int8),
        actions=np.asarray(actions, dtype=np.int8),
    )


def _episode_template(config: ExperimentConfig, policy_count: int = 16) -> dict[str, NDArray]:
    horizon = config.horizon
    n_types = config.gard.n_types
    return {
        "completed": np.zeros(horizon, dtype=np.int8),
        "growth_steps": np.full(horizon, -1, dtype=np.int32),
        "similarity": np.full(horizon, np.nan, dtype=np.float64),
        "alignment_score": np.full(horizon, np.nan, dtype=np.float64),
        "decision_regime": np.full(horizon, -1, dtype=np.int8),
        "result_regime": np.full(horizon, -1, dtype=np.int8),
        "true_state": np.full(horizon, -1, dtype=np.int8),
        "observations": np.full((horizon, 4), -1, dtype=np.int8),
        "intended_actions": np.full(horizon, int(Action.WAIT), dtype=np.int8),
        "executed_actions": np.full(horizon, int(Action.WAIT), dtype=np.int8),
        "abstract_action_cost": np.zeros(horizon, dtype=np.float64),
        "physical_action_cost": np.zeros(horizon, dtype=np.float64),
        "edit_remove": np.full(horizon, -1, dtype=np.int16),
        "edit_add": np.full(horizon, -1, dtype=np.int16),
        "parents": np.zeros((horizon, n_types), dtype=np.int16),
        "compositions": np.zeros((horizon, n_types), dtype=np.int16),
        "beliefs": np.full((horizon, 9), np.nan, dtype=np.float64),
        "predictive_priors": np.full((horizon, 9), np.nan, dtype=np.float64),
        "vfe": np.full(horizon, np.nan, dtype=np.float64),
        "log_evidence": np.full(horizon, np.nan, dtype=np.float64),
        "expected_utility": np.full((horizon, policy_count), np.nan, dtype=np.float64),
        "state_information_gain": np.full(
            (horizon, policy_count), np.nan, dtype=np.float64
        ),
        "adjusted_neg_efe": np.full((horizon, policy_count), np.nan, dtype=np.float64),
        "policy_posterior": np.full((horizon, policy_count), np.nan, dtype=np.float64),
    }


def controller_for(
    name: ControllerName,
    config: ExperimentConfig,
    pooled_model: CategoricalModel,
    local_model: CategoricalModel,
    model_variants: dict[str, CategoricalModel],
    schedule: NDArray[np.int64] | None = None,
) -> Controller:
    if name == ControllerName.AI_POOLED:
        return ActiveInferenceController(pooled_model, config)
    if name == ControllerName.REWARD_POOLED:
        return ActiveInferenceController(model_variants["reward_pooled"], config)
    if name == ControllerName.AI_LOCAL:
        return ActiveInferenceController(local_model, config)
    if name == ControllerName.REWARD_LOCAL:
        return ActiveInferenceController(model_variants["reward_local"], config)
    if name in (ControllerName.RANDOM_POOLED, ControllerName.RANDOM_LOCAL):
        if schedule is None:
            raise ValueError("yoked random controller requires a schedule")
        prior = pooled_model.D if name == ControllerName.RANDOM_POOLED else local_model.D
        return ScheduledController(np.asarray(schedule, dtype=np.int64), prior)
    if name == ControllerName.REACTIVE:
        return ReactiveController(pooled_model.D)
    if name == ControllerName.NOOP:
        return NoopController(pooled_model.D)
    if name == ControllerName.ORACLE:
        return OracleController(pooled_model.D)
    if name == ControllerName.SCRAMBLED:
        return ActiveInferenceController(model_variants["scrambled"], config)
    if name == ControllerName.SENSORY_LESION:
        return ActiveInferenceController(pooled_model, config, sensory_lesion=True)
    if name == ControllerName.ACTION_LESION:
        return ActiveInferenceController(pooled_model, config)
    if name == ControllerName.REVERSED:
        return ActiveInferenceController(model_variants["reversed"], config)
    raise ValueError(f"unsupported controller {name}")


def run_episode(
    config: ExperimentConfig,
    design: EnvironmentDesign,
    beta: NDArray[np.float64],
    initial: NDArray[np.int64],
    thresholds: ObservationThresholds,
    controller_name: ControllerName,
    controller: Controller,
    process_seeds: tuple[int, int, int],
    agent_seed: int,
) -> dict[str, NDArray]:
    environment = GardActiveInferenceEnvironment(
        config,
        design,
        beta,
        initial,
        *process_seeds,
        thresholds=thresholds,
    )
    controller.reset()
    agent_rng = np.random.default_rng(agent_seed)
    current = environment.initial_step()
    observation = encode_observation(current.raw_observation, thresholds)
    arrays = _episode_template(config)
    for step in range(config.horizon):
        decision_regime = environment.regime
        decision_alignment = encode_observation(current.raw_observation, thresholds)[2]
        state = hidden_state(decision_regime, decision_alignment)
        decision = controller.decide(observation, decision_regime, agent_rng)
        action_lesion = controller_name == ControllerName.ACTION_LESION
        result = environment.step(decision.intended_action, action_lesion=action_lesion)
        arrays["completed"][step] = int(result.completed)
        arrays["growth_steps"][step] = result.raw_observation.growth_steps
        arrays["similarity"][step] = result.raw_observation.boundary_similarity
        arrays["alignment_score"][step] = result.raw_observation.alignment_score
        arrays["decision_regime"][step] = decision_regime
        arrays["result_regime"][step] = result.external_regime
        arrays["true_state"][step] = state
        arrays["observations"][step] = observation
        arrays["intended_actions"][step] = decision.intended_action
        arrays["executed_actions"][step] = result.executed_action
        arrays["abstract_action_cost"][step] = result.abstract_action_cost
        arrays["physical_action_cost"][step] = result.physical_action_cost
        arrays["edit_remove"][step] = result.edit_remove
        arrays["edit_add"][step] = result.edit_add
        if result.parent is not None:
            arrays["parents"][step] = result.parent
        arrays["compositions"][step] = result.composition
        arrays["beliefs"][step] = decision.posterior
        arrays["predictive_priors"][step] = decision.predictive_prior
        arrays["vfe"][step] = decision.vfe
        arrays["log_evidence"][step] = decision.log_evidence
        arrays["expected_utility"][step] = decision.expected_utility
        arrays["state_information_gain"][step] = decision.state_information_gain
        arrays["adjusted_neg_efe"][step] = decision.adjusted_neg_efe
        arrays["policy_posterior"][step] = decision.policy_posterior
        believed_action = (
            decision.intended_action if action_lesion else result.executed_action
        )
        controller.advance(decision.posterior, believed_action)
        current = result
        observation = encode_observation(result.raw_observation, thresholds)
        if not result.completed:
            break
    return arrays


def stack_episodes(episodes: list[dict[str, NDArray]]) -> dict[str, NDArray]:
    if not episodes:
        raise ValueError("cannot stack an empty episode list")
    names = tuple(episodes[0])
    if any(tuple(episode) != names for episode in episodes):
        raise ValueError("episode array schemas differ")
    return {
        name: np.stack([episode[name] for episode in episodes], axis=0)
        for name in names
    }
